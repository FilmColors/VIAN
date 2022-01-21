import numpy as np
import cv2
from vian.core.container.project import VIANProject, SEGMENT
from collections import namedtuple
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

from vian.core.visualization.basic_vis import IVIANVisualization
from vian.core.visualization.image_plots import VIANPixmapGraphicsItem, VIANPixmapGraphicsItemSignals, ImagePlotRawData
from vian.core.data.computation import *
from typing import *

FeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "segment_ids"])
SegmentTuple = namedtuple("SegmentTuple", ['id', "start", "end"])


class VIANFeaturePlot(QGraphicsView, IVIANVisualization):
    def __init__(self, parent, project: VIANProject, title ="", naming_fields=None):
        QGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "keyword_timeline"
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

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


        self.fitInView(QRectF(0, 0, 80, 80), Qt.AspectRatioMode.KeepAspectRatio)

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
            log_error(e)
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
            img = cv2.resize(s.get_img_movie(), (192, 108), interpolation=cv2.INTER_CUBIC)
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
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Control:
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

    def get_scene(self):
        return self.scene()

class GenericFeaturePlot(QGraphicsView, IVIANVisualization):
    onFeatureAdded = pyqtSignal(object)
    onSegmentClicked = pyqtSignal(object)
    onImageClicked = pyqtSignal(object)

    def __init__(self, parent, title ="", naming_fields=None):
        QGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "keyword_timeline"

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 1.0#0.005
        self.spacing = 10
        self.x_scale = 1.0
        self.image_scale = 0.5

        self.range_x = [0, 1000]
        self.range_y = [0, 1000]
        self.x_end = 0

        self.font_family = "Consolas"
        self.text_color = QColor(255,255,255,200)
        self.font_size = 50
        self.title = title

        self.font = QFont(self.font_family, self.font_size)

        self.images = []
        self.features = []
        self.all_possible_features = []
        self.segments = []
        self.segment_items = []
        self.segment_label = []
        self.feature_items = []
        self.feature_items_plain = []
        self.feature_labels = []
        self.feature_base_height = 900
        self.feature_height = 100
        self.raw_data = []

        self.segment_height = 200

        self.n_grid = 12
        self.stretch = 1.0
        self.controls_itm = None

        self.scene_width = 0

        self.create_title()

        self.fitInView(QRectF(0, 0, 80, 80), Qt.AspectRatioMode.KeepAspectRatio)

        self.horizontalScrollBar().valueChanged.connect(self.on_h_scroll)

    def on_h_scroll(self):
        pos = self.mapToScene(QPoint(0,0))
        for t in self.feature_labels:
            t.setPos(np.clip(pos.x(),(-t.sceneBoundingRect().width() + 10), None), t.pos().y())

    def remove_feature(self, feature):
        pass

    def add_image(self, x, y, img, convert=True, mime_data = None, z = 0):
        timestamp = ms_to_string(x)
        if convert:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img),
                                         hover_text="Saturation:" + str(round(y, 2))+ "\t" + str(timestamp), mime_data=mime_data)
        else:
            itm = VIANPixmapGraphicsItem(numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True),
                                         hover_text="Saturation:" + str(round(y, 2))+ "\t" + str(timestamp), mime_data=mime_data)
        self.scene().addItem(itm)
        itm.setPos(np.nan_to_num(x * self.magnification * self.stretch), self.feature_base_height)
        self.raw_data.append(ImagePlotRawData(img, x, y, z, mime_data))
        itm.setScale(self.image_scale)
        self.images.append(itm)

        # if self.x_end < x * self.x_scale:
        #     self.x_end = x * self.x_scale

        itm.signals.onItemSelection.connect(self.onImageClicked.emit)
        itm.show()

        return itm

    def create_timeline(self, segments: List[SegmentTuple]):
        max = 0
        for s in segments:
            if s.end > max:
                max = s.end
        self.stretch = 2000 / np.clip(max, 1, None)
        for s in segments:
            # itm = self.scene().addRect(s.start * self.magnification, self.feature_base_height,
            #                            (s.end - s.start) * self.magnification, - self.segment_height,
            #                            QPen(), QBrush(QColor(0, 113, 122)))

            itm = SegmentRectItem(s.start * self.magnification * self.stretch, self.feature_base_height,
                                                                  (s.end - s.start) * self.magnification * self.stretch,
                                                                - self.segment_height,
                                                                  QPen(), QBrush(QColor(0, 113, 122)), s)
            self.scene().addItem(itm)
            self.segment_items.append(itm)

        self.segments = segments

    def on_x_scale(self, new_scale):
        for s in self.segment_items:
            s.set_x_scale(new_scale)

        for f in self.feature_items:
            for s in f:
                s.set_x_scale(new_scale)
        for s in self.images:
            s.scale_pos(new_scale, 1.0)
        self.x_scale = new_scale
        rect = self.scene().itemsBoundingRect()
        rect = QRectF(0, rect.y(), 2000 * self.x_scale, rect.height())
        rect.adjust(-100* self.x_scale, -100, 200* self.x_scale, 200)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def scale_images(self, new_scale):
        for s in self.images:
            s.setScale(new_scale)
        self.image_scale = new_scale

    def create_feature(self, feature:FeatureTuple, show = False):
        if feature not in self.all_possible_features:
            self.all_possible_features.append(feature)
            self.onFeatureAdded.emit(self.all_possible_features)
        if not show:
            return
        y = (self.feature_base_height - self.segment_height) - ((self.feature_height + self.spacing) * (len(self.features)))
        itms = []
        for sid in feature.segment_ids:
            if sid >= len(self.segments):
                continue

            s = self.segments[sid]
            itm = FeatureRectItem(s.start * self.magnification * self.stretch, y - self.spacing,
                                       (s.end - s.start) * self.magnification * self.stretch,
                                       - self.feature_height,
                                       QPen(), QBrush(QColor(100, 113, 122, 150)))
            self.scene().addItem(itm)
            itms.append(itm)

        label = self.scene().addText(feature.name, self.font)
        label.setDefaultTextColor(self.text_color)
        label.setPos(-(label.sceneBoundingRect().width() + 10), y - self.feature_height - self.spacing)
        self.feature_labels.append(label)

        self.features.append(feature)
        self.feature_items.append(itms)
        self.feature_items_plain.extend(itms)

        self.on_x_scale(self.curr_scale)

        rect = self.scene().itemsBoundingRect()
        rect = QRectF(0, rect.y(), 2000 * self.x_scale, rect.height())
        rect.adjust(-100, -100, 200, 200)
        self.scene().setSceneRect(rect)

    def add_screenshot(self, image, time):
        self.add_image(time, 0, image)

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()

        rect = QRectF(0, rect.y(), 2000 * self.x_scale, rect.height())
        rect.adjust(-100* self.x_scale, -100, 200* self.x_scale, 200)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        elif event.key() == Qt.Key.Key_F:
            self.frame_default()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
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

    def clear_features(self):
        for f in self.feature_items_plain:
            try:
                self.scene().removeItem(f)
            except:
                continue
        for f in self.feature_labels:
            try:
                self.scene().removeItem(f)
            except:
                continue
        # self.scene().clear()
        # self.segment_items = []
        # self.create_timeline(self.segments)

        self.feature_items = []
        self.feature_items_plain = []
        self.feature_labels = []
        self.features = []

    def render_to_image(self, background: QColor, size: QSize):
        """
                Renders the scene content to an image, alternatively if return iamge is set to True, 
                the QImage is returned and not stored to disc
                :param return_image: 
                :return: 
                """
        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        t_size = self.sceneRect().size().toSize()
        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(Qt.transparent)

        painter = QPainter()
        painter.begin(image)
        self.scene().render(painter)
        painter.end()

        return image

    def on_filter_update(self, features):
        self.clear_features()
        for f in features:
            self.create_feature(f, True)

    def get_param_widget(self):
        w = FeaturesParamWidget(None, [])
        self.onFeatureAdded.connect(w.on_features_changed)
        w.onFeatureActivated.connect(self.on_filter_update)
        w.onXScale.connect(self.on_x_scale)
        w.onImageScale.connect(self.scale_images)
        return w

    def get_raw_data(self):
        return dict(segments=self.segments, features = self.features)

    def apply_raw_data(self, raw_data):
        self.create_timeline(raw_data['segments'])
        for f in raw_data['features']:
            self.create_feature(f)

    def get_scene(self):
        return self.scene()

class FeatureRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, pen, brush):
        super(FeatureRectItem, self).__init__(x, y, w, h)
        self.setAcceptHoverEvents(True)
        self.init_pos = QPoint(x, y)
        self.init_size = QSize(w, h)
        self.c_unhovered = QBrush(QColor(100, 113, 122, 150))
        self.c_hovered = QBrush(QColor(100, 113, 122, 250))
        self.setPen(pen)
        self.setBrush(QBrush(QColor(100, 113, 122, 150)))

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_hovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(FeatureRectItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_unhovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(FeatureRectItem, self).hoverLeaveEvent(event)

    def set_x_scale(self, scale):
        x = self.init_pos.x() * scale
        w = self.init_size.width() * scale
        self.setRect(x, self.init_pos.y(), w, self.init_size.height())


class QGraphicsItemSignals(QObject):
    onSegmentClicked = pyqtSignal(object)

    def __init__(self):
        super(QGraphicsItemSignals, self).__init__()


class SegmentRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, pen, brush, segment):
        super(SegmentRectItem, self).__init__(x, y, w, h)
        self.setAcceptHoverEvents(True)
        self.init_pos = QPoint(x, y)
        self.init_size = QSize(w, h)
        self.c_unhovered = QBrush(QColor(0, 113, 122, 150))
        self.c_hovered = QBrush(QColor(0, 113, 122, 250))
        self.setPen(pen)
        self.setBrush(QBrush(QColor(0, 113, 122, 150)))
        self.segment = segment
        self.signals = QGraphicsItemSignals()
        self.setToolTip("Double Click to inspect Segment")

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_hovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(SegmentRectItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.setBrush(self.c_unhovered)
        self.scene().update(self.scene().itemsBoundingRect())
        super(SegmentRectItem, self).hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent'):
        self.signals.onSegmentClicked.emit(self.segment)

    def set_x_scale(self, scale):
        x = self.init_pos.x() * scale
        w = self.init_size.width() * scale
        self.setRect(x, self.init_pos.y(), w, self.init_size.height())


class FeaturesParamWidget(QWidget):
    onFeatureActivated = pyqtSignal(object)
    onXScale = pyqtSignal(float)
    onImageScale = pyqtSignal(float)

    def __init__(self, parent, features):
        super(FeaturesParamWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.param_list = QTreeWidget(self)
        self.layout().addWidget(self.param_list)
        self.sl_x_scale = QSlider(Qt.Orientation.Horizontal, self)
        self.sl_x_scale.setRange(1, 100)
        self.sl_x_scale.setValue(10)
        self.hb_x_scale = QHBoxLayout(self)
        self.hb_x_scale.addWidget(QLabel("x-Scale", self))
        self.hb_x_scale.addWidget(self.sl_x_scale)
        self.sl_x_scale.valueChanged.connect(self.on_slider_x_scale)

        self.sl_img_scale = QSlider(Qt.Orientation.Horizontal, self)
        self.sl_img_scale.setRange(1, 100)
        self.sl_img_scale.setValue(10)
        self.hb_img_scale = QHBoxLayout(self)
        self.hb_img_scale.addWidget(QLabel("Image-Scale", self))
        self.hb_img_scale.addWidget(self.sl_img_scale)
        self.sl_img_scale.valueChanged.connect(self.on_slider_img_scale)
        
        self.layout().addItem(self.hb_x_scale)
        self.layout().addItem(self.hb_img_scale)
        self.param_list.itemClicked.connect(self.on_clicked)
        self.features = []
        self.show()

    @pyqtSlot(object)
    def on_features_changed(self, features:List[FeatureTuple]):
        self.param_list.clear()
        self.features.clear()
        curr_voc_name = None
        curr_voc_itm = None
        curr_class_name = None
        curr_class_itm = None

        for f in sorted(features, key=lambda x:(x.class_obj, x.voc_name, x.name)):
            if not f.class_obj == curr_class_name:
                curr_class_name = f.class_obj
                curr_class_itm = QTreeWidgetItem([curr_class_name])
                self.param_list.addTopLevelItem(curr_class_itm)
                curr_voc_name = None
            if not f.voc_name == curr_voc_name:
                curr_voc_name = f.voc_name
                curr_voc_itm = QTreeWidgetItem([f.voc_name])
                curr_class_itm.addChild(curr_voc_itm)

            itm = QTreeWidgetItem([f.name])
            itm.setCheckState(0, Qt.CheckState.Unchecked)

            curr_voc_itm.addChild(itm)
            self.features.append((itm, f))

    def on_slider_x_scale(self):
        v = self.sl_x_scale.value() / 10
        self.onXScale.emit(v)

    def on_slider_img_scale(self):
        v = self.sl_img_scale.value() / 20
        self.onImageScale.emit(v)

    def on_clicked(self):
        result = []
        for f in self.features:
            if f[0].checkState(0) == Qt.CheckState.Checked:
                result.append(f[1])
        self.onFeatureActivated.emit(result)