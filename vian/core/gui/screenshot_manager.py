from functools import partial

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSlot
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import *
from vian.core.data.enums import *

from vian.core.data.computation import *
from vian.core.container.project import VIANProject
from vian.core.container.screenshot import Screenshot
from vian.core.data.interfaces import IProjectChangeNotify
from vian.core.gui.ewidgetbase import EDockWidget, EToolBar, ImagePreviewPopup

from threading import Lock

class SMSegment(object):
    def __init__(self, name, segm_id, segm_start):
        self.segm_name = name
        self.segm_id = segm_id
        self.segm_start = segm_start
        self.segm_images = []
        self.scr_captions = []
        self.scr_caption_offset = QPoint(0,0)


class ScreenshotsManagerDockWidget(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ScreenshotsManagerDockWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Screenshots")

        if is_vian_light():
            self.inner.menuBar().hide()

        self.m_display = self.inner.menuBar().addMenu("Display")

        self.lbl_n = None
        self.bar = None

        self.curr_visualization = "Row-Column"

        self.m_display.addSeparator()
        self.a_follow_time = self.m_display.addAction(" Follow Time")
        self.a_follow_time.setCheckable(True)
        self.a_follow_time.setChecked(True)
        self.a_follow_time.triggered.connect(self.on_follow_time)
        self.m_display.addSeparator()
        self.a_toggle_name = self.m_display.addAction(" Show Segment Names")
        self.a_toggle_name.setCheckable(True)
        self.a_toggle_name.setChecked(False)
        self.a_toggle_name.triggered.connect(self.on_toggle_name)

        self.a_show_only_current = self.m_display.addAction(" Only Show Current Segment")
        self.a_show_only_current.setCheckable(True)
        self.a_show_only_current.setChecked(False)
        self.a_show_only_current.triggered.connect(self.on_toggle_show_current)

        self.tab = None
        self.slider_image_size = None
        self.screenshot_manager = None

        self.color_dt_mode = "Saturation"
        self.ab_view_mean_cache = dict()

    def on_toggle_name(self):
        state = self.a_toggle_name.isChecked()
        self.screenshot_manager.show_segment_name = state
        self.screenshot_manager.update_manager()

    def on_follow_time(self):
        self.screenshot_manager.follow_time = self.a_follow_time.isChecked()

    def set_manager(self, screenshot_manager):
        self.screenshot_manager = screenshot_manager
        self.inner.setCentralWidget(screenshot_manager)

        self.main_window.currentClassificationObjectChanged.connect(self.screenshot_manager.on_classification_object_changed)

    def on_toggle_show_current(self):
        state = self.a_show_only_current.isChecked()
        self.screenshot_manager.only_show_current_segment = state
        self.screenshot_manager.frame_segment(self.screenshot_manager.current_segment_index)

    def on_n_per_row_changed(self, value):
        self.screenshot_manager.n_per_row = value + 1
        self.lbl_n.setText("\t" + str(value))
        self.screenshot_manager.arrange_images()
        self.screenshot_manager.frame_segment(self.screenshot_manager.current_segment_index)

    def remove_screenshot(self, scr):
        pass

    def on_loaded(self, project:VIANProject):
        project.onScreenshotGroupAdded.connect(self.connect_scr_group)
        for grp in project.screenshot_groups:
            self.connect_scr_group(grp)
            for scr in grp.screenshots:
                self.add_screenshot(scr)
        project.onScreenshotsHighlighted.connect(self.on_screenshots_highlighted)

    def on_closed(self):
        pass

    @pyqtSlot(object)
    def on_screenshots_highlighted(self, screenshots):
        pass

    def connect_scr_group(self, grp):
        grp.onScreenshotAdded.connect(self.add_screenshot)
        grp.onScreenshotRemoved.connect(self.remove_screenshot)

    @pyqtSlot(object)
    def add_screenshot(self, scr:Screenshot):
        pass

    @pyqtSlot(object, object, object)
    def update_screenshot(self, scr, ndarray=None, pixmap=None):
        return

class ScreenshotsManagerWidget(QGraphicsView, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    def __init__(self,main_window, parent = None, ab_view = None, color_dt_view = None):
        super(ScreenshotsManagerWidget, self).__init__(parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        self.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing|QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        self.is_hovered = False
        self.ctrl_is_pressed = False
        self.shift_is_pressed = False
        self.follow_time = True
        self.show_segment_name = False
        self.only_show_current_segment = False

        self.color = QColor(225,225,225)

        self.loading_icon = None
        self.loading_text= None

        self.setDragMode(self.DragMode.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.IntersectsItemShape)
        self.rubberband_rect = QtCore.QRect(0, 0, 0, 0)
        self.curr_scale = 1.0
        self.curr_image_scale = 1.0

        self.main_window = main_window
        self.main_window.onSegmentStep.connect(self.frame_segment)

        self.scene = ScreenshotsManagerScene(self)
        self.setScene(self.scene)

        self.project = None
        self.images_plain = []
        self.images_segmentation = []
        self.captions = []
        self.scr_captions = []
        self.selected = []
        self.selection_frames = []

        # The scrollbar location before clearing the scene
        self.current_y = 0

        self.write_lock = Lock()

        self.selected = []

        self.current_segment_index = 0
        self.current_segment_frame = None

        self.border_height = 0
        self.img_height = 0
        self.img_width = 0

        self.n_images = 0
        self.rubberBandChanged.connect(self.rubber_band_selection)

        self.qimage_cache = dict()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.current_available_size = event.size()
        self.arrange_images()

    def set_loading(self, state):
        if state:
            self.clear_manager()
            lbl = QLabel()
            movie = QtGui.QMovie(os.path.abspath("qt_ui/icons/spinner4.gif"))
            lbl.setMovie(movie)
            lbl.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
            movie.start()

            font = QFont("Bahnschrift", 36)
            self.loading_icon = self.scene.addWidget(lbl)
            self.loading_text = self.scene.addText("Loading Screenshots... please wait.", font)
            self.loading_text.setDefaultTextColor(QColor(255,255,255))
            self.loading_icon.setPos(256, 256)
            self.loading_text.setPos(512 - self.loading_text.boundingRect().width() / 2, 786)
            self.scene.removeItem(self.current_segment_frame)

            self.setSceneRect(self.scene.itemsBoundingRect())
        else:
            if self.loading_icon is not None:
                self.scene.removeItem(self.loading_icon)
                self.scene.removeItem(self.loading_text)
            self.update_manager()

    def toggle_annotations(self):
        return
        if len(self.selected) == 0:
            return

        state = not self.selected[0].screenshot_obj.annotation_is_visible
        for s in self.selected:
            # Only change those which aren't already
            if s.screenshot_obj.annotation_is_visible != state:
                if state and s.screenshot_obj.img_blend is not None:
                    s.setPixmap(numpy_to_pixmap(s.screenshot_obj.img_blend))
                    s.screenshot_obj.annotation_is_visible = state
                else:
                    s.setPixmap(numpy_to_pixmap(s.screenshot_obj.get_img_movie()))
                    s.screenshot_obj.annotation_is_visible = False
        pass

    def update_manager(self):
        """
        Recreating the Data Structures
        :return: 
        """

        if self.project is None:
            return

        self.clear_manager()

        current_segment_id = -1
        current_sm_object = None
        new_qimage_cache = dict()
        for s in self.project.screenshots:

            # If this Screenshot belongs to a new Segment, append the last SMObject to the list
            if s.scene_id != current_segment_id:
                if current_sm_object is not None:
                    self.images_segmentation.append(current_sm_object)

                current_segment_id = s.scene_id
                if current_segment_id > 0:
                    segment = self.project.get_segment_of_main_segmentation(current_segment_id - 1)
                    if segment is not None:
                        current_sm_object = SMSegment(segment.get_name(), segment.ID, segment.get_start())
                else:
                    current_sm_object = SMSegment("Unassigned Screenshots", 0, -1) # id=0 represents a container for screenshots which are not assigned to a segment

            item_image = ScreenshotManagerPixmapItems(None, self, s)
            item_image.set_pixmap()
            self.scene.addItem(item_image)

            self.images_plain.append(item_image)
            if current_sm_object is not None:
                current_sm_object.segm_images.append(item_image)

        if current_sm_object is not None:
            self.images_segmentation.append(current_sm_object)

        self.qimage_cache = new_qimage_cache
        self.clear_selection_frames()
        self.arrange_images()

    def clear_manager(self):
        self.current_y = self.verticalScrollBar().value()

        self.scene.clear()
        self.images_plain = []
        self.captions = []
        self.current_segment_frame = None
        self.images_segmentation = []

    def arrange_images(self):
        if self.current_available_size is None:
            return

        margin = 10 * self.curr_image_scale
        y = margin

        self.clear_captions()

        for segm in self.images_segmentation:
            cap = self.add_line(margin, y, self.current_available_size.width() - margin, y)
            y += cap.boundingRect().height()

            x = margin
            y += margin

            if segm.segm_id == 0: # unassigned screenshots
                cap = self.add_caption(x, y, segm.segm_name)
            else:
                cap = self.add_caption(x, y, f'{segm.segm_name} (ID: {segm.segm_id})')
            y += cap.boundingRect().height()

            highest_img_per_line = []
            current_line_index = 0
            for i, img in enumerate(segm.segm_images):

                img.setScale(self.curr_image_scale)
                scaled_width = img.boundingRect().width()*self.curr_image_scale
                scaled_height = img.boundingRect().height()*self.curr_image_scale

                if x + scaled_width > self.current_available_size.width() - margin: #i.e. new line
                    x = margin
                    if len(highest_img_per_line) > current_line_index:
                        y += highest_img_per_line[current_line_index]
                    current_line_index += 1

                #find highest image in line
                if len(highest_img_per_line) < current_line_index + 1:
                    highest_img_per_line.append(scaled_height)
                elif highest_img_per_line[current_line_index] < scaled_height:
                    highest_img_per_line[current_line_index] = scaled_height

                img.setPos(x, y)

                x += scaled_width

            if len(highest_img_per_line) > 0:
                y += highest_img_per_line[-1]
            y += 2 * margin # add a big margin at the end

        self.setSceneRect(0,0,self.current_available_size.width(), y)
        # Drawing the New Selection Frames
        self.draw_selection_frames()

    def add_line(self, x1, y1, x2, y2):
        p1 = QtCore.QPointF(x1, y1)
        p2 = QtCore.QPointF(x2, y2)

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(200, 200, 200))
        pen.setWidth(1)
        line = self.scene.addLine(QtCore.QLineF(p1, p2), pen)
        self.captions.append(line)
        return line

    def add_caption(self, x, y, text):
        caption = self.scene.addText(str(text))
        caption.setDefaultTextColor(self.color)
        caption.setPos(QtCore.QPointF(x, y))
        self.captions.append(caption)
        return caption

    def clear_selection_frames(self):
        for s in self.selection_frames:
            self.scene.removeItem(s)
        self.selection_frames = []

    def clear_captions(self):
        with self.write_lock:
            for cap in self.captions:
                self.scene.removeItem(cap)
            self.captions = []

    def clear_scr_captions(self):
        with self.write_lock:
            for cap in self.scr_captions:
                self.scene.removeItem(cap)

            self.scr_captions = []

    def select_image(self, images, dispatch = True):
        self.selected = images

        # Drawing the New Selection Frames
        self.draw_selection_frames()

        if dispatch:
            sel = []
            for i in self.selected:
                sel.append(i.screenshot_obj)
            self.project.set_selected(self, sel)

    def draw_selection_frames(self):
        return

    def frame_image(self, image):
        rect = image.sceneBoundingRect()
        self.curr_scale = self.sceneRect().width() / rect.width()

    def frame_screenshot(self, scr_item):
        for s in self.images_plain:
            if isinstance(s, ScreenshotManagerPixmapItems) and s.screenshot_obj == scr_item:
                rect = s.sceneBoundingRect()
                self.curr_scale = self.sceneRect().width() / rect.width()
                break

    def frame_segment(self, segment_index, center = True):
        return
        self.current_segment_index = segment_index
        self.arrange_images()

        if self.follow_time:
            x = self.scene.sceneRect().width()
            y = self.scene.sceneRect().height()
            width = 0
            height = 0

            if self.only_show_current_segment:
                for i, img_segm in enumerate(self.images_segmentation):
                    if img_segm.segm_id - 1 != self.current_segment_index:
                        for img in img_segm.segm_images:
                            img.hide()
                        for cap in img_segm.scr_captions:
                            cap.hide()
                    else:
                        for img in img_segm.segm_images:
                            img.show()
                        for cap in img_segm.scr_captions:
                            cap.show()

            # # Segments that are empty are not represented in self.images_segmentation
            # if segment_index >= len(self.images_segmentation):
            #     return

            index = -1
            for i, s in enumerate(self.images_segmentation):
                try:
                    if s.segm_id == segment_index + 1:
                        index = i
                except:
                    return

            if index == -1:
                return

            # Determining the Bounding Box
            for img in self.images_segmentation[index].segm_images:
                if img.scenePos().x() < x:
                    x = img.scenePos().x()
                if img.scenePos().y() < y:
                    y = img.scenePos().y()
                if img.scenePos().y() + img.pixmap().width() > width:
                    width = img.scenePos().x() + img.pixmap().width()
                if img.scenePos().y() + img.pixmap().height() > height:
                    height = img.scenePos().y() + img.pixmap().height()


            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)



            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(251, 95, 2, 60))
            pen.setWidth(20)
            self.current_segment_frame = self.scene.addRect(0, y-int(self.img_height/5) - 10, self.sceneRect().width() + 100, height - y + int(self.img_height / 7) + self.img_height - 100, pen)

            if center:
                self.current_segment_frame.boundingRect()

        else:
            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)
                self.current_segment_frame = None

    def on_loaded(self, project):
        self.clear_manager()
        self.setEnabled(True)
        self.project = project
        self.project.movie_descriptor.onLetterBoxChanged.connect(partial(self.update_manager))
        self.update_manager()

    def on_changed(self, project, item):
        if item is not None and item.get_type() not in [SEGMENT, SEGMENTATION, SCREENSHOT, SCREENSHOT_GROUP]:
            return
        # self.project = project

        self.update_manager()
        self.on_selected(None, project.get_selected())

        # if self.follow_time:
        #     self.frame_segment(self.current_segment_index)
        # else:
        #     self.center_images()

    @QtCore.pyqtSlot(object)
    def on_classification_object_changed(self):
        self.draw_visualizations(clear = True)

    def on_closed(self):
        self.clear_manager()
        self.setEnabled(False)

    def on_selected(self, sender, selected):
        return

    def rubber_band_selection(self, QRect, Union, QPointF=None, QPoint=None):
        self.rubberband_rect = self.mapToScene(QRect).boundingRect()

    def wheelEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            self.curr_image_scale = max(0.1, self.curr_image_scale + event.angleDelta().y()/1000)
            self.arrange_images()

        else:
            super(ScreenshotsManagerWidget, self).wheelEvent(event)


    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_A:
            self.select_image(self.images_plain)
        else:
            event.ignore()

    def mouseReleaseEvent(self, QMouseEvent):
        if self.rubberband_rect.width() > 20 and self.rubberband_rect.height() > 20:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if not modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                self.project.set_selected(None, [])

            for i in self.images_plain:
                i_rect = QtCore.QRectF(i.pos().x(), i.pos().y(),i.boundingRect().width(), i.boundingRect().height())
                if self.rubberband_rect.intersects(QtCore.QRectF(i_rect)):
                    i.screenshot_obj.select(multi_select=True)

            self.rubberband_rect = QtCore.QRectF(0.0, 0.0, 0.0, 0.0)
            super(ScreenshotsManagerWidget, self).mouseReleaseEvent(QMouseEvent)

    def mouseDoubleClickEvent(self, *args, **kwargs):
        sel = self.project.selected
        if len(sel) > 0:
            popup = ImagePreviewPopup(self, numpy_to_pixmap(sel[0].get_img_movie_orig_size()))
            self.main_window.player.set_media_time(sel[0].movie_timestamp)


