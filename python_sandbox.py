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
with h5py.File("testdb.hdf5", "w") as f:
    s = (1000, mask.shape[0], mask.shape[1], mask.shape[2])
    hds = f.create_dataset("masks", s, mask.dtype)
    for i in range(1000):
        hds[i] = mask

    for i in range(1000):
        d = hds[i]
        cv2.imshow("", d)
print("HDF5", time.time() - t)