from PyQt5 import QtWidgets, QtCore

from core.data.computation import ms_to_string
from core.container.project import *
from core.gui.context_menu import open_context_menu
from core.gui.drawing_widget import TIMELINE_SCALE_DEPENDENT
from core.gui.ewidgetbase import ImagePreviewPopup, TextEditPopup
import time

class TimelineContainer(EDockWidget):
    def __init__(self, main_window):
        super(TimelineContainer, self).__init__(main_window, limit_size=False, height=300)
        self.timeline = Timeline(main_window, self)
        self.setWidget(self.timeline)
        self.setWindowTitle("Timeline")
        self.resize(self.width(), 400)


        # self.toolbar = EToolBar(self)
        # self.toolbar.setWindowTitle("Timeline Toolbar")
        self.menu_create = self.inner.menuBar().addMenu("Create")
        self.a_create_segmentation = self.menu_create.addAction("New Segmentation")
        self.a_create_annotation_layer = self.menu_create.addAction("New Annotation Layer")
        self.a_create_annotation_layer.triggered.connect(partial(self.timeline.create_layer, []))
        self.a_create_segmentation.triggered.connect(self.timeline.create_segmentation)

        self.menu_tools = self.inner.menuBar().addMenu("Tools")
        self.a_cut_segment = self.menu_tools.addAction("Cut Segments")
        self.a_cut_segment.triggered.connect(self.on_cut_tools)
        self.a_merge_segment = self.menu_tools.addAction("Merge Segments")
        self.a_merge_segment.triggered.connect(self.on_merge_tool)
        self.menu_tools.addSeparator()
        self.a_tools_toolbar = self.menu_tools.addAction("Show Toolbar")
        self.a_tools_toolbar.triggered.connect(self.show_toolbar)
        self.a_tools_toolbar.setCheckable(True)
        self.a_tools_toolbar.setChecked(True)
        # self.a_merge_segments = self.menu_tools.addAction("Merge Segments")
        # self.a_merge_segments.triggered.connect(self.on_cut_tools)

        self.menu_display = self.inner.menuBar().addMenu("Display")
        self.a_show_id = self.menu_display.addAction("\tID")
        self.a_show_id.setCheckable(True)
        self.a_show_id.setChecked(True)

        self.a_show_name = self.menu_display.addAction("\tName")
        self.a_show_name.setCheckable(True)
        self.a_show_name.setChecked(False)

        self.a_show_text = self.menu_display.addAction("\tText")
        self.a_show_text.setCheckable(True)
        self.a_show_text.setChecked(True)

        self.menu_display.addSeparator()

        self.a_show_time_indicator = self.menu_display.addAction("\tShow Time Indicator")
        self.a_show_time_indicator.setCheckable(True)
        self.a_show_time_indicator.setChecked(True)

        self.menu_options = self.inner.menuBar().addMenu("Options")
        self.a_inhibit_overlap = self.menu_options.addAction("\tInhibit Overlap")
        self.a_inhibit_overlap.setCheckable(True)
        self.a_inhibit_overlap.setChecked(True)
        self.a_inhibit_overlap.triggered.connect(self.update_settings)

        self.a_forward_segmentation = self.menu_options.addAction("\tForward Segmentation")
        self.a_forward_segmentation.setCheckable(True)
        self.a_forward_segmentation.setChecked(False)
        self.a_forward_segmentation.triggered.connect(self.update_settings)

        self.a_kee_slider_in_view = self.menu_options.addAction("\tFollow Time Scrubber")
        self.a_kee_slider_in_view.setCheckable(True)
        self.a_kee_slider_in_view.setChecked(True)
        self.a_kee_slider_in_view.triggered.connect(self.update_settings)

        self.a_use_grid = self.menu_options.addAction("\tUse Grid")
        self.a_use_grid.setCheckable(True)
        self.a_use_grid.setChecked(self.main_window.settings.USE_GRID)
        self.a_use_grid.triggered.connect(self.update_settings)

        self.a_show_id.triggered.connect(self.update_settings)
        self.a_show_name.triggered.connect(self.update_settings)
        self.a_show_text.triggered.connect(self.update_settings)

        self.toolbar = TimelineToolbar(self, self.timeline)
        self.inner.addToolBar(Qt.LeftToolBarArea, self.toolbar)


        # self.inner.addToolBar(self.toolbar)

    def resizeEvent(self, *args, **kwargs):
        super(TimelineContainer, self).resizeEvent(*args, **kwargs)
        self.timeline.update_time_bar()

    def on_cut_tools(self):
        self.timeline.activate_cutting_tool()

    def on_merge_tool(self):
        self.timeline.activate_merge_tool()

    def show_toolbar(self):
        if self.a_tools_toolbar.isChecked():
            if self.toolbar is None:
                self.toolbar = TimelineToolbar(self, self.timeline)
                self.inner.addToolBar(Qt.LeftToolBarArea, self.toolbar)

            else:
                self.inner.addToolBar(Qt.LeftToolBarArea, self.toolbar)
            self.toolbar.show()
        else:
            self.toolbar.hide()

    def update_settings(self):
        self.timeline.show_id = self.a_show_id.isChecked()
        self.timeline.show_name = self.a_show_name.isChecked()
        self.timeline.show_text = self.a_show_text.isChecked()
        self.timeline.inhibit_overlap = self.a_inhibit_overlap.isChecked()
        self.timeline.settings.USE_GRID = self.a_use_grid.isChecked()

        self.timeline.show_time_indicator = self.a_show_time_indicator.isChecked()

        self.timeline.is_forward_segmenting = self.a_forward_segmentation.isChecked()
        self.timeline.keep_slider_in_view = self.a_kee_slider_in_view.isChecked()

        self.timeline.on_timeline_settings_update()


class TimelineToolbar(QToolBar):
    def __init__(self, parent, timeline):
        super(TimelineToolbar, self).__init__(parent)
        self.timeline = timeline

        self.a_move = self.addAction(create_icon("qt_ui/icons/icon_move.png"), "")
        self.a_move.triggered.connect(self.timeline.activate_move_tool)
        self.a_move.setToolTip("Move Tool")
        self.a_cut = self.addAction(create_icon("qt_ui/icons/icon_cut.png"),"Cut")
        self.a_cut.triggered.connect(self.timeline.activate_cutting_tool)
        self.a_cut.setToolTip("Cut Tool")
        self.a_merge = self.addAction(create_icon("qt_ui/icons/icon_merge.png"),"Merge")
        self.a_merge.triggered.connect(self.timeline.activate_merge_tool)
        self.a_merge.setToolTip("Merge Tool")


