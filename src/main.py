import sys
from config import CONFIG
from ui import MainWindow
from PyQt5.QtWidgets import QApplication


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow(CONFIG)
    main_window.show()
    sys.exit(app.exec_())
