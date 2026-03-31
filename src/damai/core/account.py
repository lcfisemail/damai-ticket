"""
多账号并发管理

核心能力：
- 管理多个已登录账号（各自独立的 session/cookie/指纹/代理）
- 开抢时所有账号并发下单
- 任一账号成功后通过 asyncio.Event 取消其余任务
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from damai.core.auth import Account, AuthManager
from damai.core.monitor import TicketAvailableEvent
from damai.core.mtop_client import MtopClient
from damai.core.order import BuyerInfo, OrderEngine, OrderResult
from damai.exceptions import AuthError


@dataclass
class AccountConfig:
    """账号配置"""
    nickname: str
    cookie_string: str = ""   # 直接提供 cookie 字符串
    proxy: str = ""            # 该账号专用代理（可选）
    buyers: list = field(default_factory=list)  # 该账号的观演人列表


class AccountPool:
    """
    多账号池

    用法:
        pool = AccountPool(auth_manager=auth_mgr)
        await pool.add_account(AccountConfig(nickname="账号1", cookie_string="..."))
        result = await pool.race_purchase(ticket_event, buyers, count=1)
    """

    def __init__(self, auth_manager: AuthManager):
        self._auth_manager = auth_manager
        self._accounts: list[Account] = []
        self._clients: dict[str, MtopClient] = {}  # nickname -> MtopClient

    async def add_account(self, config: AccountConfig) -> bool:
        """添加并登录一个账号"""
        try:
            if config.cookie_string:
                account = await self._auth_manager.login_by_cookie(
                    config.cookie_string,
                    nickname=config.nickname,
                )
            else:
                account = await self._auth_manager.login_by_saved_cookie(config.nickname)

            self._accounts.append(account)
            self._clients[config.nickname] = MtopClient(account.session)
            logger.info(f"账号 {config.nickname} 添加成功")
            return True
        except AuthError as e:
            logger.error(f"账号 {config.nickname} 登录失败: {e}")
            return False

    async def initialize_all(self, configs: list[AccountConfig]) -> int:
        """并发初始化所有账号，返回成功数"""
        results = await asyncio.gather(
            *[self.add_account(c) for c in configs],
            return_exceptions=True,
        )
        success_count = sum(1 for r in results if r is True)
        logger.info(f"账号初始化完成: {success_count}/{len(configs)} 成功")
        return success_count

    @property
    def active_accounts(self) -> list[Account]:
        return [a for a in self._accounts if a.logged_in]

    async def race_purchase(
        self,
        ticket_event: TicketAvailableEvent,
        buyers: list[BuyerInfo],
        count: int = 1,
        max_retries: int = 10,
    ) -> Optional[OrderResult]:
        """
        所有活跃账号并发下单，返回第一个成功结果。
        """
        if not self.active_accounts:
            logger.error("没有可用账号")
            return None

        async def account_purchase(account: Account) -> Optional[OrderResult]:
            client = self._clients.get(account.nickname)
            if not client:
                return None

            engine = OrderEngine(client=client, max_retries=max_retries)
            try:
                result = await engine.execute_purchase(ticket_event, buyers, count)
                if result.success:
                    logger.success(
                        f"[{account.nickname}] 抢票成功！订单: {result.order_id}"
                    )
                return result
            except asyncio.CancelledError:
                logger.debug(f"[{account.nickname}] 任务已取消")
                return None
            except Exception as e:
                logger.error(f"[{account.nickname}] 抢票异常: {e}")
                return None

        tasks = [
            asyncio.create_task(account_purchase(acc))
            for acc in self.active_accounts
        ]

        logger.info(f"启动 {len(tasks)} 个账号并发抢票")

        # 轮询完成任务，直到找到成功结果或所有任务均结束
        pending = set(tasks)
        winner: Optional[OrderResult] = None
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                try:
                    result = task.result()
                    if result and result.success:
                        winner = result
                        break
                except Exception:
                    pass
            if winner:
                break

        # 取消仍在运行的任务
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        if winner:
            return winner

        logger.warning("所有账号抢票均未成功")
        return None

    def get_client(self, nickname: str) -> Optional[MtopClient]:
        return self._clients.get(nickname)

    def remove_account(self, nickname: str) -> bool:
        self._accounts = [a for a in self._accounts if a.nickname != nickname]
        removed = nickname in self._clients
        self._clients.pop(nickname, None)
        return removed