class Timeline(QtWidgets.QWidget, IProjectChangeNotify, ITimeStepDepending):
    def __init__(self, main_window, parent):
        super(Timeline, self).__init__(parent)
        path = os.path.abspath("qt_ui/Timeline.ui")
        uic.loadUi(path, self)
        #self.setMinimumHeight(50)
        self.main_window = main_window
        self.settings = main_window.settings

        self.scrubber_width = 10
        self.time_scrubber = TimelineScrubber(self.frame_Bars, main_window.player, self)
        self.scrubber_min_h = 400
        self.duration = 5400000
        self.curr_movie_time = 0
        self.scale = 100

        self.is_scaling = False
        self.is_selecting = False
        self.shift_pressed = False
        self.is_marquee_selecting = False
        self.is_cutting = False
        self.is_merging = False

        self.item_segments = []
        self.item_screenshots = []
        self.item_ann_layers = []
        self.items = []

        self.bar_height_min = 10
        self.group_height = 25
        self.controls_width = 200
        self.time_bar_height = 50
        self.timeline_tail = 100
        self.opencv_frame_scale_threshold = 200

        self.time_bar = None
        self.frame_Bars.setFixedSize(self.duration, 500)
        self.frame_Bars.move(self.controls_width, 0)
        self.frame_Controls.setFixedSize(self.controls_width, 500)
        self.frame_Controls.move(0, 0)
        self.relative_corner = QtCore.QPoint(self.controls_width, 0)

        self.selected = None
        self.multi_selected = []

        self.interval_segmentation_start = None
        self.interval_segmentation_marker = None

        self.selector_context = None
        self.selector = None

        self.lay_controls = QtWidgets.QVBoxLayout()
        self.lay_bars = QtWidgets.QVBoxLayout()
        self.frame_Controls.setLayout(self.lay_controls)
        self.frame_Bars.setLayout(self.lay_bars)
        self.frame_Bars.installEventFilter(self)

        self.scrollArea.horizontalScrollBar().valueChanged.connect(self.scroll_h)
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.scroll_v)
        self.scrollArea.installEventFilter(self)

        # Settings
        self.show_id = True
        self.show_name = False
        self.show_text = True
        self.is_forward_segmenting = False
        self.keep_slider_in_view = True

        self.inhibit_overlap = True
        self.show_time_indicator = True

        self.cutting_indicator = None
        self.merging_indicator = None
        self.merge_containers = None

        self.update_time_bar()
        self.update_ui()

        self.scrollArea.wheelEvent = self.func_tes

        self.main_window.onTimeStep.connect(self.on_timestep_update)

        self.main_window.actionIntervalSegmentStart.triggered.connect(self.on_interval_segment_start)
        self.main_window.actionIntervalSegmentEnd.triggered.connect(self.on_interval_segment_end)


        self.time_label = QLabel("00:00:00::1000", self)
        self.time_label.setMinimumWidth(150)
        self.time_label.setStyleSheet("QLabel{"
                                      "background: rgba(30,30,30,200); "
                                      "border: 1px solid black; "
                                      "margin: 5px,5px,5px,5px;"
                                      "}")
        self.set_time_indicator_visibility(False)
        # self.update_timer = QtCore.QTimer()
        # self.update_timer.setInterval(100)
        # self.update_timer.timeout.connect(self.update_time)
        # self.update_timer.start()

        self.scroll_block = False
        self.scroll_h_timer = QTimer()
        self.scroll_h_timer.setInterval(30)
        self.scroll_h_timer.timeout.connect(self.on_scroll_h_timeout)
        self.show()

    def func_tes(self, WheelEvent):
        dummy = None

    def project(self):
        return self.parent().parent().project()

    def scroll_h(self):
        value= int(self.scrollArea.horizontalScrollBar().value())
        self.frame_Controls.move(self.scrollArea.mapToParent(QtCore.QPoint(value, 0)))
        self.relative_corner = QtCore.QPoint(value, self.relative_corner.y())
        self.time_bar.move(self.relative_corner)

    def scroll_v(self):
        value = self.scrollArea.verticalScrollBar().value()
        # self.time_bar.move(self.scrollArea.mapToParent(QtCore.QPoint(0, value)))
        self.relative_corner = QtCore.QPoint(self.relative_corner.x(), value)
        self.time_bar.move(self.relative_corner)
        self.time_bar.raise_()
        self.time_scrubber.raise_()

    @pyqtSlot(object)
    def add_segmentation(self, segmentation):
        control = TimelineSegmentationControl(self.frame_Controls, self, segmentation)
        bars = TimelineSegmentationBar(self.frame_Bars, self, control, segmentation)
        for i, s in enumerate(segmentation.segments):
            bars.add_slice(s)
        item = [control, [bars], self.bar_height_min]
        self.item_segments.append(item)
        self.items.append(item)
        self.update_ui()

    def on_interval_segment_start(self):
        if self.interval_segmentation_marker is not None:
            self.interval_segmentation_marker.deleteLater()

        if self.selected is not None and self.selected.get_type() == SEGMENTATION:
                self.interval_segmentation_start = self.curr_movie_time
                self.interval_segmentation_marker = TimelineTimemark(self.frame_Bars, QColor(30, 200, 30, 100))
                self.interval_segmentation_marker.move(QPoint(self.interval_segmentation_start / self.scale, 0))
                self.interval_segmentation_marker.setFixedHeight(self.height())
        else:

            self.main_window.print_message("No Segmentation Selected", "Orange")

    def on_interval_segment_end(self):
        if self.selected is not None and self.interval_segmentation_marker is not None:
            if self.selected.get_type() == SEGMENTATION:
                # self.selected.create_segment(self.interval_segmentation_start,
                #                              self.curr_movie_time,
                #                              forward_segmenting=False,
                #                              inhibit_overlap=self.inhibit_overlap)
                self.selected.create_segment2(self.interval_segmentation_start,
                                              self.curr_movie_time,
                                              mode=SegmentCreationMode.INTERVAL,
                                              inhibit_overlap=self.inhibit_overlap)
            else:
                self.main_window.print_message("No Segmentation Selected", "Orange")

            self.interval_segmentation_start = None
            self.interval_segmentation_marker.deleteLater()
            self.interval_segmentation_marker = None
        else:

            self.main_window.print_message("Please set a Start Point First", "Orange")

    @pyqtSlot(object)
    def add_annotation_layer(self, layer):
        control = TimelineAnnotationLayerControl(self.frame_Controls, self, layer)
        height = self.bar_height_min
        bars = []
        for i, a in enumerate(layer.annotations):
            new = TimelineAnnotationBar(self.frame_Bars, self, control, self.group_height)
            new.add_slice(a)
            keys = []
            for k in a.keys:
                keys.append(k)
            new.add_annotation(a, keys)
            control.add_group(a)
            bars.append(new)
            if i * self.group_height + self.group_height > self.bar_height_min:
                height += self.group_height
        height += self.group_height

        item = [control, bars, height]
        self.item_ann_layers.append(item)
        self.items.append(item)
        self.update_ui()

    @pyqtSlot(object)
    def add_screenshots(self, screenshot_group):
        control = TimelineControl(self.frame_Controls, self, name = screenshot_group.name, item=screenshot_group)
        bars = ScreenshotGroupBar(self.frame_Bars, self, screenshot_group, control)
        item = [control, [bars], self.bar_height_min]
        self.item_screenshots.append(item)
        self.items.append(item)

    def add_bar(self):
        b = TimelineBar(self.frame_Bars, self)
        return b

    def set_colormetry_progress(self, percentage):
        self.time_bar.colormetry_progress = percentage
        self.time_bar.update()

    def get_current_bar(self):
        for itm in self.item_segments:
            if itm[0].item == self.selected:
                return itm[1][0]
        return None

    def clear(self):
        self.items = self.item_screenshots + self.item_ann_layers + self.item_segments
        for i in self.items:
            ctrl = i[0]
            bars = i[1]
            for b in bars:
                b.close()
            ctrl.close()
        self.items = []
        self.item_segments = []
        self.item_ann_layers = []
        self.item_screenshots = []

    def update_location(self):
        # self.curr_movie_time = self.main_window.player.get_media_time() / 1000
        self.update()

    def set_time_indicator_visibility(self, bool):
        if self.show_time_indicator or not bool:
            self.time_label.setVisible(bool)

    def on_scroll_h_timeout(self):
        self.scroll_block = False
        self.scroll_h_timer.stop()

    def move_scrubber(self, pos):
        pos = np.clip(pos, 0, self.duration / self.scale)
        self.time_scrubber.move(pos, 0)
        self.main_window.player.set_media_time(pos * self.scale)

        self.time_label.setText(ms_to_string(pos * self.scale, True))
        self.time_label.move(pos + 20 + self.controls_width - self.scrollArea.horizontalScrollBar().value(), 5)

        self.check_auto_scroll(pos)

    def check_auto_scroll(self, pos):
        if pos - self.scrollArea.horizontalScrollBar().value() > self.width() - self.controls_width - 50 and self.scroll_block is False:
            self.scrollArea.horizontalScrollBar().setValue(self.scrollArea.horizontalScrollBar().value() + 5)
            self.scroll_h_timer.start()
        elif pos - self.scrollArea.horizontalScrollBar().value() < 50 and self.scroll_block is False:
            self.scrollArea.horizontalScrollBar().setValue(self.scrollArea.horizontalScrollBar().value() - 5)
            self.scroll_h_timer.start()

    def paintEvent(self, QPaintEvent):
        super(Timeline, self).paintEvent(QPaintEvent)

    def update_time_bar(self):
        if self.time_bar is None:
            self.time_bar = TimebarDrawing(self.frame_Bars, self)
            self.time_bar.show()

        if not self.time_bar.isVisible():
            self.time_bar.show()

        self.time_bar.move(self.relative_corner.x(), self.time_bar.y())
        self.time_bar.setFixedWidth(self.width() - self.controls_width)
        self.time_bar.setFixedHeight(self.time_bar_height)

        self.time_bar.update()
        # self.time_bar.show()

    def update_ui(self):
        # self.time_scrubber.move(self.curr_movie_time, 0)
        value = self.scrollArea.horizontalScrollBar().value()

        self.relative_corner = QtCore.QPoint(value, self.relative_corner.y())

        h = self.scrubber_min_h
        if self.scrubber_min_h < self.frame_Bars.height():
            h = self.frame_Bars.height()
        self.time_scrubber.resize(self.scrubber_width, h)

        loc_y = self.time_bar_height
        self.items = self.item_segments + self.item_ann_layers + self.item_screenshots
        for c, i in enumerate(self.items):
            bar_start = loc_y
            ctrl_height = 6
            ctrl = i[0]
            bars = i[1]
            # item_height = ((ctrl.height() - self.group_height) / np.clip(len(bars), 1, None))
            ctrl.move(2, loc_y)
            if len(bars) >= 1 and len(bars[0].annotations) > 0:
                loc_y += self.group_height
            if len(ctrl.groups) > 0:
                item_height = ((ctrl.height() - self.group_height) / np.clip(len(bars), 1, None))
            else:
                item_height = (ctrl.height() / np.clip(len(bars), 1, None))

            for b in bars:
                b.move(0, loc_y)
                b.resize(self.duration/self.scale, item_height)#item_height)
                loc_y += item_height #item_height
                ctrl_height += item_height + 4 # + item_height
                b.rescale()

            if loc_y - bar_start < self.bar_height_min:
                loc_y = self.bar_height_min + bar_start
                ctrl.resize(self.controls_width - 4, self.bar_height_min)
            else:
                ctrl.resize(self.controls_width - 4, loc_y - bar_start)

            ctrl.onHeightChanged.emit(ctrl.height())

        self.frame_Controls.setFixedSize(self.controls_width, loc_y)# self.frame_Controls.height())
        self.frame_Bars.setFixedSize(self.duration / self.scale + self.controls_width + self.timeline_tail,loc_y)
        self.frame_outer.setFixedSize(self.frame_Bars.size().width(), self.frame_Bars.height())
        self.time_scrubber.setFixedHeight(self.frame_Bars.height())
        self.time_bar.raise_()

    def on_loaded(self, project):
        self.setDisabled(False)

        self.clear()
        self.time_bar.close()
        for s in project.segmentation:
            self.add_segmentation(s)

        for l in project.annotation_layers:
            self.add_annotation_layer(l)

        for grp in project.screenshot_groups:
            self.add_screenshots(grp)

        project.onSegmentationAdded.connect(self.add_segmentation)
        project.onAnnotationLayerAdded.connect(self.add_annotation_layer)
        project.onSegmentationRemoved.connect(self.recreate_timeline)
        project.onAnnotationLayerRemoved.connect(self.recreate_timeline)

        self.update_time_bar()
        self.update_ui()
        self.scroll_h()

    def on_changed(self, project, item):
        vlocation = self.scrollArea.verticalScrollBar().value()

        # self.clear()
        self.duration = project.get_movie().duration

        # for s in project.segmentation:
        #     if s.get_timeline_visibility() is True:
        #         self.add_segmentation(s)

        # for l in project.annotation_layers:
        #     if l.get_timeline_visibility() is True:
        #         self.add_annotation_layer(l)

        # for grp in project.screenshot_groups:
        #     self.add_screenshots(grp.screenshots, grp, grp.get_name())

        self.on_selected(None, project.selected)
        self.update_ui()
        self.scrollArea.verticalScrollBar().setValue(vlocation)

    def on_selected(self, sender, selected):
        if sender is self:
            return
        if selected is None:

            return
        for entry in self.items:
            has_found = False
            for i, bars in enumerate(entry[1]):
                for s in bars.slices:
                    if s.item in selected:
                        s.is_selected = True
                        has_found = True
                    else:
                        s.is_selected = False
            entry[0].is_selected = has_found


        if self.selected is not None:
            self.select(item=self.selected, dispatch=False)

    def on_closed(self):
        self.clear()
        self.set_colormetry_progress(0.0)
        self.setDisabled(True)

    def recreate_timeline(self, args = None):
        t = time.time()
        vlocation = self.scrollArea.verticalScrollBar().value()
        project = self.main_window.project
        self.clear()
        self.duration = project.get_movie().duration

        for s in project.segmentation:
            if s.get_timeline_visibility() is True:
                self.add_segmentation(s)

        for l in project.annotation_layers:
            if l.get_timeline_visibility() is True:
                self.add_annotation_layer(l)

        for grp in project.screenshot_groups:
            self.add_screenshots(grp)

        self.on_selected(None, project.selected)
        self.update_ui()
        self.scrollArea.verticalScrollBar().setValue(vlocation)
        print("Timeline", time.time()- t)

    def select(self, control = None, item = None, dispatch = True):
        #TODO This deselectes all items in multiple selection except the last one
        if control is not None:
            search = control
        else:
            search = item

        if search is None:
            return

        for i,entry in enumerate(self.items):
            if search == entry[0] or search == entry[0].item:
                self.selected = entry[0].item
                entry[0].is_selected = True
                for b in entry[1]:
                    b.is_selected = True
            else:
                entry[0].is_selected = False
                for b in entry[1]:
                    b.is_selected = False

        if self.selected is not None and dispatch:
            self.project().set_selected(self, self.selected)
        self.update()

    def on_timestep_update(self, time):
        self.curr_movie_time = time
        self.time_scrubber.move(self.curr_movie_time / self.scale - 5, 0)

        if self.keep_slider_in_view:
            if self.time_scrubber.pos().x() > self.scrollArea.horizontalScrollBar().value() + \
                        self.scrollArea.width() - self.controls_width - 100 and self.main_window.player.is_playing():
                self.scrollArea.horizontalScrollBar().setValue(self.scrollArea.horizontalScrollBar().value() + self.scrollArea.width() - self.controls_width - 100)
            elif self.time_scrubber.pos().x() < self.scrollArea.horizontalScrollBar().value():
                self.scrollArea.horizontalScrollBar().setValue(self.time_scrubber.pos().x() - self.controls_width)

        self.update_time_bar()
        self.update()

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.scrollArea.verticalScrollBar().setEnabled(False)
            self.main_window.keyPressEvent(QKeyEvent)
        elif QKeyEvent.key() == Qt.Key_Shift:
            self.shift_pressed = True
        else:
            QKeyEvent.ignore()

    def keyReleaseEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.is_scaling = False
            self.scrollArea.verticalScrollBar().setEnabled(True)
            self.main_window.keyReleaseEvent(QKeyEvent)
        elif QKeyEvent.key() == Qt.Key_Shift:
            self.shift_pressed = False
        else:
            QKeyEvent.ignore()

    def wheelEvent(self, QWheelEvent):
        if self.is_scaling:
            self.zoom_timeline(QWheelEvent.pos(), QWheelEvent.angleDelta())
        else:
            x = -1 * QWheelEvent.angleDelta().x() + self.scrollArea.horizontalScrollBar().value()
            y = -1 * QWheelEvent.angleDelta().y() + self.scrollArea.verticalScrollBar().value()
            self.scrollArea.horizontalScrollBar().setValue(x)
            self.scrollArea.verticalScrollBar().setValue(y)

    def zoom_timeline(self, pos, angleDelta=0, abs_scale = 0, force = False):
        if self.is_scaling or force:
            center_point = (pos.x() - self.controls_width) * self.scale + self.scrollArea.horizontalScrollBar().value() * self.scale
            delta = (pos.x() - self.controls_width)

            s_max = int(self.duration / self.width()) + self.controls_width + 400 # + 400 to make sure the whole timeline can be looked at once
            if abs_scale != 0:
                self.scale = abs_scale
            else:
                self.scale = np.clip(- angleDelta.y() * (0.0005 * self.scale) + self.scale, None, s_max)
            self.update_ui()
            self.update()

            side_offset = center_point - delta * self.scale
            self.time_scrubber.move(self.curr_movie_time // self.scale - 5, 0)

            if self.settings.OPENCV_PER_FRAME == TIMELINE_SCALE_DEPENDENT:
                if self.scale < self.opencv_frame_scale_threshold:
                    self.main_window.onOpenCVFrameVisibilityChanged.emit(True)
                else:
                    self.main_window.onOpenCVFrameVisibilityChanged.emit(False)

            if self.interval_segmentation_marker is not None:
                self.interval_segmentation_marker.move(QPoint(self.interval_segmentation_start/self.scale, 0))

            self.scrollArea.horizontalScrollBar().setValue(side_offset // self.scale)

    def frame_time_range(self, t_start, t_end):
        scale = (t_end - t_start) / (self.width() - self.controls_width) + 3
        self.zoom_timeline(QPoint(0,0), abs_scale=scale, force = True)
        self.scrollArea.horizontalScrollBar().setValue(t_start / self.scale - (self.scale/2))

    def activate_move_tool(self):
        self.abort_cutting()
        self.abort_merge_tool()
        self.close_selector()

    #region CuttingTool
    def activate_cutting_tool(self):
        if self.is_cutting:
            self.abort_cutting()
        if self.is_merging:
            self.abort_merge_tool()
        if self.is_selecting:
            self.close_selector()

        self.time_scrubber.hide()
        self.is_cutting = True
        self.cutting_indicator = TimelineTimemark(self.frame_Bars, QColor(200,20,5,200))
        self.cutting_indicator.resize(1, self.height())

    def move_cutting_tool(self, pos):
        self.cutting_indicator.move(pos)
        self.main_window.player.set_media_time(pos.x() * self.scale)
        self.cutting_indicator.raise_()

    def finish_cutting_tool(self, pos, segm_container):
        segm_container.segmentation.cut_segment(segm_container, pos.x() * self.scale)
        if not self.shift_pressed:
            self.is_cutting = False
            self.cutting_indicator.deleteLater()
            self.cutting_indicator = None
            self.time_scrubber.show()

    def abort_cutting(self):
        self.time_scrubber.show()
        if self.is_cutting:
            self.is_cutting = False
            self.cutting_indicator.deleteLater()
            self.cutting_indicator = None

    #endregion

    #region MergingTool
    def activate_merge_tool(self):
        if self.is_merging:
            self.abort_merge_tool()
        if self.is_cutting:
            self.abort_cutting()
        if self.is_selecting:
            self.close_selector()

        self.time_scrubber.hide()
        self.is_merging = True
        self.merging_indicator = TimelineTimemark(self.frame_Bars, QColor(50, 220, 50, 200))
        self.merging_indicator.resize(5, self.height())

    def move_merge_tool(self, pos):
        self.merging_indicator.move(pos)
        self.main_window.player.set_media_time(pos.x() * self.scale)
        self.merging_indicator.raise_()

    def set_merge_containers(self, a = None, b = None):
        if self.merge_containers is not None and len(self.merge_containers) > 0:
            if self.merge_containers[0] is not None:
                self.merge_containers[0].merge_highlighted = False
                self.merge_containers[0].update()
            if self.merge_containers[1] is not None:
                self.merge_containers[1].merge_highlighted = False
                self.merge_containers[1].update()

        if a is not None and b is not None:
            self.merge_containers = [a, b]
            self.merge_containers[0].merge_highlighted = True
            self.merge_containers[1].merge_highlighted = True
            self.merge_containers[0].update()
            self.merge_containers[1].update()
        else:
            self.merge_containers = None

    def finish_merge_tool(self):

        if self.merge_containers is not None:
            segmentation = self.merge_containers[0].item.segmentation
            segmentation.merge_segments(self.merge_containers[0].item, self.merge_containers[1].item)
            self.set_merge_containers()

        if not self.shift_pressed:
            self.time_scrubber.show()
            self.is_merging = False
            self.merging_indicator.deleteLater()

            self.merging_indicator = None

    def abort_merge_tool(self):
        self.time_scrubber.show()
        if self.is_merging:
            self.is_merging = False
            self.merging_indicator.deleteLater()
            self.set_merge_containers()
            self.merging_indicator = None


    #endregion

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if self.shift_pressed:
                if self.selector is None:
                    self.start_selector(self.time_scrubber.pos())
                    self.move_selector(QMouseEvent.pos())
                else:
                    self.move_selector(QMouseEvent.pos())

        if QMouseEvent.button() == Qt.RightButton:
            if self.is_cutting:
                self.abort_cutting()
            else:
                self.start_selector(QMouseEvent.pos())

            # self.delta = QMouseEvent.pos() - self.frame_Bars.pos()
            # pos = QMouseEvent.pos() - self.frame_Bars.pos()
            # self.selector = TimebarSelector(self, self.frame_Bars, pos)
            # self.is_selecting = True

    def mouseReleaseEvent(self, QMouseEvent):
        if self.is_selecting and not self.shift_pressed:
            self.end_selector()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.RightButton or self.shift_pressed:
            pos = self.round_to_grid(QMouseEvent.pos() - self.frame_Bars.pos())
            self.move_selector(pos)

    #region Selector
    def start_selector(self, pos):
        if self.interval_segmentation_start is not None:
            return

        self.delta = pos
        self.selector = TimebarSelector(self, self.frame_Bars, pos)
        self.is_selecting = True

    def move_selector(self, pos):
        if self.is_selecting:
            dx = np.clip(pos.x(), self.selector.pos().x(), self.duration / self.scale)

            pos_r = QPoint(dx - self.delta.x(), pos.y() - self.delta.y())
            self.selector.set_end(pos_r)

            time = dx * self.scale
            self.main_window.player.set_media_time(time)
            self.check_auto_scroll(np.clip(pos.x(), 0, self.duration / self.scale))

    def end_selector(self):
        if self.is_selecting and self.selector_context is None:
            self.is_selecting = False
            # pos = self.selector.pos().x() + self.selector.width() + self.pos().x()
            pos = self.selector.pos().x() + self.selector.width() - self.relative_corner.x()
            self.selector_context = SelectorContextMenu(self, self.mapToGlobal(QtCore.QPoint(pos, self.pos().y())), self.selector)
            self.selector_context.new_segmentation.connect(self.create_segmentation)
            self.selector_context.new_segment.connect(self.create_segment)
            self.selector_context.new_layer.connect(self.create_layer)

    def close_selector(self):
        if self.selector is not None:
            self.selector.close()
            self.selector.deleteLater()
            self.update()
        self.selector = None
    #endregion

    #region CONTEXT MENU BINDINGS
    def new_segment(self):
        if self.selector is not None and self.selected is not None:
            if self.selected.get_type() == SEGMENTATION:
                self.selected.create_segment2(self.selector.start,
                                              self.selector.stop,
                                              mode=SegmentCreationMode.INTERVAL,
                                              inhibit_overlap=self.inhibit_overlap)
                # self.selected.create_segment(self.selector.start, self.selector.stop, forward_segmenting=False, inhibit_overlap=self.inhibit_overlap)

    def set_current_time(self, time):
        self.main_window.player.set_media_time(time)

    def round_to_grid(self, a):
        if self.settings.USE_GRID:
            if isinstance(a, QtCore.QPoint):
                px = a.x() - (a.x() % (float(self.settings.GRID_SIZE) / self.scale))
                py = a.y() - (a.y() % (float(self.settings.GRID_SIZE) / self.scale))
                return QtCore.QPoint(int(px), int(py))
            else:
                return int(a - (a % (float(self.settings.GRID_SIZE) / self.scale)))
        else:
            return a

    def on_timeline_settings_update(self):
        for s in self.item_segments:
            for bar in s[1]:
                for slice in bar.slices:
                    slice.update_text()

    def create_segment(self, lst = None, mode=SegmentCreationMode.BACKWARD):
        # If Nothing is handed in, we're performing a fast-segmentation
        # which means, that the segment is created from the last segments end to the current movie-time

        forward = False

        if not lst:
                lst = [self.curr_movie_time - 1, self.curr_movie_time]
                if self.is_forward_segmenting:
                    mode = SegmentCreationMode.FORWARD

        if self.selected is not None:
            if self.selected.get_type() == SEGMENTATION:
                self.selected.create_segment2(lst[0], lst[1], mode, inhibit_overlap=self.inhibit_overlap)
                # self.selected.create_segment(lst[0], lst[1], forward_segmenting = forward, inhibit_overlap=self.inhibit_overlap)

    def create_layer(self, lst):
        if len(lst) == 0:
            lst = [self.curr_movie_time, self.duration]
        self.project().create_annotation_layer("New Layer", lst[0], lst[1])

    def create_segmentation(self):
        self.project().create_segmentation("New Segmentation")
    #endregion

    def resizeEvent(self, QResizeEvent):
        super(Timeline, self).resizeEvent(QResizeEvent)


class TimelineControl(QtWidgets.QWidget):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent,timeline, item = None, name = "No Name"):
        super(TimelineControl, self).__init__(parent)
        self.timeline =  timeline
        self.item = item
        self.h_exp = 300
        self.h_col = 100
        self.name = name
        self.set_name()
        self.groups = dict()
        self.setMouseTracking(True)
        self.is_selected = False

        self.size_grip_hovered = False
        self.is_resizing = False
        self.resize_offset = 0
        self.show()
        if self.item.strip_height == -1:
            self.resize(self.width(), 45)
        else:
            self.resize(self.width(), self.item.strip_height)

    def set_name(self):
        if self.item is not None:
            self.name = self.item.get_name()

    def add_group(self, annotation):
        y = len(self.groups) * self.timeline.group_height
        text = annotation.get_name()
        self.groups[annotation.get_id()] = ([annotation, text])

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent):
        if self.is_resizing:
            if not a0.pos().y() + self.resize_offset < self.timeline.bar_height_min:
                self.resize(self.width(), a0.pos().y() + self.resize_offset)
                self.timeline.update_ui()
                if len(self.groups) > 0:
                    self.onHeightChanged.emit((self.height() - self.timeline.group_height) / len(self.groups.values()))
                else:
                    self.onHeightChanged.emit(self.height())
                self.item.strip_height = self.height()

        else:
            if a0.pos().y() > self.height() - 15:
                self.size_grip_hovered = True
            else:
                self.size_grip_hovered = False
            self.update()
            super(TimelineControl, self).mouseMoveEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent):
        self.size_grip_hovered = False
        super(TimelineControl, self).leaveEvent(a0)

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if QMouseEvent.pos().y() > self.height() - 15:
                self.is_resizing = True
                self.resize_offset = self.height() - QMouseEvent.pos().y()
            else:
                self.timeline.select(self)

        if QMouseEvent.button() == Qt.RightButton:
            context = open_context_menu(self.timeline.main_window,self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())
            context.show()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent):
        self.is_resizing = False

    def paintEvent(self, QPaintEvent):
        super(TimelineControl, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255, 50))
        pen.setWidth(1)
        qp.setPen(pen)

        for i,a in enumerate(self.groups.values()):
            y = i * self.timeline.group_height + self.timeline.group_height
            if i == 0:
                p1 = QtCore.QPoint(self.x(), y)
                p2 = QtCore.QPoint(self.width(), y)
                qp.drawLine(p1, p2)

            p1 = QtCore.QPoint(self.x(), y + self.timeline.group_height)
            p2 = QtCore.QPoint(self.width(), y + self.timeline.group_height)
            qp.drawLine(p1, p2)

        pen.setColor(QtGui.QColor(255, 255, 255, 200))
        qp.setPen(pen)

        if self.is_selected:
            # qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QtGui.QColor(200, 200, 255, 50))
            qp.fillRect(self.rect(), QtGui.QColor(200, 200, 255, 50))
        else:
            gradient = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
            gradient.setColorAt(0.0, QColor(50, 50, 50))
            gradient.setColorAt(0.5, QColor(65, 65, 65))
            gradient.setColorAt(1.0, QColor(50, 50, 50))
            gradient.setSpread(QGradient.PadSpread)
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), gradient)

        for i, a in enumerate(self.groups.values()):
            y = i * self.timeline.group_height + self.timeline.group_height
            text_rect = QtCore.QRect(0, y, self.width(), self.timeline.group_height)
            qp.drawText(text_rect, Qt.AlignRight|Qt.AlignVCenter, a[1])

        pen.setColor(QtGui.QColor(255, 255, 255, 255))
        qp.setPen(pen)
        qp.drawLine(QtCore.QPoint(0,0), QtCore.QPoint(self.width(), 0))

        # Title of the Control
        qp.drawText(QRect(5, 5, self.width(), 25), Qt.AlignVCenter | Qt.AlignLeft, self.name)

        if isinstance(self.item, ILockable):
            if self.item.is_locked():
                qp.drawPixmap(QtCore.QRect(self.width() - 20, 9, 16, 16), QPixmap("qt_ui/icons/icon_locked.png"))
        if isinstance(self.item, AnnotationLayer):
            if self.item.is_visible == False:
                qp.drawPixmap(QtCore.QRect(self.width() - 40, 9, 16, 16), QPixmap("qt_ui/icons/icon_hidden.png"))
        # qp.drawLine(QtCore.QPoint(0, self.height()), QtCore.QPoint(self.width(), self.height()))
        if self.size_grip_hovered:
            pen.setColor(QtGui.QColor(164, 7, 0, 200))
            pen.setWidth(4)
            qp.setPen(pen)
            qp.drawLine(0, self.height() - 2, self.width(), self.height() - 2)
        qp.end()


