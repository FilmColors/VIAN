import cv2
import sys
import os
import glob
from sys import stdout as console
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5. QtWidgets import QApplication
from core.gui.drawing_widget import DrawingOverlay
from core.gui.timeline import TimelineContainer
from core.gui.player_moviepy import MoviePyPlayer
from core.gui.shots_window import ScreenshotsManagerWidget

class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = MoviePyPlayer(self)
        self.frame = QtWidgets.QFrame(self)
        self.setCentralWidget(self.t)
       # self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.t)
        self.resize(800,400)
        self.show()







def set_style_sheet(app):
    style_sheet = open(os.path.abspath("qt_ui/themes/qt_stylesheet_dark.css"), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    set_style_sheet(app)
    main = TWindow()
    sys.exit(app.exec_())