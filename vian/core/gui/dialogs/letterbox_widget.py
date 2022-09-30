from PyQt6.QtWidgets import QWidget, QSlider, QPushButton, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, \
    QGraphicsLineItem, QGraphicsItem, QGraphicsEllipseItem, QGridLayout, QLabel, QSpacerItem, QSpinBox, QSizePolicy
from PyQt6.QtCore import *
from PyQt6.QtGui import QPen, QColor, QPainter, QPainterPath, QResizeEvent
from PyQt6 import QtCore

from vian.core.container.project import MovieDescriptor
import cv2
import os
import numpy as np
import typing

from sklearn.cluster import AgglomerativeClustering
from vian.core.data.computation import numpy_to_pixmap, detect_letterbox
from vian.core.gui.ewidgetbase import EDialogWidget
from vian.core.gui.misc.utils import dialog_with_margin

class LetterBoxWidget(EDialogWidget):
    onFrameChanged = pyqtSignal(object)

    def __init__(self, parent, main_window, done_callback = None):
        super(LetterBoxWidget, self).__init__(parent, main_window=main_window)
        self.setLayout(QHBoxLayout())

        self.inner = QWidget(self)
        self.inner.setLayout(QVBoxLayout())
        self.view = LetterBoxView(self)

        self.widget_controls = QWidget()
        self.widget_controls.setLayout(QGridLayout())

        self.widget_controls.layout().addWidget(QLabel("Left:"), 0, 0)
        self.widget_controls.layout().addWidget(QLabel("Right:"), 1, 0)
        self.widget_controls.layout().addWidget(QLabel("Top:"), 2, 0)
        self.widget_controls.layout().addWidget(QLabel("Bottom:"), 3, 0)

        self.spinbox_left = QSpinBox(self)
        self.spinbox_right = QSpinBox(self)
        self.spinbox_top = QSpinBox(self)
        self.spinbox_bottom = QSpinBox(self)

        self.spinbox_left.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_right.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_top.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_bottom.valueChanged.connect(self.on_spinbox_changed)

        self.widget_controls.layout().addWidget(self.spinbox_left, 0, 1)
        self.widget_controls.layout().addWidget(self.spinbox_right, 1, 1)
        self.widget_controls.layout().addWidget(self.spinbox_top, 2, 1)
        self.widget_controls.layout().addWidget(self.spinbox_bottom, 3, 1)

        self.pos_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.pos_slider.setRange(0, 1000)

        self.inner.layout().addWidget(self.view)
        self.inner.layout().addWidget(self.pos_slider)

        self.layout().addWidget(self.inner)
        self.layout().addWidget(self.widget_controls)

        self.pos_slider.valueChanged.connect(self.on_slider_change)
        self.onFrameChanged.connect(self.view.set_image)

        self.btn_apply = QPushButton("Apply Letterbox", self)
        self.widget_controls.layout().addWidget(self.btn_apply, 5, 0, 1, 2)
        self.btn_detect = QPushButton("Auto Detect", self)
        self.btn_detect.clicked.connect(self.on_auto)
        self.widget_controls.layout().addWidget(self.btn_detect, 4, 0, 1, 2)

        self.widget_controls.layout().addItem(QSpacerItem(1,1, hPolicy=QSizePolicy.Policy.Fixed, vPolicy= QSizePolicy.Policy.Expanding), 6, 0)

        self.view.onChange.connect(self.on_view_changed)
        self.btn_apply.clicked.connect(self.on_apply)

        self.cap = None
        self.width = None
        self.height = None

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

        self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        self.spinbox_left.setMaximum(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.spinbox_right.setMaximum(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.spinbox_bottom.setMaximum(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.spinbox_top.setMaximum(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.pos_slider.setValue(500)

        r = self.movie_descriptor.get_letterbox_rect()
        
        if r is None:
            return

        self.view.set_rect(r)

    def on_auto(self):
        margins = detect_letterbox(self.movie_descriptor.movie_path, n_samples=20)
        self.view.set_rect((margins['left'],
                            margins['top'],
                           self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) - margins['right'] - margins['left'],
                           self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) - margins['bottom'] - margins['top']))

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

            self.onFrameChanged.emit(frame)
            self.get_rect()

    def set_rect(self, r:typing.Tuple[int, int, int, int]):
        print("Rect", r)
        if self.cap is None:
            return


    @pyqtSlot()
    def on_view_changed(self):
        r = self.get_rect()
        self.spinbox_left.valueChanged.disconnect(self.on_spinbox_changed)
        self.spinbox_right.valueChanged.disconnect(self.on_spinbox_changed)
        self.spinbox_top.valueChanged.disconnect(self.on_spinbox_changed)
        self.spinbox_bottom.valueChanged.disconnect(self.on_spinbox_changed)

        self.spinbox_left.setValue(r[0])
        self.spinbox_right.setValue(self.width - (r[0] + r[2]))
        self.spinbox_top.setValue(r[1])
        self.spinbox_bottom.setValue(self.height - (r[1] + r[3]))

        self.spinbox_left.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_right.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_top.valueChanged.connect(self.on_spinbox_changed)
        self.spinbox_bottom.valueChanged.connect(self.on_spinbox_changed)


    def on_spinbox_changed(self):
        self.view.onChange.disconnect(self.on_view_changed)
        self.view.set_rect((
            self.spinbox_left.value(),
            self.spinbox_top.value(),
            self.width - self.spinbox_right.value() - self.spinbox_left.value(),
            self.height - self.spinbox_bottom.value() - self.spinbox_top.value())
        )
        self.view.onChange.connect(self.on_view_changed)

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
    onChange = pyqtSignal()

    def __init__(self, parent):
        super(LetterBoxView, self).__init__(parent)
        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)
        self.frame_pmap = None
        self.selector_right = None
        self.selector_left = None
        self.selector_up = None
        self.selector_down = None

        self.frame = None

        self.modifying_selector = None

    @pyqtSlot(object)
    def set_image(self, frame):
        self.frame = frame
        pixmap = numpy_to_pixmap(frame)
        self.frame_pmap = self.scene().addPixmap(pixmap)
        self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        if self.selector_right is None:
            t = pixmap.size()
            self.selector_left = LetterBoxSelector(0, -50, 0, t.height() + 50, Qt.Orientation.Horizontal, view = self)
            self.selector_right = LetterBoxSelector(0, -50, 0, t.height() + 50, Qt.Orientation.Horizontal, view = self)
            self.selector_up = LetterBoxSelector(-50, 0, t.width()+50, 0, Qt.Orientation.Vertical, view = self)
            self.selector_down = LetterBoxSelector(-50, 0, t.width()+50, 0, Qt.Orientation.Vertical, view = self)

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
        self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    @pyqtSlot(tuple)
    def set_rect(self, r:typing.Tuple[int, int, int, int]):
        if self.selector_left is None:
            return
        self.selector_left.setPos(r[0], 0)
        self.selector_up.setPos(0, r[1])
        self.selector_right.setPos(r[2] + r[0], 0)
        self.selector_down.setPos(0, r[3] + r[1])

class LetterBoxSelector(QGraphicsItem):
    def __init__(self, x1, y1, x2, y2, orientation, view):
        super(LetterBoxSelector, self).__init__()
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

        self.fill_color = QColor(7, 7, 7, 255)

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
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            v = value
            self.view.onChange.emit()
            if self.orientation == Qt.Orientation.Horizontal:

                # Compute the fill col
                if self.view.frame is not None:
                    mean = np.mean(self.view.frame[:, int(np.clip(np.floor(v.x()), 0, self.view.frame.shape[1] - 1))], axis=0).astype(np.uint8)
                    self.fill_color = QColor(*mean[::-1], 255)
                return QPointF(v.x(), self.pos().y())
            else:
                if self.view.frame is not None:
                    mean = np.mean(self.view.frame[int(np.clip(np.floor(v.y()), 0, self.view.frame.shape[0] - 1)), :], axis=0).astype(np.uint8)
                    self.fill_color = QColor(*mean[::-1], 255)
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

        painter.fillPath(path, self.fill_color)
        painter.drawPath(path)
        self.scene().update()

    def boundingRect(self):
        r = QRectF(self.x1 - 20,  self.y1 - 20, self.x2 + 40, self.y2 + 40)
        return r

