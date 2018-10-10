import numpy as np
import cv2
import time
import io
import pickle
import h5py
import dataset as ds


t = time.time()
mask = cv2.imread("C:\\Users\\Gaudenz Halter\\Pictures\\vlcsnap-error665.png")
# db = ds.connect("sqlite:///testdb.db")
# db.begin()
# for i in range(100):
#     f = io.BytesIO()
#     np.save(f, mask.astype(np.uint8), allow_pickle=False)
#     db["numpy"].insert(dict(idx = i, data = f.getvalue()))
#     # d = np.load(io.BytesIO(f.getvalue()), allow_pickle=False)
# db.commit()
# for i in range(100):
#     data = db['numpy'].find_one(idx = i)
#     d = np.load(io.BytesIO(data['data']), allow_pickle=False)
# print("Numpy", time.time() - t, (time.time() - t) / 1000)
#
# t = time.time()
# db.begin()
# for i in range(100):
#     f = io.BytesIO()
#     pickle.dump(mask, f)
#     db["pickle"].insert(dict(idx=i, data=f.getvalue()))
# db.commit()
# for i in range(100):
#     data = db['pickle'].find_one(idx = i)
#     d =  pickle.load(io.BytesIO(data['data']))
# print("Pickle", time.time() - t, (time.time() - t) / 1000)

t = time.time()
cap = cv2.VideoCapture("/Users/gaudenz/Desktop/sintel-1280-surround.mp4")
length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
range_min = 0
range_max = 255
mask_size = (500, 500)
with h5py.File("testdb.hdf5", "w") as f:
    hd_histograms = f.create_dataset("histograms", (length, 16, 16, 16), np.float16)
    s = (length, mask_size[0], mask_size[1])
    hd_masks = f.create_dataset("masks", s, np.uint8)
    print(hd_masks.size / 1000000)
    print(hd_histograms.size / 1000000)

    ret = True
    c = 0
    while ret:

        ret, frame = cap.read()
        hist = cv2.calcHist([frame[:, 0], frame[:, 1], frame[:, 2]], [0, 1, 2], None,
                            [16, 16, 16],
                            [range_min, range_max, range_min, range_max,
                             range_min, range_max])
        hd_histograms[c] = hist.astype(np.float16)
        hd_masks[c] = cv2.cvtColor(cv2.resize(frame, mask_size, interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2GRAY)

        c += 1
        print(c)


    # for i in range(1000):
    #     hds[i] = mask
    #
    # for i in range(1000):
    #     d = hds[i]
    #     cv2.imshow("", d)
print("HDF5", time.time() - t)