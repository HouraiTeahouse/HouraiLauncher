import config
import main
from test_config import RotatingFileHandler, RotatingFileHandlerMock
from unittest import TestCase, mock, main as unittest_main


class AppMock(object):

    def setWindowIcon(self, app_icon):
        pass


class LoopMock(object):
    exception_type = None

    def run_until_complete(self, main_window):
        pass

    def run_forever(self):
        if self.exception_type is not None:
            raise self.exception_type()

    def close(self):
        pass


class MainWindowMock(object):

    def __init__(self, config):
        pass

    def main_loop(self):
        pass

    def show(self):
        pass


class MainTest(TestCase):

    def setUp(self):
        config.RotatingFileHandler = RotatingFileHandlerMock
        main.real_app = main.app
        main.real_loop = main.loop
        main.real_MainWindow = main.MainWindow
        main.app = AppMock()
        main.loop = LoopMock()
        main.MainWindow = MainWindowMock

    def tearDown(self):
        config.RotatingFileHandler = RotatingFileHandler
        main.app = main.real_app
        main.loop = main.real_loop
        main.MainWindow = main.real_MainWindow
        del main.real_app
        del main.real_loop
        del main.real_MainWindow

    def test_main_can_initialize(self):
        main.initialize()
        assert hasattr(main, "app_icon")
        assert hasattr(main, "main_window")

        # TODO:
        # check that the icon isn't empty somehow

    def test_main_can_show_main_window(self):
        main.initialize(True)

    def test_main_can_catch_runtime_error(self):
        main.loop.exception_type = RuntimeError
        main.initialize(True)

    def test_main_will_raise_general_exception(self):
        main.loop.exception_type = Exception
        try:
            main.initialize(True)
        except Exception as e:
            if type(e) is not main.loop.exception_type:
                raise


if __name__ == "__main__":
    unittest_main()
