import numpy as np
import cv2
from core.data.containers import VIANProject, SEGMENT
from collections import namedtuple
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from core.data.computation import *
from typing import *

FeatureTuple = namedtuple("FeatureTuple", ["name", "segment_ids"])
SegmentTuple = namedtuple("SegmentTuple", ['id', "start", "end"])

class VIANFeaturePlot(QGraphicsView):
    def __init__(self, parent, project: VIANProject, title =""):
        super(VIANFeaturePlot, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)

        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.project = project
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 0.001

        self.range_x = [0, 1000]
        self.range_y = [0, 1000]
        self.x_end = 0
        self.font_size = 4
        self.title = title

        self.images = []
        self.features = []
        self.segments = []
        self.segment_pos = []
        self.segment_lines = []
        self.feature_base_height = 900
        self.feature_height = 100

        self.n_grid = 12
        self.controls_itm = None

        self.scene_width = 0

        self.add_grid()
        self.create_timeline()
        self.create_title()


        self.fitInView(QRectF(0, 0, 80, 80), Qt.KeepAspectRatio)

    def add_grid(self):
        pass

    @pyqtSlot(list)
    def on_filter(self, names):
        for name in names:
            to_add = True
            for f in self.features:
                if f[0] is name:
                    to_add = False
                    break
            if to_add:
                self.on_add_feature(name)

        all_words = [f[0] for f in self.features]
        try:
            for i, w in enumerate(all_words):
                if w not in names:
                    self.remove_feature(self.features[i])
        except Exception as e:
            print(str(e))
        self.update_segment_lines()

    def remove_feature(self, feature):
        for rect in feature[1]:
            self.scene().removeItem(rect)
        self.scene().removeItem(feature[2])
        for l in feature[3]:
            self.scene().removeItem(l)
        self.features.remove(feature)

    def on_add_feature(self, word):
        y = self.feature_base_height - (self.feature_height * len(self.features))
        rects = []
        lines = []
        for con in word.connected_items:
            if con.get_type() == SEGMENT:
                rects.append(self.scene().addRect(con.get_start() * self.magnification, y, (con.get_end() - con.get_start()) * self.magnification, self.feature_height))
                rects.append(self.scene().addRect(con.get_start() * self.magnification, y,
                                                  (con.get_end() - con.get_start()) * self.magnification,
                                                  self.feature_height, QPen(), QBrush(QColor(100,10,10,200))))

        if len(rects) > 0:
            font = QFont("Consolas", 30)
            label = self.scene().addText(str(word.name).rjust(50), font)

            label.setPos(0 - 1200, y)
            label.setDefaultTextColor(QColor(255,255,255))

            lines.append(self.scene().addLine(0, y, self.x_end, y, QColor(100,100,100,100)))
            lines.append(self.scene().addLine(0, y + self.feature_height,
                                              self.x_end, y+ self.feature_height,
                                              QColor(100,100,100,100)))
            self.features.append([word, rects, label, lines])

    def update_segment_lines(self):
        for l in self.segment_lines:
            self.scene().removeItem(l)

        y = self.feature_base_height - (self.feature_height * len(self.features))
        for s in self.segment_pos:
            self.segment_lines.append(self.scene().addLine(s,
                                                           1200, s, y,
                                                           QColor(255, 255, 255, 230)))

    def create_timeline(self):
        for s in self.project.screenshots:
            img = cv2.resize(s.img_movie, (192, 108), interpolation=cv2.INTER_CUBIC)
            # img = s.img_movie
            shot = self.scene().addPixmap(numpy_to_pixmap(img))
            shot.setPos(s.movie_timestamp * self.magnification, 1400)
            self.images.append(shot)
        main_segm = self.project.get_main_segmentation()
        if main_segm is None:
            return

        self.x_end = self.project.movie_descriptor.duration * self.magnification
        for s in main_segm.segments:
            self.segments.append(self.scene().addRect(s.get_start() * self.magnification, 1200,
                                 (s.get_end() - s.get_start())*self.magnification, 200,
                                 QPen(), QBrush(QColor(0,113,122))))
            self.segments.append(self.scene().addRect(s.get_start() * self.magnification, 1200,
                                                      (s.get_end() - s.get_start()) * self.magnification, 200,
                                                      QColor(0, 0, 0)))
            self.segment_lines.append(self.scene().addLine(s.get_start() * self.magnification,
                                                      0, s.get_start() * self.magnification, 1400, QColor(255, 255, 255, 230)))
            self.scene_width = s.get_start() * self.magnification
            self.segment_pos.append(s.get_start() * self.magnification)

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

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
            self.curr_scale = round(self.img_width / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

            for itm in self.images:
                itm.setScale(1 - self.curr_scale)

        else:
            super(QGraphicsView, self).wheelEvent(event)

    def clear_view(self):
        self.scene().clear()
        self.images.clear()


class GenericFeaturePlot(QGraphicsView):
    def __init__(self, parent, title =""):
        super(GenericFeaturePlot, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 0.01
        self.spacing = 10

        self.range_x = [0, 1000]
        self.range_y = [0, 1000]
        self.x_end = 0

        self.font_family = "Consolas"
        self.text_color = QColor(255,255,255,200)
        self.font_size = 40
        self.title = title

        self.font = QFont(self.font_family, self.font_size)


        self.images = []
        self.features = []
        self.segments = []
        self.segment_items = []
        self.segment_label = []
        self.feature_items = []
        self.feature_labels = []
        self.feature_base_height = 900
        self.feature_height = 100

        self.segment_height = 150

        self.n_grid = 12
        self.controls_itm = None

        self.scene_width = 0

        self.create_title()

        self.fitInView(QRectF(0, 0, 80, 80), Qt.KeepAspectRatio)

        self.horizontalScrollBar().valueChanged.connect(self.on_h_scroll)

    def on_h_scroll(self):
        pos = self.mapToScene(QPoint(0,0))
        for t in self.feature_labels:
            t.setPos(pos.x(), t.pos().y())

    def remove_feature(self, feature):
        pass

    def create_timeline(self, segments: List[SegmentTuple]):
        for s in segments:
            itm = self.scene().addRect(s.start * self.magnification, self.feature_base_height,
                                       (s.end - s.start) * self.magnification, - self.segment_height,
                                       QPen(), QBrush(QColor(0, 113, 122)))
            self.segment_items.append(itm)
            self.segments = segments

    def create_feature(self, feature:FeatureTuple):
        y = (self.feature_base_height - self.segment_height) - ((self.feature_height + self.spacing) * (len(self.features)))
        itms = []
        for sid in feature.segment_ids:
            if sid >= len(self.segments):
                return

            s = self.segments[sid]
            itm = FeatureRectItem(s.start * self.magnification, y - self.spacing,
                                       (s.end - s.start) * self.magnification,
                                       - self.feature_height,
                                       QPen(), QBrush(QColor(100, 113, 122, 150)))
            self.scene().addItem(itm)
            self.scene().addItem(itm)


            itms.append(itm)

        label = self.scene().addText(feature.name.rjust(50), self.font)
        label.setDefaultTextColor(self.text_color)
        label.setPos(- self.font_size * 50 * 0.8, y - (self.feature_height * 3 / 4))
        self.feature_labels.append(label)

        self.features.append(feature)
        self.feature_items.append(itms)
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-1000,-1000,2000,2000)
        self.scene().setSceneRect(rect)

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            self.curr_scale = round(self.img_width / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

            for itm in self.images:
                itm.setScale(1 - self.curr_scale)

        else:
            super(QGraphicsView, self).wheelEvent(event)

        self.on_h_scroll()
    
    def clear_view(self):
        self.scene().clear()
        self.images.clear()
        self.segments.clear()
        self.features.clear()
        self.segment_items.clear()
        self.segment_label.clear()
        self.feature_items.clear()
        self.feature_labels.clear()



class FeatureRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, pen, brush):
        super(FeatureRectItem, self).__init__(x, y, w, h)
        self.setAcceptHoverEvents(True)
        self.c_unhovered = QBrush(QColor(100, 113, 122, 150))
        self.c_hovered = QBrush(QColor(100, 113, 122, 250))
        self.setPen(pen)
        self.setBrush(brush)

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_hovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(FeatureRectItem, self).hoverEnterEvent(event)


    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_unhovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(FeatureRectItem, self).hoverLeaveEvent(event)
