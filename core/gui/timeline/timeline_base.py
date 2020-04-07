from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from core.data.interfaces import TimelineDataset
from core.container.project import *
from core.container.container_interfaces import ILockable
from core.gui.context_menu import open_context_menu
from core.gui.ewidgetbase import TextEditPopup


class TimelineControl(QtWidgets.QWidget):
    onHeightChanged = pyqtSignal(int)
    onClassificationToggle = pyqtSignal(bool)
    onPinned = pyqtSignal(bool, object)

    def __init__(self, parent, timeline, item = None, name = "No Name"):
        super(TimelineControl, self).__init__(parent)
        self.timeline =  timeline
        self.item = item

        self.h_exp = 300
        self.h_col = 100
        self.name = name
        self.groups = []

        self.sub_segmentations = [] # type:List[TimelineSubSegmentation]

        self.setMouseTracking(True)
        self.is_selected = False
        self.bar = None

        self.size_grip_hovered = False
        self.is_resizing = False
        self.is_pinned = False

        self.resize_offset = 0
        self.show()
        self.group_height = self.timeline.group_height

        self.setLayout(QGridLayout(self))
        self.layout().setSpacing(2)
        self.lbl_title = QLabel(self)
        self.lbl_title.setStyleSheet("QWidget{background:transparent; margin:0pt;}")
        self.lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout().addWidget(self.lbl_title,0, 1, 1, 3)

        self.btn_pin = QPushButton(create_icon("qt_ui/icons/icon_pin.png"), "", self)
        self.btn_pin.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.btn_pin.setStyleSheet("QWidget{background:transparent; border-radius:5px;}")
        self.layout().addWidget(self.btn_pin, 0, 0)

        self.btn_pin.clicked.connect(self.toggle_pin)

        self.expand = QSpacerItem(1,1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        self.bottom_line = None
        self.btn_lock = None
        self.text_loc = (5, 5)

        self.show_classification = False
        self.set_name()
        self._add_spacer()

        if self.item.strip_height == -1:
            self.resize(self.width(), 45)
        else:
            self.resize(self.width(), self.item.strip_height)

        if not isinstance(self.item, TimelineDataset):
            self.item.onSelectedChanged.connect(self.on_selected_changed)

    def _add_spacer(self):
        # self.bottom_line = QWidget(self)
        # self.bottom_line.setStyleSheet("QWidget{padding:1px; margin:0pt; background:transparent;}")
        # self.bottom_line.setLayout(QHBoxLayout())
        # self.bottom_line.layout().setSpacing(0)

        if isinstance(self.item, ILockable):
            self.btn_lock = QPushButton(create_icon("qt_ui/icons/icon_locked2.png"), "", self)
            self.btn_lock.setStyleSheet("QWidget{background:transparent; border-radius:5px;}")
            self.btn_lock.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            self.layout().addWidget(self.btn_lock,1,0,1,1)

            if self.item.is_locked():
                self.btn_lock.setIcon(create_icon("qt_ui/icons/icon_locked2.png"))
            else:
                self.btn_lock.setIcon(create_icon("qt_ui/icons/icon_lock_green.png"))
            self.btn_lock.clicked.connect(self.toggle_lock)

        if isinstance(self.item, Segmentation):
            self.btn_classification = QPushButton(create_icon("qt_ui/icons/icon_classification"), "", self)
            self.btn_classification.setStyleSheet("QWidget{background:transparent; border-radius:5px;}")
            self.btn_classification.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            self.layout().addWidget(self.btn_classification,1,1,1,1)
            self.btn_classification.clicked.connect(self.toggle_classification)

        self.layout().addItem(self.expand,2,0)


    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.btn_pin.setIcon(create_icon("qt_ui/icons/icon_pin_on.png"))
        else:
            self.btn_pin.setIcon(create_icon("qt_ui/icons/icon_pin.png"))
        self.onPinned.emit(self.is_pinned, self)

    def set_pinned(self, state):
        self.is_pinned = state
        if self.is_pinned:
            self.btn_pin.setIcon(create_icon("qt_ui/icons/icon_pin_on.png"))
        else:
            self.btn_pin.setIcon(create_icon("qt_ui/icons/icon_pin.png"))

    def toggle_lock(self):
        if isinstance(self.item, ILockable):

            if self.item.is_locked():
                self.item.unlock()
                self.btn_lock.setIcon(create_icon("qt_ui/icons/icon_lock_green.png"))
            else:
                self.item.lock()
                self.btn_lock.setIcon(create_icon("qt_ui/icons/icon_locked2.png"))

    def toggle_classification(self):
        self.show_classification = not self.show_classification
        self.onClassificationToggle.emit(self.show_classification)
        self.timeline.update_ui()

    @pyqtSlot(bool)
    def on_selected_changed(self, state):
        self.is_selected = state
        self.timeline.selected = self.item
        if self.bar is not None:
            self.bar.is_selected = state
            self.bar.update()
        self.update()

    def set_name(self):
        if self.item is not None:
            self.name = self.item.get_name()
            self.lbl_title.setText(self.name)

    def update_info(self, layer):
        self.set_name()

    def add_sub_segmentation(self, s):
        self.sub_segmentations.append(s)

    def get_sub_segmentation_height(self):
        h = 0
        for s in self.sub_segmentations:
            if s.is_expanded is False:
                continue
            h += len(s) * s.strip_height
        return h

    def add_group(self, annotation):
        y = len(self.groups) * self.timeline.group_height
        text = annotation.get_name()
        self.groups.append([annotation, text])
        self.update_strip_height()

    def update_strip_height(self):
        self.timeline.update_ui()
        if len(self.groups) > 0:
            self.onHeightChanged.emit((self.height() - self.timeline.group_height) / len(self.groups))
        else:
            self.onHeightChanged.emit(self.height())

        self.item.strip_height = self.height() - self.timeline.group_height
        self.group_height = self.item.strip_height / np.clip(len(self.groups), 1, None)
        self.update()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent):
        if self.is_resizing:
            if not a0.pos().y() + self.resize_offset < self.timeline.bar_height_min:
                self.resize(self.width(), a0.pos().y() + self.resize_offset)
                self.update_strip_height()
        else:
            if a0.pos().y() > self.height() - 15:
                self.size_grip_hovered = True
            else:
                self.size_grip_hovered = False
            self.update()
            super(TimelineControl, self).mouseMoveEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent):
        self.size_grip_hovered = False
        super(TimelineControl, self).leaveEvent(a0)

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if QMouseEvent.pos().y() > self.height() - 15:
                self.is_resizing = True
                self.resize_offset = self.height() - QMouseEvent.pos().y()
            else:
                if not isinstance(self.item, TimelineDataset):
                    self.item.select()
                # self.timeline.select(self)

        if QMouseEvent.button() == Qt.RightButton:
            context = open_context_menu(self.timeline.main_window,self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())
            context.show()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent):
        self.is_resizing = False

    def paintEvent(self, QPaintEvent):
        super(TimelineControl, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255, 50))
        pen.setWidth(1)
        qp.setPen(pen)

        if self.is_pinned:
            qp.fillRect(self.rect(), QColor(17,17,17))

        for i,a in enumerate(self.groups):
            y = i * self.group_height + self.timeline.group_height
            if i == 0:
                p1 = QtCore.QPoint(self.x(), y)
                p2 = QtCore.QPoint(self.width(), y)
                qp.drawLine(p1, p2)

            p1 = QtCore.QPoint(self.x(), y + self.group_height)
            p2 = QtCore.QPoint(self.width(), y + self.group_height)
            qp.drawLine(p1, p2)

        pen.setColor(QtGui.QColor(255, 255, 255, 200))
        qp.setPen(pen)

        if self.is_selected:
            # qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QtGui.QColor(200, 200, 255, 50))
            qp.fillRect(self.rect(), QtGui.QColor(200, 200, 255, 50))
        else:
            gradient = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
            gradient.setColorAt(0.0, QColor(50, 50, 50))
            gradient.setColorAt(0.5, QColor(65, 65, 65))
            gradient.setColorAt(1.0, QColor(50, 50, 50))
            gradient.setSpread(QGradient.PadSpread)
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), gradient)

        for i, a in enumerate(self.groups):
            y = i * self.group_height + self.timeline.group_height
            text_rect = QtCore.QRect(0, y, self.width(), self.group_height)
            qp.drawText(text_rect, Qt.AlignRight|Qt.AlignVCenter, a[1])

        pen.setColor(QtGui.QColor(255, 255, 255, 255))
        qp.setPen(pen)
        qp.drawLine(QtCore.QPoint(0,0), QtCore.QPoint(self.width(), 0))

        # Title of the Control
        # qp.drawText(QRect(self.text_loc[0], self.text_loc[1], self.width(), 25), Qt.AlignVCenter | Qt.AlignLeft, self.name)

        if isinstance(self.item, ILockable):
            if self.item.is_locked():
                qp.drawPixmap(QtCore.QRect(self.width() - 20, 9, 16, 16), QPixmap("qt_ui/icons/icon_locked.png"))
        if isinstance(self.item, AnnotationLayer):
            if self.item.is_visible == False:
                qp.drawPixmap(QtCore.QRect(self.width() - 40, 9, 16, 16), QPixmap("qt_ui/icons/icon_hidden.png"))
        # qp.drawLine(QtCore.QPoint(0, self.height()), QtCore.QPoint(self.width(), self.height()))
        if self.size_grip_hovered:
            pen.setColor(QtGui.QColor(164, 7, 0, 200))
            pen.setWidth(4)
            qp.setPen(pen)
            qp.drawLine(0, self.height() - 2, self.width(), self.height() - 2)
        qp.end()


