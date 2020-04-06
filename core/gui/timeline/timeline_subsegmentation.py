from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QPoint, QPointF, QRect, QRectF, Qt
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSpacerItem
from PyQt5.QtGui import QLinearGradient, QColor, QGradient, QPixmap

from PyQt5 import QtGui, QtWidgets, QtCore

from .timeline_base import TimelineControl, TimebarSlice, TimelineBar
from core.container.project import Segmentation


class TimelineSubSegmentationEntry:
    TYPE_BINARY  = 0

    def __init__(self, name, mode= TYPE_BINARY):
        self.name = name
        self.mode = mode


class TimelineSubSegmentation:
    def __init__(self, name):
        self.name = name
        self.entries = []

        self.strip_height = 30
        self.is_expanded = True

    def get_name(self):
        return self.name

    def add_entry(self, e:TimelineSubSegmentationEntry):
        self.entries.append(e)

    def __len__(self):
        return len(self.entries)


class TimelineSubSegmentationControl(QWidget):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, parent_item, sub:TimelineSubSegmentation):
        super(TimelineSubSegmentationControl, self).__init__(parent)
        self.sub = sub
        self.name = sub.name
        self.parent_item = parent_item
        self.timeline = timeline

        self.group_height = 20
        self.indent = 20
        self.entries = []

        self.setLayout(QHBoxLayout())
        self.indent_widget = QWidget()
        self.indent_widget.setFixedWidth(self.indent)
        self.layout().addWidget(self.indent_widget)

        self.vbox = QVBoxLayout(self)
        self.layout().addItem(self.vbox)
        self.lbl_title = QLabel(self.name, self)
        self.lbl_title.setStyleSheet("QWidget{background:transparent; margin:0pt;}")
        self.vbox.addWidget(self.lbl_title)
        # self.expand = QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        # DUCK TYPING
        self.groups = []
        self.size_grip_hovered = False

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

        y = self.timeline.group_height
        for i, s in enumerate(self.entries):
            y += s.strip_height
            text_rect = QtCore.QRect(0, y, self.width(), self.group_height)
            qp.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, s.name)

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

    def __init__(self, parent, timeline, control, parent_item, height = 20):
        super(TimelineSubSegmentationBar, self).__init__(parent)
        self.timeline = timeline
        self.control = control

        self.parent_item = parent_item

        self.slices = []
        self.setFixedHeight(height)
        self.slices_index = dict()

        print(self.parent_item)
        if isinstance(self.parent_item, Segmentation):
            self.parent_item.onSegmentDeleted.connect(self.remove_slice)
            self.parent_item.onSegmentAdded.connect(self.add_slice)
            for t in self.parent_item.segments:
                self.add_slice(t)

    def add_slice(self, item):
        slice = TimebarSubSegmentationSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)

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

    def rescale(self):
        return

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

        pen.setColor(QtGui.QColor(200, 200, 200, 50))
        pen.setWidth(1)
        qp.setPen(pen)
        qp.drawRect(self.rect())
        qp.end()


class TimebarSubSegmentationSlice(QWidget):
    def __init__(self, parent:TimelineSubSegmentationBar, parent_item, timeline):
        super(TimebarSubSegmentationSlice, self).__init__(parent)
        self.timeline = timeline

        self.default_color = (54, 146, 182, 100)
        self.col_selected = (54, 146, 182, 200)
        self.col_hovered = (54, 146, 182, 240)
        self.parent_item = parent_item

    def on_height_changed(self, int_height):
        self.resize(self.width(), int_height)

    def paintEvent(self, QPaintEvent):
        col = (self.default_color[0], self.default_color[1], self.default_color[2], 50)

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