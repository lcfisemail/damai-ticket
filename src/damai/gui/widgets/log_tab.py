"""实时日志标签页"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QComboBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
import time


_LEVEL_COLORS = {
    "DEBUG": "#888888",
    "INFO": "#333333",
    "SUCCESS": "#52c41a",
    "WARNING": "#fa8c16",
    "ERROR": "#f5222d",
    "CRITICAL": "#a8071a",
}

_LEVEL_ORDER = ["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
_LEVEL_INDEX = {level: i for i, level in enumerate(_LEVEL_ORDER)}


class LogTab(QWidget):
    """实时日志查看标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_level = "DEBUG"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 日志视图（先创建，toolbar 按钮引用它）
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._log_view.setFont(font)
        self._log_view.setStyleSheet("background: #1e1e1e; color: #d4d4d4;")

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("最低级别:"))

        self._level_combo = QComboBox()
        self._level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_combo.currentTextChanged.connect(self._set_level)
        toolbar.addWidget(self._level_combo)

        toolbar.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._log_view.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)
        layout.addWidget(self._log_view)

    def _set_level(self, level: str):
        self._min_level = level

    def append_log(self, level: str, message: str):
        if _LEVEL_INDEX.get(level, 0) < _LEVEL_INDEX.get(self._min_level, 0):
            return

        color = _LEVEL_COLORS.get(level, "#d4d4d4")
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] [{level:<8}] {message}"

        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")

        # 自动滚动到底部
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
