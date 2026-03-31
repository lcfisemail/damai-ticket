"""GUI 应用入口"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from damai.gui.main_window import MainWindow


def run_app():
    """启动 GUI 应用"""
    app = QApplication(sys.argv)
    app.setApplicationName("大麦抢票")
    app.setApplicationVersion("0.1.0")

    # 全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 数据目录
    data_dir = Path.home() / ".damai-ticket"
    data_dir.mkdir(parents=True, exist_ok=True)

    window = MainWindow(data_dir=data_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
