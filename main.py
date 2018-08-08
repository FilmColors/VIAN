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

import PyQt5
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from core.data.settings import UserSettings
from core.gui.main_window import MainWindow

DEBUG = False
MAIN_WINDOW = None


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    if DEBUG:
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    else:
        global MAIN_WINDOW
        QMessageBox.warning(MAIN_WINDOW, "Error occured", "An Error Occured, please safe your project.")


def handler(msg_type, msg_log_context, msg_string):
    pass


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
    PyQt5.QtCore.qInstallMessageHandler(handler)

    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    settings = UserSettings()
    settings.load()

    app = QApplication(sys.argv)
    set_attributes(app)
    set_style_sheet(app, settings.THEME_PATH)
    splash = QSplashScreen(QPixmap("qt_ui/images/loading_screen.png"))
    splash.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.SplashScreen)
    splash.show()
    app.processEvents()

    main = MainWindow(splash)
    MAIN_WINDOW = main
    sys.exit(app.exec_())



