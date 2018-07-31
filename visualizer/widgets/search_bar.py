from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *

class VisSearchBar(QWidget):
    onQuery = pyqtSignal(str, str, int)

    def __init__(self, parent, visualizer):
        super(VisSearchBar, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisSearchBar.ui")
        uic.loadUi(path, self)

        self.visualizer = visualizer
        self.btn_Search.clicked.connect(self.on_query_clicked)

    def on_query_clicked(self):
        t = self.comboBox_Type.currentText().lower()

        self.onQuery.emit(t, self.lineEdit_Query.text(), self.comboBox_Corpus.currentIndex())