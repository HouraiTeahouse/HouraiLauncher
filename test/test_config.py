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


class RotatingFileHandlerMock(RotatingFileHandler):

    def doRollover(self):
        pass

    def rotate(self, source, dest):
        pass

    def close(self):
        pass

    def _open(self):
        pass

    def emit(self, record):
        pass


class ConfigTest(TestCase):
    session_mock = None

    def setUp(self):
        config.RotatingFileHandler = RotatingFileHandlerMock

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

        config.RotatingFileHandler = RotatingFileHandler
        requests.get = requests.real_get
        del requests.real_get
        del self.session_mock

    def test_directories_are_properly_setup(self):
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

    def test_loggers_are_properly_setup(self):
        # TODO:
        # until the bug with the logger can be fixed, the logger wont be setup.
        # also need to determine how to detect if it has been set up
        config.setup_logger()

    def test_loggers_are_not_setup_twice(self):
        config._LOGGER_SETUP = True
        config.setup_logger()
        # TODO:
        # need to determine how to detect if it has been set up

    def test_translations_are_properly_installed(self):
        # TODO:
        # need to figure out how to determine if they are installed
        config.install_translations()

        self.assertTrue(config._TRANSLATIONS_INSTALLED)

    def test_config_can_load_config(self):
        with mock.patch('config.open', mock.mock_open(
                read_data=config_test_data)) as m:
            config.load_config()

        session = self.session_mock
        responses = session.responses
        self.assertIn(
            "https://patch.houraiteahouse.net/fantasy-crescendo/"
            "launcher/config.json", responses)

        m.assert_called_once_with(
            os.path.join(config.CONFIG_DIR, config.CONFIG_NAME), 'r+')

    def test_config_contains_proper_attributes(self):
        with mock.patch('config.open', mock.mock_open(
                read_data=config_test_data)) as m:
            cfg = config.load_config()

        assert hasattr(config, "TRANSLATION_DIR")
        assert hasattr(config, "TRANSLATION_DIRNAME")
        assert hasattr(config, "TRANSLATIONS")
        assert hasattr(config, "CONFIG_DIR")
        assert hasattr(config, "CONFIG_DIRNAME")
        assert hasattr(config, "CONFIG_NAME")
        assert hasattr(config, "CONFIG")
        assert hasattr(config, "BASE_DIR")
        assert hasattr(config, "RESOURCE_DIR")
        assert hasattr(config, "GLOBAL_CONTEXT")

        assert hasattr(cfg, "branches")
        assert hasattr(cfg, "config_endpoint")
        assert hasattr(cfg, "launcher_endpoint")
        assert hasattr(cfg, "index_endpoint")
        assert hasattr(cfg, "launch_flags")
        assert hasattr(cfg, "news_rss_feed")
        assert hasattr(cfg, "game_binary")
        assert hasattr(cfg, "logo")
        assert hasattr(cfg, "project")


if __name__ == "__main__":
    main()
