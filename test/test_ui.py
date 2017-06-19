import asyncio
import config
import common
import download
import ui
import os
import shutil
import subprocess
import sys
import time
from concurrent import futures
from common import GLOBAL_CONTEXT
from test_download import SessionMock, ResponseMock
from async_unittest import AsyncTestCase, async_patch, TestCase, mock, main
from PyQt5 import QtWidgets
from util import namedtuple_from_mapping, get_platform, tupperware


test_rss_data = tupperware(dict(
    # make 13 entries so we can test that only 10 are used
    entries=[
        tupperware(dict(
            updated_parsed=time.gmtime(),
            link='some_link',
            title='some_title'
            ))
        ]*13
    ))

config.setup_directories()
testing_config = namedtuple_from_mapping(
    dict(
        project="Fantasy Crescendo",
        logo="img/logo.png",
        config_endpoint=("https://patch.houraiteahouse.net/fantasy-crescendo/"
                         "launcher/config.json"),
        launcher_endpoint=(
            "https://patch.houraiteahouse.net/fantasy-crescendo/launcher/"
            "{platform}/{executable}"),
        index_endpoint=("https://patch.houraiteahouse.net/fantasy-crescendo/"
                        "{branch}/{platform}/index.json"),
        news_rss_feed="https://www.reddit.com/r/touhou.rss",
        game_binary=dict(Windows="fc.exe", Linux="fc.x86_64"),
        launch_flags=dict(Windows=["-bill", "-gates"],
                          Linux=["-linus", "-torvalds"]),
        branches=dict(develop="Development"),
        )
    )

testing_index_files = dict(
    test_file1=dict(
        sha256="one hash",
        size=0xdeadbeef
        ),
    test_file2=dict(
        sha256="two hash",
        size=0xbadf00d
        ),
    test_file3=dict(
        sha256="red AND blue hash",
        size=0xc001d00d
        )
    )

testing_index = dict(
    files=testing_index_files,
    base_url="https://patch.houraiteahouse.net",
    project="fantasy-crescendo",
    branch="develop",
    platform="Windows",
    url_format="{base_url}/{project}/{branch}/{platform}/{filename}_{filehash}"
    )


def fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen):
    try:
        del sys.argv
    except AttributeError:
        pass
    try:
        del sys.frozen
    except AttributeError:
        pass
    if has_argv:
        sys.argv = argv
    if has_frozen:
        sys.frozen = frozen


def should_not_be_run(*args, **kwargs):
    raise Exception("The line of code this patches should have not been run.")


class DownloadMock(object):
    status_code = None

    def __init__(self, path, url, download_size):
        self.url = url
        self.file_path = path
        self.total_size = download_size
        self.downloaded_bytes = 0

    def download_file(self, session=None, filehash=None):
        return self.status_code


class DownloadTrackerMock(object):
    downloads = None
    downloads_mock_info = None
    run_called_with = ()
    total_size = 0

    def __init__(self):
        self.downloads = []
        self.downloads_mock_info = {}
        self.run_called_with = []

    def add_download(self, filepath, url, filesize):
        self.downloads_mock_info[filepath] = filesize
        self.downloads.append(DownloadMock(filepath, url, filesize))

    def run(self, session=None):
        self.run_called_with.append(session)

    def __iter__(self):
        return self.downloads.__iter__()


class StopLoopException(Exception):
    pass


