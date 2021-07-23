"""
The Computation Module contains a list of often used operations in VIAN.
These operations can be of arbitrary type and are not categorized. 
"""
from datetime import datetime

from PyQt5.QtGui import QImage
from PyQt5.QtGui import QImage, QPixmap, QIcon
from core.data.log import *
import PyQt5.QtCore as QtCore
import subprocess
import cv2
import inspect
import importlib
import random

# import matplotlib.pyplot as plt
import numpy as np
import cv2
import sys
import argparse
import os
import webbrowser
import shutil
from zipfile import ZipFile
import math
from scipy.signal import kaiserord, lfilter, firwin, freqz

def is_vian_light():
    return os.environ.get("VIAN_LIGHT") is not None


def tuple2point(tpl):
    return QtCore.QPoint(tpl[0], tpl[1])


def ms2datetime(time_ms):
    return time_ms
    return datetime.utcfromtimestamp(int(time_ms / 1000))


def cart2pol(x, y):
    """
    Converts two dimensional cartesian coordinates to polar coordinates
    :param x: 
    :param y: 
    :return: 
    """
    rho = np.sqrt(x**2 + y**2)
    phi = np.arctan2(y, x)
    return(rho, phi)


def ms_to_string(ms, include_ms = False, include_frame = False, fps = 24):
    """
    Converts an Long int MS to a formatted string of type HH:MM:SS:(MS) 
    
    :param ms: the ms to convert
    :param include_ms: if the MS should be included at the end of the string
    :param include_frame: if the frame should be included at the end
    :param fps: the fps of the movie to convert the frame if needed
    :return: A string of selected format
    """
    ms = int(ms)
    seconds = (ms // 1000) % 60
    minutes = (ms // (1000 * 60)) % 60
    hours = (ms // (1000 * 60 * 60)) % 24

    r = ms - (hours * 60 * 60 * 1000 + minutes * 60 * 1000 + seconds * 1000)
    if include_ms:
        return str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2) + ":" + str(r).zfill(3)
    elif include_frame:
        frame = int(r / 1000 * fps)
        return str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2) + ":" + str(frame).zfill(2)
    else:
        return str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2)


def ts_to_ms(hour=0, min=0, sec=0, ms=0):
    """
    Converts a Timestamp to miliseconds
    :param hour: The given hours
    :param min: The given minutes
    :param sec: The given Seconds
    :param ms: The fiven MS
    :return: A int long MS
    """
    hour = int(hour)
    min = int(min)
    sec = int(sec)
    ms = int(ms)

    time = hour * 60 * 60 * 1000
    time += min * 60 * 1000
    time += sec * 1000
    time += ms
    return time


def tpl_bgr_to_lab(bgr, as_float = True):
    """
    Converts a BGR Color Tuple to a uint8 Lab Color Tuple using OpenCV Conversion.
    :param tpl: Input Tuple BGR
    :return: Output Tuple Lab
    """
    if not isinstance(bgr, np.ndarray):
        bgr = np.array(bgr)
    if as_float:
        img = bgr.astype(np.float32) / 256
    else:
        img = bgr
    lab = cv2.cvtColor(np.array([[img] * 2] * 2), cv2.COLOR_BGR2Lab)[0, 0,:]
    return lab


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


def lab_to_sat(lch = None, lab = None, implementation = "luebbe"):

    if lch is not None:
        if len(lch.shape) < 2:
            lch = np.array([lch])
        lum = lch[:, 0]
        chroma = lch[:, 1]
        hue = lch[:, 2]

    elif lab is not None:
        if len(lab.shape) < 2:
            lab = np.array([lab])
        lum = lab[:, 0]
        a_sq = np.square(lab[:, 1])
        b_sq = np.square(lab[:, 2])
        chroma = np.sqrt(np.add(a_sq, b_sq))

    if implementation == "luebbe":
        result =  chroma / np.sqrt((chroma ** 2) + (lum ** 2))

    elif implementation == "phytagoras": # implementation == "pythagoras":
        result =  np.sqrt(np.square(chroma) + np.square(lum)) - lum

    else:
        result = chroma
        # angle = np.dot(np.stack((chroma, lum), axis=1), [0, 1])
        # result = angle * chroma
    # print(angle)
    np.nan_to_num(result)
    return result


