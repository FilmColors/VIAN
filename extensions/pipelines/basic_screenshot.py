import cv2
import numpy as np

from core.data.creation_events import VIANPipeline, vian_pipeline
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis
from core.data.log import log_error, log_info, log_debug, log_warning

@vian_pipeline
class BasicScreenshotPipeline(VIANPipeline):
    name = "Basic Screenshot Pipeline"
    version = (0,1,0)
    author = "ERC Advanced Grant FilmColors, VMML"
    uuid = "5cd3b3a5-e68d-48a2-8e19-62a7c7063fcb"

    requirements = dict(segment_analyses = [],
                        screenshot_analyses = [
                            (ColorFeatureAnalysis.__name__, "Global", 1),
                            (ColorPaletteAnalysis.__name__, "Global", 1)
                        ],
                        annotation_analyses=[]
                        )
    finished_threshold = 0.95

    def __init__(self):
        super(BasicScreenshotPipeline, self).__init__()
        self.cl_obj = None

    def on_setup(self, project:VIANProject):
        exp = project.get_experiment_by_name("BasicScreenshot-Experiment")
        if exp is None:
            exp = project.create_experiment(name="BasicScreenshot-Experiment")

        cl_obj =  exp.get_classification_object_by_name("Global")
        if cl_obj is None:
            cl_obj = exp.create_class_object("Global")

        self.experiment = exp
        self.cl_obj = cl_obj

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

        ColorFeatureAnalysis().fit(screenshot, self.cl_obj)
        ColorPaletteAnalysis().fit(screenshot, self.cl_obj)



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
        pass