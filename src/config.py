import os
import json
import sys
import shutil
import gettext
import requests
import logging
import platform
from logging.handlers import RotatingFileHandler
from requests.exceptions import HTTPError
from common import inject_variables, GLOBAL_CONTEXT, sanitize_url
from util import namedtuple_from_mapping
from collections import OrderedDict

if 'win' in platform.platform().lower():
    try:
        import gettext_windows
    except:
        loggin.warning('Cannot import gettext_windows')

CHUNK_SIZE = 1024 * 1024

CONFIG_DIRNAME = 'Launcher'
TRANSLATION_DIRNAME = 'i18n'
CONFIG_FILE = 'config.json'

# Get the base directory the executable is found in
# When running from a python interpretter, it will use the current working
# directory.
# sys.frozen is an attribute injected by pyinstaller at runtime
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.getcwd()
log_handler = RotatingFileHandler(os.path.join(BASE_DIR, 'launcher_log.txt'),
                                  backupCount=5)
log_handler.doRollover()
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)
root_logger.setLevel(logging.INFO)
logging.info('Base Directory: %s' % BASE_DIR)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)

CONFIG_DIR = os.path.join(BASE_DIR, CONFIG_DIRNAME)
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
logging.info('Config Directory: %s' % CONFIG_DIR)

if getattr(sys, '_MEIPASS', False):
    RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
else:
    RESOURCE_DIR = os.getcwd()
logging.info('Resource Directory: %s' % RESOURCE_DIR)

if 'win' in platform.platform().lower():
    logging.info('Setting Windows enviorment variables for translation...')
    gettext_windows.setup_env()
TRANSLATION_DIR = os.path.join(RESOURCE_DIR, TRANSLATION_DIRNAME)
TRANSLATIONS = gettext.translation(
    'hourai-launcher', TRANSLATION_DIR, fallback=True)
TRANSLATIONS.install()
logging.info('Translation Directory: %s' % TRANSLATION_DIR)

# Load Config
config_path = os.path.join(CONFIG_DIR, CONFIG_FILE)
resource_config = os.path.join(RESOURCE_DIR, CONFIG_FILE)
if not os.path.exists(config_path) and os.path.exists(resource_config):
    shutil.copyfile(resource_config, config_path)

logging.info('Loading local config from %s...' % config_path)
with open(config_path, 'r+') as config_file:
    # Using OrderedDict to preserve JSON ordering of dictionaries
    config_json = json.load(config_file, object_pairs_hook=OrderedDict)

    old_url = None
    GLOBAL_CONTEXT['project'] = sanitize_url(config_json['project'])
    if 'config_endpoint' in config_json:
        url = inject_variables(config_json['config_endpoint'])
        while old_url != url:
            logging.info('Loading remote config from %s' % url)
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                config_json = response.json()
                logging.info('Fetched new config from %s.' % url)
                config_file.seek(0)
                config_file.truncate()
                json.dump(config_json, config_file)
                logging.info('Saved new config to disk: %s' % config_path)
            except HTTPError as http_error:
                logging.error(http_error)
                break
            except Timeout as timeout:
                logging.error(timeout)
                break
            old_url = url
            GLOBAL_CONTEXT['project'] = sanitize_url(config_json['project'])
            url = inject_variables(config_json['config_endpoint'])
            if 'config_endpoint' not in config_json:
                break
    CONFIG = namedtuple_from_mapping(config_json)
    GLOBAL_CONTEXT['project'] = sanitize_url(config_json['project'])
