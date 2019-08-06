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



abspath = os.path.abspath(sys.executable)
dname = os.path.dirname(abspath)
# os.chdir(dname)
# print(dname)
# print(os.getcwd())

import logging
logging.getLogger('tensorfyylow').disabled = True


import PyQt5
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox, QMainWindow
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QPixmap, QIcon


from core.data.settings import UserSettings
from core.gui.drop_image_container import DropImageContainer
DEBUG = True
MAIN_WINDOW = None


class MW(QMainWindow):
    def __init__(self, widget):
        super(MW, self).__init__()
        self.setCentralWidget(widget)

def set_style_sheet(app, path):
    style_sheet = open(os.path.abspath(path), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


def set_attributes(app):
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if sys.platform == "darwin":
        app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)




settings = UserSettings()
settings.load()


app = QApplication(sys.argv)
# filter = SuperFilter(app)
# app.installEventFilter(filter)
app.setWindowIcon(QIcon("qt_ui/images/main.png"))
set_attributes(app)
set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css") #settings.THEME_PATH

main = MW(DropImageContainer(None))
main.show()
sys.exit(app.exec_())



