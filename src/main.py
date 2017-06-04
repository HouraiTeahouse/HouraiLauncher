import logging
import os
from PyQt5 import QtGui, QtCore
from config import CONFIG, RESOURCE_DIR
from ui import MainWindow
from common import app, loop

app_icon = QtGui.QIcon()
for size in [16, 24, 32, 48]:
    app_icon.addFile(
        os.path.join(RESOURCE_DIR, 'img/%sx%s.ico' % (size, size)),
        QtCore.QSize(size, size))
app_icon.addFile(
    os.path.join(RESOURCE_DIR, 'img/app.ico'), QtCore.QSize(256, 256))
app.setWindowIcon(app_icon)

main_window = MainWindow(CONFIG)

if __name__ == '__main__':
    main_window.show()
    try:
        loop.run_until_complete(main_window.main_loop())
        loop.run_forever()
    except RuntimeError as e:
        logging.exception(e)
    except Exception as e:
        logging.exception(e)
        raise
    finally:
        loop.close()
