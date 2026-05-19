import os
import sys

from PySide6 import QtWidgets

from soc_one_dragon.ui.main_window import OctoUI
from soc_one_dragon.ui.styles import APP_STYLESHEET

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def use_app_directory():
    """切换到应用目录，保证配置、素材、截图都使用独立目录内的相对路径。"""
    os.chdir(APP_DIR)
    os.makedirs("img", exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def main():
    use_app_directory()
    log_path = "logs\\log_test.txt"
    with open(log_path, "w") as file:
        file.truncate(0)

    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    ui = OctoUI()
    ui.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
