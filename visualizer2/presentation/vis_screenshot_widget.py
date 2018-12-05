from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer2.presentation.presentation_widget import *
from core.visualization.palette_plot import PaletteLABView

class VisScreenshotLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisScreenshotLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisStillsLayout.ui")