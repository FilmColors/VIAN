from core.analysis.color_feature_extractor import *
from core.analysis.palette_analysis import *
from core.analysis.barcode_analysis import *
from core.analysis.movie_mosaic.movie_mosaic import *
from core.analysis.colorimetry.colormetry2 import *
from core.analysis.histogram_analysis import ColorHistogramAnalysis
from core.analysis.z_projection import ZProjectionAnalysis
from core.container.hdf5_manager import vian_analysis

# import dlib
try:
    from core.analysis.semantic_segmentation import *
    from core.analysis.deep_learning.face_identification import *
    import os
    # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    from core.analysis.import_tensortflow import tf
    # tf.test.is_gpu_available()
    # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    # tf.logging.set_verbosity(tf.logging.FATAL)
    # log_info("Verbosity", tf.logging.get_verbosity())

except:
    from core.data.enums import DataSerialization
    from core.analysis.deep_learning.labels import *


    @vian_analysis
    class SemanticSegmentationAnalysis(IAnalysisJob):
        def __init__(self):
            super(SemanticSegmentationAnalysis, self).__init__("Semantic Segmentation", [SCREENSHOT, SCREENSHOT_GROUP],
                                                               dataset_name="SemanticSegementations",
                                                               dataset_shape=(1024, 1024),
                                                               dataset_dtype = np.uint8,
                                                               author="Gaudenz Halter",
                                                               version="1.0.0",
                                                               multiple_result=False)

        def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs=None):
            """
            This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
            and gather all data we need.

            """
            super(SemanticSegmentationAnalysis, self).prepare(project, targets, fps, class_objs)

            args = []
            fps = project.movie_descriptor.fps
            for tgt in targets:
                if tgt.get_type() == SCREENSHOT_GROUP:
                    for s in tgt.screenshots:
                        args.append([ms_to_frames(s.get_start(), fps), ms_to_frames(s.get_end(), fps),
                                     project.movie_descriptor.movie_path, s.get_id()])
                else:
                    args.append([ms_to_frames(tgt.get_start(), fps), ms_to_frames(tgt.get_end(), fps),
                                 project.movie_descriptor.movie_path, tgt.get_id()])
            return args

        def process(self, args, sign_progress):
            args, sign_progress = super(SemanticSegmentationAnalysis, self).process(args, sign_progress)
            log_warning("No KERAS Backend Installed, you can not peform this analysis")

        def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
            """
            This Function will be called after the processing is completed.
            Since this function is called within the Main-Thread, we can modify our project here.
            """
            result.set_target_container(project.get_by_id(result.target_container))
            result.set_target_classification_obj(self.target_class_obj)

        def get_preview(self, analysis: IAnalysisJobAnalysis):
            """
            This should return the Widget that is shown in the Inspector when the analysis is selected
            """
            widget = EGraphicsView(None, auto_frame=True)
            widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata()['mask'], cv2.COLOR_GRAY2BGR)))
            return widget

        def get_visualization(self, analysis, result_path, data_path, project, main_window):
            """
            This function should show the complete Visualization
            """
            widget = EGraphicsView(None, auto_frame=True)
            widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata()['mask'], cv2.COLOR_GRAY2BGR)))
            return [VisualizationTab(widget=widget, name="Semantic Segmentation Mask", use_filter=False, controls=None)]

        def get_parameter_widget(self):
            """
            Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user
            activates the Analysis.
            """
            return SemanticSegmentationParameterWidget()

        def serialize(self, data_dict):
            data = dict(
                mask=pickle.dumps(data_dict['mask']),
                frame_sizes=data_dict['frame_sizes'],
                dataset=data_dict['dataset']
            )
            return data

        def deserialize(self, data_dict):
            data = dict(
                mask=pickle.loads(data_dict['mask']),
                frame_sizes=data_dict['frame_size'],
                dataset=data_dict['dataset']
            )
            return data

        def from_json(self, database_data):
            # return json.loads(database_data)
            return pickle.loads(database_data)

        def to_json(self, container_data):
            return pickle.dumps(container_data)
            # return json.dumps(self.serialize(container_data))


    class FaceRecognitionModel():
        def __init__(self, cascPath="data/models/face_identification/haarcascade_frontalface_default.xml",
                     predictor_path="data/models/face_identification/shape_predictor_68_face_landmarks.dat",
                     weights_path="data/models/face_identification/weights.hdf5",
                     cascPathside="data/models/face_identification/haarcascade_profileface.xml", serving = True):
            if os.path.isfile(cascPath):
                self.cascade = cv2.CascadeClassifier(cascPath)
            else:
                self.cascade = None
            if os.path.isfile(cascPathside):
                self.cascade_side = cv2.CascadeClassifier(cascPathside)
            else:
                self.cascade_side = None

            try:
                self.predictor = dlib.shape_predictor(predictor_path)
                self.detector = dlib.get_frontal_face_detector()
            except:
                self.predictor = None
                self.detector = None
            self.weights_path = weights_path

            self.dnn_model = None
            self.nose_point_idx = 30

        def init_model(self, n_classes, dropout):
            pass

        def extract_faces(self, frame_bgr, preview=False):
            pass

        def draw_faces(self, frame_bgr):
            return frame_bgr

        def get_vector(self, img, preview=True):
            pass

        def cluster_faces(self, eucl_dist_vecs, n_clusters=30):
            pass

        def load_weights(self, path=None):
            pass

        def store_weights(self, path=None):
            pass

        def train_model(self, X_train, y_train, X_test, y_test, load=False, callback=None):
            pass

        def predict(self, face_vec):
            pass

