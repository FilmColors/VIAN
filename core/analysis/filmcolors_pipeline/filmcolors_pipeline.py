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
import pyqtgraph as pg

from core.container.segmentation import Segment
from core.container.project import *
from core.visualization.feature_plot import *
from core.visualization.image_plots import *


#region #--- Analysis ---
class FilmColorsPipelineAnalysis(IAnalysisJob):

    def __init__(self):
        super(FilmColorsPipelineAnalysis, self).__init__(name="Filmcolors Pipeline",
                                                  source_types=[MOVIE_DESCRIPTOR],
                                                  author="Gaudenz Halter",
                                                  version="0.0.1",
                                                  multiple_result=False)

    def prepare(self, project: VIANProject, targets: List[ITimeRange], parameters, fps, class_objs = None):
        super(FilmColorsPipelineAnalysis, self).prepare(project, targets, parameters, fps, class_objs)
        path = project.movie_descriptor.get_movie_path()
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

        return win

    #endregion

    def get_visualization(self, analysis: IAnalysisJobAnalysis, result_path, data_path, project:VIANProject, main_window: QMainWindow):
        data = analysis.data

        cs_plots = ColorSpaceVis(None, data)
        feature_plot = FeaturePlotWidget(None, project)
        channel_dt = ChannelTimeVis(None, data)

        cs_plots.controls.onSourceChanged.connect(channel_dt.on_source_changed)
        cs_plots.controls.onChannelChanged.connect(channel_dt.on_channel_changed)
        cs_plots.controls.onNthImageChanged.connect(channel_dt.on_nth_frame_changed)

        tabs = [
            VisualizationTab(name="Color Space", widget=cs_plots, use_filter=True, controls=cs_plots.controls),
            VisualizationTab(name="Features", widget=feature_plot, use_filter=True, controls=None),
            VisualizationTab(name="Channels dT", widget=channel_dt, use_filter=True, controls=cs_plots.controls)
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

        self.filter_indices = []
        self.current_source = 0 # FOREGROUND, BACKGROUND, BOTH

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

        ctrl.onSourceChanged.connect(self.on_source_changed)

        self.layout().addItem(layout_left)

        self.controls = ctrl

        self.on_source_changed(0)
        self.show()

    @pyqtSlot(list)
    def on_filter(self, names):
        if len(names) == 0:
            self.filter_indices = []

        segments_time = []
        for word in names:
            for con in word.connected_items:
                if isinstance(con, Segment):
                    segments_time.append([con.get_start(), con.get_end()])

        image_frames = np.arange(0, self.data['m_duration'] - self.data['resolution'], self.data['resolution'])
        image_times = np.divide(np.multiply(image_frames, 1000), self.data['fps'])

        self.filter_indices = []
        for s in segments_time:
            self.filter_indices.extend(np.where((s[0]<=image_times) & (image_times<s[1]))[0].tolist())

        self.filter_indices = np.unique(np.array(self.filter_indices))
        self.on_source_changed(self.current_source)

    @pyqtSlot(int)
    def on_source_changed(self, index):
        self.current_source = index

        if index == SOURCE_BACKGROUND:
            self.plot_background()
        elif index == SOURCE_FOREGROUND:
            self.plot_foreground()
        else:
            self.plot_complete()

    def plot_complete(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_comp'].shape[0])

        c_sum = self.data['frame_lab_comp'][indices]
        thumbnails = self.data['thumbnails'][indices]

        self.image_plot_ab(c_sum[:, 0], c_sum[:, 1], c_sum[:, 2], thumbnails, view=self.ab_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 1], thumbnails, view=self.la_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 2], thumbnails, view=self.lb_view)

    def plot_foreground(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_fg'].shape[0])

        c_sum = self.data['frame_lab_fg'][indices]
        thumbnails = self.data['thumbnails_fg'][indices]

        self.image_plot_ab(c_sum[:, 0], c_sum[:, 1], c_sum[:, 2], thumbnails, view=self.ab_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 1], thumbnails, view=self.la_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 2], thumbnails, view=self.lb_view)

    def plot_background(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_bg'].shape[0])

        c_sum = self.data['frame_lab_bg'][indices]
        thumbnails = self.data['thumbnails_bg'][indices]

        self.image_plot_ab(c_sum[:, 0], c_sum[:, 1], c_sum[:, 2], thumbnails, view=self.ab_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 1], thumbnails, view=self.la_view)
        self.image_plot_la(c_sum[:, 0], c_sum[:, 2], thumbnails, view=self.lb_view)

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


