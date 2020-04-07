from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from core.gui.timeline.timeline_base import TimelineControl, TimelineBar, TimebarSlice

from core.analysis.color_feature_extractor import ColorFeatureAnalysis
from core.data.interfaces import TimelineDataset
from core.container.project import *


class TimelineVisualizationControl(TimelineControl):
    def __init__(self, parent,timeline, item = None, name = "No Name"):
        super(TimelineVisualizationControl, self).__init__(parent,timeline, item, name)


class TimelineVisualization(TimelineBar):
    def __init__(self, parent, timeline, control, dataset:TimelineDataset = None, height = 45):
        super(TimelineVisualization, self).__init__(parent, timeline, control, height)
        self.dataset = dataset
        self.line_color = QColor(98, 161, 169)

    def render_image(self):
        t_start = self.timeline.get_current_t_start()
        t_end = self.timeline.get_current_t_end()
        data, ms = self.dataset.get_data_range(t_start, t_end)

        qimage = QtGui.QImage(self.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        qimage.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(qimage)

        pen = QtGui.QPen()

        qp.setPen(pen)
        qp.begin(qimage)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing, True)

        rect = QRect(self.rect().x(),
                     self.rect().y(),
                     np.clip(self.rect().width(), None, self.timeline.duration / self.timeline.scale),
                     self.rect().height())

        qp.fillRect(rect, QtGui.QColor(12, 12, 12))
        return qimage, qp, data, t_start, t_end, ms


class TimelineLinePlot(TimelineVisualization):
    def __init__(self, parent, timeline, control, dataset:TimelineDataset = None, height=45):
        super(TimelineLinePlot, self).__init__(parent, timeline, control, height)
        self.dataset = dataset
        self.image = None
        self.last_values = None
        self.line_color = QColor(98, 161, 169)

    def on_height_changed(self, height):
        super(TimelineLinePlot, self).on_height_changed(height)
        self.setFixedHeight(height)

    def render_image(self):
        qimage, qp, data, t_start, t_end, ms = super(TimelineLinePlot, self).render_image()
        pen = QtGui.QPen()
        pen.setColor(self.line_color)
        qp.setPen(pen)
        path = None
        for i in range(data.shape[0]):
            x = ((ms[i] - t_start)) / self.timeline.scale
            y = self.height() - (data[i] * self.height())
            if i == 0:
                path = QPainterPath(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))
        if path is not None:
            qp.drawPath(path)

        pen = QtGui.QPen()
        pen.setColor(QColor(37, 37, 37))

        qp.setPen(pen)
        r = self.rect()
        r.adjust(1, 1, -1, -1)
        qp.drawRect(r)
        qp.end()
        self.image = qimage


    def paintEvent(self, QPaintEvent):
        t_start = self.timeline.get_current_t_start()
        t_end = self.timeline.get_current_t_end()
        values = (t_start, t_end, self.height(), self.width())

        if self.last_values != values or self.image is None:
            self.render_image()
            self.last_values = values

        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        pen.setColor(QColor(37, 37, 37))
        qp.setPen(pen)
        qp.begin(self)
        qp.drawImage(QRectF(self.rect()), self.image)
        r = self.rect()
        r.adjust(1, 1, -1, -1)
        qp.drawRect(r)

        qp.end()


class TimelineAreaPlot(TimelineVisualization):
    def __init__(self, parent, timeline, control, dataset:TimelineDataset = None, height=45):
        super(TimelineAreaPlot, self).__init__(parent, timeline, control, height)
        self.dataset = dataset
        self.fill_color = QColor(200,100,20)
        self.image = None

        self.last_values = (0,0,0,0)

    def on_height_changed(self, height):
        super(TimelineAreaPlot, self).on_height_changed(height)
        self.setFixedHeight(height)

    def render_image(self):
        qimage, qp, data, t_start, t_end, ms = super(TimelineAreaPlot, self).render_image()
        itms = list(range(data.shape[0]))
        path = None
        for i in itms:
            x = ((ms[i] - t_start)) / self.timeline.scale
            y = self.height() - (0.5 * self.height()) + ((data[i]) * self.height() / 2)
            if i == 0:
                path = QPainterPath(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))

        for i in itms[::-1]:
            x = ((ms[i] - t_start)) / self.timeline.scale
            y = self.height() - (0.5 * self.height()) - ((data[i]) * self.height() / 2)
            path.lineTo(QPointF(x, y))

        if path is not None:
            qp.drawPath(path)
            qp.fillPath(path, QColor(self.fill_color))
        qp.end()
        self.image = qimage

    def paintEvent(self, QPaintEvent):
        t_start = self.timeline.get_current_t_start()
        t_end = self.timeline.get_current_t_end()
        values = (t_start, t_end, self.height(), self.width())

        if self.last_values != values or self.image is None:
            self.render_image()
            self.last_values = values

        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        pen.setColor(QColor(37,37, 37))
        qp.setPen(pen)
        qp.begin(self)
        qp.drawImage(QRectF(self.rect()), self.image)
        r = self.rect()
        r.adjust(1, 1, -1, -1)
        qp.drawRect(r)

        qp.end()