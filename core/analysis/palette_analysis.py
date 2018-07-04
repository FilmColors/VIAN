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

class ColorPaletteAnalysis(IAnalysisJob):
    def __init__(self):
        super(ColorPaletteAnalysis, self).__init__("Color Palette", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """

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

        palettes = []

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
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

            palettes.append(color_palette(frame))
            c += 1

        if len(palettes) > 1:
            result = combine_palettes(palettes)
        else:
            result = palettes[0]

        sign_progress(1.0)
        return IAnalysisJobAnalysis(
            name="Color-Palette",
            results = dict(tree=result.tree, dist = result.merge_dists),
            analysis_job_class=self.__class__,
            parameters=params, container=args[4]
        )

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed. 
        Since this function is called within the Main-Thread, we can modify our project here.
        """
        result.set_target_container(project.get_by_id(result.target_container))

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """
        view = PaletteWidget(None)
        view.set_palette(analysis.data['tree'])
        view.draw_palette()
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        view = PaletteWidget(None)
        view.set_palette(analysis.data['tree'])
        view.draw_palette()
        return [VisualizationTab(widget=view, name="Color Palette", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user 
        activates the Analysis.
        """
        return ColorPaletteParameterWidget()

    def serialize(self, data_dict):
        dist = data_dict['dist']
        layers = data_dict['tree'][0]
        all_cols = data_dict['tree'][1]
        ns = data_dict['tree'][2]
        if not isinstance(dist, list): dist = dist.tolist()
        if not isinstance(layers, list): layers = layers.tolist()
        if not isinstance(all_cols, list): all_cols = all_cols.tolist()
        if not isinstance(ns, list): ns = ns.tolist()

        d = dict(
            dist = dist,
            layers = layers,
            all_cols = all_cols,
            ns=ns)
        for i, v in enumerate(data_dict['tree']):
            if not isinstance(v, list):
                v = v.tolist()
            d[str(i)] = v
        return d

    def deserialize(self, data_dict):
        layers = [
            np.array(data_dict['layers']),
            np.array(data_dict['all_cols']),
            np.array(data_dict['ns'])
        ]
        return dict(dist = data_dict['dist'], tree=layers)

    def from_json(self, database_data):
        return self.deserialize(json.loads(database_data))

    def to_json(self, container_data):
        return json.dumps(self.serialize(container_data)).encode()


class ColorPaletteParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the 
    interpolation type for the Preview. 

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(ColorPaletteParameterWidget, self).__init__()
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