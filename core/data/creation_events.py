"""
This file contains the decorators for VIAN's 
event system. All functions decorated with the respective decorators can be used 
as within VIAN to be called once a selector is created. 
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from core.container.project import VIANProject, Segment, Annotation, Screenshot
import traceback
import cv2
import inspect

ALL_REGISTERED_PIPELINES = dict()

class VIANEventHandler(QObject):
    onException = pyqtSignal(str)

    def __init__(self, parent):
        super(VIANEventHandler, self).__init__(parent)
        self.main_window = parent
        self.project = None                 # type: VIANProject
        self.current_pipeline = None        # type: VIANPipeline

        self.comp_segments = False
        self.comp_screenshots = False
        self.comp_annotations = False

    @pyqtSlot(object)
    def set_project(self, project):
        self.project = project

        # Hook the project to the events
        self.project.onScreenshotAdded.connect(self.run_on_screenshot_created_event)
        self.project.onAnnotationAdded.connect(self.run_on_annotation_created_event)
        self.project.onSegmentAdded.connect(self.run_segment_created_event)

    @pyqtSlot(bool, bool, bool)
    def to_compute_changed(self, comp_segments, comp_screenshots, comp_annotations):
        self.comp_segments = comp_segments
        self.comp_screenshots = comp_screenshots
        self.comp_annotations = comp_annotations

    def set_current_pipeline(self, name):
        try:
            self.current_pipeline = ALL_REGISTERED_PIPELINES[name][0]()
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot(object)
    def run_segment_created_event(self, segment):
        if self.comp_segments is False:
            return
        try:
            cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
            if self.current_pipeline is not None:
                self.current_pipeline.on_segment_created(self.project, segment, cap)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot(object)
    def run_on_screenshot_created_event(self, screenshot):
        if self.comp_screenshots is False:
            return
        try:
            if self.current_pipeline is not None:
                self.current_pipeline.on_screenshot_created(self.project, screenshot)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot(object)
    def run_on_annotation_created_event(self, annotation):
        if self.comp_annotations is False:
            return
        try:
            if self.current_pipeline is not None:
                self.current_pipeline.on_screenshot_created(self.project, annotation)
        except Exception as e:
            self.onException.emit(traceback.format_exc())

    @pyqtSlot()
    def run_on_finalize_event(self):
        try:
            if self.current_pipeline is not None:
                self.current_pipeline.on_project_finalized(self.project)
        except Exception as e:
            self.onException.emit(traceback.format_exc())


def vian_pipeline(cl):
    """Register a class as a plug-in"""
    ALL_REGISTERED_PIPELINES[cl.name] = (cl, inspect.getfile(cl))
    return cl

def get_path_of_pipeline_script(name):
    if name in ALL_REGISTERED_PIPELINES:
        return ALL_REGISTERED_PIPELINES[name][1]
    else:
        return None

def get_name_of_script_by_path(spath):
    for name, (module, path) in ALL_REGISTERED_PIPELINES.items():
        if path == spath:
            return name
    return None

class VIANPipeline:
    name = "NoName"
    author = "NoAuthor"
    version = (0,0,0)
    requirements = dict(segment_analyses=[],
                        screenshot_analyses=[],
                        annotation_analyses=[]
                        )
    finished_threshold = 0.95

    def on_segment_created(self, project:VIANProject, segment:Segment, capture):
        pass

    def on_screenshot_created(self, project:VIANProject, screenshot:Screenshot):
        pass

    def on_svg_annotation_created(self, project:VIANProject, annotation:Annotation, sub_img):
        pass

    def on_project_finalized(self, project:VIANProject):
        pass