class TimelineBar(QtWidgets.QFrame):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, height = 45):
        super(TimelineBar, self).__init__(parent)
        self.resize(parent.width(), height)
        self.timeline = timeline
        self.orig_height = height
        self.setMouseTracking(True)
        self.control = control
        self.control.bar = self
        self.control.onHeightChanged.connect(self.on_height_changed)
        self.is_selected = False

        self.setFrameStyle(QFrame.Box)

        self.slices = []
        self.slices_index = dict()
        self.annotations = []
        self.show()

    def add_annotation(self, annotation, keys):
        y = len(self.annotations) * self.timeline.group_height + self.timeline.group_height
        tb_keys = []
        for i, k in enumerate(keys):
            tb_key = TimebarKey(self, annotation, i)
            tb_key.move(k[0] // self.timeline.scale, y + 2.5)
            tb_key.resize(10, 10)
            tb_keys.append(tb_key)
            tb_key.show()
        self.annotations.append([annotation, tb_keys])

    @pyqtSlot(int)
    def on_height_changed(self, height):
        """
        This is called when the User drags the size handle into one direction in the control widget,
        usually it does not have to be used since the resizing is done in the timeline update_ui() directly.
        Screenshots override it to resize the pixmaps as well
        :param height:
        :return:
        """
        self.onHeightChanged.emit(height)

    def add_slice(self, item):
        slice = TimebarSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        item.onQueryHighlightChanged.connect(slice.set_query_highlighted)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice

    def remove_slice(self, item):
        if item.get_id() in self.slices_index:
            itm = self.slices_index[item.get_id()]
            self.slices.remove(itm)
            self.slices_index.pop(item.get_id())
            itm.close()

    def get_previous_slice(self, slice):
        result = None
        self.slices = sorted(self.slices, key=lambda x: x.pos().x())
        for s in self.slices:
            if s.pos().x() < slice.pos().x():
                result = s
            else:
                break

        return result

    def get_next_slice(self, slice):
        result = None
        self.slices = sorted(self.slices, key=lambda x: x.pos().x())
        for s in self.slices:
            if s.pos().x() > slice.pos().x():
                if result is None:
                    result = s
                else:
                    if result.pos().x() > s.pos().x():
                        result = s

        return result

    def rescale(self):
        for a in self.annotations:
            for k in a[1]:
                k.move(a[0].keys[k.key_index][0] // self.timeline.scale, k.y())

        for s in self.slices:
            s.move(int(round(s.item.get_start() / self.timeline.scale, 0)), 0)
            s.resize(int(round((s.item.get_end() - s.item.get_start()) / self.timeline.scale, 0)), self.height() / 2)

    def paintEvent(self, QPaintEvent):
        # super(TimelineBar, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(20, 20, 20, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        for i,a in enumerate(self.annotations):
            if i == 0:
                y = i * self.timeline.group_height + self.timeline.group_height
                p1 = QtCore.QPoint(self.x(), y)
                p2 = QtCore.QPoint(self.width(), y)
                qp.drawLine(p1, p2)
            y = i * self.timeline.group_height + self.timeline.group_height + self.timeline.group_height
            p1 = QtCore.QPoint(self.x(), y)
            p2 = QtCore.QPoint(self.width(), y)
            qp.drawLine(p1, p2)

        pen.setColor(QtGui.QColor(200, 200, 200, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        qp.drawRect(self.rect())
        if self.is_selected:
            qp.fillRect(self.rect(), QtGui.QColor(255, 255, 255, 50))
        qp.end()

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self.timeline.project() is not None:
            self.timeline.project().set_selected(self.timeline, [])


class TimebarSlice(QtWidgets.QWidget):
    def __init__(self, parent:TimelineBar, item, timeline, color = (232, 174, 12, 100)):
        super(TimebarSlice, self).__init__(parent)
        self.bar = parent
        self.locked = False
        self.timeline = timeline
        self.item = item

        self.show()
        self.mode = "center"
        self.setMouseTracking(True)
        self.border_width = 15
        self.offset = QtCore.QPoint(0,0)
        self.text = ""
        self.curr_pos = self.pos()
        self.curr_size = self.size()

        self.item.onSelectedChanged.connect(self.on_selected_changed)
        self.item.onClassificationChanged.connect(self.on_classification_changed)

        self.has_classification = len(self.item.tag_keywords) > 0

        self.update_text()

        self.color = color
        self.text_size = 10

        self.is_hovered = False
        self.is_selected = False

        self.media_object_items = []

        if isinstance(item, IHasMediaObject):
            self.setAcceptDrops(True)
            self.item.onMediaAdded.connect(self.on_media_objects_changed)
            self.item.onMediaRemoved.connect(self.on_media_objects_changed)

        self.merge_highlighted = False
        self.query_highlighted = False
        self.sticky_highlighted = False

        self.col_merge_highlighted = (255, 160, 47, 200)
        self.col_query_highlighted = (63, 200, 229, 200)
        self.col_sticky_highlighted = (195,38,123, 200)
        self.col_cutting = (180,0,0, 200)
        self.col_hovered = (232, 174, 12, 150)
        self.col_selected = (self.color[0], self.color[1], self.color[2], 150)

        self.min_possible = 0
        self.max_possible = self.timeline.duration * self.timeline.scale

        self.previous_slice = None
        self.next_slice = None
        self.on_media_objects_changed()

    @pyqtSlot(bool)
    def on_selected_changed(self, state):
        self.is_selected = state
        self.update()

    @pyqtSlot(object)
    def on_media_objects_changed(self, obj=None):
        if not isinstance(self.item, IHasMediaObject):
            return
        x = self.width() - 30
        for obj in self.media_object_items:
            obj.deleteLater()
        self.media_object_items = []

        for obj in self.item.media_objects:
            itm = MediaObjectWidget(self, obj)
            itm.resize(25, 25)
            itm.move(x, 5)
            if x > 50:
                itm.show()
            else:
                itm.hide()
            self.media_object_items.append(itm)
            x -= 30
        self.update()

    def set_color(self):
        pass

    def set_query_highlighted(self, state):
        self.query_highlighted = state
        self.update()

    def paintEvent(self, QPaintEvent):
        self.locked = False
        if isinstance(self.item, ILockable):
            self.locked = self.item.is_locked()

        if self.locked :
            col = (self.color[0], self.color[1], self.color[2], 20)

        else:
            if self.merge_highlighted:
                col = self.col_merge_highlighted

            elif self.query_highlighted:
                col = self.col_query_highlighted

            elif self.sticky_highlighted:
                col = self.col_sticky_highlighted

            elif self.is_hovered:
                if self.timeline.is_cutting:
                    col = self.col_cutting
                else:
                    if self.is_selected:
                        col = (self.col_hovered[0], self.col_hovered[1], self.col_hovered[2], 230)
                    else:
                        col = (self.col_hovered[0], self.col_hovered[1], self.col_hovered[2], 150)

            elif self.is_selected:
                col = self.col_selected

            else:
                col = (self.color[0], self.color[1], self.color[2], 50)

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)

        # col = QtGui.QColor(col[0], col[1], col[2], col[3])
        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
        gradient.setColorAt(0.0, QColor(col[0] - 20, col[1] - 20, col[2] - 20, col[3] - 20))
        gradient.setColorAt(0.5, QColor(col[0], col[1], col[2], col[3]))
        gradient.setColorAt(1.0, QColor(col[0] - 20, col[1] - 20, col[2] - 20, col[3]  - 20))
        gradient.setSpread(QGradient.PadSpread)

        pen.setColor(QColor(col[0], col[1], col[2], 150))
        qp.setPen(pen)
        qp.drawRect(QtCore.QRect(0, 0, self.width(), self.height()))
        qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), gradient)

        pen.setColor(QtGui.QColor(255, 255, 255))
        qp.setPen(pen)
        qp.drawText(5, (self.height() + self.text_size) // 2, self.text)

        if self.has_classification:
            pen.setColor(QtGui.QColor(240,206,0))
            qp.setPen(pen)
            qp.drawEllipse(QRectF(self.width() - 10,5,5,5))

        pen.setColor(QtGui.QColor(255, 255, 255))
        x = self.width() - 60
        y = self.height() / 2 - (25 / 2)
        can_show_all_media = True
        for m in self.media_object_items:
            m.move(x, int(y))
            if x > 50:
                m.show()
            else:
                m.hide()
                can_show_all_media = False
            x -= 30
        if not can_show_all_media:
            pen.setColor(QtGui.QColor(178,41,41) )
            qp.setPen(pen)
            qp.drawEllipse(QRect(self.width() - 10, self.height() - 10, 5, 5))

        qp.end()

    def update_text(self):
        self.text = ""
        if self.item.get_type() == SEGMENT:
            if self.timeline.show_id:
                self.text += "ID: " +  str(self.item.ID).ljust(5)
            if self.timeline.show_name:
                self.text += "Name: " +  str(self.item.get_name()) + "\t"
            if self.timeline.show_text:
                self.text += "Text: " + str(self.item.get_annotation_body())

            self.setToolTip("<FONT>" + self.item.get_annotation_body() + "</FONT>")
        else:
            self.text = str(self.item.get_name())

        self.update()

    def mousePressEvent(self, QMouseEvent):
        if not self.locked:
            if QMouseEvent.buttons() & Qt.LeftButton:
                if self.timeline.is_cutting:
                    return

                elif self.timeline.is_merging:
                    self.timeline.finish_merge_tool()

                else:
                    # Inhibiting Overlap by finding the surrounding Slices and get their boundaries
                    if self.timeline.inhibit_overlap:
                        previous = self.parent().get_previous_slice(self)
                        next = self.parent().get_next_slice(self)

                        if previous is not None:
                            self.min_possible = previous.pos().x() + previous.width()
                            self.previous_slice = previous
                        else:
                            self.min_possible = 0
                        if next is not None:
                            self.max_possible = next.pos().x()
                            self.next_slice = next
                        else:
                            self.max_possible = self.timeline.duration * self.timeline.scale

                    self.is_selected = True

                    modifiers = QtWidgets.QApplication.keyboardModifiers()
                    self.item.select(multi_select=modifiers == QtCore.Qt.ShiftModifier)

                    # self.timeline.project().set_selected(None, self.item)
                    self.offset = self.mapToParent(QMouseEvent.pos())
                    self.curr_size = self.size()
                    self.curr_pos = self.pos()
                # self.timeline.update()

            if QMouseEvent.buttons() & Qt.RightButton:
                if self.timeline.is_cutting:
                    self.timeline.abort_cutting()
                elif self.timeline.is_merging:
                    self.timeline.abort_merge_tool()
                else:
                    open_context_menu(self.timeline.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.item], self.timeline.project())

    def mouseReleaseEvent(self, QMouseEvent):
        # if the the movement is smaller than the grid-size ignore it
        if not self.locked:

            if self.timeline.is_cutting:
                self.timeline.finish_cutting_tool(self.mapToParent(QMouseEvent.pos()), self.item)
                return

            # if the Move was smaller than the Settings.Grid_SIZE, undo the movement
            else:
                if self.timeline.settings.USE_GRID:
                    if np.abs(self.pos().x() * self.timeline.scale - self.item.get_start()) < self.timeline.settings.GRID_SIZE and \
                         np.abs(self.width() * self.timeline.scale - (self.item.get_end() - self.item.get_start())) < self.timeline.settings.GRID_SIZE:
                        self.move(int(round(self.item.get_start() / self.timeline.scale, 0)), 0)
                        self.resize(int(round((self.item.get_end() - self.item.get_start()) / self.timeline.scale, 0)), self.height())
                        return

                if self.mode == "center":
                    self.item.move(int(round(self.pos().x() * self.timeline.scale, 0)), int(round((self.pos().x() + self.width()) * self.timeline.scale,0)))
                    return
                if self.mode == "left":
                    self.item.set_start(int(round((self.pos().x() * self.timeline.scale),0)))
                    if self.timeline.sticky_move and self.previous_slice is not None:
                        self.previous_slice.item.set_end(int(round((self.pos().x() * self.timeline.scale),0)))
                        self.previous_slice.sticky_highlighted = False

                    return

                if self.mode == "right":
                    self.item.set_end(int(round(((self.pos().x() + self.width()) * self.timeline.scale),0)))
                    if self.timeline.sticky_move and self.next_slice is not None:
                        self.next_slice.item.set_start(int(round(((self.pos().x() + self.width()) * self.timeline.scale),0)))
                        self.next_slice.sticky_highlighted = False
                    return

    @pyqtSlot(object)
    def on_classification_changed(self, keywords):
        self.has_classification = len(keywords) > 0
        self.update()

    @pyqtSlot(int)
    def on_height_changed(self, int_height):
        self.resize(self.width(), int_height)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent):
        a0.acceptProposedAction()

    def dropEvent(self, a0: QtGui.QDropEvent):
        self.item.project.create_media_object("New Object",
                                                    a0.mimeData().urls()[0].toLocalFile(),
                                                    self.item)
        self.update()

    def enterEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = True

    def leaveEvent(self, QEvent):
        if not self.locked:
            self.is_hovered = False

    def mouseMoveEvent(self, QMouseEvent):
        if not self.locked:
            if self.timeline.is_cutting:
                self.timeline.move_cutting_tool(QPoint(self.mapToParent(QMouseEvent.pos()).x(), 0))
            elif self.timeline.is_merging:
                if QMouseEvent.pos().x() < self.width() / 2:
                    self.timeline.set_merge_containers(self.bar.get_previous_slice(self), self)
                else:
                    self.timeline.set_merge_containers(self, self.bar.get_next_slice(self))

                self.timeline.move_merge_tool(QPoint(self.mapToParent(QMouseEvent.pos()).x(), 0))

            elif QMouseEvent.buttons() & Qt.LeftButton:
                pos = self.mapToParent(QMouseEvent.pos())
                target = pos - self.offset
                tx = int(self.timeline.round_to_grid(target.x()))
                ty = int(self.timeline.round_to_grid(target.y()))
                target = QtCore.QPoint(int(tx), int(ty))

                if self.mode == "right":
                    if self.timeline.sticky_move:
                        x = np.clip(self.curr_size.width() + target.x(), self.curr_pos.x() - self.offset.x() + 5, None)
                    elif self.timeline.inhibit_overlap:
                        x = np.clip(self.curr_size.width() + target.x(), self.curr_pos.x() - self.offset.x() + 5, self.max_possible - self.curr_pos.x())
                    else:
                        x = np.clip(self.curr_size.width() + target.x(), self.curr_pos.x() - self.offset.x() + 5, None)

                    old_width = self.width()
                    self.resize(x, self.height())
                    if self.timeline.sticky_move and self.next_slice is not None:
                        offset = self.next_slice.x() - (self.x() + old_width)
                        next_x = self.x() + self.width() + offset
                        next_width = old_width + self.next_slice.width() - ((next_x - offset) - self.x())
                        self.next_slice.move(next_x, 0)
                        self.next_slice.resize(next_width, self.height())
                        self.next_slice.sticky_highlighted = True
                    self.update()

                    time = (self.pos().x() + self.width()) * self.timeline.scale
                    self.timeline.main_window.player.set_media_time(time)
                    return

                if self.mode == "left":
                    if self.timeline.sticky_move:
                        x = np.clip(self.curr_pos.x() + target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())
                        w = np.clip(self.curr_size.width() - target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())
                    elif self.timeline.inhibit_overlap:
                        x = np.clip(self.curr_pos.x() + target.x(), a_min=self.min_possible, a_max=self.curr_pos.x() + self.curr_size.width())
                        # w = np.clip(self.curr_size.width() - target.x(), a_min=0, a_max=self.curr_pos.x() + self.curr_size.width())
                        w = np.clip(self.curr_size.width() - target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())

                    else:
                        x = np.clip(self.curr_pos.x() + target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())
                        w = np.clip(self.curr_size.width() - target.x(), a_min=0,
                                    a_max=self.curr_pos.x() + self.curr_size.width())

                    old_width = self.width()
                    if self.pos().x() != x:
                        self.move(x, 0)
                        self.resize(w, self.height())

                    if self.timeline.sticky_move and self.previous_slice is not None:
                        new_width = self.previous_slice.width() + old_width - self.width()
                        self.previous_slice.resize(new_width, self.previous_slice.height())
                        self.previous_slice.sticky_highlighted = True

                    self.update()

                    time = (self.pos().x()) * self.timeline.scale
                    self.timeline.main_window.player.set_media_time(time)
                    return

                if self.mode == "center":
                    if self.timeline.inhibit_overlap:
                        x1 = np.clip(self.curr_pos.x() + target.x() + self.width(), self.min_possible, self.max_possible - self.width())
                        x2 = np.clip(self.curr_pos.x() + target.x(), self.min_possible, None)
                        if x2 < x1:
                            x = x2
                        else:
                            x = x1

                    else:
                        x = np.clip(self.curr_pos.x() + target.x(), 0, self.parent().width() - self.width())

                    self.move(x, 0)
                    self.update()
                    return

            else:
                # Moving the Left Sid
                if  self.mapFromGlobal(self.cursor().pos()).x() < self.border_width:
                    self.mode = "left"
                    self.setCursor(QtGui.QCursor(Qt.SizeHorCursor))
                    return

                # Moving the Right Side
                if  self.mapFromGlobal(self.cursor().pos()).x() > self.width() - self.border_width:
                    self.mode = "right"
                    self.setCursor(QtGui.QCursor(Qt.SizeHorCursor))
                    return

                # Moving the whole widget
                if self.border_width <= self.mapFromGlobal(self.cursor().pos()).x() <= self.width() - self.border_width:
                    self.mode = "center"
                    self.setCursor(QtGui.QCursor(Qt.SizeAllCursor))
                    return
                else:
                    self.setCursor(QtGui.QCursor(Qt.ArrowCursor))

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent):
        if self.item.get_type() == SEGMENT:
            popup = TextEditPopup(self, self.item.set_annotation_body, self.mapToGlobal(a0.pos()), text=self.item.get_annotation_body())


