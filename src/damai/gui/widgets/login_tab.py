"""登录标签页。"""
from damai.core.auth import (
    RECOMMENDED_COOKIE_FIELDS,
    REQUIRED_COOKIE_FIELDS,
    analyze_cookie_text,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LoginTab(QWidget):
    """登录标签页。"""

    login_requested = Signal(str, str, str)
    qr_login_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        account_group = QGroupBox("账号")
        account_layout = QVBoxLayout(account_group)

        nick_row = QHBoxLayout()
        nick_row.addWidget(QLabel("账号昵称:"))
        self._nick_input = QLineEdit()
        self._nick_input.setPlaceholderText("例如: 账号1")
        self._nick_input.setText("账号1")
        nick_row.addWidget(self._nick_input)
        account_layout.addLayout(nick_row)
        layout.addWidget(account_group)

        cookie_group = QGroupBox("Cookie 登录")
        cookie_layout = QVBoxLayout(cookie_group)

        hint = QLabel(
            "支持直接粘贴 Cookie 头、完整请求头、curl 命令或 document.cookie 文本。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 12px;")
        cookie_layout.addWidget(hint)

        required_hint = QLabel("必填字段: " + ", ".join(REQUIRED_COOKIE_FIELDS))
        required_hint.setWordWrap(True)
        required_hint.setStyleSheet("color: #b54708; font-size: 12px;")
        cookie_layout.addWidget(required_hint)

        recommended_hint = QLabel("推荐包含: " + ", ".join(RECOMMENDED_COOKIE_FIELDS))
        recommended_hint.setWordWrap(True)
        recommended_hint.setStyleSheet("color: #666; font-size: 12px;")
        cookie_layout.addWidget(recommended_hint)

        cookie_layout.addWidget(QLabel("粘贴文本:"))
        self._cookie_input = QTextEdit()
        self._cookie_input.setPlaceholderText(
            "Cookie: _m_h5_tk=xxx; _m_h5_tk_enc=xxx; ...\n"
            "或粘贴完整 curl / 请求头文本"
        )
        self._cookie_input.setMaximumHeight(120)
        self._cookie_input.textChanged.connect(self._update_cookie_preview)
        cookie_layout.addWidget(self._cookie_input)

        self._cookie_preview = QLabel("尚未识别到 Cookie 字段")
        self._cookie_preview.setWordWrap(True)
        self._cookie_preview.setStyleSheet("color: #666; font-size: 12px;")
        cookie_layout.addWidget(self._cookie_preview)

        btn_row = QHBoxLayout()
        self._cookie_login_btn = QPushButton("提取并登录")
        self._cookie_login_btn.clicked.connect(self._on_cookie_login_clicked)
        self._clear_cookie_btn = QPushButton("清空")
        self._clear_cookie_btn.clicked.connect(self._cookie_input.clear)
        btn_row.addStretch()
        btn_row.addWidget(self._clear_cookie_btn)
        btn_row.addWidget(self._cookie_login_btn)
        cookie_layout.addLayout(btn_row)
        layout.addWidget(cookie_group)

        other_group = QGroupBox("其他登录方式")
        other_layout = QVBoxLayout(other_group)

        qr_hint = QLabel(
            "扫码登录会打开内嵌官方登录页，扫码或输入账号后可直接导入当前登录态。"
        )
        qr_hint.setWordWrap(True)
        qr_hint.setStyleSheet("color: #666; font-size: 12px;")
        other_layout.addWidget(qr_hint)

        other_btn_row = QHBoxLayout()
        self._saved_login_btn = QPushButton("加载已保存 Cookie")
        self._saved_login_btn.clicked.connect(self._on_saved_login_clicked)
        self._qr_login_btn = QPushButton("扫码登录")
        self._qr_login_btn.clicked.connect(self._on_qr_login_clicked)
        other_btn_row.addStretch()
        other_btn_row.addWidget(self._saved_login_btn)
        other_btn_row.addWidget(self._qr_login_btn)
        other_layout.addLayout(other_btn_row)
        layout.addWidget(other_group)

        accounts_group = QGroupBox("已登录账号")
        accounts_layout = QVBoxLayout(accounts_group)

        self._accounts_table = QTableWidget(0, 4)
        self._accounts_table.setHorizontalHeaderLabels(["账号", "大麦昵称 / UID", "状态", "操作"])
        self._accounts_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self._accounts_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        self._accounts_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Fixed,
        )
        self._accounts_table.horizontalHeader().resizeSection(2, 90)
        self._accounts_table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Fixed,
        )
        self._accounts_table.horizontalHeader().resizeSection(3, 80)
        self._accounts_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._accounts_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        accounts_layout.addWidget(self._accounts_table)
        layout.addWidget(accounts_group)
        layout.addStretch()

        self._reset_button_texts()

    def _current_nickname(self) -> str:
        return self._nick_input.text().strip() or "账号1"

    def _set_login_controls_enabled(self, enabled: bool):
        self._nick_input.setEnabled(enabled)
        self._cookie_input.setEnabled(enabled)
        self._cookie_login_btn.setEnabled(enabled)
        self._clear_cookie_btn.setEnabled(enabled)
        self._saved_login_btn.setEnabled(enabled)
        self._qr_login_btn.setEnabled(enabled)

    def _reset_button_texts(self):
        self._cookie_login_btn.setText("提取并登录")
        self._saved_login_btn.setText("加载已保存 Cookie")
        self._qr_login_btn.setText("扫码登录")

    def _update_cookie_preview(self):
        parsed = analyze_cookie_text(self._cookie_input.toPlainText())
        if not parsed.cookies:
            self._cookie_preview.setText("尚未识别到 Cookie 字段")
            return

        keys = ", ".join(list(parsed.cookies.keys())[:8])
        summary = [f"已识别 {len(parsed.cookies)} 个字段"]
        if parsed.missing_required:
            summary.append("缺少必填: " + ", ".join(parsed.missing_required))
        else:
            summary.append("必填字段已齐全")
        summary.append(f"已提取字段示例: {keys}")
        self._cookie_preview.setText("；".join(summary))

    def _on_cookie_login_clicked(self):
        raw_text = self._cookie_input.toPlainText().strip()
        nickname = self._current_nickname()
        if not raw_text:
            QMessageBox.warning(self, "提示", "请先粘贴 Cookie 或请求文本")
            return

        parsed = analyze_cookie_text(raw_text)
        if not parsed.cookies:
            QMessageBox.warning(self, "提示", "未从粘贴内容中提取到 Cookie")
            return
        if parsed.missing_required:
            QMessageBox.warning(
                self,
                "提示",
                "Cookie 缺少必填字段: " + ", ".join(parsed.missing_required),
            )
            return

        self._set_login_controls_enabled(False)
        self._cookie_login_btn.setText("登录中...")
        self.login_requested.emit("cookie", raw_text, nickname)

    def _on_saved_login_clicked(self):
        self._set_login_controls_enabled(False)
        self._saved_login_btn.setText("加载中...")
        self.login_requested.emit("saved_cookie", "", self._current_nickname())

    def _on_qr_login_clicked(self):
        self._set_login_controls_enabled(False)
        self._qr_login_btn.setText("扫码中...")
        self.qr_login_requested.emit(self._current_nickname())

    def reset_login_state(self):
        self._set_login_controls_enabled(True)
        self._reset_button_texts()

    def on_login_result(
        self,
        success: bool,
        nickname: str,
        message: str = "",
        display_name: str = "",
        user_id: str = "",
    ):
        self.reset_login_state()
        if success:
            self._add_account_row(nickname, display_name, user_id, "已登录")
            self._cookie_input.clear()
            profile_lines = []
            if display_name:
                profile_lines.append(f"大麦昵称: {display_name}")
            if user_id:
                profile_lines.append(f"UID: {user_id}")
            profile_text = "\n".join(profile_lines)
            if profile_text:
                profile_text = "\n\n" + profile_text
            QMessageBox.information(self, "成功", f"账号 {nickname} 登录成功！{profile_text}")
        else:
            QMessageBox.critical(self, "登录失败", message)

    def _add_account_row(
        self,
        nickname: str,
        display_name: str,
        user_id: str,
        status: str,
    ):
        profile_parts = []
        if display_name:
            profile_parts.append(display_name)
        if user_id:
            profile_parts.append(f"UID: {user_id}")
        profile_text = " / ".join(profile_parts) or "-"

        for row in range(self._accounts_table.rowCount()):
            if self._accounts_table.item(row, 0).text() == nickname:
                self._accounts_table.item(row, 1).setText(profile_text)
                self._accounts_table.item(row, 2).setText(status)
                return

        row = self._accounts_table.rowCount()
        self._accounts_table.insertRow(row)
        self._accounts_table.setItem(row, 0, QTableWidgetItem(nickname))
        self._accounts_table.setItem(row, 1, QTableWidgetItem(profile_text))
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._accounts_table.setItem(row, 2, status_item)

        remove_btn = QPushButton("移除")
        remove_btn.clicked.connect(lambda: self._on_remove(nickname))
        self._accounts_table.setCellWidget(row, 3, remove_btn)

    def _on_remove(self, nickname: str):
        for row in range(self._accounts_table.rowCount()):
            if self._accounts_table.item(row, 0).text() == nickname:
                self._accounts_table.removeRow(row)
                self.remove_requested.emit(nickname)
                break

    def get_accounts_data(self) -> list:
        accounts = []
        for row in range(self._accounts_table.rowCount()):
            nickname = self._accounts_table.item(row, 0).text()
            accounts.append({"nickname": nickname, "cookie_string": ""})
        return accounts
