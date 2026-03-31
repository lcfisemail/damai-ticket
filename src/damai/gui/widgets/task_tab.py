"""任务配置标签页"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QGroupBox, QListWidget,
    QListWidgetItem, QDateTimeEdit, QCheckBox, QTextEdit, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QFont


class TaskTab(QWidget):
    """任务配置标签页"""
    start_requested = Signal(dict)   # 任务配置 dict
    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 演出配置
        event_group = QGroupBox("演出配置")
        event_layout = QVBoxLayout(event_group)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("演出 URL:"))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://detail.damai.cn/item.htm?id=xxx")
        url_row.addWidget(self._url_input)
        event_layout.addLayout(url_row)

        # 场次（多行输入，每行一个）
        event_layout.addWidget(QLabel("目标场次（每行一个，空=任意场次）:"))
        self._sessions_input = QTextEdit()
        self._sessions_input.setPlaceholderText("2025-01-01 上海\n2025-01-02 上海")
        self._sessions_input.setMaximumHeight(70)
        event_layout.addWidget(self._sessions_input)

        # 票档（多行输入，按优先级）
        event_layout.addWidget(QLabel("目标票档（按优先级排序，每行一个，空=任意票档）:"))
        self._tiers_input = QTextEdit()
        self._tiers_input.setPlaceholderText("内场站票\nVIP座票\n普通座票")
        self._tiers_input.setMaximumHeight(70)
        event_layout.addWidget(self._tiers_input)

        # 票数
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("购票数量:"))
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 4)
        self._count_spin.setValue(1)
        count_row.addWidget(self._count_spin)
        count_row.addStretch()
        event_layout.addLayout(count_row)

        layout.addWidget(event_group)

        # 定时配置
        timing_group = QGroupBox("定时配置")
        timing_layout = QVBoxLayout(timing_group)

        self._use_timer = QCheckBox("定时抢票（到达开售时间前自动等待）")
        timing_layout.addWidget(self._use_timer)

        timer_row = QHBoxLayout()
        timer_row.addWidget(QLabel("开售时间:"))
        self._sale_time = QDateTimeEdit()
        self._sale_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._sale_time.setDateTime(QDateTime.currentDateTime())
        self._sale_time.setEnabled(False)
        self._use_timer.toggled.connect(self._sale_time.setEnabled)
        timer_row.addWidget(self._sale_time)
        timer_row.addStretch()
        timing_layout.addLayout(timer_row)

        layout.addWidget(timing_group)

        # 状态显示
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #333; font-size: 13px; padding: 4px;")
        layout.addWidget(self._status_label)

        # 操作按钮
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

        sessions = [
            s.strip()
            for s in self._sessions_input.toPlainText().splitlines()
            if s.strip()
        ]
        tiers = [
            t.strip()
            for t in self._tiers_input.toPlainText().splitlines()
            if t.strip()
        ]

        config = {
            "target": {
                "event_url": url,
                "sessions": sessions,
                "tiers": tiers,
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

    def set_running(self, running: bool):
        self._running = running
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def update_status(self, message: str):
        self._status_label.setText(message)
