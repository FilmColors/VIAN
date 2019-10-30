import cv2
import glob
import numpy as np
import os


def image_grid(paths, nw=15, nh=12, w=400, crop_size=None):
    """
    Creates a grid of images from a list of image paths.

    :param paths: The list of image paths
    :param nw: number of images x axis
    :param nh: number of images y axis
    :param w: the width of a single image
    :param crop_size: if a tuple is given (w, h) the images is cropped to the given tuple size
    :return: An image path
    """
    twidth = w
    w = nw
    h = nh
    files = paths

    w_single = twidth / w

    imgs = []
    fx = None
    for f in files:
        img = cv2.imread(f)
        if fx is None:
            fx = w_single / img.shape[1]
        imgs.append(cv2.resize(cv2.imread(f), None, None, fx, fx, cv2.INTER_CUBIC))

    preview = None
    counter = 0
    for x in range(h):
        line = None
        for y in range(w):
            if counter >= len(imgs):
                break
            if line is None:
                line = imgs[counter]
            else:
                line = np.hstack((line, imgs[counter]))

            counter += 1
        if preview is None:
            preview = line
        else:
            try:
                preview = np.vstack((preview, line))
            except:
                continue
    if crop_size is not None:
        # check if the image has the minimum size:
        if preview.shape[0] < crop_size[1] or preview.shape[1] < crop_size[0]:
            fx = crop_size[1] / preview.shape[0]
            fy = crop_size[0] / preview.shape[1]
            if fx > fy:
                preview = cv2.resize(preview, None, None, fx, fx, interpolation=cv2.INTER_CUBIC)
            else:
                preview = cv2.resize(preview, None, None, fy, fy, interpolation=cv2.INTER_CUBIC)
        preview = preview[0:crop_size[1], 0:crop_size[0]]

    return preview

h = 500
result = []
paths = []
n = len(glob.glob("F:/fiwi_datenbank/SCR/14_1_1/*"))
files = glob.glob("F:/fiwi_datenbank/SCR/14_1_1/*")
files = sorted(files, key=lambda x:(int(os.path.split(x)[1].split("_")[0]), int(os.path.split(x)[1].split("_")[1])))
for idx, f in enumerate(files):
    if idx % 2== 0:
        paths.append(f)
preview = image_grid(paths, 30, 100, w = 2000)
cv2.imwrite("preview.png", preview)
for idx, f in enumerate(files):
    if idx % 3 == 0:
        paths.append(f)
    print(f)
    img = cv2.imread(f)
    img = np.swapaxes(img, 0, 1)
    img = cv2.resize(img, (500,5), interpolation=cv2.INTER_CUBIC)
    # img = np.mean(img, axis=1)
    print(img.shape)
    result.extend(img)

t = np.array(result, dtype=np.uint8)
t = np.swapaxes(t, 0, 1)
print(t.shape)
cv2.imwrite("barcode.png", t)

