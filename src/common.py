import asyncio
import sys
from quamash import QEventLoop
from config import TRANSLATIONS
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
_ = TRANSLATIONS.gettext
