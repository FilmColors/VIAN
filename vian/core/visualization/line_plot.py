import numpy as np
import cv2
import typing
from functools import partial
from collections import namedtuple
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QColor, QImage, QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QPen, QFont, QPainter, QPainterPath, QTransform
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QPoint, Qt, QRectF, pyqtSlot, pyqtSignal, QEvent, QSize, QPointF, QObject
from scipy.signal import savgol_filter

from vian.core.data.computation import *
from vian.core.visualization.basic_vis import VIANPlot
SOURCE_FOREGROUND = 0

LinePlotRawData = namedtuple("LinePlotRawData", ["x", "y", "z", "col", "mime_data", "curr_grid"])

class LinePlot(VIANPlot):
    onEntriesChanged = pyqtSignal(object)

    def __init__(self, parent, x_label_format = "value", y_label_format = "value"):
        super(LinePlot, self).__init__(parent, aspect=Qt.AspectRatioMode.KeepAspectRatio, x_label_format=x_label_format, y_label_format=y_label_format)
        self.lines = []
        self.line_xs = []
        self.line_ys = []
        self.line_cols = []
        self.line_map = dict()
        self.line_active = dict()
        self.time_indicator = None
        self.x_ceil = 1.0
        self.y_ceil = 1.0

        self.sub_sampling = 1

        self.force_xmax = None
        self.force_ymax = None

        self.param_widget = None
        self.param_widget_grid = None

    def clear_view(self, reset_params = False):
        self.lines = []
        self.line_xs = []
        self.line_ys = []
        self.line_cols = []
        self.line_map = dict()
        if reset_params:
            self.line_active = dict()
        self.time_indicator = None
        self.scene().clear()

    def set_time_indicator(self, x):
        if self.time_indicator is not None:
            try:
                self.scene().removeItem(self.time_indicator)
            except:
                pass
            self.time_indicator = None

        pen = QPen()
        pen.setColor(QColor(255,0,0,200))
        pen.setWidth(2)
        x = np.multiply(np.divide(x, self.x_ceil), self.base_line_x)
        self.time_indicator = self.scene().addLine(x, 0, x, self.base_line_x, pen)

    def set_x_scale(self, scale):
        super(LinePlot, self).set_x_scale(scale)
        self.time_indicator = None

    def set_y_scale(self, scale):
        super(LinePlot, self).set_y_scale(scale)
        self.time_indicator = None

    @pyqtSlot(int)
    def set_sub_sampling(self, v):
        self.sub_sampling = v * 5
        if self.sub_sampling % 2 == 0:
            self.sub_sampling += 1
        self.scene().clear()
        self.time_indicator = None
        self.draw()
        self.grid = []
        self.plot_grid()

    def plot(self, xs, ys, col = QColor(255,255,255), mime_data = None, line_name = None, force_xmax = None, force_ymax = None):
        if isinstance(xs, list):
            xs = np.array(xs)
        if isinstance(ys, list):
            ys = np.array(ys)

        # Clear existing line
        if line_name is not None:
            if line_name in self.line_map:
                idx = self.line_map[line_name]
                self.line_xs[idx] = xs
                self.line_ys[idx] = ys
                self.line_cols[idx] = col
            else:
                self.line_map[line_name] = len(self.line_xs)
                self.line_xs.append(xs)
                self.line_ys.append(ys)
                self.line_cols.append(col)
            if not line_name in self.line_active:
                self.line_active[line_name] = True

        self.onEntriesChanged.emit(self.line_active)

        self.force_xmax = force_xmax
        self.force_ymax = force_ymax

        self.scene().clear()
        self.lines = []
        self.grid = []
        self.draw()
        self.plot_grid()

        # point.setZValue(z)
        # self.points.append(point)
        # self.raw_data.append(LinePlotRawData(x=x, y = y, z = z, col=col, mime_data=None, curr_grid=self.curr_grid))


    def draw(self):
        if len(self.line_xs) == 0:
            return

        to_plot_x = []
        to_plot_y = []
        for k in self.line_map.keys():
            if self.line_active[k]:
                to_plot_x.append(self.line_xs[self.line_map[k]])
                to_plot_y.append(self.line_ys[self.line_map[k]])

        if len(to_plot_y) == 0:
            return

        if self.force_xmax is None:
            self.max_x = np.amax(to_plot_x)
        else:
            self.max_x = self.force_xmax
        if self.force_ymax is None:
            self.max_y = np.amax(to_plot_y)
        else:
            self.max_y = self.force_ymax

        x_ceil, x_step = self.get_ceil(self.max_x)
        y_ceil, y_step = self.get_ceil(self.max_y)

        self.x_ceil = x_ceil
        self.y_ceil = y_ceil

        xs = np.multiply(np.divide(self.line_xs, x_ceil), self.base_line_x)
        ys = np.multiply(np.divide(self.line_ys, y_ceil), self.base_line_y)

        if self.sub_sampling > 4:
            for i in range(ys.shape[0]):
                wf = np.clip(self.sub_sampling, 0, ys.shape[1] - 1)
                if wf % 2 == 0:
                    wf -= 1
                ys[i] = savgol_filter(ys[i], wf, 3)
        p = QPen()

        p.setWidth(0.1)
        to_plot = []
        for k in self.line_map.keys():
            if self.line_active[k]:
                to_plot.append(self.line_map[k])

        for j in range(xs.shape[0]):
            if j not in to_plot:
                continue

            p.setColor(self.line_cols[j])
            path = None

            for i in range(xs.shape[1]):
                x = xs[j][i]
                y = self.base_line_y - ys[j][i]

                if i == 0:
                    path = QPainterPath(QPointF(x, y))
                else:
                    path.lineTo(QPointF(x, y))

            if path is not None:
                path = self.scene().addPath(path, p)
                self.lines.append(path)

        p.setColor(QColor(255,255,255,200))
        n_legend = len(list(self.line_map.keys()))
        legend_box = self.scene().addRect(QRectF(self.base_line_x + 50, 50, 200, 30 * n_legend), p)

        font = QFont()
        font.setPointSize(10)
        c = 1
        for name in sorted(list(self.line_map.keys())):
            if not self.line_active[name]:
                continue
            y = 50 + ((c * 30) - 15)
            p.setColor(self.line_cols[self.line_map[name]])
            lbl = self.scene().addText(name, font)
            lbl.setPos(self.base_line_x + 55, y - lbl.boundingRect().height() / 2)
            lbl.setDefaultTextColor(QColor(255,255,255,255))
            self.scene().addLine(self.base_line_x + 55 + lbl.boundingRect().width() + 5, y, self.base_line_x + 245, y, p)
            c += 1

    def on_entry_state_changed(self, name, value):
        if name in self.line_active:
            self.line_active[name] = value

        self.scene().clear()
        self.draw()
        self.time_indicator = None
        self.grid = []
        self.plot_grid()

    def get_param_widget(self):
        w = LineParamWidget(None)
        w.onEntryStateChanged.connect(self.on_entry_state_changed)
        w.onXScale.connect(self.set_x_scale)
        w.onYScale.connect(self.set_y_scale)
        w.onSubSampling.connect(self.set_sub_sampling)
        self.onEntriesChanged.connect(w.on_entries_changed)
        return w