def lab_to_lch(lab, human_readable = False):
    """
    Converts LAB to LCH, if human readable is true:
    L: {0,...,100}
    C: {0, 100}
    H: {0, 360}

    else:
    L: {0,...,100}
    C: {0, sqrt(128**2 + 128**2) == 181.019}
    H: {-np.pi, np.pi}

    :param lab:
    :param human_readable:
    :return:
    """
    if not isinstance(lab, np.ndarray):
        lab = np.array(lab)

    if len(lab.shape) > 1:
        lch = np.empty(lab.shape, dtype=np.float32)
        lch[:, 0] = lab[:, 0]
        lch[:, 1] = np.linalg.norm(lab[:, 1:3], axis=1)
        lch[:, 2] = np.arctan2(lab[:, 2], lab[:, 1])
    else:
        lch = np.empty(lab.shape, dtype=np.float32)
        lch[0] = lab[0]
        lch[1] = np.linalg.norm(lab[1:3])
        lch[2] = np.arctan2(lab[2], lab[1])

    if human_readable:
        lch = lch_to_human_readable(lch)
    return lch


def lch_to_human_readable(lch):
    """
    Converts LCH to human readable:
    L: {0,...,100}
    C: {0, 100}
    H: {0, 360}

    :param lch:
    :return:
    """
    if not isinstance(lch, np.ndarray):
        lch = np.array(lch)

    lch[..., 1] = lch[..., 1] / np.sqrt(128**2 + 128**2) * 100.0
    lch[..., 2] = np.rad2deg(lch[..., 2]) % 360
    return lch