class TimelineAnnotationLayerControl(TimelineControl):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, item = None, name = "No Name"):
        super(TimelineAnnotationLayerControl, self).__init__(parent, timeline, item, name)
        self.layer = item


class TimelineSegmentationControl(TimelineControl):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, item=None, name="No Name"):
        super(TimelineSegmentationControl, self).__init__(parent, timeline, item, name)
        self.segmentation = item


class TimelineBar(QtWidgets.QFrame):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, height = 45):
        super(TimelineBar, self).__init__(parent)
        self.resize(parent.width(), height)
        self.timeline = timeline
        self.orig_height = height
        self.setMouseTracking(True)
        self.control = control
        self.control.onHeightChanged.connect(self.on_height_changed)
        self.is_selected = False

        self.setFrameStyle(QFrame.Box)

        self.slices = []
        self.slices_index = dict()
        self.annotations = []
        self.show()

    def add_annotation(self, annotation, keys):
        y = len(self.annotations) * self.timeline.group_height + self.timeline.group_height
        tb_keys = []
        for i, k in enumerate(keys):
            tb_key = TimebarKey(self, annotation, i)
            tb_key.move(k[0] // self.timeline.scale, y + 2.5)
            tb_key.resize(10, 10)
            tb_keys.append(tb_key)
            tb_key.show()
        self.annotations.append([annotation, tb_keys])

    @pyqtSlot(int)
    def on_height_changed(self, height):
        """
        This is called when the User drags the size handle into one direction in the control widget, 
        usually it does not have to be used since the resizing is done in the timeline update_ui() directly. 
        Screenshots override it to resize he pixmaps as well
        :param height: 
        :return: 
        """
        self.onHeightChanged.emit(height)

    def add_slice(self, item):
        slice = TimebarSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice

    def remove_slice(self, item):
        if item.get_id() in self.slices_index:
            itm = self.slices_index[item.get_id()]
            self.slices.remove(itm)
            self.slices_index.pop(item.get_id())
            itm.close()

    def get_previous_slice(self, slice):
        result = None
        self.slices = sorted(self.slices, key=lambda x: x.pos().x())
        for s in self.slices:
            if s.pos().x() < slice.pos().x():
                result = s
            else:
                break

        return result

    def get_next_slice(self, slice):
        result = None
        self.slices = sorted(self.slices, key=lambda x: x.pos().x())
        for s in self.slices:
            if s.pos().x() > slice.pos().x():
                if result is None:
                    result = s
                else:
                    if result.pos().x() > s.pos().x():
                        result = s

        return result

    def rescale(self):
        for a in self.annotations:
            for k in a[1]:
                k.move(a[0].keys[k.key_index][0] // self.timeline.scale, k.y())

        for s in self.slices:
            s.move(int(round(s.item.get_start() / self.timeline.scale, 0)), 0)
            s.resize(int(round((s.item.get_end() - s.item.get_start()) / self.timeline.scale, 0)), self.height() / 2)

    def paintEvent(self, QPaintEvent):
        # super(TimelineBar, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(20, 20, 20, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        for i,a in enumerate(self.annotations):
            if i == 0:
                y = i * self.timeline.group_height + self.timeline.group_height
                p1 = QtCore.QPoint(self.x(), y)
                p2 = QtCore.QPoint(self.width(), y)
                qp.drawLine(p1, p2)
            y = i * self.timeline.group_height + self.timeline.group_height + self.timeline.group_height
            p1 = QtCore.QPoint(self.x(), y)
            p2 = QtCore.QPoint(self.width(), y)
            qp.drawLine(p1, p2)

        pen.setColor(QtGui.QColor(200, 200, 200, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        qp.drawRect(self.rect())
        if self.is_selected:
            qp.fillRect(self.rect(), QtGui.QColor(255, 255, 255, 50))
        qp.end()


class TimebarSlice(QtWidgets.QWidget):
    def __init__(self, parent:TimelineBar, item, timeline, color = (232, 174, 12, 100)):
        super(TimebarSlice, self).__init__(parent)
        self.bar = parent
        self.locked = False
        self.timeline = timeline
        self.item = item
        self.show()
        self.mode = "center"
        self.setMouseTracking(True)
        self.border_width = 10
        self.offset = QtCore.QPoint(0,0)
        self.text = ""
        self.curr_pos = self.pos()
        self.curr_size = self.size()

        self.update_text()

        self.color = color
        self.text_size = 10

        self.is_hovered = False
        self.is_selected = False

        self.media_object_items = []

        if isinstance(item, IHasMediaObject):
            self.setAcceptDrops(True)
            x = self.width() - 30
            for obj in self.item.media_objects:
                    itm = MediaObjectWidget(self, obj)
                    itm.resize(25,25)
                    itm.move(x, 5)
                    if x > 50:
                        itm.show()
                    else:
                        itm.hide()
                    self.media_object_items.append(itm)
                    x -= 30

        self.merge_highlighted = False

        self.min_possible = 0
        self.max_possible = self.timeline.duration * self.timeline.scale

    def paintEvent(self, QPaintEvent):
        self.locked = False
        if isinstance(self.item, ILockable):
            self.locked = self.item.is_locked()

        if self.locked :
            col = (self.color[0], self.color[1], self.color[2], 20)

        else:
            if self.merge_highlighted:
                col = (255, 160, 47, 200)

            elif self.is_hovered:
                if self.timeline.is_cutting:
                    col = (180,0,0, 200)
                else:
                    if self.is_selected:
                        col = (self.color[0], self.color[1], self.color[2], 150)
                    else:
                        col = (self.color[0], self.color[1], self.color[2], 80)

            elif self.is_selected:
                col = (self.color[0], self.color[1], self.color[2], 150)

            else:
                col = (self.color[0], self.color[1], self.color[2], 50)



        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)

        # col = QtGui.QColor(col[0], col[1], col[2], col[3])
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
        gradient.setColorAt(0.0, QColor(col[0] - 20, col[1] - 20, col[2] - 20, col[3] - 20))
        gradient.setColorAt(0.5, QColor(col[0], col[1], col[2], col[3]))
        gradient.setColorAt(1.0, QColor(col[0] - 20, col[1] - 20, col[2] - 20, col[3]  - 20))
        gradient.setSpread(QGradient.PadSpread)

        pen.setColor(QColor(col[0], col[1], col[2], 150))
        qp.drawRect(QtCore.QRect(0, 0, self.width(), self.height()))
        qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), gradient)

        pen.setColor(QtGui.QColor(255, 255, 255))
        qp.drawText(5, (self.height() + self.text_size) // 2, self.text)

        x = self.width() - 60
        y = self.height() / 2 - (25 / 2)
        for m in self.media_object_items:
            m.move(x, int(y))
            if x > 50:
                m.show()
            else:
                m.hide()
            x -= 30

        qp.end()

    def update_text(self):
        self.text = ""
        if self.item.get_type() == SEGMENT:
            if self.timeline.show_id:
                self.text += "ID: " +  str(self.item.ID).ljust(5)
            if self.timeline.show_name:
                self.text += "Name: " +  str(self.item.get_name()) + "\t"
            if self.timeline.show_text:
                self.text += "Text: " + str(self.item.get_annotation_body())

            self.setToolTip("<FONT>" + self.item.get_annotation_body() + "</FONT>")
        else:
            self.text = str(self.item.get_name())

        self.update()

    def mousePressEvent(self, QMouseEvent):
        if not self.locked:
            if QMouseEvent.buttons() & Qt.LeftButton:
                if self.timeline.is_cutting:
                    return

                elif self.timeline.is_merging:
                    self.timeline.finish_merge_tool()

                else:
                    # Inhibiting Overlap by finding the surrounding Slices and get their boundaries
                    if self.timeline.inhibit_overlap:
                        previous = self.parent().get_previous_slice(self)
                        next = self.parent().get_next_slice(self)

                        if previous is not None:
                            self.min_possible = previous.pos().x() + previous.width()
                        else:
                            self.min_possible = 0
                        if next is not None:
                            self.max_possible = next.pos().x()
                        else:
                            self.max_possible = self.timeline.duration * self.timeline.scale

                    self.is_selected = True
                    self.timeline.project().set_selected(None, self.item)
                    self.offset = self.mapToParent(QMouseEvent.pos())
                    self.curr_size = self.size()
                    self.curr_pos = self.pos()
                self.timeline.update()

            if QMouseEvent.buttons() & Qt.RightButton:
                if self.timeline.is_cutting:
                    self.timeline.abort_cutting()
                elif self.timeline.is_merging:
                    self.timeline.abort_merge_tool()
                else:
                    open_context_menu(self.timeline.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())

    def mouseReleaseEvent(self, QMouseEvent):
        # if the the movement is smaller than the grid-size ignore it
        if not self.locked:

            if self.timeline.is_cutting:
                self.timeline.finish_cutting_tool(self.mapToParent(QMouseEvent.pos()), self.item)
                return

            # if the Move was smaller than the Settings.Grid_SIZE, undo the movement
            else:
                if self.timeline.settings.USE_GRID:
                    if np.abs(self.pos().x() * self.timeline.scale - self.item.get_start()) < self.timeline.settings.GRID_SIZE and \
                         np.abs(self.width() * self.timeline.scale - (self.item.get_end() - self.item.get_start())) < self.timeline.settings.GRID_SIZE:
                        self.move(int(round(self.item.get_start() / self.timeline.scale, 0)), 0)
                        self.resize(int(round((self.item.get_end() - self.item.get_start()) / self.timeline.scale, 0)), self.height())
                        return

                if self.mode == "center":
                    self.item.move(int(round(self.pos().x() * self.timeline.scale, 0)), int(round((self.pos().x() + self.width()) * self.timeline.scale,0)))
                    return
                if self.mode == "left":
                    self.item.set_start(int(round((self.pos().x() * self.timeline.scale),0)))
                    return

                if self.mode == "right":
                    self.item.set_end(int(round(((self.pos().x() + self.width()) * self.timeline.scale),0)))
                    return

    @pyqtSlot(int)
    def on_height_changed(self, int_height):
        self.resize(self.width(), int_height)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent):
        a0.acceptProposedAction()

    def dropEvent(self, a0: QtGui.QDropEvent):
        self.item.project.create_media_object("New Object",
                                                    a0.mimeData().urls()[0].toLocalFile(),
                                                    self.item)

    def enterEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = True

    def leaveEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = False

    def mouseMoveEvent(self, QMouseEvent):
        if not self.locked:
            if self.timeline.is_cutting:
                self.timeline.move_cutting_tool(QPoint(self.mapToParent(QMouseEvent.pos()).x(), 0))
            elif self.timeline.is_merging:
                if QMouseEvent.pos().x() < self.width() / 2:
                    self.timeline.set_merge_containers(self.bar.get_previous_slice(self), self)
                else:
                    self.timeline.set_merge_containers(self, self.bar.get_next_slice(self))

                self.timeline.move_merge_tool(QPoint(self.mapToParent(QMouseEvent.pos()).x(), 0))

            elif QMouseEvent.buttons() & Qt.LeftButton:
                pos = self.mapToParent(QMouseEvent.pos())
                target = pos - self.offset
                tx = int(self.timeline.round_to_grid(target.x()))
                ty = int(self.timeline.round_to_grid(target.y()))
                target = QtCore.QPoint(int(tx), int(ty))

                if self.mode == "right":
                    if self.timeline.inhibit_overlap:
                        x = np.clip(self.curr_size.width() + target.x(), self.curr_pos.x() - self.offset.x() + 5, self.max_possible - self.curr_pos.x())
                    else:
                        x = np.clip(self.curr_size.width() + target.x(), self.curr_pos.x() - self.offset.x() + 5, None)

                    self.resize(x, self.height())
                    self.update()

                    time = (self.pos().x() + self.width()) * self.timeline.scale
                    self.timeline.main_window.player.set_media_time(time)
                    return

                if self.mode == "left":
                    if self.timeline.inhibit_overlap:
                        x = np.clip(self.curr_pos.x() + target.x(), a_min=self.min_possible, a_max=self.curr_pos.x() + self.curr_size.width())
                        # w = np.clip(self.curr_size.width() - target.x(), a_min=0, a_max=self.curr_pos.x() + self.curr_size.width())
                        w = np.clip(self.curr_size.width() - target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())

                    else:
                        x = np.clip(self.curr_pos.x() + target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())
                        w = np.clip(self.curr_size.width() - target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())

                    if self.pos().x() != x:
                        self.move(x, 0)
                        self.resize(w, self.height())

                    self.update()

                    time = (self.pos().x()) * self.timeline.scale
                    self.timeline.main_window.player.set_media_time(time)
                    return

                if self.mode == "center":
                    if self.timeline.inhibit_overlap:
                        x1 = np.clip(self.curr_pos.x() + target.x() + self.width(), self.min_possible, self.max_possible - self.width())
                        x2 = np.clip(self.curr_pos.x() + target.x(), self.min_possible, None)
                        if x2 < x1:
                            x = x2
                        else:
                            x = x1

                    else:
                        x = np.clip(self.curr_pos.x() + target.x(), 0, self.parent().width() - self.width())

                    self.move(x, 0)
                    self.update()
                    return

            else:
                # Moving the Left Sid
                if  self.mapFromGlobal(self.cursor().pos()).x() < self.border_width:
                    self.mode = "left"
                    self.setCursor(QtGui.QCursor(Qt.SizeHorCursor))
                    return

                # Moving the Right Side
                if  self.mapFromGlobal(self.cursor().pos()).x() > self.width() - self.border_width:
                    self.mode = "right"
                    self.setCursor(QtGui.QCursor(Qt.SizeHorCursor))
                    return

                # Moving the whole widget
                if self.border_width <= self.mapFromGlobal(self.cursor().pos()).x() <= self.width() - self.border_width:
                    self.mode = "center"
                    self.setCursor(QtGui.QCursor(Qt.SizeAllCursor))
                    return
                else:
                    self.setCursor(QtGui.QCursor(Qt.ArrowCursor))

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent):
        if self.item.get_type() == SEGMENT:
            popup = TextEditPopup(self, self.item.set_annotation_body, self.mapToGlobal(a0.pos()), text=self.item.get_annotation_body())

    def update(self, *__args):
        super(TimebarSlice, self).update(*__args)


