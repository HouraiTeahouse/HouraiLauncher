import os
import platform
import sys
import subprocess
from config import BASE_DIR, RESOURCE_DIR
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap


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

        self.launch_game_btn = QPushButton('Checking for updates...')
        self.launch_game_btn.setEnabled(False)
        self.branch_box = QComboBox()
        self.branch_lookup = {name : branch for branch, name in
                              self.config.branches.items()}
        for name in self.config.branches.values():
            self.branch_box.addItem(name)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        logo = QPixmap(os.path.join(RESOURCE_DIR, self.config.logo))
        logo = logo.scaledToWidth(WIDTH)
        logo_label = QLabel()
        logo_label.setPixmap(logo)
        logo_label.setScaledContents(True)

        # Default Layout
        default_layout = QVBoxLayout()
        default_layout.addWidget(logo_label)
        default_layout.addStretch(1)
        default_layout.addWidget(self.progress_bar)
        default_layout.addWidget(self.branch_box)
        default_layout.addWidget(self.launch_game_btn)

        self.setLayout(default_layout)

        self.launch_game_btn.clicked.connect(self.launch_game)


    def launch_game(self):
        print('Launching game...')
        self.launch_game_btn.setEnabled(False)
        system = platform.system()
        args = [os.path.join(BASE_DIR, self.config.game_binary[system])]
        if system in self.config.launch_flags:
            args += self.config.launch_flags[system]
        print("Command:", ' '.join(args))
        subprocess.Popen(args)
        sys.exit()

