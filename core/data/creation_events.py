"""
This file contains the decorators for VIAN's 
event system. All functions decorated with the respective decorators can be used 
as within VIAN to be called once a selector is created. 
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from core.container.project import VIANProject
import traceback
import cv2

ALL_REGISTERED_PIPELINES = dict()

class VIANEventHandler(QObject):
    onException = pyqtSignal(str)

    def __init__(self, parent):
        super(VIANEventHandler, self).__init__(parent)
        self.main_window = parent
        self.project = None                 # type: VIANProject
        self.current_pipeline = None        # type: VIANPipeline

    @pyqtSlot(object)
    def set_project(self, project):
        self.project = project

        # Hook the project to the events
        self.project.onScreenshotAdded.connect(self.run_on_screenshot_created_event)
        self.project.onAnnotationAdded.connect(self.run_on_annotation_created_event)
        self.project.onSegmentAdded.connect(self.run_segment_created_event)


    @pyqtSlot(object)
    def run_segment_created_event(self, segment):
        try:
            cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
            if self.current_pipeline is not None:
                self.current_pipeline.on_segment_created(self.project, segment, cap)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot(object)
    def run_on_screenshot_created_event(self, screenshot):
        try:
            if self.current_pipeline is not None:
                self.current_pipeline.on_screenshot_created(self.project, screenshot)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot(object)
    def run_on_annotation_created_event(self, annotation):
        try:
            if self.current_pipeline is not None:
                self.current_pipeline.on_screenshot_created(self.project, annotation)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

def vian_pipeline(cl):
    """Register a function as a plug-in"""
    ALL_REGISTERED_PIPELINES[cl.name] = cl
    return cl

class VIANPipeline:
    name = "NoName"
    author = "NoAuthor"
    version = (0,0,0)

    def on_segment_created(self, project, segment, capture):
        pass

    def on_screenshot_created(self, project, screenshot):
        pass

    def on_svg_annotation_created(self, project, annotation, sub_img):
        pass

    def on_project_finalized(self, project):
        pass