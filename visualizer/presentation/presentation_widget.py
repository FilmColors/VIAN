from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

class PresentationWidget(QWidget):
    def __init__(self, parent, visualizer, path = ""):
        super(PresentationWidget, self).__init__(parent)
        self.visualizer = visualizer
        if path != "":
            path = os.path.abspath(path)
            uic.loadUi(path, self)