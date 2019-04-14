from core.gui.ewidgetbase import EDockWidget
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import Qt
from core.data.interfaces import IProjectChangeNotify
import os
from core.gui.python_script_editor import PythonScriptEditor
from core.data.creation_events import VIANEventHandler, ALL_REGISTERED_PIPELINES

class PipelineDock(EDockWidget):
    def __init__(self, parent, event_manager):
        super(PipelineDock, self).__init__(parent, False)
        self.setWindowTitle("Pipeline Manager")
        self.pipeline = PipelineWidget(self, event_manager)
        self.inner.setCentralWidget(QSplitter(Qt.Horizontal))
        self.inner.centralWidget().setLayout(QHBoxLayout())

        #self.setWidget(self.inner)
        self.inner.centralWidget().addWidget(self.pipeline)
        self.editor = PythonScriptEditor(self.inner.centralWidget())
        self.inner.centralWidget().layout().addWidget(self.editor)




class PipelineWidget(QWidget):
    def __init__(self, parent, event_manager: VIANEventHandler):
        super(PipelineWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/PipelineWidget.ui")
        uic.loadUi(path, self)

        self.btn_onSegment.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}")
        self.btn_onScreenshot.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}")
        self.btn_onAnnotation.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}")

        self.event_manager = event_manager
        self.on_reload_scripts()

    def on_reload_scripts(self):
        self.listWidget_Pipelines.clear()
#        self.listWidget_Pipelines = QListWidget()
        for pipeline in ALL_REGISTERED_PIPELINES.keys():
            self.listWidget_Pipelines.addItem(pipeline)