import os, sys

import sys, os
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    _VIAN_ROOT = sys._MEIPASS
else:
    _VIAN_ROOT = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../")


def get_data_dir():
    return os.path.join(_VIAN_ROOT, "data")


def get_voc_dir():
    return os.path.join(get_data_dir(), "vocabularies")


def get_models_dir():
    return os.path.join(get_data_dir(), "models")


def get_examples_dir():
    return os.path.join(get_data_dir(), "examples")


def get_templates_dir():
    return os.path.join(get_data_dir(), "templates")