class MediaObjectWidget(QWidget):
    def __init__(self, parent, media_object):
        super(MediaObjectWidget, self).__init__(parent)
        self.media_object = media_object
        self.hovered = False
        self.setToolTip("Open: " + str(self.media_object.name))

    def enterEvent(self, a0: QtCore.QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QtCore.QEvent):
        self.hovered = False

    def paintEvent(self, QPaintEvent):
        col = [5, 175, 242, 1]
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)

        pen.setColor(QColor(col[0], col[1], col[2], 150))
        if self.hovered:
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QColor(col[0], col[1], col[2], 200))
        else:
            qp.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), QColor(col[0], col[1], col[2], col[3]))

        if self.media_object.dtype == MediaObjectType.PDF:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_pdf.png"))
        elif self.media_object.dtype == MediaObjectType.IMAGE:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_image_media.png"))
        elif self.media_object.dtype == MediaObjectType.EXTERNAL:
            qp.drawPixmap(QRect(0, 0, 25, 25), QPixmap("qt_ui/icons/icon_external_media.png"))

        qp.end()

    def mousePressEvent(self, a0: QtGui.QMouseEvent):
        if a0.button() == Qt.LeftButton:
            self.media_object.preview()
        elif a0.button() == Qt.RightButton:
            open_context_menu(self.parent().timeline.main_window, self.mapToGlobal(a0.pos()),
                              [self.media_object], self.media_object.project)


