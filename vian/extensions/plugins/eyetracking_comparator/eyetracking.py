import os
import glob

import pandas as pd
import numpy as np
import h5py
import cv2
from core.data.computation import ms_to_frames


class XEyeTrackingHandler():
    def __init__(self, reference_frame = (1680, 1050), **kwargs):
        super(XEyeTrackingHandler, self).__init__()

        self.show_live = False
        self.movie_meta = None
        self.reference_frame = reference_frame

        for key, val in kwargs:
            if hasattr(self, key):
                setattr(self, key, val)

    def import_(self, file_path, **kwargs):
        # df_participants = pd.read_csv(DATA_ROOT + "/tabular/eyetracking-participants.txt", delimiter="\t")
        self.fixations = pd.read_csv(file_path, **kwargs)

    def import_movie_meta(self, files):
        """
        imports the necessary information about the movies for later computation.
        namely FPS, frame wirdth and frame height.

        :param files: a list of absolutoe paths to the files
        :return: a dict where dict(file_name:dict(metadata:keys))

        """
        for f in files:
            cap = cv2.VideoCapture(f)
            self.movie_meta[os.path.splitext(os.path.split(f)[1])[0]] = dict(
                fps = cap.get(cv2.CAP_PROP_FPS),
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            )
        return self.movie_meta


    def subsample(self, sample_fps = 0):
        """
        Samples the fixations to a given frame_rate
        :param sample_fps: the sampling frequency, if higher than the FPS of the segmented movie, it is clamped, if sample_fps = 0, the frame rate is used, default: 0
        :return:
        """
        if self.fixations is None:
            raise ValueError("Import he fixations first")
        if self.movie_meta is None:
            raise ValueError("Import the movie meta data first")

        self.fixations_sampled = pd.DataFrame(["Stimulus", "FixationX", "FixationY", "FramePos", "isBlackWhite"])
        print(self.fixations_sampled)

        q = []

        for index, r in self.fixations.iterrows():
            try:
                is_bw = "bw_" in r.Stimulus
                stimulus = os.path.splitext(r['Stimulus'])[0].replace("bw_", "")
                x = int(round(float(r['Fixation Position X [px]'])))
                y = int(round(float(r['Fixation Position Y [px]'])))
                t0 = int(round(float(r['Event Start Trial Time [ms]'])))
                t1 = int(round(float(r['Event End Trial Time [ms]'])))
            except Exception as e:
                print (e)
                continue

            n = ms_to_frames(t1 - t0, self.movie_meta[stimulus]['fps'])
            if sample_fps != 0:
                n = int(np.floor(n / sample_fps))
                f_step = sample_fps
            else:
                f_step = 1

            f0 = ms_to_frames(t0, self.movie_meta[stimulus]['fps'])
            # print(n)

            for i in range(n):
                q.append(dict(
                    Stimulus = stimulus,
                    isBlackWhite = is_bw,
                    FixationX = x,
                    FixationY = y,
                    FramePos = f0 + (i * f_step)
                ))

        self.fixations_sampled = pd.DataFrame(q)
        self.fixations = self.fixations_sampled


if __name__ == '__main__':
    files = glob.glob("E:/Programming/Datasets/eye-tracking/*.mp4")

    XEye = XEyeTrackingHandler("../resources/eyetracking/segmentation.hdf5")
    XEye.import_("../resources/eyetracking/tabular/eyetracking-fixations.txt", delimiter="\t")
    XEye.import_movie_meta(files)
    print(XEye.movie_meta)
    XEye.subsample()
    XEye.save("../resources/eyetracking/tabular/eyetracking-fixations-sampled.txt")
    XEye.evaluate()
    XEye.save("../resources/eyetracking/tabular/eyetracking-fixations-labeled.txt")

    # XEye.print_hdf5()
