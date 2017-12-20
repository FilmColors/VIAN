from core.data.interfaces import IAnalysisJob, ParameterWidget
from core.data.containers import *
from core.analysis.colorimetry.hilbert import *
from core.analysis.colorimetry.computation import *
from core.gui.ewidgetbase import EHtmlDisplay
from bokeh.embed import file_html
from bokeh.colors import RGB
from bokeh.resources import CDN
import numpy as np
from typing import List
import cv2
from core.data.computation import ms_to_frames
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class ColometricsAnalysis(IAnalysisJob):

    def __init__(self):
        super(ColometricsAnalysis, self).__init__(name="Colorimetry",
                                                  source_types=[SEGMENTATION, SCREENSHOT, SEGMENT, ANNOTATION_LAYER, MOVIE_DESCRIPTOR],
                                                  author="Gaudenz Halter",
                                                  version="0.0.1",
                                                  multiple_result=True)

    def prepare(self, project: ElanExtensionProject, targets: List[ITimeRange], parameters, fps):
        path = project.movie_descriptor.movie_path
        resolution = parameters['resolution']
        color_space = cv2.COLOR_BGR2Lab

        args = []
        for tgt in targets:
            args.append([path, ms_to_frames(tgt.get_start(), fps), ms_to_frames(tgt.get_end(), fps), resolution, color_space])

        return args

    def get_name(self):
        return self.name

    def process(self, args, sign_progress):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        color_space = args[3]
        resolution = args[4]
        cache_size = 100

        length = np.clip(int(end - start),1,None)
        data_size = int(np.ceil(length / resolution))
        data_size_cached = int(np.ceil(np.ceil(float(length / cache_size)) / resolution))
        video_capture = cv2.VideoCapture(movie_path)

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        grad_bokeh, grad_in_bgr = create_hilbert_color_pattern(8, 32)

        frame_stack = np.zeros(shape=(int(cache_size), height, width, 3), dtype=np.uint8)
        hist_stack = np.zeros(shape=(data_size_cached, 8, 8, 8))
        avg_color_tuples = np.zeros(shape=(data_size, 3))

        progress_counter = 0
        cache_counter = 0
        hist_counter = 0
        for i in range(length):
            ret, frame = video_capture.read()
            if i % resolution == 0:

                if progress_counter % 5 == 0:
                    progress = float(i) / length
                    sign_progress(progress)

                if frame is not None:
                    frame = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)
                    frame_stack[cache_counter] = frame
                    cache_counter += 1

                    # avg_color_tuples[progress_counter] = np.mean(frame, axis=(0, 1))

                if cache_counter == cache_size:
                    hist = calculate_histogram(frame_stack, 8)
                    hist_stack[hist_counter] = hist
                    frame_stack = np.zeros(shape=(cache_size, height, width, 3))
                    hist_counter += 1
                    cache_counter = 0


                progress_counter += 1

        # adding the Frames to the Hist_stack which haven reached the Cache-Limit
        if cache_counter != 0:
            frame_stack = frame_stack[:cache_counter]
            hist = calculate_histogram(frame_stack, 8)
            hist_stack[hist_counter] = hist



        result = np.sum(hist_stack, axis=0)
        result = np.divide(result, width * height)
        result = np.divide(result, length)
        hist = hilbert_mapping_3d(8, result, HilbertMode.Values_All)

        analysis = IAnalysisJobAnalysis("Colormetrics", [hist, grad_in_bgr], self.__class__, None)
        sign_progress(1.0)
        return analysis

    def get_parameter_widget(self):
        return ColormetricsPreferences()

    def plot_histogram(self, data, colors):
        colors_bokeh = []
        for c in colors:
            colors_bokeh.append(RGB(c[2], c[1], c[0]))

        colors = colors_bokeh
        y_range = [10 ** -10, 1]
        bottom = 10 ** -9
        floor = 10 ** -10
        x = range(len(data))
        tools = "wheel_zoom, box_zoom, reset,save"
        color_hist = figure(width=600, height=400, y_axis_type="log", y_range=y_range, tools=tools)
        color_hist.vbar(x=x, width=1, bottom=floor, top=bottom, color=colors, alpha=1.0)
        color_hist.vbar(x=x, width=1, bottom=bottom, top=data, color=colors, alpha=1.0)

        color_hist.title.text = "Histogram"
        color_hist.title.align = "center"
            # color_hist.title.text_font_size = title_size

        # color_hist.xaxis.axis_label_text_font_size = label_size
        # color_hist.yaxis.axis_label_text_font_size = label_size


        color_hist.xaxis.axis_label = "Histogram Bin"


        return color_hist

    def get_visualization(self, analysis: IAnalysisJobAnalysis, result_path, data_path):
        return EHtmlDisplay(None, file_html(self.plot_histogram(analysis.data[0], analysis.data[1]), CDN, "Histogram"))

    def get_preview(self, analysis):
        plot = self.plot_histogram(analysis[0], analysis[1])
        html = file_html(plot, CDN, "Histogram")
        return EHtmlDisplay(None, html)



class ColormetricsPreferences(ParameterWidget):
    def __init__(self):
        super(ColormetricsPreferences, self).__init__()
        path = os.path.abspath("qt_ui/Analysis_Colormetrics.ui")
        uic.loadUi(path, self)
        self.show()

    def get_parameters(self):
        resolution = self.resolutionFramesSpinBox.value()
        color_space = self.colorSpaceComboBox.currentText()
        parameters = dict(
            resolution=resolution,
            color_space=color_space,
        )
        return parameters
