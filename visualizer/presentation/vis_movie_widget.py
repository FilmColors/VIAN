from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisMovieLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisMovieLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisMovieLayout.ui")