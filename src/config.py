import os
import json
import sys
from util import namedtuple_from_mapping
from collections import OrderedDict

CONFIG_FILE = 'config.json'

# Get the base directory the executable is found in
# When running from a python interpretter, it will use the current working
# directory.
# sys.frozen is an attribute injected by pyinstaller at runtime
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.getcwd()

if getattr(sys, '_MEIPASS', False):
    RESOURCE_DIR = os.path.abspath(sys._MEIPASS)
else:
    RESOURCE_DIR = os.getcwd()

# Load Config
with open(os.path.join(RESOURCE_DIR, CONFIG_FILE)) as config_file:
    # Using OrderedDict to preserve JSON ordering of dictionaries
    CONFIG = namedtuple_from_mapping(
        json.load(config_file, object_pairs_hook=OrderedDict))
