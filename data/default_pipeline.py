import cv2
import numpy as np

from core.data.creation_events import segment_created_event, screenshot_created_event, annotation_created_event
from core.container.project import *



@segment_created_event
def on_segment_created(project:VIANProject, segment:Segment, capture:cv2.VideoCapture):
    print("Segment Created")

@screenshot_created_event
def on_screenshot_created(project:VIANProject, screenshot:Screenshot, img:np.ndarray):
    print("Screenshot Created")

@annotation_created_event
def on_annotation_created(project:VIANProject, annotation:Annotation, sub_img:np.ndarray):
    print("Annotation Created")