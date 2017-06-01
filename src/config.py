import os
import json
import sys
import shutil
import gettext
import requests
import logging
from requests.exceptions import HTTPError
from common import inject_variables, GLOBAL_CONTEXT, sanitize_url
from util import namedtuple_from_mapping
from collections import OrderedDict

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

CONFIG_DIR = os.path.join(BASE_DIR, CONFIG_DIRNAME)
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

if getattr(sys, '_MEIPASS', False):
    RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
else:
    RESOURCE_DIR = os.getcwd()

TRANSLATION_DIR = os.path.join(RESOURCE_DIR, TRANSLATION_DIRNAME)
TRANSLATIONS = gettext.translation(
    'hourai-launcher', TRANSLATION_DIR, fallback=True)
TRANSLATIONS.install()

# Load Config
config_path = os.path.join(CONFIG_DIR, CONFIG_FILE)
if not os.path.exists(config_path):
    resource_config = os.path.join(RESOURCE_DIR, CONFIG_FILE)
    shutil.copyfile(resource_config, config_path)

logging.info('Loading local config from %s...' % config_path)
with open(config_path, 'r+') as config_file:
    # Using OrderedDict to preserve JSON ordering of dictionaries
    config_json = json.load(config_file, object_pairs_hook=OrderedDict)

    old_url = None
    url = ''
    while old_url != url and 'config_endpoint' in config_json:
        old_url = url
        GLOBAL_CONTEXT['project'] = sanitize_url(config_json['project'])
        url = inject_variables(config_json['config_endpoint'])
        logging.info('Loading remote config from %s' % url)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            config_json = response.json()
            logging.info('Fetched new config from %s.' % url)
            config_file.seek(0)
            config_file.truncate()
            json.dump(config_json, config_file)
            logging.info('Saved new config to disk.')
        except HTTPError as http_error:
            logging.error(http_error)
            break
        except Timeout as timeout:
            logging.error(timeout)
            break
    CONFIG = namedtuple_from_mapping(config_json)
