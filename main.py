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
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import platform
import sys
from time import sleep
import time
import cProfile
import traceback as tb
import subprocess

from datetime import datetime
from threading import Thread

from core.hidden_imports import *

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
print("Directory", dname)

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)

import logging
logging.getLogger('tensorfyylow').disabled = True
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import PyQt5
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QPixmap, QIcon


from core.data.settings import UserSettings
from core.gui.main_window import MainWindow, version

DEBUG = os.path.isfile("is_dev.txt")
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
        if not os.path.isdir("log-files"):
            os.mkdir("log-files")

        timestr = time.strftime("%Y%m%d-%H%M%S") + ".txt"

        with open(os.path.join("log-files", timestr), "w") as f:
            f.write("Plaform:  " + sys.platform + "\n")
            f.write("Date:     " + timestr + "\n")
            f.write("Version:  " + version.__version__ + "\n")
            f.write("\n\n#### Traceback ####\n\n")
            tb.print_tb(traceback, file=f)
            f.write("\n\n#### Exception ####\n\n")
            tb.print_exception(exctype, value, traceback, file=f)
            f.write("\n")

        global MAIN_WINDOW
        # print("CRASH")
        # sys._excepthook(exctype, value, traceback)
        answer = QMessageBox.question(MAIN_WINDOW, "Error occured", "Oups, there has gone something wrong.\n"
                                                          "Maybe you can just work on, maybe not.\n"
                                                          "Best you make a backup of your project now. \n" 
                                                          "Also, don't forget to send us the log files in /Your/VIAN/Directory/log-files/\n "
                                                                    "Do you want to open the folder now?")

        if answer == QMessageBox.Yes:
            if sys.platform == "win32":
                subprocess.run("explorer log-files", shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", "log-files"])
            else:
                try:
                    subprocess.run(["nautilus", "log-files"])
                except:
                    pass


def handler(msg_type, msg_log_context, msg_string):
    pass


def set_style_sheet(app, path):
    style_sheet = open(os.path.abspath(path), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


def set_attributes(app):
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # if sys.platform == "darwin":
    #     app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)


if __name__ == '__main__':
    attributes = None
    PyQt5.QtCore.qInstallMessageHandler(handler)

    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    file = None
    print("Input Arguments", sys.argv)
    if len(sys.argv) == 2:
        file = sys.argv[1]

    settings = UserSettings()
    settings.load()
    print("Settings loaded")

    app = QApplication(sys.argv)
    print("ApplicationDone")

    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    # app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    # filter = SuperFilter(app)
    # app.installEventFilter(filter)

    # if sys.platform.startswith("win"):
    #     os.environ['QT_ENABLE_HIGHDPI_SCALING'] = "1"

    print("Setting UI")
    print(os.getcwd())

    app.setWindowIcon(QIcon("qt_ui/images/main.png"))
    # set_attributes(app)
    set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css") #settings.THEME_PATH

    screen = app.desktop().screenGeometry()

    pixmap = QPixmap("qt_ui/images/loading_screen_round.png")
    pixmap = pixmap.scaled(screen.height() / 2, screen.height() / 2, transformMode=Qt.SmoothTransformation)

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.SplashScreen)
    splash.show()
    app.processEvents()

    print("Starting Up")
    main = MainWindow(splash, file)
    MAIN_WINDOW = main
    sys.exit(app.exec_())



