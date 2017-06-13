import logging
import os
import config
from PyQt5 import QtGui, QtCore
from ui import MainWindow
from common import app, loop


def initialize(show_main_window=False):
    g = globals()

    config.set_directories()
    config.install_translations()

    # load all the icons from the img folder into a QIcon object
    g['app_icon'] = app_icon = QtGui.QIcon()
    for size in (16, 32, 48, 64, 256):
        app_icon.addFile(
            os.path.join(
                config.RESOURCE_DIR, 'img', '%sx%s.ico' % (size, size)),
            QtCore.QSize(size, size))
    app.setWindowIcon(app_icon)
    g['main_window'] = main_window = MainWindow(config.get_config())

    if show_main_window:
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

initialize(__name__ == '__main__')
