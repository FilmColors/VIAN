from core.container.project import *
import cv2
import numpy as np
from PyQt5 import uic
import pickle

from core.analysis.colorimetry.computation import *
from core.data.enums import DataSerialization
from core.data.computation import ms_to_frames
from core.container.project import *
from core.gui.ewidgetbase import EGraphicsView  # , GraphicsViewDockWidget
from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.container.hdf5_manager import vian_analysis


@vian_analysis
class MovieMosaicAnalysis(IAnalysisJob):
    def __init__(self):
        super(MovieMosaicAnalysis, self).__init__(name = "Movie Mosaic",
                                                  source_types=[MOVIE_DESCRIPTOR, SEGMENT, ANNOTATION],
                                                  dataset_name="Mosaics",
                                                  dataset_shape=(1024, 1024, 3),
                                                  dataset_dtype=np.uint8,
                                                  help_path = "",
                                                  author="Gaudenz Halter",
                                                  version = "0.0.1",
                                                  multiple_result=True)

    def prepare(self, project, targets, fps, class_objs = None):
        super(MovieMosaicAnalysis, self).prepare(project, targets, fps, class_objs)
        args = []
        for t in targets:
            if t.get_type() == MOVIE_DESCRIPTOR:
                start = ms_to_frames(t.get_start(), fps)
                end = t.get_end()
            else:
                start = ms_to_frames(t.get_start(), fps)
                end = ms_to_frames(t.get_end(), fps)
            args.append([start, end, project.movie_descriptor.get_movie_path(), t.get_id()])

        return args

    def process(self, args, sign_progress):
        args, sign_progress = super(MovieMosaicAnalysis, self).process(args, sign_progress)
        start = args[0]
        end = args[1]
        path = args[2]
        param = args[3]
        resolution = param['resolution']
        method = param['method']
        per_row = param['per_row']

        if method == "Average Color Patches":
            result =  self.mosaic_color_patches(start, end, path, resolution, per_row, sign_progress)
        else:
            result = self.mosaic_frame_patches(start, end, path, resolution, per_row, sign_progress)

        analysis = IAnalysisJobAnalysis(name="Mosaic",
                                        results = result,
                                        analysis_job_class=self.__class__,
                                        parameters=param,
                                        container=args[4])
        return analysis

    def mosaic_color_patches(self, start, end, path, resolution, per_row, sign_progress):

        capture = cv2.VideoCapture(path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, start)
        # end = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        n_width = 50
        n_height = 50
        length = int((end - start) / resolution)

        images = np.zeros(shape=(length, n_width, n_height, 3), dtype=np.uint8)
        for i in range(length):
            sign_progress(i / length)
            capture.set(cv2.CAP_PROP_POS_FRAMES, float(i * resolution))
            ret, frame = capture.read()
            col = np.mean(frame.astype(np.float32), axis=(0, 1)).astype(np.uint8)
            images[i, :, :] = col

        columns = int(np.ceil(length / per_row))
        final = np.zeros(shape=(columns * n_height, per_row * n_width, 3), dtype=np.uint8)

        counter = 0
        for i in range(columns):
            for j in range(per_row):
                if counter < images.shape[0]:
                    final[i * n_height: i * n_height + n_height,
                    j * n_width: j * n_width + n_width] = images[counter]
                    counter += 1
                else:
                    break

        result = dict(
            mosaic=final
        )
        return result

    def mosaic_frame_patches(self, start, end, path, resolution, per_row, sign_progress):
        capture = cv2.VideoCapture(path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        n_width = 100
        n_height = int((100 / width) * height)
        length = int((end - start) / resolution)

        images = np.zeros(shape=(length, n_height, n_width, 3), dtype=np.uint8)
        for i in range(length):
            sign_progress(i / length)
            capture.set(cv2.CAP_PROP_POS_FRAMES, i * resolution)
            ret, frame = capture.read()

            images[i] = cv2.resize(frame, (n_width, n_height), interpolation=cv2.INTER_CUBIC)

        columns = int(np.ceil(length / per_row))
        final = np.zeros(shape=(columns * n_height, per_row * n_width, 3), dtype=np.uint8)

        counter = 0
        for i in range(columns):
            for j in range(per_row):
                if counter < images.shape[0]:
                    final[i * n_height: i * n_height + n_height,
                    j * n_width: j * n_width + n_width] = images[counter]
                    counter += 1
                else:
                    break

        result = dict(
            mosaic=final
        )


        return result

    def get_preview(self, analysis):
        gw = EGraphicsView(None)
        gw.set_image(numpy_to_pixmap(analysis.get_adata()["mosaic"]))
        return gw

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        view = EGraphicsView(None, False, main_window)
        view.set_image(numpy_to_pixmap(analysis.get_adata()["mosaic"]))
        return [VisualizationTab("Mosaic", widget=view, use_filter=False, controls=None)]

    def get_parameter_widget(self):
        return MovieMosaicPreferences()

    def to_hdf5(self, data):
        pass

    def from_hdf5(self, db_data):
        pass



class MovieMosaicPreferences(ParameterWidget):
    def __init__(self):
        super(MovieMosaicPreferences, self).__init__()
        path = os.path.abspath("qt_ui/Analysis_MovieMosaic.ui")
        uic.loadUi(path, self)
        self.comboBox_Method.addItems(["Average Color Patches", "Frames"])
        self.show()

    def get_parameters(self):
        resolution = self.spinBox_Resolution.value()
        parameters = dict(
            resolution=resolution,
            method= self.comboBox_Method.currentText(),
            per_row = self.spinBox_ImageRow.value()
        )
        return parameters
