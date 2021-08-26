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
        self.movie_meta = dict()
        self.reference_frame = reference_frame

        for key, val in kwargs:
            if hasattr(self, key):
                setattr(self, key, val)

    def import_(self, file_path, sfilter=None, **kwargs):
        self.fixations = pd.read_csv(file_path, **kwargs)
        if sfilter is not None:
            self.fixations = self.fixations[self.fixations['Stimulus'].str.contains(sfilter)]


    def import_movie_meta(self, files):
        """
        imports the necessary information about the movies for later computation.
        namely FPS, frame wirdth and frame height.

        :param files: a list of absolutoe paths to the files
        :return: a dict where dict(file_name:dict(metadata:keys))

        """
        for f in files:
            try:
                cap = cv2.VideoCapture(f)
                self.movie_meta[os.path.splitext(os.path.split(f)[1])[0]] = dict(
                    fps = cap.get(cv2.CAP_PROP_FPS),
                    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                    path= f
                )
            except Exception as e:
                print(e)
                continue
        return self.movie_meta


    def subsample(self, sample_fps = 0):
        """-+6*-+
        .30
        Samples the fixations to a given frame_rate
Exception   Q        :param sample_fps: the sampling frequency, if higher than the FPS of the segmented movie, it is clamped, if sample_fps = 0, the frame rate is used, default: 0
        :return:
        """
        if self.fixations is None:
            raise ValueError("Import he fixations first")
        if self.movie_meta is None:
            raise ValueError("Import the movie meta data first")

        self.fixations_sampled = pd.DataFrame(["Stimulus", "FixationX", "FixationY", "FramePos", "Variant"])
        print(self.fixations_sampled)

        result = dict()

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

            if stimulus not in self.movie_meta:
                print("Stimulus {f} not in passed movie files.".format(f=stimulus))
                continue

            width = self.movie_meta[stimulus]['width']
            height = self.movie_meta[stimulus]['height']

            fw = width / self.reference_frame[0]
            fh = height / self.reference_frame[1]

            if stimulus not in result:
                result[stimulus] = []

            n = ms_to_frames(t1 - t0, self.movie_meta[stimulus]['fps'])
            if sample_fps != 0:
                n = int(np.floor(n / sample_fps))
                f_step = sample_fps
            else:
                f_step = 1

            f0 = ms_to_frames(t0, self.movie_meta[stimulus]['fps'])
            # print(n)

            for i in range(n):
                result[stimulus].append(dict(
                    Stimulus = stimulus,
                    Variant = is_bw,
                    FixationX=int(x * fw),
                    FixationY=int(y * fh),
                    FramePos = f0 + (i * f_step)
                ))

        final = dict()
        for k, v in result.items():
            final[k] = dict(
                df = pd.DataFrame(v),
                stimulus = self.movie_meta[k]
            )
        return final


if __name__ == '__main__':
    files = glob.glob("E:/Programming/Datasets/eye-tracking/*.mp4")

    XEye = XEyeTrackingHandler("../resources/eyetracking/segmentation.hdf5")
    XEye.import_("eyetracking-fixations.txt", delimiter="\t")
    XEye.import_movie_meta(files)
    print(XEye.movie_meta)
    XEye.subsample()

    # XEye.print_hdf5()
