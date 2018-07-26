from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.presentation_widget import *
from visualizer.widgets.search_bar import *
from core.corpus.shared.entities import *
class VisSearchLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSearchLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisSearchLayout.ui")
        self.search_widget = VisSearchBar(self, visualizer)
        self.keyword_widget = KeywordWidget(self, visualizer)
        self.hbox_SearchField.addWidget(self.search_widget)
        self.hbox_Keywords.addWidget(self.keyword_widget)

    def on_query_result(self, obj):
        if obj['type'] == "keywords":
            print(obj)

class KeywordWidget(QWidget):
    def __init__(self,parent, visualizer):
        super(KeywordWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.setLayout(QHBoxLayout(self))
        self.class_obj_list = ClassificationObjectList(self)
        self.class_obj_list.setMaximumWidth(300)
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QWidget(), "Category_1")

        self.tabs_map = dict()
        self.layout().addWidget(self.class_obj_list)
        self.layout().addWidget(self.tab_widget)

    def add_unique_keyword(self, ukw:DBUniqueKeyword, cl_obj:DBClassificationObject, voc:DBVocabulary, voc_word:DBVocabularyWord):
        pass
        # if cl_obj.name not in self.tabs_map:
        #     stack = QWidget()
        #     self.tabs_map[]
        # if voc.category not in self.tabs_map:
        #     tab = QWidget(self.tab_widget)
        #     self.tab_widget.addTab(tab, voc.category)
        #     tab[voc.category] =

class ClassificationObjectList(QListWidget):
    def __init__(self, parent):
        super(ClassificationObjectList, self).__init__(parent)