import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton

WIDTH = 640
HEIGHT = 480

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.resize(WIDTH, HEIGHT)
        self.setWindowTitle('Hourai Launcher')
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        btn = QPushButton('Launch Game', self)
        btn.clicked.connect(self.launch_game)

    def launch_game(self):
        print ('Launching game...')
        pass

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.center()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
