import os
import platform
import hashlib
import sys
import subprocess
import re
import asyncio
import time
import shutil
import aiohttp
from config import BASE_DIR, RESOURCE_DIR
from enum import Enum
from common import loop
from quamash import QThreadExecutor
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *


WIDTH = 640
HEIGHT = 480

vars_regex = re.compile('{(.*?)}')


def sanitize_url(url):
    return url.lower().replace(' ', '-')


def inject_variables(path_format, vars_obj):
    matches = vars_regex.findall(path_format)
    path = path_format
    for match in matches:
        target = '{%s}' % match
        if isinstance(vars_obj, dict) and match in vars_obj:
            path = path.replace(target, str(vars_obj[match]))
        else:
            replacement = getattr(vars_obj, match, None)
            if replacement is not None:
                path = path.replace(target, str(replacement))
    return path


def sha256_hash(filepath, block_size=65536):
    hash = hashlib.sha256()
    with open(filepath, 'rb') as hash_file:
        buf = hash_file.read(block_size)
        while len(buf) > 0:
            hash.update(buf)
            buf = hash_file.read(block_size)
    return hash.hexdigest()


class Branch(object):

    def __init__(self, name, source_branch, config):
        self.name = name
        self.source_branch = source_branch
        self.directory = os.path.join(BASE_DIR, name)
        self.is_indexed = False
        self.last_fetched = None
        self.config = config
        self.files = {}
        self.remote_index = {}

    def index_directory(self):
        if not os.path.exists(self.directory):
            self.is_indexed = True
            return
        replacement = self.directory + os.path.sep
        tasks = []
        for directory, _, files in os.walk(self.directory):
            for file in files:
                full_path = os.path.join(directory, file)
                relative_path = full_path.replace(replacement, '')
                self.files[relative_path] = sha256_hash(full_path)
        self.is_indexed = True

    def launch_game(self, game_binary, command_args):
        binary_path = os.path.join(self.directory, game_binary)
        print(os.stat(binary_path))
        os.chmod(binary_path, 0o740)
        args = [binary_path] + command_args
        print("Command:", ' '.join(args))
        subprocess.Popen(args)
        sys.exit()

    async def fetch_remote_index(self, context):
        branch_context = dict(context)
        branch_context["branch"] = self.source_branch
        url = inject_variables(self.config.index_endpoint, branch_context)
        print('Remote index URL:', url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                self.remote_index = await response.json()
        file_downloads = {}
        branch_context['base_url'] = self.remote_index['base_url']
        url_format = self.remote_index['url_format']
        download_bytes = 0
        for filename, filedata in self.remote_index['files'].items():
            filehash = filedata['sha256']
            filesize = filedata['size']
            branch_context['filename'] = filename
            branch_context['filehash'] = filehash
            url = inject_variables(url_format, branch_context)

            if filename not in self.files:
                file_downloads[filename] = url
                download_bytes += filesize
                print('Missing file:', filename)
            elif self.files[filename] != filehash:
                file_downloads[filename] = url
                download_bytes += filesize
                print('Hash mismatch:', filename,
                      filehash, self.files[filename])
        print('Total download size:', download_bytes)
        await asyncio.gather(*[self.download_file(filename, url)
                               for filename, url in file_downloads.items()])

    async def download_file(self, filename, url):
        path = os.path.join(self.directory, filename)
        directory = os.path.dirname(path)
        print('Downloading', path, 'from', url, '...')
        if not os.path.exists(directory):
            os.makedirs(directory)
        if os.path.isdir(path):
            shutil.rmtree(path)
        with open(path, 'wb+') as downloaded_file:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    print(response.status)
                    async for block in response.content.iter_chunked(1024):
                        downloaded_file.write(block)


class ClientState(Enum):
    # Game is ready to play and launch
    READY = 0
    # Checking for updates for the base launcher/updater
    LAUNCHER_UPDATE_CHECK = 1
    # Launcher needs to update
    LAUNCHER_UPDATE = 2
    # Checking the status of the local files
    GAME_STATUS_CHECK = 3
    # Checking the status of the local
    GAME_UPDATE_CHECK = 4
    # Game is downloading needed new files for update
    GAME_UPDATE = 5
    # Game update errored out, need to restart patching process
    GAME_UPDATE_ERROR = 6


class MainWindow(QWidget):

    def __init__(self, config):
        super().__init__()
        self.config = config
        branches = self.config.branches
        self.branches = {
            name: Branch(name, branch, config)
            for branch, name in branches.items()
        }
        self.branch_lookup = {v: k for k, v in self.config.branches.items()}
        self.client_state = ClientState.LAUNCHER_UPDATE_CHECK
        self.branch = next(iter(self.config.branches.values()))
        self.context = {
            'platform': platform.system()
        }
        self.state_mapping = {
            ClientState.LAUNCHER_UPDATE_CHECK: self.launcher_update_check,
            ClientState.GAME_STATUS_CHECK: self.game_status_check,
            ClientState.GAME_UPDATE_CHECK: self.game_update_check,
            ClientState.READY: self.ready
        }
        self.init_ui()

    async def main_loop(self):
        with QThreadExecutor(1) as exec:
            while True:
                if self.client_state in self.state_mapping:
                    await self.state_mapping[self.client_state]()
                else:
                    await asyncio.sleep(0.1)

    async def ready(self):
        self.launch_game_btn.setText('Launch Game')
        self.launch_game_btn.setEnabled(True)
        self.launch_game_btn.show()
        self.progress_bar.hide()
        await asyncio.sleep(0.1)

    async def launcher_update_check(self):
        # TODO(james7132): Properly set this up
        self.client_state = ClientState.GAME_STATUS_CHECK

    async def game_status_check(self):
        self.launch_game_btn.setText('Checking local installation...')
        self.launch_game_btn.setEnabled(False)
        start = time.time()
        with QThreadExecutor(1) as exec:
            await asyncio.gather(*[
                loop.run_in_executor(exec, lambda: branch.index_directory())
                for branch in self.branches.values()])
        print('Game status check took', time.time() - start, 'seconds')
        self.client_state = ClientState.GAME_UPDATE_CHECK

    async def game_update_check(self):
        self.launch_game_btn.hide()
        self.progress_bar.show()
        context = {
            'project': sanitize_url(self.config.project),
            'branch': 'develop',
            'platform': platform.system()
        }
        await asyncio.gather(*[branch.fetch_remote_index(context)
                               for branch in self.branches.values()])
        self.client_state = ClientState.READY

    def init_ui(self):
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowTitle(self.config.project)

        self.launch_game_btn = QPushButton('Checking for updates...')
        self.launch_game_btn.setEnabled(False)

        self.branch_box = QComboBox()
        self.branch_box.activated[str].connect(self.on_branch_change)
        self.branch_box.addItems(self.config.branches.values())
        if len(self.config.branches) <= 1:
            self.branch_box.hide()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar.setMaximum(1000)
        self.progress_bar.hide()

        self.launch_game_btn.clicked.connect(self.launch_game)

        logo = QPixmap(os.path.join(RESOURCE_DIR, self.config.logo))
        logo = logo.scaledToWidth(WIDTH)
        logo_label = QLabel()
        logo_label.setPixmap(logo)
        logo_label.setScaledContents(True)

        # Default Layout
        default_layout = QVBoxLayout()
        default_layout.addWidget(logo_label)
        default_layout.addStretch(1)
        default_layout.addWidget(self.branch_box)
        default_layout.addWidget(self.launch_game_btn)
        default_layout.addWidget(self.progress_bar)

        self.setLayout(default_layout)

    def on_branch_change(self, selection):
        self.branch = self.branch_lookup[selection]
        print(self.branch)

    def launch_game(self):
        print('Launching game...')
        self.launch_game_btn.setEnabled(False)
        system = platform.system()
        binary = self.config.game_binary[system]
        if system in self.config.launch_flags:
            args = self.config.launch_flags[system]
        else:
            args = []
        self.branches[self.branch].launch_game(binary, args)
