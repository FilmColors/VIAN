from PyQt5.QtCore import *
import cv2
from core.data.computation import *

class TimestepUpdateSignals(QObject):
    onOpenCVFrameUpdate = pyqtSignal(object)
    onLocationUpdate = pyqtSignal(list)
    onError = pyqtSignal(list)
    onMessage = pyqtSignal(str)

class TimestepUpdateWorkerSingle(QObject):
    def __init__(self):
        super(TimestepUpdateWorkerSingle, self).__init__()
        self.signals = TimestepUpdateSignals()

        self.active = True
        self.wait = True

        self.position_ms = -1
        self.position_frame = -1

        self.movie_path = ""
        self.video_capture = None

        self.opencv_frame = False

    @pyqtSlot()
    def set_movie_path(self, movie_path):
        self.movie_path = movie_path
        self.video_capture = cv2.VideoCapture(movie_path)

    def set_opencv_frame(self, state):
        self.opencv_frame = state

    def setMSPosition(self, ms, frame):
        if self.position_frame == frame:
            return

        self.position_ms = ms
        self.position_frame = frame

    @pyqtSlot()
    def abort_thread(self):
        self.active = False

    @pyqtSlot(int, int)
    def perform(self, time, frame):
        self.setMSPosition(time, frame)
        self.run()

    @pyqtSlot()
    def run(self):
        try:
            # Load the OpenCV Frame
            frame_pixmap = self.get_opencv_frame(self.position_frame)
            if frame_pixmap is not None:
                self.signals.onOpenCVFrameUpdate.emit(frame_pixmap)

        except Exception as e:
            self.signals.onError.emit([e])

    def get_opencv_frame(self, time_frame):
        if self.video_capture is not None:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, time_frame)
            ret, frame = self.video_capture.read()
            qimage, qpixmap = numpy_to_qt_image(frame)
            return qpixmap
        else:
            return None