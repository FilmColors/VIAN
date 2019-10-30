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



#region NUMERIC
class DT_Literal(DataType):
    def __init__(self,parent = None,  color = QColor(82,139,230), default_value = None):
        super(DT_Literal, self).__init__(parent, color = color, default_value=default_value)


class DT_Numeric(DataType):
    def __init__(self,parent = None,  color = QColor(229,229,229), default_value = None):
        super(DT_Numeric, self).__init__(parent, color = color, default_value=default_value)


class DT_Vector(DT_Numeric):
    def __init__(self,parent = None, color = QColor(229,229,229), default_value = None):
        super(DT_Vector, self).__init__(parent, color, default_value=default_value)


class DT_Vector2(DT_Vector):
    def __init__(self, parent = None, default_value = None):
        super(DT_Vector2, self).__init__(parent, color=QColor(232,209,116), default_value=default_value)


class DT_Vector3(DT_Vector):
    def __init__(self, parent = None, default_value = None):
        super(DT_Vector3, self).__init__(parent, color=QColor(227,158,84), default_value=default_value)


class DT_VectorArray(DT_Numeric):
    def __init__(self, parent = None,color=QColor(132, 204, 51), default_value = None):
        super(DT_VectorArray, self).__init__(parent, color=color)


class DT_ImageStack(DT_Numeric):
    def __init__(self, parent = None,color=QColor(102,6,11), default_value = None):
        super(DT_ImageStack, self).__init__(parent, color=color)


class DT_Image(DT_ImageStack):
    def __init__(self, parent = None, default_value = None):
        super(DT_Image, self).__init__(parent, color=QColor(214, 77, 77), default_value=default_value)

#endregion

#region PROJECT DataTypes
class DT_Segment(DataType):
    def __init__(self,parent = None,  color = QColor(82,139,230), default_value = None):
        super(DT_Segment, self).__init__(parent, color = color, default_value=default_value)

        self.value = ["New Segment", 0, 100]

    def set_segment_name(self, name):
        self.value[0] = name

    def set_segment_start(self, start_ms):
        self.value[1] = start_ms

    def set_segment_end(self, end_ms):
        self.value[2] = end_ms


class DT_Annotation(DataType):
    def __init__(self,parent = None,  color = QColor(225, 82, 230), default_value = None):
        super(DT_Annotation, self).__init__(parent, color = color, default_value=default_value)

        self.value = ["New Annotation", (0, 0), (100, 100)]


class DT_Screenshot(DataType):
    def __init__(self, parent = None, color = QColor(225, 160, 20), default_value = None):
        super(DT_Screenshot, self).__init__(parent, color = color, default_value=default_value)
        self.value = ["New Screenshot", 0]

#endregion

#region CASTING
def cast_numeric_output_type_highest(input_slots):
    input_types = [s.data_type() for s in input_slots]

    if isinstance(input_types[0], DT_Image) or isinstance(input_types[1], DT_Image):
        output_types = [DT_Image]

    elif isinstance(input_types[0], DT_ImageStack) or isinstance(input_types[1], DT_ImageStack):
        output_types = [DT_ImageStack]

    elif isinstance(input_types[0], DT_Vector3) or isinstance(input_types[1], DT_Vector3):
        output_types = [DT_Vector3]

    elif isinstance(input_types[0], DT_Vector2) or isinstance(input_types[1], DT_Vector2):
        output_types = [DT_Vector2]

    elif isinstance(input_types[0], DT_Vector) or isinstance(input_types[1], DT_Vector):
        output_types = [DT_Vector]

    elif isinstance(input_types[0], DT_Numeric) or isinstance(input_types[1], DT_Numeric):
        output_types = [DT_Numeric]
    else:
        output_types = [input_types[0]]

    return output_types


def cast_numeric_axis_reduction(input_slots, axis):
    input_types = [s.data_type() for s in input_slots]


    ax = axis.default_value

    axis = [int(a) for a in ax]
    axis.sort()


    if isinstance(input_types[0], DT_Image) and (axis == [0] or axis == [1]):
        output_types = [DT_VectorArray]

    elif isinstance(input_types[0], DT_Image) and axis == [0, 1, 2] :
        output_types = [DT_Numeric]

    elif isinstance(input_types[0], DT_Image) and axis == [0, 1] :
        output_types = [DT_Vector3]

    elif isinstance(input_types[0], DT_ImageStack) and axis == [0]:
        output_types = [DT_Image]

    elif isinstance(input_types[0], DT_Vector):
        output_types = [DT_Numeric]

    elif isinstance(input_types[0], DT_VectorArray):
        output_types = [DT_Vector]

    else:
        output_types = [eval(input_types[0].__class__.__name__)]

    return output_types


def cast_axis_extension(input_slots):
    input_types = [s.data_type() for s in input_slots]

    if isinstance(input_types[0], DT_Image):
        output_types = [DT_ImageStack]

    elif isinstance(input_types[0], DT_ImageStack):
        output_types = [DT_Numeric]

    elif isinstance(input_types[0], DT_VectorArray):
        output_types = [DT_Image]

    elif isinstance(input_types[0], DT_Vector):
        output_types = [DT_VectorArray]

    else:
        output_types = [eval(input_types[0].__class__.__name__)]

    return output_types

#endregion
""