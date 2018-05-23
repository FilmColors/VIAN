from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.data.containers import *
from core.analysis.colorimetry.hilbert import *
from core.analysis.colorimetry.computation import *
from core.gui.ewidgetbase import EGraphicsView #, GraphicsViewDockWidget

import numpy as np
from typing import List
import cv2
import webbrowser
from core.data.computation import ms_to_frames
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *



class MovieMosaicAnalysis(IAnalysisJob):
    def __init__(self):
        super(MovieMosaicAnalysis, self).__init__(name = "Movie Mosaic",
                                                  source_types=[MOVIE_DESCRIPTOR, SEGMENT, ANNOTATION],
                                                  help_path = "",
                                                  author="Gaudenz Halter",
                                                  version = "0.0.1",
                                                  multiple_result=True)

    def prepare(self, project, targets, parameters, fps):
        args = []
        for t in targets:
            if t.get_type() == MOVIE_DESCRIPTOR:
                start = ms_to_frames(t.get_start(), fps)
                end = t.get_end()
            else:
                start = ms_to_frames(t.get_start(), fps)
                end = ms_to_frames(t.get_end(), fps)
            args.append([start, end, project.movie_descriptor.get_movie_path(), parameters])

        return args


    def process(self, args, sign_progress):
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

        analysis = IAnalysisJobAnalysis("Mosaic", result, self.__class__, parameters=param)
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
        gw = EGraphicsView(None, main_window=analysis.project.main_window)
        gw.set_image(numpy_to_pixmap(analysis.data["mosaic"]))
        return gw


    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        view = EGraphicsView(None, False, main_window)
        view.set_image(numpy_to_pixmap(analysis.data["mosaic"]))
        return [VisualizationTab("Mosaic", widget=view, use_filter=False, controls=None)]


    def get_parameter_widget(self):
        return MovieMosaicPreferences()


    def from_database(self, database_data):
        return np.array(eval(database_data.decode()))

    def to_database(self, container_data):
        return np.array2string(container_data['mosaic'], separator=",").encode()



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
