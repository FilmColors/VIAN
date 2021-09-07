"""
Gaudenz Halter
University of Zurich
June 2018

"""

from vian.core.data.interfaces import IAnalysisJob, VisualizationTab, ParameterWidget
from vian.core.container.project import SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP, BaseProjectEntity, VIANProject
from vian.core.container.analysis import IAnalysisJobAnalysis

from vian.core.analysis.color.palette_extraction import *
from vian.core.container.hdf5_manager import vian_analysis
from vian.core.visualization.palette_plot import *

from vian.core.analysis.misc import preprocess_frame

"""
array Structure: 

    d = np.zeros(shape=8)
    d[0:3] = np.array(data["color_lab"])
    d[3:6] = np.array(data["color_bgr"])
    d[6] = np.array(data["saturation_l"])
    d[7] = np.array(data["saturation_p"])
    return d
"""

@vian_analysis
class ColorFeatureAnalysis(IAnalysisJob):
    """
    IAnalysisJob to extract average color values in VIAN.

    .. note:: **HDF5 Memory Layout**

        - 1st: index of the feature vector
        - 2nd: Average Color Features

            - [0]: Average Value: Luminance (CIELab) {0.0, ..., 100.0 }
            - [1] Average Value: A-Channel (CIELab) {-128.0, ..., 128.0}
            - [2] Average Value: B-Channel (CIELab) {-128.0, ..., 128.0}
            - [3] Average Value: B-Channel (BGR) {0, ..., 255}
            - [4] Average Value: G-Channel (BGR) {0, ..., 255}
            - [5] Average Value: R-Channel (BGR) {0, ..., 255}
            - [6] Average Value: Luebbe Saturation (BGR) {0, ..., 1.0} (Deprecated, this will be removed at some point)
            - [7] Average Value: Experimental Saturation (BGR) {0, ..., 1.0} (Deprecated, this will be removed at some point)
    """

    def __init__(self, resolution = 30):
        super(ColorFeatureAnalysis, self).__init__("Color Feature Extractor",
                                                   [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                   dataset_name="ColorFeatures",
                                                   dataset_shape=(8,),
                                                   dataset_dtype=np.float16,
                                                   author="Gaudenz Halter",
                                                   version="1.0.0",
                                                   multiple_result=False)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[BaseProjectEntity], fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        fps = project.movie_descriptor.fps
        targets, args = super(ColorFeatureAnalysis, self).prepare(project, targets, fps, class_objs)

        # TODO Why is this here?
        self.hdf5_manager = project.hdf5_manager

        return args

    def process(self, argst, sign_progress):
        argst, sign_progress = super(ColorFeatureAnalysis, self).process(argst, sign_progress)
        result = []
        # Signal the Progress
        cap = None
        counter = 0
        for args in argst:
            sign_progress(counter / len(argst))
            counter += 1

            start = args['start']
            stop = args['end']
            movie_path = args['movie_path']
            margins = args['margins']
            semseg = args['semseg']
            colors_lab = []
            colors_bgr = []

            if cap is None:
                cap = cv2.VideoCapture(movie_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            c = start

            if self.coverage is not None:
                self.resolution = self.resolution_from_coverage(start, stop + 1)

            for i in range(start, stop  + 1, self.resolution):
                sign_progress((c - start) / ((stop - start) + 1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if frame is None:
                    break

                # Get sub frame if there are any margins
                if margins is not None:
                    frame = frame[margins[1]:margins[3], margins[0]:margins[2]]

                frame = preprocess_frame(frame, self.max_width)

                bin_mask = None
                if semseg is not None and self.target_class_obj is not None:
                    name, labels = self.target_class_obj.semantic_segmentation_labels
                    mask = semseg.get_adata()
                    bin_mask = labels_to_binary_mask(mask, labels)
                    if margins is not None:
                        bin_mask = bin_mask[margins[1]:margins[3], margins[0]:margins[2]]
                    bin_mask = preprocess_frame(bin_mask, self.max_width, mode=cv2.INTER_NEAREST)

                if bin_mask is not None:
                    indices = np.where(bin_mask > 0)
                    colors_bgr.append(np.mean(frame[indices], axis=(0)))
                    frame_lab = cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
                    colors_lab.append(np.mean(frame_lab[indices], axis=(0)))
                else:
                    colors_bgr.append(np.mean(frame, axis = (0, 1)))
                    frame_lab = cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
                    colors_lab.append(np.mean(frame_lab, axis=(0, 1)))
                c += 1

            if len(colors_lab) > 1:
                colors_bgr = np.mean(colors_bgr, axis = 0)
                colors_lab = np.mean(colors_lab, axis = 0)

            elif len(colors_lab) == 1:
                colors_bgr = colors_bgr[0]
                colors_lab = colors_lab[0]

            else:
                continue

            saturation_l = lab_to_sat(lab=colors_lab, implementation="luebbe")
            saturation_p = lab_to_sat(lab=colors_lab, implementation="pythagoras")

            sign_progress(1.0)
            result.append(
             IAnalysisJobAnalysis(
                name="Color Average",
                results = dict(color_lab=colors_lab,
                               color_bgr = colors_bgr,
                               saturation_l=saturation_l,
                               saturation_p = saturation_p
                               ),
                analysis_job_class=self.__class__,
                parameters=dict(resolution = self.resolution),
                container=args['target']
            )
            )
        return result

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed. 
        Since this function is called within the Main-Thread, we can modify our project here.
        """

        super(ColorFeatureAnalysis, self).modify_project(project, result, main_window)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """
        w = QWidget()
        lt = QGridLayout(w)
        w.setLayout(lt)

        lt.addWidget(QLabel("Lab:"),0,0)
        lbl1 = QLabel(str(analysis.get_adata()['color_lab']).replace("[", "(").replace("]",")"))
        lt.addWidget(lbl1, 0, 1)

        lt.addWidget(QLabel("RGB:"), 1, 0)
        lbl2 = QLabel(str(analysis.get_adata()['color_bgr'][::-1]).replace("[", "(").replace("]",")"))
        lt.addWidget(lbl2, 1, 1)

        lt.addWidget(QLabel("LCH:"), 2, 0)
        lbl3 = QLabel(str(lab_to_lch(analysis.get_adata()['color_lab'])).replace("[", "(").replace("]",")"))
        lt.addWidget(lbl3, 2, 1)

        view = EGraphicsView(w)
        view.set_image(numpy_to_pixmap(np.array(([[analysis.get_adata()['color_bgr']] * 100 ] * 25)).astype(np.uint8)))
        lt.addWidget(view, 3, 0, 1, 2)
        return w

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        w = QWidget()
        w.setLayout(QVBoxLayout(w))
        w.layout().addWidget(QLabel("Color CIE-Lab:".rjust(20) + str(analysis.get_adata()['color_lab']), w))
        w.layout().addWidget(QLabel("Color BGR:".rjust(20) + str(analysis.get_adata()['color_bgr']), w))
        w.layout().addWidget(QLabel("Saturation Luebbe:".rjust(20) + str(analysis.get_adata()['saturation_l']), w))
        w.layout().addWidget(QLabel("Saturation FilmCo:".rjust(20) + str(analysis.get_adata()['saturation_p']), w))
        view = EGraphicsView(w)
        view.set_image(numpy_to_pixmap(np.array(([[analysis.get_adata()['color_bgr']] * 100] * 25)).astype(np.uint8)))
        w.layout().addWidget(view)
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

    def get_hdf5_description(self):
        return dict(
            title = "Average Color Values",
            description = "Contains a list of average color values. ",
            color_space = "CIELab, BGR",
            dimensions = "1st: index of the feature vector \\ "
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
        d = np.zeros(shape=8)
        d[0:3] = np.array(data["color_lab"])
        d[3:6] = np.array(data["color_bgr"])
        d[6] = np.array(data["saturation_l"])
        d[7] = np.array(data["saturation_p"])
        return d

    def from_hdf5(self, db_data):
        d = dict(color_lab=db_data[0:3],
                 color_bgr=db_data[3:6],
                 saturation_l=db_data[6],
                 saturation_p=db_data[7]
             )
        return d


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