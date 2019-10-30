from core.data.computation import images_to_movie
import cv2
import glob

images = []
for j, img in enumerate(glob.glob("C:\\Users\\Gaudenz Halter\Downloads\Bregt2\\*.TIF")):
    p = img
    print(p)
    images.append(cv2.imread(p))
images_to_movie(images, "C:\\Users\\Gaudenz Halter\Downloads\Bregt2\\output.mp4", time_scale=150)