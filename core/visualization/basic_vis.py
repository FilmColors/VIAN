# import pyqtgraph as pg
import time
import os
from PyQt5.QtWidgets import  QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QCheckBox, QMenu
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import numpy as np
from core.data.computation import get_heatmap_value
from core.gui.ewidgetbase import EGraphicsView
from core.analysis.colorimetry.hilbert import create_hilbert_transform
from core.gui.tools import ExportImageDialog

class IVIANVisualization():
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


class VIANPlot(QGraphicsView, IVIANVisualization):
    def __init__(self, parent, background=QColor(30, 30, 30), aspect = Qt.KeepAspectRatio):
        super(VIANPlot, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))

        self.aspect = aspect
        self.curr_zoom_scale = 1.0
        self.x_scale = 1.0
        self.y_scale = 1.0
        self.base_line = 1000
        self.ctrl_is_pressed = False

        # For Grid
        self.max_x = 1.0
        self.max_y = 1.0

        self.font_size = 10
        self.raw_data = []
        self.grid = []

    def get_ceil(self, tmax):
        for i in range(100):
            if tmax <= 10 ** i:
                step = round(10 ** (i - 1), 1)
                ceil = np.ceil(tmax / step) * step
                return ceil, step

        return 1.0, 0.1


    def plot_grid(self, col = QColor(255,255,255,128)):
        for itm in self.grid:
            self.scene().removeItem(itm)
        self.grid = []

        x_ceil, x_step = self.get_ceil(self.max_x)
        y_ceil, y_step = self.get_ceil(self.max_y)

        pen = QPen()
        pen.setWidthF(0.1)
        pen.setColor(col)
        font = QFont()
        font.setPointSize(self.font_size)
        for i in range(11):
            x_true = x_step * i
            # x_view = self.base_line / 10 * x_true
            x_view = self.base_line / 10 * i

            y_true = y_step * i
            y_view = self.base_line - self.base_line / 10 * i

            self.grid.append(self.scene().addLine(0, y_view, self.base_line, y_view, pen))
            self.grid.append(self.scene().addLine(x_view, 0, x_view, self.base_line, pen))
            x_lbl = self.scene().addText(str(x_true), font)
            x_lbl.setPos(x_view - x_lbl.boundingRect().width() / 2, self.base_line + x_lbl.boundingRect().height())
            x_lbl.setDefaultTextColor(col)

            y_lbl = self.scene().addText(str(y_true), font)
            y_lbl.setPos(-y_lbl.boundingRect().width(), y_view - y_lbl.boundingRect().height() / 2)
            y_lbl.setDefaultTextColor(col)
            self.grid.append(x_lbl)
            self.grid.append(y_lbl)
            self.grid.append(self.scene().addText(str(x_true)))

    def clear_view(self):
        self.scene().clear()

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-10, -10, 20, 20)
        self.scene().setSceneRect(rect)
        self.fitInView(rect,  self.aspect)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        elif event.key() == Qt.Key_F:
            self.frame_default()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            if event.angleDelta().y() > 0.0 and self.curr_zoom_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_zoom_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_zoom_scale > 0.001:
                self.curr_zoom_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(QGraphicsView, self).wheelEvent(event)

    def get_raw_data(self):
        return self.raw_data

    def apply_raw_data(self, raw_data):
        for i, r in enumerate(raw_data):
            if i == 0:
                self.add_grid(r.curr_grid)
            self.add_point(r.x, r.y, r.z, r.col)

    def render_to_image(self, background: QColor, size: QSize):
        """
        Renders the scene content to an image, alternatively if return iamge is set to True, 
        the QImage is returned and not stored to disc
        :param return_image: 
        :return: 
        """

        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        image = QImage(size, QImage.Format_ARGB32)
        image.fill(background)

        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene().render(painter)
        painter.end()

        return image


class VIANTextGraphicsItemSignals(QObject):
    onClicked = pyqtSignal(object)
    onEnter = pyqtSignal(object)
    onLeave = pyqtSignal(object)


class VIANTextGraphicsItem(QGraphicsTextItem):
    def __init__(self, text, font, meta = None):
        super(VIANTextGraphicsItem, self).__init__(text)
        self.setFont(font)
        self.signals = VIANTextGraphicsItemSignals()
        self.meta = meta

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(VIANTextGraphicsItem, self).mousePressEvent(event)
        self.signals.onClicked.emit(self)

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        super(VIANTextGraphicsItem, self).hoverEnterEvent(event)
        self.signals.onEnter.emit(self)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        super(VIANTextGraphicsItem, self).hoverLeaveEvent(event)
        self.signals.onLeave.emit(self)


