import cv2
import numpy as np

from core.data.creation_events import VIANPipeline, vian_pipeline
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis
from core.data.log import log_error, log_info, log_debug, log_warning

@vian_pipeline
class FigureGroundScreenshotPipeline(VIANPipeline):
    name = "Figure-Ground Screenshots Pipeline"
    version = (0,1,0)
    author = "ERC Advanced Grant FilmColors, VMML"
    uuid = "b974c859-e7e7-4804-bce4-bd7631420c36"

    requirements = dict(segment_analyses = [],
                        screenshot_analyses = [
                            (SemanticSegmentationAnalysis.__name__, "Global", 0),
                            (ColorPaletteAnalysis.__name__, "Global", 1),
                            (ColorFeatureAnalysis.__name__, "Global", 1),
                            (ColorPaletteAnalysis.__name__, "Figure", 1),
                            (ColorFeatureAnalysis.__name__, "Figure", 1),
                            (ColorPaletteAnalysis.__name__, "Ground", 1),
                            (ColorFeatureAnalysis.__name__, "Ground", 1)
                        ],
                        annotation_analyses=[]
                        )
    finished_threshold = 0.95

    def __init__(self):
        super(FigureGroundScreenshotPipeline, self).__init__()
        self.cl_obj_fig = None
        self.cl_obj_glob = None
        self.cl_obj_gnd = None

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

    def on_setup(self, project: VIANProject):
        """
        This event is yielded when the pipeline is activate using the "Use Pipeline" button.
        Here we can setup the environment to fit our purpose.

        :param project: the VIANProject instance.
        :return: None
        """
        pass
        exp = project.get_experiment_by_name("FigureGround-Experiment")
        if exp is None:
            exp = project.create_experiment(name="FigureGround-Experiment")

        self.experiment = exp

        self.cl_obj_glob = exp.create_class_object("Global")
        self.cl_obj_fig = exp.create_class_object("Figure")
        self.cl_obj_gnd = exp.create_class_object("Ground")

        self.cl_obj_glob.semantic_segmentation_labels = (DATASET_NAME_LIP, list(range(0,20)))
        self.cl_obj_fig.semantic_segmentation_labels = (DATASET_NAME_LIP, list(range(1, 20)))
        self.cl_obj_gnd.semantic_segmentation_labels = (DATASET_NAME_LIP, [LIPLabels.Background])

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
            self.cl_obj_glob,
            self.cl_obj_fig,
            self.cl_obj_gnd
        ]

        semseg = SemanticSegmentationAnalysis(model=self.model, model_name="LIP", graph=self.graph, session=self.session)
        semseg.fit(screenshot, cl_objs[0])

        ColorFeatureAnalysis().fit(screenshot, cl_objs)
        ColorPaletteAnalysis().fit(screenshot, cl_objs)

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