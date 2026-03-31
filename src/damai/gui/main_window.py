"""主窗口。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)
from loguru import logger

from damai.core.captcha import CaptchaSolution
from damai.gui.widgets.log_tab import LogTab
from damai.gui.widgets.login_tab import LoginTab
from damai.gui.widgets.qr_login_dialog import QrLoginDialog
from damai.gui.widgets.settings_tab import SettingsTab
from damai.gui.widgets.task_tab import TaskTab
from damai.gui.workers import LoginWorker, TicketWorker


class CaptchaDialog(QDialog):
    """验证码手动解决对话框。"""

    def __init__(self, challenge_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("请完成验证码")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "大麦网触发了滑动验证码。\n"
                "请在浏览器中完成验证后，将 nc_token 粘贴到下方:"
            )
        )
        self._token_input = QTextEdit()
        self._token_input.setMaximumHeight(60)
        layout.addWidget(self._token_input)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_solution(self) -> CaptchaSolution:
        return CaptchaSolution(nc_token=self._token_input.toPlainText().strip())


class MainWindow(QMainWindow):
    """大麦抢票工具主窗口。"""

    def __init__(self, data_dir: Path):
        super().__init__()
        self._data_dir = data_dir
        self._ticket_worker: TicketWorker | None = None
        self._login_worker: LoginWorker | None = None
        self._accounts_config: list = []
        self._setup_ui()
        self._setup_loguru_sink()

    def _setup_ui(self):
        self.setWindowTitle("大麦网抢票工具 v0.1")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        self._login_tab = LoginTab()
        self._task_tab = TaskTab()
        self._log_tab = LogTab()
        self._settings_tab = SettingsTab(config_path=self._data_dir / "settings.toml")

        tabs.addTab(self._login_tab, "登录")
        tabs.addTab(self._task_tab, "任务")
        tabs.addTab(self._log_tab, "日志")
        tabs.addTab(self._settings_tab, "设置")

        self.statusBar().showMessage("就绪")

        self._login_tab.login_requested.connect(self._on_login_requested)
        self._login_tab.qr_login_requested.connect(self._on_qr_login_requested)
        self._login_tab.remove_requested.connect(self._on_remove_requested)
        self._task_tab.start_requested.connect(self._on_start_requested)
        self._task_tab.stop_requested.connect(self._on_stop_requested)

    def _setup_loguru_sink(self):
        def gui_sink(message):
            record = message.record
            level = record["level"].name
            text = record["message"]
            self._log_tab.append_log(level, text)

        logger.add(gui_sink, format="{message}")

    def _start_login_worker(self, login_method: str, login_payload: str, nickname: str):
        if self._login_worker and self._login_worker.isRunning():
            self._login_tab.reset_login_state()
            return

        self._login_worker = LoginWorker(
            login_method=login_method,
            login_payload=login_payload,
            nickname=nickname,
            data_dir=self._data_dir,
        )
        self._login_worker.login_success.connect(self._on_login_success)
        self._login_worker.login_failed.connect(self._on_login_failed)
        self._login_worker.start()

    @Slot(str, str, str)
    def _on_login_requested(self, login_method: str, login_payload: str, nickname: str):
        self.statusBar().showMessage(f"正在登录账号 {nickname}...")
        self._start_login_worker(login_method, login_payload, nickname)

    @Slot(str)
    def _on_qr_login_requested(self, nickname: str):
        dialog = QrLoginDialog(self)
        self.statusBar().showMessage("请在弹窗中完成扫码登录")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._login_tab.reset_login_state()
            self.statusBar().showMessage("已取消扫码登录")
            return

        cookie_string = dialog.get_cookie_string().strip()
        if not cookie_string:
            self._login_tab.reset_login_state()
            QMessageBox.warning(self, "提示", "未从扫码登录页获取到 Cookie")
            return

        self.statusBar().showMessage(f"正在导入账号 {nickname} 的扫码登录态...")
        self._start_login_worker("cookie", cookie_string, nickname)

    @Slot(dict)
    def _on_login_success(self, profile: dict):
        nickname = profile.get("nickname", "")
        display_name = profile.get("display_name", "")
        user_id = profile.get("user_id", "")
        logger.success(f"账号 {nickname} 登录成功")

        status_parts = [f"账号 {nickname} 已登录"]
        if display_name:
            status_parts.append(f"昵称: {display_name}")
        if user_id:
            status_parts.append(f"UID: {user_id}")
        self.statusBar().showMessage(" | ".join(status_parts))

        self._login_tab.on_login_result(
            True,
            nickname,
            display_name=display_name,
            user_id=user_id,
        )
        if not any(account["nickname"] == nickname for account in self._accounts_config):
            self._accounts_config.append(
                {
                    "nickname": nickname,
                    "cookie_string": "",
                    "display_name": display_name,
                    "user_id": user_id,
                }
            )

    @Slot(str)
    def _on_login_failed(self, error: str):
        logger.error(f"登录失败: {error}")
        self._login_tab.on_login_result(False, "", error)

    @Slot(str)
    def _on_remove_requested(self, nickname: str):
        self._accounts_config = [
            account
            for account in self._accounts_config
            if account.get("nickname") != nickname
        ]
        self.statusBar().showMessage(f"已移除账号 {nickname}")

    @Slot(dict)
    def _on_start_requested(self, config: dict):
        if not self._accounts_config:
            QMessageBox.warning(self, "提示", "请先在「登录」标签页添加账号")
            return

        if self._ticket_worker and self._ticket_worker.isRunning():
            return

        settings = self._settings_tab.get_settings()
        config["timing"].update(settings.get("timing", {}))

        self._ticket_worker = TicketWorker(
            config=config,
            accounts_config=self._accounts_config,
            data_dir=self._data_dir,
        )
        self._ticket_worker.status_update.connect(self._on_status_update)
        self._ticket_worker.order_success.connect(self._on_order_success)
        self._ticket_worker.order_failed.connect(self._on_order_failed)
        self._ticket_worker.captcha_required.connect(self._on_captcha_required)
        self._ticket_worker.finished.connect(lambda: self._task_tab.set_running(False))
        self._ticket_worker.start()
        self._task_tab.set_running(True)
        logger.info("抢票任务已启动")

    @Slot()
    def _on_stop_requested(self):
        if self._ticket_worker:
            self._ticket_worker.stop()
            self._ticket_worker.wait(3000)
        self._task_tab.set_running(False)
        self.statusBar().showMessage("已停止")
        logger.info("抢票任务已停止")

    @Slot(str)
    def _on_status_update(self, message: str):
        self._task_tab.update_status(message)
        self.statusBar().showMessage(message)

    @Slot(dict)
    def _on_order_success(self, result: dict):
        order_id = result.get("order_id", "")
        logger.success(f"抢票成功！订单号: {order_id}")
        QMessageBox.information(
            self,
            "抢票成功！",
            f"订单号: {order_id}\n\n请尽快前往大麦网完成支付！",
        )
        self._task_tab.set_running(False)

    @Slot(str)
    def _on_order_failed(self, message: str):
        logger.error(f"抢票失败: {message}")
        self._task_tab.set_running(False)

    @Slot(object)
    def _on_captcha_required(self, challenge):
        dialog = CaptchaDialog(
            challenge_data=challenge.raw_data if hasattr(challenge, "raw_data") else {},
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            solution = dialog.get_solution()
            if self._ticket_worker:
                self._ticket_worker.submit_captcha(solution)
        else:
            self._on_stop_requested()

    def closeEvent(self, event):
        if self._ticket_worker and self._ticket_worker.isRunning():
            self._ticket_worker.stop()
            self._ticket_worker.wait(2000)
        super().closeEvent(event)
