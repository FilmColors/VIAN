"""
Gaudenz Halter
University of Zurich
June 2018

"""
COLOR_PALETTES_MAX_LENGTH = 1024
from typing import List

from core.data.computation import ms_to_frames, numpy_to_pixmap
from core.container.project import *
from core.gui.ewidgetbase import EGraphicsView
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from core.analysis.palette_extraction import *
from core.visualization.palette_plot import *
from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.container.hdf5_manager import vian_analysis


@vian_analysis
class ColorPaletteAnalysis(IAnalysisJob):
    def __init__(self):
        super(ColorPaletteAnalysis, self).__init__("Color Palette", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                   dataset_name="ColorPalettes",
                                                   dataset_shape=(COLOR_PALETTES_MAX_LENGTH, 6), #(Distance, Layer, L, A, B, N)
                                                   dataset_dtype=np.float16,
                                                   author="Gaudenz Halter",
                                                     version="1.0.0",
                                                     multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(ColorPaletteAnalysis, self).prepare(project, targets, parameters, fps, class_objs)
        args = []
        fps = project.movie_descriptor.fps
        for tgt in targets:
            semseg = None
            if isinstance(tgt, Screenshot):
                if class_objs is not None:
                    semseg = tgt.get_connected_analysis("SemanticSegmentationAnalysis")
                    if len(semseg) > 0:
                        semseg = semseg[0]
                    else:
                        semseg = None

            args.append([ms_to_frames(tgt.get_start(), fps),
                         ms_to_frames(tgt.get_end(), fps),
                         project.movie_descriptor.movie_path,
                         parameters,
                         tgt.get_id(),
                         project.movie_descriptor.get_letterbox_rect(),
                         semseg])
        return args

    def process(self, args, sign_progress):

        # Signal the Progress
        sign_progress(0.0)

        start = args[0]
        stop = args[1]
        movie_path = args[2]
        params = args[3]
        margins = args[5]
        semseg = args[6]
        bin_mask = None
        if semseg is not None:
            name, labels = self.target_class_obj.semantic_segmentation_labels
            mask = semseg.get_adata()
            bin_mask = labels_to_binary_mask(mask, labels)

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

            if frame is None:
                break

            # Get sub frame if there are any margins
            if margins is not None:
                frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            palettes.append(color_palette(frame, mask=bin_mask, mask_index=255))
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
        result.set_target_classification_obj(self.target_class_obj)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """
        view = PaletteView(None)
        view.depth = 10
        image = QImage(QSize(1024,256), QImage.Format_RGBA8888)
        view.palette_layer = analysis.get_adata()['tree']
        view.draw_palette(image)
        pixmap = QPixmap().fromImage(image)
        view = EGraphicsView(None)
        view.set_image(pixmap)
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        view = PaletteWidget(None)
        view.set_palette(analysis.get_adata()['tree'])
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
        return json.dumps(self.serialize(container_data))

    def to_hdf5(self, data):
        d = np.zeros(shape=(COLOR_PALETTES_MAX_LENGTH, 6))
        count = COLOR_PALETTES_MAX_LENGTH
        if len(data['tree'][0]) < COLOR_PALETTES_MAX_LENGTH:
            count = len(data['tree'][0])
        d[:len(data['dist']), 0] = data['dist']
        d[:count, 1] = data['tree'][0][:count]
        d[:count, 2:5] = data['tree'][1][:count]
        d[:count, 5] = data['tree'][2][:count]
        return d

    def from_hdf5(self, db_data):
        layers = [
            np.array(db_data[:, 1]),
            np.array(db_data[:, 2:5]),
            np.array(db_data[:, 5])
        ]
        return dict(dist=db_data[:, 0], tree=layers)


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