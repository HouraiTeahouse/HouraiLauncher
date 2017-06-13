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

__all__ = (
    "TRANSLATION_DIRNAME", "TRANSLATION_DIR", "TRANSLATIONS",
    "CONFIG", "CONFIG_DIRNAME", "CONFIG_DIR", "CONFIG_NAME",
    "BASE_DIR", "RESOURCE_DIR", "GLOBAL_CONTEXT"
    )


CONFIG_DIRNAME = 'Launcher'
CONFIG_NAME = 'config.json'
TRANSLATION_DIRNAME = 'i18n'
_TRANSLATIONS_INSTALLED = False
_DIRECTORIES_SETUP = False
_LOGGER_SETUP = False


def get_config():
    if globals().get('CONFIG') is None:
        reload_config()

    return CONFIG


def install_translations():
    g = globals()
    if g.get('_TRANSLATIONS_INSTALLED'):
        return

    gettext_windows = None
    if 'win' in platform.platform().lower():
        logging.info(
            'Setting Windows environment variables for translation...')
        try:
            import gettext_windows
        except:
            logging.warning('Cannot import gettext_windows')

    if gettext_windows is not None:
        gettext_windows.setup_env()

    g['TRANSLATIONS'] = gettext.translation(
        'hourai-launcher', TRANSLATION_DIR, fallback=True)
    TRANSLATIONS.install()
    g['_TRANSLATIONS_INSTALLED'] = True


def reload_config():
    g = globals()
    setup_directories()
    install_translations()

    # Load Config
    config_path = os.path.join(CONFIG_DIR, CONFIG_NAME)
    resource_config = os.path.join(RESOURCE_DIR, CONFIG_NAME)
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
        g['CONFIG'] = namedtuple_from_mapping(config_json)
        GLOBAL_CONTEXT['project'] = sanitize_url(config_json['project'])

    return g['CONFIG']


def setup_logger(log_dir, backup_count=5):
    g = globals()
    if g.get('_LOGGER_SETUP'):
        return

    log_handler = RotatingFileHandler(
        os.path.join(log_dir, 'launcher_log.txt'),
        backupCount=backup_count)
    log_handler.doRollover()
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    g['_LOGGER_SETUP'] = True


def setup_directories():
    g = globals()
    if g.get('_DIRECTORIES_SETUP'):
        return
    # Get the base directory the executable is found in
    # When running from a python interpreter, it will use the current working
    # directory.
    # sys.frozen is an attribute injected by pyinstaller at runtime
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    else:
        BASE_DIR = os.getcwd()

    setup_logger(log_dir=BASE_DIR, backup_count=5)
    logging.info('Base Directory: %s' % BASE_DIR)

    if getattr(sys, '_MEIPASS', False):
        RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
    else:
        RESOURCE_DIR = os.getcwd()
    logging.info('Resource Directory: %s' % RESOURCE_DIR)

    CONFIG_DIR = os.path.join(BASE_DIR, CONFIG_DIRNAME)
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    logging.info('Config Directory: %s' % CONFIG_DIR)

    TRANSLATION_DIR = os.path.join(RESOURCE_DIR, TRANSLATION_DIRNAME)
    logging.info('Translation Directory: %s' % TRANSLATION_DIR)

    # inject the directories into the module globals
    g.update(BASE_DIR=BASE_DIR, RESOURCE_DIR=RESOURCE_DIR,
             CONFIG_DIR=CONFIG_DIR, TRANSLATION_DIR=TRANSLATION_DIR)

    g['_DIRECTORIES_SETUP'] = True
