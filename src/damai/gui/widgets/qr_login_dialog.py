"""扫码登录对话框。"""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from damai.core.auth import analyze_cookie_text, build_cookie_string

try:
    from PySide6.QtNetwork import QNetworkCookie
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWebEngineWidgets import QWebEngineView

    WEBENGINE_AVAILABLE = True
except ImportError:
    QNetworkCookie = object
    QWebEnginePage = object
    QWebEngineProfile = object
    QWebEngineView = object
    WEBENGINE_AVAILABLE = False


class QrLoginDialog(QDialog):
    LOGIN_URL = (
        "https://passport.alibaba.com/mini_login.htm"
        "?style=mini&appName=damai&appEntrance=web"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cookies: dict[str, str] = {}
        self._profile = None
        self._page = None
        self._view = None
        self._status_label = QLabel()
        self._import_button = None
        self._setup_ui()
        self._refresh_status()
        if WEBENGINE_AVAILABLE:
            self._setup_webview()

    def _setup_ui(self):
        self.setWindowTitle("扫码登录")
        self.resize(720, 760)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "请在下方官方登录页中完成扫码或账号登录。\n"
            "检测到有效 Cookie 后，可直接导入当前登录态。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        if WEBENGINE_AVAILABLE:
            self._view = QWebEngineView(self)
            layout.addWidget(self._view, 1)
        else:
            fallback = QLabel("当前环境缺少 QtWebEngine，无法使用内嵌扫码登录。")
            fallback.setWordWrap(True)
            layout.addWidget(fallback)

        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        button_box = QDialogButtonBox(self)
        refresh_button = QPushButton("重新加载")
        button_box.addButton(refresh_button, QDialogButtonBox.ButtonRole.ActionRole)
        self._import_button = button_box.addButton(
            "导入当前登录态",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_button = button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        refresh_button.clicked.connect(self._reload_login_page)
        self._import_button.clicked.connect(self._accept_if_ready)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

    def _setup_webview(self):
        self._profile = QWebEngineProfile(self)
        self._page = QWebEnginePage(self._profile, self)
        self._view.setPage(self._page)
        self._profile.cookieStore().cookieAdded.connect(self._on_cookie_added)
        self._view.urlChanged.connect(self._on_url_changed)
        self._reload_login_page()

    def _reload_login_page(self):
        if not WEBENGINE_AVAILABLE:
            return
        self._cookies.clear()
        self._profile.cookieStore().deleteAllCookies()
        self._view.setUrl(QUrl(self.LOGIN_URL))
        self._refresh_status("已加载官方登录页，等待扫码或完成登录")

    def _on_url_changed(self, url: QUrl):
        host = url.host() or url.toString()
        self._refresh_status(f"当前页面: {host}")

    def _on_cookie_added(self, cookie: QNetworkCookie):
        name = bytes(cookie.name()).decode("utf-8", errors="ignore")
        value = bytes(cookie.value()).decode("utf-8", errors="ignore")
        domain = cookie.domain().lstrip(".").lower()

        if not name or not value:
            return

        if domain and not any(
            domain.endswith(suffix)
            for suffix in (
                "damai.cn",
                "m.damai.cn",
                "taobao.com",
                "alibaba.com",
            )
        ):
            return

        self._cookies[name] = value
        self._refresh_status()

    def _refresh_status(self, prefix: str = ""):
        parsed = analyze_cookie_text(self.get_cookie_string())
        messages: list[str] = []
        if prefix:
            messages.append(prefix)

        if not WEBENGINE_AVAILABLE:
            messages.append("当前环境无法启用扫码登录")
            self._import_button.setEnabled(False)
        elif not parsed.cookies:
            messages.append("尚未捕获到登录 Cookie")
            self._import_button.setEnabled(False)
        elif parsed.missing_required:
            missing = ", ".join(parsed.missing_required)
            messages.append(f"已识别 {len(parsed.cookies)} 个字段，缺少必填字段: {missing}")
            self._import_button.setEnabled(False)
        else:
            messages.append(f"已识别 {len(parsed.cookies)} 个字段，可以导入登录态")
            if parsed.missing_recommended:
                messages.append("建议补全字段: " + ", ".join(parsed.missing_recommended))
            self._import_button.setEnabled(True)

        self._status_label.setText("\n".join(messages))

    def _accept_if_ready(self):
        parsed = analyze_cookie_text(self.get_cookie_string())
        if parsed.missing_required:
            QMessageBox.warning(
                self,
                "提示",
                "当前登录态仍缺少必填 Cookie，请先在登录页完成登录。",
            )
            return
        self.accept()

    def get_cookie_string(self) -> str:
        return build_cookie_string(self._cookies)
