"""
VIAN - Visual Movie Annotation and Analysis


copyright by 
Gaudenz Halter
University of Zurich
2017

Visualization and MultimediaLab 

"""


import os
import platform
import sys
from time import sleep
import cProfile
import traceback
from datetime import datetime
from threading import Thread

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from core.corpus.server.corpus_server import CorpusServerWindow
from core.data.settings import UserSettings

#TODO DEBUG needs to be fixed, start in non debug does not work currently
DEBUG = True


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def set_style_sheet(app, path):
    style_sheet = open(os.path.abspath(path), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


def set_attributes(app):
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if sys.platform == "darwin":
        app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)


if __name__ == '__main__':
    attributes = None
    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    settings = UserSettings()
    settings.load()

    app = QApplication(sys.argv)
    set_attributes(app)
    set_style_sheet(app, settings.THEME_PATH)
    app.processEvents()

    main = CorpusServerWindow()
    main.show()
    sys.exit(app.exec_())



