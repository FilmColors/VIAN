"""
Gaudenz Halter
University of Zurich
June 2018

"""

from core.data.interfaces import IAnalysisJob, ParameterWidget, TimelineDataset
from core.container.project import  IProjectContainer, VIANProject, MOVIE_DESCRIPTOR, DataSerialization, FileAnalysis
from core.container.analysis import IAnalysisJobAnalysis

from core.analysis.color.palette_extraction import *
from core.container.hdf5_manager import vian_analysis
from core.visualization.palette_plot import *

import pandas as pd



@vian_analysis
class EyetrackingAnalysis(IAnalysisJob):
    def __init__(self, resolution = 30):
        super(EyetrackingAnalysis, self).__init__("Eyetracking", [MOVIE_DESCRIPTOR],
                                                   author="Gaudenz Halter",
                                                   version="1.0.0",
                                                   multiple_result=False,
                                                   data_serialization=DataSerialization.FILE)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(EyetrackingAnalysis, self).prepare(project, targets, fps, class_objs)
        cap = cv2.VideoCapture(project.movie_descriptor.movie_path)
        width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH),  cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        args = dict(
            file = QFileDialog.getOpenFileName(filter="*.csv")[0],
            fps = project.movie_descriptor.fps,width=width,
            frame_count = frame_count,
            height=height,
            target = targets[0]
        )
        return args

    def process(self, argst, sign_progress):
        print(argst)
        w, h = argst['width'], argst['height']
        points_x = []
        points_y = []
        ttime = []

        for i in range(int(np.floor(argst['frame_count'] / self.resolution))):
            points_x.extend(np.random.randint(0, w, 500).tolist())
            points_y.extend(np.random.randint(0, h, 500).tolist())
            ttime.extend([i] * 500)

        df = pd.DataFrame()

        df['time'] = ttime
        df['points_x'] = points_x
        df['points_y'] = points_y

        return FileAnalysis(
            name="Eyetracking Dataset",
            results = df,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution)
        )

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed. 
        Since this function is called within the Main-Thread, we can modify our project here.
        """

        super(EyetrackingAnalysis, self).modify_project(project, result, main_window)

    def get_timeline_datasets(self, analysis, project) -> List[TimelineDataset]:
        df = analysis.get_adata()
        ms_to_idx = 1000 / (project.movie_descriptor.fps / self.resolution)
        data = df.to_numpy()[:, 1:]
        print(data.shape)
        result = []
        for i in np.unique(data[:, 0]):
            result.append(np.mean(data[np.where(data[:, 0] == i)]))
        print(result)
        print(data)
        return [TimelineDataset("Eyetracking Variance",
                        np.array(result),
                        ms_to_idx=ms_to_idx,
                        vis_type=TimelineDataset.VIS_TYPE_LINE, vis_color=QColor(188, 80, 144))]

    def to_file(self, data, file_path):
        file_path = file_path + ".csv"
        data.to_csv(file_path)
        return file_path

    def from_file(self, file_path):
        file_path = file_path + ".csv"
        data = pd.read_csv(file_path)
        return data


class ColorFeatureParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the 
    interpolation type for the Preview. 

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(ColorFeatureParameterWidget, self).__init__()
        self.setLayout(QVBoxLayout(self))

        l2 = QHBoxLayout(self)
        self.spin_frame = QSpinBox(self)
        self.spin_frame.setMinimum(1)
        self.spin_frame.setMaximum(10000)
        self.spin_frame.setValue(50)
        l2.addWidget(QLabel("Frame Resolution".ljust(25), self))
        l2.addWidget(self.spin_frame)

        self.layout().addItem(l2)

    def get_parameters(self):
        resolution = self.spin_frame.value()
        parameters = dict(
            resolution=resolution,
        )
        return parameters