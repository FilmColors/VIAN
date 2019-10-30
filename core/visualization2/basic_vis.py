import time
import os
from PyQt5.QtWidgets import  QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QCheckBox, QMenu, QHBoxLayout, QLabel, QSlider
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtCore
import numpy as np
from core.data.computation import get_heatmap_value, ms_to_string, overlap_rect
from core.gui.ewidgetbase import EGraphicsView
from core.analysis.colorimetry.hilbert import create_hilbert_transform
from core.gui.tools import ExportImageDialog


SCEEN_EXTEND = 1000
ZOOM_INCREMENT = 2.0

class IVIANVisualization():
    def __init__(self, naming_fields = None):
        self.grid_color = QColor(20,20,20,150)
        self.font_size = 12
        self.naming_fields = dict()
        if naming_fields is not None:
            self.naming_fields = naming_fields.copy()
            self.naming_fields['plot_name'] = "vis"

    def get_param_widget(self):
        return QWidget()

    def set_time_indicator(self, x):
        pass

    def set_heads_up_widget(self, widget):
        pass

    def get_heads_up_widget(self):
        pass

    def get_raw_data(self):
        pass

    def apply_raw_data(self, raw_data):
        pass

    def export(self, main_window = None):
        if not isinstance(main_window, QWidget):
            main_window = None
        dialog = ExportImageDialog(main_window, self)
        dialog.show()

    def render_to_image(self, background: QColor, size: QSize):
        image = QImage(size, QImage.Format_RGBA8888)
        qp = QPainter()
        qp.begin(image)
        qp.fillRect(image.rect(), background)
        qp.end()
        return image


class VIANPlotGrid:
    def __init__(self, plot):
        self.plot = plot
        self.grid_color = QColor(100, 100, 100, 100)
        self.font_color = QColor(200, 200, 200, 200)
        self.font_size = 30
        self.items = []

    def clear_grid(self):
        for itm in self.items:
            self.plot.scene().removeItem(itm)
        self.items = []

    def draw_grid(self):
        pass


class PolarGrid(VIANPlotGrid):
    def __init__(self, plot):
        super(PolarGrid, self).__init__(plot)

    def draw_grid(self):
        self.clear_grid()

        pen = QPen()
        pen.setWidth(1)
        pen.setColor(self.grid_color)

        font = QFont()
        font.setPointSize(self.font_size)
        self.n_grid = 10


        polar_range = np.amax(list(self.plot.x_range + self.plot.y_range)) / self.plot.pos_scale_x

        sceen_scale = SCEEN_EXTEND / polar_range

        for i in range(7):
            self.circle0 = self.plot.scene().addEllipse(QRectF(0,
                                                          0,
                                                          (polar_range * 2 / 6 * i * sceen_scale),
                                                          (polar_range * 2 / 6 * i * sceen_scale)),
                                                   pen)
            q = -(polar_range / 6 * i * sceen_scale)
            self.circle0.setPos(q, q)
            self.items.append(self.circle0)

        for i in range(self.n_grid):
            x = sceen_scale * polar_range * np.cos(i * (2 * np.pi / self.n_grid))
            y = sceen_scale * polar_range * np.sin(i * (2 * np.pi / self.n_grid))
            l = self.plot.scene().addLine(0, 0, x, y, pen)
            self.items.append(l)

        lbla = self.plot.scene().addText("-B", font)
        lbla.setDefaultTextColor(self.font_color)
        lbla.setPos(- lbla.boundingRect().width() / 2, SCEEN_EXTEND)
        self.items.append(lbla)

        lblb = self.plot.scene().addText("A", font)
        a_pos_w = SCEEN_EXTEND + lblb.boundingRect().width() / 2
        lblb.setDefaultTextColor(self.font_color)
        lblb.setPos(a_pos_w, - lblb.boundingRect().height() / 2)
        self.items.append(lblb)

        self.lbl_max = self.plot.scene().addText(str(round(polar_range / self.plot.pos_scale_x, 0)), font)
        self.lbl_max.setDefaultTextColor(self.font_color)
        self.lbl_max.setPos(a_pos_w, + (self.lbl_max.boundingRect().height()) / 2)
        self.items.append(self.lbl_max)

        lbla = self.plot.scene().addText("B", font)
        lbla.setDefaultTextColor(self.font_color)
        lbla.setPos(- lbla.boundingRect().width() / 2, -SCEEN_EXTEND - lbla.boundingRect().height())
        self.items.append(lbla)

        lblb = self.plot.scene().addText("-A", font)
        lblb.setDefaultTextColor(self.font_color)
        lblb.setPos(-SCEEN_EXTEND  - 2 * lbla.boundingRect().width(), - lblb.boundingRect().height() / 2)
        self.items.append(lblb)

        self.circle0.show()


