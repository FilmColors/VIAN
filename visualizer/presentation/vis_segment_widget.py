from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisSegmentLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSegmentLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisSegmentsLayout.ui")