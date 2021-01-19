from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QPoint, QPointF, QRect, QRectF, Qt
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSpacerItem
from PyQt5.QtGui import QLinearGradient, QColor, QGradient, QPixmap

from PyQt5 import QtGui, QtWidgets, QtCore

from .timeline_base import TimelineControl, TimebarSlice, TimelineBar
from core.container.project import Segmentation, UniqueKeyword, Segment, AnnotationBody
import numpy as np
from functools import partial
from core.gui.annotation_editor import AnnotationEditorPopup
from core.gui.ewidgetbase import TextEditPopup


class TimelineSubSegmentationEntry:
    TYPE_BINARY  = 0

    def __init__(self, name, mode= TYPE_BINARY, mime_data = None):
        self.name = name
        self.mode = mode
        self.mime_data = mime_data

        self.slices = []
        self.strip = None


class TimelineSubSegmentation:
    def __init__(self, name):
        self.name = name
        self.entries = []

        self.strip_height = 30
        self.is_expanded = False

        self.control = None

    def get_name(self):
        return self.name

    def add_entry(self, e:TimelineSubSegmentationEntry):
        self.entries.append(e)

    def __len__(self):
        return len(self.entries)


class TimelineControlParent(QWidget):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, children = None, name="Global"):
        super(TimelineControlParent, self).__init__(parent)
        self.children = children
        self.name = name
        self.is_expanded = False
        if self.children is None:
            self.children = []

        self.hidden = False

        self.timeline = timeline
        self.setMouseTracking(True)

        self.indent = 20
        self.group_height = self.fontMetrics().height() * 3

        self.btn_expand = QtWidgets.QPushButton("+", self)
        self.btn_expand.clicked.connect(self.toggle_expand)
        self.btn_expand.setStyleSheet("QWidget{background:rgba(42, 116, 145, 100); margin:0pt; border-radius: 5px; font-size: 15pt;}")
        self.btn_expand.move(5, 5)

        self.btn_expand.show()

        self.setLayout(QHBoxLayout())
        self.indent_widget = QWidget(self)
        self.indent_widget.setStyleSheet("QWidget{background:transparent; margin:0pt; border-radius: 5 px;}")
        self.indent_widget.setFixedWidth(self.indent)
        self.layout().addWidget(self.indent_widget)

        self.vbox = QVBoxLayout(self)
        self.layout().addItem(self.vbox)

        self.lbl_title = QLabel(self.name, self)
        self.lbl_title.setStyleSheet("QWidget{background:transparent; }")
        self.lbl_title.setAlignment(Qt.AlignLeft)
        self.lbl_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.expander = QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        self.vbox.addWidget(self.lbl_title)
        self.vbox.addItem(self.expander)

        self.btn_expand.setFixedSize(QtCore.QSize(self.indent_widget.width(), self.lbl_title.height() - 5))

        self.groups = []

        self.btn_expand.raise_()
        self.collapse()


    def add_child(self, c):
        self.children.append(c)
        c.set_indent(self.indent + 10)

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.is_expanded = True
        for c in self.children:
            c.set_expanded(False)
            c.show()
        self.timeline.update_ui()

    def collapse(self):
        self.is_expanded = False
        for c in self.children:
            c.set_expanded(False)
            c.hide()
        self.timeline.update_ui()


