import cv2
import numpy as np

d_shape = (512, 512, 3)

dataset = np.zeros(d_shape, np.uint8)
img = cv2.imread("data/test_image.png")

if img.shape[1] > d_shape[1]:
    fx = d_shape[1] / img.shape[1]
    img = cv2.resize(img, None, None, fx, fx, cv2.INTER_NEAREST)
dataset[0:img.shape[0], 0:img.shape[1]] = img
cv2.imshow("Hello", dataset)
print(img.shape)
cv2.waitKey()