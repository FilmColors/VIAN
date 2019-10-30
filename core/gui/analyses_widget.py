import os
from random import randint
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QTreeWidgetItem, QLineEdit, QMainWindow, QListWidget, QListWidgetItem, QHBoxLayout, QFrame, QWidget, QSizePolicy, QVBoxLayout, QSpacerItem
from PyQt5.QtGui import QFont

from core.data.computation import ms_to_string
from core.container.project import MOVIE_DESCRIPTOR
from core.data.interfaces import IProjectChangeNotify, IAnalysisJob
from core.data.enums import get_type_as_string
from .ewidgetbase import EDockWidget, EDialogWidget


class AnalysisDialog(EDialogWidget):
    onAnalyse = pyqtSignal(dict)

    def __init__(self, main_window, analysis, selected):
        super(AnalysisDialog, self).__init__(main_window, main_window, analysis.help_path)
        path = os.path.abspath("qt_ui/DialogAnalysis.ui")
        uic.loadUi(path, self)

        # self.list_Targets = QListWidget()
        if len(selected) == 0 and MOVIE_DESCRIPTOR in analysis.source_types and main_window.project is not None:
            selected = [main_window.project.movie_descriptor]
        self.targets = selected
        self.analysis = analysis
        self.param_widget = self.analysis.get_parameter_widget()
        self.widget_Parameters.layout().addWidget(self.param_widget)
        
        self.update_list()
        self.all_classification_objects = dict()
        self.all_classification_objects['Default'] = None
        self.comboBox_ClObj.addItem("Default")
        for e in main_window.project.experiments:
            for cl_obj in e.get_classification_objects_plain():
                self.all_classification_objects[e.name + ":" + cl_obj.name] = cl_obj
                self.comboBox_ClObj.addItem(e.name + ":" + cl_obj.name)

        self.btn_AddTarget.clicked.connect(self.add_selection)
        self.btn_RemoveTarget.clicked.connect(self.remove_selected)
        self.btn_Analyse.clicked.connect(self.on_analyse)
        self.btn_Cancel.clicked.connect(self.on_cancel)

        self.lbl_AnalysisName.setText(self.analysis.name)
        self.lbl_Author.setText(self.analysis.author)
        self.lbl_Version.setText(self.analysis.version)
        self.setWindowTitle("Analysis: " + self.analysis.name)

    def remove_selected(self):
        selected = self.list_Targets.selectedItems()
        for s in selected:
            for t in self.targets:
                if t is s.item:
                    self.targets.remove(t)
                    break
        self.update_list()

    def add_selection(self):
        targets = []
        for sel in self.main_window.project.selected:
            if sel.get_type() in self.analysis.source_types and sel not in self.targets:
                targets.append(sel)

        self.targets.extend(targets)
        self.update_list()

    def update_list(self):
        self.list_Targets.clear()
        for sel in self.targets:
            self.list_Targets.addItem(SelectedItem(sel))

    def on_analyse(self):
        parameters = self.param_widget.get_parameters()
        message = dict(
            analysis = self.analysis,
            targets = self.targets,
            parameters = parameters,
            classification_objs = self.all_classification_objects[self.comboBox_ClObj.currentText()]
        )
        self.onAnalyse.emit(message)
        self.close()

    def on_cancel(self):
        self.close()


class SelectedItem(QListWidgetItem):
    def __init__(self, item):
        super(SelectedItem, self).__init__()
        self.item = item
        self.setText(item.get_name().ljust(30) + "[" + get_type_as_string(self.item.get_type()) + "]")