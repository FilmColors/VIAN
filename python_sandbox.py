import cv2
import numpy as np
import h5py
import time

from core.data.computation import apply_mask, labels_to_binary_mask
d_shape = (512, 512, 3)
DEFAULT_SIZE = (50,)

img = cv2.imread("data/01_shot.jpg")
mask =  cv2.imread("data/01_mask.png", 0)
indices = list(range(150))
indices = [12]
mask_size = 200
t = time.time()
tt = time.time()
mask = cv2.resize(mask, (mask_size, mask_size), interpolation=cv2.INTER_NEAREST)
print("Resize:", time.time() - t)

t = time.time()
bin_mask = labels_to_binary_mask(mask, indices)

bin_mask = cv2.resize(bin_mask, img.shape[:2][::-1], interpolation=cv2.INTER_NEAREST)
print("Binary Mask:", time.time() - t)

print(bin_mask.shape, img.shape)
t = time.time()
alpha = np.zeros(img.shape[:2], dtype=np.uint8)
alpha[np.nonzero(bin_mask)] = 255
print("Masking:", time.time() - t)

t = time.time()
result = np.dstack((img, alpha))
print("DSTACK:", time.time() - t)

print("Total:", time.time() - tt)
cv2.imwrite("out_img.png", result)
# cv2.imshow("Mask", mask)
# cv2.waitKey()
