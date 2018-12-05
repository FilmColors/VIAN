from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer2.presentation.presentation_widget import *
from visualizer2.widgets.search_bar import *

class VisHeaderBar(QWidget):
    onShowPlots = pyqtSignal()

    def __init__(self, parent, visualizer):
        super(VisHeaderBar, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisHeaderBar.ui")
        uic.loadUi(path, self)

        self.visualizer = visualizer
        # self.search_bar = VisSearchBar(self, self.visualizer)
        # self.widget_SearchLineHolder.addWidget(self.search_bar)
        self.font = QFont()
        self.font.setPointSize(18)
        self.lbl_Layer.setFont(self.font)
        self.btn_Plots.clicked.connect(self.onShowPlots.emit)

    def set_header_name(self, text):
        self.lbl_Layer.setText(text)
        self.lbl_Layer.setFont(self.font)
