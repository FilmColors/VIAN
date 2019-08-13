#!bin/bash
"""
VIAN - Visual Movie Annotation and Analysis


copyright by 
Gaudenz Halter
University of Zurich
2017

Visualization and MultimediaLab 

"""


import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import platform
import sys
from time import sleep
import cProfile
import traceback
from datetime import datetime
from threading import Thread


abspath = os.path.abspath(sys.executable)
dname = os.path.dirname(abspath)
# os.chdir(dname)
# print(dname)
# print(os.getcwd())

import logging
logging.getLogger('tensorfyylow').disabled = True

import PyQt5
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QPixmap, QIcon


from core.data.settings import UserSettings
from core.gui.main_window import MainWindow

DEBUG = True
MAIN_WINDOW = None

class SuperFilter(QObject):
    def __init__(self, parent):
        super(SuperFilter, self).__init__(parent)

    def eventFilter(self, a0: 'QObject', a1: 'QEvent'):
        if a1.type() == QEvent.MouseButtonPress:
            print(a0.parent(), a0.parent())
            if a0.parent() is not None: print(a0.parent().parent())
            print(a0, a1)
        return super(SuperFilter, self).eventFilter(a0, a1)


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    if DEBUG:
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    else:
        global MAIN_WINDOW
        # print("CRASH")
        # sys._excepthook(exctype, value, traceback)
        QMessageBox.warning(MAIN_WINDOW, "Error occured", "Oups, there has gone something wrong.\n"
                                                          "Probably you can just work on, probably not.\n"
                                                          "Best you make a backup of your project now. ")


def handler(msg_type, msg_log_context, msg_string):
    pass


def set_style_sheet(app, path):
    style_sheet = open(os.path.abspath(path), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


def set_attributes(app):
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # if sys.platform == "darwin":
    #     app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)


if __name__ == '__main__':
    attributes = None
    PyQt5.QtCore.qInstallMessageHandler(handler)

    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    settings = UserSettings()
    settings.load()


    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    # filter = SuperFilter(app)
    # app.installEventFilter(filter)
    app.setWindowIcon(QIcon("qt_ui/images/main.png"))
    set_attributes(app)
    set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css") #settings.THEME_PATH

    screen = app.desktop().screenGeometry()

    pixmap = QPixmap("qt_ui/images/loading_screen_round.png")
    pixmap = pixmap.scaled(screen.height() / 2, screen.height() / 2, transformMode=Qt.SmoothTransformation)

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.SplashScreen)
    splash.show()
    app.processEvents()

    main = MainWindow(splash)
    MAIN_WINDOW = main
    sys.exit(app.exec_())



