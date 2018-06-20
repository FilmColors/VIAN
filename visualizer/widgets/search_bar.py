from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisSearchBar(QWidget):
    def __init__(self, parent, visualizer):
        super(VisSearchBar, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisSearchBar.ui")
        uic.loadUi(path, self)

        self.visualizer = visualizer

