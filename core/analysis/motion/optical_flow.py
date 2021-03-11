
"""
Gaudenz Halter
University of Zurich
June 2018

"""
import numpy as np

from core.data.interfaces import IAnalysisJob, VisualizationTab, ParameterWidget, DataSerialization, TimelineDataset
from core.container.project import MOVIE_DESCRIPTOR, IProjectContainer, VIANProject, SEGMENT
from core.container.analysis import IAnalysisJobAnalysis

from core.analysis.color.palette_extraction import *
from core.container.hdf5_manager import vian_analysis
from core.visualization.palette_plot import *

import librosa
from core.analysis.misc import preprocess_frame

"""
array Structure: 

    d = np.zeros(shape=1)

"""


@vian_analysis
class OpticalFlowAnalysis(IAnalysisJob):
    def __init__(self, resolution=30):
        super(OpticalFlowAnalysis, self).__init__("Optical Flow", [MOVIE_DESCRIPTOR],
                                                 menu=IAnalysisJob.M_MOVEMENT,
                                                 dataset_name="OpticalFlow",
                                                 dataset_shape=(1,),
                                                 dataset_dtype=np.float16,
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=False,
                                                 data_serialization=DataSerialization.HDF5_SINGLE)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs=None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
        and gather all data we need.

        """
        fps = project.movie_descriptor.fps
        targets, args = super(OpticalFlowAnalysis, self).prepare(project, targets, fps, class_objs)
        self.movie_path = project.movie_descriptor.movie_path
        self.margins = project.movie_descriptor.get_letterbox_rect()
        return args

    def process(self, argst, sign_progress):
        args, sign_progress = super(OpticalFlowAnalysis, self).process(argst, sign_progress)
        print(argst)
        # Signal the Progress
        sign_progress(0.0)

        movie_path = self.movie_path
        margins = self.margins

        cap = cv2.VideoCapture(movie_path)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        start = 0
        stop = int(length)
        prvs = None

        magnitudes = np.zeros(shape=int(np.ceil(stop / self.resolution)))
        idx = 0
        for i in range(start, stop, self.resolution):
            sign_progress((i - start) / ((stop - start) + 1))

            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if frame is None:
                break

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if margins is not None:
                frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

            preprocess_frame(frame, self.max_width)

            if prvs is None:
                prvs = frame

            flow = cv2.calcOpticalFlowFarneback(prvs, frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            magnitudes[idx] = np.mean(mag)
            idx += 1

            prvs = frame

        magnitudes[magnitudes == np.inf] = 0
        magnitudes = np.nan_to_num(magnitudes)
        result = IAnalysisJobAnalysis(
            name="Optical Flow",
            results=magnitudes,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution),
            container=None
        )

        return result

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed.
        Since this function is called within the Main-Thread, we can modify our project here.
        """

        super(OpticalFlowAnalysis, self).modify_project(project, result, main_window)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """
        w = QWidget()
        lt = QGridLayout(w)
        w.setLayout(lt)

        lt.addWidget(QLabel("Lab:"), 0, 0)
        lbl1 = QLabel(str(analysis.get_adata()['color_lab']).replace("[", "(").replace("]", ")"))
        lt.addWidget(lbl1, 0, 1)

        lt.addWidget(QLabel("RGB:"), 1, 0)
        lbl2 = QLabel(str(analysis.get_adata()['color_bgr'][::-1]).replace("[", "(").replace("]", ")"))
        lt.addWidget(lbl2, 1, 1)

        lt.addWidget(QLabel("LCH:"), 2, 0)
        lbl3 = QLabel(str(lab_to_lch(analysis.get_adata()['color_lab'])).replace("[", "(").replace("]", ")"))
        lt.addWidget(lbl3, 2, 1)

        view = EGraphicsView(w)
        view.set_image(numpy_to_pixmap(np.array(([[analysis.get_adata()['color_bgr']] * 100] * 25)).astype(np.uint8)))
        lt.addWidget(view, 3, 0, 1, 2)
        return w

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        return []


    def get_timeline_datasets(self, analysis, project) -> List[TimelineDataset]:
        ms_to_idx = 1000 / (project.movie_descriptor.fps / self.resolution)

        return [
            TimelineDataset("Optical Flow (mean)", analysis.get_adata(), ms_to_idx)
        ]


    def get_hdf5_description(self):
        return dict(
            title="Average Color Values",
            description="Contains a list of average color values. ",
            color_space="CIELab, BGR",
            dimensions="1st: index of the feature vector \\ "
                       " [0]: Average Value: Luminance (CIELab) {0.0, ..., 100.0 }\\"
                       " [1] Average Value: A-Channel (CIELab) {-128.0, ..., 128.0}\\"
                       " [2] Average Value: B-Channel (CIELab) {-128.0, ..., 128.0}\\"
                       " [3] Average Value: B-Channel (BGR) {0, ..., 255}\\"
                       " [4] Average Value: G-Channel (BGR) {0, ..., 255}\\"
                       " [5] Average Value: R-Channel (BGR) {0, ..., 255}\\"
                       " [6] Average Value: Luebbe Saturation (BGR) {0, ..., 1.0}, "
                       "(Deprecated, this will be removed at some point)\\"
                       " [7] Average Value: Experimental Saturation (BGR) {0, ..., 1.0}, "
                       "(Deprecated, this will be removed at some point)\\"
        )

    def to_hdf5(self, data):
        return data

    def from_hdf5(self, db_data):
        return db_data


