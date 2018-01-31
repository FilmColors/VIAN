"""
    result = dict(
        resolution = resolution,
        fps = fps,
        m_width = m_width,
        m_height = m_height,
        m_duration = m_duration,
        n_data = n_data,        # for later convenience
        thumbnails = thumbnails,
        thumbnails_fg = thumbnails_fg,
        thumbnails_bg = thumbnails_bg,
        z_projection_imagej = z_projection_imagej,
        frame_rgb = avg_colors_rgb,
        frame_lab_fg = avg_colors_lab_fg,
        frame_lab_bg =avg_colors_lab_bg,
        movie_hist_fg = movie_hist_fg,
        movie_hist_bg = movie_hist_bg,
        frame_hists_fg = color_hists_fg,
        frame_hists_bg = color_hists_bg,
        segment_hist = None,
        segment_rgb = None,
        segment_lab = None,
        segment_zprojection = None,
    )
    
"""


from core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab
from core.data.containers import *
from core.analysis.colorimetry.computation import *

import numpy as np
from typing import List
import cv2
from core.data.computation import ms_to_frames
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from core.visualization.image_plots import *



import pyqtgraph as pg

#region #--- Analysis ---
class FilmColorsPipelineAnalysis(IAnalysisJob):

    def __init__(self):
        super(FilmColorsPipelineAnalysis, self).__init__(name="Filmcolors Pipeline",
                                                  source_types=[MOVIE_DESCRIPTOR],
                                                  author="Gaudenz Halter",
                                                  version="0.0.1",
                                                  multiple_result=False)

    def prepare(self, project: ElanExtensionProject, targets: List[ITimeRange], parameters, fps):
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
        pass

    def get_parameter_widget(self):
        return FilmColorsPipelinePreferences()

    #region #--- VISUALIZATIONS ---
    def graph_plot(self, l, a, b, frame_pos, fps):
        pg.setConfigOption("background", pg.mkColor(30, 30, 30))
        win = pg.GraphicsWindow(title="Colorimetry Results")
        pg.setConfigOptions(antialias=True)
        l = pg.GraphicsLayout(border=(100, 100, 100))
        win.setCentralWidget(l)

        frame_pos = frame_pos

        lum_dt = np.multiply(np.divide(l , 255), 100)
        a_dt = np.subtract(a.astype(np.int16), 128)
        b_dt = np.subtract(b.astype(np.int16), 128)

        major_ticks = []
        minor_ticks = []
        step = int(round(lum_dt.shape[0] / 5, 0))
        for i in range(frame_pos.shape[0]):
            if i % step == 0:
                major_ticks.append((i, ms_to_string(frame2ms(frame_pos[i], fps=fps))))
            else:
                minor_ticks.append(
                    (i, ms_to_string(frame2ms(frame_pos[i], fps=fps))))
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
              np.amin(a),
              np.amax(a))
        return win

    #endregion

    def get_visualization(self, analysis: IAnalysisJobAnalysis, result_path, data_path, project:ElanExtensionProject, main_window: QMainWindow):
        data = analysis.data

        cs_plots = ColorSpaceVis(None, data)

        tabs = [
            VisualizationTab(name="ColorSpace Plots", widget=cs_plots)
        ]

        return tabs

    def get_preview(self, analysis):
        return QLabel("FilmColors Pipeline")
        # plot = self.plot_histogram(analysis.data[0], analysis.data[1])
        # html = file_html(plot, CDN, "Histogram")
        # return EHtmlDisplay(None, html)


class FilmColorsPipelinePreferences(ParameterWidget):
    def __init__(self):
        super(FilmColorsPipelinePreferences, self).__init__()
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

#endregion

class ColorSpaceVis(QWidget):
    def __init__(self, parent, data):
        super(ColorSpaceVis, self).__init__(parent)
        self.data = data

        self.ab_view = ImagePlotCircular(self)
        self.la_view = ImagePlotPlane(self, range_x=[-128, 128], range_y=[0, 100], title="L-a Plane")
        self.lb_view = ImagePlotPlane(self, range_x=[-128, 128], range_y=[0, 100], title="L-b Plane")

        self.setLayout(QHBoxLayout(self))

        ctrl = ImagePlotControls(self.ab_view)
        self.ab_view.add_controls(ctrl)

        ctrl.onLowCutChange.connect(self.ab_view.on_low_cut)
        ctrl.onHighCutChange.connect(self.ab_view.on_high_cut)
        self.layout().addWidget(self.ab_view)

        layout_left = QVBoxLayout(self)

        ctrl.onLowCutChange.connect(self.la_view.on_low_cut)
        ctrl.onHighCutChange.connect(self.la_view.on_high_cut)
        layout_left.addWidget(self.la_view)

        self.lb_view.setParent(self)

        ctrl.onLowCutChange.connect(self.lb_view.on_low_cut)
        ctrl.onHighCutChange.connect(self.lb_view.on_high_cut)
        layout_left.addWidget(self.lb_view)

        self.layout().addItem(layout_left)

        self.plot_foreground()
        self.show()

    def plot_complete(self):
        c_sum = np.divide(np.add(self.data['frame_lab_fg'], self.data['frame_lab_bg']), 2.0)
        print("TEST", np.amax(c_sum), np.amin(c_sum))

        self.image_plot_ab(c_sum[:, 0], c_sum[:, 1], c_sum[:, 2], self.data['thumbnails'], view=self.ab_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 1], self.data['thumbnails'], view=self.la_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 2], self.data['thumbnails'], view=self.lb_view)

    def plot_foreground(self):
        c_sum = self.data['frame_lab_fg']

        self.image_plot_ab(c_sum[:, 0], c_sum[:, 1], c_sum[:, 2], self.data['thumbnails_fg'], view=self.ab_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 1], self.data['thumbnails_fg'], view=self.la_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 2], self.data['thumbnails_fg'], view=self.lb_view)

    def plot_background(self):
        pass

    def image_plot_ab(self, luminances, xs, ys, imgs, range_x=None, range_y=None, view = None):
        if view is None:
            view = ImagePlotCircular(None)
        else:
            view.clear_view()
            view.add_grid()

        luminances = np.multiply(np.divide(luminances.astype(np.float32), 255), 100)

        for i, img in enumerate(imgs):
            view.add_image(xs[i], ys[i], img, convert=False, luminance=luminances[i])

        view.sort_images()
        return view

    def image_plot_la(self, l, a, imgs, range_x=None, range_y=None, title="", view = None):
        if view is None:
            view = ImagePlotPlane(None, range_x=[-128, 128], range_y=[0, 100], title=title)
        else:
            view.clear_view()
            view.add_grid()

        a = np.subtract(a.astype(np.float32), 128)
        l = np.multiply(np.divide(l.astype(np.float32), 255), 100)

        for i, img in enumerate(imgs):
            view.add_image(a[i], l[i], img, convert=False)

        view.sort_images()

        return view