class TimelineSegmentationBar(TimelineBar):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, segmentation, height = 45):
        super(TimelineSegmentationBar, self).__init__(parent, timeline, control, height)
        self.segmentation = segmentation
        self.segmentation.onSegmentDeleted.connect(self.remove_slice)
        self.segmentation.onSegmentAdded.connect(self.add_slice)

    def add_slice(self, item):
        slice = TimebarSegmentationSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice


class TimebarSegmentationSlice(TimebarSlice):
    def __init__(self, parent:TimelineSegmentationBar, item, timeline):
        super(TimebarSegmentationSlice, self).__init__(parent, item, timeline, color = (54,146,182, 100))


class TimelineAnnotationBar(TimelineBar):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, height = 45):
        super(TimelineAnnotationBar, self).__init__(parent, timeline, control, height)

    def add_slice(self, item):
        slice = TimebarAnnotationSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice


class TimebarAnnotationSlice(TimebarSlice):
    def __init__(self, parent:TimelineSegmentationBar, item, timeline):
        super(TimebarAnnotationSlice, self).__init__(parent, item, timeline, color = (133, 42, 42, 100))


class MediaObjectWidget(QWidget):
    def __init__(self, parent, media_object):
        super(MediaObjectWidget, self).__init__(parent)
        self.media_object = media_object
        self.hovered = False
        self.setToolTip("Open: " + str(self.media_object.name))

    def enterEvent(self, a0: QtCore.QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QtCore.QEvent):
        self.hovered = False

    def paintEvent(self, QPaintEvent):

        col = [5, 175, 242, 1]

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)

        pen.setColor(QColor(col[0], col[1], col[2], 150))
        if self.hovered:
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QColor(col[0], col[1], col[2], 200))
        else:
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QColor(col[0], col[1], col[2], col[3]))

        pen.setColor(QtGui.QColor(255, 255, 255))

        if self.media_object.dtype == MediaObjectType.PDF:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_pdf.png"))
        elif self.media_object.dtype == MediaObjectType.IMAGE:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_image_media.png"))
        elif self.media_object.dtype == MediaObjectType.EXTERNAL:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_external_media.png"))

        qp.end()

    def mousePressEvent(self, a0: QtGui.QMouseEvent):
        if a0.button() == Qt.LeftButton:
            self.media_object.preview()
        elif a0.button() == Qt.RightButton:
            open_context_menu(self.parent().timeline.main_window, self.mapToGlobal(a0.pos()),
                              [self.media_object], self.media_object.project)


