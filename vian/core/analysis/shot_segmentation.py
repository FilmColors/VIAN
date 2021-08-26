from typing import List
import numpy as np

from PyQt5.QtCore import QObject

from core.data.enums import *
from core.data.log import log_info, log_warning, log_error, log_debug
from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab

from core.gui.ewidgetbase import EGraphicsView

from core.container.hdf5_manager import vian_analysis
from core.container.analysis import IAnalysisJobAnalysis, AnalysisContainer
from core.container.project import VIANProject, Segmentation
from core.data.computation import floatify_img, frame2ms


import cv2
from core.analysis.colorimetry.computation import calculate_histogram
from sklearn.cluster import AgglomerativeClustering

MAX_CLUSTER = 500
MAX_DEPTH = 500

@vian_analysis
class ShotSegmentationAnalysis(IAnalysisJob):
    """
    This is the BaseClass for all Analyses.
    Subclass it to implement your own Analyses.

    Array: nd.array([CLUSTER, MERGE_DIST, ]

    """

    def __init__(self, resolution=30, cluster_range=(1,60), method="histogram", frame_resolution=10, return_frames=False, frame_width_clamp=100, return_hdf5_compatible = False):
        super(ShotSegmentationAnalysis, self).__init__("ShotSegmentation", [MOVIE_DESCRIPTOR],
                                                 dataset_name="ShotSegmentation",
                                                 dataset_shape=(MAX_DEPTH,MAX_CLUSTER, 3),
                                                 dataset_dtype=np.uint32,
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=False)
        self.method = method
        self.resolution = resolution
        self.cluster_range = cluster_range
        self.frame_resolution = frame_resolution
        self.return_frames = return_frames
        self.frame_width_clamp = frame_width_clamp
        self.return_hdf5_compatible = return_hdf5_compatible

    def prepare(self, project: VIANProject, targets: List[Segmentation], fps, class_objs=None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
        and gather all data we need.

        """
        super(ShotSegmentationAnalysis, self).prepare(project, targets, fps, class_objs)
        args = dict(movie_path = project.movie_descriptor.movie_path, movie_descriptor = project.movie_descriptor)
        return args

    def process(self, args, sign_progress):
        """
        This is the actual analysis, which takes place in a WorkerThread.
        Do NOT and NEVER modify the project within this function.

        We want to read though the movie and get the Average Colors from each Segment.

        Once done, we create an Analysis Object from it.
        """
        args, sign_progress = super(ShotSegmentationAnalysis, self).process(args, sign_progress)
        # Signal the Progress
        sign_progress(0.0)

        video_capture = cv2.VideoCapture(args['movie_path'])

        duration = video_capture.get(cv2.CAP_PROP_FRAME_COUNT)
        resize_f = 192.0 / video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        resize_clamp = self.frame_width_clamp / video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        width = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        n = int(np.floor(duration / self.resolution))
        X = np.zeros(shape=(n, 16**3), dtype=np.float16)
        frame_pos = np.zeros(shape=n, dtype=np.int32)

        frames = []
        for i in range(int(n)):
            if self.aborted:
                return None

            idx = int(i * self.resolution)
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, idx)

            ret, frame = video_capture.read()
            if frame is None:
                continue

            if self.return_frames and i % self.frame_resolution == 0:
                frames.append(cv2.resize(frame, None, None, resize_f, resize_f, cv2.INTER_CUBIC))

            if resize_clamp < 1.0:
                frame = cv2.resize(frame, None, None, resize_clamp, resize_clamp, cv2.INTER_CUBIC)
            frame = cv2.cvtColor(floatify_img(frame), cv2.COLOR_BGR2LAB)
            X[i] = np.resize(calculate_histogram(frame, lab_mode=True), new_shape=16 ** 3) / (width * height)
            frame_pos[i] = idx
            sign_progress(round(i / n, 4))

        connectivity = np.zeros(shape=(n, n), dtype=np.uint8)
        for i in range(1, n - 1, 1):
            connectivity[i][i - 1] = 1
            connectivity[i][i] = 1
            connectivity[i][i + 1] = 1
        clusterings = []

        cluster_sizes = range(self.cluster_range[0], self.cluster_range[1], 1)
        for i, n_cluster in enumerate(cluster_sizes):
            sign_progress(i / len(cluster_sizes))
            if X.shape[0] > n_cluster:
                model = AgglomerativeClustering(linkage="ward",
                                                connectivity=connectivity,
                                                n_clusters=n_cluster, compute_full_tree=True)
                model.fit(X)
                timestamps = self._generate_segments(model.labels_, frame_pos, video_capture.get(cv2.CAP_PROP_FPS))
                clusterings.append(timestamps)

        if self.return_hdf5_compatible:
            result = np.zeros(shape=self.dataset_shape, dtype=self.dataset_dtype)
            for i in range(len(clusterings)):
                result[i][0:len(clusterings[i])] = [[c['label'], c['f_start'], c['f_stop']] for c in clusterings[i]]
            # Creating an IAnalysisJobAnalysis Object that will be handed back to the Main-Thread
            analysis = IAnalysisJobAnalysis(name="My Analysis",
                                            results=result,
                                            analysis_job_class=self.__class__,
                                            parameters=dict(resolution=self.resolution),
                                            container=args['movie_descriptor'])
        else:
            analysis = AnalysisContainer(name=self.name, data=clusterings)
        sign_progress(1.0)
        return analysis

    def _generate_segments(self, clustering, timestamps, fps):
        result_dict = []
        current_lbl = -1
        start = timestamps[0]
        stop = None
        for i, lbl in enumerate(clustering):
            if lbl != current_lbl or i == len(clustering) - 1:
                if current_lbl != -1:
                    stop = timestamps[i]
                    result_dict.append(dict(label=lbl,
                                       f_start = start,
                                       f_stop = stop,
                                       t_start = frame2ms(start, fps),
                                       t_stop = frame2ms(stop, fps)
                                       ))
                current_lbl = lbl
                start = timestamps[i]

        return result_dict

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed.
        Since this function is called within the Main-Thread, we can modify our project here.
        """

        pass

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """

        return EGraphicsView(None)

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        return [VisualizationTab(widget=EGraphicsView(None), name="Barcode", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user
        activates the Analysis.
        """
        return ShotSegmentationParameterWidget()


class ShotSegmentationParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the
    interpolation type for the Preview.

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(ShotSegmentationParameterWidget, self).__init__()
        # Put UI Here

    def get_parameters(self):
        """
        This function is called by VIAN to retrieve the user given parameters.
        Override to add functionality
        :return:
        """
        parameters = dict(
        )
        return parameters