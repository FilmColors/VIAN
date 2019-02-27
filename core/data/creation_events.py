"""
This file contains the decorators for VIAN's 
event system. All functions decorated with the respective decorators can be used 
as within VIAN to be called once a selector is created. 
"""

from PyQt5.QtCore import QObject, pyqtSlot
import cv2

EVENT_C_SEGMENT = dict()
EVENT_C_SCREENSHOT = dict()
EVENT_C_ANNOTATION = dict()

class VIANEventHandler(QObject):
    def __init__(self, parent):
        super(VIANEventHandler, self).__init__(parent)
        self.project = None

    @pyqtSlot(object)
    def set_project(self, project):
        self.project = project

        # Hook the project to the events
        self.project.onScreenshotAdded.connect(self.run_on_screenshot_created_event)
        self.project.onAnnotationAdded.connect(self.run_on_annotation_created_event)
        self.project.onSegmentAdded.connect(self.run_segment_created_event)


    @pyqtSlot(object)
    def run_segment_created_event(self, segment):
        cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        EVENT_C_SEGMENT['default_segment_c_inform'](self.project, segment, cap)
        pass

    @pyqtSlot(object)
    def run_on_screenshot_created_event(self, screenshot):
        EVENT_C_SCREENSHOT['default_screenshot_c_inform'](self.project, screenshot, None)
        pass

    @pyqtSlot(object)
    def run_on_annotation_created_event(self):
        pass



def segment_created_event(func):
    """Register a function as a plug-in"""
    EVENT_C_SEGMENT[func.__name__] = func
    return func


def screenshot_created_event(func):
    """Register a function as a plug-in"""
    EVENT_C_SCREENSHOT[func.__name__] = func
    return func


def annotation_created_event(func):
    """Register a function as a plug-in"""
    EVENT_C_ANNOTATION[func.__name__] = func
    return func


@segment_created_event
def default_segment_c_inform(project, segment, capture):
    print("Segment Created")

@screenshot_created_event
def default_screenshot_c_inform(project, screenshot, img):
    print("Screenshot Created")

@annotation_created_event
def default_annotation_c_inform(project, annotation, sub_img):
    print("Annotation Created")