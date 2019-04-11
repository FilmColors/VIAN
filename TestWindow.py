import os
import os
import sys
import numpy as np

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from core.visualization2.basic_vis import VIANPlotBase, DotPlot

# CorrelationFeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "id"])
class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.w = QWidget(self)
        self.w.setLayout(QVBoxLayout())
        self.t = DotPlot(self)
        self.w.layout().addWidget(self.t)

        for i in range(100):
            q = np.random.randint(0,100,2)
            self.t.add_dot(q[0], q[1])
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

