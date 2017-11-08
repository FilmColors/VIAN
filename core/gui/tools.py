
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFrame
from PyQt5.QtCore import pyqtSignal

from core.gui.ewidgetbase import EDialogWidget


class ColorPicker(QFrame):
    colorChanged = pyqtSignal(tuple)
    def __init__(self, parent):
        super(ColorPicker, self).__init__(parent)
        path = os.path.abspath("qt_ui/ColorPicker.ui")
        uic.loadUi(path, self)

        self.chosen_color = (255,255,255)

        self.btn_Col1.clicked.connect(self.on_click1)
        self.btn_Col2.clicked.connect(self.on_click2)
        self.btn_Col3.clicked.connect(self.on_click3)
        self.btn_Col4.clicked.connect(self.on_click4)
        self.btn_Col5.clicked.connect(self.on_click5)
        self.btn_Col6.clicked.connect(self.on_click6)
        self.btn_Col7.clicked.connect(self.on_click7)
        self.btn_Col8.clicked.connect(self.on_click8)
        self.btn_Col9.clicked.connect(self.on_click9)

    def color(self):
        return self.chosen_color

    def on_click1(self):
        self.chosen_color = (255, 204, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click2(self):
        self.chosen_color = (255, 102, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click3(self):
        self.chosen_color = (255, 0, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click4(self):
        self.chosen_color = (0, 170, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click5(self):
        self.chosen_color = (6, 122, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click6(self):
        self.chosen_color = (0, 85, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click7(self):
        self.chosen_color = (85, 0, 255)
        self.colorChanged.emit(self.chosen_color)

    def on_click8(self):
        self.chosen_color = (85, 170, 255)
        self.colorChanged.emit(self.chosen_color)

    def on_click9(self):
        self.chosen_color = (255, 85, 255)
        self.colorChanged.emit(self.chosen_color)


class DialogPrompt(EDialogWidget):
    def __init__(self, parent, text):
        super(DialogPrompt, self).__init__(parent)
        path = os.path.abspath("qt_ui/DialogPrompt.ui")
        uic.loadUi(path, self)
        self.label.setText(text)
        self.show()

