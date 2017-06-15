import asyncio
import config
import common
import ui
import os
import shutil
import subprocess
import sys
from PyQt5 import QtWidgets
from unittest import TestCase, mock, main
from util import namedtuple_from_mapping, get_platform

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

    def __init__(self):
        self.downloads = []
        self.downloads_mock_info = {}

    def add_download(self, filepath, url, filesize):
        self.downloads_mock_info[filepath] = filesize
        self.downloads.append(DownloadMock(filepath, url, filesize))

    def __iter__(self):
        return self.downloads.__iter__()


class BranchTest(TestCase):
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


class UiTest(TestCase):

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

        # TODO: determine if the widgets are set up properly?

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

        # TODO: This part needs to be tested using async. need to figure
        # out how to use asyncio in order to finish this test
        return
        with mock.patch('PyQt5.QtWidgets.QPushButton.setEnabled',
                        launch_game_button_enable_mock) as m1,\
                mock.patch('PyQt5.QtWidgets.QPushButton.show',
                           launch_game_button_show_mock) as m2,\
                mock.patch('PyQt5.QtWidgets.QProgressBar.hide',
                           progress_bar_hide_mock) as m3:
            main_window.ready()

        self.assertTrue(mock_data['launch_game_button_enabled'])
        self.assertTrue(mock_data['launch_game_button_shown'])
        self.assertFalse(mock_data['progress_bar_shown'])


if __name__ == "__main__":
    main()
