import asyncio, sys
from quamash import QEventLoop
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
