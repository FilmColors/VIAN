from core.data.containers import VIANProject
from core.data.interfaces import IConcurrentJob
from core.analysis.colorimetry.computation import calculate_histogram
from core.data.computation import frame2ms, ms_to_frames
from core.analysis.palette_extraction import *
import cv2
import numpy as np
from collections import namedtuple
from PyQt5.QtCore import pyqtSlot, QObject

YieldedResult = namedtuple("YieldedResult", ["frame_pos", "time_ms", "hist", "avg_color", "palette"])

class ColormetryJob2(QObject):
    def __init__(self, resolution, main_window):
        super(ColormetryJob2, self).__init__()
        self.resolution = resolution
        self.colormetry_analysis = None
        self.main_window = main_window
        self.duration =  None
        self.aborted = False

    def prepare(self, project:VIANProject):
        if project.colormetry_analysis is None:
            self.colormetry_analysis = project.create_colormetry()
            start = 0
        else:
            self.colormetry_analysis = project.colormetry_analysis
            start = self.colormetry_analysis.curr_location
        self.duration = project.movie_descriptor.duration
        frame_duration = ms_to_frames(self.duration, project.movie_descriptor.fps)
        return [
            project.movie_descriptor.get_movie_path(),
            start,
            frame_duration,
            30,
            project.movie_descriptor.fps
        ]

    def run_concurrent(self, args, callback):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        resolution = args[3]
        fps = args[4]

        length = np.clip(int(end - start), 1, None)

        video_capture = cv2.VideoCapture(movie_path)
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        progress_counter = 0
        hist_counter = 0

        for i in range(length):
            if i % resolution == 0:
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, i + start)
                ret, frame = video_capture.read()
            else:
                continue

            if frame is None:
                break

            # Colorspace Conversion
            frame_lab = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)

            # Histogram
            hist = np.divide(calculate_histogram(frame_lab, 16), (width * height))
            # hist = None
            palette = color_palette(frame_lab, n_merge_steps=200, n_merge_per_lvl=20, image_size=150.0)
            # palette = None
            # AVG Color
            avg_color = np.mean(frame_lab, axis=(0, 1)).astype(np.uint8)

            if self.aborted:
                return

            yielded_result = dict(frame_pos=i, time_ms=frame2ms(i, fps), hist=hist, avg_color=avg_color, palette=palette)
            callback.emit([yielded_result, i / end])

            hist_counter += 1
            progress_counter += 1

    @pyqtSlot(object)
    def colormetry_callback(self, yielded_result):

        self.colormetry_analysis.append_data(yielded_result)
        self.main_window.timeline.timeline.set_colormetry_progress(yielded_result.time_ms / self.duration)

    @pyqtSlot()
    def abort(self):
        self.aborted = True



