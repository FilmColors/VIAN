from PyQt5.QtWidgets import QWidget, QSlider, QPushButton, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, \
    QGraphicsLineItem, QGraphicsItem, QGraphicsEllipseItem
from PyQt5.QtCore import *
from PyQt5.QtGui import QPen, QColor, QPainter, QPainterPath, QResizeEvent
from PyQt5 import QtCore

from core.container.project import MovieDescriptor
import cv2
import os
import numpy as np
import typing

from core.data.computation import numpy_to_pixmap
from core.gui.ewidgetbase import EDialogWidget
from core.gui.misc.utils import dialog_with_margin

class LetterBoxWidget(EDialogWidget):
    onFrameChanged = pyqtSignal(object)

    def __init__(self, parent, main_window, done_callback = None):
        super(LetterBoxWidget, self).__init__(parent, main_window=main_window)
        self.setLayout(QVBoxLayout())
        self.view = LetterBoxView(self)
        self.pos_slider = QSlider(Qt.Horizontal, self)
        self.pos_slider.setRange(0, 1000)
        self.layout().addWidget(self.view)
        self.layout().addWidget(self.pos_slider)
        self.pos_slider.valueChanged.connect(self.on_slider_change)
        self.onFrameChanged.connect(self.view.set_image)

        self.btn_apply = QPushButton("Apply Letterbox", self)
        self.layout().addWidget(self.btn_apply)

        self.btn_apply.clicked.connect(self.on_apply)

        self.cap = None
        self.duration = 1000
        self.movie_descriptor = None #type:None|MovieDescriptor
        self.done_callback = done_callback

        dialog_with_margin(self.main_window, self, mode="lg")


    def set_movie(self, movie_descriptor):
        self.movie_descriptor = movie_descriptor
        if not os.path.isfile(movie_descriptor.movie_path):
            return
        self.cap = cv2.VideoCapture(movie_descriptor.movie_path)
        self.duration = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

        # self.resize(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 0.8, self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * 0.8)
        self.pos_slider.setValue(1)

        r = self.movie_descriptor.get_letterbox_rect()
        if r is None:
            return

        self.view.selector_left.setPos(r[0], 0)
        self.view.selector_up.setPos(0, r[1])
        self.view.selector_right.setPos(r[2] + r[0], 0)
        self.view.selector_down.setPos(0, r[3] + r[1])


    def on_slider_change(self):
        if self.cap is None:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.pos_slider.value() * (self.duration / 1000)))
        ret, frame = self.cap.read()
        if frame is not None:

            # Uncomment this for correct aspect in letterbox dialog
            # if self.movie_descriptor.display_width is not None and self.movie_descriptor.display_height is not None:
            #     frame = cv2.resize(frame,
            #                        (self.movie_descriptor.display_width, self.movie_descriptor.display_height),
            #                        interpolation=cv2.INTER_CUBIC)

            self.onFrameChanged.emit(numpy_to_pixmap(frame))
            self.get_rect()

    def on_apply(self):
        if self.movie_descriptor is not None:
            self.movie_descriptor.set_letterbox_rect(self.get_rect())
        self.close()
        if self.done_callback is not None:
            self.done_callback()

    def get_rect(self):
        r = (int(np.clip(self.view.selector_left.pos().x(), 0, self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))),
             int(np.clip(self.view.selector_up.pos().y(), 0, self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))),
             int(np.clip(self.view.selector_right.pos().x() - self.view.selector_left.pos().x(), 0, self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))),
             int(np.clip(self.view.selector_down.pos().y() - self.view.selector_up.pos().y(), 0, self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        return r


class LetterBoxView(QGraphicsView):
    def __init__(self, parent):
        super(LetterBoxView, self).__init__(parent)
        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.frame_pmap = None
        self.selector_right = None
        self.selector_left = None
        self.selector_up = None
        self.selector_down = None

        self.modifying_selector = None

    @pyqtSlot(object)
    def set_image(self, pixmap):
        self.frame_pmap = self.scene().addPixmap(pixmap)
        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        if self.selector_right is None:
            t = pixmap.size()
            self.selector_left = LetterBoxSelector(0, -50, 0, t.height() + 50, Qt.Horizontal, view = self)
            self.selector_right = LetterBoxSelector(0, -50, 0, t.height() + 50, Qt.Horizontal, view = self)
            self.selector_up = LetterBoxSelector(-50, 0, t.width()+50, 0, Qt.Vertical, view = self)
            self.selector_down = LetterBoxSelector(-50, 0, t.width()+50, 0, Qt.Vertical, view = self)

            self.scene().addItem(self.selector_right)
            self.scene().addItem(self.selector_left)
            self.scene().addItem(self.selector_up)
            self.scene().addItem(self.selector_down)

            self.selector_right.setPos(t.width(), 0)
            self.selector_down.setPos(0, t.height())
        self.selector_down.setZValue(1)
        self.selector_left.setZValue(1)
        self.selector_up.setZValue(1)
        self.selector_down.setZValue(1)

        self.frame_pmap.setZValue(-5)

    def resizeEvent(self, event: QResizeEvent):
        super(LetterBoxView, self).resizeEvent(event)
        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)


class LetterBoxSelector(QGraphicsItem):
    def __init__(self, x1, y1, x2, y2, orientation, view):
        super(LetterBoxSelector, self).__init__()
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

        # self.setAcceptedMouseButtons()
        self.pen = QPen(QColor(255, 255, 255, 200))
        self.pen.setWidth(1)
        self.orientation = orientation
        self.view = view
        self.old_pos = None
        self.hovered = False

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(LetterBoxSelector, self).mousePressEvent(event)
        self.view.modifying_selector = self
        self.old_pos = self.pos()

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.hovered = True

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.hovered = False

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if change == QGraphicsItem.ItemPositionChange:
            v = value
            if self.orientation == Qt.Horizontal:
                return QPointF(v.x(), self.pos().y())
            else:
                return QPointF(self.pos().x(), v.y())

        return super(LetterBoxSelector, self).itemChange(change, value)

    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: typing.Optional[QWidget] = ...):
        path = QPainterPath()
        path.addEllipse(QRectF(self.x1 - 10,  self.y1 - 10, 20, 20))
        if self.hovered:
            self.pen.setColor(QColor(255,100,100,250))
        else:
            self.pen.setColor(QColor(255,100,100,150))
        painter.setPen(self.pen)
        painter.drawLine(self.x1, self.y1, self.x2, self.y2)

        painter.fillPath(path, QColor(7, 7, 7, 255))
        painter.drawPath(path)
        self.scene().update()

    def boundingRect(self):
        r = QRectF(self.x1 - 20,  self.y1 - 20, self.x2 + 40, self.y2 + 40)
        return r

