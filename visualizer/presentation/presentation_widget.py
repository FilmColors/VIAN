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
        self.visualizer.query_worker.signals.onQueryResult.connect(self.on_query_result)

    @pyqtSlot(object)
    def on_query_result(self, obj):
        pass