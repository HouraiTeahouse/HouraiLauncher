import logging
import os
from PyQt5 import QtGui, QtCore
from config import CONFIG, RESOURCE_DIR
from ui import MainWindow
from common import app, loop

# load all the icons from the img folder into a QIcon object
app_icon = QtGui.QIcon()
for size in (16, 32, 48, 64, 256):
    app_icon.addFile(
        os.path.join(RESOURCE_DIR, 'img', '%sx%s.ico' % (size, size)),
        QtCore.QSize(size, size))
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
        print('Hello')
        logging.exception(e)
        raise
    finally:
        loop.close()
