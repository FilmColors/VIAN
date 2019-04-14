import cv2
import numpy as np

from core.data.creation_events import VIANPipeline, vian_pipeline
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis

@vian_pipeline
class ERCFilmColorsVIANPipeline(VIANPipeline):
    name = "ERCFilmColors Pipeline"
    version = (0,1,0)
    author = "Gaudenz Halter"

    def __init__(self):
        super(ERCFilmColorsVIANPipeline, self).__init__()

    def on_segment_created(self, project:VIANProject, segment:Segment, capture:cv2.VideoCapture):
        pass

    def on_screenshot_created(self, project, screenshot):
        print("Hello Screenshot")
        pass

    def on_svg_annotation_created(self, project, annotation, sub_img):
        print("Hello Annotation")
        pass

    def on_project_finalized(self, project):
        cl_obj_global = [project.get_experiment("ERC Advanced Grant FilmColors").get_classification_object_by_name("Global")]
        for segment in project.segments:
            run_analysis(project, ColorFeatureAnalysis(), [segment], dict(resolution=30), cl_obj_global)

        cl_objs = [
            project.get_experiment("ERC Advanced Grant FilmColors").get_classification_object_by_name("Global"),
            project.get_experiment("ERC Advanced Grant FilmColors").get_classification_object_by_name("Foreground"),
            project.get_experiment("ERC Advanced Grant FilmColors").get_classification_object_by_name("Background")
                         ]
        for screenshot in project.screenshots:
            run_analysis(project, SemanticSegmentationAnalysis(), [screenshot], dict(model = "LIP"), [cl_objs[0]])
            run_analysis(project, ColorFeatureAnalysis(), [screenshot], dict(resolution=30), cl_objs)
            run_analysis(project, ColorPaletteAnalysis(), [screenshot], dict(resolution=30), cl_objs)
        pass