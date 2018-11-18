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
r, f = cap.read()
h5_file.create_dataset(name='movie', shape=(50, ) + f.shape, dtype=f.dtype, maxshape=(None, ) + f.shape, chunks=True)
c = 0
print(h5_file['movie'].shape)
t = time.time()
i = 0
while r:
    r, f = cap.read()
    c += 1
    if c % 5 != 0:
        continue
    h5_file['movie'][i] = f
    i += 1
    if c > 0 and c % DEFAULT_SIZE[0] == 0:
        print(c)
        h5_file['movie'].resize((i + DEFAULT_SIZE[0],) + h5_file['movie'].shape[1:])
print(time.time() - t)
h5_file.close()