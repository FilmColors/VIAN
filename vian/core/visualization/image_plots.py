import numpy as np
import cv2
import typing
from collections import namedtuple
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QImage, QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QPen, QFont, QPainter, QPainterPath, QTransform
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QPoint, Qt, QRectF, pyqtSlot, pyqtSignal, QEvent, QSize, QPointF, QObject

from core.data.computation import *
from core.visualization.basic_vis import IVIANVisualization
SOURCE_FOREGROUND = 0
SOURCE_BACKGROUND = 1
SOURCE_COMPLETE = 2

ImagePlotRawData = namedtuple("ImagePlotRawData", ["image", "x", "y", "z", "mime_data"])

ANGLE_DELTA_STEP = 120

class ImagePlot(QGraphicsView, IVIANVisualization):
    onImageClicked = pyqtSignal(object)

    def __init__(self, parent, range_x = None, range_y = None, create_controls = False, title = "", naming_fields = None):
        QGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "image_plot"

        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.heads_up_widget = None
        if range_x is None:
            range_x = [-128, 128]
        if range_y is None:
            range_y = [-128, 128]

        self.grid_color = QColor(200, 200, 200, 150)

        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.pos_scale = 1.0
        self.img_scale = 1.0

        self.grid = []

        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 100
        self.images = []
        self.range_x = range_x
        self.range_y = range_y
        self.font_size = 8
        self.title = title
        self.grid_line_width = 10

        self.left_button_pressed = False
        self.last_mouse_pos = QPoint()

        self.luminances = []
        self.raw_data = []

        self.n_grid = 12
        self.controls_itm = None

        self.add_grid()
        self.create_title()
        self.item_idx = dict()


        # self.tipp_label = self.scene().addText("Use F to Focus the complete Plot\nUse Ctrl/Cmd and Wheel to Zoom")
        # self.tipp_label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        # self.tipp_label.setDefaultTextColor(QColor(10,255,10))
        # self.tipp_label.setPos(self.mapToScene(QPoint(0, self.height() - 50)))

        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        # self.fitInView(   -range_x[0] * self.magnification / 12,
        #                   -range_y[0] * self.magnification/ 12,
        #                  (range_x[1] - range_x[0]) * self.magnification/ 12,
        #                  (range_y[1] - range_y[0]) * self.magnification/ 12, Qt.KeepAspectRatio)

    def add_image(self, x, y, img, convert = True, luminance = None, mime_data = None, z = 0, uid = None):
        pass

    def remove_image_by_uid(self, uid):
        if uid in self.item_idx:
            item = self.item_idx[uid][0]
            self.scene().removeItem(item)
            self.item_idx.pop(uid)
            self.images.remove(item)

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

    def update_item(self, uid, pos, pixmap = None):
        if uid in self.item_idx:
            itm = self.item_idx[uid]
            if pixmap is not None:
                itm.setPixmap(pixmap)
            itm.setPos(pos[0], pos[1])
            return True
        return False

    def set_image_scale(self, scale):
        for img in self.images:
            img.setScale(scale)
        self.img_scale = scale

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
        super(ImagePlot, self).mouseMoveEvent(event)
        if self.ctrl_is_pressed:
            delta = event.pos() - self.last_mouse_pos
            self.set_magnification(delta.x(),delta.y())
            self.last_mouse_pos = event.pos()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super(ImagePlot, self).resizeEvent(event)
        self.frame_default()

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
                itm.setScale(self.img_scale)

        else:
            t = 0
            if event.angleDelta().y() > 0.0:
                t = 0.1

            elif event.angleDelta().y() < 0.0:
                t = -0.1

            if 0 < self.pos_scale + t < 100:
                self.scale_pos(t)
            super(QGraphicsView, self).wheelEvent(event)

        # self.tipp_label.setPos(self.mapToScene(QPoint(30, self.height() - 50)))

    def clear_view(self):
        self.scene().clear()
        self.images.clear()
        self.luminances.clear()
        self.raw_data = []
        self.item_idx = dict()
        self.grid = []

    def frame_default(self):
        # self.tipp_label.setPos(QPointF())
        self.setSceneRect(self.scene().itemsBoundingRect())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

        # self.tipp_label.setPos(self.mapToScene(QPoint(30, self.height() - 50)))

    def render_to_image(self, background: QColor, size: QSize):
        """
        Renders the scene content to an image, alternatively if return iamge is set to True, 
        the QImage is returned and not stored to disc
        :param return_image: 
        :return: 
        """

        self.add_grid()
        r = self.scene().itemsBoundingRect()
        r.adjust(-20, -20, 20, 20)
        self.scene().setSceneRect(r)

        image = QImage(size, QImage.Format_ARGB32)
        image.fill(background)

        painter = QPainter()
        painter.begin(image)
        self.scene().render(painter)
        painter.end()

        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        return image

    def set_heads_up_widget(self, widget:QWidget):
        self.heads_up_widget = widget
        widget.setParent(self)
        widget.move(5,5)
        widget.resize(150, 20)
        widget.show()

    def get_heads_up_widget(self):
        return self.heads_up_widget

    def set_highlighted_by_uid(self, uids, reset = False, alpha_active = 1.0, alpha_inactive = 0.0):
        uids_hash = dict(zip(uids, uids))
        if len(uids) > 0:
            for k, v in self.item_idx.items():
                if k in uids_hash:
                    v[0].set_transparency(alpha_active)
                    uids_hash.pop(k)
                else:
                    v[0].set_transparency(alpha_inactive)
        else:
            if reset:
                for idx, img in enumerate(self.images):
                    img.set_transparency(1.0)
                    # img.setZValue(0.0)

    def set_highlighted(self, indices, reset = False):
        if len(indices) > 0:
            for idx, img in enumerate(self.images):
                if idx in indices:
                    img.set_transparency(1.0)
                    # img.setZValue(0.0)
                else:
                    img.set_transparency(0.2)
                    # img.setZValue(-10.0)
        else:
            if reset:
                for idx, img in enumerate(self.images):
                    img.set_transparency(1.0)

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

    def get_raw_data(self):
        return self.raw_data

    def apply_raw_data(self, raw_data):
        for itm in raw_data:
            self.add_image(x=itm.x, y = itm.y, img=itm.image, z=itm.z, mime_data=itm.mime_data)

    def reset_view(self):
        self.set_highlighted([], True)

    def get_scene(self):
        return self.scene()


