"""
The Computation Module contains a list of often used operations in VIAN.
These operations can be of arbitrary type and are not categorized. 
"""

from PyQt5.QtGui import QImage
from PyQt5.QtGui import QImage, QPixmap, QIcon
import subprocess
import cv2
# import matplotlib.pyplot as plt
import numpy as np
import cv2
import sys
import argparse
import os
import webbrowser
import shutil
from zipfile import ZipFile

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


def tpl_bgr_to_lab(bgr):
    """
    Converts a BGR Color Tuple to a uint8 Lab Color Tuple using OpenCV Conversion.
    :param tpl: Input Tuple BGR
    :return: Output Tuple Lab
    """
    if not isinstance(bgr, np.ndarray):
        bgr = np.array(bgr)
    img = bgr.astype(np.float32) / 255
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
            arr = cv2.cvtColor(arr,cvt)

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
    return int(float(time) / 1000 * fps)


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
    icon = QIcon(path)
    # print icon.availableSizes()
    return icon


def version_check(smaller_than, version):
    if isinstance(version, str):
        version = version.split(".")
    version = [int(version[0]), int(version[1]), int(version[2])]

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
        print(e)
        return False


def extract_zip(zipfilepath, extractiondir):
    zip = ZipFile(zipfilepath)
    zip.extractall(path=extractiondir)
    print("Extraction finished")

def is_subdir(path, directory):
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    relative = os.path.relpath(path, directory)
    return not relative.startswith(os.pardir + os.sep)