class CartesianGrid(VIANPlotGrid):
    def __init__(self, plot, x_axis_label = "x-Axis Label", y_axis_label="y-Axis Label"):
        super(CartesianGrid, self).__init__(plot)
        self.split_threshold = 10
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label


    def draw_grid(self):
        self.clear_grid()

        pen = QPen()
        pen.setWidth(1)
        pen.setColor(self.grid_color)

        font = QFont()
        font.setPointSize(self.font_size)

        sceen_x = self.plot.width()
        sceen_y = self.plot.height()

        screen_transform_x = sceen_x / (abs(self.plot.view_range_x[1]) - abs(self.plot.view_range_x[0]))
        screen_transform_y = sceen_y / (abs(self.plot.view_range_y[1]) - abs(self.plot.view_range_y[0]))

        step = 10

        n_grid_x = int(np.ceil((abs(self.plot.view_range_x[0]) + abs(self.plot.view_range_x[1]) / step)))
        n_grid_y = int(np.ceil((abs(self.plot.view_range_y[0]) + abs(self.plot.view_range_y[1]) / step)))

        for i in range(0, n_grid_x):
            self.items.append(self.plot.scene().addLine(i * step * screen_transform_x, 0, i * step * screen_transform_x, sceen_y, pen))

        for i in range(0, n_grid_y):
            self.items.append(self.plot.scene().addLine(0, sceen_y - i * step * screen_transform_y, sceen_x, sceen_y - i * step *screen_transform_y, pen))

        font.setPointSize(self.font_size)
        text = self.plot.scene().addText("Time", font)
        text.setPos(sceen_x / 2 - (text.boundingRect().width() / 2), sceen_y + text.boundingRect().height())
        text.setDefaultTextColor(self.font_color)
        self.items.append(text)

        text = self.plot.scene().addText("Saturation", font)
        text.setRotation(-90)
        text.setPos(-(text.boundingRect().height() * 3), sceen_y / 2 + text.boundingRect().width() / 2)
        text.setDefaultTextColor(self.font_color)
        self.items.append(text)

    def convert_format(self, val, format):
        if format == "value":
            return val
        if format == "ms":
            return ms_to_string(val)
        else:
            return val


class VIANPlotBase(QGraphicsView, IVIANVisualization):
    def __init__(self, parent):
        super(VIANPlotBase, self).__init__(parent)
        self.title = "Some Plot"
        self.grid = CartesianGrid(self)

        self.x_range = (0, 100)
        self.y_range = (0, 100)

        self.view_range_x = (0, 100)
        self.view_range_y = (0, 100)

        self.pos_scale_x = 1.0
        self.pos_scale_y = 1.0

        self.x_offset = 0.0
        self.y_offset = 0.0

        self.x_zoom_active = True
        self.y_zoom_active = False

        self.ctrl_is_pressed = False

        self.items = dict()

        self.setScene(QGraphicsScene(self))

        self.setMouseTracking(True)
        self.draw()

    def add_item(self, x, y, itm, item_id):
        if item_id not in self.items:
            self.items[item_id] = (x, y, itm)

    def draw(self):
        self.grid.draw_grid()

    def update_position(self):
        for k, v in self.items.items():
            print(v[0] * self.pos_scale_x, v[1] * self.pos_scale_y)
            v[2].setPos(v[0] * self.pos_scale_x, v[1] * self.pos_scale_y)

    def resizeEvent(self, event: QResizeEvent):
        super(VIANPlotBase, self).resizeEvent(event)
        rect = self.scene().itemsBoundingRect()
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.draw()

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-10, -10, 20, 20)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def zoom(self):
        self.grid.draw_grid()
        self.update_position()

    def map_to_data(self, p:QPointF):
        x = p.x() / self.scene().width() * (self.x_range[1] - self.x_range[0])
        y =  p.y() / self.scene().height() * (self.y_range[1] - self.y_range[0])
        return (x, y)

    def map_data_to_scene(self, x, y):
        x = x * (self.scene().width() / self.x_range[1])
        y = y * (self.scene().height() / self.y_range[1])
        return x, y

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        elif event.key() == Qt.Key_F:
            self.frame_default()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            if event.angleDelta().y() > 0.0 and self.pos_scale_x < 100:
                if self.x_zoom_active:
                    increment_x = ((self.pos_scale_x * self.x_range[1]) + ZOOM_INCREMENT) / self.x_range[1]
                    self.pos_scale_x = increment_x

                if self.y_zoom_active:
                    increment_y = ((self.pos_scale_y * self.y_range[1]) + ZOOM_INCREMENT) / self.y_range[1]
                    self.pos_scale_y = increment_y

            elif event.angleDelta().y() < 0.0 and self.pos_scale_x > 0.001:
                if self.x_zoom_active:
                    increment_x = ((self.pos_scale_x * self.x_range[1]) - ZOOM_INCREMENT) / self.x_range[1]
                    self.pos_scale_x = increment_x

                if self.y_zoom_active:
                    increment_y = ((self.pos_scale_y * self.y_range[1]) - ZOOM_INCREMENT) / self.y_range[1]
                    self.pos_scale_y = increment_y

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            if isinstance(self.grid, CartesianGrid):
                if self.x_zoom_active:
                    self.view_range_x = (self.x_range[0] * self.pos_scale_x, self.x_range[1] * self.pos_scale_x)
                if self.y_zoom_active:
                    self.view_range_y = (self.y_range[0] * self.pos_scale_x, self.y_range[1] * self.pos_scale_x)

            self.zoom()
            self.frame_default()

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(QGraphicsView, self).wheelEvent(event)


class DotPlot(VIANPlotBase):
    def add_dot(self, x, y, color=QColor(200,20,13)):
        x, y = self.map_data_to_scene(x, y)
        itm = self.scene().addEllipse(x, y, 2, 2, color)
        VIANPlotBase.add_item(self, x, y, itm, len(self.items.keys()))