class VIANPixmapGraphicsItemSignals(QObject):
    onItemSelection = pyqtSignal(object)
    def __init__(self, parent = None):
        super(VIANPixmapGraphicsItemSignals, self).__init__(parent)


class VIANPixmapGraphicsItem(QGraphicsPixmapItem):
    def __init__(self, pixmap:QPixmap, hover_text = None, mime_data = None, alternative_channels = None):
        super(VIANPixmapGraphicsItem, self).__init__(pixmap)
        if hover_text is not None:
            self.setToolTip(hover_text)
        self.abs_pos = None
        self.pos_scale = 1.0
        self.mime_data = mime_data
        self.signals = VIANPixmapGraphicsItemSignals()
        self.pixmap = pixmap
        self.curr_alpha = 1.0
        self.setAcceptHoverEvents(True)

        if alternative_channels is None:
            self.alternative_channels = dict()
        else:
            self.alternative_channels = alternative_channels
        # self.hovered = False

    def setPixmap(self, pixmap: QtGui.QPixmap):
        super(VIANPixmapGraphicsItem, self).setPixmap(pixmap)
        self.pixmap = pixmap

    def boundingRect(self):
        return QRectF(self.pixmap.rect())

    def scale_pos(self, scale, scale_y = None):
        if scale_y is None:
            self.pos_scale = scale
            super(VIANPixmapGraphicsItem, self).setPos(self.abs_pos * self.pos_scale)
        else:
            super(VIANPixmapGraphicsItem, self).setPos(QPointF(self.abs_pos.x() * scale, self.abs_pos.y() * scale_y))

    def setPos(self, x, y):
        pos = QPointF(x, y)
        if self.pixmap is not None:
            pos = pos - QPoint(0, self.boundingRect().height() * self.scale())
        super(VIANPixmapGraphicsItem, self).setPos(pos)
        self.abs_pos = pos

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        # super(VIANPixmapGraphicsItem, self).mousePressEvent(event)
        self.signals.onItemSelection.emit(self.mime_data)

    def set_transparency(self, alpha):
        if self.curr_alpha != alpha:
            self.setOpacity(alpha)
            self.curr_alpha = alpha


