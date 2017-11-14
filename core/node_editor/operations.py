import cv2
import numpy as np
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *

DT_IMAGE = (0, QColor(255,255,199))
DT_COLOR = (1, QColor(252,170,103))



class Operation(QObject):
    def __init__(self,name, input_types, output_types, is_final_node = False):
        super(Operation, self).__init__()
        self.name = name
        self.result = []
        self.input_types = input_types
        self.output_types = output_types
        self.is_final_node = is_final_node

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


class OperationMean(Operation):
    def __init__(self):
        super(OperationMean, self).__init__("Mean", [DT_IMAGE], [DT_IMAGE])

    def perform(self, args):

        avg = np.mean(args[0], axis=(0, 1))
        print avg
        data = np.zeros(shape=(500,500,3)).astype(np.uint8)
        data[:,:] = avg
        self.result = data


class OperationShowImage(Operation):
    def __init__(self):
        super(OperationShowImage, self).__init__("Show Image", [DT_IMAGE], [], is_final_node= True)

    def perform(self, args):
        try:
            cv2.imshow("ImShow Output", np.array(args[0], dtype=np.uint8))
            cv2.waitKey()
        except Exception as e:
            self.handle_exception(e)


class ImageReader(Operation):
    def __init__(self):
        super(ImageReader, self).__init__("Read Frame Movie",[], [DT_IMAGE])

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