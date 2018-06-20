from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisHomeWidget(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisHomeWidget, self).__init__(parent, visualizer, "qt_ui/visualizer/VisStartLayout.ui")
