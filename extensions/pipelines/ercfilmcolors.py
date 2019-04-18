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
    author = "ERC Advanced Grant FilmColors, VMML"

    requirements = dict(segment_analyses = [
                            (ColorFeatureAnalysis.__name__, "Global", 0),
                            (ColorPaletteAnalysis.__name__, "Global", 0),
                            (ColorHistogramAnalysis.__name__, "Global", 0)
                        ],
                        screenshot_analyses = [
                            (SemanticSegmentationAnalysis.__name__, "Global", 0),
                            (ColorFeatureAnalysis.__name__, "Foreground", 1),
                            (ColorFeatureAnalysis.__name__, "Background", 1),
                            (ColorFeatureAnalysis.__name__, "Global", 1),
                            (ColorPaletteAnalysis.__name__, "Foreground", 1),
                            (ColorPaletteAnalysis.__name__, "Background", 1),
                            (ColorPaletteAnalysis.__name__, "Global", 1)
                        ],
                        annotation_analyses=[]
                        )
    finished_threshold = 0.95

    def __init__(self):
        super(ERCFilmColorsVIANPipeline, self).__init__()

    def on_segment_created(self, project:VIANProject, segment:Segment, capture:cv2.VideoCapture):
        """
        This event is yielded as soon as a segment is created or changed.

        :param project: the VIANProject instance.
        :param segment: the Segment instance created
        :param capture: an cv2.VideoCapture instance with the movie already opened
        :return: None
        """
        pass

    def on_screenshot_created(self, project, screenshot):
        """
        This event is yielded as soon as a screenshot is created.

        :param project: the VIANProject instance.
        :param screenshot: the Screenshot instance created
        :return: None
        """
        pass

    def on_svg_annotation_created(self, project, annotation, sub_img):
        """
        This event is yielded as soon as an svg annotation is created or changed.

        :param project: the VIANProject instance.
        :param annotation: the Annotation instance created.
        :param sub_img: the image of the annotations bounding box
        :return: None
        """
        pass

    def on_project_finalized(self, project):
        """
        This event is yielded when the user manually pushes the button "Finalize"

        :param project: The VIANProject instance
        :return: None
        """
        cl_obj_global = [project.get_experiment("ERC Advanced Grant FilmColors")
                             .get_classification_object_by_name("Global")]
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