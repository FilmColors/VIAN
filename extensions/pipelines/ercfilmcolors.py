import cv2
import numpy as np

from core.data.creation_events import segment_created_event, screenshot_created_event, annotation_created_event
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis



@segment_created_event
def on_segment_created(project:VIANProject, segment:Segment, capture:cv2.VideoCapture):
    run_analysis(project, ColorHistogramAnalysis(), [segment], dict(resolution=30),
                 [project.experiments[0].get_classification_object_by_name("Global")])

    print("Segment Created, analysis finished")

@screenshot_created_event
def on_screenshot_created(project:VIANProject, screenshot:Screenshot, img:np.ndarray):
    run_analysis(project, ColorHistogramAnalysis(), [screenshot], dict(resolution=30),
                 [project.experiments[0].get_classification_object_by_name("Global")])
    print("Screenshot Created, analysis finished")

@annotation_created_event
def on_annotation_created(project:VIANProject, annotation:Annotation, sub_img:np.ndarray):

    print("Annotation Created")