class ImagePlotCircular(ImagePlot):
    sendRangeScaleToControl = pyqtSignal(int)

    def __init__(self, parent, range_x = None, range_y = None, naming_fields = None):
        self.lbl_max = None
        super(ImagePlotCircular, self).__init__(parent, range_x, range_y, naming_fields=naming_fields)
        self.naming_fields['plot_name'] = "image_ab_plot"
        self.to_float = False
        self.img_scale = 2.8
        self.rho_max = 1.0
        self.pos_scale = 1.0
        self.magnification = 100.0

    def add_image(self, x, y, img, convert = True, luminance = None, to_float = False, mime_data = None, z = 0, uid = None):
        try:
            if convert:
                # itm = QGraphicsPixmapItem(numpy_to_pixmap(img))
                itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img), mime_data=mime_data)
            else:
                # itm = QGraphicsPixmapItem(numpy_to_pixmap(img, cvt=None,  with_alpha = True))
                itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True), mime_data=mime_data)
            self.scene().addItem(itm)

            self.to_float = to_float
            if to_float:
                itm.setPos(np.nan_to_num(-1.0 * (x -128) * self.magnification),np.nan_to_num(1.0 * (y -128) * self.magnification))
            else:
                itm.setPos(np.nan_to_num(-1.0 * (x * self.magnification)), np.nan_to_num(1.0 * (y * self.magnification)))

            self.raw_data.append(ImagePlotRawData(img, x, y, 0, mime_data))

            itm.setScale(self.img_scale)
            itm.scale_pos(self.pos_scale)
            itm.signals.onItemSelection.connect(self.onImageClicked.emit)
            self.images.append(itm)

            # set default position scaling if necessary
            rho = cart2pol(x, y)[0]
            if rho > self.rho_max:
                rho = (np.ceil(rho / 10)) * 10
                self.rho_max = rho
                scale = 128 / rho
                self.sendRangeScaleToControl.emit(int(scale * 100))
                self.pos_scale = scale
                self.set_range_scale()

            if uid is not None:
                if uid in self.item_idx:
                    self.scene().removeItem(self.item_idx[uid][0])
                self.item_idx[uid] = (itm, len(self.images) - 1)

            if luminance is not None:
                self.luminances.append([luminance, itm])

            itm.show()
            return itm

        except Exception as e:
            print(e)
            return None

    def update_item(self, uid, pos, pixmap = None):
        if uid in self.item_idx:
            itm = self.item_idx[uid][0]
            x = pos[0]
            y = pos[1]
            if pixmap is not None:
                itm.setPixmap(pixmap)
            if self.to_float:
                itm.setPos(np.nan_to_num(-1.0 * (x - 128) * self.magnification),
                           np.nan_to_num(1.0 * (y - 128) * self.magnification))
            else:
                itm.setPos(np.nan_to_num(-1.0 * (x * self.magnification)),
                           np.nan_to_num(1.0 * (y * self.magnification)))

            itm.scale_pos(self.pos_scale)
            return True
        return False

    def add_grid(self):
        for g in self.grid:
            self.scene().removeItem(g)
        if self.lbl_max is not None:
            if self.lbl_max in self.scene().items():
                self.scene().removeItem(self.lbl_max)
            self.lbl_max = None
        self.grid = []
        pen = QPen()
        pen.setWidth(self.grid_line_width)
        pen.setColor(self.grid_color)

        font = QFont()
        font.setPointSize(8 * self.magnification)

        for i in range(7):
            self.circle0 = self.scene().addEllipse(QRectF(0,
                                           0,(255/6 * i) * self.magnification,
                                                          (255 / 6 * i) * self.magnification),pen)
            self.grid.append(self.circle0)

            q = -(128/6 * i)
            self.circle0.setPos(q * self.magnification, q * self.magnification)

        for i in range(self.n_grid):
            x = 128 * self.magnification * np.cos(i * (2 * np.pi / self.n_grid))
            y = 128 * self.magnification * np.sin(i * (2 * np.pi / self.n_grid))
            l = self.scene().addLine(0, 0 , x, y, pen)
            self.grid.append(l)

        lbla = self.scene().addText("-B", font)
        lbla.setDefaultTextColor(self.grid_color)
        lbla.setPos( - lbla.boundingRect().width() / 2, 130 * self.magnification)
        self.grid.append(lbla)

        lblb = self.scene().addText("A", font)
        lblb.setDefaultTextColor(self.grid_color)
        lblb.setPos(130 * self.magnification,  - lblb.boundingRect().height() / 2)
        self.grid.append(lblb)

        self.lbl_max = self.scene().addText(str(round(128 / self.pos_scale, 0)), font)
        self.lbl_max.setDefaultTextColor(self.grid_color)
        self.lbl_max.setPos(130 * self.magnification, + (self.lbl_max.boundingRect().height()))

        lbla = self.scene().addText("B", font)
        lbla.setDefaultTextColor(self.grid_color)
        lbla.setPos(- lbla.boundingRect().width() / 2, -130 * self.magnification -lbla.boundingRect().height())
        self.grid.append(lbla)

        lblb = self.scene().addText("-A", font)
        lblb.setDefaultTextColor(self.grid_color)
        lblb.setPos(-130 * self.magnification - 2 * lbla.boundingRect().width(), - lblb.boundingRect().height() / 2 )
        self.grid.append(lblb)
        # self.circle0.show()

    def set_range_scale(self, value = None):
        if value is not None:
            self.pos_scale = value / 100

        font = QFont()
        font.setPointSize(10 * self.magnification)

        if self.lbl_max is not None:
            self.scene().removeItem(self.lbl_max)
            self.lbl_max = None
        self.lbl_max = self.scene().addText(str(round(128 / self.pos_scale, 0)), font)
        self.lbl_max.setDefaultTextColor(self.grid_color)
        self.lbl_max.setPos(130 * self.magnification, + (self.lbl_max.boundingRect().height()))

        for img in self.images:
            if isinstance(img, VIANPixmapGraphicsItem):
                img.scale_pos(self.pos_scale)

    def set_image_scale(self,value):
        for img in self.images:
            img.setScale(value / 100)
        self.img_scale = value / 100

    def get_param_widget(self, w = None):
        if w is None:
            w = ImagePlotCircularControls(self)
        w.slider_xscale.valueChanged.connect(self.set_range_scale)
        w.slider_yscale.valueChanged.connect(self.set_image_scale)
        self.sendRangeScaleToControl.connect(w.slider_xscale.setValue)

        self.set_range_scale(w.slider_xscale.value())
        self.set_image_scale(w.slider_yscale.value())

        return w

    def wheelEvent(self, event: QWheelEvent):
        t = 0
        q = abs(event.angleDelta().y() / ANGLE_DELTA_STEP)
        if event.angleDelta().y() > 0.0:
            t = (self.pos_scale + (0.1 * q)) * 100

        elif event.angleDelta().y() < 0.0:
            t = (self.pos_scale - (0.1 * q)) * 100

        if 0 < t / 100 < 100:
            self.set_range_scale(t)


class ImagePlotCircularControls(QWidget):
    def __init__(self, plot):
        super(ImagePlotCircularControls, self).__init__()
        self.setLayout(QVBoxLayout())
        hl1 = QHBoxLayout(self)
        hl1.addWidget(QLabel("Range Scale:", self))
        hl2 = QHBoxLayout(self)
        hl2.addWidget(QLabel("Image Scale:", self))

        self.slider_xscale = QSlider(Qt.Horizontal, self)
        self.slider_xscale.setRange(1, 1000)
        self.slider_xscale.setValue(100)
        self.slider_yscale = QSlider(Qt.Horizontal, self)
        self.slider_yscale.setRange(1, 1000)
        self.slider_yscale.setValue(int(plot.img_scale * 100))
        self.slider_xscale.setValue(int(plot.pos_scale * 100))


        hl1.addWidget(self.slider_xscale)
        x_scale_line = QSpinBox(self)
        x_scale_line.setRange(1, 1000)
        x_scale_line.setValue(int(plot.pos_scale * 100))

        hl1.addWidget(x_scale_line)

        hl2.addWidget(self.slider_yscale)
        self.y_scale_line = QSpinBox(self)
        self.y_scale_line.setRange(1, 1000)
        self.y_scale_line.setValue(int(plot.img_scale * 100))

        hl2.addWidget(self.y_scale_line)

        self.slider_yscale.valueChanged.connect(self.y_scale_line.setValue)
        self.y_scale_line.valueChanged.connect(self.slider_yscale.setValue)
        x_scale_line.valueChanged.connect(self.slider_xscale.setValue)
        self.slider_xscale.valueChanged.connect(x_scale_line.setValue)

        self.layout().addItem(hl1)
        self.layout().addItem(hl2)


