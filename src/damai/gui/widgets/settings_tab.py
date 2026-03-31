"""设置标签页"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QCheckBox, QSpinBox, QTextEdit,
    QMessageBox, QDoubleSpinBox,
)
from PySide6.QtCore import Signal
from pathlib import Path


class SettingsTab(QWidget):
    """设置标签页 — 通知、代理、轮询参数"""
    settings_saved = Signal(dict)

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 通知配置
        notify_group = QGroupBox("通知推送")
        notify_layout = QVBoxLayout(notify_group)

        # 企业微信
        wechat_row = QHBoxLayout()
        self._wechat_enabled = QCheckBox("企业微信")
        self._wechat_url = QLineEdit()
        self._wechat_url.setPlaceholderText("Webhook URL")
        wechat_row.addWidget(self._wechat_enabled)
        wechat_row.addWidget(self._wechat_url)
        notify_layout.addLayout(wechat_row)

        # 钉钉
        dd_row = QHBoxLayout()
        self._dd_enabled = QCheckBox("钉钉机器人")
        self._dd_url = QLineEdit()
        self._dd_url.setPlaceholderText("Webhook URL")
        self._dd_secret = QLineEdit()
        self._dd_secret.setPlaceholderText("加签密钥（可选）")
        dd_row.addWidget(self._dd_enabled)
        dd_row.addWidget(self._dd_url)
        dd_row.addWidget(self._dd_secret)
        notify_layout.addLayout(dd_row)

        layout.addWidget(notify_group)

        # 代理配置
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QVBoxLayout(proxy_group)

        self._proxy_enabled = QCheckBox("启用代理")
        proxy_layout.addWidget(self._proxy_enabled)

        proxy_layout.addWidget(
            QLabel("代理列表（每行一个，格式: http://ip:port 或 socks5://ip:port）:")
        )
        self._proxy_list = QTextEdit()
        self._proxy_list.setMaximumHeight(100)
        self._proxy_list.setPlaceholderText(
            "http://127.0.0.1:7890\nsocks5://127.0.0.1:1080"
        )
        proxy_layout.addWidget(self._proxy_list)

        layout.addWidget(proxy_group)

        # 轮询参数
        poll_group = QGroupBox("轮询参数")
        poll_layout = QHBoxLayout(poll_group)

        poll_layout.addWidget(QLabel("间隔最小(s):"))
        self._poll_min = QDoubleSpinBox()
        self._poll_min.setRange(0.1, 10.0)
        self._poll_min.setSingleStep(0.1)
        self._poll_min.setValue(0.5)
        poll_layout.addWidget(self._poll_min)

        poll_layout.addWidget(QLabel("间隔最大(s):"))
        self._poll_max = QDoubleSpinBox()
        self._poll_max.setRange(0.1, 30.0)
        self._poll_max.setSingleStep(0.1)
        self._poll_max.setValue(2.0)
        poll_layout.addWidget(self._poll_max)

        poll_layout.addWidget(QLabel("最大重试次数:"))
        self._max_retries = QSpinBox()
        self._max_retries.setRange(1, 50)
        self._max_retries.setValue(10)
        poll_layout.addWidget(self._max_retries)

        poll_layout.addStretch()
        layout.addWidget(poll_group)

        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _save(self):
        from damai.utils.config import save_config
        proxies = [
            p.strip()
            for p in self._proxy_list.toPlainText().splitlines()
            if p.strip()
        ]
        config = {
            "timing": {
                "poll_interval_min": self._poll_min.value(),
                "poll_interval_max": self._poll_max.value(),
                "order_retry_max": self._max_retries.value(),
            },
            "proxy": {
                "enabled": self._proxy_enabled.isChecked(),
                "proxies": proxies,
            },
            "notification": {
                "wechat": {
                    "enabled": self._wechat_enabled.isChecked(),
                    "webhook_url": self._wechat_url.text().strip(),
                },
                "dingtalk": {
                    "enabled": self._dd_enabled.isChecked(),
                    "webhook_url": self._dd_url.text().strip(),
                    "secret": self._dd_secret.text().strip(),
                },
            },
        }
        try:
            save_config(config, self._config_path)
            QMessageBox.information(self, "成功", "设置已保存")
            self.settings_saved.emit(config)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def get_settings(self) -> dict:
        proxies = [
            p.strip()
            for p in self._proxy_list.toPlainText().splitlines()
            if p.strip()
        ]
        return {
            "timing": {
                "poll_interval_min": self._poll_min.value(),
                "poll_interval_max": self._poll_max.value(),
                "order_retry_max": self._max_retries.value(),
            },
            "proxy": {
                "enabled": self._proxy_enabled.isChecked(),
                "proxies": proxies,
            },
        }