class LineParamWidget(QWidget):
    onEntryStateChanged = pyqtSignal(object, bool)
    onYScale = pyqtSignal(int)
    onXScale = pyqtSignal(int)
    onSubSampling = pyqtSignal(int)

    def __init__(self, parent):
        super(LineParamWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        hl2 = QHBoxLayout(self)
        hl2.addWidget(QLabel("Y-Scale:", self))
        hl3 = QHBoxLayout(self)
        hl3.addWidget(QLabel("X-Scale:", self))
        hl4 = QHBoxLayout(self)
        hl4.addWidget(QLabel("Filter:", self))

        slider_yscale = QSlider(Qt.Orientation.Horizontal, self)
        slider_yscale.setRange(1, 1000)
        slider_yscale.setValue(100)
        slider_yscale.valueChanged.connect(self.onYScale.emit)
        hl2.addWidget(slider_yscale)

        slider_xscale = QSlider(Qt.Orientation.Horizontal, self)
        slider_xscale.setRange(1, 1000)
        slider_xscale.setValue(100)
        slider_xscale.valueChanged.connect(self.onXScale.emit)
        hl3.addWidget(slider_xscale)

        slider_subsampling = QSlider(Qt.Orientation.Horizontal, self)
        slider_subsampling.setRange(1, 20)
        slider_subsampling.setValue(1)
        slider_subsampling.valueChanged.connect(self.onSubSampling.emit)
        hl4.addWidget(slider_subsampling)

        self.layout().addItem(hl2)
        self.layout().addItem(hl3)
        self.layout().addItem(hl4)
        self.grid = QGridLayout()
        self.layout().addItem(self.grid)

        self.all_checkboxes = dict()

    def on_entries_changed(self, entries):
        x = 0
        y = 0
        if entries.keys() == self.all_checkboxes.keys():
            for cb in self.all_checkboxes.values():
                cb.show()
            return
        for key in entries.keys():
            if key in self.all_checkboxes:
                cb = self.all_checkboxes[key]
            else:
                cb = QCheckBox(key, self)
                cb.setChecked(entries[key])
                cb.stateChanged.connect(partial(self.on_check_state_changed, key))
            self.grid.addWidget(cb, y, x)
            x += 1
            if x == 3:
                x = 0
                y += 1
            self.all_checkboxes[key] = cb
            cb.show()

    def on_check_state_changed(self, name):
        s = self.sender()
        self.onEntryStateChanged.emit(name, s.isChecked())
