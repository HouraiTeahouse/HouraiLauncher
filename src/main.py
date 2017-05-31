import os
from PyQt5 import QtGui, QtCore
from config import CONFIG, RESOURCE_DIR
from ui import MainWindow
from common import app, loop


app_icon = QtGui.QIcon()
app_icon.addFile(os.path.join(RESOURCE_DIR, 'img/16x16.ico'),
                 QtCore.QSize(16, 16))
app_icon.addFile(os.path.join(RESOURCE_DIR, 'img/24x24.ico'),
                 QtCore.QSize(24, 24))
app_icon.addFile(os.path.join(RESOURCE_DIR, 'img/32x32.ico'),
                 QtCore.QSize(32, 32))
app_icon.addFile(os.path.join(RESOURCE_DIR, 'img/48x48.ico'),
                 QtCore.QSize(48, 48))
app_icon.addFile(os.path.join(RESOURCE_DIR, 'img/app.ico'),
                 QtCore.QSize(256, 256))
app.setWindowIcon(app_icon)


main_window = MainWindow(CONFIG)

if __name__ == "__main__":
    main_window.show()
    try:
        loop.run_until_complete(main_window.main_loop())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
