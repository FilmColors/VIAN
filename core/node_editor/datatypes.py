from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from functools import partial


class DataType(object):
    def __init__(self, parent = None,  color = QColor(10,10,10), default_value = None):
        # super(DataType, self).__init__(parent)
        # self.setAttribute(Qt.WA_MouseTracking, True)
        self.value = default_value
        self.color = color

        self.font_size = 12

        # self.name = QLabel("DataType", self)
        # self.name.move(0,0)
        # self.name.resize(self.width(), self.height() / 2.0)
        # self.name.setAttribute(Qt.WA_TranslucentBackground)
        # self.name.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        # self.show()

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def scale(self, scale):
        pass
        # font = self.name.font()
        # font.setPointSize(self.font_size * scale)
        # self.name.setFont(font)
        # self.name.resize(self.width() * scale, self.height() / 2.0)


class DT_Numeric(DataType):
    def __init__(self,parent = None,  color = QColor(229,229,229), default_value = None):
        super(DT_Numeric, self).__init__(parent, color = color, default_value=default_value)


class DT_Vector(DT_Numeric):
    def __init__(self,parent = None, color = QColor(229,229,229), default_value = None):
        super(DT_Vector, self).__init__(parent, color, default_value=default_value)


class DT_Vector2(DT_Vector):
    def __init__(self, parent = None, default_value = None):
        super(DT_Vector2, self).__init__(parent, color=QColor(232,209,116), default_value=default_value)

    # def widget(self, parent):
    #     w = super(DT_Vector2, self).widget(parent)
    #     sp1 = QSpinBox(w)
    #     sp2 = QSpinBox(w)
    #
    #     sp1.valueChanged.connect(partial(self.on_widget_changed, [sp1, sp2]))
    #     sp2.valueChanged.connect(partial(self.on_widget_changed, [sp1, sp2]))
    #
    #     w.layout().addWidget(sp1)
    #     w.layout().addWidget(sp2)
    #     w.setStyleSheet("QWidget{margin: 0pt; padding: 0pt;}")
    #
    #     return w

    # def on_widget_changed(self, boxes):
    #     self.value = [boxes[0].value(), boxes[1].value()]


class DT_Vector3(DT_Vector):
    def __init__(self, parent = None, default_value = None):
        super(DT_Vector3, self).__init__(parent, color=QColor(227,158,84), default_value=default_value)

    # def widget(self, parent):
    #     w = super(DT_Vector3, self).widget(parent)
    #     sp1 = QSpinBox(w)
    #     sp2 = QSpinBox(w)
    #     sp3 = QSpinBox(w)
    #
    #     sp1.valueChanged.connect(partial(self.on_widget_changed, [sp1, sp2, sp3]))
    #     sp2.valueChanged.connect(partial(self.on_widget_changed, [sp1, sp2, sp3]))
    #     sp3.valueChanged.connect(partial(self.on_widget_changed, [sp1, sp2, sp3]))
    #
    #     w.layout().addWidget(sp1)
    #     w.layout().addWidget(sp2)
    #     w.layout().addWidget(sp3)
    #
    #     return w


    # def on_widget_changed(self, boxes):
    #     self.value = [boxes[0].value(), boxes[1].value(), boxes[2].value()]


class DT_Image(DT_Numeric):
    def __init__(self, parent = None, default_value = None):
        super(DT_Image, self).__init__(parent, color=QColor(214, 77, 77), default_value=default_value)

