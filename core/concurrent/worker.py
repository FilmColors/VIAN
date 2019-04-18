from PyQt5.QtCore import QRunnable, QObject, Qt, QThread
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from random import randint
import traceback, sys
import cv2
from core.data.computation import numpy_to_pixmap, generate_id
from core.data.interfaces import IProjectChangeNotify

class WorkerSignals(QObject):
    sign_finished = pyqtSignal(tuple)
    sign_error = pyqtSignal(tuple)
    sign_result = pyqtSignal(object)
    sign_progress = pyqtSignal(tuple)
    sign_aborted = pyqtSignal(int)
    sign_task_manager_progress = pyqtSignal(int, float)
    sign_create_progress_bar = pyqtSignal(int, str, object, object)
    sign_remove_progress_bar = pyqtSignal(int)


class Worker(QRunnable):

    def __init__(self, function, main_window, result_cb, args = None, msg_finished = "Worker Finished", concurrent_job = None, target_id= None, i_analysis_job=None):
        super(Worker, self).__init__()
        self.message_finished = msg_finished
        self.function = function
        self.args = args
        self.concurrent_job = concurrent_job
        self.i_analysis_job = i_analysis_job
        self.setAutoDelete(True)
        self.task_id = randint(100000, 999999)
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


class WorkerManager(QObject, IProjectChangeNotify):
    onPushTask = pyqtSignal(object, object)
    onStartWorker = pyqtSignal()

    def __init__(self, main_window):
        super(WorkerManager, self).__init__()
        self.main_window = main_window
        self.project = None
        self.queue = []
        self.running = None

        self.worker = AnalysisWorker(self)
        self.execution_thread = QThread()
        self.worker.moveToThread(self.execution_thread)
        self.execution_thread.start()

        self.onPushTask.connect(self.worker.push_task)
        self.onStartWorker.connect(self.worker.run_worker)

        self.worker.signals.sign_create_progress_bar.connect(self.main_window.concurrent_task_viewer.add_task)
        self.worker.signals.sign_remove_progress_bar.connect(self.main_window.concurrent_task_viewer.remove_task)
        self.worker.signals.sign_task_manager_progress.connect(self.main_window.concurrent_task_viewer.update_progress)

    def push(self, project, analysis, targets, parameters, fps, class_objs):
        self.queue.append((analysis, (project, targets, parameters, fps, class_objs)))
        if self.running is None:
            self._start()

    def _start(self):
        if len(self.queue) > 0:
            analysis, params = self.queue.pop(0)
            self.running = analysis

            args = analysis.prepare(*params)

            if analysis.multiple_result:
                for arg in args:
                    self.onPushTask.emit(analysis, arg)
            else:
                self.onPushTask.emit(analysis, args)
            self.onStartWorker.emit()
        else:
            self.running = None

    @pyqtSlot(object)
    def on_worker_finished(self, finished_tasks):
        for task_id, result in finished_tasks.items():
            try:
                if isinstance(result, list):
                    for r in result:
                        self.running.modify_project(self.project, r, main_window=self.main_window)
                        self.project.add_analysis(r, dispatch=False)
                        r.unload_container()
                else:
                    self.running.modify_project(self.project, result, main_window=self.main_window)
                    self.project.add_analysis(result)
                    result.unload_container()
            except Exception as e:
                print("Exception in AnalysisWorker.analysis_result", str(e))

        self.project.dispatch_changed(item=self.project)
        self._start()

    def on_loaded(self, project):
        self.project = project

    @pyqtSlot(tuple)
    def on_signal_error(self, error):
        print("*********ERROR**IN**WORKER***********")
        print(error)
        print("*************************************")

    @pyqtSlot(tuple)
    def on_signal_progress(self, progress):
        print(progress)
        # total = self.concurrent_task_viewer.update_progress(progress[0], progress[1])
        # self.main_window.progress_bar.set_progress(float(total) / 100)


class AnalysisWorker(QObject):
    def __init__(self, worker_manager):
        super(AnalysisWorker, self).__init__()

        self.signals = WorkerSignals()
        self.signals.sign_progress.connect(worker_manager.on_signal_progress, Qt.AutoConnection)
        self.signals.sign_error.connect(worker_manager.on_signal_error, Qt.AutoConnection)
        self.signals.sign_result.connect(worker_manager.on_worker_finished, Qt.AutoConnection)

        self.scheduled_task = dict()
        self.finished_tasks = dict()
        self.current_task_id = 0

    @pyqtSlot(object, object)
    def push_task(self, analysis, args):
        task_id = generate_id(self.scheduled_task.keys())
        self.scheduled_task[task_id] = (task_id, analysis, args, self._on_progress)
        self.signals.sign_create_progress_bar.emit(task_id, analysis.__class__.__name__, None, None)

    @pyqtSlot()
    def run_worker(self):
        n_jobs = len(self.scheduled_task.keys())
        for i, (task_id, args) in enumerate(self.scheduled_task.items()):
            self.current_task_id = task_id
            result = self._run_task(*args)
            if result is not None:
                self.finished_tasks[task_id] = result
            self.signals.sign_remove_progress_bar.emit(task_id)
        self.signals.sign_result.emit(self.finished_tasks)

        # Clean up
        self.scheduled_task = dict()
        self.finished_tasks = dict()

    def _run_task(self, task_id, analysis, args, on_progress):
        try:
            return analysis.process(args, on_progress)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sign_error.emit((exctype, value, traceback.format_exc()))
            return None

    def _on_progress(self, float_value):
        self.signals.sign_task_manager_progress.emit(self.current_task_id, float_value)