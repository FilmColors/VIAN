from PyQt5.QtCore import QRunnable, QObject, Qt, QThread
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from random import randint
import traceback, sys
import cv2
from core.data.computation import numpy_to_pixmap

class WorkerSignals(QObject):
    sign_finished = pyqtSignal(tuple)
    sign_error = pyqtSignal(tuple)
    sign_result = pyqtSignal(object)
    sign_progress = pyqtSignal(tuple)
    sign_aborted = pyqtSignal(int)


class Worker(QRunnable):

    def __init__(self, function, main_window, result_cb, args = None, msg_finished = "Worker Finished", concurrent_job = None, target_id= None, i_analysis_job=None):
        super(Worker, self).__init__()
        self.message_finished = msg_finished
        self.function = function
        self.args = args
        self.concurrent_job = concurrent_job
        self.i_analysis_job = i_analysis_job
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
            if result == "aborted":
                self.signals.sign_aborted.emit(self.task_id)

            elif self.concurrent_job is None and self.i_analysis_job is None:
                self.signals.sign_result.emit(result)  # Return the result of the processing
            elif self.i_analysis_job is not None:
                self.signals.sign_result.emit([result, self.i_analysis_job])
            else:
                self.signals.sign_result.emit([result, self.concurrent_job])
        finally:

            self.signals.sign_finished.emit((self.task_id, self.message_finished))  # Done

    def on_progress(self, float_value):
        self.signals.sign_progress.emit((self.task_id, float_value))


# class ProjectModifierSignals(QObject):
#     sign_progress = pyqtSignal(int)
#
#
# class ProjectModifier(QRunnable):
#     def __init__(self, function, worker_result, main_window, project, progress_popup = None):
#         super(ProjectModifier, self).__init__()
#         self.project = project
#         self.main_window = main_window
#         self.function = function
#         self.worker_result = worker_result
#
#         self.signals = ProjectModifierSignals()
#
#         if progress_popup:
#             self.signals.sign_progress.connect(progress_popup.on_progress, Qt.AutoConnection)
#
#     @pyqtSlot()
#     def run(self):
#         try:
#            self.function(self.project, self.worker_result, self.on_progress)
#
#         except:
#             traceback.print_exc()
#             exctype, value = sys.exc_info()[:2]
#             print(exctype, value, traceback.format_exc())
#
#     def on_progress(self, int_value):
#         self.signals.sign_progress.emit(int_value)


# class CurrentSegmentEvaluaterSignals(QObject):
#     segmentChanged = pyqtSignal(int)
#
#
# class CurrentSegmentEvaluater(QRunnable):
#     def __init__(self):
#         super(CurrentSegmentEvaluater, self).__init__()
#         self.running = False
#         self.aborted = False
#         self.current_segment = -1
#         self.time = -1
#         self.segments = None
#         self.signals = CurrentSegmentEvaluaterSignals()
#
#
#     @pyqtSlot()
#     def run(self):
#         while not self.aborted:
#             if self.running and self.segments is not None:
#                 for i, s in enumerate(self.segments):
#                     if s[0] <= self.time < s[1]:
#                         if i != self.current_segment:
#                             self.current_segment = i
#                             self.signals.segmentChanged.emit(self.current_segment)
#
#     @pyqtSlot()
#     def pause(self):
#         self.running = False
#
#     @pyqtSlot()
#     def play(self):
#         self.running = True
#
#     @pyqtSlot(int)
#     def set_time(self, time):
#         self.time = time
#
#     @pyqtSlot(list)
#     def set_segments(self, segments):
#         self.segments = segments

class MinimalWorkerSignals(QObject):
    finished = pyqtSignal(object)
    callback = pyqtSignal(object)
    error = pyqtSignal(str)


class MinimalThreadWorker(QRunnable):
    def __init__(self, func, args = None, use_callback = False):
        super(MinimalThreadWorker, self).__init__()
        self.function = func
        self.args = args
        self.use_callback = use_callback
        self.signals = MinimalWorkerSignals()
        self.aborted = False

    @pyqtSlot()
    def run(self):
        try:
            if self.use_callback:
                if self.args is None:
                    result = self.function(self.signals.callback)
                    self.signals.finished.emit(result)
                else:
                    result = self.function(self.args, self.signals.callback)
                    self.signals.finished.emit(result)
            else:
                if self.args is None:
                    result = self.function()
                    self.signals.finished.emit(result)
                else:
                    result = self.function(self.args)
                    self.signals.finished.emit(result)
        except Exception as e:
            raise e
            self.signals.error.emit(e)

    @pyqtSlot()
    def abort(self):
        self.aborted = True

class LiveWidgetThreadWorker(MinimalThreadWorker):
    def __init__(self, frame, data, func):
        super(LiveWidgetThreadWorker, self).__init__(func)
        self.frame = frame
        self.data = data

    def process(self):
        try:
            result = self.function(self.frame, self.data)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)


class ImageLoaderThreadWorker(MinimalThreadWorker):
    def __init__(self, paths, callback):
        super(ImageLoaderThreadWorker, self).__init__(None)
        self.paths = paths
        print(self.paths)
        self.cb_func = callback

    @pyqtSlot()
    def process(self):
        try:
            for i, p in enumerate(self.paths):
                try:
                    print(i)
                    img = cv2.imread(p)
                    # qpixmap = numpy_to_pixmap(img, cvt=None)
                    self.callback.emit([i, img])
                except Exception as e:
                    print(e)
                    continue

        except Exception as e:
            print(e)
            self.error.emit(e)


class SimpleWorker(QRunnable):

    def __init__(self, function, result_cb, sign_progress, sign_error = None, args = None):
        super(SimpleWorker, self).__init__()
        self.function = function
        self.args = args
        self.setAutoDelete(True)
        self.task_id = randint(100000,999999)
        self.result_cb = result_cb
        self.signals = WorkerSignals()
        self.signals.sign_progress.connect(sign_progress, Qt.AutoConnection)

        if sign_error is not None:
            self.signals.sign_error.connect(sign_error, Qt.AutoConnection)

        if result_cb is not None:
            self.signals.sign_result.connect(result_cb, Qt.AutoConnection)

    @pyqtSlot()
    def run(self):
        try:
            if self.args is None:
                result = self.function(self.on_progress)
            else:
                result = self.function(self.args, self.on_progress)

            if result == "aborted":
                self.signals.sign_aborted.emit(self.task_id)

            if self.result_cb is not None:
                self.signals.sign_result.emit(result)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sign_error.emit((exctype, value, traceback.format_exc()))
        finally:

            self.signals.sign_finished.emit((self.task_id, "Finished"))  # Done

    def on_progress(self, float_value):
        self.signals.sign_progress.emit((float_value * 100, 0))


#
# class YieldingWorkerSignals(QObject):
#     sign_finished = pyqtSignal(tuple)
#     sign_error = pyqtSignal(tuple)
#     sign_progress = pyqtSignal(tuple)
#     sign_yield = pyqtSignal(object)
#     sign_aborted = pyqtSignal(int)
#
#
# class YieldingWorker():
#     def __init__(self):
#         self.signals = YieldingWorkerSignals()
#



def run_minimal_worker(worker: MinimalThreadWorker, finish_func = None):
    thread = QThread()
    worker.moveToThread(thread)
    if finish_func is not None:
        worker.finished.connect(finish_func)
    thread.start()
    worker.process()
    return thread