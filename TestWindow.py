import os
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from visualizer.vis_main_window import *
from core.visualization.dot_plot import DotPlot
# from core.gui.player_vlc import Player_Qt
from core.visualization.bar_plot import BarPlot

class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = Player_Qt(self)
        # self.t.media_player.mediaChanged.connect(self.on_change)
        self.t.media_player.stateChanged.connect(self.on_change)
        self.t.open_movie("C:\\Users\\Gaudenz Halter\\Videos\\2018-10-03 17-23-28.flv")

        # self.t.play()

        # self.addDockWidget(Qt.LeftDockWidgetArea, self.t)

        self.setCentralWidget(self.t)
        self.resize(1200, 800)


        self.show()

    def on_change(self, args):
        print("Change", args)

def set_style_sheet(app):
    style_sheet = open(os.path.abspath("qt_ui/themes/qt_stylesheet_dark.css"), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)

def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)

if __name__ == '__main__':
    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook
    app = QApplication(sys.argv)
    set_style_sheet(app)
    main = TWindow()
    sys.exit(app.exec_())

