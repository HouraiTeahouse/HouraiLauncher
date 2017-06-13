import config
import ui
from test_config import RotatingFileHandler, RotatingFileHandlerMock
from unittest import TestCase, mock, main


class UiTest(TestCase):

    def setUp(self):
        config.RotatingFileHandler = RotatingFileHandlerMock

    def tearDown(self):
        config.RotatingFileHandler = RotatingFileHandler


if __name__ == "__main__":
    main()
