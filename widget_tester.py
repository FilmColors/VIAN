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


# from OpenGL import GL

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *

# from core.data.settings import UserSettings
from PyQt5.Qt import PYQT_VERSION_STR

print("PyQt version:", PYQT_VERSION_STR)
DEBUG = True
MAIN_WINDOW = None



print(QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath))

class MW(QMainWindow):
    def __init__(self, widget):
        super(MW, self).__init__()
        self.central = QWidget(self)
        self.central.setLayout(QVBoxLayout())

        self.v = QWebEngineView(self)
        # self.v = QWidget();
        # self.v.load(QUrl("http://www.google.com"))
        # self.v.setStyleSheet("QWebEngineView{background-color:rgb(0,0,0); border: 10px solid black;}")
        # self.browser = QWebEngineView()
        # self.browser.load(QUrl('http://www.google.com'))
        self.lineedit = QLineEdit(self)
        self.lineedit.editingFinished.connect(self.on_change)
        self.setCentralWidget(self.central)
        self.central.layout().addWidget(self.lineedit)
        self.centralWidget().layout().addWidget(self.v)

        # self.v.show()

        # self.v.loadFinished.connect(print)
        # self.v.loadProgress.connect(print)
        print(self.v)
        self.show()

        print(self.v.isVisible())

    def on_change(self):
        t = QUrl(self.lineedit.text())
        self.v.load(t)

        # print(os.environ['QTWEBENGINEPROCESS_PATH '])
        # self.dock_widgets = []
        # self.addDockWidget(Qt.LeftDockWidgetArea, NodeEditorDock(self))

# def set_style_sheet(app, path):
#     style_sheet = open(os.path.abspath(path), 'r')
#     style_sheet = style_sheet.read()
#     app.setStyleSheet(style_sheet)
#
#
# def set_attributes(app):
#     app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#     if sys.platform == "darwin":
#         app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)

# settings = UserSettings()
# settings.load()


app = QApplication(sys.argv)
# filter = SuperFilter(app)
# app.installEventFilter(filter)
# app.setWindowIcon(QIcon("qt_ui/images/main.png"))
# set_attributes(app)
# set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css") #settings.THEME_PATH

main = MW(None)
main.show()
sys.exit(app.exec_())