class ScreenshotsManagerScene(QGraphicsScene):
    def __init__(self, graphicsViewer):
        super(ScreenshotsManagerScene, self).__init__()
        self.graphicsViewer = graphicsViewer


class ScreenshotManagerPixmapItems(QGraphicsPixmapItem):
    def __init__(self, qpixmap, manager, obj:Screenshot, selection_rect = QtCore.QRect(0,0,0,0)):
        self.screenshot_obj = obj

        super(ScreenshotManagerPixmapItems, self).__init__(self.get_qpixmap())
        self.manager = manager

        self.selection_rect = selection_rect
        self.is_selected = False

        # self.qpixmap = qpixmap
        self.screenshot_obj.onImageSet.connect(self.set_pixmap)
        self.screenshot_obj.onSelectedChanged.connect(self.on_selected_changed)

    def get_qpixmap(self):
        _, qpixmap = self.screenshot_obj.get_preview(apply_letterbox=True)
        return qpixmap

    def boundingRect(self) -> QtCore.QRectF:
        if self.get_qpixmap() is None:
            return QRectF()
        return QRectF(self.get_qpixmap().rect())

    # @pyqtSlot(object, object, object)
    def set_pixmap(self, scr=None, ndarray=None, pixmap=None):
        self.setPixmap(self.get_qpixmap())
        # self.qpixmap = pixmap

    # @pyqtSlot(bool)
    def on_selected_changed(self, state):
        self.is_selected = state
        self.update()

    def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionGraphicsItem', widget: QWidget) -> None:
        super(ScreenshotManagerPixmapItems, self).paint(painter, option, widget)
        if self.is_selected:
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(255, 160, 74, 150))
            pen.setWidth(10)
            painter.setPen(pen)
            painter.drawRect(self.get_qpixmap().rect())

    def mousePressEvent(self, *args, **kwargs):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.screenshot_obj.select(modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier)


