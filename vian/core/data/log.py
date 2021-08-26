import traceback
import logging
import os

# logging.basicConfig(format='%(asctime)s %(message)s', level="INFO")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from copy import copy
from logging import Formatter

MAPPING = {
    'DEBUG'   : 37, # white
    'INFO'    : 36, # cyan
    'WARNING' : 33, # yellow
    'ERROR'   : 31, # red
    'CRITICAL': 41, # white on red bg
}

PREFIX = '\033['
SUFFIX = '\033[0m'

class ColoredFormatter(Formatter):

    def __init__(self, patern):
        Formatter.__init__(self, patern)

    def format(self, record):
        colored_record = copy(record)
        levelname = colored_record.levelname
        seq = MAPPING.get(levelname, 37) # default white
        colored_levelname = ('{0}{1}m{2}{3}') \
            .format(PREFIX, seq, levelname, SUFFIX)
        colored_record.levelname = colored_levelname
        return Formatter.format(self, colored_record)

# Create top level logger
log = logging.getLogger("VIAN")

# Add console handler using our custom ColoredFormatter
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
cf = ColoredFormatter("[%(name)s][%(levelname)s]  %(message)s")
ch.setFormatter(cf)
log.addHandler(ch)

# # Add file handler
# fh = logging.FileHandler('app.log')
# fh.setLevel(logging.DEBUG)
# ff = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# fh.setFormatter(ff)
# log.addHandler(fh)

# Set log level
log.setLevel(logging.DEBUG)


def log_info(*args):
    msg = ""
    for a in args:
        msg += str(a) + " "
    log.info(msg)

def log_warning(*args):
    msg = ""
    for a in args:
        msg += str(a) + " "
    log.warning(msg)

def log_error(*args):
    msg = ""
    for a in args:
        msg += str(a) + " "
    log.error(msg)
    log.error(traceback.format_exc())

def log_debug(*args):
    msg = ""
    for a in args:
        msg += str(a) + " "
    log.debug(msg)
# def log_warning(*args)

if __name__ == '__main__':
    log_info("Hello", "Info")
    log_warning("Hello", "Warning")
    log_error("Hello", "Error")
    log_debug("Hello", "Debug")