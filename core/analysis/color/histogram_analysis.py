"""
Gaudenz Halter
University of Zurich
June 2018

"""
from typing import List
from core.data.computation import ms_to_frames, numpy_to_pixmap
from core.container.project import *
from core.gui.ewidgetbase import EGraphicsView
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from core.visualization.basic_vis import HistogramVis
from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.container.hdf5_manager import vian_analysis

@vian_analysis
class ColorHistogramAnalysis(IAnalysisJob):
    """
    IAnalysisJob to extract color histograms in VIAN.

    .. note:: **HDF5 Memory Layout**

        - 1st: index of the feature vector
        - 2nd: Color Histograms

             - [0]: Bins Luminance {0.0, ..., 100.0}
             - [1]: Bins A-Channel {-128.0, ..., 128.0}
             - [2]: Bins B-Channel {-128.0, ..., 128.0}
    """

    def __init__(self, resolution=30):
        super(ColorHistogramAnalysis, self).__init__("Color Histogram", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                   dataset_name="ColorHistograms",
                                                   dataset_shape=(16,16,16),
                                                   dataset_dtype=np.float32,
                                                   author="Gaudenz Halter",
                                                     version="1.0.0",
                                                     multiple_result=True)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs = None):
        fps = project.movie_descriptor.fps
        targets, args = super(ColorHistogramAnalysis, self).prepare(project, targets, fps, class_objs)
        return args

    def process(self, args, sign_progress):
        args, sign_progress = super(ColorHistogramAnalysis, self).process(args, sign_progress)

        # Signal the Progress
        sign_progress(0.0)

        start = args['start']
        stop = args['end']
        movie_path = args['movie_path']
        margins = args['margins']
        semseg = args['semseg']

        cap = cv2.VideoCapture(movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        c = start
        final_hist = np.zeros(shape=(16,16,16), dtype = np.float32)
        shape = (1,1)

        bin_mask = None
        if semseg is not None:
            name, labels = self.target_class_obj.semantic_segmentation_labels
            mask = semseg.get_adata()
            bin_mask = labels_to_binary_mask(mask, labels)

        for i in range(start, stop  + 1, self.resolution):
            sign_progress((c - start) / ((stop - start) + 1))

            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if frame is None:
                break

            # Get sub frame if there are any margins
            if margins is not None:
                frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

            if c == start:
                shape = frame.shape
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            if bin_mask is not None:
                data = frame[np.where(bin_mask==True)]
            else:
                data = np.resize(frame, (frame.shape[0] * frame.shape[1], 3))

            final_hist += cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                                [16, 16, 16],
                                [0, 255, 0, 255, 1, 255])
            c += 1

        final_hist /= (np.clip(stop - start, 1, None))
        final_hist /= (shape[0] * shape[1])

        sign_progress(1.0)
        return IAnalysisJobAnalysis(
            name="Color-Histogram",
            results = final_hist,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution),
            container=args['target']
        )

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        super(ColorHistogramAnalysis, self).modify_project(project, result, main_window)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        view = HistogramVis(None)
        view.plot_color_histogram(analysis.get_adata())
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        view = HistogramVis(None)
        view.plot_color_histogram(analysis.get_adata())
        return [VisualizationTab(widget=view, name="Color Histogram", use_filter=False, controls=view.get_param_widget())]

    def get_parameter_widget(self):
        return ColorHistogramParameterWidget()

    def deserialize(self, data_dict):
        return data_dict

    def get_hdf5_description(self):
        return dict(
            title = "CIE-Lab Color Histograms",
            description = "Contains a list of color histograms in CIELab colorspace. ",
            dimensions = "1st: index of the histogram\\ "
                         "2nd: Bins Luminance {0.0, ..., 100.0} \\"
                         "3rd: Bins A-Channel {-128.0, ..., 128.0}\\"
                         "4th: Bins B-Channel {-128.0, ..., 128.0}\\"
        )

    def to_hdf5(self, data):
        return data

    def from_hdf5(self, db_data):
        return db_data


class ColorHistogramParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the 
    interpolation type for the Preview. 

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(ColorHistogramParameterWidget, self).__init__()
        self.setLayout(QVBoxLayout(self))

        l2 = QHBoxLayout(self)
        self.spin_frame = QSpinBox(self)
        self.spin_frame.setMinimum(1)
        self.spin_frame.setMaximum(10000)
        self.spin_frame.setValue(10)
        l2.addWidget(QLabel("Frame Resolution".ljust(25), self))
        l2.addWidget(self.spin_frame)

        self.layout().addItem(l2)

    def get_parameters(self):
        resolution = self.spin_frame.value()
        parameters = dict(
            resolution=resolution,
        )
        return parameters