class ImagePlotPlane(ImagePlot):
    sendRangeScaleToControl = pyqtSignal(int)

    def __init__(self, parent, range_x = None, range_y = None, title="", naming_fields=None):
        self.curr_angle = 0.0
        self.compass = None
        self.rho_max = 1.0
        super(ImagePlotPlane, self).__init__(parent, range_x, range_y, title=title, naming_fields=naming_fields)
        self.naming_fields['plot_name'] = "image_lc_plot"
        self.img_scale = 2.8

    def add_image(self, x, y, img, convert = True, mime_data = None, z = 0, uid=None):
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img), mime_data=mime_data)
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True), mime_data=mime_data)
        self.scene().addItem(itm)

        self.raw_data.append(ImagePlotRawData(img, x, y, z, mime_data))
        nx, nz = rotate((0, 0), (x, y), self.curr_angle)

        itm.setPos(np.nan_to_num(nx * self.curr_scale * self.magnification),
                   np.nan_to_num(self.range_y[1] * self.magnification - y * self.magnification * self.curr_scale))
        self.images.append(itm)
        itm.setZValue(nz)
        itm.signals.onItemSelection.connect(self.onImageClicked.emit)

        self.luminances.append([y, itm])
        if uid is not None:
            if uid in self.item_idx:
                self.scene().removeItem(self.item_idx[uid][0])
            self.item_idx[uid] = (itm, len(self.images) - 1)

        # set default position scaling if necessary
        rho = np.amax([cart2pol(x, y)[0], z])
        if rho > self.rho_max:
            q = rho
            rho = (np.ceil(cart2pol(x, y)[0] / 10)) * 10
            self.rho_max = rho
            scale = 255 / rho
            self.sendRangeScaleToControl.emit(int(scale * 100))
            self.curr_scale = scale
            self.set_scale()

        itm.show()
        itm.setScale(self.img_scale)
        return itm

    def update_item(self, uid, pos, pixmap = None):
        if uid in self.item_idx:
            itm, idx = self.item_idx[uid]
            x = pos[0]
            y = pos[1]
            z = pos[2]
            raw = self.raw_data[idx]
            self.raw_data[idx] = ImagePlotRawData(x=x, y=y, z=z,image=raw.image, mime_data=raw.mime_data)
            x, z = rotate((0, 0), (x, z), self.curr_angle)
            itm.setPos(np.nan_to_num(x * self.magnification) * self.curr_scale,
                                    np.nan_to_num(self.range_y[1] * self.magnification - y * self.magnification * self.curr_scale))
            itm.setZValue(z)
            if pixmap is not None:
                itm.setPixmap(pixmap)
            itm.scale_pos(self.pos_scale)
            return True
        return False

    def draw_compass(self):
        if self.compass is not None:
            return
        m = self.magnification
        p = QPen()
        p.setColor(QColor(100,100,100,200))
        p.setWidth(0.1)
        f = QFont()
        f.setPointSize(5* m)

        path = QPainterPath(QPointF(0,0))
        path.addEllipse(QRectF(95 * m,95* m,30* m,30* m))
        path.moveTo(110* m, 95* m)
        path.lineTo(110* m, 125* m)
        path.addText(105* m, 93* m, f, "+B")
        path.addText(105* m, 133* m, f, "-B")
        path.addText(85* m, 112* m, f, "-A")
        path.addText(127* m, 112* m, f, "+A")

        pitem = self.scene().addPath(path, p)
        self.compass = pitem
        t = QTransform()
        x, y = -110* m, -110* m
        t.translate(-x, -y)
        t.rotate(self.curr_angle)
        t.translate(x, y)

    def set_scale(self, v=None):
        try:
            if v is not None:
                self.curr_scale = v / 100
            for idx, itm in enumerate(self.raw_data):
                x, z = rotate((0, 0), (itm.x, itm.z), self.curr_angle)
                self.images[idx].setPos(np.nan_to_num(x * self.magnification) * self.curr_scale,
                                        np.nan_to_num(self.range_y[1] * self.magnification - itm.y * self.magnification * self.curr_scale))
                self.images[idx].setZValue(z)
            self.add_grid()
        except Exception as e:
            print(e)

    def rotate_view(self, angle_rad):
        angle = (angle_rad / 360 * np.pi) * 2
        self.curr_angle = angle_rad

        for idx, itm in enumerate(self.raw_data):
            x,z = rotate((0,0), (itm.x, itm.z), angle)
            try:
                self.images[idx].setPos(np.nan_to_num(x * self.magnification * self.curr_scale),
                                        np.nan_to_num(self.range_y[1] * self.magnification - itm.y * self.magnification * self.curr_scale))
                self.images[idx].setZValue(z)
            except Exception as e:
                print(e)
                continue

        t = QTransform()
        x, y = -110 * self.magnification, -110 * self.magnification
        t.translate(-x, -y)
        t.rotate(self.curr_angle)
        t.translate(x, y)
        self.compass.setTransform(t)

    def set_image_scale(self,value):
        for img in self.images:
            img.setScale(value / 100)
        self.img_scale = value / 100

    def add_grid(self):
        for itm in self.grid:
            self.scene().removeItem(itm)
        self.grid = []
        pen = QPen()
        pen.setWidth(self.grid_line_width)
        pen.setColor(self.grid_color)

        font = QFont()
        font.setPointSize(self.font_size * self.magnification)

        x0 = self.range_x[0] * self.magnification
        x1 = self.range_x[1] * self.magnification
        y0 = self.range_y[0] * self.magnification
        y1 = self.range_y[1] * self.magnification

        counter = 0
        for x in range(self.range_x[0] * self.magnification, self.range_x[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                l = self.scene().addLine(x, y0, x, y1, pen)
                self.grid.append(l)
                if counter % 2 == 0:
                    text = self.scene().addText(str(round((x / (self.magnification * self.curr_scale)), 0)), font)
                    text.setPos(x - text.boundingRect().width() / 2, self.range_y[1] * self.magnification)
                    text.setDefaultTextColor(self.grid_color)
                    self.grid.append(text)
                counter += 1

        font.setPointSize(int(self.font_size * 1.5 * self.magnification))
        text = self.scene().addText("Luminance", font)
        text.setRotation(-90)
        text.setPos(-(sum(self.range_y) / 2 + self.font_size) * self.magnification - text.boundingRect().height(), x + self.magnification / 2 + text.boundingRect().width() / 2)
        text.setDefaultTextColor(self.grid_color)
        font.setPointSize(self.font_size * self.magnification)
        self.grid.append(text)

        counter = 0
        for x in range(self.range_y[0] * self.magnification, self.range_y[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                l = self.scene().addLine(x0, x, x1, x, pen)
                self.grid.append(l)
                if counter % 2 == 0:
                    text = self.scene().addText(str(round(((self.range_y[1] * self.magnification - x) / (self.magnification * self.curr_scale)), 0)), font)
                    text.setPos(self.range_x[0] * self.magnification, x - text.boundingRect().height() / 2)
                    text.setDefaultTextColor(self.grid_color)
                    self.grid.append(text)
                counter += 1


        font.setPointSize(int(self.font_size * 1.5 * self.magnification))
        text = self.scene().addText("Chroma", font)
        text.setPos(sum(self.range_x) / 2 * self.magnification - (text.boundingRect().width() / 2), x + self.font_size * 2 * self.magnification)
        text.setDefaultTextColor(self.grid_color)
        self.grid.append(text)


        self.draw_compass()

    def get_param_widget(self, w=None):
        if w is None:
            w = ImagePlotPlaneControls(self)

        w.slider_image.valueChanged.connect(self.set_image_scale)
        w.slider_angle.valueChanged.connect(self.rotate_view)
        w.slider_xscale.valueChanged.connect(self.set_scale)
        self.sendRangeScaleToControl.connect(w.slider_xscale.setValue)

        self.set_image_scale(w.slider_image.value())
        self.rotate_view(w.slider_angle.value())
        self.set_scale(w.slider_xscale.value())

        return w

    def wheelEvent(self, event: QWheelEvent):
        t = 0
        q = abs(event.angleDelta().y() / ANGLE_DELTA_STEP)
        if event.angleDelta().y() > 0.0:
            t = (self.curr_scale + (0.1 * q))  * 100

        elif event.angleDelta().y() < 0.0:
            t = (self.curr_scale - (0.1 * q)) * 100

        if 0 < t / 100 < 100:
            self.set_scale(t)


class ImagePlotPlaneControls(QWidget):
    def __init__(self, plot):
        super(ImagePlotPlaneControls, self).__init__()
        self.setLayout(QVBoxLayout())

        hl2 = QHBoxLayout(self)
        hl2.addWidget(QLabel("Image Scale:", self))

        hl3 = QHBoxLayout(self)
        hl3.addWidget(QLabel("View Angle:", self))

        self.slider_image = QSlider(Qt.Horizontal, self)
        self.slider_image.setRange(1, 1000)
        self.slider_image.setValue(int(plot.img_scale * 100))

        hl2.addWidget(self.slider_image)

        self.slider_angle = QSlider(Qt.Horizontal, self)
        self.slider_angle.setRange(0, 360)

        hl1 = QHBoxLayout(self)
        hl1.addWidget(QLabel("Scale:", self))
        self.slider_xscale = QSlider(Qt.Horizontal, self)
        self.slider_xscale.setRange(1, 1000)
        self.slider_xscale.setValue(plot.curr_scale * 100)
        hl1.addWidget(self.slider_xscale)
        x_scale_line = QSpinBox(self)
        x_scale_line.setRange(1, 1000)
        x_scale_line.setValue(plot.curr_scale * 100)
        x_scale_line.valueChanged.connect(self.slider_xscale.setValue)
        self.slider_xscale.valueChanged.connect(x_scale_line.setValue)
        hl1.addWidget(x_scale_line)

        # hl2.addWidget(y_scale_line)

        hl3.addWidget(self.slider_angle)

        angle_sp = QSpinBox(self)
        angle_sp.setRange(1, 360)
        angle_sp.setValue(0)
        angle_sp.valueChanged.connect(self.slider_angle.setValue)
        self.slider_angle.valueChanged.connect(angle_sp.setValue)
        hl3.addWidget(angle_sp)

        self.layout().addItem(hl1)
        self.layout().addItem(hl2)
        self.layout().addItem(hl3)


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
    def __init__(self, parent, range_x = None, range_y = None, title="", image_scale = 150, y_scale = 100, naming_fields=None):
        self.x_scale = 0.001
        self.y_scale = 2000 #50 default
        self.base_line = 1000
        self.x_max = 0
        self.y_max = 1.0
        self.img_scale = 0.3

        self.lines = []
        self.itm_is_shown = dict()
        self.channel = "Saturation"
        self.channels = ["Saturation", "Chroma", "Hue", "Luminance"]

        self.pixel_size_x = 10000
        self.pixel_size_y = 2000

        self.border = 10000

        self.labels = []

        self.values = []
        self.shown_items = dict()
        super(ImagePlotTime, self).__init__(parent, range_x, range_y, title=title, naming_fields=naming_fields)
        self.naming_fields['plot_name'] = "image_color_dt"
        self.font_size = 60
        self.set_y_scale(y_scale)
        self.set_image_scale(image_scale)
        self.grid_line_width = 2

    def create_scene(self, x_max, y_max, pixel_size_x = 500, pixel_size_y = 500):
        self.pixel_size_x = pixel_size_x
        self.pixel_size_y = pixel_size_y

        self.x_scale = self.pixel_size_x / x_max
        self.y_scale = self.pixel_size_y / y_max
        self.base_line = y_max

        self.scene().setSceneRect(0, 0, x_max * self.x_scale, y_max * self.y_scale)

    def add_image(self, x, y, img, convert=True, mime_data = None, z = 0, uid = None, channels = None):
        timestamp = ms_to_string(x)
        # y = np.log10(y + 1.0)
        # y *= 10
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img),
                                         hover_text="Saturation:" + str(round(y, 2))+ "\t" + str(timestamp),
                                         mime_data=mime_data, alternative_channels=channels)
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True),
                                         hover_text="Saturation:" + str(round(y, 2))+ "\t" + str(timestamp), mime_data=mime_data,
                                         alternative_channels=channels)
        self.scene().addItem(itm)
        try:
            y = itm.alternative_channels[self.channel.lower()]
        except:
            log_error("Channel " + self.channel + "does not exist in VIANPixmapGraphicsItem")
            pass
        itm.setPos(np.nan_to_num(x * self.x_scale), np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale) - itm.boundingRect().height()))

        self.raw_data.append(ImagePlotRawData(img, x, y, z, mime_data))
        self.images.append(itm)
        self.itm_is_shown[itm] = True

        if self.x_max < x:
            self.x_max = x
            self.x_scale = (self.pixel_size_x / np.clip(self.x_max, 1, None))

        if self.y_max < y:
            self.y_max = y
            self.y_scale = (self.pixel_size_y / np.clip(self.y_max, 1, None))

        self.luminances.append([np.nan_to_num(y), itm])
        self.values.append([x, np.nan_to_num(y)])
        itm.signals.onItemSelection.connect(self.onImageClicked.emit)
        itm.show()

        if uid is not None:
            if uid in self.item_idx:
                self.scene().removeItem(self.item_idx[uid][0])
            self.item_idx[uid] = (itm, len(self.images) - 1)
            # self.set_x_scale(self.x_scale)
        # self.set_y_scale(self.y_scale)
        # self.set_image_scale(self.img_scale)
        self.update_position()
        return itm

    def update_item(self, uid, values, pixmap = None):
        if uid in self.item_idx:
            tpl = self.item_idx[uid]
            idx = tpl[1]
            itm = tpl[0]
            self.values[idx] = values
            x, y = values[0], values[1]
            if pixmap is not None:
                itm.setPixmap(pixmap)
            itm.setPos(np.nan_to_num(x * self.x_scale),
                       np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale))# - itm.boundingRect().height())
                       )

            update_grid = False
            if x > self.x_max:
                self.x_max = x
                update_grid = True
            if y > self.y_max:
                self.y_max = y
                update_grid = True
            if update_grid:
                self.update_grid()

            return True
        return False

    def clear_view(self):
        super(ImagePlotTime, self).clear_view()
        self.x_end = 0
        self.values = []
        self.lines = []
        self.item_idx = dict()
        self.images = []

    def add_grid(self, set_scene_rect = True):
        for l in self.lines:
            self.scene().removeItem(l)
        self.lines = []

        pen = QPen()
        pen.setWidth(self.grid_line_width)
        pen.setColor(self.grid_color)

        font = QFont()
        font.setPointSize(self.font_size)
        self.lines.append(self.scene().addLine(0, self.base_line * self.y_scale, self.x_max * self.x_scale * 1.1, self.base_line * self.y_scale , pen))
        self.lines.append(self.scene().addLine(0, self.base_line * self.y_scale, 0, np.nan_to_num((self.base_line * self.y_scale) - (self.y_max * self.y_scale) * 1.1), pen))

        step = np.ceil(self.y_max / 10)
        if step == 0:
            return
        n_steps = np.ceil(self.y_max / step) + 1

        for i in range(int(n_steps)):
            y = np.nan_to_num((self.base_line * self.y_scale) - ((i * step) * self.y_scale))
            self.lines.append(self.scene().addLine(0, y, self.x_max * self.x_scale * 1.1, y, pen))
            lbl = self.scene().addText(str(i * step), font)
            lbl.setDefaultTextColor(self.grid_color)
            lbl.setPos(-lbl.boundingRect().width(), y - (lbl.boundingRect().height() / 2))
            self.lines.append(lbl)

        font.setPointSize(self.font_size * 2)
        text = self.scene().addText("Time", font)
        text.setPos(self.x_max * self.x_scale / 2 - (text.boundingRect().width() / 2), self.base_line * self.y_scale + text.boundingRect().height())
        text.setDefaultTextColor(self.grid_color)
        self.lines.append(text)

        text = self.scene().addText(self.channel, font)
        text.setRotation(-90)
        text.setPos(-(text.boundingRect().height() * 3), self.base_line * self.y_scale - (self.y_max * self.y_scale / 2) + text.boundingRect().width() / 2)
        text.setDefaultTextColor(self.grid_color)
        self.lines.append(text)

        if set_scene_rect:
            self.setSceneRect(self.scene().itemsBoundingRect())
        for l in self.lines:
            l.setZValue(-100)

    def update_grid(self):
        for l in self.lines:
            self.scene().removeItem(l)
        self.lines = []
        self.setSceneRect(self.scene().itemsBoundingRect())
        # self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        self.add_grid(False)

    def set_x_scale(self, value):
        self.x_scale = (value / 50) * 0.001
        # self.x_scale = self.pixel_size_x / np.clip((len(self.images) * ((500 - value) / 100)), 0.00001, None)
        # self.x_scale = 0.01
        self.update_position()

    def set_y_scale(self, value):
        self.y_scale = value * 0.1
        self.update_position()

    def set_y_max(self, value):
        self.y_max = value
        self.y_scale = (self.pixel_size_y / np.clip(self.y_max, 1, None))
        self.update_position()

    def set_image_scale(self, scale):
        scale = scale / 100
        self.img_scale = scale
        super(ImagePlotTime, self).set_image_scale(scale)

    def set_channel(self, name):
        self.channel = name
        self.update_grid()
        self.update_position()

    def update_position(self):
        for idx, v in enumerate(self.values):
            itm = self.images[idx]
            x = v[0]
            y = v[1]

            try:
                y = itm.alternative_channels[self.channel.lower()]
            except Exception as e:
                print(e)

            if y * self.y_scale > self.pixel_size_y:
                if self.itm_is_shown[itm]:
                    self.scene().removeItem(itm)
                    self.itm_is_shown[itm] = False
            else:
                if self.itm_is_shown[itm] is False:
                    self.scene().addItem(itm)
                    self.itm_is_shown[itm] = True

            itm.setPos(np.nan_to_num(x * self.x_scale),
                       np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale)))
        super(ImagePlotTime, self).set_image_scale(self.img_scale)
        self.update_grid()

    def get_param_widget(self, w = None):
        if w is None:
            w = ImagePlotTimeControls(self)

        w.slider_y_max.valueChanged.connect(self.set_y_max)
        # w.slider_xscale.valueChanged.connect(self.set_x_scale)
        w.slider_imagescale.valueChanged.connect(self.set_image_scale)
        w.cb_channel.currentTextChanged.connect(self.set_channel)

        # self.set_y_scale(w.slider_yscale.value())
        # self.set_x_scale(w.slider_xscale.value())
        self.set_image_scale(w.slider_imagescale.value())
        self.set_channel(w.cb_channel.currentText())
        return w

    def wheelEvent(self, event: QWheelEvent):
        t = 0
        q = abs(event.angleDelta().y() / ANGLE_DELTA_STEP)
        if event.angleDelta().y() > 0.0:
            t = self.y_max + (5 * q)

        elif event.angleDelta().y() < 0.0:
            t = self.y_max - (5 * q)
        if 1 < t <= 255:
            self.set_y_max(t)


