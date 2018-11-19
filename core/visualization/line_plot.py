import numpy as np
import cv2
import typing
from collections import namedtuple
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QImage, QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QPen, QFont, QPainter, QPainterPath, QTransform
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QPoint, Qt, QRectF, pyqtSlot, pyqtSignal, QEvent, QSize, QPointF, QObject

from core.data.computation import *
from core.visualization.basic_vis import VIANPlot
SOURCE_FOREGROUND = 0

LinePlotRawData = namedtuple("LinePlotRawData", ["x", "y", "z", "col", "mime_data", "curr_grid"])

class LinePlot(VIANPlot):
    def __init__(self, parent):
        super(LinePlot, self).__init__(parent, aspect=Qt.IgnoreAspectRatio)
        self.lines = []
        self.line_xs = []
        self.line_ys = []
        self.line_cols = []
        self.line_map = dict()

    def plot(self, xs, ys, col = QColor(255,255,255), mime_data = None, line_name = None):
        if isinstance(xs, list):
            xs = np.array(xs)
        if isinstance(ys, list):
            ys = np.array(ys)

        # Clear existing line
        if line_name is not None:
            if line_name in self.line_map:
                idx = self.line_map[line_name]
                self.line_xs.pop(idx)
                self.line_ys.pop(idx)
                self.line_cols.pop(idx)
            self.line_map[line_name] = len(self.line_xs)

        self.line_xs.append(xs)
        self.line_ys.append(ys)
        self.line_cols.append(col)
        # Normalize to View

        self.max_x = np.amax(self.line_xs)
        self.max_y = np.amax(self.line_ys)

        self.scene().clear()
        self.lines = []
        self.grid = []
        self.draw()
        self.plot_grid()
        # point.setZValue(z)
        # self.points.append(point)
        # self.raw_data.append(LinePlotRawData(x=x, y = y, z = z, col=col, mime_data=None, curr_grid=self.curr_grid))

    def draw(self):
        x_ceil, x_step = self.get_ceil(self.max_x)
        y_ceil, y_step = self.get_ceil(self.max_y)

        xs = np.multiply(np.divide(self.line_xs, x_ceil), 1000)
        ys = np.multiply(np.divide(self.line_ys, y_ceil), 1000)

        p = QPen()

        p.setWidth(0.1)

        for j in range(xs.shape[0]):
            p.setColor(self.line_cols[j])
            path = None

            for i in range(xs.shape[1]):
                x = xs[j][i]
                y = 1000 - ys[j][i]
                if i == 0:
                    path = QPainterPath(QPointF(x, y))
                else:
                    path.lineTo(QPointF(x, y))

            if path is not None:
                path = self.scene().addPath(path, p)
                self.lines.append(path)

        p.setColor(QColor(255,255,255,200))
        n_legend = len(list(self.line_map.keys()))
        legend_box = self.scene().addRect(QRectF(1050, 50, 200, 30 * n_legend), p)

        font = QFont()
        font.setPointSize(10)
        c = 1
        for name in self.line_map.keys():
            y = 50 + ((c * 30) - 15)
            p.setColor(self.line_cols[self.line_map[name]])
            lbl = self.scene().addText(name, font)
            lbl.setPos(1055, y - lbl.boundingRect().height() / 2)
            lbl.setDefaultTextColor(QColor(255,255,255,255))
            self.scene().addLine(1055 + lbl.boundingRect().width() + 5, y, 1245, y, p)
            c += 1

