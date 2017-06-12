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
