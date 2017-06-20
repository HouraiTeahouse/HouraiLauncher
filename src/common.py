import asyncio
import os
import sys
import re
from quamash import QEventLoop
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from util import get_platform

try:
    # common needs to import config, and config needs to import common.
    # whichever one successfully imports the other will give the other
    # a reference to itself.
    import config
    config.common = sys.modules[__name__]
except ImportError:
    config = None

ICON_SIZES = (16, 32, 48, 64, 256)

GLOBAL_CONTEXT = {
    'platform': get_platform(),
    'executable': os.path.basename(sys.executable)
}

vars_regex = re.compile('{(.*?)}')


def get_app():
    g = globals()
    if g.get('app') is None:
        g['app'] = QApplication(sys.argv)

    return app


def get_loop():
    g = globals()
    if g.get('loop') is None:
        if g.get('app') is None:
            raise NameError("cannot create loop without an app to bind it to.")
        new_loop = QEventLoop(app)
        asyncio.set_event_loop(new_loop)
        g['loop'] = new_loop

    return loop


def set_app_icon():
    g = globals()

    if g.get('app') is None:
        raise NameError("'app' is not defined. cannot set its icon.")
    # load all the icons from the img folder into a QIcon object
    app_icon = QtGui.QIcon()
    for size in ICON_SIZES:
        app_icon.addFile(
            os.path.join(
                config.RESOURCE_DIR, 'img', '%sx%s.ico' % (size, size)),
            QtCore.QSize(size, size))

    g['app_icon'] = app_icon
    app.setWindowIcon(app_icon)


def sanitize_url(url):
    return url.lower().replace(' ', '-')


def inject_variables(path_format, vars_obj=GLOBAL_CONTEXT):
    matches = vars_regex.findall(path_format)
    path = path_format
    vars_is_dict = isinstance(vars_obj, dict)
    for match in matches:
        if vars_is_dict:
            replacement = vars_obj.get(match)
        else:
            replacement = getattr(vars_obj, match, None)
        if replacement is None:
            continue
        path = path.replace('{%s}' % match, str(replacement))
    return path
