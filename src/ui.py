import asyncio
import config
import logging
import os
import shutil
import subprocess
import sys
import time
import multiprocessing
import requests
import feedparser
from babel.dates import format_date
from datetime import datetime
from time import mktime
from enum import Enum
from common import inject_variables, get_loop, sanitize_url, GLOBAL_CONTEXT
from util import get_platform, sha256_hash, list_files
from download import DownloadTracker
from quamash import QThreadExecutor
from requests.exceptions import HTTPError, Timeout, ConnectionError
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *


WIDTH = 640
HEIGHT = 480

THREAD_MULTIPLIER = 5


class Branch(object):

    def __init__(self, name, source_branch, cfg):
        self.name = name
        self.source_branch = source_branch
        self.directory = os.path.join(config.BASE_DIR, name)
        self.is_indexed = False
        self.last_fetched = None
        self.config = cfg
        self.files = {}

    def index_directory(self):
        if not os.path.exists(self.directory):
            self.is_indexed = True
            return
        self.files = {relative: sha256_hash(full) for full, relative, in
                      list_files(self.directory)}
        self.is_indexed = True

    def launch_game(self, game_binary, command_args):
        binary_path = os.path.join(self.directory, game_binary)
        if not os.path.isfile(binary_path):
            logging.error("Path to binary does not exist: %s" % binary_path)
            return
        # set to mask for owner permissions and read by group
        os.chmod(binary_path, 0o740)
        args = [binary_path] + list(command_args)
        logging.info('Command: %s' % ' '.join(args))
        subprocess.Popen(args)
        sys.exit()

    def _diff_files(self,
                    context,
                    download_tracker,
                    remote_index,
                    session=None):
        url_format = remote_index['url_format']
        for filename, filedata in remote_index['files'].items():
            filehash = filedata['sha256']
            filesize = filedata['size']
            context.update(filename=filename, filehash=filehash)
            url = inject_variables(url_format, context)

            file_path = os.path.join(self.directory, filename)
            if filename not in self.files:
                logging.info('Missing file: %s (%s)' % (filehash, filename))
            elif self.files[filename] != filehash:
                logging.info('Hash mismatch: %s (%s vs %s)' % (filename,
                             filehash, self.files[filename]))
            else:
                logging.info('Matched File: %s (%s)' % (filehash, filename))
                continue

            download_tracker.add_download(file_path, url, filesize)

    def _preclean_branch_directory(self, download_tracker):
        directories = set(os.path.dirname(download.file_path)
                          for download in download_tracker)
        for directory in directories:
            if not os.path.exists(directory):
                logging.info('Creating new directory: %s' % directory)
                os.makedirs(directory)
        for download in download_tracker:
            path = download.file_path
            if os.path.isdir(path):
                logging.info('Delete conflicting directory: %s' % path)
                shutil.rmtree(path)

    def fetch_remote_index(self, context, download_tracker):
        asyncio.set_event_loop(get_loop())
        branch_context = dict(context)
        branch_context["branch"] = self.source_branch
        url = inject_variables(self.config.index_endpoint, branch_context)
        logging.info('Fetching remote index from %s...' % url)
        response = requests.get(url)

        # TODO(james7132): Do proper error checking
        remote_index = response.json()
        logging.info('Fetched remote index from %s...' % url)
        branch_context['base_url'] = remote_index['base_url']
        with requests.Session() as session:
            logging.info(
                'Comparing local installation against remote index...')
            self._diff_files(branch_context, download_tracker, remote_index,
                             session)
            logging.info(
                'Total download size: %s' % download_tracker.total_size)
            self._preclean_branch_directory(download_tracker)
            download_tracker.run(session=session)
        files = filter(lambda f: f[1] not in remote_index['files'],
                       list_files(self.directory))
        for fullpath, filename in files:
            logging.info('Removing extra file: %s' % filename)
            os.remove(fullpath)


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
    news_row_count = 0

    def __init__(self, cfg):
        super().__init__()
        self.config = cfg
        branches = self.config.branches
        self.branches = {
            name: Branch(name, branch, cfg)
            for branch, name in branches.items()
        }
        self.branch_lookup = {v: k for k, v in self.config.branches.items()}
        self.branch = next(iter(self.config.branches.values()))
        self.context = dict(GLOBAL_CONTEXT)
        self.context.update({
            'project': sanitize_url(self.config.project),
            'branch': 'develop',
        })
        self.client_state = ClientState.LAUNCHER_UPDATE_CHECK
        self.init_ui()

    async def main_loop(self):
        state_mapping = {
            ClientState.LAUNCHER_UPDATE_CHECK: self.launcher_update_check,
            ClientState.GAME_STATUS_CHECK: self.game_status_check,
            ClientState.GAME_UPDATE_CHECK: self.game_update_check,
            ClientState.READY: self.ready
        }
        thread_count = multiprocessing.cpu_count() * THREAD_MULTIPLIER
        with QThreadExecutor(thread_count) as self.executor:
            self.download_tracker.executor = self.executor
            asyncio.ensure_future(self.fetch_news())
            while True:
                if self.client_state in state_mapping:
                    state = self.client_state
                    await state_mapping[self.client_state]()
                else:
                    await asyncio.sleep(0.1)

    async def fetch_news(self):
        logging.info('Fetching news!')
        if not hasattr(self.config, 'news_rss_feed'):
            logging.info('No specified news RSS feed. Aborting fetch.')
            return
        feed_url = self.build_path(self.config.news_rss_feed)
        # TODO(james7132): Do proper error checking
        try:
            rss_response = requests.get(
                feed_url, headers={
                    'User-Agent': 'HouraiLauncher 0.1.0'
                    })
            error_occurred = False
        except HTTPError as http_error:
            logging.error(http_error)
            error_occurred = True
        except Timeout as timeout:
            logging.error(timeout)
            error_occurred = True
        except ConnectionError as connection_error:
            logging.error(connection_error)
            error_occurred = True

        if error_occurred:
            if self.news_row_count < 10:
                self.news_row_count += 1
                self.news_view.addRow(QLabel(
                    "Could not fetch news. Check the log for details."))
            return

        rss_data = feedparser.parse(rss_response.text)
        for entry in rss_data.entries:
            entry_time = datetime.fromtimestamp(mktime(entry.updated_parsed))
            entry_date = entry_time.date()
            label = QLabel()
            label.setOpenExternalLinks(True)
            label.setText('<a href="%s">%s</a>' % (entry.link, entry.title))
            self.news_view.addRow(QLabel(self._get_date(entry_date)), label)
            logging.info('News Item: %s (%s)' %
                         (format_date(entry_date), entry.title))
            self.news_row_count += 1
            if self.news_row_count >= 10:
                break
        logging.info('News fetched!')


    def _get_date(self, entry_date):
      if 'win' in get_platform().lower():
          logging.info(
              'Setting Windows environment variables for translation...')
          try:
              from gettext_windows import get_language_windows
              lang = get_language_windows()
              return format_date(entry_date, lang)
          except:
              logging.warning('Cannot import gettext_windows')
      else:
          return format_date(entry_date)


    def build_path(self, path, context=None):
        if context is None:
            context = self.context
        return inject_variables(path, context)

    async def ready(self):
        self.launch_game_btn.setText(_('Launch Game'))
        self.launch_game_btn.setEnabled(True)
        self.launch_game_btn.show()
        self.progress_bar.hide()
        await asyncio.sleep(0.1)

    async def launcher_update_check(self):
        self.client_state = ClientState.GAME_STATUS_CHECK
        if not hasattr(sys, 'frozen'):
            logging.info('Not build executable')
            return
        if '--test' in sys.argv or not hasattr(self.config,
                                               'launcher_endpoint'):
            return
        launcher_hash = sha256_hash(sys.executable)
        logging.info('Launcher Hash: %s' % launcher_hash)
        url = self.build_path(self.config.launcher_endpoint)
        hash_url = url + '.hash'
        logging.info('Fetching remote hash from: %s' % hash_url)
        # TODO(james7132): Do proper error checking
        try:
            response = await get_loop().run_in_executor(self.executor,
                                                        requests.get,
                                                        hash_url)
            error_occurred = False
        except HTTPError as http_error:
            logging.error(http_error)
            error_occurred = True
        except Timeout as timeout:
            logging.error(timeout)
            error_occurred = True
        except ConnectionError as connection_error:
            logging.error(connection_error)
            error_occurred = True

        if error_occurred:
            if self.news_row_count < 10:
                self.news_row_count += 1
                self.news_view.addRow(QLabel(
                    "Could not check for launcher updates. "
                    "Check the log for details."))
            return

        remote_launcher_hash = response.text
        logging.info('Remote launcher hash: %s' % remote_launcher_hash)
        if remote_launcher_hash == launcher_hash:
            return
        logging.info('Fetching new launcher from: %s' % url)
        temp_file = sys.executable + '.new'
        logging.info('Saving new launcher to: %s' % temp_file)
        old_file = sys.executable + '.old'
        self.download_tracker.clear()
        self.download_tracker.add_download(
            temp_file, url, os.path.getsize(sys.executable))
        self.launch_game_btn.setText(_('Updating Launcher'))
        self.launch_game_btn.show()
        self.progress_bar.show()
        await self.download_tracker.run_async()
        if remote_launcher_hash != sha256_hash(temp_file):
            logging.error('Downloaded launcher does not match one'
                          ' described by remote hash file.')
        self.launch_game_btn.setText(_('Restarting launcher...'))
        if os.path.exists(old_file):
            os.remove(old_file)
        os.rename(sys.executable, old_file)
        logging.info('Renaming old launcher to: %s' % old_file)
        os.rename(temp_file, sys.executable)
        # set to mask for owner permissions and read/execute by group
        os.chmod(sys.executable, 0o750)
        subprocess.Popen([sys.executable])
        sys.exit(0)

    async def game_status_check(self):
        logging.info('Checking local installation...')
        self.launch_game_btn.setText(_('Checking local installation...'))
        self.launch_game_btn.setEnabled(False)
        start = time.time()
        await asyncio.gather(*[
            get_loop().run_in_executor(self.executor, branch.index_directory)
            for branch in self.branches.values()])
        logging.info('Local installation check completed.')
        logging.info('Game status check took %s seconds.' % (time.time() -
                                                             start))
        self.client_state = ClientState.GAME_UPDATE_CHECK

    async def game_update_check(self):
        self.launch_game_btn.hide()
        self.progress_bar.show()
        logging.info('Checking for remote game updates...')
        downloads = [get_loop().run_in_executor(
            self.executor, branch.fetch_remote_index,
            self.context, self.download_tracker)
                     for branch in self.branches.values()]
        try:
            await asyncio.gather(*downloads)
            error_occurred = False
        except HTTPError as http_error:
            logging.error(http_error)
            error_occurred = True
        except Timeout as timeout:
            logging.error(timeout)
            error_occurred = True
        except ConnectionError as connection_error:
            logging.error(connection_error)
            error_occurred = True

        if error_occurred:
            if self.news_row_count < 10:
                self.news_row_count += 1
                self.news_view.addRow(QLabel(
                    "Could not check for game updates. "
                    "Check the log for details."))

        logging.info('Remote game update check completed.')
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

        self.news_view = QFormLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.download_tracker = DownloadTracker(self.progress_bar)

        self.launch_game_btn.clicked.connect(self.launch_game)

        logo = QPixmap(os.path.join(config.RESOURCE_DIR, self.config.logo))
        logo = logo.scaledToWidth(WIDTH)
        logo_label = QLabel()
        logo_label.setPixmap(logo)
        logo_label.setScaledContents(True)

        # Default Layout
        default_layout = QVBoxLayout()
        default_layout.addWidget(logo_label)
        default_layout.addLayout(self.news_view)
        default_layout.addStretch(1)
        default_layout.addWidget(self.branch_box)
        default_layout.addWidget(self.progress_bar)
        default_layout.addWidget(self.launch_game_btn)

        self.setLayout(default_layout)

    def on_branch_change(self, selection):
        self.branch = self.branch_lookup[selection]
        logging.info("Changed to branch: %s" % self.branch)

    def launch_game(self):
        logging.info('Launching game...')
        self.launch_game_btn.setText(_('Launching game...'))
        self.launch_game_btn.setEnabled(False)
        system = get_platform()
        binary = self.config.game_binary.get(system, '')
        args = ()
        if system in self.config.launch_flags:
            args = self.config.launch_flags[system]
        self.branches[self.branch].launch_game(binary, args)
