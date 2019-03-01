import cv2
import numpy as np

from core.data.creation_events import segment_created_event, screenshot_created_event, annotation_created_event
from core.container.project import *



@segment_created_event
def default_segment_c_inform(project:VIANProject, segment:Segment, capture:cv2.VideoCapture):
    print("Segment Created")

@screenshot_created_event
def default_screenshot_c_inform(project:VIANProject, screenshot:Screenshot, img:np.ndarray):
    print("Screenshot Created")

@annotation_created_event
def default_annotation_c_inform(project:VIANProject, annotation:Annotation, sub_img:np.ndarray):
    print("Annotation Created")