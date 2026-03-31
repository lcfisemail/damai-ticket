"""
QThread <-> asyncio 桥接

所有异步网络操作（登录、监控、下单）运行在独立的 QThread 中的 asyncio 事件循环里。
与 GUI 线程的通信完全通过 Qt Signal/Slot 机制，绝不直接跨线程调用方法。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from damai.core.account import AccountConfig, AccountPool
from damai.core.auth import AuthManager
from damai.core.captcha import CaptchaChallenge, CaptchaSolution, ManualCaptchaHandler
from damai.core.monitor import SessionWarmup, TicketMonitor, extract_item_id
from damai.core.order import BuyerInfo
from damai.utils.time_sync import parse_sale_start_time, sleep_until, sync_time


class LoginWorker(QThread):
    """账号登录工作线程。"""

    login_success = Signal(dict)
    login_failed = Signal(str)

    def __init__(
        self,
        login_method: str,
        login_payload: str,
        nickname: str,
        data_dir: Path,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._login_method = login_method
        self._login_payload = login_payload
        self._nickname = nickname
        self._data_dir = data_dir

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._login())
        finally:
            loop.close()

    async def _login(self):
        auth = AuthManager(data_dir=self._data_dir)
        try:
            if self._login_method == "cookie":
                account = await auth.login_by_cookie(
                    self._login_payload,
                    self._nickname,
                )
            elif self._login_method == "saved_cookie":
                account = await auth.login_by_saved_cookie(self._nickname)
            else:
                raise ValueError(f"不支持的登录方式: {self._login_method}")
            self.login_success.emit(
                {
                    "nickname": account.nickname,
                    "display_name": account.profile.display_name,
                    "user_id": account.profile.user_id,
                }
            )
        except Exception as error:
            self.login_failed.emit(str(error))


class TicketWorker(QThread):
    """
    抢票工作线程。
    完整流程：NTP同步 -> 会话预热 -> 定时等待 -> 监控 -> 并发下单 -> 通知
    """

    status_update = Signal(str)
    order_success = Signal(dict)
    order_failed = Signal(str)
    captcha_required = Signal(object)
    log_message = Signal(str, str)

    def __init__(
        self,
        config: dict,
        accounts_config: list,
        data_dir: Path,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config = config
        self._accounts_config = accounts_config
        self._data_dir = data_dir
        self._captcha_handler: Optional[ManualCaptchaHandler] = None
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True
        if self._captcha_handler:
            self._captcha_handler.cancel()

    def submit_captcha(self, solution: CaptchaSolution):
        if self._captcha_handler:
            self._captcha_handler.submit_solution(solution)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._main())
        except Exception as error:
            self.order_failed.emit(f"任务异常: {error}")
        finally:
            loop.close()

    async def _main(self):
        cfg = self._config
        target_cfg = cfg.get("target", {})
        timing_cfg = cfg.get("timing", {})

        event_url = target_cfg.get("event_url", "")
        item_id = extract_item_id(event_url)
        if not item_id:
            self.order_failed.emit(f"无法从 URL 中提取演出ID: {event_url}")
            return

        self.status_update.emit("正在同步时间...")
        await asyncio.get_event_loop().run_in_executor(None, sync_time)

        self.status_update.emit("正在初始化账号...")
        auth_manager = AuthManager(data_dir=self._data_dir)
        pool = AccountPool(auth_manager=auth_manager)
        configs = [
            AccountConfig(
                nickname=config.get("nickname", ""),
                cookie_string=config.get("cookie_string", ""),
                proxy=config.get("proxy", ""),
                buyers=config.get("buyers", []),
            )
            for config in self._accounts_config
        ]
        count = await pool.initialize_all(configs)
        if count == 0:
            self.order_failed.emit("没有可用账号，请先登录")
            return
        self.status_update.emit(f"已初始化 {count} 个账号")

        def on_captcha(challenge: CaptchaChallenge):
            self.captcha_required.emit(challenge)

        self._captcha_handler = ManualCaptchaHandler(on_captcha_required=on_captcha)

        sale_start_str = timing_cfg.get("sale_start_time", "")
        sale_ts = parse_sale_start_time(sale_start_str) if sale_start_str else None

        if sale_ts:
            import time

            warmup_duration = min(30.0, sale_ts - time.time() - 5)
            if warmup_duration > 0:
                self.status_update.emit(f"会话预热中 ({warmup_duration:.0f}s)...")
                if pool.active_accounts:
                    client = pool.get_client(pool.active_accounts[0].nickname)
                    if client:
                        warmup = SessionWarmup(client, item_id)
                        await warmup.warmup(warmup_duration)

            self.status_update.emit("等待开售时间...")
            await asyncio.get_event_loop().run_in_executor(
                None,
                sleep_until,
                sale_ts,
                2.0,
            )

        self.status_update.emit("监控中，等待开票...")
        first_client = pool.get_client(pool.active_accounts[0].nickname)
        monitor = TicketMonitor(
            client=first_client,
            item_id=item_id,
            target_sessions=target_cfg.get("sessions", []),
            target_tiers=target_cfg.get("tiers", []),
            poll_interval_min=timing_cfg.get("poll_interval_min", 0.5),
            poll_interval_max=timing_cfg.get("poll_interval_max", 2.0),
        )

        try:
            ticket_event = await monitor.watch()
        except asyncio.CancelledError:
            self.status_update.emit("监控已停止")
            return

        self.status_update.emit(
            f"发现票档: {ticket_event.session_name} - {ticket_event.tier_name}"
        )

        self.status_update.emit("正在抢票...")
        buyers_raw = target_cfg.get("buyers", [])
        buyers = []
        for buyer in buyers_raw:
            if isinstance(buyer, dict):
                buyers.append(
                    BuyerInfo(
                        buyer_id=buyer.get("id", ""),
                        name=buyer.get("name", ""),
                        id_card=buyer.get("id_card", ""),
                        phone=buyer.get("phone", ""),
                    )
                )
            else:
                buyers.append(BuyerInfo(buyer_id=str(buyer), name=""))

        count_tickets = target_cfg.get("ticket_count", 1)

        result = await pool.race_purchase(
            ticket_event=ticket_event,
            buyers=buyers,
            count=count_tickets,
            max_retries=timing_cfg.get("order_retry_max", 10),
        )

        if result and result.success:
            self.order_success.emit(
                {"order_id": result.order_id, "message": result.message}
            )
            self.status_update.emit(f"抢票成功！订单号: {result.order_id}")
        else:
            message = result.message if result else "未知错误"
            self.order_failed.emit(message)
            self.status_update.emit(f"抢票失败: {message}")
