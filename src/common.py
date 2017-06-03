import asyncio
import os
import sys
import platform
import re
from quamash import QEventLoop
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
GLOBAL_CONTEXT = {
    'platform': platform.system(),
    'executable': os.path.basename(sys.executable)
}

vars_regex = re.compile('{(.*?)}')


def sanitize_url(url):
    return url.lower().replace(' ', '-')


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
