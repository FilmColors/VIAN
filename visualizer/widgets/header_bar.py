from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *
from visualizer.widgets.search_bar import *

class VisHeaderBar(QWidget):
    def __init__(self, parent, visualizer):
        super(VisHeaderBar, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisHeaderBar.ui")
        uic.loadUi(path, self)

        self.visualizer = visualizer
        self.search_bar = VisSearchBar(self, self.visualizer)
        self.widget_SearchLineHolder.addWidget(self.search_bar)