"""
Gaudenz Halter
University of Zurich
June 2018

"""

from typing import List
import pickle

from core.data.computation import ms_to_frames, numpy_to_pixmap
from core.container.project import *
from core.container.analysis import SemanticSegmentationAnalysisContainer
from core.gui.ewidgetbase import EGraphicsView
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from core.analysis.deep_learning.labels import *
from core.analysis.deep_learning.models import *
from core.data.interfaces import IAnalysisJob, VisualizationTab, ParameterWidget
from core.data.enums import DataSerialization
from core.container.hdf5_manager import vian_analysis

@vian_analysis
class SemanticSegmentationAnalysis(IAnalysisJob):
    def __init__(self, resolution=30, model = "LIP"):
        super(SemanticSegmentationAnalysis, self).__init__("Semantic Segmentation", [SCREENSHOT, SCREENSHOT_GROUP],
                                                           dataset_name="SemanticSegementations",
                                                           dataset_shape=(1024, 1024),
                                                           dataset_dtype=np.uint8,
                                                           author="Gaudenz Halter",
                                                           version="1.0.0",
                                                           multiple_result=False,
                                                           data_serialization=DataSerialization.MASKS)
        self.model = model
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(SemanticSegmentationAnalysis, self).prepare(project, targets, parameters, fps, class_objs)

        args = []
        fps = project.movie_descriptor.fps
        for tgt in targets:
            if tgt.get_type() == SCREENSHOT_GROUP:
                for s in tgt.screenshots:
                    args.append([ms_to_frames(s.get_start(), fps),
                                 ms_to_frames(s.get_end(), fps),
                                 project.movie_descriptor.movie_path,
                                 s.get_id()])
            else:
                args.append([ms_to_frames(tgt.get_start(), fps),
                             ms_to_frames(tgt.get_end(), fps),
                             project.movie_descriptor.movie_path,
                             tgt.get_id()])
        return args

    def process(self, args, sign_progress):
        sign_progress(0.0)

        # Signal the Progress

        results = []
        tot = len(args)
        counter = 0
        config = tf.ConfigProto()

        config.gpu_options.allow_growth = True  # dynamically grow the memory used on the GPU
        config.log_device_placement = True  # to log device placement (on which device the operation ran)

        config.gpu_options.per_process_gpu_memory_fraction = 0.4

        with tf.Graph().as_default():
            session = tf.Session(config=config)
            KTF.set_session(session)

            model = None
            if self.model == "LIP":
                model = PSPNetModelVIAN(input_shape=(512, 512, 3))
                model.load_weights(KERAS_LIP_WEIGHTS)
                model_name = DATASET_NAME_LIP
            else:
                raise Exception("Model not Found")

            for arg in args:
                start = arg[0]
                movie_path = arg[2]

                cap = cv2.VideoCapture(movie_path)
                cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                c = start

                sign_progress(counter / tot)
                counter += 1

                cap.set(cv2.CAP_PROP_POS_FRAMES, c)
                ret, frame = cap.read()
                masks = model.forward(frame)

                results.append(SemanticSegmentationAnalysisContainer(
                    name="Semantic Segmentation",
                    results=np.argmax(masks, axis=2).astype(np.uint8),
                    analysis_job_class=self.__class__,
                    parameters=dict(model = self.model, resolution=self.resolution),
                    container=arg[3],
                    dataset=model_name
                ))

        sign_progress(1.0)
        return results

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
        widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata(), cv2.COLOR_GRAY2BGR)))
        return widget

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        widget = EGraphicsView(None, auto_frame=True)
        widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata(), cv2.COLOR_GRAY2BGR)))
        return [VisualizationTab(widget=widget, name="Semantic Segmentation Mask", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user 
        activates the Analysis.
        """
        return SemanticSegmentationParameterWidget()

    def serialize(self, data_dict):
        data = dict(
            mask = pickle.dumps(data_dict['mask']),
            frame_sizes = data_dict['frame_sizes'],
            dataset = data_dict['dataset']
        )
        return data

    def deserialize(self, data_dict):
        data = dict(
            mask=pickle.loads(data_dict['mask']),
            frame_sizes=data_dict['frame_size'],
            dataset=data_dict['dataset']
        )
        return data

    def to_hdf5(self, data):
        entry = np.zeros(self.dataset_shape, self.dataset_dtype)

        if data.shape[1] > self.dataset_shape[1]:
            fx = self.dataset_shape[1] / data.shape[1]
            data = cv2.resize(data, None, None, fx, fx, cv2.INTER_NEAREST)
        entry[0:data.shape[0], 0:data.shape[1]] = data
        return entry, data.shape

    def from_hdf5(self, db_data):
        return db_data.astype(self.dataset_dtype)


class SemanticSegmentationParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the 
    interpolation type for the Preview. 

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(SemanticSegmentationParameterWidget, self).__init__()
        self.setLayout(QVBoxLayout(self))

        l2 = QHBoxLayout(self)
        self.spin_frame = QSpinBox(self)
        self.spin_frame.setMinimum(1)
        self.spin_frame.setMaximum(10000)
        self.spin_frame.setValue(50)
        l2.addWidget(QLabel("Frame Resolution:".ljust(25), self))
        l2.addWidget(self.spin_frame)

        l3 = QHBoxLayout(self)
        l3.addWidget((QLabel("Dataset:".ljust(25), self)))
        self.cb_dataset = QComboBox(self)
        self.cb_dataset.addItems(['Look into Persons', 'Ade20k'])
        l3.addWidget(self.cb_dataset)

        self.layout().addItem(l2)
        self.layout().addItem(l3)

    def get_parameters(self):
        resolution = self.spin_frame.value()
        if (self.cb_dataset.currentText() == "Look into Persons"):
            model = "LIP"
        elif (self.cb_dataset.currentText() == "ADE20K"):
            model = "ADE20K"
        else:
            return

        parameters = dict(
            model = model,
            resolution=resolution,
        )
        return parameters