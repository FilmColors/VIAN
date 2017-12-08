import os

import numpy as np
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPushButton

from core.data.computation import ms_to_string, numpy_to_qt_image
from core.data.interfaces import IProjectChangeNotify, ITimeStepDepending
from core.gui.ewidgetbase import EDockWidget, EToolBar
from core.data.containers import *
from core.gui.context_menu import open_context_menu


class TimelineContainer(EDockWidget):
    def __init__(self, main_window):
        super(TimelineContainer, self).__init__(main_window, limit_size=False)
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

        self.menu_display = self.inner.menuBar().addMenu("Display")
        self.a_show_id = self.menu_display.addAction("\tID")
        self.a_show_id.setCheckable(True)
        self.a_show_id.setChecked(True)

        self.a_show_name = self.menu_display.addAction("\tName")
        self.a_show_name.setCheckable(True)
        self.a_show_name.setChecked(True)

        self.a_show_text = self.menu_display.addAction("\tText")
        self.a_show_text.setCheckable(True)
        self.a_show_text.setChecked(True)

        self.a_show_id.triggered.connect(self.update_settings)
        self.a_show_name.triggered.connect(self.update_settings)
        self.a_show_text.triggered.connect(self.update_settings)

        # self.inner.addToolBar(self.toolbar)

    def resizeEvent(self, *args, **kwargs):
        super(TimelineContainer, self).resizeEvent(*args, **kwargs)
        self.timeline.update_time_bar()

    def update_settings(self):
        self.timeline.show_id = self.a_show_id.isChecked()
        self.timeline.show_name = self.a_show_name.isChecked()
        self.timeline.show_text = self.a_show_text.isChecked()


        self.timeline.on_timeline_settings_update()



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
        self.is_fast_selecting = False
        self.is_marquee_selecting = False
        self.item_segments = []
        self.item_screenshots = []
        self.item_ann_layers = []
        self.items = []
        self.bar_height = 45
        self.group_height = 15
        self.controls_width = 200
        self.time_bar_height = 50
        self.timeline_tail = 100
        self.time_bar = None
        self.frame_Bars.setFixedSize(self.duration, 500)
        self.frame_Bars.move(self.controls_width, 0)
        self.frame_Controls.setFixedSize(self.controls_width, 500)
        self.frame_Controls.move(0, 0)
        self.relative_corner = QtCore.QPoint(self.controls_width, 0)

        self.selected = None

        self.interval_segmentation_start = None
        self.interval_segmentation_marker = None

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
        self.show_name = True
        self.show_text = True

        self.update_time_bar()
        self.update_ui()

        self.scrollArea.wheelEvent = self.func_tes

        self.main_window.onTimeStep.connect(self.on_timestep_update)

        self.main_window.actionIntervalSegmentStart.triggered.connect(self.on_interval_segment_start)
        self.main_window.actionIntervalSegmentEnd.triggered.connect(self.on_interval_segment_end)




        # self.update_timer = QtCore.QTimer()
        # self.update_timer.setInterval(100)
        # self.update_timer.timeout.connect(self.update_time)
        # self.update_timer.start()

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

    def add_item(self, ctrl_itm, bar_itms):
        control = self.add_control()
        bars = []
        for i in bar_itms:
            bars.append(self.add_bar())
        item = [control, bars]
        self.items.append(item)
        self.update_ui()

    def add_segmentation(self, segmentation):
        control = TimelineControl(self.frame_Controls,self, segmentation)
        bars = TimelineBar(self.frame_Bars, self)
        for i, s in enumerate(segmentation.segments):
            bars.add_slice(s)
        item = [control, [bars], self.bar_height]
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
                self.selected.create_segment(self.interval_segmentation_start, self.curr_movie_time)
            else:
                self.main_window.print_message("No Segmentation Selected", "Orange")

            self.interval_segmentation_start = None
            self.interval_segmentation_marker.deleteLater()
            self.interval_segmentation_marker = None
        else:

            self.main_window.print_message("Please set a Start Point First", "Orange")

    def add_annotation_layer(self, layer):
        control = TimelineControl(self.frame_Controls,self, layer)
        bars = TimelineBar(self.frame_Bars, self)
        bars.add_slice(layer)
        height = self.bar_height
        for i, a in enumerate(layer.annotations):
            keys = []
            for k in a.keys:
                keys.append(k)
            bars.add_annotation(a, keys)
            control.add_group(a)

            if i * self.group_height + self.group_height > self.bar_height:
                height += self.group_height
        height += self.group_height

        item = [control, [bars], height]
        self.item_ann_layers.append(item)
        self.items.append(item)
        self.update_ui()

    def add_screenshots(self, screenshots, screenshot_group, grp_name = "Screenshots", ):
        control = TimelineControl(self.frame_Controls, self, name = grp_name, item=screenshot_group)
        bars = ScreenshotBar(self.frame_Bars, self, screenshots)
        item = [control, [bars], self.bar_height]
        self.item_screenshots.append(item)
        self.items.append(item)
        self.update_ui()

    def add_bar(self):
        b = TimelineBar(self.frame_Bars, self)
        return b

    def clear(self):
        # self.time_bar.close()
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

    def paintEvent(self, QPaintEvent):
        #TODO are these statements really necessary??
        # self.frame_Controls.setFixedSize(self.controls_width, self.frame_Controls.height())
        # self.frame_Bars.setFixedSize(self.duration /self.scale + self.controls_width + self.timeline_tail, self.frame_Bars.height())
        # self.frame_outer.setFixedSize(self.frame_Bars.size().width(), self.frame_Bars.height())
        # self.time_scrubber.setFixedHeight(self.height())

        super(Timeline, self).paintEvent(QPaintEvent)



        # This makes OSX go crazy
        # self.update_time_bar()


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

        # self.time_bar.move(self.scrollArea.mapToParent(QtCore.QPoint(0, value)))
        # # self.time_bar.setFixedSize(self.duration / self.scale + self.controls_width, self.time_bar_height)
        # self.time_bar.setFixedSize(self.width() - self.controls_width, self.time_bar_height)
        # self.time_bar.raise_()

        self.relative_corner = QtCore.QPoint(value, self.relative_corner.y())

        h = self.scrubber_min_h
        if self.scrubber_min_h < self.frame_Bars.height():
            h = self.frame_Bars.height()
        self.time_scrubber.resize(self.scrubber_width, h)

        loc_y = self.time_bar_height
        for i in self.items:
            ctrl_height = 6
            ctrl = i[0]
            bars = i[1]
            item_height = i[2]
            ctrl.move(2, loc_y)
            for b in bars:
                b.move(0, loc_y)
                b.resize(self.duration/self.scale, item_height)
                loc_y += item_height
                ctrl_height += item_height + 4
                b.rescale()
            ctrl.resize(self.controls_width - 4, ctrl_height)

        if loc_y + self.bar_height < 400:
            loc_y = 400 - self.bar_height

        # self.frame_Bars.setFixedSize(self.duration / self.scale + self.controls_width + self.timeline_tail, loc_y + self.bar_height)
        # self.frame_Controls.setFixedSize(self.controls_width, self.frame_Bars.height())

        self.frame_Controls.setFixedSize(self.controls_width, self.frame_Controls.height())
        self.frame_Bars.setFixedSize(self.duration / self.scale + self.controls_width + self.timeline_tail,
                                     self.frame_Bars.height())
        self.frame_outer.setFixedSize(self.frame_Bars.size().width(), self.frame_Bars.height())
        self.time_scrubber.setFixedHeight(self.frame_Bars.height())

        self.time_bar.raise_()



    def on_loaded(self, project):
        self.clear()
        self.time_bar.close()
        for s in project.segmentation:
            self.add_segmentation(s)

        for l in project.annotation_layers:
            self.add_annotation_layer(l)

        for grp in project.screenshot_groups:
            self.add_screenshots(grp.screenshots, grp, grp.get_name())

        self.update_time_bar()
        self.update_ui()
        self.scroll_h()

    def on_changed(self, project, item):
        self.clear()
        self.duration = project.get_movie().duration

        for s in project.segmentation:
            if s.get_timeline_visibility() is True:
                self.add_segmentation(s)

        for l in project.annotation_layers:
            if l.get_timeline_visibility() is True:
                self.add_annotation_layer(l)

        for grp in project.screenshot_groups:
            self.add_screenshots(grp.screenshots, grp, grp.get_name())

        # self.update_time_bar()
        self.update_ui()

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
        self.update_time_bar()
        self.update()

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.is_scaling = True
            self.scrollArea.verticalScrollBar().setEnabled(False)
        elif QKeyEvent.key() == Qt.Key_Shift:
            self.is_fast_selecting = True

    def keyReleaseEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.is_scaling = False
            self.scrollArea.verticalScrollBar().setEnabled(True)
        elif QKeyEvent.key() == Qt.Key_Shift:
            self.is_fast_selecting = False

    def wheelEvent(self, QWheelEvent):
        if self.is_scaling:
            self.zoom_timeline(QWheelEvent.pos(), QWheelEvent.angleDelta())
        else:
            x = -1 * QWheelEvent.angleDelta().x() + self.scrollArea.horizontalScrollBar().value()
            y = -1 * QWheelEvent.angleDelta().y() + self.scrollArea.verticalScrollBar().value()
            self.scrollArea.horizontalScrollBar().setValue(x)
            self.scrollArea.verticalScrollBar().setValue(y)

    def zoom_timeline(self, pos, angleDelta):
        if self.is_scaling:
            center_point = (pos.x() - self.controls_width) * self.scale + self.scrollArea.horizontalScrollBar().value() * self.scale
            delta = (pos.x() - self.controls_width)

            s_max = int(self.duration / self.width()) + self.controls_width + 400 # + 400 to make sure the whole timeline can be looked at once
            self.scale = np.clip(- angleDelta.y() * (0.0005 * self.scale) + self.scale, None, s_max)
            self.update_ui()
            self.update()

            side_offset = center_point - delta * self.scale
            self.time_scrubber.move(self.curr_movie_time // self.scale - 5, 0)

            if self.interval_segmentation_marker is not None:
                self.interval_segmentation_marker.move(QPoint(self.interval_segmentation_start/self.scale, 0))

            self.scrollArea.horizontalScrollBar().setValue(side_offset // self.scale)


    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if self.is_fast_selecting:
                if self.selector is None:
                    self.start_selector(self.time_scrubber.pos())
                    self.move_selector(QMouseEvent.pos())
                else:
                    self.move_selector(QMouseEvent.pos())


        if QMouseEvent.button() == Qt.RightButton:
            self.start_selector(QMouseEvent.pos())

            # self.delta = QMouseEvent.pos() - self.frame_Bars.pos()
            # pos = QMouseEvent.pos() - self.frame_Bars.pos()
            # self.selector = TimebarSelector(self, self.frame_Bars, pos)
            # self.is_selecting = True

    # def start_selector(self, pos):
    #     self.delta = pos - self.frame_Bars.pos()
    #     pos = pos - self.frame_Bars.pos()
    #     self.selector = TimebarSelector(self, self.frame_Bars, pos)
    #     self.is_selecting = True

    def mouseReleaseEvent(self, QMouseEvent):
        if self.is_selecting and not self.is_fast_selecting:
            self.end_selector()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.RightButton or self.is_fast_selecting:
            pos = self.round_to_grid(QMouseEvent.pos() - self.frame_Bars.pos())
            self.move_selector(pos)

    def start_selector(self, pos):
        self.delta = pos
        self.selector = TimebarSelector(self, self.frame_Bars, pos)
        self.is_selecting = True

    def move_selector(self, pos):
        if self.is_selecting:
            pos_r = pos - self.delta
            self.selector.set_end(pos_r)

            time = (pos.x() * self.scale)
            self.main_window.player.set_media_time(time)

    def end_selector(self):

        if self.is_selecting:
            self.is_selecting = False
            pos = self.selector.pos().x() + self.selector.width() + self.pos().x()

            self.selector_context = SelectorContextMenu(self, self.mapToGlobal(QtCore.QPoint(pos, self.pos().y())), self.selector)
            self.selector_context.new_segmentation.connect(self.create_segmentation)
            self.selector_context.new_segment.connect(self.create_segment)
            self.selector_context.new_layer.connect(self.create_layer)
            self.selector_context.show()

    # CONTEXT MENU BINDINGS
    def new_segment(self):
        if self.selector is not None and self.selected is not None:
            if self.selected.get_type() == SEGMENTATION:
                self.selected.create_segment(self.selector.start, self.selector.stop)

    def close_selector(self):
        if self.selector is not None:
            self.selector.close()
            self.selector.deleteLater()
        self.selector = None

    def round_to_grid(self, a):
        if isinstance(a, QtCore.QPoint):
            px = a.x() - (a.x() % (float(self.settings.GRID_SIZE) / self.scale))
            py = a.y() - (a.y() % (float(self.settings.GRID_SIZE) / self.scale))
            return QtCore.QPoint(int(px), int(py))
        else:
            return int(a - (a % (float(self.settings.GRID_SIZE) / self.scale)))

    def on_timeline_settings_update(self):
        for s in self.item_segments:
            for bar in s[1]:
                for slice in bar.slices:
                    slice.update_text()

    def create_segment(self, lst = None):
        # If Nothing is handed in, we're performing a fast-segmentation
        # which means, that the segment is created from the last segments end to the current movie-time
        if not lst:
            lst = [self.curr_movie_time - 1, self.curr_movie_time]
        if self.selected is not None:
            if self.selected.get_type() == SEGMENTATION:
                self.selected.create_segment(lst[0], lst[1])

    def create_layer(self, lst):
        if len(lst) == 0:
            lst = [self.curr_movie_time, self.duration]
        self.project().create_annotation_layer("New Layer", lst[0], lst[1])

    def create_segmentation(self):
        self.project().create_segmentation("New Segmentation")

    def resizeEvent(self, QResizeEvent):
        super(Timeline, self).resizeEvent(QResizeEvent)


class TimelineControl(QtWidgets.QWidget):
    def __init__(self, parent,timeline, item = None, name = "No Name"):
        super(TimelineControl, self).__init__(parent)
        self.timeline =  timeline
        self.item = item
        self.h_exp = 300
        self.h_col = 100
        self.name = name
        self.set_name()
        self.groups = []

        self.is_selected = False

        self.show()

    def set_name(self):
        if self.item is not None:
            self.name = self.item.get_name()

    def add_group(self, annotation):
        y = len(self.groups) * self.timeline.group_height
        text = annotation.get_name()
        self.groups.append([annotation, text])

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.timeline.select(self)

        if QMouseEvent.button() == Qt.RightButton:
            context = open_context_menu(self.timeline.main_window,self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())
            context.show()

    def paintEvent(self, QPaintEvent):
        super(TimelineControl, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255, 50))
        pen.setWidth(1)
        qp.setPen(pen)

        for i,a in enumerate(self.groups):
            y = i * self.timeline.group_height + self.timeline.group_height
            if i == 0:
                p1 = QtCore.QPoint(self.x(), y)
                p2 = QtCore.QPoint(self.width(), y)
                qp.drawLine(p1, p2)

            p1 = QtCore.QPoint(self.x(), y+ self.timeline.group_height)
            p2 = QtCore.QPoint(self.width(), y+ self.timeline.group_height)
            qp.drawLine(p1, p2)

        pen.setColor(QtGui.QColor(255, 255, 255, 200))
        qp.setPen(pen)
        for i, a in enumerate(self.groups):
            y = i * self.timeline.group_height + self.timeline.group_height
            text_rect = QtCore.QRect(0, y, self.width(), self.timeline.group_height)
            qp.drawText(text_rect, Qt.AlignRight, a[1])

        pen.setColor(QtGui.QColor(255, 255, 255, 255))
        qp.setPen(pen)
        qp.drawLine(QtCore.QPoint(0,0), QtCore.QPoint(self.width(), 0))

        # Title of the Control

        qp.drawText(QtCore.QPoint(0,10), self.name)

        if isinstance(self.item, ILockable):
            if self.item.is_locked():
                qp.drawPixmap(QtCore.QRect(0, 25, 16, 16), QPixmap("qt_ui/icons/icon_locked.png"))
        # qp.drawLine(QtCore.QPoint(0, self.height()), QtCore.QPoint(self.width(), self.height()))
        if self.is_selected:
            qp.fillRect(QtCore.QRect(0,0,self.width(), self.height() - 10), QtGui.QColor(200, 200, 255, 50))
        qp.end()


class TimelineBar(QtWidgets.QFrame):
    def __init__(self, parent, timeline, height = 45):
        super(TimelineBar, self).__init__(parent)
        self.resize(parent.width(), height)
        self.timeline = timeline

        self.is_selected = False

        self.setFrameStyle(1)
        self.slices = []
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

    def add_slice(self, item):
        slice = TimebarSlice(self, item, self.timeline)
        slice.move(item.get_start() // self.timeline.scale, 0)
        slice.resize((item.get_end() - item.get_start()) // self.timeline.scale, self.height())
        self.slices.append(slice)

    def rescale(self):
        for a in self.annotations:
            for k in a[1]:
                k.move(a[0].keys[k.key_index][0] // self.timeline.scale, k.y())

        for s in self.slices:
            s.move(s.item.get_start() // self.timeline.scale, 0)
            s.resize((s.item.get_end() - s.item.get_start()) // self.timeline.scale, self.height())

    def paintEvent(self, QPaintEvent):
        super(TimelineBar, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255, 50))
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

        if self.is_selected:
            qp.fillRect(self.rect(), QtGui.QColor(255, 255, 255, 50))
        qp.end()


class TimebarSlice(QtWidgets.QWidget):
    def __init__(self, parent, item, timeline):
        super(TimebarSlice, self).__init__(parent)
        self.locked = False
        self.timeline = timeline
        self.item = item
        self.show()
        self.mode = "center"
        self.setMouseTracking(True)
        self.border_width = 10
        self.offset = QtCore.QPoint(0,0)
        self.text = ""

        self.update_text()

        self.color = (232, 174, 12, 100)
        if item.get_type() == ANNOTATION_LAYER:
            self.color = (232,55,40,100)
        if item.get_type() == SEGMENT:
            self.color = (202, 54, 109, 100)

        self.text_size = 10



        self.is_hovered = False
        self.is_selected = False

    def paintEvent(self, QPaintEvent):
        self.locked = False
        if isinstance(self.item, ILockable):
            self.locked = self.item.is_locked()

        if self.locked :
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 20)

        else:
            if self.is_hovered:
                col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 80)
            else:
                col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 50)

            if self.is_selected:
                col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 100)

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)

        qp.drawRect(QtCore.QRect(0, 0, self.width(), self.height()))
        qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), col)
        qp.drawText(5, (self.height() + self.text_size) // 2, self.text)
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
                self.is_selected = True
                self.timeline.project().set_selected(None, self.item)
                self.offset = self.mapToParent(QMouseEvent.pos())
                self.curr_size = self.size()
                self.curr_pos = self.pos()
                self.update()

            if QMouseEvent.buttons() & Qt.RightButton:
                open_context_menu(self.timeline.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())

    def mouseReleaseEvent(self, QMouseEvent):
        # if the the movement is smaller than the grid-size ignore it
        if not self.locked:
            if np.abs(self.pos().x() * self.timeline.scale - self.item.get_start()) < self.timeline.settings.GRID_SIZE and \
                 np.abs(self.width() * self.timeline.scale - (self.item.get_end() - self.item.get_start())) < self.timeline.settings.GRID_SIZE:
                self.move(self.item.get_start()//self.timeline.scale, 0)
                self.resize((self.item.get_end() - self.item.get_start()) // self.timeline.scale, self.height())
                return

            if self.mode == "center":
                self.item.move(int(self.pos().x() * self.timeline.scale), int((self.pos().x() + self.width()) * self.timeline.scale))
                return
            if self.mode == "left":
                self.item.set_start(int(self.pos().x() * self.timeline.scale))
                return
            if self.mode == "right":
                self.item.set_end(int((self.pos().x() + self.width()) * self.timeline.scale))
                return

    def enterEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = True

    def leaveEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = False

    def mouseMoveEvent(self, QMouseEvent):
        if not self.locked:
            if QMouseEvent.buttons() & Qt.LeftButton:
                pos = self.mapToParent(QMouseEvent.pos())
                target = pos - self.offset
                tx = int(self.timeline.round_to_grid(target.x()))
                ty = int(self.timeline.round_to_grid(target.y()))
                target = QtCore.QPoint(int(tx), int(ty))

                if self.mode == "right":
                    x = np.clip(self.curr_size.width() + target.x(),self.curr_pos.x() - self.offset.x() + 5,None)
                    self.resize(x, self.height())
                    self.update()
                    return

                if self.mode == "left":
                    x = np.clip(self.curr_pos.x() + target.x(), a_min=0, a_max=self.curr_pos.x() + self.curr_size.width())
                    w = np.clip(self.curr_size.width() - target.x(), a_min=0, a_max=self.curr_pos.x() + self.curr_size.width())
                    self.move(x, 0)
                    self.resize(w, self.height())
                    self.update()
                    return

                if self.mode == "center":
                    x = np.clip(self.curr_pos.x() + target.x(), 0, self.parent().width()-self.width())
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

    def update(self, *__args):
        super(TimebarSlice, self).update(*__args)


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


class ScreenshotBar(TimelineBar):
    def __init__(self, parent, timeline, screenshots, height=45):
        super(ScreenshotBar, self).__init__(parent, timeline, height=45)
        self.screenshots = []
        self.pictures = []
        self.timeline = timeline

        for s in screenshots:
            pic = TimebarPicture(self, s, timeline)
            pic.move(s.get_start()//timeline.scale, 0)
            self.pictures.append(pic)

        self.show()

    def rescale(self):
        for s in self.pictures:
            s.move(s.item.get_start()//self.timeline.scale, 0)


class TimebarPicture(QtWidgets.QWidget):
    def __init__(self, parent, screenshot, timeline, height = 43):
        super(TimebarPicture, self).__init__(parent)
        self.item = screenshot
        self.timeline = timeline
        self.is_hovered = False
        self.color = (123, 86, 32, 100)
        self.pic_height = height
        qimage, qpixmap = numpy_to_qt_image(screenshot.get_preview(scale=0.1))
        self.qimage = qimage
        self.size = (screenshot.img_movie.shape[0], screenshot.img_movie.shape[1])
        width = self.size[1] * self.pic_height // self.size[0]
        self.img_rect = QtCore.QRect(1, 1, width, self.pic_height)
        self.resize(width, self.pic_height)
        self.show()

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

    def leaveEvent(self, QEvent):
        self.is_hovered = False


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

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.was_playing = self.player.is_playing()
            self.player.pause()
            self.timeline.main_window.update_timer.stop()
            self.offset = self.mapToParent(QMouseEvent.pos())
            self.curr_pos = self.pos()

        else:
            QMouseEvent.ignore()
            # self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))


        # if QMouseEvent.buttons() & Qt.RightButton:
        #     self.timeline.mousePressEvent(QMouseEvent)

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.was_playing:
                self.player.play()
                self.was_playing = False
        else:
            QMouseEvent.ignore()
            # self.timeline.end_selector()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            pos = self.mapToParent(QMouseEvent.pos()) - self.offset
            self.move(self.curr_pos.x() + pos.x() + 5, 0)
            self.player.set_media_time((self.curr_pos.x() + pos.x() + 5) * self.timeline.scale)

        if QMouseEvent.buttons() & Qt.RightButton:
            QMouseEvent.ignore()

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
            if not self.timeline.main_window.player.playing:
                self.timeline.main_window.drawing_overlay.show_opencv_image()
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
            if not self.timeline.main_window.player.playing:
                self.timeline.main_window.drawing_overlay.show_opencv_image()
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
            self.timeline.main_window.drawing_overlay.hide_opencv_image()
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

        qp.end()

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if self.was_playing:
                self.timeline.main_window.player.play()
            if self.timeline.is_fast_selecting and self.timeline.selector is not None:
                self.timeline.end_selector()



        if QMouseEvent.button() == Qt.RightButton:
            self.timeline.end_selector()

    def mousePressEvent(self, QMouseEvent):
        self.was_playing = self.timeline.main_window.player.is_playing()
        if QMouseEvent.buttons() & Qt.LeftButton:
            old_pos = self.mapToParent(self.pos())
            if self.was_playing:
                self.timeline.main_window.player.pause()

            pos = self.mapToParent(QMouseEvent.pos()).x()
            self.timeline.time_scrubber.move(pos, 0)
            self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            if self.timeline.is_fast_selecting:
                self.timeline.start_selector(old_pos)
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))


        if QMouseEvent.buttons() & Qt.RightButton:
            self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            pos = self.mapToParent(QMouseEvent.pos()).x()
            pos += 1 #offset correction
            self.timeline.time_scrubber.move(pos, 0)
            self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            if self.timeline.is_fast_selecting and self.timeline.selector is not None:
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))

        if QMouseEvent.buttons() & Qt.RightButton:
            self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))


