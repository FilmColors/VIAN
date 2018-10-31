import os
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from visualizer.vis_main_window import *
from core.visualization.basic_vis import HistogramVis
from core.analysis.colorimetry.hilbert import create_hilbert_transform

# CorrelationFeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "id"])
class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = HistogramVis(self)
        lookup = np.load("core/analysis/colorimetry/hilbert_lookup.npy")
        img = cv2.imread("data/test_image.png")
        img = calculate_histogram(img)

        table, colors = create_hilbert_transform(16)
        hist_lin = img[table]
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.t)
        self.t.plot(hist_lin, np.array(colors))
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

