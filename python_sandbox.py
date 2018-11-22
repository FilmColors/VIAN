import cv2
import numpy as np
import h5py
import time
from core.data.computation import apply_mask
d_shape = (512, 512, 3)
DEFAULT_SIZE = (50,)

img = cv2.imread("data/01_shot.jpg")
mask =  cv2.imread("data/01_mask.png", 0)

cv2.imwrite("out_img.png", img)
cv2.imshow("Mask", mask)
cv2.waitKey()
