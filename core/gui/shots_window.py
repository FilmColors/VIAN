import os
import cv2
import numpy as np
# from PyQt4 import QtCore, QtGui, uic
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import *

from core.data.computation import *
from core.data.containers import Screenshot
from core.data.exporters import ScreenshotsExporter
from core.data.interfaces import IProjectChangeNotify
from core.gui.Dialogs.screenshot_exporter_dialog import DialogScreenshotExporter
from core.gui.ewidgetbase import EDockWidget, EToolBar


class ScreenshotsToolbar(EToolBar):
    def __init__(self, main_window, screenshot_manager):
        super(ScreenshotsToolbar, self).__init__(main_window, "Screenshots Toolbar")
        self.setWindowTitle("Screenshots")

        self.manager = screenshot_manager
        self.action_export = self.addAction(create_icon("qt_ui/icons/icon_export_screenshot.png"), "")
        self.toggle_annotation = self.addAction(create_icon("qt_ui/icons/icon_toggle_annotations.png"), "")
        self.action_export.triggered.connect(self.on_export)
        self.toggle_annotation.triggered.connect(self.on_toggle_annotations)
        self.show()

    def on_export(self):
        self.exporter_dialog = DialogScreenshotExporter( self.main_window, self.manager)
        self.exporter_dialog.show()

    def on_toggle_annotations(self):
        self.manager.toggle_annotations()


