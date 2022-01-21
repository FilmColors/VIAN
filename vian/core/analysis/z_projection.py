"""
Gaudenz Halter
University of Zurich
June 2018

"""
from typing import List
from vian.core.data.computation import ms_to_frames, numpy_to_pixmap
from vian.core.container.project import *
from vian.core.gui.ewidgetbase import EGraphicsView
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from vian.core.visualization.basic_vis import HistogramVis
from vian.core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from vian.core.container.hdf5_manager import vian_analysis

@vian_analysis
class ZProjectionAnalysis(IAnalysisJob):
    def __init__(self, resolution=30):
        super(ZProjectionAnalysis, self).__init__("Z-Projection", [SEGMENTATION, SEGMENT, SCREENSHOT, SCREENSHOT_GROUP],
                                                  author="Gaudenz Halter",
                                                  version="1.0.0",
                                                  multiple_result=True,
                                                  data_serialization=DataSerialization.FILE)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[BaseProjectEntity], fps, class_objs = None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
        and gather all data we need.

        """
        targets, args = super(ZProjectionAnalysis, self).prepare(project, targets, fps, class_objs)

        if project.folder is None and self.output_dir is None:
            raise ValueError("Z-Projections need a directory-based project or an output_dir")
        elif project.folder is not None:
            self.output_dir = os.path.join(project.data_dir)

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

            args.append(dict(start=ms_to_frames(tgt.get_start(), fps),
                         end=ms_to_frames(tgt.get_end(), fps),
                         movie_path=project.movie_descriptor.movie_path,
                         target=tgt.get_id(),
                         margins=project.movie_descriptor.get_letterbox_rect(),
                         semseg=semseg))
        return args

    def process(self, args, sign_progress):
        args, sign_progress = super(ZProjectionAnalysis, self).process(args, sign_progress)

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
        c = start
        z_projection = np.zeros(shape=frame.shape, dtype = np.float32)

        bin_mask = None
        if semseg is not None:
            name, labels = self.target_class_obj.semantic_segmentation_labels
            mask = semseg.get_adata()
            bin_mask = labels_to_binary_mask(mask, labels)

        n = 0
        while c < stop + self.resolution:
            if c % self.resolution != 0:
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

            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            # z_projection += floatify_img(frame)
            z_projection += frame
            c += 1
            n += 1

        z_projection = np.divide(z_projection, n)
        z_projection -= np.amin(z_projection)
        z_projection *= (255 / np.amax(z_projection))
        # z_projection = (z_projection * 255).astype(np.uint8)
        z_projection = z_projection.astype(np.uint8)
        # z_projection = cv2.cvtColor(z_projection, cv2.COLOR_LAB2BGR)
        sign_progress(1.0)
        return FileAnalysis(
            name="Z-Projection",
            results = z_projection,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution),
            container=args['target']
        )

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed.
        Since this function is called within the Main-Thread, we can modify our project here.
        """
        super(ZProjectionAnalysis, self).modify_project(project, result, main_window)

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
        return ZProjectionParameterWidget()

    # def deserialize(self, data_dict):
    #     return data_dict


    def get_extension(self):
        return ".jpg"

    def to_file(self, data, file_path):
        file_path = file_path + self.get_extension()
        cv2.imwrite(file_path, data)
        return file_path

    def from_file(self, file_path):
        file_path = file_path + self.get_extension()
        img = cv2.imread(file_path)
        return img


class ZProjectionParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the
    interpolation type for the Preview.

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(ZProjectionParameterWidget, self).__init__()
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