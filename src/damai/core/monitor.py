"""
票务监控引擎

轮询大麦网演出详情接口，检测票档开售状态，
在发现可购买票档后触发下单流程。
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, parse_qs

from loguru import logger

from damai.constants import API_DETAIL, API_SUBPAGE
from damai.core.mtop_client import MtopClient
from damai.exceptions import CaptchaRequiredError, TrafficLimitError


@dataclass
class TicketAvailableEvent:
    """当监控到可购买票档时触发的事件"""
    item_id: str                     # 演出 ID
    session_id: str                  # 场次 ID
    session_name: str                # 场次名称
    tier_id: str                     # 票档 ID
    tier_name: str                   # 票档名称
    price: int                       # 票价（分）
    sku_id: str = ""                 # SKU ID
    raw_detail: dict = field(default_factory=dict)


def extract_item_id(url: str) -> Optional[str]:
    """
    从大麦网演出 URL 中提取 itemId
    支持格式:
    - https://detail.damai.cn/item.htm?id=123456789
    - https://m.damai.cn/damai/detail/item.html?itemId=123456789
    """
    # 尝试 query 参数
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for key in ("id", "itemId", "item_id"):
        if key in qs:
            return qs[key][0]
    # 尝试路径中的纯数字
    match = re.search(r"/(\d{8,})", parsed.path)
    if match:
        return match.group(1)
    return None


class TicketMonitor:
    """
    票务监控器

    用法:
        monitor = TicketMonitor(
            client=mtop_client,
            item_id="123456789",
            target_sessions=["场次A"],   # 空=任意
            target_tiers=["内场站票"],    # 按优先级，空=任意
        )
        event = await monitor.watch()
        # event.session_id, event.tier_id 即可用于下单
    """

    def __init__(
        self,
        client: MtopClient,
        item_id: str,
        target_sessions: list[str] | None = None,
        target_tiers: list[str] | None = None,
        poll_interval_min: float = 0.5,
        poll_interval_max: float = 2.0,
        on_captcha: Optional[object] = None,
    ):
        self._client = client
        self._item_id = item_id
        self._target_sessions = target_sessions or []
        self._target_tiers = target_tiers or []
        self._poll_min = poll_interval_min
        self._poll_max = poll_interval_max
        self._on_captcha = on_captcha
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """外部停止监控"""
        self._stop_event.set()

    async def watch(self) -> TicketAvailableEvent:
        """
        持续轮询直到发现可购买票档。
        返回 TicketAvailableEvent，调用方可立即发起下单。
        """
        logger.info(
            f"开始监控演出 {self._item_id}，"
            f"目标场次={self._target_sessions}，"
            f"目标票档={self._target_tiers}"
        )
        poll_count = 0

        while not self._stop_event.is_set():
            poll_count += 1
            try:
                event = await self._poll_once()
                if event:
                    logger.success(
                        f"发现可购买票档: {event.session_name} - "
                        f"{event.tier_name} ¥{event.price // 100}"
                    )
                    return event
            except TrafficLimitError:
                logger.warning("轮询被限流，稍后重试")
                await asyncio.sleep(1.0)
                continue
            except CaptchaRequiredError as e:
                logger.warning("轮询触发验证码")
                if self._on_captcha:
                    try:
                        await self._on_captcha.solve(e.captcha_data)
                    except Exception:
                        pass
                await asyncio.sleep(2.0)
                continue
            except Exception as e:
                logger.error(f"轮询异常: {e}")
                await asyncio.sleep(2.0)
                continue

            interval = random.uniform(self._poll_min, self._poll_max)
            if poll_count % 10 == 0:
                logger.debug(f"已轮询 {poll_count} 次，间隔 {interval:.2f}s")
            await asyncio.sleep(interval)

        raise asyncio.CancelledError("监控已停止")

    async def _poll_once(self) -> Optional[TicketAvailableEvent]:
        """单次轮询，返回可购买事件或 None"""
        resp = await self._client.execute(
            API_DETAIL,
            "1.0",
            {"itemId": self._item_id},
        )

        if not resp.is_success:
            return None

        detail = resp.data.get("detail", {})
        perform = detail.get("perform", {})

        # 检查演出状态
        perform_status = perform.get("performStatus", {})
        status_name = perform_status.get("name", "")
        if status_name not in ("立即购买", "马上抢"):
            logger.debug(f"演出状态: {status_name}，继续等待")
            return None

        # 解析场次和票档
        sessions = perform.get("performs", [])
        for session in sessions:
            session_id = str(session.get("performId", ""))
            session_name = session.get("performName", "")

            # 过滤目标场次
            if self._target_sessions and not any(
                t in session_name for t in self._target_sessions
            ):
                continue

            # 遍历票档（按用户优先级排序）
            tiers = session.get("priceList", [])
            matched_tiers = self._filter_and_sort_tiers(tiers)

            for tier in matched_tiers:
                tier_id = str(tier.get("priceId", ""))
                tier_name = tier.get("priceName", "")
                price = int(tier.get("price", 0))  # 分
                sku_id = str(tier.get("skuId", ""))

                # 检查是否可购买（priceStatus == 1 表示有票可买）
                tier_status = tier.get("priceStatus", 1)
                if tier_status != 1:
                    continue

                return TicketAvailableEvent(
                    item_id=self._item_id,
                    session_id=session_id,
                    session_name=session_name,
                    tier_id=tier_id,
                    tier_name=tier_name,
                    price=price,
                    sku_id=sku_id,
                    raw_detail=detail,
                )

        return None

    def _filter_and_sort_tiers(self, tiers: list[dict]) -> list[dict]:
        """按用户配置的票档优先级过滤和排序"""
        if not self._target_tiers:
            return tiers

        priority_map = {name: i for i, name in enumerate(self._target_tiers)}
        matched = []
        for tier in tiers:
            tier_name = tier.get("priceName", "")
            # Find the highest-priority (lowest index) target keyword that matches
            best = min(
                (priority_map[t] for t in priority_map if t in tier_name),
                default=None,
            )
            if best is not None:
                matched.append((best, tier))

        matched.sort(key=lambda x: x[0])
        return [t for _, t in matched]


class SessionWarmup:
    """开售前的会话预热，模拟正常用户浏览行为"""

    def __init__(self, client: MtopClient, item_id: str):
        self._client = client
        self._item_id = item_id

    async def warmup(self, duration_seconds: float = 30.0) -> None:
        """
        在开售前 duration_seconds 秒内进行随机浏览行为，
        建立正常的请求基线，减少触发风控的概率。
        """
        logger.info(f"开始会话预热，持续 {duration_seconds:.0f}s")
        deadline = time.time() + duration_seconds
        while time.time() < deadline:
            try:
                await self._client.execute(
                    API_DETAIL,
                    "1.0",
                    {"itemId": self._item_id},
                )
            except Exception:
                pass
            await asyncio.sleep(random.uniform(3.0, 8.0))
        logger.info("会话预热完成")
