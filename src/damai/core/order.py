"""
下单引擎

大麦网购票流程：
1. order.build  (mtop.trade.order.build.h5)   — 构建订单，获取 submitRef
2. order.create (mtop.trade.order.create.h5)  — 提交订单，获取订单 ID

失败处理：
- 票档售罄 → 自动尝试下一个备选票档
- 限流     → 指数退避重试
- 验证码   → 挂起等待 GUI 用户完成
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from damai.constants import API_ORDER_BUILD, API_ORDER_CREATE
from damai.core.captcha import CaptchaChallenge, ManualCaptchaHandler
from damai.core.monitor import TicketAvailableEvent
from damai.core.mtop_client import MtopClient
from damai.exceptions import (
    CaptchaRequiredError,
    OrderBuildError,
    OrderCreateError,
    SoldOutError,
    TrafficLimitError,
)


@dataclass
class BuyerInfo:
    """观演人信息"""
    buyer_id: str
    name: str
    id_card: str = ""
    phone: str = ""


@dataclass
class OrderResult:
    """下单结果"""
    success: bool
    order_id: str = ""
    message: str = ""
    raw_response: dict = field(default_factory=dict)


class OrderEngine:
    """
    下单引擎

    用法:
        engine = OrderEngine(client=mtop_client, captcha_handler=handler)
        result = await engine.execute_purchase(
            monitor_result=ticket_event,
            buyers=[BuyerInfo(buyer_id="xxx", name="张三")],
            count=1,
        )
    """

    def __init__(
        self,
        client: MtopClient,
        captcha_handler: Optional[ManualCaptchaHandler] = None,
        fallback_tiers: list[str] | None = None,
        max_retries: int = 10,
        backoff_base: float = 0.1,
    ):
        self._client = client
        self._captcha_handler = captcha_handler
        self._fallback_tiers = fallback_tiers or []
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    async def execute_purchase(
        self,
        monitor_result: TicketAvailableEvent,
        buyers: list[BuyerInfo],
        count: int = 1,
    ) -> OrderResult:
        """
        执行完整购票流程：build → create。
        在失败时自动重试或切换票档。
        """
        tier_candidates = [
            (monitor_result.tier_id, monitor_result.tier_name)
        ] + [(t, t) for t in self._fallback_tiers if t != monitor_result.tier_id]

        for tier_id, tier_name in tier_candidates:
            logger.info(f"尝试购买票档: {tier_name} (ID: {tier_id})")
            result = await self._try_purchase(
                item_id=monitor_result.item_id,
                session_id=monitor_result.session_id,
                tier_id=tier_id,
                sku_id=monitor_result.sku_id,
                buyers=buyers,
                count=count,
            )
            if result.success:
                return result
            if "售罄" in result.message or "无票" in result.message:
                logger.warning(f"票档 {tier_name} 已售罄，尝试备选")
                continue
            # 其他失败不切票档
            return result

        return OrderResult(success=False, message="所有票档均已售罄")

    async def _try_purchase(
        self,
        item_id: str,
        session_id: str,
        tier_id: str,
        sku_id: str,
        buyers: list[BuyerInfo],
        count: int,
    ) -> OrderResult:
        """单个票档的购买尝试（含重试）"""
        attempt = 0
        while attempt < self._max_retries:
            try:
                build_result = await self._build_order(
                    item_id, session_id, tier_id, sku_id, buyers, count
                )
                return await self._create_order(build_result)

            except CaptchaRequiredError as e:
                if self._captcha_handler:
                    logger.warning("下单触发验证码，等待用户完成")
                    challenge = CaptchaChallenge(raw_data=e.captcha_data)
                    await self._captcha_handler.solve(challenge)
                    # 验证码完成后重试，不消耗重试配额
                    continue
                return OrderResult(success=False, message="需要验证码但未配置处理器")

            except TrafficLimitError:
                wait = self._backoff_base * (2 ** attempt) + random.uniform(0, 0.05)
                logger.warning(
                    f"下单被限流，{wait:.2f}s 后重试 ({attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait)
                attempt += 1

            except SoldOutError as e:
                return OrderResult(success=False, message=f"售罄: {e}")

            except (OrderBuildError, OrderCreateError) as e:
                logger.error(f"下单失败: {e}")
                return OrderResult(success=False, message=str(e))

        return OrderResult(success=False, message=f"超过最大重试次数 ({self._max_retries})")

    async def _build_order(
        self,
        item_id: str,
        session_id: str,
        tier_id: str,
        sku_id: str,
        buyers: list[BuyerInfo],
        count: int,
    ) -> dict:
        """
        Phase 1: mtop.trade.order.build.h5
        提交场次、票档、观演人信息，获取 submitRef 和订单预览数据
        """
        buyer_list = [
            {
                "id": b.buyer_id,
                "name": b.name,
                "idNo": b.id_card,
                "mobile": b.phone,
            }
            for b in buyers
        ]

        data = {
            "itemId": item_id,
            "performId": session_id,
            "priceId": tier_id,
            "skuId": sku_id,
            "count": count,
            "buyerList": buyer_list,
        }

        resp = await self._client.execute(API_ORDER_BUILD, "1.0", data)

        if not resp.is_success:
            # 检查是否售罄
            if any("nostock" in r.lower() or "售罄" in r for r in resp.ret):
                raise SoldOutError("票档已售罄")
            raise OrderBuildError(f"构建订单失败: {resp.ret}")

        build_data = resp.data
        inner = build_data.get("data")
        if not inner:
            raise OrderBuildError(f"build 响应缺少 data 字段: {build_data}")

        logger.debug(f"order.build 成功，submitRef: {str(inner.get('submitRef', 'N/A'))[:20]}...")
        return build_data

    async def _create_order(self, build_result: dict) -> OrderResult:
        """
        Phase 2: mtop.trade.order.create.h5
        提交 build 结果，创建最终订单
        """
        order_data = build_result.get("data", {})
        submit_ref = order_data.get("submitRef", "")

        if not submit_ref:
            raise OrderCreateError("build 结果中缺少 submitRef")

        data = {
            "submitRef": submit_ref,
            "data": order_data,
        }

        resp = await self._client.execute(API_ORDER_CREATE, "1.0", data)

        if not resp.is_success:
            if any("nostock" in r.lower() or "售罄" in r for r in resp.ret):
                raise SoldOutError("创建订单时票档售罄")
            raise OrderCreateError(f"创建订单失败: {resp.ret}")

        result_data = resp.data
        order_id = (
            result_data.get("data", {}).get("orderId")
            or result_data.get("orderId", "")
        )

        logger.success(f"下单成功！订单号: {order_id}")
        return OrderResult(
            success=True,
            order_id=str(order_id),
            message="下单成功",
            raw_response=result_data,
        )
