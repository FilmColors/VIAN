import cv2
import numpy as np
from matplotlib import pyplot as plt
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *

from core.node_editor.datatypes import *
# DT_IMAGE = (0, QColor(255,255,199))
# DT_COLOR = (1, QColor(252,170,103))
# DT_ARRAY = (2, QColor(71,51,53))
# DT_NUMERIC = (3, QColor(3,63,99))

class Slot():
    def __init__(self, name, data_type, default_value):
        self.name = name
        self.data_type = data_type
        self.default_value = default_value

class Operation(QObject):
    def __init__(self, name, input_types, output_types, is_final_node = False):
        super(Operation, self).__init__()
        self.name = name
        self.result = []
        self.node = None
        # self.input_types = input_types
        # self.output_types = output_types
        self.input_slots = input_types
        self.output_slots = output_types

        # for i in input_types:
        #     self.input_types.append(i())
        # for o in output_types:
        #     self.output_types.append(o())
        self.is_final_node = is_final_node

    def update_out_types(self, input_types):
        return [slot.data_type for slot in self.output_slots]

    def perform(self, args):
        self.result = args

    def get_input_types(self):
        return self.input_types

    def get_output_types(self):
        return self.output_types

    def get_result(self):
        return self.result

    def handle_exception(self, exception):
        print ""
        print "Exception in Node"
        print self
        print exception.message
        print ""


class OperationValue(Operation):
    def __init__(self, name, input, output):
        super(OperationValue, self).__init__( name, input, output)

    def perform(self, args):
        self.result = self.spin_box.value()


class OperationScalar(OperationValue):
    def __init__(self):
        super(OperationScalar, self).__init__("Scalar", [], [Slot("Value", DT_Numeric, 0)])


class OperationVector2(OperationValue):
    def __init__(self):
        super(OperationVector2, self).__init__("Vector2", [], [Slot("Value", DT_Vector2, [0,1])])

    def perform(self, args):
        self.result = [self.spin_box_1.value(), self.spin_box_2.value()]


#region InputNodes
class ImageReader(Operation):
    def __init__(self):
        super(ImageReader, self).__init__("Read Frame Movie",[], [Slot("Frame", DT_Image, None)])

    def perform(self, args):
        try:
            cap = cv2.VideoCapture("C:\\Users\\Gaudenz Halter\\Videos\\Hyper\\GameStar\\test.mp4")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
            ret, frame = cap.read()
            self.result = frame
            if frame is None:
                raise Exception("Frame returned None, couldn't read Movie")
        except Exception as e:
            self.handle_exception(e)
#endregion


class OperationMean(Operation):
    def __init__(self):
        super(OperationMean, self).__init__("Mean", [
            Slot("Data", DT_Numeric, None),
            Slot("Axis", DT_Vector, [0,1])],
                                            [Slot("Mean", DT_Numeric, None)])

    def perform(self, args):
        try:
            axis = tuple(args[1])
            avg = np.mean(args[0], axis=axis)
            self.result = avg
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        print input_types
        if isinstance(input_types[0], DT_Image):
            self.output_types = [DT_Vector3]

        return self.output_types


