import cv2
import numpy as np

from vian.core.data.creation_events import VIANPipeline, vian_pipeline
from vian.core.container.project import *
from vian.core.analysis.analysis_import import *
from vian.core.analysis.analysis_utils import run_analysis

@vian_pipeline
class %PIPELINE_NAME%(VIANPipeline):
    name = "%PIPELINE_NAME%"
    version = (1,0,0)
    author = "%AUTHOR%"
    uuid = "%UUID%"

    def __init__(self):
        super(%PIPELINE_NAME%, self).__init__()

    def on_segment_created(self, project, segment, capture):
        print("Hello Segment")
        pass

    def on_screenshot_created(self, project, screenshot):
        print("Hello Screenshot")
        pass

    def on_svg_annotation_created(self, project, annotation, sub_img):
        print("Hello SVGAnnotation")
        pass

    def on_project_finalized(self, project):
        print("Ciao Project")
        pass