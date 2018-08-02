# import pyqtgraph as pg
from PyQt5.QtWidgets import  QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import numpy as np

from core.gui.tools import ExportImageDialog

class IVIANVisualization():
    def set_heads_up_widget(self, widget):
        pass

    def get_heads_up_widget(self):
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


# class HistogramVis(QWidget, IVIANVisualization):
#     def __init__(self, parent):
#         super(HistogramVis, self).__init__(parent)
#         self.view = pg.PlotWidget()
#
#         self.setLayout(QVBoxLayout(self))
#         self.layout().addWidget(self.view)
#         self.items = []
#         # self.plt = pg.PlotItem()
#         # self.view.addItem(self.plt)
#
#
#     def plot(self, ys, colors, width = 1):
#         for i in self.items:
#             self.view.removeItem(i)
#         self.items.clear()
#
#         for i in range(len(ys)):
#             item = pg.BarGraphItem(x = [i], height=[ys[i]], width=[width],
#                                    brush=QColor(colors[i][0], colors[i][1], colors[i][2]),
#                                    pen=QPen(QColor(colors[i][0],colors[i][1],colors[i][2])))
#
#             self.view.addItem(item)
#             self.items.append(item)
#         self.view.updateMatrix()
#
#     def update_plot(self, ys):
#         for i, itm in enumerate(self.items):
#             itm.setOpts(height=[ys[i]])


class PaletteVis(QWidget, IVIANVisualization):
    def __init__(self, parent):
        super(PaletteVis, self).__init__(parent)
        self.view = QGraphicsView()
        self.view.setScene(QGraphicsScene())

        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(self.view)
        self.items = []
        # self.plt = pg.PlotItem()
        # self.view.addItem(self.plt)


    def plot(self, values, colors):
        size_factor = 1.0 / np.sum(values)
        cx = 0
        for i in self.items:
            self.view.scene().removeItem(i)
        self.items.clear()


        ax = 0.0
        bx = 0.0
        for i in range(len(values)):
            bx = ax + values[i] * size_factor
            itm = self.view.scene().addRect(QRectF(ax, 1.0, bx, 0.0),
                                            brush=QColor(colors[i][0],colors[i][1],colors[i][2]),
                                            pen=QPen(QColor(colors[i][0],colors[i][1],colors[i][2])))
            ax += values[i] * size_factor
            self.items.append(itm)

        self.view.fitInView(self.view.sceneRect())

