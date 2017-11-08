from core.data.interfaces import IAnalysisJob
from core.data.containers import *
from extensions.colormetrics.hilbert import *
from extensions.colormetrics.computation import *
import numpy as np
import cv2

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class ColometricsAnalysis(IAnalysisJob):
    name = "Colormetrics"
    source_types = [SEGMENTATION, SCREENSHOT, SEGMENT, ANNOTATION_LAYER, MOVIE_DESCRIPTOR]

    def __init__(self, id):
        self.name = "Colormetrics"
        self.procedure_id = id
        self.resolution = 10
        self.color_space = cv2.COLOR_BGR2Lab

    def prepare(self, path, target):
        args = [path, target.get_start(), target.get_end(), self.resolution, self.color_space]
        return args

    def get_name(self):
        return self.name

    def process(self, target_id, args, sign_progress):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        color_space = args[3]
        resolution = args[4]

        length = int(end - start)
        data_size = int(np.ceil(float(end - start) / resolution))
        video_capture = cv2.VideoCapture(movie_path)

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        grad_bokeh, grad_in_bgr = create_hilbert_color_pattern(8, 32)

        hist_stack = np.zeros(shape=(data_size, 8, 8, 8))
        avg_color_tuples = np.zeros(shape=(data_size, 3))

        progress_counter = 0
        for i in range(length):
            ret, frame = video_capture.read()
            if i % resolution == 0:

                if progress_counter % 10 == 0:
                    progress = float(i) / length
                    sign_progress(progress)

                if frame is not None:
                    frame = cv2.cvtColor(frame.astype(np.uint8), color_space)
                    hist = calculate_histogram(frame, 8)
                    hist_stack[progress_counter] = hist

                    avg_color_tuples[progress_counter] = np.mean(frame, axis=(0,1))

                progress_counter += 1

        result = np.sum(hist_stack, axis=0)
        result = np.divide(result, length * width * height)
        hist = hilbert_mapping_3d(8, result, HilbertMode.Values_All)

        analysis = Analysis("Colormetrics", start, end, [hist, grad_in_bgr[0], hist_stack, avg_color_tuples], procedure_id=self.procedure_id, target_id=target_id)
        sign_progress(1.0)
        return analysis

    def get_preferences(self):
        return ColormetricsPreferences(None, self)


class ColormetricsPreferences(QWidget):
    def __init__(self, parent, colormetrics_analysis):
        super(ColormetricsPreferences, self).__init__(parent)
        self.colormetrics_analysis = colormetrics_analysis
        path = os.path.abspath("qt_ui/Analysis_Colormetrics.ui")
        uic.loadUi(path, self)
        self.show()
