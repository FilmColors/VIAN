from PyQt5.QtCore import *
import cv2
from typing import Dict
from core.data.computation import *
from core.analysis.spacial_frequency import get_spacial_frequency_heatmap, get_spacial_frequency_heatmap2
from core.container.project import VIANProject, IAnalysisJobAnalysis
from core.data.interfaces import SpatialOverlayDataset

class TimestepUpdateSignals(QObject):
    onOpenCVFrameUpdate = pyqtSignal(object)
    onColormetryUpdate = pyqtSignal(object, int)
    onLocationUpdate = pyqtSignal(list)
    onError = pyqtSignal(list)
    onMessage = pyqtSignal(str)


class TimestepUpdateWorkerSingle(QObject):
    def __init__(self):
        super(TimestepUpdateWorkerSingle, self).__init__()
        self.signals = TimestepUpdateSignals()
        self.project = None

        self.active = True
        self.wait = True

        self.position_ms = -1
        self.position_frame = -1
        self.fps = 30


        self.movie_path = ""
        self.video_capture = None

        self.opencv_frame = False
        self.update_colormetry = True

        self.spatial_datasets = dict() #type:Dict[str, SpatialOverlayDataset]
        self.current_spatial_dataset = None  # type:SpatialOverlayDataset

        self.update_face_rec = False
        self.update_spacial_frequency = False
        self.update_face_identification = True
        self.spacial_frequency_method = "edge-mean"


    @pyqtSlot(str)
    def set_movie_path(self, movie_path):
        self.movie_path = movie_path
        self.video_capture = cv2.VideoCapture(movie_path)
        ret, frame = self.video_capture.read()
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        if frame is not None:
            self.seedsmodel = cv2.ximgproc.createSuperpixelSEEDS(frame.shape[1], frame.shape[0], 3, 200,
                                                                 num_levels=6, histogram_bins=8)

    @pyqtSlot(bool, str)
    def toggle_spacial_frequency(self, state, method):
        self.update_spacial_frequency = state
        self.spacial_frequency_method = method
        self.run()

    @pyqtSlot(bool)
    def toggle_face_recognition(self, state):
        self.update_face_rec = state
        self.run()

    def set_project(self, project:VIANProject):
        self.project = project
        self.spatial_datasets = dict()

        self.project.onAnalysisAdded.connect(self.on_analysis_added)
        for a in project.analysis:
            self.on_analysis_added(a)

    @pyqtSlot(object)
    def on_analysis_added(self, analysis):
        if issubclass(analysis.__class__, IAnalysisJobAnalysis):
            t = analysis.get_spatial_overlays()
            if len(t) > 0:
                for overlay in t: #type:SpatialOverlayDataset
                    self.spatial_datasets[overlay.name] = overlay
                    self.current_spatial_dataset = overlay

    def set_opencv_frame(self, state):
        self.opencv_frame = state

    @pyqtSlot(bool)
    def set_colormetry_update(self, state):
        self.update_colormetry = state

    def setMSPosition(self, ms, frame):
        if self.position_frame == frame:
            return False

        self.position_ms = ms
        self.position_frame = frame
        return True

    @pyqtSlot()
    def abort_thread(self):
        self.active = False

    @pyqtSlot(int, int)
    def perform(self, time, frame):
        ret = self.setMSPosition(time, frame)
        if ret:
            self.run()

    @pyqtSlot()
    def run(self):
        try:
            # Load the OpenCV Frame
            if self.opencv_frame:
                frame_pixmap = self.get_opencv_frame(self.position_frame)
                if frame_pixmap is not None:
                    pass
                    self.signals.onOpenCVFrameUpdate.emit(frame_pixmap)
            if self.update_colormetry:
                if self.project is not None and self.project.colormetry_analysis is not None:
                    data = self.project.colormetry_analysis.get_update(self.position_ms)
                    if data is not False:
                        self.signals.onColormetryUpdate.emit(data, self.position_ms)

        except Exception as e:
            print("Exception in Timestep Update", e)
            self.signals.onError.emit([e])

    def get_opencv_frame(self, time_frame):
        """
        Returns the exact frame of the current visualization.
        
        :param time_frame:
        :return:
        """
        if self.video_capture is not None:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, time_frame)
            ret, frame = self.video_capture.read()
            if frame is None:
                return None

            # Calculate Spacial Frequency if necessary
            if self.update_spacial_frequency:
                f = None
                if self.project.colormetry_analysis.check_finished():
                    if self.spacial_frequency_method == "edge-mean":
                        f = self.project.hdf5_manager.get_colorimetry_spatial_max()['edge']
                    elif self.spacial_frequency_method == "color-var":
                        f = self.project.hdf5_manager.get_colorimetry_spatial_max()['color']
                    elif self.spacial_frequency_method == "hue-var":
                        f = self.project.hdf5_manager.get_colorimetry_spatial_max()['hue']
                    elif self.spacial_frequency_method == "luminance-var":
                        f = self.project.hdf5_manager.get_colorimetry_spatial_max()['luminance']
                if f == 0.0:
                    f = None
                heatmap, mask, denorm = get_spacial_frequency_heatmap(frame, method=self.spacial_frequency_method, normalize=True, norm_factor=f)
                frame = heatmap

            if self.current_spatial_dataset is not None:
                frame = self.current_spatial_dataset.get_overlay(frame2ms(time_frame, self.fps), frame)

            qimage, qpixmap = numpy_to_qt_image(frame)
            return qpixmap

        else:
            return None