class TimelineSubSegmentationControl(QWidget):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, parent_item, sub:TimelineSubSegmentation):
        super(TimelineSubSegmentationControl, self).__init__(parent)
        self.sub = sub
        self.sub.control = self
        self.setMouseTracking(True)

        self.name = sub.name

        self.parent_item = parent_item
        self.timeline = timeline

        self.group_height = self.fontMetrics().height() * 3
        self.indent = 30
        self.is_expanded = False

        # self.setFixedHeight(self.sub.strip_height * len(self.sub.entries))

        self.btn_expand = QtWidgets.QPushButton("+", self)
        self.btn_expand.clicked.connect(self.toggle_expand)
        self.btn_expand.setStyleSheet("QWidget{background:rgba(42, 116, 145, 100); margin:0pt; border-radius: 5px; font-size: 15pt;}")
        self.btn_expand.move(5, 5)
        self.btn_expand.setFixedSize(QtCore.QSize(self.indent - 10, self.indent - 10))

        self.btn_expand.show()

        self.setLayout(QHBoxLayout())
        self.indent_widget = QWidget(self)
        self.indent_widget.setStyleSheet("QWidget{background:transparent; margin:0pt; border-radius: 5 px;}")
        self.indent_widget.setFixedWidth(self.indent)
        self.layout().addWidget(self.indent_widget)

        self.vbox = QVBoxLayout(self)
        self.layout().addItem(self.vbox)
        self.lbl_title = QLabel(self.name, self)
        self.lbl_title.setStyleSheet("QWidget{background:transparent; }")
        self.lbl_title.setAlignment(Qt.AlignLeft)
        self.lbl_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.expand = QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.vbox.addWidget(self.lbl_title)
        self.vbox.addItem(self.expand)

        self.groups = []

        self.btn_expand.raise_()

        self.size_grip_hovered = False
        self.is_resizing = False
        self.resize_offset = 0
        self.highlighted_entry = None

    def set_indent(self, d):
        self.indent = d
        self.btn_expand.move(5 + d, 5)
        self.indent_widget.setFixedWidth(self.indent + self.btn_expand.width())
        self.update()

    def toggle_expand(self):
        if self.btn_expand.text() == "+":
            self.is_expanded = True
            self.btn_expand.setText("-")
            for t in self.sub.entries:
                t.strip.show()
        else:
            self.is_expanded = False
            self.btn_expand.setText("+")
            for t in self.sub.entries:
                t.strip.hide()
        self.timeline.update_ui()

    def set_expanded(self, state):
        if state:
            self.is_expanded = True
            self.btn_expand.setText("-")
            for t in self.sub.entries:
                t.strip.show()
        else:
            self.is_expanded = False
            self.btn_expand.setText("+")
            for t in self.sub.entries:
                t.strip.hide()
        self.timeline.update_ui()

    def highlight_entry(self, entry):
        self.highlighted_entry = entry
        self.update()

    def update_strip_height(self):
        if len(self.sub.entries) > 0:
            t = (self.height() - self.timeline.group_height) / len(self.sub.entries)
            # if t < 20:
            #     return
            self.sub.strip_height = t
            self.onHeightChanged.emit(self.sub.strip_height)
        else:
            self.onHeightChanged.emit(self.height())
        self.timeline.update_ui()
        self.update()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent):
        if self.is_resizing:
            if not a0.pos().y() + self.resize_offset < self.timeline.bar_height_min:
                self.resize(self.width(), a0.pos().y() + self.resize_offset)
                self.update_strip_height()
        else:
            if a0.pos().y() > self.height() - 15 and self.is_expanded:
                self.size_grip_hovered = True
            else:
                self.size_grip_hovered = False
            self.update()
            super(TimelineSubSegmentationControl, self).mouseMoveEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent):
        self.size_grip_hovered = False
        super(TimelineSubSegmentationControl, self).leaveEvent(a0)

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            if QMouseEvent.pos().y() > self.height() - 15 and self.is_expanded:
                self.is_resizing = True
                self.resize_offset = self.height() - QMouseEvent.pos().y()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent):
        self.is_resizing = False

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super(TimelineSubSegmentationControl, self).paintEvent(a0)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(255, 255, 255, 50))
        pen.setWidth(1)
        qp.setPen(pen)

        pen.setColor(QtGui.QColor(255, 255, 255, 200))
        qp.setPen(pen)

        gradient = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
        gradient.setColorAt(0.0, QColor(50, 50, 50))
        gradient.setColorAt(0.5, QColor(65, 65, 65))
        gradient.setColorAt(1.0, QColor(50, 50, 50))
        gradient.setSpread(QGradient.PadSpread)
        qp.fillRect(QtCore.QRect(self.indent, 0, self.width(), self.height()), gradient)

        if self.is_expanded:
            y = self.timeline.group_height + self.sub.strip_height
            for i, s in enumerate(self.sub.entries):
                text_rect = QtCore.QRect(0, y, self.width(), self.sub.strip_height)
                if s.strip == self.highlighted_entry:
                    r = QtCore.QRect(self.indent, y, self.width(),  self.sub.strip_height)
                    qp.fillRect(r,  QColor(120,120,120,120))
                qp.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, s.name)
                y += self.sub.strip_height

        pen.setColor(QtGui.QColor(54, 146, 182, 200))
        pen.setWidth(5)
        qp.setPen(pen)
        qp.drawLine(QtCore.QPoint(self.indent, 0), QtCore.QPoint(self.indent, self.height()))

        pen.setWidth(1)
        pen.setColor(QtGui.QColor(255, 255, 255, 255))
        qp.setPen(pen)
        qp.drawLine(QtCore.QPoint(0, 0), QtCore.QPoint(self.width(), 0))

        if self.size_grip_hovered:
            pen.setColor(QtGui.QColor(164, 7, 0, 200))
            pen.setWidth(4)
            qp.setPen(pen)
            qp.drawLine(0, self.height() - 2, self.width(), self.height() - 2)
        qp.end()


