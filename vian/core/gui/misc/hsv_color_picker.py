from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from vian.core.gui.ewidgetbase import EDockWidget
from vian.core.data.log import log_error
import numpy as np
import os
"""
A Simple HSV Color Picker wich emits a ColorChanged Signal on click

"""

class HSVColorPickerDock(EDockWidget):
    colorChanged = pyqtSignal(tuple)

    def __init__(self, main_window):
        super(HSVColorPickerDock, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Color Picker")
        self.picker = HSVColorPicker(self)
        self.setWidget(self.picker)
        self.picker.colorChanged.connect(self.colorChanged)


class HSVColorPicker(QWidget):
    colorChanged = pyqtSignal(tuple)

    def __init__(self, parent):
        super(HSVColorPicker, self).__init__(parent)
        self.h = 0
        self.s = 0
        self.v = 1.0

        self.hsv_selector = HSVSpaceWidget(self)
        self.hsv_selector.valueChanged.connect(self.set_sv)
        self.hue_selector = HueSelectorWidget(self)
        self.hue_selector.valueChanged.connect(self.set_h)

        self.setLayout(QVBoxLayout())
        self.lt_upper = QHBoxLayout()
        self.lt_upper.setSpacing(5)
        self.lt_upper.addWidget(self.hsv_selector)
        self.lt_upper.addWidget(self.hue_selector)
        self.layout().addItem(self.lt_upper)
        self.values = ValuesWidget(self)
        self.values.preview.colorClicked.connect(self.add_to_recent)
        self.recent = RecentColors(self, self)

        self.layout().addWidget(self.values)
        self.lbl_recent = QLabel("Recent Colors:")
        self.lbl_recent.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.layout().addWidget(self.lbl_recent)
        self.layout().addWidget(self.recent)
        self.current_color = (0, 0, 0)

    def colorRGB(self):
        c = QColor()
        c.setHsv(self.h, self.s, self.v)
        return (c.red(), c.green(), c.blue())

    def on_color_changed(self, color):
        color = (np.clip(color[0],0, 360), np.clip(color[1],0, 255), np.clip(color[2],0, 255))
        self.current_color = color
        self.h = color[0]
        self.s = color[1]
        self.v = color[2]
        self.colorChanged.emit(color)

    def set_h(self, hue):
        self.h = hue
        self.hsv_selector.update()
        self.values.update_values()
        self.on_color_changed((self.h, self.s, self.v))

    def set_sv(self, v, s):
        self.s = s
        self.v = v
        self.on_color_changed((self.h, self.s, self.v))
        self.values.update_values()

    def add_to_recent(self, c):
        self.recent.add_color(c[0], c[1], c[2])
        self.colorChanged.emit(c)

    def setColorRGB(self, rgb):
        color = QColor(rgb[0], rgb[1], rgb[2])
        hsv = color.toHsv()
        self.current_color = (hsv.hue(), hsv.saturation(), hsv.value())
        self.h = hsv.hue()
        self.s = hsv.saturation()
        self.v = hsv.value()
        self.values.update_values()
        self.update()


class HSVSpaceWidget(QWidget):
    valueChanged = pyqtSignal(int, int)

    def __init__(self, parent:HSVColorPicker):
        super(HSVSpaceWidget, self).__init__(parent)
        self.setMouseTracking(True)
        self.mouse_pressed = False

    def paintEvent(self, a0: QPaintEvent):
        qp = QPainter()
        pen = QPen()
        qp.setPen(pen)
        qp.begin(self)

        curr_color_sat = QColor()
        curr_color_sat.setHsv(self.parent().h, 255, 255)

        curr_color_desat = QColor()
        curr_color_desat.setHsv(self.parent().h, 0, 255)

        bw_gradient = QLinearGradient(QPointF(0.0, 0.0), QPointF(self.width(), 0.0))
        bw_gradient.setColorAt(0.0, QColor(0, 0, 0))
        bw_gradient.setColorAt(1.0, QColor(255,255,255))

        c_gradient = QLinearGradient(QPointF(0.0, self.height()), QPointF(0.0, 0.0))
        c_gradient.setColorAt(0.0, curr_color_desat)
        c_gradient.setColorAt(1.0, curr_color_sat)

        qp.fillRect(self.rect(), QColor(255,255,255))

        qp.setCompositionMode(QPainter.CompositionMode_Multiply)
        qp.fillRect(self.rect(), bw_gradient)
        qp.fillRect(self.rect(), c_gradient)

        qp.end()

    def mouseMoveEvent(self, a0: QMouseEvent):
        if self.mouse_pressed:
            self.valueChanged.emit(int((a0.pos().x()) / self.width() * 255),
                                   int((self.height() - a0.pos().y()) / self.height() * 255)
                                   )

    def mousePressEvent(self, a0: QMouseEvent):
        self.mouse_pressed = True

    def mouseReleaseEvent(self, a0: QMouseEvent):
        self.mouse_pressed = False


class HueSelectorWidget(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent:HSVColorPicker):
        super(HueSelectorWidget, self).__init__(parent)
        self.mouse_pressed = False
        self.setMouseTracking(True)
        self.setFixedWidth(30)

    def mouseMoveEvent(self, a0: QMouseEvent):
        if self.mouse_pressed:
            self.valueChanged.emit(int((self.height() - a0.pos().y()) / self.height() * 360))

    def paintEvent(self, a0: QPaintEvent):
        qp = QPainter()
        pen = QPen()
        qp.setPen(pen)
        qp.begin(self)
        qp.drawPixmap(self.rect(), QPixmap(os.path.abspath("qt_ui/images/hue_gradient.png")))

        qp.end()

    def mousePressEvent(self, a0: QMouseEvent):
        self.mouse_pressed = True

    def mouseReleaseEvent(self, a0: QMouseEvent):
        self.mouse_pressed = False


class ValuesWidget(QWidget):
    def __init__(self, parent:HSVColorPicker):
        super(ValuesWidget, self).__init__(parent)
        self.lt = QGridLayout()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setLayout(self.lt)
        self.lbl_r = QLabel("R")
        self.lbl_g = QLabel("G")
        self.lbl_b = QLabel("B")

        self.lbl_h = QLabel("H")
        self.lbl_s = QLabel("S")
        self.lbl_v = QLabel("V")

        self.preview = ColorField(self)
        self.preview.setToolTip("Click to Store Color in Recent Colors")

        self.lt.addWidget(self.lbl_r, 0, 0)
        self.lt.addWidget(self.lbl_g, 1, 0)
        self.lt.addWidget(self.lbl_b, 2, 0)

        self.lt.addWidget(self.lbl_h, 0, 1)
        self.lt.addWidget(self.lbl_s, 1, 1)
        self.lt.addWidget(self.lbl_v, 2, 1)

        self.lt.addWidget(self.preview,0,3,3,1)

    def update_values(self):

        self.lbl_r.setText("R: " + str(self.parent().h))
        self.lbl_g.setText("G: " + str(self.parent().h))
        self.lbl_b.setText("B: " + str(self.parent().h))

        self.lbl_h.setText("H: " + str(self.parent().h))
        self.lbl_s.setText("S: " + str(self.parent().s))
        self.lbl_v.setText("V: " + str(self.parent().v))

        self.preview.set_color(self.parent().h, self.parent().s, self.parent().v)
        self.preview.update()


class ColorField(QWidget):
    colorClicked = pyqtSignal(tuple)
    colorRightClicked = pyqtSignal(tuple)

    def __init__(self, parent, size = 50):
        super(ColorField, self).__init__(parent)
        self.h = 0
        self.s = 0
        self.v = 0
        self.setFixedSize(size,size)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.is_hovered = False

    def enterEvent(self, a0: QEvent):
        self.is_hovered = True

    def leaveEvent(self, a0: QEvent):
        self.is_hovered = False

    def set_color(self, h, s, v):
        self.h = h
        self.s = s
        self.v = v

    def mousePressEvent(self, a0: QMouseEvent):
        if a0.button() == Qt.RightButton:
            self.colorRightClicked.emit((self.h,self.s,self.v))
        else:
            self.colorClicked.emit((self.h,self.s,self.v))

    def paintEvent(self, a0: QPaintEvent):
        qp = QPainter()
        pen = QPen()
        pen.setWidth(3)
        pen.setColor(QColor(255,255,255,200))
        qp.setPen(pen)
        qp.begin(self)
        col = QColor()
        col.setHsv(self.h, self.s, self.v)
        qp.fillRect(self.rect(), col)

        if self.is_hovered:
            qp.drawRect(1,1, self.width() - 2, self.height() - 2)
        qp.end()


class RecentColors(QScrollArea):
    def __init__(self, parent, picker:HSVColorPicker):
        super(RecentColors, self).__init__(parent)
        self.picker = picker
        self.recent_colors = []
        self.setWidget(QFrame(self))
        self.setWidgetResizable(True)
        self.widget().setLayout(QHBoxLayout())
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setFixedHeight(50)

        self.widgets = []
        self.spacer = None

    def add_color(self, h, s, v):
        self.recent_colors.append((h,s,v))
        self.update_widgets()

    @pyqtSlot(object)
    def remove_color(self, c):
        try:
            self.recent_colors.remove(c)
        except Exception as e:
            log_error(e)

        self.update_widgets()

    def update_widgets(self):
        for w in self.widgets:
            w.close()
        self.widgets = []
        if self.spacer is not None:
            self.widget().layout().removeItem(self.spacer)

        for i in range(0, len(self.recent_colors)):
            w = ColorField(self, 20)
            w.set_color(self.recent_colors[len(self.recent_colors) - 1 - i][0],
                        self.recent_colors[len(self.recent_colors) - 1 - i][1],
                        self.recent_colors[len(self.recent_colors) - 1 - i][2])
            self.widget().layout().addWidget(w)
            w.colorClicked.connect(self.picker.colorChanged.emit)
            w.colorRightClicked.connect(self.remove_color)
            self.widgets.append(w)

        self.spacer = QSpacerItem(1,1,QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.widget().layout().addItem(self.spacer)