class TimebarKey(QtWidgets.QWidget):
    def __init__(self, parent, annotation, key_index):
        super(TimebarKey, self).__init__(parent)
        self.annotation = annotation
        self.key_index = key_index
        self.color = (255,0,0)
        self.is_hovered = False

    def paintEvent(self, QPaintEvent):
        if self.is_hovered:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 100)
        else:
            col = QtGui.QColor(self.color[0], self.color[1], self.color[2], 50)

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        qp.setPen(pen)
        path = QtGui.QPainterPath()
        path.addEllipse(QtCore.QRectF(self.rect()))
        qp.fillPath(path, col)
        qp.end()

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False


class TimelineScrubber(QtWidgets.QWidget):
    def __init__(self, parent, player, timeline):
        super(TimelineScrubber, self).__init__(parent)
        r = parent.rect()
        self.timeline = timeline
        self.player = player
        self.resize(10, r.height())
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.is_hovered = False
        self.was_playing = False
        self.offset = 0

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.timeline.set_time_indicator_visibility(True)
            self.was_playing = self.player.is_playing()
            self.player.pause()
            self.timeline.main_window.update_timer.stop()
            self.offset = self.mapToParent(QMouseEvent.pos())
            self.curr_pos = self.pos()

        else:
            # QMouseEvent.ignore()
            self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
        #     # self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
        #
        #
        # # if QMouseEvent.buttons() & Qt.RightButton:
        # #     self.timeline.mousePressEvent(QMouseEvent)

    def mouseReleaseEvent(self, QMouseEvent):
        self.timeline.set_time_indicator_visibility(False)
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.was_playing:
                self.player.play()
                self.was_playing = False
        else:
            QMouseEvent.ignore()
            # self.timeline.end_selector()
            # QMouseEvent.ignore()
            # self.timeline.end_selector()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            pos = self.mapToParent(QMouseEvent.pos())# - self.offset
            self.timeline.move_scrubber(pos.x() - self.width()/2)
            # self.move(self.curr_pos.x() + pos.x() + 5, 0)
            # self.player.set_media_time((self.curr_pos.x() + pos.x() + 5) * self.timeline.scale)

        if QMouseEvent.buttons() & Qt.RightButton:
            if self.timeline.selector is not None:
                self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))
            else:
                pos = self.mapToParent(QMouseEvent.pos()).x()
                self.timeline.move_scrubber(pos - self.width()/2)
                # self.timeline.time_scrubber.move(pos, 0)
                # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
            # QMouseEvent.ignore()

    def paintEvent(self, QPaintEvent):
        self.raise_()
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 0, 0))
        pen.setWidth(2)
        qp.setPen(pen)
        a = QtCore.QPoint(5, 0)
        b = QtCore.QPoint(5, self.height())
        qp.drawLine(a,b)
        if self.is_hovered:
            qp.fillRect(self.rect(),QtGui.QColor(255, 255, 255, 50))
        else:
            qp.fillRect(self.rect(), QtGui.QColor(255, 255, 255, 1))
        qp.end()


class TimelineTimemark(QtWidgets.QWidget):
    def __init__(self, parent, color = QColor(255,255,255,50)):
        super(TimelineTimemark, self).__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.color = color
        self.setFixedWidth(5)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.show()

    def paintEvent(self, a0: QtGui.QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)

        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(self.color)
        pen.setWidth(3)
        qp.setPen(pen)

        a = QtCore.QPoint(3, 0)
        b = QtCore.QPoint(3, self.height())
        qp.drawLine(a, b)

        qp.end()

    def move(self, a0: QtCore.QPoint):
        pos = QPoint(a0.x() - 3, a0.y())
        super(TimelineTimemark, self).move(pos)