from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.data.containers import *
from core.analysis.colorimetry.hilbert import *
from core.analysis.colorimetry.computation import *
from core.gui.ewidgetbase import EHtmlDisplay

import numpy as np
from typing import List
import cv2
import webbrowser
from core.data.computation import ms_to_frames
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import pyqtgraph as pg

class ColometricsAnalysis(IAnalysisJob):

    def __init__(self):
        super(ColometricsAnalysis, self).__init__(name="Colorimetry",
                                                  source_types=[MOVIE_DESCRIPTOR, SEGMENT],
                                                  author="Gaudenz Halter",
                                                  version="0.0.1",
                                                  multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[ITimeRange], parameters, fps):
        path = project.movie_descriptor.movie_path
        resolution = parameters['resolution']
        color_space = cv2.COLOR_BGR2Lab

        args = []

        # TODO Dirty hack because a Moviedescirptor returns Frames instead of MS on get_end() (STUPID... SHIT, Have fun finding its usage)
        for tgt in targets:
            if tgt.get_type() == MOVIE_DESCRIPTOR:
                args.append([path,
                             ms_to_frames(tgt.get_start(), fps),
                             tgt.get_end(),
                             resolution,
                             color_space,
                             parameters,
                             fps])
            else:
                args.append([path,
                             ms_to_frames(tgt.get_start(), fps),
                             ms_to_frames(tgt.get_end(), fps),
                             resolution,
                             color_space,
                             parameters,
                             fps])

        return args

    def get_name(self):
        return self.name

    def process(self, args, sign_progress):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        color_space = args[3]
        resolution = args[4]
        parameters = args[5]
        fps = args[6]

        print(start, end)
        length = np.clip(int(end - start),1,None)
        data_size = int(np.ceil(length / resolution))
        video_capture = cv2.VideoCapture(movie_path)

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        grad_bokeh, grad_in_bgr = create_hilbert_color_pattern(8, 32)

        frame_pos = np.zeros(shape=(data_size, 1), dtype=np.uint16)
        hist_stack = np.zeros(shape=(data_size, 16, 16, 16), dtype=np.float16)
        avg_color_tuples = np.zeros(shape=(data_size, 3), dtype=np.uint8)

        progress_counter = 0
        hist_counter = 0

        for i in range(length):
            ret, frame = video_capture.read()
            if i % resolution == 0:

                if progress_counter % 2 == 0:
                    progress = float(i) / length
                    sign_progress(progress)

                if frame is not None:
                    # Colorspace Conversion
                    frame_pos[hist_counter] = i
                    frame_lab = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)

                    # Histogram
                    hist = calculate_histogram(frame_lab, 16)
                    hist_stack[hist_counter] = hist

                    # AVG Color
                    avg_color_tuples[hist_counter] = np.mean(frame_lab, axis=(0, 1))

                    hist_counter += 1


                progress_counter += 1

        # result = np.sum(hist_stack, axis=0)
        # result = np.divide(result, width * height)
        # result = np.divide(result, length)
        # hist = hilbert_mapping_3d(8, result, HilbertMode.Values_All)

        # Normalize Hist
        hist_stack = np.divide(hist_stack, (width * height))
        print(hist_stack.nbytes / 1000000, "MB")



        result = dict(
            fps = fps,
            hist_stack = hist_stack,
            avg_colors = avg_color_tuples,
            frame_pos=frame_pos
        )

        analysis = ColometricsAnalysis(result, self.__class__, parameters)

        sign_progress(1.0)
        return analysis

    def get_parameter_widget(self):
        return ColormetricsPreferences()

    def create_graph_plot(self, analysis):
        pg.setConfigOption("background", pg.mkColor(30, 30, 30))
        win = pg.GraphicsWindow(title="Colorimetry Results")
        pg.setConfigOptions(antialias=True)
        l = pg.GraphicsLayout(border=(100, 100, 100))
        win.setCentralWidget(l)

        frame_pos = analysis.data['frame_pos']

        lum_dt = np.multiply(np.divide(analysis.data["avg_colors"][:, 0], 255), 100)
        a_dt = np.subtract(analysis.data["avg_colors"][:, 1].astype(np.int16), 128)
        b_dt = np.subtract(analysis.data['avg_colors'][:, 2].astype(np.int16), 128)

        major_ticks = []
        minor_ticks = []
        step = int(round(lum_dt.shape[0] / 5, 0))
        for i in range(frame_pos.shape[0]):
            if i % step == 0:
                major_ticks.append((i, ms_to_string(frame2ms(frame_pos[i], fps=analysis.data['fps']))))
            else:
                minor_ticks.append(
                    (i, ms_to_string(frame2ms(frame_pos[i], fps=analysis.data['fps']))))
        h_axis1 = pg.AxisItem("bottom")
        h_axis2 = pg.AxisItem("bottom")
        h_axis3 = pg.AxisItem("bottom")
        h_axis1.setTicks([major_ticks, minor_ticks])
        h_axis2.setTicks([major_ticks, minor_ticks])
        h_axis3.setTicks([major_ticks, minor_ticks])

        plot_lum = l.addPlot(title="L-Channel", y=lum_dt, axisItems=dict(bottom=h_axis1), name="LChannel", row=0,
                             column=0, colspan=2)
        plot_lum.setYRange(0, 100)
        plot_lum.setXLink('AChannel')
        l.nextRow()
        plot_a = l.addPlot(title="a-Channel", y=a_dt, axisItems=dict(bottom=h_axis2), name="AChannel", row=1, column=0,
                           colspan=2)
        plot_a.setYRange(-128, 128)
        plot_a.setYLink("BChannel")
        plot_a.setXLink('BChannel')

        l.nextRow()
        plot_b = l.addPlot(title="b-Channel", y=b_dt, axisItems=dict(bottom=h_axis3), name="BChannel", row=2, column=0,
                           colspan=2)
        plot_b.setYRange(-128, 128)

        print(np.amin(b_dt),
              np.amax(b_dt),
              np.amin(analysis.data['avg_colors'][:, 2]),
              np.amax(analysis.data['avg_colors'][:, 2]))
        return win

    def get_visualization(self, analysis: IAnalysisJobAnalysis, result_path, data_path, project:VIANProject, main_window: QMainWindow):

        p_graphs = self.create_graph_plot(analysis)


        return [VisualizationTab(name="Colorimetric", widget=p_graphs)]
        # mw = EDockWidget(main_window, limit_size=False)
        # mw.setWindowTitle("Colorimetry Result")
        # mw.setWidget(win)
        #
        # main_window.addDockWidget(Qt.RightDockWidgetArea, mw, Qt.Horizontal)

        # hist = self.plot_histogram(analysis.data[0], analysis.data[1])
        # l = layout([
        #     [hist]
        # ])
        #
        # path = data_path + "/" + analysis.get_name() + ".html"
        # save(l, path)
        #
        # open_web_browser(path)

    def get_preview(self, analysis):
        widget = QWidget()
        widget.setLayout(QVBoxLayout(widget))

        try:
            avg_c = analysis.data['avg_colors']
        except:
            print(analysis.data.items())

        n_sample = QHBoxLayout(widget)
        n_sample.addWidget(QLabel("n-Samples: ", widget))
        n_sample.addWidget(QLabel(str(avg_c.shape[0]), widget))

        avg_color = QHBoxLayout(widget)
        avg_color.addWidget(QLabel("Average Color: ", widget))
        avg_color.addWidget(QLabel("L:" + str(np.round(np.mean(avg_c[:,0]) / 255 * 100, 0)) + " " +
                                   "a:" + str(np.round(np.mean(avg_c[:,1]),0) - 128) + " " +
                                   "b:" + str(np.round(np.mean(avg_c[:,2]),0) - 128), widget))


        widget.layout().addItem(n_sample)
        widget.layout().addItem(avg_color)
        widget.show()
        return widget
        # plot = self.plot_histogram(analysis.data[0], analysis.data[1])
        # html = file_html(plot, CDN, "Histogram")
        # return EHtmlDisplay(None, html)


class ColormetryVisualization(EDockWidget):
    def __init__(self, main_window):
        super(ColormetryVisualization, self).__init__(main_window, limit_size=False)


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
