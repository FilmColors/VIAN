from PyQt6 import QtGui
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import QSlider, QLabel, QHBoxLayout

from vian.core.gui.timeline.timeline_base import TimelineControl, TimelineBar, QPushButton
from vian.core.container.project import *
from vian.core.data.interfaces import TimelineDataset

class TimelineVisualizationControl(TimelineControl):
    onVisibilityChanged = pyqtSignal(bool)

    def __init__(self, parent, timeline, item = None, name = "No Name"):
        super(TimelineVisualizationControl, self).__init__(parent,timeline, item, name)
        self.sp_filter = QSlider(Qt.Orientation.Horizontal)
        self.sp_filter.setMinimum(1)
        self.sp_filter.setMaximum(20)
        self.sp_filter.setStyleSheet("background-color: rgba(0, 0, 0, 0);")  # for transparent background

        self.filter_layout = QHBoxLayout()


        self.filterlabel = QLabel("Filter")
        self.filterlabel.setStyleSheet("background-color: rgba(0, 0, 0, 0);") #for transparent background
        self.filter_layout.addWidget(self.filterlabel)
        self.filter_layout.addWidget(self.sp_filter)

        self.btn_toggle_visible = QPushButton("Hide")
        self.btn_toggle_visible.clicked.connect(self.on_hide)
        self.btn_toggle_visible.setStyleSheet("background-color: rgba(0, 0, 0, 0);")  # for transparent background
        self.filter_layout.addWidget(self.btn_toggle_visible)

        self.mainLayout.addLayout(self.filter_layout)

    def on_hide(self):
        if self.btn_toggle_visible.text() == "Hide":
            self.onVisibilityChanged.emit(False)
            self.btn_toggle_visible.setText("Show")
        else:
            self.onVisibilityChanged.emit(True)
            self.btn_toggle_visible.setText("Hide")


class TimelineVisualization(TimelineBar):
    def __init__(self, parent, timeline, control, dataset:TimelineDataset = None, height = 45):
        super(TimelineVisualization, self).__init__(parent, timeline, control, height)
        self.dataset = dataset
        control.sp_filter.valueChanged.connect(partial(self.render_image))

        self.last_data = None
        self.t_start = 0
        self.t_end = 0
        self.hover_dot_size = int(self.fontMetrics().height() * 0.8)

        self.control.onVisibilityChanged.connect(self.on_visibility_changed)

    def on_visibility_changed(self, state):
        self.setVisible(state)

    def render_image(self):
        t_start = self.timeline.get_current_t_start()
        t_end = self.timeline.get_current_t_end()

        self.t_start = t_start
        self.t_end = t_end

        filter_window = self.control.sp_filter.value()

        data, ms = self.dataset.get_data_range(t_start, t_end, filter_window=filter_window)

        self.last_data = data, ms

        qimage = QtGui.QImage(self.size(), QtGui.QImage.Format.Format_ARGB32_Premultiplied)
        qimage.fill(QtCore.Qt.GlobalColor.transparent)
        qp = QtGui.QPainter(qimage)

        pen = QtGui.QPen()

        qp.setPen(pen)
        qp.begin(qimage)
        qp.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        rect = QRect(self.rect().x(),
                     self.rect().y(),
                     np.clip(self.rect().width(), None, self.timeline.duration / self.timeline.scale),
                     self.rect().height())

        qp.fillRect(rect, QtGui.QColor(12, 12, 12))
        self.update()
        return qimage, qp, data, t_start, t_end, ms

    def get_current_value_and_pos(self):
        """
        Interpolates the drawn spline to visualize the current location of the value in regards to the timeline location
        :return:
        """
        if self.last_data is not None:
            ms = self.timeline.curr_movie_time

            data, times = self.last_data
            indices = np.where(ms < times)[0]

            if len(indices.tolist()) == 0:
                return None, None

            # Find the current segment of the Visualized Line where the time scrubber is within
            idx0 = indices[0] - 1
            idx1 = idx0 + 1

            if idx1 >= data.shape[0] or idx0 < 0:
                return None, None

            x0 = float(((times[idx0] - self.t_start)) / self.timeline.scale)
            y0 = float(self.height() - (data[idx0] * self.height()))

            x1 = float(((times[idx1] - self.t_start)) / self.timeline.scale)
            y1 = float(self.height() - (data[idx1] * self.height()))

            # Draw a painter path and interpolate the accurate location
            p = QPainterPath(QPointF(x0, y0))
            p.lineTo(QPointF(x1, y1))

            f = (ms - times[idx0])/(times[idx1] - times[idx0])
            p = p.pointAtPercent(f)
            val = (data[idx0] + (f * (data[idx1] - data[idx0]))) * self.dataset.d_max
            return p, val
        else:
            return None, None



class TimelineLinePlot(TimelineVisualization):
    def __init__(self, parent, timeline, control, dataset:TimelineDataset = None, height=45):
        super(TimelineLinePlot, self).__init__(parent, timeline, control, height)
        self.dataset = dataset
        self.image = None
        self.last_values = None
        self.line_color = QColor(98, 161, 169)
        self.timeline.main_window.onTimeStep.connect(self.on_time_changed)

    def on_height_changed(self, height):
        super(TimelineLinePlot, self).on_height_changed(height)
        self.setFixedHeight(height)

    def render_image(self):
        qimage, qp, data, t_start, t_end, ms = super(TimelineLinePlot, self).render_image()

        pen = QtGui.QPen()
        pen.setColor(self.dataset.vis_color)
        pen.setWidthF(3.0)

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
            self.interpol_spline = path


        pen = QtGui.QPen()
        pen.setColor(QColor(37, 37, 37))

        qp.setPen(pen)
        r = self.rect()
        r.adjust(1, 1, -1, -1)
        qp.drawRect(r)
        qp.end()
        self.image = qimage


    def on_time_changed(self):
        self.update()

    def paintEvent(self, QPaintEvent):
        if not hasattr(self, "timeline"):
            #TODO Not really clear why I need this, since timeline is an attribute of type:TimelineBar
            return

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

        point, val = self.get_current_value_and_pos()

        if point is not None:
            pen = QtGui.QPen()
            pen.setColor(self.dataset.vis_color)
            pen.setWidthF(3.0)

            qp.setPen(pen)

            d = self.hover_dot_size
            hd = self.hover_dot_size / 2
            qp.drawEllipse(QRectF(float(point.x() - hd), float(point.y() - hd), d, d))
            p = QPointF(d,0.0) + point
            qp.drawText(p, self.dataset.name + ": {v}".format(v=round(val, 2)))

            c = QColor(self.dataset.vis_color.rgb())
            c.setAlphaF(0.5)
            pen = QtGui.QPen()
            pen.setColor(c)
            pen.setWidthF(1.5)

            qp.setPen(pen)
            qp.drawLine(QPointF(0, point.y()), QPointF(self.width(), point.y()))

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