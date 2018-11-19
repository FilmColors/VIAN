from core.container.project import VIANProject
from core.data.interfaces import IConcurrentJob
from core.analysis.colorimetry.computation import calculate_histogram
from core.data.computation import frame2ms, ms_to_frames, lab_to_sat
from core.analysis.spacial_frequency import get_spacial_frequency_heatmap
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
            self.colormetry_analysis.clear()
            start = 0
        else:
            # if project.colormetry_analysis.current_idx == 0:
            #     project.colormetry_analysis.clear()

            self.colormetry_analysis = project.colormetry_analysis
            start = self.colormetry_analysis.current_idx
        self.duration = project.movie_descriptor.duration
        frame_duration = ms_to_frames(self.duration, project.movie_descriptor.fps)
        return [
            project.movie_descriptor.get_movie_path(),
            start,
            frame_duration,
            self.resolution,
            project.movie_descriptor.fps,
            project.movie_descriptor.get_letterbox_rect()
        ]

    def run_concurrent(self, args, callback):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        resolution = args[3]
        fps = args[4]
        margins = args[5]

        start *= resolution
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

            # Get sub frame if there are any margins
            if margins is not None:
                frame = frame[margins[1]:margins[3], margins[0]:margins[2]]
                # cv2.imshow("", frame)
                # cv2.waitKey(5)

            # Colorspace Conversion
            frame_lab = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)

            # Histogram
            hist = np.divide(calculate_histogram(frame_lab, 16), (width * height))
            # hist = None
            palette = color_palette(frame_lab, n_merge_steps=200, n_merge_per_lvl=20, image_size=150.0, n_pixels=400, seeds_input_width=400)
            # palette = None

            # Color Features
            frame_lab = cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
            color_bgr = np.mean(frame, axis = (0, 1))
            color_lab = np.mean(frame_lab, axis = (0, 1))

            feature_mat = np.zeros(shape=8)
            feature_mat[0:3] = color_lab
            feature_mat[3:6] = color_bgr
            feature_mat[6] = lab_to_sat(lab=color_lab, implementation="luebbe")
            feature_mat[7] = lab_to_sat(lab=color_lab, implementation="pythagoras")

            # Spatial
            eout, enorm, edenorm = get_spacial_frequency_heatmap(frame, method="edge-mean", normalize=False)
            cout, cnorm, cdenorm = get_spacial_frequency_heatmap(frame, method="color-var", normalize=False)
            hout, hnorm, hdenorm = get_spacial_frequency_heatmap(frame, method="hue-var", normalize=False)
            lout, lnorm, ldenorm = get_spacial_frequency_heatmap(frame, method="luminance-var", normalize=False)

            if self.aborted:
                return

            max_p_length = 1000
            palette_mat = np.zeros(shape=(max_p_length, 6))
            count = max_p_length
            if len(palette.tree[0]) < max_p_length:
                count = len(palette.tree[0])
            palette_mat[:len(palette.merge_dists), 0] = palette.merge_dists
            palette_mat[:count, 1] = palette.tree[0][:count]
            palette_mat[:count, 2:5] = palette.tree[1][:count]
            palette_mat[:count, 5] = palette.tree[2][:count]

            yielded_result = dict(frame_pos=i + start,
                                  time_ms=frame2ms(i + start, fps),
                                  hist=hist,
                                  palette=palette_mat,
                                  features=feature_mat,
                                  spatial_edge = np.array([np.amax(edenorm), np.mean(edenorm)],dtype=np.float32),
                                  spatial_color=np.array([np.amax(cdenorm), np.mean(cdenorm)], dtype=np.float32),
                                  spatial_hue = np.array([np.amax(hdenorm), np.mean(hdenorm)], dtype=np.float32),
                                  spatial_luminance = np.array([np.amax(ldenorm), np.mean(ldenorm)], dtype=np.float32))
            callback.emit([yielded_result, (i + start) / end])

            hist_counter += 1
            progress_counter += 1

    @pyqtSlot(object)
    def colormetry_callback(self, yielded_result):
        self.colormetry_analysis.append_data(yielded_result)
        self.main_window.timeline.timeline.set_colormetry_progress(yielded_result.time_ms / self.duration)

    @pyqtSlot()
    def abort(self):
        self.aborted = True



