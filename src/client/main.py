import os
import sys
import json
import subprocess
import platform
from collections import OrderedDict
from common.util import namedtuple_from_mapping
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton

WIDTH = 640
HEIGHT = 480

CONFIG_FILE = 'config.json'

# Get the base directory the executable is found in
# When running from a python interpretter, it will use the current working
# directory.
# sys.frozen is an attribute injected by pyinstaller at runtime
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.getcwd()

if getattr(sys, '_MEIPASS', False):
    RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
else:
    RESOURCE_DIR = os.getcwd()

# Load Config
with open(os.path.join(RESOURCE_DIR, CONFIG_FILE)) as config_file:
    # Using OrderedDict to preserve JSON ordering of dictionaries
    CONFIG = namedtuple_from_mapping(
        json.load(config_file, object_pairs_hook=OrderedDict))


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
        subprocess.call(args)


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow(CONFIG)
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
