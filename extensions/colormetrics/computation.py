# Gaudenz Halter University of Zurich, 2017
# Semester Thesis: "Color Palettes in Movies"
#
# This File contains all functions that are used to compute arbitary data on the movies


import math
import os
import csv
import sys
from random import randint

import cv2
import numpy as np


def calculate_histogram(image_stack, n_bins = 16, range_min = 0, range_max = 255):
    """
    Calculates the 3d histogram of a stack of images
    
    :param image_stack: a numpy array of images with the shape (n_images, image_width, image_height, 3)
    :param n_bins: the number of bins created in each axis
    :param range_min: the lowest value to include
    :param range_max: the highest value to include
    :return: a numpy array with 3 dimensions 
    
    """
    if len(image_stack.shape) > 2:
        # Reshaping to a a linear array of colors
        if not len(image_stack.shape) == 4:
            data = np.resize(image_stack, (image_stack.shape[0] * image_stack.shape[1], 3))
        else:
            data = np.resize(image_stack, (image_stack.shape[0] * image_stack.shape[1] * image_stack.shape[2], 3))
    else:
        data = image_stack
    # Calculating the Histogram
    hist = cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                        [n_bins, n_bins, n_bins],
                        [range_min, range_max, range_min, range_max,
                         range_min, range_max])
    return hist.astype(np.uint64)