class BranchTest(AsyncTestCase):
    branch = None

    def setUp(self):
        self.branch = ui.Branch("Development", "develop", testing_config)

    def test_branch_can_create_branch(self):
        branch = self.branch
        self.assertEqual(branch.name, "Development")
        self.assertEqual(branch.source_branch, "develop")
        self.assertEqual(branch.directory,
                         os.path.join(config.BASE_DIR, "Development"))
        self.assertFalse(branch.is_indexed)
        self.assertIs(branch.last_fetched, None)
        self.assertIs(branch.config, testing_config)
        self.assertIsInstance(branch.files, dict)
        self.assertEqual(branch.files, {})

    def test_branch_can_index_directory(self):
        branch = self.branch
        test_paths = (("full_1", "rel_1"), ("full_2", "rel_2"))
        with mock.patch('os.path.exists', lambda dir: True) as m1,\
                mock.patch('ui.list_files', lambda dir: test_paths) as m2,\
                mock.patch('ui.sha256_hash', lambda p: "HASH%s" % p) as m3:
            branch.index_directory()

        files = branch.files
        self.assertIn("rel_1", files)
        self.assertIn("rel_2", files)

    def test_branch_cannot_index_nonexistant_directory(self):
        branch = self.branch
        old_files = branch.files
        test_paths = (("full_1", "rel_1"), ("full_2", "rel_2"))
        with mock.patch('os.path.exists', lambda dir: False) as m1,\
                mock.patch('ui.list_files', lambda dir: test_paths) as m2:
            branch.index_directory()

        self.assertTrue(branch.is_indexed)
        self.assertIs(old_files, branch.files)

    def test_branch_can_detect_diff_files(self):
        download_tracker = DownloadTrackerMock()
        downloads = download_tracker.downloads_mock_info
        branch = self.branch
        old_files = branch.files
        branch_context = dict(
            common.GLOBAL_CONTEXT,
            project='fantasy-crescendo', branch='develop',
            base_url=testing_index['base_url']
            )

        # add two files, one with a good hash and one with a mismatched
        # hash so we can test that one isnt downloaded and the other is
        branch.files.update(test_file1="one hash", test_file2="bad hash")

        with mock.patch('os.path.join', lambda *args: args[-1]) as m:
            branch._diff_files(branch_context, download_tracker, testing_index)

        self.assertEqual(len(downloads), 2)
        self.assertIn("test_file2", downloads)
        self.assertIn("test_file3", downloads)
        self.assertEqual(downloads["test_file2"], 0xbadf00d)
        self.assertEqual(downloads["test_file3"], 0xc001d00d)

    def test_branch_can_preclean_branch_directory(self):
        branch = self.branch
        download_tracker = DownloadTrackerMock()
        downloads = download_tracker.downloads

        download_tracker.add_download("root\\test1.bin", "", 0)
        download_tracker.add_download("root\\test", "", 0)
        download_tracker.add_download("root\\test\\test2.bin", "", 0)
        download_tracker.add_download("root\\test\\test3.bin", "", 0)
        download_tracker.add_download("root\\test\\asdf\\test4.bin", "", 0)

        existing_dirs = set(["root"])
        existing_files = set(["root\\test"])

        def os_path_exists_mock(path):
            path = path.replace('/', '\\')
            if path in existing_dirs or path in existing_files:
                return True
            return False

        def os_path_isdir_mock(path):
            return path.replace('/', '\\') in existing_dirs

        def os_makedirs_mock(root_dir):
            dirs = root_dir.replace('/', '\\').split('\\')
            for i in range(len(dirs)):
                existing_dirs.add(
                    os.path.join(*dirs[: i + 1]).replace('/', '\\'))

        def shutil_rmtree_mock(path):
            existing_files.remove(path.replace('/', '\\'))

        def os_path_dirname_mock(path):
            dirname = ""
            path = path.replace('/', '\\')
            for dir in path.split('\\')[: -1]:
                dirname += "%s\\" % dir
            return dirname[: -1]

        with mock.patch('os.path.exists', os_path_exists_mock) as m1,\
                mock.patch('os.path.isdir', os_path_isdir_mock) as m2,\
                mock.patch('os.path.dirname', os_path_dirname_mock) as m3,\
                mock.patch('os.makedirs', os_makedirs_mock) as m4,\
                mock.patch('shutil.rmtree', shutil_rmtree_mock) as m5:
            branch._preclean_branch_directory(download_tracker)

        self.assertNotIn("root\\test", existing_files)
        self.assertIn("root", existing_dirs)
        self.assertIn("root\\test", existing_dirs)
        self.assertIn("root\\test\\asdf", existing_dirs)

    def test_branch_can_launch_game(self):
        branch = self.branch
        mock_data = dict(
            sys_exit_called=False,
            os_chmod_args=('', 0),
            subprocess_Popen_args=('',)
            )

        game_binary = "fc.exe"
        binary_path = os.path.join(branch.directory, game_binary)
        command_args = ["-have", "-some", "-arguments"]

        def sys_exit_mock():
            mock_data['sys_exit_called'] = True

        def os_chmod_mock(binary_path, new_mode):
            mock_data['os_chmod_args'] = (binary_path, new_mode)

        def subprocess_Popen_mock(args):
            mock_data['subprocess_Popen_args'] = args

        with mock.patch('subprocess.Popen', subprocess_Popen_mock) as m1,\
                mock.patch('os.chmod', os_chmod_mock) as m2,\
                mock.patch('os.path.isfile', lambda dir: True) as m3,\
                mock.patch('sys.exit', sys_exit_mock) as m4:
            branch.launch_game(game_binary, command_args)

        self.assertEqual(mock_data['os_chmod_args'][0], binary_path)
        self.assertEqual(mock_data['os_chmod_args'][1], 0o740)
        self.assertEqual(mock_data['subprocess_Popen_args'][0], binary_path)
        self.assertEqual(mock_data['subprocess_Popen_args'][1:], command_args)
        self.assertTrue(mock_data['sys_exit_called'])

    def test_branch_cannot_launch_nonexistant_binary(self):
        branch = self.branch
        mock_data = dict(
            sys_exit_called=False,
            os_chmod_args=('', 0),
            subprocess_Popen_args=('',)
            )

        def sys_exit_mock():
            mock_data['sys_exit_called'] = True

        def os_chmod_mock(binary_path, new_mode):
            mock_data['os_chmod_args'] = (binary_path, new_mode)

        def subprocess_Popen_mock(args):
            mock_data['subprocess_Popen_args'] = args

        with mock.patch('subprocess.Popen', subprocess_Popen_mock) as m1,\
                mock.patch('os.chmod', os_chmod_mock) as m2,\
                mock.patch('os.path.isfile', lambda dir: False) as m3,\
                mock.patch('sys.exit', sys_exit_mock) as m4:
            branch.launch_game('qwerty', ('-fake', '-args'))

        self.assertEqual(mock_data['os_chmod_args'][0], '')
        self.assertEqual(mock_data['os_chmod_args'][1], 0)
        self.assertEqual(mock_data['subprocess_Popen_args'][0], '')
        self.assertEqual(mock_data['subprocess_Popen_args'][1:], ())
        self.assertFalse(mock_data['sys_exit_called'])

    def test_branch_fetch_remote_index_can_succeed(self):
        branch = self.branch
        download_tracker = DownloadTrackerMock()

        index_session = ResponseMock(b'')
        index_session._json = testing_index
        session = SessionMock()
        existing_files = [('root\\extra_file1', 'extra_file1'),
                          ('root\\asdf\\extra_file1', 'asdf\\extra_file2')]

        with mock.patch('ui.get_loop', return_value=self.loop) as m1,\
                mock.patch('ui.Branch._preclean_branch_directory') as m2,\
                mock.patch('requests.get', return_value=index_session) as m3,\
                mock.patch('requests.Session', return_value=session) as m4,\
                mock.patch('ui.Branch._diff_files') as m5,\
                mock.patch('os.remove') as m6,\
                mock.patch('ui.list_files', return_value=existing_files) as m7:
            branch.fetch_remote_index(GLOBAL_CONTEXT, download_tracker)

        m2.assert_called_once_with(download_tracker)
        self.assertEqual(m3.call_count, 1)
        self.assertEqual(m4.call_count, 1)
        self.assertEqual(1, len(download_tracker.run_called_with))


