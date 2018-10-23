import os
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from visualizer.vis_main_window import *
from core.visualization.dot_plot import DotPlot
from core.visualization.basic_vis import MatrixPlot
from core.visualization.bar_plot import BarPlot
from core.visualization.correlation_matrix import CorrelationVisualization, CorrelationFeatureTuple

# CorrelationFeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "id"])
class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = CorrelationVisualization(self)
        m = np.array(
            [[0.2,0.5,0.3],
             [0.4,0.8,0.9],
             [0.5,0.4,0.2]]
        )
        features = [
            CorrelationFeatureTuple("alpha", "c", "g", 0),
            CorrelationFeatureTuple("beta", "c", "g", 1),
            CorrelationFeatureTuple("gamma", "c", "g", 2)
        ]

        self.t.set_data(features, m)

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