class ImagePlotTimeControls(QWidget):
    def __init__(self, plot):
        super(ImagePlotTimeControls, self).__init__()
        self.setLayout(QVBoxLayout())
        hl1 = QHBoxLayout(self)
        hl1.addWidget(QLabel("Image-Scale", self))
        hl2 = QHBoxLayout(self)
        hl2.addWidget(QLabel("Y-Max:", self))
        hl3 = QHBoxLayout(self)

        self.slider_imagescale = QSlider(Qt.Horizontal, self)
        self.slider_imagescale.setRange(1, 2000)
        self.slider_y_max = QSlider(Qt.Horizontal, self)
        self.slider_y_max.setRange(1, 256)

        hl1.addWidget(self.slider_imagescale)
        hl2.addWidget(self.slider_y_max)

        image_scale_line = QSpinBox(self)
        image_scale_line.setRange(1, 2000)
        image_scale_line.setValue(plot.x_scale)
        image_scale_line.valueChanged.connect(self.slider_imagescale.setValue)
        self.slider_imagescale.valueChanged.connect(image_scale_line.setValue)
        hl1.addWidget(image_scale_line)

        y_scale_line = QSpinBox(self)
        y_scale_line.setRange(1, 2000)
        y_scale_line.setValue(plot.y_scale)
        y_scale_line.valueChanged.connect(self.slider_y_max.setValue)
        self.slider_y_max.valueChanged.connect(y_scale_line.setValue)
        hl2.addWidget(y_scale_line)

        hl3.addWidget(QLabel("Channels:", self))
        self.cb_channel = QComboBox(self)
        self.cb_channel.addItems(plot.channels)
        hl3.addWidget(self.cb_channel)

        self.slider_imagescale.setValue(30)
        self.slider_y_max.setValue(255)

        self.layout().addItem(hl1)
        self.layout().addItem(hl2)
        self.layout().addItem(hl3)


