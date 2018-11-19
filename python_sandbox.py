import cv2
import numpy as np
import h5py
import time
d_shape = (512, 512, 3)
DEFAULT_SIZE = (50,)


dataset = np.zeros(d_shape, np.uint8)
img = cv2.imread("data/test_image.png")
h5_file = h5py.File("test_movie.hdf5", mode="w")

cap =cv2.VideoCapture("C:\\Users\\Gaudenz Halter\\Desktop\\1307_1_1_Aliens_1986_DVD_eng.mov")
t_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
t_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
ds_width = 200
ds_height = int(t_height * (ds_width / t_width))
n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
r, f = cap.read()

h5_file.create_dataset(name='movie', shape=(50, ds_width, ds_height, 3), dtype=f.dtype, maxshape=(None, ) + f.shape, chunks=True)

c = -1
idx = 0
resolution = 10

t = time.time()
while r:
    c += 1
    if c % resolution != 0:
        continue
    cap.set(cv2.CAP_PROP_POS_FRAMES, c)

    r, f = cap.read()
    f = cv2.resize(f, (ds_height, ds_width), interpolation=cv2.INTER_CUBIC)
    h5_file['movie'][idx] = f
    idx += 1
    if idx > 0 and idx % DEFAULT_SIZE[0] == 0:
        print(c, n)
        h5_file['movie'].resize((idx + DEFAULT_SIZE[0],) + h5_file['movie'].shape[1:])

print(time.time() - t)
h5_file.close()