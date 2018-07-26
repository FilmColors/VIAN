from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *
from visualizer.widgets.search_bar import *

class VisSearchLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSearchLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisSearchLayout.ui")
        self.search_widget = VisSearchBar(self, visualizer)
        self.keyword_widget = KeywordWidget(self, visualizer)
        self.hbox_SearchField.addWidget(self.search_widget)
        self.hbox_Keywords.addWidget(self.keyword_widget)


class KeywordWidget(QWidget):
    def __init__(self,parent, visualizer):
        super(KeywordWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.setLayout(QHBoxLayout(self))
        self.class_obj_list = ClassificationObjectList(self)
        self.class_obj_list.setMaximumWidth(300)
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QWidget(), "Category_1")

        self.layout().addWidget(self.class_obj_list)
        self.layout().addWidget(self.tab_widget)

class ClassificationObjectList(QListWidget):
    def __init__(self, parent):
        super(ClassificationObjectList, self).__init__(parent)
        self.addItem("Foreground")
        self.addItem("Background")
        self.addItem("Something entirely different")