class MatrixPlot(EGraphicsView, IVIANVisualization):
    itemClicked = pyqtSignal(object)

    def __init__(self, parent, max=1.0, allow_hover = True):
        super(MatrixPlot, self).__init__(parent)
        self.dot_size = 1.0
        self.total_width = 1000
        self.max = max
        self.items = []
        self.setScene(QGraphicsScene(self))
        self.use_gray = True
        self.hover_frame = None
        self.allow_hover = allow_hover

        self.matrix = None

    def plot_data(self, matrix, names = None, meta = None, draw_image = False):
        self.scene().clear()
        self.items = []
        self.matrix = matrix
        p = QPen()
        f = QFont()
        f.setPointSize(20)
        self.dot_size = self.total_width / matrix.shape[0]

        if not draw_image:
            for x in range(matrix.shape[0]):
                for y in range(matrix.shape[1]):
                    col = get_heatmap_value(matrix[x, y], self.max, gray=self.use_gray)
                    itm = self.scene().addRect(x * self.dot_size, y * self.dot_size, self.dot_size, self.dot_size, p, QBrush(QColor(col[0], col[1], col[2])))
                    if names is not None:
                        itm.setToolTip(names[x] + "-" + names[y] + ":" + str(matrix[x,y]))
                    self.items.append(itm)
        else:
            painter = QPainter()
            img = QImage(QSize(1000,1000), QImage.Format_RGB888)
            img.fill(QColor(0,0,0))
            painter.begin(img)
            for x in range(matrix.shape[0]):
                for y in range(matrix.shape[1]):
                    col = get_heatmap_value(matrix[x, y], self.max, gray=self.use_gray)
                    painter.fillRect(QRectF(x * self.dot_size, y * self.dot_size, self.dot_size, self.dot_size), QBrush(QColor(col[0], col[1], col[2])))
            painter.end()
            self.scene().addPixmap(QPixmap().fromImage(img))
        if names is not None:
            for x in range(matrix.shape[0]):
                lbl = VIANTextGraphicsItem(names[x], f)
                self.scene().addItem(lbl)
                # lbl = self.scene().addText(names[x], f)
                lbl.setPos(x * self.dot_size + (self.dot_size / 2), -50)
                lbl.setRotation(-45.0)
                lbl.setDefaultTextColor(QColor(230, 230, 230))
                lbl.signals.onClicked.connect(self.on_text_clicked)

                if meta is not None:
                    lbl.meta = meta[x]
                if self.allow_hover:
                    lbl.signals.onEnter.connect(self.on_enter_text)
                    lbl.signals.onLeave.connect(self.on_leave_text)


                lbl = VIANTextGraphicsItem(names[x], f)
                self.scene().addItem(lbl)
                # lbl = self.scene().addText(names[x], f)
                lbl.setPos(-lbl.sceneBoundingRect().width() - 10, x * self.dot_size)
                lbl.setDefaultTextColor(QColor(230,230,230))
                lbl.signals.onClicked.connect(self.on_text_clicked)

                if meta is not None:
                    lbl.meta = meta[x]
                if self.allow_hover:
                    lbl.signals.onEnter.connect(self.on_enter_text)
                    lbl.signals.onLeave.connect(self.on_leave_text)

        self.add_value_bar(0, matrix.shape[0] * self.dot_size + 50, matrix.shape[0] * self.dot_size)

    def add_value_bar(self, x, y, width, height = 50, n_steps = 50):
        step = self.max / n_steps
        width_size = width / n_steps
        p = QPen()
        for i in range(n_steps):
            col = get_heatmap_value(i * step, self.max,gray=self.use_gray)
            itm = self.scene().addRect(i * width_size, y, width_size, height, p, QBrush(QColor(col[0], col[1], col[2])))

    @pyqtSlot(object)
    def on_text_clicked(self, object):
        pass

    @pyqtSlot(object)
    def on_enter_text(self, object):
        pass

    @pyqtSlot(object)
    def on_leave_text(self, object):
        pass


