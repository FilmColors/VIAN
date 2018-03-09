import sys
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication

import pyqtgraph as pg
from core.visualization.feature_plot import GenericFeaturePlot, SegmentTuple, FeatureTuple
from extensions.plugins.fiwi_tools.fiwi_visualizer.visualizer import FiwiVisualizer

class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = GenericFeaturePlot(self)
        self.frame = QtWidgets.QFrame(self)
        self.setCentralWidget(self.t)

        segments = [SegmentTuple(0,0,10000), SegmentTuple(1,10000,30000), SegmentTuple(2,30000,60000), SegmentTuple(3,60000,80000), SegmentTuple(4,80000,120000)]
        feature_a = FeatureTuple("Children", [0,2])
        feature_b = FeatureTuple("Something very Oddly Long", [0,1,4])
        feature_c = FeatureTuple("Something very Oddly Long", [0,2, 3, 4])

        self.t.create_timeline(segments)
        self.t.create_feature(feature_a)
        self.t.create_feature(feature_b)
        self.t.create_feature(feature_c)
        self.resize(1200, 800)


        self.show()

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
    main = FiwiVisualizer(None, None)
    sys.exit(app.exec_())

