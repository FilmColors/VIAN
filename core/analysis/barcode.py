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
class BarcodeAnalysis(IAnalysisJob):
    def __init__(self, resolution=30):
        super(BarcodeAnalysis, self).__init__("BarcodeAnalysis", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                  author="Gaudenz Halter",
                                                  version="1.0.0",
                                                  multiple_result=True,
                                                  data_serialization=DataSerialization.FILE)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
        and gather all data we need.

        """
        fps = project.movie_descriptor.fps
        targets, args = super(BarcodeAnalysis, self).prepare(project, targets, fps, class_objs)

        if project.folder is None and self.output_dir is None:
            raise ValueError("Z-Projections need a directory-based project or an output_dir")
        elif project.folder is not None:
            self.output_dir = os.path.join(project.data_dir)

        return args

    def process(self, args, sign_progress):
        args, sign_progress = super(BarcodeAnalysis, self).process(args, sign_progress)

        # Signal the Progress
        sign_progress(0.0)

        start = args["start"]
        stop = args["end"]
        movie_path = args["movie_path"]
        margins = args["margins"]
        semseg = args["semseg"]

        cap = cv2.VideoCapture(movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        r, frame = cap.read()
        if margins is not None:
            frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_height = 500
        out_width = 4000

        resolution = np.clip(length / out_width, 1, None)
        resolution = int(resolution)
        frame_count = int(length // resolution)
        res = np.zeros(shape=(height, frame_count, 3), dtype=np.uint8)
        c = 0
        for i in range(frame_count):
            sign_progress((c - start) / ((stop - start) + 1))
            print(i, frame_count)
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * resolution)
            ret, frame = cap.read()
            # frame = frame.astype(np.float32) // 255
            res[:, i] = np.mean(frame, axis=1)

        res = cv2.resize(res, (out_width, out_height), interpolation=cv2.INTER_NEAREST)

        return FileAnalysis(
            name="Z-Projection",
            results = res,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution),
            container=args['target']
        )

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
        view = EGraphicsView(None)
        pixmap = numpy_to_pixmap(analysis.get_adata())
        view.set_image(pixmap)
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        view = EGraphicsView(None)
        pixmap = numpy_to_pixmap(analysis.get_adata())
        view.set_image(pixmap)
        return [VisualizationTab(widget=view, name="Z-Projection", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user
        activates the Analysis.
        """
        return BarcodeAnalysisParameterWidget()

    def deserialize(self, data_dict):
        return data_dict

    def to_file(self, data, file_path):
        file_path = file_path + ".png"
        cv2.imwrite(file_path, data)
        return file_path

    def from_file(self, file_path):
        file_path = file_path + ".png"
        img = cv2.imread(file_path)
        return img

    def get_file_path(self, file_path):
        return file_path + ".png"

class BarcodeAnalysisParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the
    interpolation type for the Preview.

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(BarcodeAnalysisParameterWidget, self).__init__()
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