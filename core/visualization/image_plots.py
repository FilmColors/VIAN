import numpy as np
import cv2
import typing
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QImage, QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QPen, QFont, QPainter
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QPoint, Qt, QRectF, pyqtSlot, pyqtSignal, QEvent, QSize, QPointF

from core.data.computation import *

SOURCE_FOREGROUND = 0
SOURCE_BACKGROUND = 1
SOURCE_COMPLETE = 2

class ImagePlot(QGraphicsView):
    def __init__(self, parent, range_x = None, range_y = None, create_controls = False, title = ""):
        super(ImagePlot, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        if range_x is None:
            range_x = [-128, 128]
        if range_y is None:
            range_y = [-128, 128]

        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.pos_scale = 1.0
        self.img_scale = 1.0

        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 100
        self.images = []
        self.range_x = range_x
        self.range_y = range_y
        self.font_size = 4
        self.title = title


        self.left_button_pressed = False
        self.last_mouse_pos = QPoint()

        self.luminances = []

        self.n_grid = 12
        self.controls_itm = None

        self.add_grid()
        self.create_title()

        # self.tipp_label = self.scene().addText("Use F to Focus the complete Plot\nUse Ctrl/Cmd and Wheel to Zoom")
        # self.tipp_label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        # self.tipp_label.setDefaultTextColor(QColor(10,255,10))
        # self.tipp_label.setPos(self.mapToScene(QPoint(0, self.height() - 50)))

        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        # self.fitInView(   -range_x[0] * self.magnification / 12,
        #                   -range_y[0] * self.magnification/ 12,
        #                  (range_x[1] - range_x[0]) * self.magnification/ 12,
        #                  (range_y[1] - range_y[0]) * self.magnification/ 12, Qt.KeepAspectRatio)

    def add_image(self, x, y, img, convert = True, luminance = None):
        pass

    def sort_images(self):
        self.luminances = sorted(self.luminances, key=lambda x: x[0])

    def add_grid(self):
        pass

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def add_controls(self, ctrl):
        self.controls_itm = self.scene().addWidget(ctrl)
        self.controls_itm.show()

    def set_image_scale(self, scale):
        for img in self.images:
            img.setScale(img.scale() + scale)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()

        elif event.key() == Qt.Key_F:
            self.frame_default()

        elif event.key() == Qt.Key_Plus:
            self.set_image_scale(0.1)
        elif event.key() == Qt.Key_Minus:
            self.set_image_scale(-0.1)

        else:


            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.ctrl_is_pressed:
            delta = event.pos() - self.last_mouse_pos
            self.set_magnification(delta.x(),delta.y())
            self.last_mouse_pos = event.pos()

    def set_magnification(self, x, y):
        pass

    def scale_pos(self, scale_inc):
        for img in self.images:
            if isinstance(img, VIANPixmapGraphicsItem):
                img.scale_pos(self.pos_scale + scale_inc)
        self.pos_scale += scale_inc

    def wheelEvent(self, event: QWheelEvent):
        # bbox = self.sceneRect()
        # self.controls_itm.setPos(bbox.x(), bbox.y())

        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            self.curr_scale = round(self.img_width / np.clip((viewport_size.x()), 0.001, None), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

            for itm in self.images:
                itm.setScale(self.img_scale * (1.0 - self.curr_scale))

        else:
            super(QGraphicsView, self).wheelEvent(event)

        # self.tipp_label.setPos(self.mapToScene(QPoint(30, self.height() - 50)))

    def clear_view(self):
        self.scene().clear()
        self.images.clear()
        self.luminances.clear()

    def frame_default(self):
        # self.tipp_label.setPos(QPointF())
        self.setSceneRect(self.scene().itemsBoundingRect())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

        # self.tipp_label.setPos(self.mapToScene(QPoint(30, self.height() - 50)))

    def export(self, return_image = False, width = 4096, height = 4096):
        """
        Renders the scene content to an image, alternatively if return iamge is set to True, 
        the QImage is returned and not stored to disc
        :param return_image: 
        :return: 
        """

        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        t_size = self.sceneRect().size().toSize()
        image = QImage(QSize(width, height), QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        painter = QPainter()
        painter.begin(image)
        self.scene().render(painter)
        painter.end()

        if return_image:
            return image
        else:
            path = QFileDialog.getSaveFileName()[0]
            image.save(path)

    @pyqtSlot(int)
    def on_high_cut(self, value):
        for tpl in self.luminances:
            if tpl[0] > value:
                tpl[1].hide()
            else:
                tpl[1].show()


    @pyqtSlot(int)
    def on_low_cut(self, value):
        for tpl in self.luminances:
            if tpl[0] < value:
                tpl[1].hide()
            else:
                tpl[1].show()


class VIANPixmapGraphicsItem(QGraphicsPixmapItem):
    onItemSelection = pyqtSignal(object)

    def __init__(self, pixmap, hover_text = None):
        super(VIANPixmapGraphicsItem, self).__init__(pixmap)
        if hover_text != None:
            self.setToolTip(hover_text)
        self.abs_pos = None
        self.pos_scale = 1.0

    def scale_pos(self, scale):
        self.pos_scale = scale
        super(VIANPixmapGraphicsItem, self).setPos(self.abs_pos * self.pos_scale)

    def setPos(self, x, y):
        pos = QPointF(x, y)
        super(VIANPixmapGraphicsItem, self).setPos(pos)
        self.abs_pos = pos

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(VIANPixmapGraphicsItem, self).mousePressEvent(event)
        # self.onItemSelection.emit(self)


class ImagePlotCircular(ImagePlot):
    def __init__(self, parent, range_x = None, range_y = None):
        super(ImagePlotCircular, self).__init__(parent, range_x, range_y)

    def add_image(self, x, y, img, convert = True, luminance = None, to_float = False):
        try:
            if convert:
                # itm = QGraphicsPixmapItem(numpy_to_pixmap(img))
                itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img))
            else:
                # itm = QGraphicsPixmapItem(numpy_to_pixmap(img, cvt=None,  with_alpha = True))
                itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=None, with_alpha=True))
            self.scene().addItem(itm)

            if to_float:
                itm.setPos(np.nan_to_num((x -128) * self.magnification),np.nan_to_num((y -128) * self.magnification))
            else:
                itm.setPos(np.nan_to_num(x * self.magnification), np.nan_to_num(y * self.magnification))

            itm.setScale(self.img_scale)

            self.images.append(itm)

            if luminance is not None:
                self.luminances.append([luminance, itm])

            itm.show()

        except Exception as e:
            print(e)

    def add_grid(self):
        pen = QPen()
        pen.setWidth(10)
        pen.setColor(QColor(200,200,200,150))

        font = QFont()
        font.setPointSize(self.font_size * self.magnification)

        for i in range(7):
            self.circle0 = self.scene().addEllipse(QRectF(0,
                                           0,
                                                          (255/6 * i) * self.magnification,
                                                          (255 / 6 * i) * self.magnification),
                                    pen)

            q = -(128/6 * i)
            self.circle0.setPos(q * self.magnification, q * self.magnification)
            # text = self.scene().addText(str(round(i *(128/6),0)), font)
            # text.setPos(0,(-i *(128/6) * self.magnification)- self.font_size *self.magnification)
            # text.setDefaultTextColor(QColor(200,200,200,200))

        for i in range(self.n_grid):
            x = 128 * self.magnification * np.cos(i * (2 * np.pi / self.n_grid))
            y = 128 * self.magnification * np.sin(i * (2 * np.pi / self.n_grid))
            self.scene().addLine(0, 0 , x, y, pen)
        self.circle0.show()

    def set_range_scale(self, value):
        self.pos_scale = value / 100
        for img in self.images:
            if isinstance(img, VIANPixmapGraphicsItem):
                img.scale_pos(self.pos_scale)

    def set_image_scale(self,value):
        for img in self.images:
            img.setScale(value / 100)
        self.img_scale = value / 100

    def get_param_widget(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        hl1 = QHBoxLayout(w)
        hl1.addWidget(QLabel("Range Scale:", w))
        hl2 = QHBoxLayout(w)
        hl2.addWidget(QLabel("Image Scale:", w))

        slider_xscale = QSlider(Qt.Horizontal, w)
        slider_xscale.setRange(1, 1000)
        slider_xscale.setValue(100)
        slider_xscale.valueChanged.connect(self.set_range_scale)
        slider_yscale = QSlider(Qt.Horizontal, w)
        slider_yscale.setRange(1, 1000)
        slider_xscale.setValue(100)
        slider_yscale.valueChanged.connect(self.set_image_scale)

        hl1.addWidget(slider_xscale)
        hl2.addWidget(slider_yscale)

        w.layout().addItem(hl1)
        w.layout().addItem(hl2)

        return w


class ImagePlotPlane(ImagePlot):
    def __init__(self, parent, range_x = None, range_y = None, title=""):
        super(ImagePlotPlane, self).__init__(parent, range_x, range_y, title=title)

    def add_image(self, x, y, img, convert = True):
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img))
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=None, with_alpha=True))
        self.scene().addItem(itm)

        itm.setPos(np.nan_to_num(x * self.magnification),np.nan_to_num(self.range_y[1] * self.magnification - y * self.magnification))
        self.images.append(itm)

        self.luminances.append([y, itm])

        itm.show()

    def add_grid(self):
        pen = QPen()
        pen.setWidth(10)
        pen.setColor(QColor(200, 200, 200, 150))

        font = QFont()
        font.setPointSize(self.font_size * self.magnification)

        x0 = self.range_x[0] * self.magnification
        x1 = self.range_x[1] * self.magnification
        y0 = self.range_y[0] * self.magnification
        y1 = self.range_y[1] * self.magnification
        for x in range(self.range_x[0] * self.magnification, self.range_x[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                self.scene().addLine(x, y0, x, y1, pen)

                text = self.scene().addText(str(round((x / self.magnification), 0)), font)
                text.setPos(x, self.range_y[1] * self.magnification)
                text.setDefaultTextColor(QColor(200, 200, 200, 200))


        for x in range(self.range_y[0] * self.magnification, self.range_y[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                self.scene().addLine(x0, x, x1, x, pen)

                text = self.scene().addText(str(round(((self.range_y[1] * self.magnification - x) / self.magnification), 0)), font)
                text.setPos(self.range_x[0] * self.magnification, x)
                text.setDefaultTextColor(QColor(200, 200, 200, 200))


class ImagePlotControls(QWidget):
    onLowCutChange = pyqtSignal(int)
    onHighCutChange = pyqtSignal(int)
    onSourceChanged = pyqtSignal(int)
    onChannelChanged = pyqtSignal(int)
    onNthImageChanged = pyqtSignal(int)

    def __init__(self, parent):
        super(ImagePlotControls, self).__init__(parent)
        self.view = parent
        self.low_cut = -128
        self.high_cut = 128

        self.setLayout(QVBoxLayout(self))

        self.lay_hcut = QHBoxLayout(self)
        self.sl_hcut = QSlider(Qt.Horizontal, self)
        self.sl_hcut.setRange(0, 100)
        self.sl_hcut.setValue(100)
        self.sl_hcut.valueChanged.connect(self.on_high_cut)
        self.lbl_hcut = QLabel("High Cut: 100", self)
        self.lbl_hcut.setStyleSheet("QLabel {color: rgb(255,255,255)}")
        self.lay_hcut.addWidget(self.sl_hcut)
        self.lay_hcut.addWidget(self.lbl_hcut)

        self.lay_lcut = QHBoxLayout(self)
        self.sl_lcut = QSlider(Qt.Horizontal, self)
        self.sl_lcut.setRange(0, 100)
        self.sl_hcut.setValue(0)
        self.sl_lcut.valueChanged.connect(self.on_low_cut)
        self.lbl_lcut = QLabel("Low Cut: 0", self)
        self.lbl_lcut.setStyleSheet("QLabel {color: rgb(255,255,255)}")
        self.lay_lcut.addWidget(self.sl_lcut)
        self.lay_lcut.addWidget(self.lbl_lcut)

        self.layout().addItem(self.lay_lcut)
        self.layout().addItem(self.lay_hcut)

        self.layout().addWidget(QLabel("Color Source"))
        self.cb_source = QComboBox(self)
        self.cb_source.addItem("Foreground")
        self.cb_source.addItem("Background")
        self.cb_source.addItem("Complete")
        self.layout().addWidget(self.cb_source)

        self.ctrl_color_dt = QWidget(self)
        self.ctrl_color_dt.setLayout(QVBoxLayout(self.ctrl_color_dt))
        self.ctrl_color_dt.layout().addWidget(QLabel("Color dT Vis"))
        self.ctrl_color_dt.layout().addWidget(QLabel("Channel"))
        self.cb_channel = QComboBox(self.ctrl_color_dt)
        self.cb_channel.addItems(["Luminance", "a-Channel", "b-Channel"])

        self.ctrl_color_dt.layout().addWidget(self.cb_channel)
        self.layout().addWidget(self.ctrl_color_dt)
        self.ctrl_color_dt.layout().addWidget(QLabel("Image Density"))
        self.sl_image_density = QSlider(Qt.Horizontal, self.ctrl_color_dt)
        self.sl_image_density.setRange(1, 300)
        self.sl_image_density.setValue(30)

        self.cb_channel.currentIndexChanged.connect(self.onChannelChanged)
        self.sl_image_density.valueChanged.connect(self.onNthImageChanged)
        self.cb_source.currentIndexChanged.connect(self.onSourceChanged)

        self.ctrl_color_dt.layout().addWidget(self.sl_image_density)

        self.cb_channel.view().installEventFilter(self)
        self.cb_source.view().installEventFilter(self)

        self.resize(200, 100)

    @pyqtSlot(int)
    def on_plot_changed(self, index):
        if index == 2:
            self.ctrl_color_dt.show()
        else:
            self.ctrl_color_dt.hide()

    def on_low_cut(self):
        value = self.sl_lcut.value()
        self.lbl_lcut.setText("L-Low Cut:" + str(value))
        self.onLowCutChange.emit(value)

    def on_high_cut(self):
        value = self.sl_hcut.value()
        self.lbl_hcut.setText("L-Low Cut:" + str(value))
        self.onHighCutChange.emit(value)

    def eventFilter(self, a0: 'QObject', a1: 'QEvent'):
        if a1.type() == QEvent.HoverLeave:
            return True

        return super(ImagePlotControls, self).eventFilter(a0, a1)


class ImagePlotTime(ImagePlot):
    def __init__(self, parent, range_x = None, range_y = None, title=""):
        self.x_scale = 0.001
        self.y_scale = 200 #50 default
        self.base_line = 1000
        self.x_end = 0
        self.lines = []

        self.pixel_size_x = 1500
        self.pixel_size_y = 800

        self.border = 10000

        self.labels = []

        self.values = []
        super(ImagePlotTime, self).__init__(parent, range_x, range_y, title=title)
        self.font_size = 60


    def create_scene(self, x_max, y_max, pixel_size_x = 500, pixel_size_y = 500):
        self.pixel_size_x = pixel_size_x
        self.pixel_size_y = pixel_size_y

        self.x_scale = self.pixel_size_x / x_max
        self.y_scale = self.pixel_size_y / y_max
        self.base_line = y_max

        self.scene().setSceneRect(0, 0, x_max * self.x_scale, y_max * self.y_scale)


    def add_image(self, x, y, img, convert=True):
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img),
                                         hover_text=str(round(x, 2))+ "\t" + str(round(y, 2)))
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=None, with_alpha=True),
                                         hover_text=str(round(x, 2))+ "\t" + str(round(y, 2)))
        self.scene().addItem(itm)

        itm.setPos(np.nan_to_num(x * self.x_scale), np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale) - itm.boundingRect().height()))

        self.images.append(itm)

        if self.x_end < x * self.x_scale:
            self.x_end = x * self.x_scale

        self.luminances.append([np.nan_to_num(y), itm])
        self.values.append([x, np.nan_to_num(y)])
        itm.show()

    def clear_view(self):
        super(ImagePlotTime, self).clear_view()
        self.x_end = 0
        self.values = []
        self.lines = []

    def add_grid(self, set_scene_rect = True):
        pen = QPen()
        pen.setWidth(10)
        pen.setColor(QColor(200, 200, 200, 150))

        font = QFont()
        font.setPointSize(self.font_size)
        self.lines.append(self.scene().addLine(0, self.base_line * self.y_scale, self.x_end, self.base_line * self.y_scale , pen))
        self.lines.append(self.scene().addLine(0, self.base_line * self.y_scale, 0, 0, pen))
        if set_scene_rect:
            self.setSceneRect(self.scene().itemsBoundingRect())

    def update_grid(self):
        for l in self.lines:
            self.scene().removeItem(l)
        self.lines = []
        self.setSceneRect(self.scene().itemsBoundingRect())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        self.add_grid(False)


    def set_x_scale(self, value):
        self.x_scale = value
        self.x_scale = self.pixel_size_x / np.clip((len(self.images) * ((500 - value) / 100)), 0.00001, None)
        self.update_position()

    def set_y_scale(self, value):
        self.y_scale = value
        self.y_scale = self.pixel_size_y / np.clip((100 * (value / 100)), 0.00001, None)
        self.update_position()

    def update_position(self):
        for idx, v in enumerate(self.values):
            itm = self.images[idx]
            x = v[0]
            y = v[1]
            itm.setPos(np.nan_to_num(x * self.x_scale), np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale) - itm.boundingRect().height()))
        self.update_grid()

    def get_param_widget(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        hl1 = QHBoxLayout(w)
        hl1.addWidget(QLabel("X-Scale:", w))
        hl2 = QHBoxLayout(w)
        hl2.addWidget(QLabel("Y-Scale:", w))

        slider_xscale = QSlider(Qt.Horizontal, w)
        slider_xscale.setRange(1, 500)
        slider_xscale.setValue(self.x_scale)
        slider_xscale.valueChanged.connect(self.set_x_scale)
        slider_yscale = QSlider(Qt.Horizontal, w)
        slider_yscale.setRange(1, 500)
        slider_xscale.setValue(self.y_scale)
        slider_yscale.valueChanged.connect(self.set_y_scale)

        hl1.addWidget(slider_xscale)
        hl2.addWidget(slider_yscale)

        w.layout().addItem(hl1)
        w.layout().addItem(hl2)

        return w
