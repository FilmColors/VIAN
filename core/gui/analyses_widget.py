import os
from random import randint
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QTreeWidgetItem, QLineEdit, QMainWindow, QListWidget, QListWidgetItem, QHBoxLayout, QFrame, QWidget, QSizePolicy, QVBoxLayout, QSpacerItem
from PyQt5.QtGui import QFont

from core.data.computation import ms_to_string
from core.data.containers import *
from core.data.interfaces import IProjectChangeNotify, IAnalysisJob

from .ewidgetbase import EDockWidget


class AnalysesWidget(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(AnalysesWidget, self).__init__(main_window)
        path = os.path.abspath("qt_ui/AnalysesWidget.ui")
        uic.loadUi(path, self)

        self.setWidget(AnalysesContent(main_window))


class AnalysesContent(QWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(AnalysesContent, self).__init__(main_window)
        path = os.path.abspath("qt_ui/AnalysesWidget.ui")
        uic.loadUi(path, self)

        self.setWindowTitle("Analyses")
        self.main_window = main_window

        self.update_analyses_list()

        self.selected_analyse = None
        self.curr_preferences = None

        self.targets = []


        self.listWidget_Analyses.itemClicked.connect(self.on_analysis_changed)
        self.listWidget_Sources.setSelectionMode(self.listWidget_Sources.MultiSelection)

        self.btn_addSelected.clicked.connect(self.on_add_targets)
        self.btn_removeSelected.clicked.connect(self.on_remove_targets)
        self.btn_Run.clicked.connect(self.on_run)
        self.show()

    def on_run(self):
        for t in self.targets:
            args = self.selected_analyse.prepare(self.project().movie_descriptor.movie_path, t)
            self.main_window.on_start_analysis(self.selected_analyse, t.unique_id, args)
        self.targets = []
        self.update_source_list()

    def on_add_targets(self):
        if self.selected_analyse is not None:
            selected = self.project().get_selected(self.selected_analyse.source_types)
            self.targets.extend(selected)
            self.update_source_list()

    def on_remove_targets(self):
        selected = self.listWidget_Sources.selectedItems()
        for s in selected:
            self.targets.remove(s.item)
        self.update_source_list()

    def on_analysis_changed(self):
        self.selected_analyse = self.listWidget_Analyses.currentItem().analysis
        self.project().highlight_types(self.selected_analyse.source_types)
        self.update_preferences()

    def update_analyses_list(self):
        for ext in self.main_window.extension_list.analyses:
            item = AnalysesItemWidget(self.listWidget_Analyses, ext)
            self.listWidget_Analyses.addItem(item)

    def update_preferences(self):

        self.widget_parameters.layout().removeWidget(self.curr_preferences)

        self.curr_preferences = self.selected_analyse.get_preferences()
        self.widget_parameters.layout().addWidget(self.curr_preferences)

    def update_source_list(self):
        self.listWidget_Sources.clear()
        for t in self.targets:
            self.listWidget_Sources.addItem(SourceItemWidget(self.listWidget_Sources, t))

    def project(self):
        return self.parent().parent().project()


class AnalysesItemWidget(QListWidgetItem):
    def __init__(self, parent, analysis):
        super(AnalysesItemWidget, self).__init__(parent)
        self.analysis = analysis
        self.setText(analysis.name)
        self.setSizeHint(QtCore.QSize(200,50))


class SourceItemWidget(QListWidgetItem):
    def __init__(self, parent, item):
        super(SourceItemWidget, self).__init__(parent)
        self.item = item
        self.setText(item.get_name())
