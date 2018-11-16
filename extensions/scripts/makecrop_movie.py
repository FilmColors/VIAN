import cv2
import numpy as np
import glob

files = glob.glob("images\\*.jpg")
imgs = [cv2.imread(f) for f in files]

shape = imgs[0][:, 140:-150].shape
final = []
for img in imgs:
    img1 = img[:400, 140:-150]
    img2 = img[400:, 140:-150]
    final.append(img1)
    final.append(img2)
    cv2.imshow("", img1)
    cv2.waitKey()
imgs = final
shape = (int(shape[0]), int(shape[1]))
print(shape)
fourcc = cv2.VideoWriter_fourcc(*"MJPG")
writer = cv2.VideoWriter("out.mp4", fourcc, 30.0,  (shape[0], shape[1]))
for i in imgs:
    for y in range(30):
        img = cv2.resize(i, (shape[0], shape[1]), interpolation=cv2.INTER_CUBIC)
        writer.write(img)
writer.release()