class HistogramVis(EGraphicsView, IVIANVisualization):
    def __init__(self, parent, cache_file = "data/hilbert.npz"):
        super(HistogramVis, self).__init__(parent)
        # self.view = EGraphicsView(self, auto_frame=False)
        self.setLayout(QVBoxLayout(self))
        # self.layout().addWidget(self.view)
        self.items = []

        # self.plt = pg.PlotItem()
        # self.view.addItem(self.plt)

        self.qimage = None
        if not os.path.isfile(cache_file):
            self.table, self.colors = create_hilbert_transform(16)
            np.savez(cache_file, table=self.table, colors=self.colors)
        else:
            d = np.load(cache_file)
            print(d.keys())
            self.table = (d['table'][0], d['table'][1], d['table'][2])
            self.colors = d['colors']

        self.raw_data = None

        self.plot_floor = True
        self.plot_zeros = False
        self.normalize = True
        self.draw_grid = False
        self.plot_log = True

    def plot_color_histogram(self, hist_cube):
        hist_lin = hist_cube[self.table]
        if not self.plot_zeros:
            nonz_idx =  np.nonzero(hist_lin)
            hist_lin = np.array(hist_lin)[nonz_idx]
            colors = np.array(self.colors)[nonz_idx[0]]
        else:
            colors = np.array(self.colors)
        if hist_lin.shape[0] == 0:
            return
        if self.plot_log:
            hist_lin = np.log10(hist_lin.astype(np.float32) + 1.0)
        if self.normalize:
            hist_lin = (hist_lin / np.amax(hist_lin) * 4096).astype(np.float32)

        self.raw_data = dict(hist=hist_lin, colors = colors)
        self.plot(hist_lin, colors)

    def redraw(self):
        if self.raw_data is not None:
            self.plot(self.raw_data['hist'], self.raw_data['colors'])

    def plot(self, ys, colors, width = 1):
        for i in self.items:
            self.view.removeItem(i)
        self.items.clear()
        self.scene().clear()
        img = QImage(QSize(4096,4096), QImage.Format_RGBA8888)
        img.fill(QColor(27,27,27,255))

        p = QPainter()
        p.begin(img)
        pen = QPen()
        pen.setColor(QColor(255,255,255, 255))
        pen.setWidth(5)
        p.setPen(pen)
        width = 4096 / ys.shape[0]
        if self.draw_grid:
            step = 4096 / 5
            for i in range(5):
                p.drawLine(0, i * step, 4096, i * step)

        for i in range(ys.shape[0]):
            p.fillRect(i * width, 4096 - int(ys[i]), width, int(ys[i]), QBrush(QColor(colors[i][0],colors[i][1],colors[i][2])))
            if self.plot_floor:
                p.fillRect(i * width, 4050, width, 46,
                           QBrush(QColor(colors[i][0], colors[i][1], colors[i][2])))

        p.end()
        self.qimage = img
        # self.scene().clear()
        img = self.scene().addPixmap(QPixmap().fromImage(self.qimage))
        self.fitInView(self.scene().itemsBoundingRect())

    def get_param_widget(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        plot_floor = QCheckBox("Plot Floor")
        plot_zeros = QCheckBox("Plot Zeros")
        normalize = QCheckBox("Normalize")
        draw_grid = QCheckBox("Draw Grid")
        plot_log = QCheckBox("Plot Log")

        plot_floor.setChecked(self.plot_floor)
        plot_zeros.setChecked(self.plot_zeros)
        normalize.setChecked(self.normalize)
        draw_grid.setChecked(self.draw_grid)
        plot_log.setChecked(self.plot_log)

        plot_floor.stateChanged.connect(self.set_plot_floor)
        plot_zeros.stateChanged.connect(self.set_plot_zeros)
        normalize.stateChanged.connect(self.set_normalize)
        draw_grid.stateChanged.connect(self.set_draw_grid)
        plot_log.stateChanged.connect(self.set_plot_log)

        w.layout().addWidget(plot_floor)
        w.layout().addWidget(plot_zeros)
        w.layout().addWidget(normalize)
        w.layout().addWidget(draw_grid)
        w.layout().addWidget(plot_log)

        return w

    def set_plot_floor(self, state):
        self.plot_floor = state
        self.redraw()

    def set_plot_zeros(self, state):
        self.plot_zeros = state
        self.redraw()

    def set_normalize(self, state):
        self.normalize = state
        self.redraw()

    def set_draw_grid(self, state):
        self.draw_grid = state
        self.redraw()

    def set_plot_log(self, state):
        self.plot_log = state
        self.redraw()


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
