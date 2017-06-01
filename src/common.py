import asyncio
import logging
import sys
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
GLOBAL_CONTEXT = {'platform': platform.system()}

vars_regex = re.compile('{(.*?)}')


def inject_variables(path_format, vars_obj=GLOBAL_CONTEXT):
    matches = vars_regex.findall(path_format)
    path = path_format
    for match in matches:
        target = '{%s}' % match
        if isinstance(vars_obj, dict) and match in vars_obj:
            path = path.replace(target, str(vars_obj[match]))
        else:
            replacement = getattr(vars_obj, match, None)
            if replacement is not None:
                path = path.replace(target, str(replacement))
    return path
