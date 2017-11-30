from PyQt5.QtCore import QRunnable, QObject, Qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from random import randint
import traceback, sys


class WorkerSignals(QObject):
    sign_finished = pyqtSignal(tuple)
    sign_error = pyqtSignal(tuple)
    sign_result = pyqtSignal(object)
    sign_progress = pyqtSignal(tuple)

class Worker(QRunnable):

    def __init__(self, function, main_window, result_cb, args = None, msg_finished = "Worker Finished", concurrent_job = None, target_id= None):
        super(Worker, self).__init__()
        self.message_finished = msg_finished
        self.function = function
        self.args = args
        self.concurrent_job = concurrent_job
        self.setAutoDelete(True)
        self.task_id = randint(100000,999999)
        self.target_id = target_id

        self.signals = WorkerSignals()
        self.signals.sign_progress.connect(main_window.worker_progress,Qt.AutoConnection)
        self.signals.sign_error.connect(main_window.worker_error,Qt.AutoConnection)
        self.signals.sign_finished.connect(main_window.worker_finished,Qt.AutoConnection)
        if result_cb is not None:
            self.signals.sign_result.connect(result_cb, Qt.AutoConnection)

    @pyqtSlot()
    def run(self):
        try:
            if self.target_id:
                if self.args is None:
                    result = self.function(self.target_id, self.on_progress)
                else:
                    result = self.function(self.target_id, self.args, self.on_progress)
            else:
                if self.args is None:
                    result = self.function(self.on_progress)
                else:
                    result = self.function(self.args, self.on_progress)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sign_error.emit((exctype, value, traceback.format_exc()))
        else:
            if self.concurrent_job is None:
                self.signals.sign_result.emit(result)  # Return the result of the processing
            else:
                self.signals.sign_result.emit([result, self.concurrent_job])
        finally:

            self.signals.sign_finished.emit((self.task_id, self.message_finished))  # Done

    def on_progress(self, float_value):
        self.signals.sign_progress.emit((self.task_id, float_value))

class ProjectModifierSignals(QObject):
    sign_progress = pyqtSignal(int)

class ProjectModifier(QRunnable):
    def __init__(self, function, worker_result, main_window, project, progress_popup = None):
        super(ProjectModifier, self).__init__()
        self.project = project
        self.main_window = main_window
        self.function = function
        self.worker_result = worker_result

        self.signals = ProjectModifierSignals()

        if progress_popup:
            self.signals.sign_progress.connect(progress_popup.on_progress, Qt.AutoConnection)

    @pyqtSlot()
    def run(self):
        try:
           self.function(self.project, self.worker_result, self.on_progress)

        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            print exctype, value, traceback.format_exc()

    def on_progress(self, int_value):
        self.signals.sign_progress.emit(int_value)


class CurrentSegmentEvaluaterSignals(QObject):
    segmentChanged = pyqtSignal(int)

class CurrentSegmentEvaluater(QRunnable):
    def __init__(self):
        super(CurrentSegmentEvaluater, self).__init__()
        self.running = False
        self.aborted = False
        self.current_segment = -1
        self.time = -1
        self.segments = None
        self.signals = CurrentSegmentEvaluaterSignals()


    @pyqtSlot()
    def run(self):
        while not self.aborted:
            if self.running and self.segments is not None:
                for i, s in enumerate(self.segments):
                    if s[0] <= self.time < s[1]:
                        if i != self.current_segment:
                            self.current_segment = i
                            self.signals.segmentChanged.emit(self.current_segment)

    @pyqtSlot()
    def pause(self):
        self.running = False

    @pyqtSlot()
    def play(self):
        self.running = True

    @pyqtSlot(long)
    def set_time(self, time):
        self.time = time

    @pyqtSlot(list)
    def set_segments(self, segments):
        self.segments = segments