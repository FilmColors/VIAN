import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap
import sys

def frame_to_timecode(frame, fps):
    return 0


def print_size_mb(numpyarr):
    print(round(numpyarr.nbytes / 1000000, 3), "MB")


def numpy_to_pixmap(arr, cvt = cv2.COLOR_BGR2RGB, target_width = None, with_alpha = False):
    """
    Converts a numpy Image to a QPixmap. 
    
    :param arr: the numpy array
    :param cvt: Should the array be Converted before the the QPixmap is created. Default is BGR2RGB
    :param target_width: If not None, the Image will be resized to a certain width, mainting Aspect-Ratio
    :param with_alpha: If the output QPixmap should have an Alpha-Channel. Make sure to hand in an Image with four 
    Channels or Convert it accordingly
    :return: A QPixmap of the same image
    """
    if cvt is not None:
            arr = cv2.cvtColor(arr, cvt)

    if target_width is not None:
        factor = float(target_width) / arr.shape[1]
        arr = cv2.resize(arr, None, None, factor, factor, cv2.INTER_CUBIC)

    if not with_alpha:
        qimage = QImage(arr, arr.shape[1], arr.shape[0], arr.shape[1] * 3, QImage.Format_RGB888)
        qpixmap = QPixmap(qimage)
    else:
        qimage = QImage(arr, arr.shape[1], arr.shape[0], arr.shape[1] * 4, QImage.Format_RGBA8888)
        qpixmap = QPixmap(qimage)

    return qpixmap


def tpl_bgr_to_lab(bgr):
    """
    Converts a BGR Color Tuple to a uint8 Lab Color Tuple using OpenCV Conversion.
    :param tpl: Input Tuple BGR
    :return: Output Tuple Lab
    """
    img = bgr.astype(np.float32) / 255
    lab = cv2.cvtColor(np.array([[img] * 2] * 2), cv2.COLOR_BGR2Lab)[0, 0,:]
    return lab


def frame2ms(frame, fps):
    return int(round(int(frame) * 1000.0 / fps,0))

def ms2frames(time, fps):
    return int(float(time) / 1000 * fps)


def tpl_bgr_to_lch(tpl):
    """
    Converts a BGR Color Tuple to a float32 Lab Color Tuple using OpenCV Conversion.
    :param tpl: Input Tuple BGR
    :return: Output Tuple LCH, float32
    """

    lab = tpl_bgr_to_lab(tpl)
    lch = np.empty(lab.shape, dtype=np.float32)
    lch[:, 0] = lab[:, 0]
    lch[:, 1] = np.linalg.norm(lab[:, 1:3], axis=1)
    lch[:, 2] = np.arctan2(lab[:, 2], lab[:, 1])
    return lch


def lab_to_lch(lab):
    """
    Converts an OpenCV Lab Color to a lch Color
    :param lab: 
    :return: 
    """
    lch = np.empty(lab.shape, dtype=np.float32)
    lch[:, 0] = lab[:, 0]
    lch[:, 1] = np.linalg.norm(lab[:, 1:3], axis=1)
    lch[:, 2] = np.arctan2(lab[:, 2], lab[:, 1])
    return lch


def calculate_histogram(image_stack, n_bins=16, range_min=0, range_max=255, normalization_factor = 0):
    """
    Calculates the 3d histogram of a stack of images

    :param image_stack: a numpy array of images with the shape (n_images, image_width, image_height, 3)
    :param n_bins: the number of bins created in each axis
    :param range_min: the lowest value to include
    :param range_max: the highest value to include
    :param normalization_factor: if set, the histogram will be divided by normalization_factor.
    :return: a numpy array with 3 dimensions 

    """
    if len(image_stack.shape) > 2:
        # Reshaping to a a linear array of colors
        if not len(image_stack.shape) == 4:
            data = np.resize(image_stack, (image_stack.shape[0] * image_stack.shape[1], 3)).astype(np.uint8)
        else:
            data = np.resize(image_stack,
                             (image_stack.shape[0] * image_stack.shape[1] * image_stack.shape[2], 3)).astype(np.uint8)
    else:
        data = image_stack
    # Calculating the Histogram

    hist = cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                        [n_bins, n_bins, n_bins],
                        [range_min, range_max, range_min, range_max,
                         range_min, range_max])

    if normalization_factor != 0:
        hist = np.divide(hist, normalization_factor)

    return hist.astype(np.uint64)


def movie_lengths(movie_list):
    for m in movie_list:
        cap = cv2.VideoCapture(m)
        print(m.split("\\").pop().rjust(50), "\t", str(cap.get(cv2.CAP_PROP_FRAME_COUNT)))


def read_movie_with_callback(path, callback, start = 0, resolution = 1):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    for i in range(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) - start)):
        ret, frame = cap.read()
        if i % resolution == 0:
            callback(frame)


def qt_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def lab_to_sat(lab, implementation = "luebbe"):
    """
    https://en.wikipedia.org/wiki/Colorfulness#Chroma_in_CIE_1976_L*a*b*_and_L*u*v*_color_spaces
    Eva Lübbe: Colours in the Mind - Colour Systems in Reality- A formula for colour saturation. [Book on Demand]
    
    :param lch: 
    :return: 
    """
    a_sq = np.square(lab[:, 1])
    b_sq = np.square(lab[:, 2])
    chroma = np.sqrt(np.add(a_sq, b_sq))

    if implementation == "luebbe":
        div = np.add(np.square(chroma), np.square(lab[:, 0]))
        div = np.sqrt(div)
        return np.divide(chroma, div)

    elif implementation == "barbara":
        return np.sqrt(np.add(np.square(chroma), np.square(lab[:, 0])))
    else:
        return np.divide(chroma, lab[:, 0])


def lch_to_sat(lch, implementation = "luebbe"):
    lum = lch[:, 0]
    chroma = lch[:, 1]
    hue = lch[:, 2]

    if implementation == "luebbe":
        result =  chroma / np.sqrt((chroma ** 2) + (lum ** 2))

    else: # implementation == "pythagoras":
        result =  np.sqrt(np.square(chroma) + np.square(lum)) - lum
    np.nan_to_num(result)
    return result


def resize_to_width(img, width):
    thumb_width = width
    thumb_height = int(width / img.shape[1] * img.shape[0])
    return cv2.resize(img, (thumb_width, thumb_height), cv2.INTER_CUBIC)


def bgr_to_float(bgr):
    return np.divide(bgr.astype(np.float32), 255)


def binary_masks_to_labels(binary_masks):
    res = np.amax(binary_masks, axis=2)

import glob, os
def all_test_images():
    print("../../input/images/*" + ".jpg")
    files = glob.glob("../../input/images/*" + ".jpg")
    return files