class TimebarSelector(QtWidgets.QWidget):
    def __init__(self, timeline, parent, pos):
        super(TimebarSelector, self).__init__(parent)
        self.timeline = timeline
        self.background_color = QtGui.QColor(50, 80, 100, 150)
        self.start = self.mapToParent(pos).x() * timeline.scale
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
    new_segment = pyqtSignal(list)
    new_segmentation = pyqtSignal()
    new_layer = pyqtSignal(list)
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
        if self.selector.width() < 10:
            self.selector.end = self.selector.start + 100 * self.timeline.scale

        self.action_add_layer = self.addAction("New Annotation Layer")
        self.action_add_segmentation = self.addAction("New Segmentation")

        self.action_add_layer.triggered.connect(self.on_add_layer)
        self.action_add_segmentation.triggered.connect(self.on_add_segmentation)

        self.popup(pos)

    def add_segment(self):
        self.new_segment.emit([self.selector.start, self.true_end])
        self.hide()

    def on_add_segmentation(self):
        self.new_segmentation.emit()
        self.hide()

    def on_add_layer(self):
        self.new_layer.emit([self.selector.start, self.selector.end])
        self.hide()

    def closeEvent(self, *args, **kwargs):
        self.timeline.close_selector()
        super(SelectorContextMenu, self).closeEvent(*args, **kwargs)
        self.timeline.update()