class TimelineSubSegmentationBar(QWidget):
    onHeightChanged = pyqtSignal(int)
    onHoverEnter = pyqtSignal(object)
    onHoverLeave = pyqtSignal(object)

    def __init__(self, parent, timeline, control, parent_item, sub_entry, height = 20):
        super(TimelineSubSegmentationBar, self).__init__(parent)
        self.setMouseTracking(True)

        self.sub_entry = sub_entry
        sub_entry.strip = self

        self.timeline = timeline
        self.control = control

        self.control.onHeightChanged.connect(self.on_height_changed)
        self.onHoverEnter.connect(partial(self.control.highlight_entry, self))
        self.onHoverLeave.connect(partial(self.control.highlight_entry, None))

        self.parent_item = parent_item

        self.slices = []
        self.slices_index = dict()

        self.selection_update_state = False
        self.is_selecting = False
        self.selection_rect = None

        if isinstance(self.parent_item, Segmentation):
            self.parent_item.onSegmentDeleted.connect(self.remove_slice)
            self.parent_item.onSegmentAdded.connect(self.add_slice)
            for t in self.parent_item.segments:
                self.add_slice(t)

        if self.control.is_expanded == False:
            self.hide()

    @pyqtSlot(int)
    def on_height_changed(self, height):
        """
        This is called when the User drags the size handle into one direction in the control widget,
        usually it does not have to be used since the resizing is done in the timeline update_ui() directly.
        Screenshots override it to resize the pixmaps as well
        :param height:
        :return:
        """
        self.resize(self.width(), height)
        self.onHeightChanged.emit(height)

    def add_slice(self, item):
        slice = TimebarSubSegmentationSlice(self, item, self.timeline,
                                            mime_data=self.sub_entry.mime_data,
                                            is_active=item.has_word(self.sub_entry.mime_data['keyword']))
        self.sub_entry.slices.append(slice)

        self.onHeightChanged.connect(slice.on_height_changed)

        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())

        slice.onHoverEnter.connect(self.onHoverEnter.emit)
        slice.onHoverLeave.connect(self.onHoverLeave.emit)
        slice.onClicked.connect(self.on_clicked)

        if self.control.is_expanded:
            slice.show()

        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice

    def remove_slice(self, item):
        if item.get_id() in self.slices_index:
            itm = self.slices_index[item.get_id()]
            self.slices.remove(itm)
            self.slices_index.pop(item.get_id())
            itm.close()

    def on_clicked(self, state, slice):
        kwd = self.sub_entry.mime_data['keyword'] #type:UniqueKeyword
        slice.is_active = kwd.experiment.toggle_tag(slice.parent_item, kwd)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self.is_selecting:
            if self.selection_rect is None:
                self.selection_rect = (a0.pos(), a0.pos() + QPoint(1, 0))
            else:
                self.selection_rect = (self.selection_rect[0], QPoint(a0.pos().x(), self.selection_rect[0].y()))
            self.update()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.is_selecting = False
        if self.selection_rect is not None:
            t = QRect(self.selection_rect[0].x(),
                      self.selection_rect[0].y(),
                      self.selection_rect[1].x() - self.selection_rect[0].x(), 5)

            for w in self.slices:
                w_rect = QRect(w.pos(), w.rect().size())
                if w_rect.intersects(t):
                    w.set_active(self.selection_update_state)
            self.selection_rect = None

        print("Hello Release")

    def set_selecting(self, new_state):
        self.selection_update_state = new_state
        self.is_selecting = True


    def rescale(self):
        if self.control.is_expanded:
            for s in self.slices:
                s.move(int(round(s.parent_item.get_start() / self.timeline.scale, 0)), 0)
                s.resize(int(round((s.parent_item.get_end() - s.parent_item.get_start()) / self.timeline.scale, 0)), self.height() / 2)

    def paintEvent(self, QPaintEvent):
        # super(TimelineBar, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        pen.setColor(QtGui.QColor(20, 20, 20, 50))
        pen.setWidth(1)
        qp.setPen(pen)

        if self.is_selecting and self.selection_rect is not None:
            pen.setColor(QtGui.QColor(174, 55, 55))
            pen.setWidth(5)
            qp.setPen(pen)
            qp.drawLine(self.selection_rect[0], self.selection_rect[1])

        pen.setColor(QtGui.QColor(200, 200, 200, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        qp.drawRect(self.rect())
        qp.end()


class TimebarSubSegmentationSlice(QWidget):
    onClicked = pyqtSignal(bool, object)
    onDoubleClicked = pyqtSignal(object)
    onHoverEnter = pyqtSignal(object)
    onHoverLeave = pyqtSignal(object)

    def __init__(self, parent:TimelineSubSegmentationBar, parent_item, timeline, mime_data=None, is_active = False):
        super(TimebarSubSegmentationSlice, self).__init__(parent)
        self.timeline = timeline
        self.bar = parent
        self.setMouseTracking(True)

        self.default_color = (50, 50, 50, 150)
        self.col_active = (54, 146, 182, 200)
        self.col_hovered = (133, 42, 42, 100)
        self.parent_item = parent_item #type: Segment

        self.is_hovered = False
        self.is_active = is_active

        # When the mouse move event + key spawned already this is true
        self.already_changed = False

        self.mime_data = mime_data
        self.parent_item.onClassificationChanged.connect(self.on_classification_changed)


    @pyqtSlot(object)
    def on_classification_changed(self, keywords):
        if self.mime_data['keyword'] in keywords:
            self.is_active = True
        else:
            self.is_active = False

    @pyqtSlot(bool)
    def set_active(self, state):
        if self.is_active == state:
            return

        self.is_active = state
        self.onClicked.emit(self.is_active, self)
        self.update()

    def mouseDoubleClickEvent(self, QMouseEvent):
        if not self.is_active:
            self.is_active = True
            self.onClicked.emit(self.is_active, self)

        print(self.parent_item)
        name = "Remark: {name}".format(name=self.mime_data['keyword'].get_root_name())
        if len(self.parent_item.get_annotations(name=name)) == 0:
            self.parent_item.add_annotation(AnnotationBody(name=name, mime_type=AnnotationBody.MIMETYPE_TEXT_PLAIN))

        popup = AnnotationEditorPopup(self, self.parent_item, self.mapToGlobal(QMouseEvent.pos()), size=None,
                                      multi_annotation=True, timeline=self.timeline)

        popup.inner.select_by_name(name)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        super(TimebarSubSegmentationSlice, self).mousePressEvent(a0)
        if a0.button() == Qt.LeftButton:
            self.is_active = not self.is_active
            self.onClicked.emit(self.is_active, self)
            self.bar.set_selecting(self.is_active)
            self.update()

    def on_height_changed(self, int_height):
        self.resize(self.width(), int_height)

    def enterEvent(self, QEvent):
        super(TimebarSubSegmentationSlice, self).enterEvent(QEvent)
        self.is_hovered = True
        self.onHoverEnter.emit(self)
        self.update()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        super(TimebarSubSegmentationSlice, self).mouseMoveEvent(a0)
        if a0.button() == Qt.LeftButton and not self.already_changed:
            self.is_active = not self.is_active
            self.onClicked.emit(self.is_active, self)
            self.already_changed = True
            self.update()

    def leaveEvent(self, QEvent):
        super(TimebarSubSegmentationSlice, self).leaveEvent(QEvent)
        self.is_hovered = False
        self.already_changed = False
        self.onHoverLeave.emit(self)
        self.update()

    def paintEvent(self, QPaintEvent):
        if self.is_active:
            col = self.col_active
        elif self.is_hovered:
            col = self.col_hovered[:3] + (50, )
        else:
            col = (self.default_color[0], self.default_color[1], self.default_color[2], 100)

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

        # pen.setColor(QtGui.QColor(255, 255, 255))
        # qp.setPen(pen)
        # qp.drawText(5, (self.height() + self.text_size) // 2, self.text)

        qp.end()