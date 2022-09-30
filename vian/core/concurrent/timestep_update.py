from PyQt6.QtCore import *
import cv2
from PyQt6.QtGui import QPainter, QPainterPath, QColor
from typing import Dict
from vian.core.data.computation import *
from vian.core.analysis.spacial_frequency import get_spacial_frequency_heatmap, get_spacial_frequency_heatmap2
from vian.core.container.project import VIANProject, IAnalysisJobAnalysis
from vian.core.data.interfaces import SpatialOverlayDataset

from matplotlib import cm


class TimestepUpdateSignals(QObject):
    onOpenCVFrameUpdate = pyqtSignal(object)
    onColormetryUpdate = pyqtSignal(object, int)
    onLocationUpdate = pyqtSignal(list)
    onError = pyqtSignal(list)
    onMessage = pyqtSignal(str)
    onSpatialDatasetsChanged = pyqtSignal(object)


class OverlayVisualization:
    def __init__(self, dataset:SpatialOverlayDataset, blend_alpha=0.5):
        self.dataset = dataset
        self.blend_alpha = blend_alpha

    def get_overlay(self, ms, frame, fx, colormap):
        return frame


class HeatmapOverlayVisualization(OverlayVisualization):
    def __init__(self, dataset:SpatialOverlayDataset):
        super(HeatmapOverlayVisualization, self).__init__(dataset)

    def get_overlay(self, ms, frame, fx, colormap):
        points = self.dataset.get_data_for_time(ms, frame)

        overlay = np.zeros(frame.shape, dtype=np.float32)

        for x, y in points.tolist():
            cv2.circle(overlay, (int(x * fx), int(y * fx)), radius=int(4 * fx), color=(1.0,1.0,1.0), thickness=-1)

        tsize = int(33 * fx)
        if tsize % 2 == 0:
            tsize = tsize -1

        overlay = cv2.GaussianBlur(overlay, (tsize, tsize), 0)
        overlay /= np.amax(overlay)

        for i in range(5):
            tt = i * (255/5) + 1
            col = (np.array(colormap(tt / 255)) * 255).astype(np.uint8).tolist()

            ret, thresh = cv2.threshold(overlay[:,:,0] * 255, int(tt), 255, 0)
            contours, hierarchy, = cv2.findContours(thresh.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)

            cv2.drawContours(frame, contours, -1, (col[2], col[1], col[0]), 1)

        layer = cv2.cvtColor((colormap(overlay[:,:,0]) * 255).astype(np.uint8), cv2.COLOR_RGBA2BGR)
        overlay = overlay - self.blend_alpha

        overlay2 =      np.clip(overlay * layer.astype(np.float32), 0, 255)
        frame =  np.clip((1.0 - overlay) * frame.astype(np.float32), 0, 255)

        frame = (frame + overlay2).astype(np.uint8)
        return frame


class PointsOverlayVisualization(OverlayVisualization):
    def __init__(self, dataset: SpatialOverlayDataset):
        super(PointsOverlayVisualization, self).__init__(dataset)

    def get_overlay(self, ms, frame, fx, colormap):
        points = self.dataset.get_data_for_time(ms, frame)

        overlay = np.zeros(frame.shape, dtype=np.float32)

        for x, y in points.tolist():
            cv2.circle(overlay, (int(x * fx), int(y * fx)), radius=int(3 * fx), color=(1.0, 1.0, 1.0), thickness=-1)

        layer = cv2.cvtColor((colormap(overlay[:, :, 0]) * 255).astype(np.uint8), cv2.COLOR_RGBA2BGR)
        overlay = overlay - self.blend_alpha

        overlay2 = np.clip(overlay * layer.astype(np.float32), 0, 255)
        frame = np.clip((1.0 - overlay) * frame.astype(np.float32), 0, 255)

        frame = (frame + overlay2).astype(np.uint8)
        return frame


class ImageOverlayVisualization(OverlayVisualization):
    def __init__(self, dataset: SpatialOverlayDataset):
        super(ImageOverlayVisualization, self).__init__(dataset)

    def get_overlay(self, ms, frame, fx, colormap):

        overlay = self.dataset.get_data_for_time(ms, frame)

        overlay = overlay - self.blend_alpha
        frame = (frame + overlay).astype(np.uint8)

        return frame


def get_overlay_visualization_for_dataset(dataset:SpatialOverlayDataset):
    if dataset.vis_type == SpatialOverlayDataset.VIS_TYPE_HEATMAP:
        return HeatmapOverlayVisualization(dataset)

    elif dataset.vis_type == SpatialOverlayDataset.VIS_TYPE_POINTS:
        return PointsOverlayVisualization(dataset)

    elif dataset.vis_type == SpatialOverlayDataset.VIS_TYPE_COLOR_RGBA:
        return ImageOverlayVisualization(dataset)


class TimestepUpdateWorkerSingle(QObject):
    def __init__(self, settings):
        super(TimestepUpdateWorkerSingle, self).__init__()
        self.signals = TimestepUpdateSignals()
        self.project = None

        self.active = True
        self.wait = True

        self.position_ms = -1
        self.position_frame = -1
        self.fps = 30

        self.overlay_frame_width = settings.OVERLAY_RESOLUTION_WIDTH
        self.overlay_colormap = cm.get_cmap(settings.OVERLAY_VISUALIZATION_COLORMAP)

        self.movie_path = ""
        self.video_capture = None

        self.opencv_frame = False
        self.update_colormetry = True

        self.spatial_datasets = dict() #type:Dict[str, SpatialOverlayDataset]
        self.current_spatial_dataset = None  # type:OverlayVisualization or None

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
                    self.current_spatial_dataset = get_overlay_visualization_for_dataset(overlay)

                self.signals.onSpatialDatasetsChanged.emit(self.spatial_datasets.keys())

    @pyqtSlot(object)
    def on_settings_changed(self, settings):
        self.overlay_frame_width = settings.OVERLAY_RESOLUTION_WIDTH
        self.overlay_colormap = cm.get_cmap(settings.OVERLAY_VISUALIZATION_COLORMAP)
        self.run()

    @pyqtSlot(str)
    def on_set_spatial_dataset(self, name):
        if name in self.spatial_datasets:
            self.current_spatial_dataset = get_overlay_visualization_for_dataset(self.spatial_datasets[name])
        else:
            self.current_spatial_dataset = None

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

    def on_user_settings_changed(self, settings):
        self.overlay_frame_width = settings.OVERLAY_RESOLUTION_WIDTH

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

            # Ensure the display aspect ratio is correct
            if self.project.movie_descriptor.display_width is not None and self.project.movie_descriptor.display_height is not None:
                frame = cv2.resize(frame,
                                   (self.project.movie_descriptor.display_width, self.project.movie_descriptor.display_height),
                                   interpolation=cv2.INTER_CUBIC)

            fx = self.overlay_frame_width / frame.shape[1]
            frame = cv2.resize(frame, None, None, fx, fx, cv2.INTER_CUBIC)

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
                frame = self.current_spatial_dataset.get_overlay(frame2ms(time_frame, self.fps), frame, fx, self.overlay_colormap)

            qimage, qpixmap = numpy_to_qt_image(frame)
            return qpixmap

        else:
            return None