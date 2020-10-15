import cv2
import numpy as np

from core.data.computation import resize_with_aspect


def preprocess_frame(frame, max_width=1920, mode=cv2.INTER_CUBIC):
    if frame.shape[1] > max_width:
        frame = resize_with_aspect(frame, width=max_width, mode=mode)
    return frame
