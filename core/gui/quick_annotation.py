import os
from random import randint
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QLineEdit, QMainWindow, QWidget
from PyQt5.QtGui import QFont, QIcon

from core.data.computation import ms_to_string
from core.data.interfaces import IProjectChangeNotify
from core.gui.context_menu import open_context_menu
from .ewidgetbase import EDockWidget

class QuickAnnotationDock(EDockWidget):
    def __init__(self, main_window):
        super(QuickAnnotationDock, self).__init__(main_window, limit_size=False)
        self.quick_annotation_widget = QuickAnnotationWidget(main_window)
        self.setWidget(self.quick_annotation_widget)


class QuickAnnotationWidget(QWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(QuickAnnotationWidget, self).__init__(main_window, width=500)
        path = os.path.abspath("qt_ui/QuickAnnotationWidget.ui")
        uic.loadUi(path, self)

