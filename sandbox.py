import cv2
import numpy as np


def detect_letterbox(movie_path, n_samples=100) -> dict:
    """
    Attempts to detect the letterbox by thresholding the mean of multiple slices

    :param movie_path:
    :param n_samples:
    :return:
    """
    cap = cv2.VideoCapture(movie_path)
    ret, frame = cap.read()
    samples = []
    for i in range(n_samples):
        f_idx = int(np.floor(cap.get(cv2.CAP_PROP_FRAME_COUNT) * (i / n_samples)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if frame is None:
            continue
        samples.append(cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_BGR2LAB))
    frame = np.array(samples)[..., 0]
    variance = np.mean(frame, axis=0)
    variance -= np.amin(variance)
    variance /= np.amax(variance)
    cv2.imshow(f"out_t_var", variance)
    ret, thresh = cv2.threshold(variance, 0.1, 1, cv2.THRESH_BINARY)
    if np.mean(thresh) == 1.0:
        return dict(left = 0, right=0, top=0, bottom=0)
    else:

        # We search for the first pixel from each border which is > 0
        left = thresh[thresh.shape[0] // 2].tolist().index(1.0)
        right = thresh[thresh.shape[0] // 2][::-1].tolist().index(1.0)
        top = thresh[:, thresh.shape[0] // 2].tolist().index(1.0)
        bottom = thresh[:, thresh.shape[0] // 2][::-1].tolist().index(1.0)
        return dict(left = left, right=right, top=top, bottom=bottom)

detect_letterbox("/Users/Gaudenz/Documents/movies/96_1_1_MOV.mov")