class TimebarKey(QtWidgets.QWidget):
    def __init__(self, parent, annotation, key_index):
        super(TimebarKey, self).__init__(parent)
        self.annotation = annotation
        self.key_index = key_index
        self.color = (255,0,0)
        self.is_hovered = False

    def paintEvent(self, QPaintEvent):
        if self.is_hovered:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 100)
        else:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 50)

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)
        path = QtGui.QPainterPath()
        path.addEllipse(QtCore.QRectF(self.rect()))
        qp.fillPath(path, col)
        qp.end()

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False


class ScreenshotGroupBar(TimelineBar):
    def __init__(self, parent, timeline, screenshot_group, control, height=45):
        super(ScreenshotGroupBar, self).__init__(parent, timeline, control, height=45)
        self.screenshot_group = screenshot_group
        self.screenshot_group.onScreenshotAdded.connect(self.add_screenshot)
        self.screenshot_group.onScreenshotRemoved.connect(self.remove_screenshot)
        # self.screenshots = dict([(s.unique_id, s) for s in screenshot_group.screenshots])
        self.pictures = dict()
        self.timeline = timeline

        for s in screenshot_group.screenshots:
            self.add_screenshot(s)
        self.show()

    def add_screenshot(self, scr):
        if scr.unique_id not in self.pictures:
            pic = TimebarPicture(self, scr, self.timeline)
            self.onHeightChanged.connect(pic.on_height_changed)
            pic.move(scr.get_start() // self.timeline.scale, 0)
            self.pictures[scr.unique_id] = pic


    def remove_screenshot(self, scr):
        if scr.unique_id in self.pictures:
            self.pictures[scr.unique_id].close()

    def rescale(self):
        for s in self.pictures.keys():
            pic = self.pictures[s]
            pic.move(pic.item.get_start()//self.timeline.scale, 0)


class TimebarPicture(QtWidgets.QWidget):
    def __init__(self, parent, screenshot:Screenshot, timeline, height = 43):
        super(TimebarPicture, self).__init__(parent)
        self.item = screenshot
        self.item.onImageSet.connect(self.on_image_set)
        self.timeline = timeline
        self.is_hovered = False
        self.color = (123, 86, 32, 100)
        self.pic_height = height
        qimage, qpixmap = screenshot.get_preview(scale=0.1)
        self.pixmap = qpixmap
        self.qimage = qimage
        self.size = (screenshot.get_img_movie(ignore_cl_obj = True).shape[0],
                     screenshot.get_img_movie(ignore_cl_obj = True).shape[1])
        width = self.size[1] * self.pic_height // self.size[0]
        self.img_rect = QtCore.QRect(1, 1, width, self.pic_height)
        self.resize(width, self.pic_height)
        self.show()

    def on_image_set(self, screenshot):
        qimage, qpixmap = screenshot.get_preview(scale=0.1)
        self.pixmap = qpixmap
        self.qimage = qimage
        self.update()

    def on_height_changed(self, height):
        self.pic_height = height
        width = self.size[1] * self.pic_height // self.size[0]
        self.resize(width, self.pic_height)
        self.img_rect = QtCore.QRect(1, 1, width, self.pic_height)

    def paintEvent(self, QPaintEvent):
        if self.is_hovered:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 100)
        else:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 50)

        qp = QtGui.QPainter()

        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(col)
        pen.setWidth(5)
        qp.setPen(pen)

        qp.drawImage(self.img_rect, self.qimage)
        qp.drawRect(self.img_rect)

        qp.end()

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.timeline.project().set_selected(self, self.item)
        if QMouseEvent.buttons() & Qt.RightButton:
            open_context_menu(self.timeline.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())

    def enterEvent(self, QEvent):
        self.is_hovered = True
        self.raise_()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent):
        preview = ImagePreviewPopup(self.timeline.main_window, numpy_to_pixmap(self.item.get_img_movie(ignore_cl_obj = True)))
        preview.show()
        self.timeline.set_current_time(self.item.movie_timestamp)

    def leaveEvent(self, QEvent):
        self.is_hovered = False
        self.lower()


