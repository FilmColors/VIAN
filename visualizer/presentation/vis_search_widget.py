from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisSearchLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSearchLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisSearchLayout.ui")