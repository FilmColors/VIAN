import cv2
import numpy as np

d_shape = (512, 512, 3)

dataset = np.zeros(d_shape, np.uint8)
img = cv2.imread("data/test_image.png")

print(img.shape)