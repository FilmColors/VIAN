import os

import numpy as np
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton

class ColorPaletteSelector(QtWidgets.QMainWindow):
    on_selection = pyqtSignal(list)

    def __init__(self, parent, settings, is_transparent = True):
        super(ColorPaletteSelector, self).__init__(parent)
        self.is_transparent = is_transparent
        self.color_selector = ColorSelector(self, settings)
        self.color_selector.on_selection.connect(self.on_color_selection)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setCentralWidget(self.color_selector)
        self.show()

    def paintEvent(self, *args, **kwargs):
        if self.is_transparent:
            qp = QtGui.QPainter()
            pen = QtGui.QPen()
            qp.begin(self)
            qp.setPen(pen)
            qp.fillRect(self.rect(), QtGui.QColor(10,10,10,20))
            qp.end()
    def on_color_selection(self, color):
        self.on_selection.emit(color)

class ColorSelector(QtWidgets.QWidget):
    on_selection = pyqtSignal(list)
    def __init__(self, parent, settings):
        super(ColorSelector, self).__init__(parent)
        self.settings = settings
        self.setLayout(QtWidgets.QVBoxLayout(self))
        # self.titleLabel = QtWidgets.QLabel("Color Palettes", self)
        # self.layout().addWidget(self.titleLabel)
        self.color_selector_1 = ColorSelectorLine(self, settings)
        self.layout().addWidget(self.color_selector_1)
        self.color_selector_2 = ColorSelectorLine(self, settings, current_index = 1)
        self.layout().addWidget(self.color_selector_2)
        self.color_selector_1.on_selection.connect(self.selection_dispatch)
        self.color_selector_2.on_selection.connect(self.selection_dispatch)


    def selection_dispatch(self, list):
        self.on_selection.emit(list)

class ColorSelectorLine(QtWidgets.QWidget):
    on_selection = pyqtSignal(list)

    def __init__(self, parent, settings, current_index = 0):
        super(ColorSelectorLine, self).__init__(parent)
        path = os.path.abspath("qt_ui/ColorPalette.ui")
        uic.loadUi(path, self)
        self.settings = settings

        for p in settings.PALETTES:
            self.comboBox_Palette.addItem(p.palette_name)

        self.comboBox_Palette.setCurrentIndex(current_index)
        self.comboBox_Palette.currentIndexChanged.connect(self.update_palette)

        self.color_buttons = []
        self.update_palette()

    def on_color_selection(self, color):
        self.on_selection.emit(color)

    def update_palette(self):
        for b in self.color_buttons:
            b.close()
        index = self.comboBox_Palette.currentIndex()
        for c in self.settings.PALETTES[index].palette_colors:
            btn = ColorButton(self, c)
            btn.on_click.connect(self.on_color_selection)
            self.horizontalLayout_Colors.addWidget(btn)
            btn.show()
            self.color_buttons.append(btn)




class ColorButton(QPushButton):
    on_click = pyqtSignal(list)
    def __init__(self, parent, color):
        super(ColorButton, self).__init__(parent)
        self.color = color
        self.setStyleSheet("background-color: rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")")
        self.clicked.connect(self.on_clicked)

    def on_clicked(self, bool=False):
        self.on_click.emit(self.color)
