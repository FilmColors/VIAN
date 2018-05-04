import cv2
import numpy as np
from random import randint
from sys import stdout as console

path = "C:\\Users\\Gaudenz Halter\\Desktop\\matrix_2.mp4"

def find_closest(frame, segment):
    a = np.sum((segment - frame[np.newaxis, ...]) ** 2, axis=(1, 2, 3))
    match = np.argmin(a)
    rate = np.amin(a)
    return match, rate

if __name__ == '__main__':
    a = [1,2,3,4,5,6,7,8,9]
    idx = 0
    for i, x in enumerate(a):
         if x is 5:
             idx = i
    a.pop(idx)
    a.insert(idx, 10)
    print(a)




