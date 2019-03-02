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

class ColorHistogramAnalysis(IAnalysisJob):
    def __init__(self):
        super(ColorHistogramAnalysis, self).__init__("Color Histogram", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                   dataset_name="ColorHistograms",
                                                   dataset_shape=(16,16,16),
                                                   dataset_dtype=np.float32,
                                                   author="Gaudenz Halter",
                                                     version="1.0.0",
                                                     multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(ColorHistogramAnalysis, self).prepare(project, targets, parameters, fps, class_objs)
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
            parameters=params,
            container=args[4]
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
        view = HistogramVis(None)
        view.plot_color_histogram(analysis.get_adata())
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        view = HistogramVis(None)
        view.plot_color_histogram(analysis.get_adata())
        return [VisualizationTab(widget=view, name="Color Histogram", use_filter=False, controls=view.get_param_widget())]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user 
        activates the Analysis.
        """
        return ColorHistogramParameterWidget()

    def deserialize(self, data_dict):
        return data_dict

    def from_json(self, database_data):
        return database_data

    def to_json(self, container_data):
        return json.dumps(container_data)

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