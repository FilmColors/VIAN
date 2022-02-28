from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import *

from PyQt5.QtCore import pyqtSlot
from vian.core.gui.timeline.timeline_base import TimelineBar

from vian.core.gui.context_menu import open_context_menu
from vian.core.container.project import Screenshot
from vian.core.gui.ewidgetbase import ImagePreviewPopup
from vian.core.data.computation import numpy_to_pixmap


class ScreenshotGroupBar(TimelineBar):
    def __init__(self, parent, timeline, screenshot_group, control, height=45):
        super(ScreenshotGroupBar, self).__init__(parent, timeline, control, height=45)
        self.screenshot_group = screenshot_group
        self.screenshot_group.onScreenshotAdded.connect(self.add_screenshot)
        self.screenshot_group.onScreenshotRemoved.connect(self.remove_screenshot)
        # self.screenshots = dict([(s.unique_id, s) for s in screenshot_group.screenshots])
        self.pictures = dict()
        self.timeline = timeline

        for s in screenshot_group.screenshots:
            self.add_screenshot(s)
        self.show()

    def add_screenshot(self, scr):
        if scr.unique_id not in self.pictures:
            pic = TimebarPicture(self, scr, self.timeline)
            self.onHeightChanged.connect(pic.on_height_changed)
            pic.move(int(round(scr.get_start() / self.timeline.scale,0)), 0)
            self.pictures[scr.unique_id] = pic

    def remove_screenshot(self, scr):
        if scr.unique_id in self.pictures:
            self.pictures[scr.unique_id].close()

    def rescale(self):
        for s in self.pictures.keys():
            pic = self.pictures[s]
            pic.move(int(round(pic.item.get_start() / self.timeline.scale, 0)), 0)


class TimebarPicture(QtWidgets.QWidget):
    def __init__(self, parent, screenshot:Screenshot, timeline, height = 43):
        super(TimebarPicture, self).__init__(parent)
        self.item = screenshot
        self.item.onImageSet.connect(self.on_image_set)
        self.timeline = timeline
        self.has_classification = len(self.item.tag_keywords)
        self.item.onClassificationChanged.connect(self.on_classification_changed)

        self.is_hovered = False
        self.is_selected = False

        self.item.onSelectedChanged.connect(self.on_selected_changed)
        self.color = (123, 86, 32, 100)
        self.pic_height = height
        self.size = (screenshot.get_img_movie(ignore_cl_obj = True).shape[0],
                     screenshot.get_img_movie(ignore_cl_obj = True).shape[1])
        width = self.size[1] * self.pic_height // self.size[0]
        self.img_rect = QtCore.QRect(1, 1, width, self.pic_height)
        self.resize(width, self.pic_height)
        self.show()

    @pyqtSlot(bool)
    def on_selected_changed(self, state):
        self.is_selected = state
        self.update()

    @pyqtSlot(object, object, object)
    def on_image_set(self, screenshot, ndarray, pixmap):
        print("Received")
        self.update()

    def on_height_changed(self, height):
        self.pic_height = height
        width = self.size[1] * self.pic_height // self.size[0]
        self.resize(width, self.pic_height)
        self.img_rect = QtCore.QRect(1, 1, width, self.pic_height)

    @pyqtSlot(object)
    def on_classification_changed(self, keywords):
        self.has_classification = len(keywords) > 0
        self.update()

    def paintEvent(self, QPaintEvent):
        if self.is_hovered or self.is_selected:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 200)
            w  = 7
        else:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 50)
            w = 3

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(col)
        pen.setWidth(w)
        qp.setPen(pen)

        qimage, _ = self.item.get_preview(apply_letterbox=True)

        qp.drawImage(self.img_rect, qimage)
        qp.drawRect(self.img_rect)

        if self.has_classification:
            pen.setColor(QtGui.QColor(0, 255, 0))
            qp.setPen(pen)
            qp.drawEllipse(QRectF(self.width() - 10, 5, 5, 5))
        qp.end()

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            self.item.select(multi_select=modifiers == QtCore.Qt.ShiftModifier)

        if QMouseEvent.buttons() & Qt.RightButton:
            open_context_menu(self.timeline.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())

    def enterEvent(self, QEvent):
        self.is_hovered = True
        self.raise_()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent):
        preview = ImagePreviewPopup(self.timeline.main_window, numpy_to_pixmap(self.item.get_img_movie_orig_size()))
        preview.show()
        self.timeline.set_current_time(self.item.movie_timestamp)

    def leaveEvent(self, QEvent):
        self.is_hovered = False
        self.lower()