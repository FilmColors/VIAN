from functools import partial
import os
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QTableWidgetItem, QTableWidget, QHBoxLayout, QProgressBar, QScrollArea
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import IProjectChangeNotify
from core.data.computation import ms_to_string, numpy_to_qt_image
from core.data.enums import MovieSource

class ConcurrentTaskDock(EDockWidget, IProjectChangeNotify):
    onTotalProgressUpdate = pyqtSignal(float)

    def __init__(self, main_window):
        super(ConcurrentTaskDock, self).__init__(main_window)
        self.setWindowTitle("Concurrent Tasks")
        self.task_list_widget = ConcurrentTasksList(self)
        self.scroll_area = QScrollArea(self)
        self.setWidget(self.scroll_area)
        self.scroll_area.setWidget(self.task_list_widget)
        self.scroll_area.setWidgetResizable(True)
        self.show()

    @pyqtSlot(int, str, object, object)
    def add_task(self, task_id, task_name, task_object, job = None):
        self.task_list_widget.add_task(task_id, task_name, task_object, job)

    @pyqtSlot(int)
    def remove_task(self, task_id):
        self.task_list_widget.remove_task(task_id)

    @pyqtSlot(int, float)
    def update_progress(self, task_id, value_float):
        return self.task_list_widget.update_progress(task_id, value_float)


class ConcurrentTasksList(QWidget):
    def __init__(self, parent):
        super(ConcurrentTasksList, self).__init__(parent)
        path = os.path.abspath("qt_ui/ConcurrentTasksList.ui")
        uic.loadUi(path, self)
        self.task_entries = []
        self.dock = parent
        self.show()

    @pyqtSlot(int, str, object, object)
    def add_task(self, task_id, name, task_object, job):
        entry = ConcurrentTaskEntry(self,task_id, name, task_object, job)
        self.task_entries.append(entry)
        self.widget_task_list.layout().addWidget(entry)
        entry.onProgress.connect(self.update_total)

    @pyqtSlot(int)
    def remove_task(self, task_id):
        for t in self.task_entries:
            if t.task_id == task_id:
                t.close()
                t.deleteLater()
                self.task_entries.remove(t)
                break
        self.update_progress(-1,-1)

    @pyqtSlot(int, float)
    def update_progress(self,task_id, value_float):
        if len(self.task_entries) > 0:
            complete_progress = 0
            for t in self.task_entries:
                if t.task_id == task_id:
                    t.update_progress(value_float)
                complete_progress += t.progress_bar.value()
            complete_progress = int(float(complete_progress) / len(self.task_entries))

            self.progressBar_total.setValue(complete_progress)
            self.dock.onTotalProgressUpdate.emit(complete_progress)
            return complete_progress
        else:
            self.progressBar_total.setValue(0)
            self.dock.onTotalProgressUpdate.emit(0)
            return 0.0

    def update_total(self):
        if len(self.task_entries) > 0:
            complete_progress = 0
            for t in self.task_entries:
                complete_progress += t.progress_bar.value()
            complete_progress = int(float(complete_progress) / len(self.task_entries))
            self.progressBar_total.setValue(complete_progress)
            self.dock.onTotalProgressUpdate.emit(complete_progress)
            return complete_progress
        else:
            self.progressBar_total.setValue(0)
            self.dock.onTotalProgressUpdate.emit(0)
            return 0.0


class ConcurrentTaskEntry(QWidget):
    onAborted = pyqtSignal(int)
    onProgress = pyqtSignal()

    def __init__(self, parent, task_id, name, worker, job):
        super(ConcurrentTaskEntry, self).__init__(parent)
        self.task_id = task_id
        self.name = name
        self.job = job
        self.progress = 0.0
        self.task_object = worker

        self.setLayout(QHBoxLayout(self))
        self.lbl_name = QLabel(name)
        self.progress_bar = QProgressBar(self)
        self.btn_abort = QPushButton("Abort")

        if job is not None:
            self.btn_abort.clicked.connect(self.job.abort)

        self.btn_abort.clicked.connect(self.abort)

        self.layout().addWidget(self.lbl_name)
        self.layout().addWidget(self.progress_bar)
        self.layout().addWidget(self.btn_abort)

        self.show()

    def update_progress(self, float_value):
        self.progress_bar.setValue(float_value * 100)
        self.progress = float_value
        self.onProgress.emit()

    def abort(self):
        self.onAborted.emit(self.task_id)


