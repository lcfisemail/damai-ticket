"""任务配置标签页。"""
from __future__ import annotations

import time

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class TaskTab(QWidget):
    """任务配置标签页。"""

    start_requested = Signal(dict)
    stop_requested = Signal()
    detail_load_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        event_group = QGroupBox("演出信息")
        event_layout = QVBoxLayout(event_group)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("演出 URL:"))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://detail.damai.cn/item.htm?id=xxx")
        url_row.addWidget(self._url_input)

        self._load_btn = QPushButton("加载数据")
        self._load_btn.setFixedWidth(100)
        self._load_btn.clicked.connect(self._on_load_detail)
        url_row.addWidget(self._load_btn)
        event_layout.addLayout(url_row)

        self._event_info = QLabel("未加载演出信息")
        self._event_info.setWordWrap(True)
        self._event_info.setStyleSheet(
            "background: #fafafa; border: 1px solid #f0f0f0; padding: 8px;"
        )
        event_layout.addWidget(self._event_info)

        event_layout.addWidget(QLabel("场次筛选（可多选，不勾选则默认全部场次）:"))
        self._sessions_list = QListWidget()
        self._sessions_list.setMaximumHeight(110)
        event_layout.addWidget(self._sessions_list)

        event_layout.addWidget(QLabel("票档筛选（可多选，不勾选则默认全部票档）:"))
        self._tiers_list = QListWidget()
        self._tiers_list.setMaximumHeight(130)
        event_layout.addWidget(self._tiers_list)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("购票数量:"))
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 4)
        self._count_spin.setValue(1)
        count_row.addWidget(self._count_spin)
        count_row.addStretch()
        event_layout.addLayout(count_row)

        layout.addWidget(event_group)

        timing_group = QGroupBox("定时设置")
        timing_layout = QVBoxLayout(timing_group)

        self._use_timer = QCheckBox("定时抢票（在开票时间前自动等待）")
        timing_layout.addWidget(self._use_timer)

        timer_row = QHBoxLayout()
        timer_row.addWidget(QLabel("开抢时间:"))
        self._sale_time = QDateTimeEdit()
        self._sale_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._sale_time.setDateTime(QDateTime.currentDateTime())
        self._sale_time.setEnabled(False)
        self._use_timer.toggled.connect(self._sale_time.setEnabled)
        timer_row.addWidget(self._sale_time)
        timer_row.addStretch()
        timing_layout.addLayout(timer_row)

        layout.addWidget(timing_group)

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #333; font-size: 13px; padding: 4px;")
        layout.addWidget(self._status_label)

        task_log_group = QGroupBox("任务日志")
        task_log_layout = QVBoxLayout(task_log_group)
        self._task_log = QPlainTextEdit()
        self._task_log.setReadOnly(True)
        self._task_log.setMaximumBlockCount(800)
        self._task_log.setMinimumHeight(180)
        self._task_log.setStyleSheet("background: #1f1f1f; color: #d9d9d9;")
        task_log_layout.addWidget(self._task_log)
        layout.addWidget(task_log_group)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("开始抢票")
        self._start_btn.setFixedHeight(36)
        self._start_btn.setStyleSheet(
            "QPushButton { background: #1890ff; color: white; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background: #40a9ff; }"
            "QPushButton:disabled { background: #ccc; }"
        )
        self._start_btn.clicked.connect(self._on_start)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setFixedHeight(36)
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { background: #ff4d4f; color: white; font-size: 14px; border-radius: 4px; }"
            "QPushButton:disabled { background: #ccc; }"
        )
        self._stop_btn.clicked.connect(self._on_stop)

        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _on_start(self):
        url = self._url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入演出 URL")
            return

        config = {
            "target": {
                "event_url": url,
                "sessions": self._collect_checked_values(self._sessions_list),
                "tiers": self._collect_checked_values(self._tiers_list),
                "ticket_count": self._count_spin.value(),
                "buyers": [],
            },
            "timing": {
                "poll_interval_min": 0.5,
                "poll_interval_max": 2.0,
                "sale_start_time": (
                    self._sale_time.dateTime().toString("yyyy-MM-ddTHH:mm:ss+08:00")
                    if self._use_timer.isChecked()
                    else ""
                ),
                "order_retry_max": 10,
            },
        }

        self.start_requested.emit(config)

    def _on_stop(self):
        self.stop_requested.emit()

    def _on_load_detail(self):
        url = self._url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请先输入演出 URL")
            return
        self.detail_load_requested.emit(url)

    @staticmethod
    def _collect_checked_values(widget: QListWidget) -> list[str]:
        values: list[str] = []
        for index in range(widget.count()):
            item = widget.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                values.append(item.data(Qt.ItemDataRole.UserRole) or item.text())
        return values

    def _populate_check_list(
        self,
        widget: QListWidget,
        items: list[dict],
        default_checked: bool = False,
    ):
        widget.clear()
        for entry in items:
            text = entry.get("label") or entry.get("name") or "未命名"
            value = entry.get("name") or text
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if default_checked else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, value)
            widget.addItem(item)

    def set_event_detail(self, detail: dict):
        title = detail.get("title", "")
        status = detail.get("status", "") or "未知"
        venue = detail.get("venue", "") or "未知"
        city = detail.get("city", "") or "未知"
        item_id = detail.get("item_id", "")
        session_count = detail.get("session_count", 0)
        tier_count = detail.get("tier_count", 0)

        self._event_info.setText(
            f"演出：{title}\n"
            f"状态：{status}\n"
            f"城市：{city}\n"
            f"场馆：{venue}\n"
            f"项目 ID：{item_id}\n"
            f"场次数：{session_count} | 票档数：{tier_count}"
        )
        self._populate_check_list(self._sessions_list, detail.get("sessions", []))
        self._populate_check_list(self._tiers_list, detail.get("tiers", []))

    def set_loading(self, loading: bool):
        self._load_btn.setEnabled(not loading)

    def append_log(self, level: str, message: str):
        ts = time.strftime("%H:%M:%S")
        self._task_log.appendPlainText(f"[{ts}] [{level}] {message}")

    def clear_logs(self):
        self._task_log.clear()

    def set_running(self, running: bool):
        self._running = running
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def update_status(self, message: str):
        self._status_label.setText(message)
