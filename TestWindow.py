import os
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from visualizer.vis_main_window import *
from core.visualization.line_plot import LinePlot

# CorrelationFeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "id"])
class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = LinePlot(self)
        ys1 = np.random.randint(0, 10, 20)
        xs1 = list(range(20))
        ys2 = np.random.randint(0, 100, 20)
        xs2 = list(range(20))
        self.setCentralWidget(self.t)
        self.t.plot(xs1, ys1, col = QColor(255,200,200), line_name = "Bob")
        self.t.plot(xs2, ys2, col=QColor(200, 255, 200), line_name="Susanne")
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

