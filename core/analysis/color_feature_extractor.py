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
from core.analysis.palette_extraction import *
from core.visualization.palette_plot import *


class ColorFeatureAnalysis(IAnalysisJob):
    def __init__(self):
        super(ColorFeatureAnalysis, self).__init__("Color Feature Extractor", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(ColorFeatureAnalysis, self).prepare(project, targets, parameters, fps, class_objs)

        args = []
        fps = project.movie_descriptor.fps
        for tgt in targets:
            args.append([ms_to_frames(tgt.get_start(), fps), ms_to_frames(tgt.get_end(), fps), project.movie_descriptor.movie_path, parameters, tgt.get_id()])
        return args

    def process(self, args, sign_progress):

        # Signal the Progress
        sign_progress(0.0)

        start = args[0]
        stop = args[1]
        movie_path = args[2]
        params = args[3]

        colors_lab = []
        colors_bgr = []

        cap = cv2.VideoCapture(movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        c = start

        while (c < stop + params['resolution']):
            if c % params['resolution'] != 0:
                c += 1
                continue
            sign_progress((c - start) / ((stop - start) + 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, c)
            ret, frame = cap.read()
            colors_bgr.append(np.mean(frame, axis = (0, 1)))

            frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            colors_lab.append(np.mean(frame_lab, axis=(0, 1)))
            c += 1

        if len(colors_lab) > 1:
            colors_bgr = np.mean(colors_bgr, axis = 0)
            colors_lab = np.mean(colors_lab, axis = 0)

        else:
            colors_bgr = colors_bgr[0]
            colors_lab = colors_lab[0]

        saturation_l = lab_to_sat(lab=colors_lab, implementation="luebbe")
        saturation_p = lab_to_sat(lab=colors_lab, implementation="pythagoras")

        sign_progress(1.0)
        return IAnalysisJobAnalysis(
            name="Color-Features",
            results = dict(color_lab=colors_lab,
                           color_bgr = colors_bgr,
                           saturation_l=saturation_l,
                           saturation_p = saturation_p
                           ),
            analysis_job_class=self.__class__,
            parameters=params, container=args[4]
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
        w = QWidget()
        w.setLayout(QVBoxLayout())
        w.layout().addWidget(QLabel("Color CIE-Lab:\t" + str(analysis.get_adata()['color_lab']), w))
        w.layout().addWidget(QLabel("    Color BGR:\t" + str(analysis.get_adata()['color_bgr']), w))
        w.layout().addWidget(QLabel("Saturation Luebbe:\t" + str(analysis.get_adata()['saturation_l']), w))
        w.layout().addWidget(QLabel("Saturation FilmCo:\t" + str(analysis.get_adata()['saturation_p']), w))
        return w

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        w = QWidget()
        w.setLayout(QVBoxLayout())
        w.layout().addWidget(QLabel("Color CIE-Lab:\t" + str(analysis.get_adata()['color_lab']), w))
        w.layout().addWidget(QLabel("    Color BGR:\t" + str(analysis.get_adata()['color_bgr']), w))
        w.layout().addWidget(QLabel("Saturation Luebbe:\t" + str(analysis.get_adata()['saturation_l']), w))
        w.layout().addWidget(QLabel("Saturation FilmCo:\t" + str(analysis.get_adata()['saturation_p']), w))
        return [VisualizationTab(widget=w, name="Color-Features", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user 
        activates the Analysis.
        """
        return ColorFeatureParameterWidget()

    def serialize(self, data_dict):

        d = dict(color_lab=np.array(data_dict["color_lab"]).tolist(),
                 color_bgr=np.array(data_dict["color_bgr"]).tolist(),
                 saturation_l=np.array(data_dict["saturation_l"]).tolist(),
                 saturation_p=np.array(data_dict["saturation_p"]).tolist()
             )
        return d

    def from_json(self, database_data):
        return json.loads(database_data)

    def to_json(self, container_data):
        return json.dumps(self.serialize(container_data))


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