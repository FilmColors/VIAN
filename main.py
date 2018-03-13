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

import core.vlc.vlc as vlc
from core.data.settings import UserSettings
from core.gui.main_window import MainWindow





#TODO DEBUG needs to be fixed, start in non debug does not work currently
DEBUG = True

class MainThread(Thread):
    def __init__(self, vlc_media_player, vlc_instance, server):
        Thread.__init__(self)
        self.vlc_instance = vlc_instance
        self.vlc_media_player = vlc_media_player
        self.qt_server = server
        self.style_sheet_path = "qt_ui/themes/qt_stylesheet_dark.css"

    def run(self):
        if __name__ == '__main__':

            app = QApplication(sys.argv)
            self.set_style_sheet(app)
            main = MainWindow(self.vlc_instance, self.vlc_media_player, self.qt_server)

            sys.exit(app.exec_())

    def set_style_sheet(self, app):
        style_sheet = open(os.path.abspath(self.style_sheet_path), 'r')
        style_sheet = style_sheet.read()
        app.setStyleSheet(style_sheet)


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


    if not DEBUG:
        try:
            sys._excepthook = sys.excepthook
            sys.excepthook = my_exception_hook

            settings = UserSettings()
            settings.load()

            app = QApplication(sys.argv)
            set_attributes(app)
            set_style_sheet(app, settings.THEME_PATH)
            main = MainWindow()
            main.run()
            sys.exit(app.exec_())

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            time =datetime.now()
            path = settings.DIR_PROJECT + "error_log_" + str(time.year) + "_" + str(time.day) + "_" + str(time.hour) + ".txt"

            system_info = [platform.system(), platform.version(), platform.machine(), platform.processor(),"","PYTHON", platform.python_version()]
            with open(path, "w") as log_file:
                log_file.write("\nELAN EXTENSION ERROR LOG FILE: \n\n")

                log_file.write("\nERROR TIME OCCURRED: ")
                log_file.write(time.ctime())

                log_file.write("\nERROR MESSAGE: ")
                log_file.writelines(str(e) + "\n")
                tb = traceback.extract_tb(exc_traceback)

                log_file.write("\nERROR STACK TRACE \n")
                for l in tb:
                    log_file.write(str(l) + "\n")
                # log_file.writelines(str(traceback.print_exception(exc_type, exc_value, exc_traceback,
                #                   limit=2, file=sys.stdout)))

                log_file.write("\nSYSTEM INFO \n")
                for s in system_info:
                    log_file.write(str(s) + "\n")

            with open(path, "r") as log_file:
                for l in log_file:
                    print(l.replace("\n", ""))
    else:
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
        sys.exit(app.exec_())



