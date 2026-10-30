import sys

from PyQt6.QtWidgets import QApplication

from Base.main_window import DiskUsageApp
from Base.theme import apply_dark_theme


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    window = DiskUsageApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