class TimelineScrubber(QtWidgets.QWidget):
    def __init__(self, parent, player, timeline):
        super(TimelineScrubber, self).__init__(parent)
        r = parent.rect()
        self.timeline = timeline
        self.player = player
        self.resize(10, r.height())
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.is_hovered = False
        self.was_playing = False
        self.offset = 0

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.timeline.set_time_indicator_visibility(True)
            self.was_playing = self.player.is_playing()
            self.player.pause()
            self.timeline.main_window.update_timer.stop()
            self.offset = self.mapToParent(QMouseEvent.pos())
            self.curr_pos = self.pos()

        else:
            # QMouseEvent.ignore()
            self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
        #     # self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
        #
        #
        # # if QMouseEvent.buttons() & Qt.RightButton:
        # #     self.timeline.mousePressEvent(QMouseEvent)

    def mouseReleaseEvent(self, QMouseEvent):
        self.timeline.set_time_indicator_visibility(False)
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.was_playing:
                self.player.play()
                self.was_playing = False
        else:
            QMouseEvent.ignore()
            # self.timeline.end_selector()
            # QMouseEvent.ignore()
            # self.timeline.end_selector()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            pos = self.mapToParent(QMouseEvent.pos())# - self.offset
            self.timeline.move_scrubber(pos.x())
            # self.move(self.curr_pos.x() + pos.x() + 5, 0)
            # self.player.set_media_time((self.curr_pos.x() + pos.x() + 5) * self.timeline.scale)

        if QMouseEvent.buttons() & Qt.RightButton:
            if self.timeline.selector is not None:
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))
            else:
                pos = self.mapToParent(QMouseEvent.pos()).x()
                self.timeline.move_scrubber(pos)
                # self.timeline.time_scrubber.move(pos, 0)
                # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            # QMouseEvent.ignore()

    def paintEvent(self, QPaintEvent):
        self.raise_()
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 0, 0))
        pen.setWidth(2)
        qp.setPen(pen)
        a = QtCore.QPoint(5, 0)
        b = QtCore.QPoint(5, self.height())
        qp.drawLine(a,b)
        if self.is_hovered:
            qp.fillRect(self.rect(),QtGui.QColor(255, 255, 255, 50))
        else:
            qp.fillRect(self.rect(), QtGui.QColor(255, 255, 255, 1))
        qp.end()


