import numpy as np
import cv2
import time

t = time.time()
mask = cv2.imread("F:\\_projects\\026_1_1_Joan the Woman_1916\\corpus_export\\project\\masks\\1_1.png")
img = cv2.imread("F:\\_projects\\026_1_1_Joan the Woman_1916\\corpus_export\\project\\scr\\Global_1_1_All Shots.png")

for i in range(100):
    temp_mask = np.zeros_like(img)
    lbl = [0,1,2,3,4,5,6,7,8,9,10]
    res = img[np.where(np.isin(mask, lbl))]

print(time.time() - t)