class UiTest(AsyncTestCase):
    executor = futures.ThreadPoolExecutor()

    def setUp(self):
        common.get_app()
        common.get_loop()

    def test_main_window_can_create_main_window(self):
        with mock.patch('ui.MainWindow.init_ui', lambda self: None) as m:
            main_window = ui.MainWindow(testing_config)

        self.assertTrue(hasattr(main_window, "branches"))
        self.assertTrue(hasattr(main_window, "branch_lookup"))
        self.assertTrue(hasattr(main_window, "context"))
        self.assertTrue(hasattr(main_window, "client_state"))
        self.assertTrue(hasattr(main_window, "config"))
        self.assertIn("Development", main_window.branches)

    def test_main_window_can_initialize_ui(self):
        main_window = ui.MainWindow(testing_config)
        self.assertTrue(hasattr(main_window, "launch_game_btn"))
        self.assertTrue(hasattr(main_window, "branch_box"))
        self.assertTrue(hasattr(main_window, "news_view"))
        self.assertTrue(hasattr(main_window, "progress_bar"))
        self.assertTrue(hasattr(main_window, "download_tracker"))
        self.assertTrue(hasattr(main_window, "download_tracker"))

        # TODO: maybe determine if the widgets are set up properly?

    def test_main_window_can_launch_game(self):
        launch_args = []
        system = get_platform()
        testing_config.launch_flags.setdefault(system, ("-unknown", "-system"))
        testing_config.game_binary.setdefault(system, "unknown.bin")
        main_window = ui.MainWindow(testing_config)

        def branch_launch_game_mock(self, binary, args):
            launch_args.extend([self.name, binary, args])

        with mock.patch('ui.Branch.launch_game', branch_launch_game_mock) as m:
            main_window.launch_game()

        self.assertEqual(len(launch_args), 3)
        self.assertEqual(launch_args[0], "Development")
        self.assertEqual(launch_args[1],
                         testing_config.game_binary[system])
        self.assertEqual(launch_args[2],
                         testing_config.launch_flags[system])

    def test_main_window_can_change_branch_name(self):
        main_window = ui.MainWindow(testing_config)
        main_window.branch = None
        self.assertIs(main_window.branch, None)
        main_window.on_branch_change("Development")
        self.assertEqual(main_window.branch, "develop")

    def test_main_window_can_build_path(self):
        main_window = ui.MainWindow(testing_config)
        test_path = (
            "https://patch.houraiteahouse.net/fantasy-crescendo/launcher/" +
            "%s/%s" % (get_platform(), os.path.basename(sys.executable)))
        built_path = main_window.build_path(testing_config.launcher_endpoint)
        self.assertEqual(built_path, test_path)

    def test_main_window_ready_swaps_progress_bar_and_launch_game_button(self):
        main_window = ui.MainWindow(testing_config)
        mock_data = dict(
            launch_game_button_enabled=False,
            launch_game_button_shown=False,
            progress_bar_shown=True,
            )

        def launch_game_button_enable_mock(self, new_state):
            mock_data['launch_game_button_enabled'] = bool(new_state)

        def launch_game_button_show_mock(self):
            mock_data['launch_game_button_shown'] = True

        def progress_bar_hide_mock(self):
            mock_data['progress_bar_shown'] = False

        with mock.patch('PyQt5.QtWidgets.QPushButton.setEnabled',
                        launch_game_button_enable_mock) as m1,\
                mock.patch('PyQt5.QtWidgets.QPushButton.show',
                           launch_game_button_show_mock) as m2,\
                mock.patch('PyQt5.QtWidgets.QProgressBar.hide',
                           progress_bar_hide_mock) as m3:
            self.run_async(main_window.ready)

        self.assertTrue(mock_data['launch_game_button_enabled'])
        self.assertTrue(mock_data['launch_game_button_shown'])
        self.assertFalse(mock_data['progress_bar_shown'])

    def test_main_window_game_update_check_can_succeed(self):
        main_window = ui.MainWindow(testing_config)
        main_window.executor = self.executor

        mock_data = dict(
            launch_game_button_shown=True,
            progress_bar_shown=False,
            )

        def launch_game_button_hide_mock(self):
            mock_data['launch_game_button_shown'] = False

        def progress_bar_show_mock(self):
            mock_data['progress_bar_shown'] = True

        with mock.patch('PyQt5.QtWidgets.QPushButton.hide',
                        launch_game_button_hide_mock) as m1,\
                mock.patch('PyQt5.QtWidgets.QProgressBar.show',
                           progress_bar_show_mock) as m2,\
                mock.patch('ui.get_loop', return_value=self.loop) as m3,\
                mock.patch('ui.Branch.fetch_remote_index') as m4:
            m4._is_coroutine = False
            self.run_async(main_window.game_update_check)

        m4.assert_called_once_with(main_window.context,
                                   main_window.download_tracker)
        self.assertFalse(mock_data['launch_game_button_shown'])
        self.assertTrue(mock_data['progress_bar_shown'])
        self.assertEqual(main_window.client_state, ui.ClientState.READY)

    def test_main_window_game_status_check_can_succeed(self):
        main_window = ui.MainWindow(testing_config)
        main_window.executor = self.executor

        mock_data = dict(
            launch_game_button_enabled=True,
            )

        def launch_game_button_enable_mock(self, new_state):
            mock_data['launch_game_button_enabled'] = bool(new_state)

        with mock.patch('PyQt5.QtWidgets.QPushButton.setEnabled',
                        launch_game_button_enable_mock) as m1,\
                mock.patch('PyQt5.QtWidgets.QPushButton.setText') as m2,\
                mock.patch('ui.get_loop', return_value=self.loop) as m3,\
                mock.patch('ui.Branch.index_directory') as m4:
            m4._is_coroutine = False
            self.run_async(main_window.game_status_check)

        self.assertEqual(m4.call_count, len(main_window.branches))
        self.assertFalse(mock_data['launch_game_button_enabled'])
        self.assertEqual(main_window.client_state,
                         ui.ClientState.GAME_UPDATE_CHECK)

    def test_main_window_main_loop_increments_successfully(self):
        main_window = ui.MainWindow(testing_config)
        mock_data = dict(
            launcher_update=-1,
            game_status=-1,
            game_update=-1,
            ready=-1,
            )

        def launcher_update_mock(_self):
            mock_data['launcher_update'] = ui.ClientState.LAUNCHER_UPDATE_CHECK
            _self.client_state = ui.ClientState.GAME_STATUS_CHECK

        def game_status_mock(_self):
            mock_data['game_status'] = ui.ClientState.GAME_STATUS_CHECK
            _self.client_state = ui.ClientState.GAME_UPDATE_CHECK

        def game_update_mock(_self):
            mock_data['game_update'] = ui.ClientState.GAME_UPDATE_CHECK
            _self.client_state = ui.ClientState.READY

        def ready_mock(_self):
            mock_data['ready'] = ui.ClientState.READY
            raise StopLoopException()

        with mock.patch('ui.get_loop', return_value=self.loop) as m1,\
                mock.patch('ui.QThreadExecutor') as m2,\
                async_patch('ui.MainWindow.launcher_update_check',
                            launcher_update_mock) as m3,\
                async_patch('ui.MainWindow.game_status_check',
                            game_status_mock) as m4,\
                async_patch('ui.MainWindow.game_update_check',
                            game_update_mock) as m5,\
                async_patch('ui.MainWindow.ready', ready_mock) as m6,\
                async_patch('ui.MainWindow.fetch_news') as m7:
            try:
                self.run_async(main_window.main_loop)
            except StopLoopException:
                pass

        self.assertEqual(mock_data.get('launcher_update'),
                         ui.ClientState.LAUNCHER_UPDATE_CHECK)
        self.assertEqual(mock_data.get('game_status'),
                         ui.ClientState.GAME_STATUS_CHECK)
        self.assertEqual(mock_data.get('game_update'),
                         ui.ClientState.GAME_UPDATE_CHECK)
        self.assertEqual(mock_data.get('ready'), ui.ClientState.READY)

    def test_main_window_fetch_news_can_succeed(self):
        main_window = ui.MainWindow(testing_config)
        rows = []
        rss_data = test_rss_data

        def add_row_mock(self, date_label, link_label):
            rows.append((date_label, link_label))

        with mock.patch('ui.feedparser.parse', return_value=rss_data) as m1,\
                mock.patch('requests.get') as m2,\
                mock.patch('ui.QLabel') as m3,\
                mock.patch('ui.QFormLayout.addRow', add_row_mock) as m4:
            self.run_async(main_window.fetch_news)

        self.assertEqual(len(rows), 10)

    def test_main_window_fetch_news_fails_without_news_rss_feed(self):
        main_window = ui.MainWindow(testing_config)
        main_window.config = None
        rows = []
        rss_data = test_rss_data

        def add_row_mock(self, date_label, link_label):
            rows.append((date_label, link_label))

        with mock.patch('ui.feedparser.parse', return_value=rss_data) as m1,\
                mock.patch('requests.get') as m2,\
                mock.patch('ui.QLabel') as m3,\
                mock.patch('ui.QFormLayout.addRow', add_row_mock) as m4:
            self.run_async(main_window.fetch_news)

        self.assertEqual(len(rows), 0)

    def test_main_window_launcher_update_fails_without_sys_frozen(self):
        main_window = ui.MainWindow(testing_config)
        main_window.config = None
        with mock.patch('ui.sha256_hash', should_not_be_run) as m:
            try:
                has_argv = hasattr(sys, 'argv')
                has_frozen = hasattr(sys, 'frozen')
                argv = getattr(sys, 'argv', None)
                frozen = getattr(sys, 'frozen', None)
                if has_frozen:
                    del sys.frozen
                self.run_async(main_window.launcher_update_check)
                exception = None
            except Exception as e:
                exception = e

            fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen)

            if exception is not None:
                raise exception

        self.assertEqual(main_window.client_state,
                         ui.ClientState.GAME_STATUS_CHECK)

    def test_main_window_launcher_update_returns_early_when_testing(self):
        main_window = ui.MainWindow(testing_config)
        with mock.patch('ui.sha256_hash', should_not_be_run) as m:
            try:
                has_argv = hasattr(sys, 'argv')
                has_frozen = hasattr(sys, 'frozen')
                argv = getattr(sys, 'argv', None)
                frozen = getattr(sys, 'frozen', None)
                sys.argv, sys.frozen = ['--test'], True
                self.run_async(main_window.launcher_update_check)
                exception = None
            except Exception as e:
                exception = e

            fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen)

            if exception is not None:
                raise exception

        self.assertEqual(main_window.client_state,
                         ui.ClientState.GAME_STATUS_CHECK)

    def test_main_window_launcher_update_returns_early_with_bad_config(self):
        main_window = ui.MainWindow(testing_config)
        main_window.config = None
        with mock.patch('ui.sha256_hash', should_not_be_run) as m:
            try:
                has_argv = hasattr(sys, 'argv')
                has_frozen = hasattr(sys, 'frozen')
                argv = getattr(sys, 'argv', None)
                frozen = getattr(sys, 'frozen', None)
                sys.argv, sys.frozen = [], True
                self.run_async(main_window.launcher_update_check)
                exception = None
            except Exception as e:
                exception = e

            fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen)

            if exception is not None:
                raise exception

        self.assertEqual(main_window.client_state,
                         ui.ClientState.GAME_STATUS_CHECK)

    def test_main_window_launcher_update_returns_on_early_same_hash(self):
        main_window = ui.MainWindow(testing_config)
        main_window.executor = self.executor
        response = ResponseMock(b'')
        has_exec = hasattr(sys, 'executable')
        executable = getattr(sys, 'executable')
        sys.executable = 'test_exec.bin'
        launcher_hash = 'qwerty'
        remote_hash = 'qwerty'

        with mock.patch('ui.sha256_hash', return_value=launcher_hash) as m1,\
                mock.patch('requests.get', return_value=response) as m2,\
                mock.patch('download.DownloadTracker.clear',
                           should_not_be_run) as m3:
            response._text = remote_hash
            try:
                has_argv = hasattr(sys, 'argv')
                has_frozen = hasattr(sys, 'frozen')
                argv = getattr(sys, 'argv', None)
                frozen = getattr(sys, 'frozen', None)
                sys.argv, sys.frozen = [], True
                self.run_async(main_window.launcher_update_check)
                exception = None
            except Exception as e:
                exception = e

            fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen)

            if exception is not None:
                raise exception

        if has_exec:
            sys.executable = executable

    def test_main_window_launcher_update_can_succeed(self):
        main_window = ui.MainWindow(testing_config)
        main_window.executor = self.executor
        response = ResponseMock(b'')
        has_exec = hasattr(sys, 'executable')
        executable = getattr(sys, 'executable')
        sys.executable = 'test_exec.bin'
        launcher_hash = 'qwerty'
        remote_hash = 'qwerty'
        # TODO: Finish this test
        return

        with mock.patch('ui.sha256_hash', return_value=launcher_hash) as m1,\
                mock.patch('requests.get', return_value=response) as m2,\
                async_patch('download.DownloadTracker.run_async', asdf) as m3,\
                mock.patch('os.path.exists', asdf) as m4,\
                mock.patch('os.remove', asdf) as m5,\
                mock.patch('os.rename', asdf) as m6,\
                mock.patch('os.chmod', asdf) as m7,\
                mock.patch('subprocess.Popen', asdf) as m8,\
                mock.patch('sys.exit', asdf) as m9:
            response._text = remote_hash
            try:
                self.run_async(main_window.launcher_update_check)
                exception = None
            except Exception as e:
                exception = e

            fix_sys_argv_and_frozen(has_argv, has_frozen, argv, frozen)

            if exception is not None:
                raise exception

        if has_exec:
            sys.executable = executable


if __name__ == "__main__":
    main()