class TimelineTimemark(QtWidgets.QWidget):
    def __init__(self, parent, color = QColor(255,255,255,50)):
        super(TimelineTimemark, self).__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.color = color
        self.setFixedWidth(5)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.show()

    def paintEvent(self, a0: QtGui.QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)


        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(self.color)
        pen.setWidth(3)
        qp.setPen(pen)

        a = QtCore.QPoint(3, 0)
        b = QtCore.QPoint(3, self.height())
        qp.drawLine(a, b)

        qp.end()

    def move(self, a0: QtCore.QPoint):
        pos = QPoint(a0.x() - 3, a0.y())
        super(TimelineTimemark, self).move(pos)


class TimebarDrawing(QtWidgets.QWidget):
    def __init__(self,parent, timeline):
        super(TimebarDrawing, self).__init__(parent)
        self.timeline = timeline
        self.background_color = QtGui.QColor(50,50,50,230)
        self.scale_image = None

        self.colormetry_progress = 0

        self.is_hovered = False
        self.was_playing = False
        self.a = 50
        self.b = 200
        self.c = 1000
        self.time_offset = 0
        self.show()

    def paintEvent(self, QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        pen.setColor(QtGui.QColor(255, 255, 255))
        qp.fillRect(self.rect(),self.background_color)

        t_start = float(self.pos().x()) * self.timeline.scale / 1000
        t_end = t_start + float(self.width() * self.timeline.scale / 1000)
        self.time_offset = 0
        if self.timeline.scale <= self.a:
            for i in range(int(t_start), int(t_end)):

            #for i in range(int(self.timeline.duration) / 1000):
                # pos = i * 1000 / self.timeline.scale
                pos = round(float(i - t_start) / self.timeline.scale * 1000 + self.time_offset)
                if i % 2 == 0:
                    s = ms_to_string(i * 1000)
                    qp.drawText(QtCore.QPoint(pos - (len(s) / 2) * 7, 8), s)
                if i % 2 == 0:
                    h = 10
                    pen.setWidth(1)
                else:
                    pen.setWidth(1)
                    if float(i) % 1 == 0:
                        h = 15
                    if float(i) % 1 == 0.5:
                        h = 20
                qp.setPen(pen)
                a = QtCore.QPoint(pos, h)
                b = QtCore.QPoint(pos, 30)
                qp.drawLine(a, b)

        if self.a  < self.timeline.scale <= self.b:
            for i in range(int(t_start), int(t_end)):
            #for i in range(int(self.timeline.duration) / 1000):
                # pos = i * 1000 / self.timeline.scale
                pos = float(i - t_start) / self.timeline.scale * 1000 + self.time_offset
                if i % 30 == 0:
                    s = ms_to_string(i * 1000)
                    qp.drawText(QtCore.QPoint(pos - (len(s)/2)*7, 8), s)
                if i % 10 == 0:
                    h = 10
                    pen.setWidth(1)
                else:
                    pen.setWidth(1)
                    if i % 5 == 0:
                        h = 15
                    else:
                        h = 20
                qp.setPen(pen)
                a = QtCore.QPoint(pos, h)
                b = QtCore.QPoint(pos, 30)
                qp.drawLine(a, b)

        if self.b  < self.timeline.scale <= self.c:
            for i in range(int(t_start), int(t_end)):
            #for i in range(int(self.timeline.duration) / 1000):
                paint = True
                # pos = i * 1000 / self.timeline.scale
                pos = float(i - t_start) / self.timeline.scale * 1000 + self.time_offset
                if i % 60 == 0:
                    pen.setWidth(1)
                    s = ms_to_string(i * 1000)
                    qp.drawText(QtCore.QPoint(pos - (len(s)/2)*7, 8), s)
                    h = 10
                else:
                    if i % 30 == 0:
                        h = 15
                        pen.setWidth(1)
                    if i % 15 == 0:
                        h = 20
                    else:
                        paint = False

                if paint:
                    qp.setPen(pen)
                    a = QtCore.QPoint(pos, h)
                    b = QtCore.QPoint(pos, 30)
                    qp.drawLine(a, b)

        if self.c < self.timeline.scale:
            for i in range(int(t_start), int(t_end)):
            #for i in range(int(self.timeline.duration) / 1000):
                paint = True
                # pos = i * 1000 / self.timeline.scale
                pos = float(i - t_start) / self.timeline.scale * 1000 + self.time_offset
                if i % 600 == 0:
                    pen.setWidth(1)
                    s = ms_to_string(i * 1000)
                    qp.drawText(QtCore.QPoint(pos - (len(s)/2)*7, 8), s)
                    h = 10
                else:
                    if i % 300 == 0:
                        h = 15
                        pen.setWidth(1)
                    if i % 150 == 0:
                        h = 20
                    else:
                        paint = False

                if paint:
                    qp.setPen(pen)
                    a = QtCore.QPoint(pos, h)
                    b = QtCore.QPoint(pos, 30)
                    qp.drawLine(a, b)

        # Draw the colormetry progress Bar
        if  0.0 < self.colormetry_progress:
            pen.setColor(QtGui.QColor(35,165,103))
            pen.setWidth(3)
            t_progress = (self.timeline.duration * self.colormetry_progress)
            qp.setPen(pen)
            qp.drawLine(QPoint(0, self.height() - 2),
                        QPoint((t_progress - (self.pos().x()) * self.timeline.scale) /self.timeline.scale, self.height() - 2))
        qp.end()

    def mouseReleaseEvent(self, QMouseEvent):
        self.timeline.set_time_indicator_visibility(False)
        if QMouseEvent.button() == Qt.LeftButton:
            if self.was_playing:
                self.timeline.main_window.player.play()
            if self.timeline.shift_pressed and self.timeline.selector is not None:
                self.timeline.end_selector()



        if QMouseEvent.button() == Qt.RightButton:
            # self.timeline.end_selector()
            QMouseEvent.ignore()

    def mousePressEvent(self, QMouseEvent):
        self.was_playing = self.timeline.main_window.player.is_playing()
        self.timeline.set_time_indicator_visibility(True)
        if QMouseEvent.buttons() & Qt.LeftButton:
            old_pos = self.mapToParent(self.pos())
            if self.was_playing:
                self.timeline.main_window.player.pause()

            pos = self.mapToParent(QMouseEvent.pos()).x()
            # self.timeline.time_scrubber.move(pos, 0)
            # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            self.timeline.move_scrubber(pos)
            if self.timeline.shift_pressed:
                self.timeline.start_selector(old_pos)
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))

        if QMouseEvent.buttons() & Qt.RightButton:
            self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            pos = self.mapToParent(QMouseEvent.pos()).x()
            pos += 1 # offset correction
            self.timeline.move_scrubber(pos)
            # self.timeline.time_scrubber.move(pos, 0)
            # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            if self.timeline.shift_pressed and self.timeline.selector is not None:
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))

        if QMouseEvent.buttons() & Qt.RightButton:
            if self.timeline.selector is not None:
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))
            else:
                pos = self.mapToParent(QMouseEvent.pos()).x()
                # self.timeline.time_scrubber.move(pos, 0)
                # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
                self.timeline.move_scrubber(pos)