class FeaturePlotWidget(QWidget):
    def __init__(self, parent, project):
        super(FeaturePlotWidget, self).__init__(parent)
        self.project = project

        self.setLayout(QHBoxLayout(self))
        self.plot = VIANFeaturePlot(self, project)
        self.layout().addWidget(self.plot)

    @pyqtSlot(list)
    def on_filter(self, names):
        self.plot.on_filter(names)


class ChannelTimeVis(QWidget):
    def __init__(self, parent, data):
        super(ChannelTimeVis, self).__init__(parent)
        self.data = data

        self.nth_frame = 30

        self.current_source = SOURCE_COMPLETE
        self.filter_indices = []

        self.setLayout(QHBoxLayout(self))
        self.view = ImagePlotTime(self)
        self.layout().addWidget(self.view)

        self.curr_channel = 0

        self.on_source_changed(self.current_source)


    @pyqtSlot(list)
    def on_filter(self, names):
        if len(names) == 0:
            self.filter_indices = []

        segments_time = []
        for word in names:
            for con in word.connected_items:
                if isinstance(con, Segment):
                    segments_time.append([con.get_start(), con.get_end()])

        image_frames = np.arange(0, self.data['m_duration'] - self.data['resolution'], self.data['resolution'])
        image_times = np.divide(np.multiply(image_frames, 1000), self.data['fps'])

        self.filter_indices = []
        for s in segments_time:
            self.filter_indices.extend(np.where((s[0]<=image_times) & (image_times<s[1]))[0].tolist())

        self.filter_indices = np.unique(np.array(self.filter_indices))
        self.on_source_changed(self.current_source)

    @pyqtSlot(int)
    def on_source_changed(self, index):
        self.current_source = index

        if index == SOURCE_BACKGROUND:
            self.plot_background()
        elif index == SOURCE_FOREGROUND:
            self.plot_foreground()
        else:
            self.plot_complete()

    @pyqtSlot(int)
    def on_channel_changed(self, idx):
        self.curr_channel = idx
        self.on_source_changed(self.current_source)

    @pyqtSlot(int)
    def on_nth_frame_changed(self, nth):
        self.nth_frame = nth
        self.on_source_changed(self.current_source)

    def plot_complete(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_comp'].shape[0])

        image_frames = np.arange(0, self.data['m_duration'] - self.data['resolution'], self.data['resolution'])
        image_times = np.divide(np.multiply(image_frames, 1000), self.data['fps'])

        c_sum = self.data['frame_lab_comp'][indices]
        thumbnails = self.data['thumbnails'][indices]

        self.plot(image_times, c_sum[:, self.curr_channel], thumbnails)

    def plot_foreground(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_fg'].shape[0])

        image_frames = np.arange(0, self.data['m_duration'] - self.data['resolution'], self.data['resolution'])
        image_times = np.divide(np.multiply(image_frames, 1000), self.data['fps'])
        c_sum = self.data['frame_lab_fg'][indices]
        thumbnails = self.data['thumbnails_fg'][indices]

        self.plot(image_times, c_sum[:, self.curr_channel], thumbnails)

    def plot_background(self):
        indices = self.filter_indices
        if len(self.filter_indices) == 0:
            indices = range(self.data['frame_lab_bg'].shape[0])

        image_frames = np.arange(0, self.data['m_duration'] - self.data['resolution'], self.data['resolution'])
        image_times = np.divide(np.multiply(image_frames, 1000), self.data['fps'])
        c_sum = self.data['frame_lab_bg'][indices]
        thumbnails = self.data['thumbnails_bg'][indices]

        self.plot(image_times, c_sum[:, self.curr_channel], thumbnails)


    def plot(self, time, channel, imgs, is_liminance = True):
        self.view.clear_view()

        indices = np.arange(0, channel.shape[0], self.nth_frame)
        time = np.array(time)[indices]
        channel = np.array(channel)[indices]
        imgs = np.array(imgs)[indices]
        if is_liminance:
            channel = np.multiply(np.divide(channel.astype(np.float32), 255), 100)

        for i, img in enumerate(imgs):
            self.view.add_image(time[i], channel[i], img, convert=False)

        self.view.update_grid()
        self.view.sort_images()



