import builtins
import config
import requests
import os
import sys
from logging.handlers import RotatingFileHandler
from unittest import TestCase, main, mock
from test_download import SessionMock

config_test_data = """
{
"project": "Fantasy Crescendo",
"logo": "img/logo.png",
"config_endpoint": "https://patch.houraiteahouse.net/{project}/launcher/\
config.json",
"launcher_endpoint": "https://patch.houraiteahouse.net/{project}/launcher/\
{platform}/{executable}",
"index_endpoint": "https://patch.houraiteahouse.net/{project}/{branch}/\
{platform}/index.json",
"news_rss_feed": "https://www.reddit.com/r/touhou.rss",
"game_binary": {
  "Windows": "fc.exe",
  "Linux": "fc.x86_64"
},
"launch_flags":{
},
"branches" : {
  "develop": "Development"
  }
}
"""


def should_not_be_run(*args, **kwargs):
    raise Exception("The line of code should have not been run.")


class ConfigTest(TestCase):
    session_mock = None

    def setUp(self):
        self.session_mock = SessionMock()
        self.session_mock.data = config_test_data
        requests.real_get = requests.get
        requests.get = self.session_mock.get

    def tearDown(self):
        config._LOGGER_SETUP = False
        config._DIRECTORIES_SETUP = False
        config._TRANSLATIONS_INSTALLED = False
        config.CONFIG = None
        config.TRANSLATION_DIR = None
        config.TRANSLATIONS = None
        config.CONFIG_DIR = None
        config.BASE_DIR = None
        config.RESOURCE_DIR = None

        requests.get = requests.real_get
        del requests.real_get
        del self.session_mock

    def test_directories_are_properly_setup(self):
        with mock.patch('os.path.exists', return_value=False) as m1,\
                mock.patch('os.makedirs') as m2:
            config.setup_directories()

        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
        else:
            BASE_DIR = os.getcwd()

        if getattr(sys, '_MEIPASS', False):
            RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
        else:
            RESOURCE_DIR = os.getcwd()

        CONFIG_DIR = os.path.join(BASE_DIR, config.CONFIG_DIRNAME)
        TRANSLATION_DIR = os.path.join(
            RESOURCE_DIR, config.TRANSLATION_DIRNAME)

        self.assertEqual(config.BASE_DIR, BASE_DIR)
        self.assertEqual(config.RESOURCE_DIR, RESOURCE_DIR)
        self.assertEqual(config.CONFIG_DIR, CONFIG_DIR)
        self.assertEqual(config.TRANSLATION_DIR, TRANSLATION_DIR)

        self.assertTrue(config._DIRECTORIES_SETUP)

    def test_loggers_can_be_setup(self):
        config._LOGGER_SETUP = False
        with mock.patch(
                'logging.handlers.RotatingFileHandler.doRollover') as m1,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.rotate') as m2,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.close') as m3,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler._open') as m4,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.emit') as m5:
            config.setup_logger()
        self.assertTrue(config._LOGGER_SETUP)

    def test_loggers_cannot_be_setup_twice(self):
        config._LOGGER_SETUP = True
        with mock.patch('config.RotatingFileHandler', should_not_be_run) as m:
            config.setup_logger()

    def test_translations_can_be_installed(self):
        config.install_translations()
        self.assertIn("_", __builtins__.keys())

    def test_translations_cannot_be_installed_twice(self):
        config._TRANSLATIONS_INSTALLED = True
        with mock.patch('config.get_platform', should_not_be_run) as m:
            config.install_translations()

    def test_config_can_load_config(self):
        config.CONFIG = None
        config.setup_logger()
        config.setup_directories()
        config.install_translations()

        resource_config = os.path.join(config.RESOURCE_DIR, config.CONFIG_NAME)

        def resource_exists_mock(path):
            return path == resource_config

        with mock.patch('config.open', mock.mock_open(
                read_data=config_test_data)) as m1,\
                mock.patch('os.path.exists', resource_exists_mock) as m2,\
                mock.patch('shutil.copyfile') as m3,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.doRollover') as m4,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.rotate') as m5,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.close') as m6,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler._open') as m7,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.emit') as m8:
            config.load_config()

        session = self.session_mock
        responses = session.responses
        self.assertIn(
            "https://patch.houraiteahouse.net/fantasy-crescendo/"
            "launcher/config.json", responses)

        m1.assert_called_once_with(
            os.path.join(config.CONFIG_DIR, config.CONFIG_NAME), 'r+')

    def test_config_contains_proper_attributes(self):
        with mock.patch('config.open', mock.mock_open(
                read_data=config_test_data)) as m1,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.doRollover') as m2,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.rotate') as m3,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.close') as m4,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler._open') as m5,\
                mock.patch(
                    'logging.handlers.RotatingFileHandler.emit') as m6:
            cfg = config.load_config()

        for attr_name in ("TRANSLATION_DIR", "TRANSLATION_DIRNAME",
                          "CONFIG_DIR", "CONFIG_DIRNAME", "CONFIG_NAME",
                          "CONFIG", "BASE_DIR", "RESOURCE_DIR"):
            assert hasattr(config, attr_name), (
                "config module is missing its '%s' attribute" % attr_name)

        for attr_name in ("branches", "config_endpoint", "launcher_endpoint",
                          "index_endpoint", "launch_flags", "news_rss_feed",
                          "game_binary", "logo", "project"):
            assert hasattr(cfg, attr_name), (
                "config is missing its '%s' attribute" % attr_name)


if __name__ == "__main__":
    main()
