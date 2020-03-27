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
    """
    IAnalysisJob to extract color palettes in VIAN.

    .. note:: **HDF5 Memory Layout**

        - 1st: index of the feature vector
        - 2nd: Palette Clusters

            - [0]: Merge Distance
            - [1]: Merge Depth
            - [2] Cluster Color: B-Channel (BGR) {0, ..., 255}
            - [3] Cluster Color: G-Channel (BGR) {0, ..., 255}
            - [4] Cluster Color: R-Channel (BGR) {0, ..., 255}
            - [5] Number of Pixels
    """
    def __init__(self, resolution = 30, input_width = 300, n_super_pixel = 200):
        super(ColorPaletteAnalysis, self).__init__("Color Palette", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                   dataset_name="ColorPalettes",
                                                   dataset_shape=(COLOR_PALETTES_MAX_LENGTH, 6), #(Distance, Layer, L, A, B, N)
                                                   dataset_dtype=np.float16,
                                                   author="Gaudenz Halter",
                                                   version="1.0.0",
                                                   multiple_result=True)
        self.resolution = resolution
        self.seeds_input_width = input_width
        self.n_super_pixel = n_super_pixel

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], fps, class_objs = None):
        fps = project.movie_descriptor.fps
        targets, args = super(ColorPaletteAnalysis, self).prepare(project, targets, fps, class_objs)
        return args

    def process(self, args, sign_progress):
        args, sign_progress = super(ColorPaletteAnalysis, self).process(args, sign_progress)
        # Signal the Progress
        sign_progress(0.0)

        start = args['start']
        stop = args['end']
        movie_path = args['movie_path']
        margins = args['margins']
        semseg = args['semseg']
        bin_mask = None
        if semseg is not None:
            name, labels = self.target_class_obj.semantic_segmentation_labels
            mask = semseg.get_adata()
            bin_mask = labels_to_binary_mask(mask, labels)

        palettes = []

        cap = cv2.VideoCapture(movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        c = start

        model = None
        for i in range(start, stop + 1, self.resolution):
            sign_progress((c - start) / ((stop - start) + 1))

            cap.set(cv2.CAP_PROP_POS_FRAMES, i )
            ret, frame = cap.read()

            if frame is None:
                break
            # Get sub frame if there are any margins
            if margins is not None:
                frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

            if model is None:
                if self.seeds_input_width < frame.shape[0]:
                    rx = self.seeds_input_width / frame.shape[0]
                    frame = cv2.resize(frame, None, None, rx, rx, cv2.INTER_CUBIC)
                model = PaletteExtractorModel(frame, n_pixels=self.n_super_pixel, num_levels=8)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            try:
                pal = color_palette(frame, mask=bin_mask,
                                    mask_index=255,
                                    n_pixels=self.n_super_pixel,
                                    seeds_input_width = self.seeds_input_width,
                                    seeds_model=model)
            except Exception as e:
                log_error(e)
                pal = None
            if pal is not None:
                palettes.append(pal)
            c += 1

        if len(palettes) > 0:
            if len(palettes) > 1:
                result = combine_palettes(palettes)
            else:
                result = palettes[0]

            sign_progress(1.0)
            return IAnalysisJobAnalysis(
                name="Color-Palette",
                results = dict(tree=result.tree, dist = result.merge_dists),
                analysis_job_class=self.__class__,
                parameters=dict(resolution=self.resolution),
                container=args['target']
            )
        return None

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        result.set_target_container(project.get_by_id(result.target_container))
        result.set_target_classification_obj(self.target_class_obj)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
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
        view = PaletteWidget(None)
        view.set_palette(analysis.get_adata()['tree'])
        view.draw_palette()
        return [VisualizationTab(widget=view, name="Color Palette", use_filter=False, controls=None)]

    def get_parameter_widget(self):
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

    def get_hdf5_description(self):
        return dict(
            title = "Average Color Values",
            description = "A bottom-up color palette clustering. ",
            color_space = "BGR, computed in CIELab",
            dimensions = "1st: index of the feature vector \\ "
                         "2nd: Palette Clusters\\"
                         " [0]: Merge Distance\\"
                         " [1]: Merge Depth"
                         " [3] Cluster Color: B-Channel (BGR) {0, ..., 255}\\"
                         " [4] Cluster Color: G-Channel (BGR) {0, ..., 255}\\"
                         " [5] Cluster Color: R-Channel (BGR) {0, ..., 255}\\"
                         " [6] Number of Colors"
        )

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


def get_palette_at_merge_depth(palette, depth = 10):
    t = palette['tree']
    all_depths = t[0]
    all_cols = t[1]
    all_bins = t[2]

    stored_depths = np.unique(all_depths)
    try:
        indices = np.where(all_depths == stored_depths[np.clip(depth, 0, stored_depths.shape[0])])[0]
        n_bins_total = np.sum(all_bins[indices])
        res = []

        all_bins /= n_bins_total
        all_bins = np.round(all_bins, 6)
        all_bins = np.nan_to_num(all_bins)

        all_cols = np.nan_to_num(all_cols)
        all_cols = np.clip(all_cols, 0, 255)

        for i in indices:
            lab = tpl_bgr_to_lab(all_cols[i]).tolist()
            amount = float(all_bins[i])

            res.append(dict(
                bgr = all_cols[i].tolist(),
                lab = lab,
                amount = amount
            ))
        return res
    except Exception as e:
        return None



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