class TimebarSelector(QtWidgets.QWidget):
    def __init__(self, timeline, parent, pos):
        super(TimebarSelector, self).__init__(parent)
        self.timeline = timeline
        self.background_color = QtGui.QColor(50, 80, 100, 150)
        self.start = self.mapTo(self.timeline.frame_Bars, pos).x() * timeline.scale

        self.end = self.start

        self.rescale()
        self.show()

    def set_end(self, pos):
        self.end = self.mapToParent(pos).x() * self.timeline.scale
        self.rescale()

    def rescale(self):
        x = self.start / self.timeline.scale
        w = (self.end - self.start) / self.timeline.scale

        self.move(x, 0)
        self.resize(w, self.parent().height())

    def paintEvent(self, QPaintEvent):
        self.rescale()
        qp = QtGui.QPainter()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        qp.fillRect(self.rect(), self.background_color)

        qp.end()

        self.raise_()


class SelectorContextMenu(QtWidgets.QMenu):
    new_segment = pyqtSignal(list, object)
    new_segmentation = pyqtSignal()
    new_layer = pyqtSignal(list)

    # noinspection PyUnresolvedReferences
    def __init__(self, parent, pos, selector):
        super(SelectorContextMenu, self).__init__(parent)
        self.selector = selector
        self.timeline = parent

        self.project = self.timeline.project()
        self.setAttribute(Qt.WA_MacNoClickThrough)

        if self.timeline.selected is not None:
            if self.timeline.selected.get_type() == SEGMENTATION:
                self.action_add_segment = self.addAction("Add Segment")
                self.action_add_segment.triggered.connect(self.add_segment)

        self.true_end = self.selector.end
        if self.selector.width() < 20:
            self.selector.end = self.selector.start + 100 * self.timeline.scale

        self.action_add_layer = self.addAction("New Annotation Layer")
        self.action_add_segmentation = self.addAction("New Segmentation")

        self.action_add_layer.triggered.connect(self.on_add_layer)
        self.action_add_segmentation.triggered.connect(self.on_add_segmentation)

        self.annotation_menu = self.addMenu("Create Annotation")
        self.a_add_rectangle = self.annotation_menu.addAction("Rectangle")
        self.a_add_ellipse = self.annotation_menu.addAction("Ellipse")
        self.a_add_text = self.annotation_menu.addAction("Text")
        self.a_add_image = self.annotation_menu.addAction("Image")
        self.a_add_free_hand = self.annotation_menu.addAction("Free Hand")


        self.a_add_rectangle.triggered.connect(partial(self.timeline.main_window.drawing_overlay.create_rectangle,
                                                       [255, 255, 255], 12, start=self.selector.start, end=self.selector.end))
        self.a_add_ellipse.triggered.connect(partial(self.timeline.main_window.drawing_overlay.create_ellipse,
                                                       [255, 255, 255], 12, start=self.selector.start, end=self.selector.end))
        self.a_add_text.triggered.connect(partial(self.timeline.main_window.drawing_overlay.create_text,
                                                       [255, 255, 255], 12, 12, start=self.selector.start, end=self.selector.end))
        self.a_add_image.triggered.connect(partial(self.timeline.main_window.drawing_overlay.create_image,
                                                       image_path=None, start=self.selector.start, end=self.selector.end))
        self.a_add_free_hand.triggered.connect(partial(self.timeline.main_window.drawing_overlay.create_freehand,
                                                       [255, 255, 255], 12, start=self.selector.start, end=self.selector.end))

        self.popup(pos)

    def add_segment(self):
        self.new_segment.emit([self.selector.start, self.true_end], SegmentCreationMode.INTERVAL)
        self.close()

    def on_add_segmentation(self):
        self.new_segmentation.emit()
        self.close()

    def on_add_layer(self):
        self.new_layer.emit([self.selector.start, self.selector.end])
        self.close()

    def closeEvent(self, *args, **kwargs):
        self.timeline.close_selector()
        self.timeline.selector_context = None
        self.timeline.update()
        super(SelectorContextMenu, self).closeEvent(*args, **kwargs)


