import asyncio
import sys
import logging
from quamash import QEventLoop
from config import TRANSLATIONS
from PyQt5.QtWidgets import QApplication

logging.basicConfig(filename='launcher_log.txt',
                    filemode='w',
                    level=logging.INFO)

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
_ = TRANSLATIONS.gettext
