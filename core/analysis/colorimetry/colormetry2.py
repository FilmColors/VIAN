from core.data.containers import VIANProject
from core.data.interfaces import IConcurrentJob
from core.analysis.colorimetry.computation import calculate_histogram
import cv2
import numpy as np


class ColormetryJob():
    def __init__(self, resolution, main_window):
        self.resolution = resolution
        self.colormetry_analysis = None

    def prepare(self, project:VIANProject):
        self.colormetry_analysis = project.create_an

    def run_concurrent(self, args, callback):
        movie_path = args[0]
        start = args[1]
        end = args[2]
        color_space = args[3]
        resolution = args[4]
        parameters = args[5]
        fps = args[6]

        length = np.clip(int(end - start), 1, None)
        data_size = int(np.ceil(length / resolution))
        video_capture = cv2.VideoCapture(movie_path)

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame_pos = np.zeros(shape=(data_size, 1), dtype=np.uint16)
        hist_stack = np.zeros(shape=(data_size, 16, 16, 16), dtype=np.float16)
        avg_color_tuples = np.zeros(shape=(data_size, 3), dtype=np.uint8)

        progress_counter = 0
        hist_counter = 0

        for i in range(length):
            ret, frame = video_capture.read()
            if i % resolution == 0:

                if progress_counter % 2 == 0:
                    progress = float(i) / length
                    sign_progress(progress)

                if frame is not None:
                    # Colorspace Conversion
                    frame_pos[hist_counter] = i
                    frame_lab = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)

                    # Histogram
                    hist = calculate_histogram(frame_lab, 16)
                    hist_stack[hist_counter] = hist

                    # AVG Color
                    avg_color_tuples[hist_counter] = np.mean(frame_lab, axis=(0, 1))

                    hist_counter += 1

                progress_counter += 1

        #Normalize the Hist
        hist_stack = np.divide(hist_stack, (width * height))
        print(hist_stack.nbytes / 1000000, "MB")

    def callback(self, timestep_data):