def numpy_to_qt_image(arr, cvt = cv2.COLOR_BGR2RGB, target_width = None, with_alpha = False):
    """
    Converts a Numpy Image array to a QTImage
    :param arr: The nUmpy array 
    :param cvt: A OpenCV Convertion if needed else NONE
    :param target_width: The width of the final Image
    :param with_alpha: if the alpha should be included
    :return: (qimage, qpixmap) tuple
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
    return qimage, qpixmap


def numpy_to_pixmap(arr, cvt = cv2.COLOR_BGR2RGB, target_width = None, with_alpha = False):
    """
    Converts a Numpy Image array to a QPixmap
    :param arr: The nUmpy array 
    :param cvt: A OpenCV Convertion if needed else NONE
    :param target_width: The width of the final Image
    :param with_alpha: if the alpha should be included
    :return: QPixmap
    """

    if cvt is not None:
            arr = cv2.cvtColor(arr,cvt)

    if target_width is not None:
        factor = float(target_width) / arr.shape[1]
        arr = cv2.resize(arr, None, None, factor, factor, cv2.INTER_CUBIC)

    if not with_alpha or arr.shape[2] < 4:
        qimage = QImage(arr, arr.shape[1], arr.shape[0], arr.shape[1] * 3, QImage.Format_RGB888)
        qpixmap = QPixmap(qimage)
    else:
        qimage = QImage(arr, arr.shape[1], arr.shape[0], arr.shape[1] * 4, QImage.Format_RGBA8888)
        qpixmap = QPixmap(qimage)

    return qpixmap


def pixmap_to_numpy(pixmap: QPixmap):
    """
    Converts a Pixmap to a numpy array
    :param pixmap: the Pixmap
    :return: a numpy array
    """
    return convertQImageToMat(pixmap.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied))


def convertQImageToMat(qimage):
    '''  Converts a QImage into an opencv MAT format  '''

    width = qimage.width()
    height = qimage.height()

    ptr = qimage.bits()
    ptr.setsize(qimage.byteCount())

    if qimage.format() == QImage.Format_ARGB32_Premultiplied:
        arr = np.array(ptr).reshape(height, width, 4)  #  Copies the data
    else:
        arr = np.array(ptr).reshape(height, width, 3)
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGRA)
    return arr


def blend_transparent(background, foreground):
    """
    Alpha blending of to images
    :param background: foreground with alpha
    :param foreground: background with no alpha
    :return: a blended image
    """
    alpha = foreground[:,:,3:]

    # Convert uint8 to float
    foreground = foreground[:,:,:3].astype(float)
    background = background.astype(float)

    # Normalize the alpha mask to keep intensity between 0 and 1
    alpha = alpha.astype(float) / 255

    # Multiply the foreground with the alpha matte
    foreground = np.multiply(alpha, foreground)

    # Multiply the background with ( 1 - alpha )
    background = np.multiply(1.0 - alpha, background)

    # Add the masked foreground and background.
    outImage = np.add(foreground, background).astype(np.uint8)

    return outImage


def get_mouse_handle_by_location(pos, rect, border_size = 0.1, corner_size = 0.1, min_size = 40):
    """
    Returns a String of where the mouse is regarding to some center
    
    :param pos: 
    :param rect: 
    :param border_size: 
    :param corner_size: 
    :param min_size: 
    :return: 
    """
    x = pos.x()
    y = pos.y()
    width = rect.width()
    height = rect.height()
    center_x = width/2
    center_y = height/2

    lower = False
    upper = False
    left = False
    right = False

    is_too_small = False
    if width < min_size or height < min_size:
        border_size = 0.5
        corner_size = 0.5
        is_too_small = True
    # Getting the Side of the Mouse
    # Right Side

    if x > width - int(float(width) * border_size):
        right = True

    # Left Side
    if x < int(float(width) * corner_size):
        left = True

    # Lower Side
    if y > height - int(float(height) * border_size):
        lower = True

    # Upper Side
    if y < int(float(height) * border_size):
        upper = True

    if not is_too_small:
        if right and upper:
            return "UpperRightCorner"
        if right and lower:
            return "LowerRightCorner"
        if left and lower:
            return "LowerLeftCorner"
        if left and upper:
            return "UpperLeftCorner"

    if upper:
        return "UpperBorder"
    if right:
        return "RightBorder"
    if lower:
        return "LowerBorder"
    if left:
        return "LeftBorder"

    return "Center"


def ms_to_frames(time, fps):
    """
    Converts Miliseconds to Frames
    :param time: Time MS
    :param fps: FPS of the Film
    :return: returns a FRAME IDX
    """
    return int(round(float(time) / 1000 * fps))


def frame2ms(frame, fps):
    """
    Converts a Frame IDX to MS
    :param frame: THE Frame IDX
    :param fps: FPS of the Film
    :return: Milliseconds of the Frame IDX
    """
    return int(round(int(frame) * 1000.0 / fps,0))


def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err = np.divide(err, float(imageA.shape[0] * imageA.shape[1]))

    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err


def compare_images(imageA, imageB):
    # compute the mean squared error and structural similarity
    # index for the images
    m = mse(imageA, imageB)

    # Slower
    # s = ssim(imageA, imageB)

    return m


def find_time_of_screenshot(movie, shot, start, end):
    # import the necessary packages
    # construct the argument parse and parse the arguments

    video_capture = cv2.VideoCapture(movie)
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)
    length = end - start
    x_res = 10**6
    frame_index = -1
    gray_shot = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)

    for i in range(length):
        if i%100 == 0:
            sys.stdout.write("\r" + str(float(i) / length * 100))
        # grab the current frame
        ret, frame = video_capture.read()
        if ret is None:
            break
        image = frame
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray_shot.shape
        resized_image = cv2.resize(gray, (width, height))
        x = mse(resized_image, gray_shot)
        if x < x_res:
            x_res = x
            frame_index = i + start

    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = video_capture.read()

    cv2.waitKey()

    video_capture.release()
    return frame_index


def parse_file_path(path):
    if sys.platform =="darwin":
        return str(path.replace("file://", ""))
    else:
        return str(path.replace("file:///", ""))


def create_icon(path):
    # h_dir = os.path.join("qt_ui", "icons", "hdpi")
    # if not os.path.isdir(os.path.join("qt_ui", "icons", "hdpi")):
    #     os.mkdir(h_dir)
    #
    # f, end = os.path.split(path)[1].split(".")
    # h_file = f + "@2x." + end
    # h_path = os.path.join(h_dir, h_file)
    # if not os.path.isfile(h_path):
    #     shutil.copy2(path,h_path)
    icon = QIcon(path)
    # icon.addFile(h_path)

    return icon


def version_check(smaller_than, version):
    if isinstance(version, str):
        version = version.split(".")
    version = [int(v) for v in version]

    if isinstance(smaller_than, str):
        smaller_than = smaller_than.split(".")
    smaller_than = [int(v) for v in smaller_than]

    if version[0] < smaller_than[0]:
        return True
    elif version[0] == smaller_than[0]:
        if version[1]< smaller_than[1]:
            return True
        elif version[1] == smaller_than[1]:
            if version[2] < smaller_than[2]:
                return True

    return False


def open_web_browser(file_path):
    if sys.platform == "darwin":  # check if on OSX
        file_path = "file:///" + file_path
    webbrowser.get().open(file_path)


def find_closest(frame, segment):
    a = np.sum((segment - frame[np.newaxis, ...]) ** 2, axis=(1, 2, 3))
    match = np.argmin(a)
    rate = np.amin(a)
    return match, rate


def open_file(file_name):
    try:
        if sys.platform == "win32":
            os.startfile(file_name)
        else:
            opener ="open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, file_name])
        return True
    except Exception as e:
        log_error(e)
        return False


def extract_zip(zipfilepath, extractiondir):
    zip = ZipFile(zipfilepath)
    zip.extractall(path=extractiondir)
    log_info("Extraction finished")


def is_subdir(path, directory):
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    relative = os.path.relpath(path, directory)
    return not relative.startswith(os.pardir + os.sep)


def images_to_movie(imgs, out_file, time_scale = 180, fps = 30.0, size = (640,480), codec = 'MJPG'):
    """
    Creates a movie from a list of numpy images
    :param imgs: a list of numpy images
    :param out_file: the name of the output file
    :param time_scale: How often an image should be repeated before the next one is drawn
    :param fps: the FPS of the movie
    :param size: the size of the movie
    :param codec: the Codec
    :return: 
    """
    if size is None:
        size = (imgs[0].shape[0], imgs[0].shape[1])
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(out_file, fourcc, fps, size)
    for img in imgs:
        for t in range(time_scale):
            img = cv2.resize(img, size, interpolation=cv2.INTER_CUBIC)
            writer.write(img)
    writer.release()


def labels_to_binary_mask(multi_mask, labels, as_bool = False):
    """
    Converts a Label Mask to a binary mask with all indices that have a value which is in labels are set to True
    else 0. 
    
    :param multi_mask: 
    :param labels: 
    :return: 
    """
    result = np.zeros_like(multi_mask, dtype=np.uint8)
    for i in labels:
        result[np.where(multi_mask == i)] = 255
    if as_bool:
        return result.astype(np.bool)
    return result


def apply_mask(img, mask, indices, mask_size = 100):
    if len(mask.shape) > 2:
        mask = cv2.cvtColor(mask ,cv2.COLOR_BGR2GRAY)
    # if mask.shape[0] != img.shape[0] and mask.shape[1] != img.shape[1]:
    #     mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    mask = cv2.resize(mask, (mask_size, mask_size), interpolation=cv2.INTER_NEAREST)
    bin_mask = labels_to_binary_mask(mask, indices)
    bin_mask = cv2.resize(bin_mask, img.shape[:2][::-1], interpolation=cv2.INTER_NEAREST)

    alpha = np.zeros(img.shape[:2], dtype=np.uint8)
    alpha[np.nonzero(bin_mask)] = 255
    result = np.dstack((img, alpha))
    return result


def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


def overlap_rect(r1, r2):
    '''Overlapping rectangles overlap both horizontally & vertically
    '''

    if (r1[0] > r2[0] + r2[2]) or (r1[0] + r1[2] < r2[0]):
        return False

    if (r1[1] < r2[1] + r2[3]) or (r1[1] + r1[3] < r2[1]):
        return False
    return True


def contains_rect(r1, r2):
    if (r1[0] > r2[0]) and r1[1] > r2[1] and r1[2] < r2[2] and r1[3] < r2[3]:
        return True

    if (r2[0] > r1[0]) and r2[1] > r1[1] and r2[2] < r1[2] and r2[3] < r1[3]:
        return True
    return False


def get_heatmap_value(val, max = 1.0, asuint8=True, asrgb = True, gray = False):
    result = np.zeros(shape=(3), dtype=np.float32)
    if gray:
        result.fill(val/max)
    else:
        result[2] = ((np.clip(val, 0.5, 1.0) - 0.5) / 0.5) * max
        result[1] = (0.25 - np.abs(np.clip(val, 0.25, 0.75) - 0.5)) / 0.25 * max
        result[0] = ((0.5 - np.clip(val, 0, 0.5)) / 0.5)

    if asuint8:
        result *= 255
    if asrgb:
        result = result[::-1]
    return result


def floatify_img(img):
    return img.astype(np.float32) / 255


def handle_exception(func_name, e):
    text = "Exception in\t" + str(inspect.stack()[0][3]).rjust(25) + "with message:\t" + str(e)
    print("handle_exception", text)


def import_module_from_path(path):
    spec = importlib.util.spec_from_file_location("current_pipeline_module", path)
    foo = importlib.util.module_from_spec(spec)
    sys.modules["current_pipeline_module"] = foo
    spec.loader.exec_module(foo)


def generate_id(not_list = None):
    if not_list is None:
        not_list = []

    new_id = random.randint(0, 9999999)
    while new_id in not_list:
        new_id = random.randint(0, 9999999)

    return new_id


def get_colormap(n=12, map="gist_ncar"):
    try:
        from matplotlib import cm

        viridis = cm.get_cmap(map, n)
        res = []
        for i in range(n):
            res.append(viridis(i / n))
        return res
    except:
        res = []
        for i in range(n):
            res.append(np.random.random(3))
        return res


def resize_with_aspect(img, width = None, height = None, mode=cv2.INTER_CUBIC):
    if width is not None:
        fy = width / img.shape[1]
    elif height is not None:
        fy = width / img.shape[0]
    else:
        raise ValueError("Either width or height have to be given")

    return cv2.resize(img, None, None, fy, fy, mode)


def fir_lowpass_filter(sample_rate):
    # The Nyquist rate of the signal.
    nyq_rate = sample_rate / 2.0

    # The desired width of the transition from pass to stop,
    # relative to the Nyquist rate.  We'll design the filter
    # with a 5 Hz transition width.
    width = 5.0 / nyq_rate

    # The desired attenuation in the stop band, in dB.
    ripple_db = 60.0

    # Compute the order and Kaiser parameter for the FIR filter.
    N, beta = kaiserord(ripple_db, width)

    # The cutoff frequency of the filter.
    cutoff_hz = 10.0

    # Use firwin with a Kaiser window to create a lowpass FIR filter.
    taps = firwin(N, cutoff_hz / nyq_rate, window=('kaiser', beta))

    # Use lfilter to filter x with the FIR filter.
    filtered_x = lfilter(taps, 1.0, x)


def is_gui():
    return "VIAN_GUI" in os.environ