class OperationAdd(Operation):
    def __init__(self):
        super(OperationAdd, self).__init__("Sum", [Slot("a", DT_Numeric, 0), Slot("b", DT_Numeric, 0)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args):
        try:
            sum = np.add(args[0], args[1])
            self.result = sum
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        if isinstance(input_types[0], DT_Image) or isinstance(input_types[1], DT_Image):
            self.output_types = [DT_Image]

        elif isinstance(input_types[0], DT_Vector3) or isinstance(input_types[1], DT_Vector3):
            self.output_types = [DT_Vector3]

        elif isinstance(input_types[0], DT_Vector2) or isinstance(input_types[1], DT_Vector2):
            self.output_types = [DT_Vector2]

        elif isinstance(input_types[0], DT_Vector) or isinstance(input_types[1], DT_Vector):
            self.output_types = [DT_Vector]

        return self.output_types


class OperationSubtract(Operation):
    def __init__(self):
        super(OperationSubtract, self).__init__("Subtract", [Slot("a", DT_Numeric, 0), Slot("b", DT_Numeric, 0)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args):
        try:
            subtract = np.subtract(args[0], args[1])
            self.result = subtract
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        if isinstance(input_types[0], DT_Image) or isinstance(input_types[1], DT_Image):
            self.output_types = [DT_Image]

        elif isinstance(input_types[0], DT_Vector3) or isinstance(input_types[1], DT_Vector3):
            self.output_types = [DT_Vector3]

        elif isinstance(input_types[0], DT_Vector2) or isinstance(input_types[1], DT_Vector2):
            self.output_types = [DT_Vector2]

        elif isinstance(input_types[0], DT_Vector) or isinstance(input_types[1], DT_Vector):
            self.output_types = [DT_Vector]

        return self.output_types


class OperationMultiply(Operation):
    def __init__(self):
        super(OperationMultiply, self).__init__("Multiply", [Slot("a", DT_Numeric, 1), Slot("b", DT_Numeric, 1)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args):
        try:
            subtract = np.multiply(args[0], args[1])
            self.result = subtract
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        if isinstance(input_types[0], DT_Image) or isinstance(input_types[1], DT_Image):
            self.output_types = [DT_Image]

        elif isinstance(input_types[0], DT_Vector3) or isinstance(input_types[1], DT_Vector3):
            self.output_types = [DT_Vector3]

        elif isinstance(input_types[0], DT_Vector2) or isinstance(input_types[1], DT_Vector2):
            self.output_types = [DT_Vector2]

        elif isinstance(input_types[0], DT_Vector) or isinstance(input_types[1], DT_Vector):
            self.output_types = [DT_Vector]

        return self.output_types


class OperationDivision(Operation):
    def __init__(self):
        super(OperationDivision, self).__init__("Division", [Slot("a", DT_Numeric, 1), Slot("b", DT_Numeric, 1)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args):
        try:
            subtract = np.divide(args[0], args[1])
            self.result = subtract
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        if isinstance(input_types[0], DT_Image) or isinstance(input_types[1], DT_Image):
            self.output_types = [DT_Image]

        elif isinstance(input_types[0], DT_Vector3) or isinstance(input_types[1], DT_Vector3):
            self.output_types = [DT_Vector3]

        elif isinstance(input_types[0], DT_Vector2) or isinstance(input_types[1], DT_Vector2):
            self.output_types = [DT_Vector2]

        elif isinstance(input_types[0], DT_Vector) or isinstance(input_types[1], DT_Vector):
            self.output_types = [DT_Vector]

        return self.output_types


class OperationNormalize(Operation):
    def __init__(self):
        super(OperationNormalize, self).__init__("Normalization", [Slot("In", DT_Numeric, None)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args):
        try:
            result = np.subtract(np.array(args[0]).astype(np.float64), np.amin(args[0]))
            result = np.multiply(np.divide(result, np.amax(result)), 255)
            self.result = result
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        self.output_types = [input_types[0].__class__]
        print self.output_types

        return self.output_types

class OperationShowImage(Operation):
    def __init__(self):
        super(OperationShowImage, self).__init__("Show Image", [Slot("Image", DT_Image, None)], [], is_final_node= True)

    def perform(self, args):
        try:
            img = np.array(np.clip(args[0], 0, 255)).astype(np.uint8)
            cv2.imshow("ImShow Output", img)
            cv2.waitKey()
        except Exception as e:
            self.handle_exception(e)


class OperationColor2Image(Operation):
    def __init__(self):
        super(OperationColor2Image, self).__init__("Color -> Image", [Slot("Color", DT_Vector3, [0,0,0])], [Slot("Image", DT_Image, None)])

    def perform(self, args):
        try:
            data = np.zeros(shape=(500, 500, 3)).astype(np.uint8)
            data[:, :] = args[0]
            self.result = data
        except Exception as e:
            self.handle_exception(e)


class OperationBarPlot(Operation):
    def __init__(self):
        super(OperationBarPlot, self).__init__("Bar Plot", [DT_Vector], [], is_final_node= True)

    def perform(self, args):
        try:
            if not isinstance(args[0], list) or not isinstance(args[0], np.ndarray):
                y = np.array([args[0]])
            else:
                y = args[0]

            plt.bar(range(y.shape[0]), y)
            plt.show()

        except Exception as e:
            self.handle_exception(e)