class ImagePlotYear(ImagePlotTime):
    def __init__(self, parent, range_x = None, range_y = None, title="", image_scale = 150, y_scale = 100,naming_fields=None):
        self.x_scale = 0.1
        self.years = []
        self.year_grid = []
        # self.total_width = 20000
        super(ImagePlotYear, self).__init__(parent, range_x, range_y, title, image_scale, y_scale, naming_fields=naming_fields)
        self.itm_is_shown = dict()
        self.naming_fields['plot_name'] = "image_color_dy"
        self.grid_line_width = 2

    def add_image(self, x, y, img, convert=True, mime_data = None, z = 0, uid = None, hover_text = None, channels=None):
        if hover_text is None:
            hover_text = "Saturation:" + str(round(y, 2)) + "\nx: " + str(x)

        # y = np.log10(y + 1.0)
        # y *= 10
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img),
                                         hover_text=hover_text, mime_data=mime_data,
                                         alternative_channels=channels)
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True),
                                         hover_text=hover_text,
                                         mime_data=mime_data,
                                         alternative_channels=channels)
        self.scene().addItem(itm)
        itm.setPos(np.nan_to_num(x * self.x_scale), np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale) - itm.boundingRect().height()))

        self.raw_data.append(ImagePlotRawData(img, x, y, z, mime_data))
        self.images.append(itm)

        self.itm_is_shown[itm] = True

        if self.x_max < x:
            self.x_max = x
            self.x_scale = (self.pixel_size_x / np.clip(self.x_max, 1, None))

        if self.y_max < y:
            self.y_max = y
            self.y_scale = (self.pixel_size_y / np.clip(self.y_max, 1, None))

        self.luminances.append([np.nan_to_num(y), itm])
        self.values.append([x, np.nan_to_num(y)])
        itm.signals.onItemSelection.connect(self.onImageClicked.emit)
        itm.show()

        if uid is not None:
            if uid in self.item_idx:
                self.scene().removeItem(self.item_idx[uid][0])
            self.item_idx[uid] = (itm, len(self.images) - 1)

        # self.set_x_scale(self.x_scale)
        # self.set_y_scale(self.y_scale)
        # self.set_image_scale(self.img_scale)
        self.update_position()
        return itm

    def set_x_scale(self, value):
        return
        self.x_scale = (value / 50) * 0.1
        # self.x_scale = self.pixel_size_x / np.clip((len(self.images) * ((500 - value) / 100)), 0.00001, None)
        # self.x_scale = 0.01
        self.update_position()

    def set_y_max(self, value):
        self.y_max = value
        self.y_scale = (self.pixel_size_y / np.clip(self.y_max, 1, None))
        self.update_position()

    def add_year(self, value, name):
        self.years.append((value, name))
        self.update_grid()

    def update_grid(self):
        self.add_grid()

    def add_grid(self, set_scene_rect = True):
        for l in self.year_grid:
            self.scene().removeItem(l)
        self.year_grid = []
        for l in self.lines:
            self.scene().removeItem(l)
        self.lines = []

        pen = QPen()
        pen.setColor(self.grid_color)
        pen.setWidth(self.grid_line_width)

        # Y - Axis
        font = QFont()
        font.setPointSize(self.font_size)
        step = np.ceil(self.y_max / 10)
        if step == 0:
            return
        n_steps = np.ceil(self.y_max / step) + 1

        for i in range(int(n_steps)):
            y = np.nan_to_num((self.base_line * self.y_scale) - ((i * step) * self.y_scale))
            self.lines.append(self.scene().addLine(0, y, self.x_max * self.x_scale * 1.1, y, pen))
            lbl = self.scene().addText(str(i * step), font)
            lbl.setDefaultTextColor(self.grid_color)
            lbl.setPos(-lbl.boundingRect().width(), y - (lbl.boundingRect().height() / 2))
            self.lines.append(lbl)

        # X - Axis
        last_year_x = -100
        y_bottom_second_row = None
        for (value, name) in self.years:
            font = QFont()
            font.setPointSize(self.font_size)

            x = value * self.x_scale
            y = self.base_line * self.y_scale
            line = self.scene().addLine(x, y, x, (self.base_line - self.y_max) * self.y_scale, pen)
            text = self.scene().addText(str(name), font)
            if last_year_x > x:
                y += text.boundingRect().height() * 1.2
                y_bottom_second_row = text.boundingRect().height() * 2.0
            last_year_x = x + text.boundingRect().width()
            text.setPos(x - text.boundingRect().width()/2, y + text.boundingRect().height())
            text.setDefaultTextColor(self.grid_color)
            self.year_grid.append(line)
            self.year_grid.append(text)

            self.setSceneRect(self.scene().itemsBoundingRect())
            # self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            #             # self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
            #             # self.add_grid(False)


        font.setPointSize(self.font_size * 2)
        text = self.scene().addText("Year", font)
        text.setPos(self.x_max * self.x_scale / 2 - (text.boundingRect().width() / 2), self.base_line * self.y_scale + (text.boundingRect().height() * 2.0))
        text.setDefaultTextColor(self.grid_color)
        self.lines.append(text)

        text = self.scene().addText("Saturation", font)
        text.setRotation(-90)
        text.setPos(-(text.boundingRect().height() * 3), self.base_line * self.y_scale - (self.y_max * self.y_scale / 2) + text.boundingRect().width() / 2)
        text.setDefaultTextColor(self.grid_color)
        self.lines.append(text)

    def update_item(self, uid, values, pixmap=None):
        if uid in self.item_idx:
            tpl = self.item_idx[uid]
            idx = tpl[1]
            itm = tpl[0]
            self.values[idx] = values
            x, y = values[0], values[1]

            if y * self.y_scale > self.pixel_size_y:
                if self.itm_is_shown[itm]:
                    self.scene().removeItem(itm)
                    self.itm_is_shown[itm] = False
            else:
                if self.itm_is_shown[itm] is False:
                    self.scene().addItem(itm)
                    self.itm_is_shown[itm] = True

            if pixmap is not None:
                itm.setPixmap(pixmap)
            itm.setPos(itm.x(),
                       np.nan_to_num((self.base_line * self.y_scale) - (y * self.y_scale) - itm.boundingRect().height())
                       )
            return True

        return False

    def get_param_widget(self, w = None):
        if w is None:
            w = ImagePlotYearControls(self)
        w.slider_y_max.valueChanged.connect(self.set_y_max)
        w.slider_imagescale.valueChanged.connect(self.set_image_scale)
        w.cb_channel.currentTextChanged.connect(self.set_channel)

        self.set_y_scale(w.slider_y_max.value())
        self.set_image_scale(w.slider_imagescale.value())
        self.set_channel(w.cb_channel.currentText())

        return w
    
    
