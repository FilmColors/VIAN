from vian.core.data.computation import images_to_movie
import cv2
import glob

images = []
for j, img in enumerate(glob.glob("C:/Users/gaude/Desktop/Filmmaterial EYE Fotos/*.jpg")):
    p = img
    images.append(cv2.imread(p))

images_to_movie(images, "C:/Users/gaude/Desktop/Filmmaterial EYE Fotos/output.mp4", time_scale=30, size=None)