class ScreenshotsManagerDockWidget(EDockWidget):
    def __init__(self, main_window):
        super(ScreenshotsManagerDockWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Screenshot Manager")

        # self.inner.addToolBar(ScreenshotsToolbar(main_window, self.main_window.screenshots_manager))


    def set_manager(self, screenshot_manager):
        self.setWidget(screenshot_manager)


class ScreenshotsManagerWidget(QGraphicsView, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    def __init__(self,main_window, key_event_handler, parent = None):
        super(ScreenshotsManagerWidget, self).__init__(parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.SmoothPixmapTransform)

        self.is_hovered = False
        self.ctrl_is_pressed = False

        self.annotation_visible = True

        self.font = QFont("Consolas")
        self.font_size = 48
        self.font_size_segments = 120
        self.font.setPointSize(self.font_size)
        self.color = QColor(255,255,255)

        self.key_event_handler = key_event_handler

        self.setDragMode(self.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.rubberband_rect = QtCore.QRect(0, 0, 0, 0)
        self.curr_scale = 1.0

        self.main_window = main_window

        self.scene = ScreenshotsManagerScene(self)
        self.setScene(self.scene)
        self.images = []
        self.captions = []
        self.selected_images = []
        self.selection_frames = []
        self.segmentation_captions = []
        self.lines = []
        self.border = None
        self.x_offset = 100
        self.y_offset = 200
        self.border_width = 1500
        self.bottom_height = 1000


        self.n_per_row = 10

        self.n_images = 0

        self.rubberBandChanged.connect(self.rubber_band_selection)

        # SEGMENT EVALUATOR
        # self.main_window.currentSegmentChanged.connect(self.frame_segment)

    def toggle_annotations(self):
        if len(self.selected_images) == 0:
            return
        visibility = not self.selected_images[len(self.selected_images)-1].screenshot_obj.annotation_is_visible
        for sel in self.selected_images:
            sel.screenshot_obj.annotation_is_visible = visibility

        self.update_manager(center = False)

    def add_images(self, screenshots, n_per_row = 4):
        n_per_row = self.n_per_row
        font = QFont("Consolas")

        border_width = self.border_width
        x = border_width
        y = border_width

        if len(screenshots)> 0:
            self.x_offset = screenshots[0].img_movie.shape[1] / 5
            self.y_offset = screenshots[0].img_movie.shape[0] / 5


        width = 0
        height = 0
        scene_counter = 1
        n_per_segment_counter = 0
        #TODO image might be NONE
        for i, screenshot in enumerate(screenshots):
            # font.setPointSize(np.clip(self.font_size * self.transform().m11(), 5, None))
            font.setPointSize(self.font_size)

            if screenshot.annotation_is_visible and screenshot.img_blend is not None:
                image = screenshot.img_blend
            else:
                image = screenshot.img_movie

            n_per_segment_counter += 1
            try:
                qgraph, qpixmap = numpy_to_qt_image(image)
            except Exception as e:
                self.main_window.print_message("An Error Occured, Save and Restart. An Error occured in the Screenshot Manager, I suggest you restart the application" + e )
                continue

            w = qpixmap.width()
            if w > width:
                width = w
            height = qpixmap.height()
            item_image = ScreenshotManagerPixmapItems(qpixmap, self, screenshot)
            item_caption = QGraphicsTextItem()

            caption = self.create_caption_text(screenshot)
            item_caption.setPlainText(caption)
            item_caption.setDefaultTextColor(self.color)
            item_caption.setFont(font)

            self.scene.addItem(item_caption)
            self.captions.append(item_caption)

            caption_x = 0
            caption_y = qpixmap.height() + 20

            item_image.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

            item_image.moveBy(x, y)
            item_image.selection_rect = QtCore.QRect(x, y, qpixmap.width(), qpixmap.height())
            item_caption.moveBy(x + caption_x, y + caption_y)

            self.images.append(item_image)
            self.scene.addItem(item_image)

            # font.setPointSize(np.clip(self.font_size_segments * self.transform().m11(), 5, None))
            font.setPointSize(self.font_size_segments)

            if i == len(screenshots) - 1:
                segm_caption = self.scene.addText("Scene ID: " + str(screenshot.scene_id), font)
                segm_caption.setDefaultTextColor(QColor(255, 255, 255))
                segm_caption.setPos(QtCore.QPointF(border_width / 3, y))
                self.segmentation_captions.append(segm_caption)

                segm_counter = self.scene.addText(" n-Shots: " + str(n_per_segment_counter), font)
                segm_counter.setDefaultTextColor(QColor(255, 255, 255))
                segm_counter.setPos(QtCore.QPointF(border_width / 3, y + 200))
                self.segmentation_captions.append(segm_counter)
                n_per_segment_counter = 0

                break

            # If the next Screenshot is from a different Scene ID, add a spacer Line
            if screenshot.scene_id != screenshots[i+1].scene_id:
                segm_caption = self.scene.addText("Scene ID: " + str(screenshot.scene_id), font)
                segm_caption.setDefaultTextColor(QColor(255, 255, 255))
                segm_caption.setPos(QtCore.QPointF(border_width/3, y))
                self.segmentation_captions.append(segm_caption)

                segm_counter = self.scene.addText(" n-Shots: " + str(n_per_segment_counter), font)
                segm_counter.setDefaultTextColor(QColor(255, 255, 255))
                segm_counter.setPos(QtCore.QPointF(border_width / 3, y + 200))
                self.segmentation_captions.append(segm_counter)
                n_per_segment_counter = 0

                y += self.y_offset + height
                p1 = QtCore.QPointF(0, y)
                p2 = QtCore.QPointF(self.scene.sceneRect().width(), y)

                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(200, 200, 200))
                pen.setWidth(5)
                line = self.scene.addLine(QtCore.QLineF(p1, p2), pen)

                self.lines.append(line)


                scene_counter = 1
                x = border_width
                y += self.y_offset

            else:
                t = scene_counter
                if t % n_per_row == 0:
                    x = border_width
                    y += self.y_offset + height
                    scene_counter = 1
                else:
                    x += self.x_offset + width
                    scene_counter += 1

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(10, 10, 10))
        pen.setWidth(5)

        rect = self.scene.addRect(QtCore.QRectF(0, 0, n_per_row * (self.x_offset + width) + 2*border_width, y + self.y_offset + 2* self.bottom_height), pen)
        self.border = rect
        self.scene.setSceneRect(QtCore.QRectF(0, 0, n_per_row * (self.x_offset + width) + 2*border_width, y + self.y_offset + 2* self.bottom_height))

    def add_image(self, screenshot):

        if self.annotation_visible:
            image = screenshot.img_blend
        else:
            image = screenshot.img_movie

        qgraph, qpixmap = numpy_to_qt_image(image)

        item_image = ScreenshotManagerPixmapItems(qpixmap, self, screenshot)

        item_caption = QGraphicsTextItem()
        caption = self.create_caption_text(screenshot)
        item_caption.setPlainText(caption)
        item_caption.setDefaultTextColor(self.color)
        item_caption.setFont(self.font)

        self.scene.addItem(item_caption)
        self.captions.append(item_caption)

        caption_x = 0
        caption_y = qpixmap.height() + 20

        item_image.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

        if len(self.images) % 4 == 0:
            y = len(self.images) / 4 * self.y_offset
            x = 0
        else:
            y = len(self.images) / 4 * self.y_offset
            x = len(self.images) % 4 * self.x_offset

        item_image.moveBy(x,y)
        item_image.selection_rect = QtCore.QRect(x, y, qpixmap.width(), qpixmap.height())
        item_caption.moveBy(x + caption_x, y + caption_y)
        self.images.append(item_image)

        self.scene.addItem(item_image)

    def remove_image(self, image):
        print("")

    def select_image(self, images, dispatch = True):
        self.clear_selection()
        self.selected_images = images

        # Drawing the New Selection Frames
        if len(self.selected_images) > 0:
            for i in self.selected_images:

                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(255, 160, 74))
                pen.setWidth(15 * 1/self.curr_scale)
                item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(i.selection_rect))
                item.setPen(pen)
                # rect = QtCore.QRectF(i.selection_rect)
                self.selection_frames.append(item)
                self.scene.addItem(item)


        self.update()

        items = []
        if dispatch:
            for i in images:
                items.append(i.screenshot_obj)
            self.main_window.project.set_selected(self, items)

    def selected_image(self):
        return self.selected_images

    def update_manager(self, center = True):
        self.clear_caption()
        self.clear_selection()
        self.clear_images()
        self.clear_lines()
        self.images = []
        self.captions = []
        if self.main_window.project is not None:
            # self.add_images(self.main_window.project.get_screenshots())
            self.add_images(self.main_window.project.get_active_screenshots())
            if len(self.main_window.project.get_active_screenshots()) > 0:
                size = self.sceneRect().width() / self.images[0].pixmap().width() * 10
                self.font.setPixelSize(size)
                self.update_caption()

        if center:
            self.center_images()
            self.curr_scale = 1.0

        self.update_caption()

    def center_images(self):
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def enterEvent(self, *args, **kwargs):
        self.is_hovered = True
        self.focusWidget()

    def leaveEvent(self, *args, **kwargs):
        self.is_hovered = False

    def wheelEvent(self, event):
        if self.is_hovered:
            if self.key_event_handler.ctrl:
                self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
                self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

                old_pos = self.mapToScene(event.pos())
                if self.main_window.is_darwin:
                    h_factor = 1.1
                    l_factor = 0.9
                else:
                    h_factor = 1.1
                    l_factor = 0.9

                if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                    self.scale(h_factor,h_factor)
                    self.curr_scale *= h_factor
                    self.update_caption()

                elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.2:
                    self.curr_scale *= l_factor
                    self.scale(l_factor, l_factor)
                    self.update_caption()

                if len(self.images)>0:
                    viewport_width = (self.mapToScene(self.width(), self.height()) - self.mapToScene(QtCore.QPoint(0,0)))
                    self.n_per_row = np.clip(np.floor( viewport_width.x() / self.images[0].pixmap().width()), 1, None)
                    print (self.n_per_row, viewport_width.x(), self.images[0].pixmap().width())

                cursor_pos = self.mapToScene(event.pos()) - old_pos
                self.translate(cursor_pos.x(), cursor_pos.y())



            else:
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() - (500 * (float(event.angleDelta().y()) / 360)))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.UpArrowCursor))
        self.key_event_handler.pressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.key_event_handler.releaseEvent(event)

    def on_loaded(self, project):
        self.update_manager()

    def on_changed(self, project, item):
        self.update_manager()

    def on_selected(self, sender, selected):
        if not sender is self:
            sel = []
            for i in self.images:
                    for s in selected:
                        if isinstance(s, Screenshot):
                            if i.screenshot_obj is s:
                                sel.append(i)
            self.select_image(sel, dispatch=False)

    def update_caption(self):
        return
        point_size = np.clip(self.font_size * self.transform().m11(),5,None)
        self.font.setPointSize(point_size)

        s = self.main_window.project.get_active_screenshots()
        for i, c in enumerate(self.captions):

            caption = self.create_caption_text(s[i])
            c.setPlainText(caption)
            c.setFont(self.font)

    def create_caption_text(self, screenshot):
        if "No Segmentation" in str(screenshot.scene_id):
            s_id = ""
        else:
            s_id = screenshot.scene_id
        # caption = str(screenshot.title) + "\t" + str(s_id) + "\t" + str(screenshot.movie_timestamp)
        caption = str(s_id) + "\t" + str(screenshot.shot_id_segm)
        return caption

    def paintEvent(self, QPaintEvent):
        super(ScreenshotsManagerWidget, self).paintEvent(QPaintEvent)

        # #Removing all Selection Frames
        # self.clear_selection()
        # # Painting the Selection Frames
        # if len(self.selected_images) > 0:
        #     for i in self.selected_images:
        #
        #         pen = QtGui.QPen()
        #         pen.setColor(QtGui.QColor(255, 160, 74))
        #         pen.setWidth(15 * 1/self.curr_scale)
        #         item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(i.selection_rect))
        #         item.setPen(pen)
        #         # rect = QtCore.QRectF(i.selection_rect)
        #         self.selection_frames.append(item)
        #         self.scene.addItem(item)

    def rubber_band_selection(self, QRect, Union, QPointF=None, QPoint=None):
        self.rubberband_rect = self.mapToScene(QRect).boundingRect()

    def mouseReleaseEvent(self, QMouseEvent):
        selected = []
        if self.rubberband_rect.width() > 20 and self.rubberband_rect.height() > 20:
            for i in self.images:
                i_rect = QtCore.QRectF(i.pos().x(), i.pos().y(),i.boundingRect().width(), i.boundingRect().height())
                if self.rubberband_rect.intersects(QtCore.QRectF(i_rect)):
                    selected.append(i)
            self.select_image(selected)

            self.rubberband_rect = QtCore.QRectF(0.0, 0.0, 0.0, 0.0)
            super(ScreenshotsManagerWidget, self).mouseReleaseEvent(QMouseEvent)

    def export_screenshots(self, path, visibility = None, image_type = None, quality = None, naming = None, smooth = False):
        screenshots = []

        # If there are selected Screenshots, only export those,
        # Else export all
        if len(self.selected_images) == 0:
            for item in self.images:
                screenshots.append(item.screenshot_obj)
            self.main_window.print_message("No Screenshots selected, exporting all Screenshots", "red")
        else:
            for item in self.selected_images:
                screenshots.append(item.screenshot_obj)

        try:
            if not os.path.isdir(path):
                os.mkdir(path)

            exporter = ScreenshotsExporter(self.main_window.settings, self.main_window.project, naming)
            exporter.export(screenshots, path, visibility, image_type, quality, smooth)
        except OSError as e:
            QMessageBox.warning(self.main_window, "Failed to Create Directory", "Please choose a valid path\n\n" + path)
            self.main_window.print_message("Failed to Create Directory: " + path, "Red")

    def clear_selection(self):
        if len(self.selection_frames) > 0:
            for f in self.selection_frames:
                self.scene.removeItem(f)
            self.selection_frames = []

    def clear_caption(self):
        if len(self.captions) > 0:
            for f in self.captions:
                self.scene.removeItem(f)
            self.captions = []
        if len(self.segmentation_captions) > 0:
            for f in self.segmentation_captions:
                self.scene.removeItem(f)
            self.segmentation_captions = []

    def clear_images(self):
        if len(self.images) > 0:
            for f in self.images:
                self.scene.removeItem(f)
            self.images = []
            self.segment_rects = []

    def clear_lines(self):
        if self.border is not None:
            self.scene.removeItem(self.border)
            self.border = None
        if len(self.lines) > 0:
            for f in self.lines:
                self.scene.removeItem(f)
            self.lines = []

    def frame_image(self, image):
        rect = image.sceneBoundingRect()
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.curr_scale = self.sceneRect().width() / rect.width()

    # SEGMENT EVALUATOR
    # def frame_segment(self, segment_index):
    #     pos = QtCore.QPoint(0,0)
    #     scrs = self.get_project().get_screenshots_of_segment(segment_index)
    #     for i in self.images:
    #         if i.screenshot_obj in scrs:
    #             pos = i.sceneBoundingRect()
    #             self.fitInView(rect, Qt.KeepAspectRatio)
    #             break

    def get_project(self):
        return self.main_window.project




    def mouseDoubleClickEvent(self, *args, **kwargs):
        if len(self.selected_images) > 0:
            self.frame_image(self.selected_images[0])
        else:
            self.center_images()


class ScreenshotsManagerScene(QGraphicsScene):
    def __init__(self, graphicsViewer):
        super(ScreenshotsManagerScene, self).__init__()
        self.graphicsViewer = graphicsViewer


class ScreenshotManagerPixmapItems(QGraphicsPixmapItem):
    def __init__(self, qpixmap, manager, obj, selection_rect = QtCore.QRect(0,0,0,0)):
        super(ScreenshotManagerPixmapItems, self).__init__(qpixmap)
        self.manager = manager
        self.screenshot_obj = obj
        self.selection_rect = selection_rect


    def mousePressEvent(self, *args, **kwargs):
        self.setSelected(True)

        if self.manager.key_event_handler.shift:
            selected = self.manager.selected_images
            if self in selected:
                selected.remove(self)
            else:
                selected.append(self)
        else:
            selected = [self]

        self.manager.select_image(selected)
        # self.manager.main_window.screenshots_editor.set_current_screenshot(self.screenshot_obj)