class ImagePlotYearControls(QWidget):
    def __init__(self, plot):
        super(ImagePlotYearControls, self).__init__()
        self.setLayout(QVBoxLayout())
        hl1 = QHBoxLayout(self)
        hl1.addWidget(QLabel("Image-Scale", self))
        hl2 = QHBoxLayout(self)
        hl2.addWidget(QLabel("Y-Max:", self))

        self.slider_imagescale = QSlider(Qt.Horizontal, self)
        self.slider_imagescale.setRange(1, 2000)

        self.slider_y_max = QSlider(Qt.Horizontal, self)
        self.slider_y_max.setRange(1, 255)

        hl1.addWidget(self.slider_imagescale)
        hl2.addWidget(self.slider_y_max)

        self.image_scale_line = QSpinBox(self)
        self.image_scale_line.setRange(1, 2000)
        self.image_scale_line.setValue(plot.x_scale)
        self.image_scale_line.valueChanged.connect(self.slider_imagescale.setValue)
        self.slider_imagescale.valueChanged.connect(self.image_scale_line.setValue)
        hl1.addWidget(self.image_scale_line)

        self.y_scale_line = QSpinBox(self)
        self.y_scale_line.setRange(1, 2000)
        self.y_scale_line.setValue(plot.y_scale)
        self.y_scale_line.valueChanged.connect(self.slider_y_max.setValue)
        self.slider_y_max.valueChanged.connect(self.y_scale_line.setValue)
        hl2.addWidget(self.y_scale_line)

        hl3 = QHBoxLayout(self)
        hl3.addWidget(QLabel("Channels:", self))
        self.cb_channel = QComboBox(self)
        self.cb_channel.addItems(plot.channels)
        hl3.addWidget(self.cb_channel)

        self.slider_imagescale.setValue(100)
        self.slider_y_max.setValue(255)


        self.layout().addItem(hl1)
        self.layout().addItem(hl2)
        self.layout().addItem(hl3)