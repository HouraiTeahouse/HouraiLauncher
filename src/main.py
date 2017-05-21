import os
import sys
import subprocess
import platform
from config import BASE_DIR, RESOURCE_DIR, CONFIG
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton

WIDTH = 640
HEIGHT = 480


class MainWindow(QWidget):

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowTitle(self.config.project)
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.launch_game_btn = QPushButton('Launch Game', self)
        self.launch_game_btn.clicked.connect(self.launch_game)
        for branch, name in self.config.branches.items():
            print(branch, name)

    def launch_game(self):
        print('Launching game...')
        self.launch_game_btn.setEnabled(False)
        system = platform.system()
        args = [os.path.join(BASE_DIR, self.config.game_binary[system])]
        if system in self.config.launch_flags:
            args += self.config.launch_flags[system]
        print ("Command:", ' '.join(args))
        subprocess.Popen(args)
        sys.exit()


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow(CONFIG)
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
