import aiohttp
import asyncio
import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from config import BASE_DIR, RESOURCE_DIR
from enum import Enum
from common import inject_variables, loop, sanitize_url, GLOBAL_CONTEXT
from quamash import QThreadExecutor
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *


WIDTH = 640
HEIGHT = 480

CHUNK_SIZE = 1024 * 1024


def sha256_hash(filepath, block_size=CHUNK_SIZE):
    hash = hashlib.sha256()
    with open(filepath, 'rb') as hash_file:
        buf = hash_file.read(block_size)
        while len(buf) > 0:
            hash.update(buf)
            buf = hash_file.read(block_size)
    return hash.hexdigest()


def list_files(directory):
    replacement = directory + os.path.sep
    for directory, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(directory, file)
            relative_path = full_path.replace(replacement,
                                              '').replace(os.path.sep, '/')
            yield full_path, relative_path


class Download(object):

    def __init__(self, path, url, download_size):
        self.url = url
        self.file_path = path
        self.total_size = download_size
        self.downloaded_bytes = 0

    async def download_file(self, session, tracker=None):
        path = self.file_path
        directory = os.path.dirname(path)
        logging.info('Downloading %s from %s...' % (path, self.url))
        if not os.path.exists(directory):
            os.makedirs(directory)
        if os.path.isdir(path):
            shutil.rmtree(path)
        with open(path, 'wb+') as downloaded_file:
            async with session.get(self.url) as response:
                logging.info(response.status)
                async for block in response.content.iter_chunked(
                        CHUNK_SIZE):
                    self.downloaded_bytes += len(block)
                    if tracker is not None:
                        loop.call_soon_threadsafe(tracker.update)
                    downloaded_file.write(block)


class DownloadTracker(object):

    def __init__(self, progress_bar):
        self.downloads = []
        self.progress_bar = progress_bar

    def update(self):
        if self.progress_bar is None:
            return
        total_download_size = sum(download.total_size for download in
                                  self.downloads)
        total_downloaded_bytes = sum(download.downloaded_bytes for download in
                                     self.downloads)
        if total_download_size <= 0:
            return
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_download_size)
        self.progress_bar.setValue(total_downloaded_bytes)


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
        self.files = {relative: sha256_hash(full) for full, relative, in
                      list_files(self.directory)}
        self.is_indexed = True

    def launch_game(self, game_binary, command_args):
        binary_path = os.path.join(self.directory, game_binary)
        os.chmod(binary_path, 0o740)
        args = [binary_path] + command_args
        logging.info("Command:", ' '.join(args))
        subprocess.Popen(args)
        sys.exit()

    async def fetch_remote_index(self, context, progress_bar):
        branch_context = dict(context)
        branch_context["branch"] = self.source_branch
        url = inject_variables(self.config.index_endpoint, branch_context)
        logging.info('Remote index URL: %s' % url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                self.remote_index = await response.json()
        file_downloads = {}
        branch_context['base_url'] = self.remote_index['base_url']
        url_format = self.remote_index['url_format']
        download_bytes = 0
        download_tracker = DownloadTracker(progress_bar)
        for filename, filedata in self.remote_index['files'].items():
            filehash = filedata['sha256']
            filesize = filedata['size']
            branch_context['filename'] = filename
            branch_context['filehash'] = filehash
            url = inject_variables(url_format, branch_context)

            file_path = os.path.join(self.directory, filename)
            download = None
            if filename not in self.files:
                download = Download(file_path, url, filesize)
                logging.info('Missing file:', filename)
            elif self.files[filename] != filehash:
                download = Download(file_path, url, filesize)
                logging.info('Hash mismatch:', filename,
                             filehash, self.files[filename])
            if download is not None:
                download_tracker.downloads.append(download)
        logging.info('Total download size: %s' % download_bytes)
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[download.download_file(session,
                                                          download_tracker)
                                   for download in download_tracker.downloads])
        files = filter(lambda f: f[1] not in self.remote_index['files'],
                       list_files(self.directory))
        for _, filename in files:
            logging.info('Extra file', filename)


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
        self.context = dict(GLOBAL_CONTEXT)
        print(self.context)
        self.state_mapping = {
            ClientState.LAUNCHER_UPDATE_CHECK: self.launcher_update_check,
            ClientState.GAME_STATUS_CHECK: self.game_status_check,
            ClientState.GAME_UPDATE_CHECK: self.game_update_check,
            ClientState.READY: self.ready
        }
        self.init_ui()

    async def main_loop(self):
        while True:
            if self.client_state in self.state_mapping:
                await self.state_mapping[self.client_state]()
            else:
                await asyncio.sleep(0.1)

    async def ready(self):
        self.launch_game_btn.setText(_('Launch Game'))
        self.launch_game_btn.setEnabled(True)
        self.launch_game_btn.show()
        self.progress_bar.hide()
        await asyncio.sleep(0.1)

    async def launcher_update_check(self):
        # TODO(james7132): Properly set this up
        self.client_state = ClientState.GAME_STATUS_CHECK
        if not hasattr(sys, 'frozen'):
            logging.info('Not build executable')
            return
        launcher_hash = sha256_hash(sys.executable)
        logging.info('Launcher Hash: %s' % launcher_hash)
        print(self.config)
        url = inject_variables(self.config.launcher_endpoint, self.context)
        hash_url = url + '.hash'
        logging.info('Fetching remote hash from: %s' % hash_url)
        async with aiohttp.ClientSession() as session:
            async with session.get(hash_url) as response:
                remote_launcher_hash = await response.content
            if remote_launcher_hash != launcher_hash:
                logging.info('Fetching new launcher from: %s' % url)

    async def game_status_check(self):
        self.launch_game_btn.setText(_('Checking local installation...'))
        self.launch_game_btn.setEnabled(False)
        start = time.time()
        with QThreadExecutor(len(self.branches)) as exec:
            await asyncio.gather(*[
                loop.run_in_executor(exec, lambda: branch.index_directory())
                for branch in self.branches.values()])
        logging.info('Game status check took %s seconds.' % (time.time() -
                     start))
        self.client_state = ClientState.GAME_UPDATE_CHECK

    async def game_update_check(self):
        self.launch_game_btn.hide()
        self.progress_bar.show()
        context = {
            'project': sanitize_url(self.config.project),
            'branch': 'develop',
            'platform': platform.system()
        }
        await asyncio.gather(*[branch.fetch_remote_index(context,
                                                         self.progress_bar)
                               for branch in self.branches.values()])
        self.client_state = ClientState.READY

    def init_ui(self):
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowTitle(self.config.project)

        self.launch_game_btn = QPushButton(_('Checking for updates...'))
        self.launch_game_btn.setEnabled(False)

        self.branch_box = QComboBox()
        self.branch_box.activated[str].connect(self.on_branch_change)
        self.branch_box.addItems(self.config.branches.values())
        if len(self.config.branches) <= 1:
            self.branch_box.hide()

        self.progress_bar = QProgressBar()
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
        logging.info("Changed to branch: %s" % self.branch)

    def launch_game(self):
        logging.info('Launching game...')
        self.launch_game_btn.setEnabled(False)
        system = platform.system()
        binary = self.config.game_binary[system]
        if system in self.config.launch_flags:
            args = self.config.launch_flags[system]
        else:
            args = []
        self.branches[self.branch].launch_game(binary, args)
