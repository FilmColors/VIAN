#!bin/bash
"""
VIAN - Visual Movie SVGAnnotation and Analysis


copyright by pip
Gaudenz Halter
University of Zurich
2017

Visualization and MultimediaLab 

"""

import os

# Comment this out for the full VIAN Version
# os.environ['VIAN_LIGHT'] = "1"

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from vian.core.paths import get_root_dir

application_path = get_root_dir()
os.chdir(application_path)

import time
import logging
import traceback as tb
import subprocess

import PyQt5
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QPixmap, QIcon
from vian.core.data.settings import CONFIG

from vian.core.data.settings import UserSettings
from vian.core.gui.main_window import MainWindow, version
from vian.core.data.computation import is_gui

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["QT_MAC_WANTS_LAYER"] = "1"
os.environ["VIAN_GUI"] = "1"

print("IS GUI", is_gui())
from datetime import datetime
from threading import Thread

from vian.core.hidden_imports import *

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
print("Directory", dname)

# Check if we are in a pyinstaller release
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)

logging.getLogger('tensorfyylow').disabled = True

MAIN_WINDOW = None


def vian_exception_hook(exctype, value, traceback):
    """
    This function is called whenever a critical exception is thrown by the application.
    If debug, we let VIAN crash and raise the Exception.
    When in release mode, we write the exception to a log, and continue with a warning.

    :param exctype:
    :param value:
    :param traceback:
    :return:
    """
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    if CONFIG["dev_mode"]:
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


if __name__ == '__main__':
    attributes = None
    PyQt5.QtCore.qInstallMessageHandler(handler)

    sys._excepthook = sys.excepthook
    sys.excepthook = vian_exception_hook

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
    app.setAttribute(Qt.AA_EnableHighDpiScaling)

    print("Setting UI")
    print(os.getcwd())

    app.setWindowIcon(QIcon("qt_ui/images/main.png"))
    set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css")

    # Splash Screen during loading
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



