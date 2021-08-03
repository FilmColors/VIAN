import cv2
import numpy as np

from core.data.creation_events import VIANPipeline, vian_pipeline
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis
from core.data.log import log_error, log_info, log_debug, log_warning

@vian_pipeline
class ERCFilmColorsVIANPipeline(VIANPipeline):
    name = "ERCFilmColors Pipeline"
    version = (0,1,0)
    author = "ERC Advanced Grant FilmColors, VMML"
    uuid = "fa71ec23-39ef-4af8-b59f-b419f8551f07"

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
    finished_threshold = 0.8

    def __init__(self):
        super(ERCFilmColorsVIANPipeline, self).__init__()
        try:
            self.graph = tf.Graph()
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True  # dynamically grow the memory used on the GPU
            config.gpu_options.per_process_gpu_memory_fraction = 0.4

            with self.graph.as_default():
                self.session = tf.Session(config=config)
                KTF.set_session(self.session)
                self.model = PSPNetModelVIAN(input_shape=(512, 512, 3))
                self.model.load_weights(KERAS_LIP_WEIGHTS)
                self.model_name = DATASET_NAME_LIP
        except Exception as e:
            log_error(e)
            self.model = None
            self.model_name = "LIP"
            self.session = None
        log_info(self.model, self.model_name)

    def on_setup(self, project:VIANProject):
        if project.get_experiment_by_name("ERC Advanced Grant FilmColors") is None:
            project.apply_template(template_path="data/templates/ERC-FilmColors-Template.viant")

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
        cl_objs = [
            self.experiment.get_classification_object_by_name("Global"),
            self.experiment.get_classification_object_by_name("Foreground"),
            self.experiment.get_classification_object_by_name("Background")
                         ]

        semseg = SemanticSegmentationAnalysis(model=self.model, model_name="LIP", graph=self.graph, session=self.session)
        semseg.fit(screenshot, cl_objs[0])

        # run_analysis(project, SemanticSegmentationAnalysis(model=self.model, model_name="LIP",
        #                                                    graph=self.graph, session=self.session ),
        #              [screenshot], dict(model_name="LIP"), [cl_objs[0]])
        # run_analysis(project, ColorFeatureAnalysis(), [screenshot], dict(resolution=30), cl_objs)
        # run_analysis(project, ColorPaletteAnalysis(), [screenshot], dict(resolution=30), cl_objs)

        ColorFeatureAnalysis().fit(screenshot, cl_objs)
        ColorPaletteAnalysis().fit(screenshot, cl_objs)

    def on_svg_annotation_created(self, project, annotation, sub_img):
        """
        This event is yielded as soon as an svg annotation is created or changed.

        :param project: the VIANProject instance.
        :param annotation: the SVGAnnotation instance created.
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
        cl_obj_global = [self.experiment.get_classification_object_by_name("Global")]
        for segment in project.segments:
            run_analysis(project, ColorFeatureAnalysis(), [segment], dict(resolution=30), cl_obj_global)

        cl_objs = [
            self.experiment.get_classification_object_by_name("Global"),
            self.experiment.get_classification_object_by_name("Foreground"),
            self.experiment.get_classification_object_by_name("Background")
                         ]
        for screenshot in project.screenshots:
            run_analysis(project, SemanticSegmentationAnalysis(), [screenshot], dict(model = "LIP"), [cl_objs[0]])
            run_analysis(project, ColorFeatureAnalysis(), [screenshot], dict(resolution=30), cl_objs)
            run_analysis(project, ColorPaletteAnalysis(), [screenshot], dict(resolution=30), cl_objs)
        pass