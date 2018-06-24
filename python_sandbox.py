# import dataset as ds
#
# db = ds.connect("mysql://zauberkl_ghalte:ghalte_991@zauberkl.mysql.db.hostpoint.ch:3306/zauberkl_VIANCorpusTest")
# print(db.tables)
<<<<<<< HEAD
import numpy as np

a = [1,2,3,4,5,6,7,8,9]
d = dict(hello = "hello")
for i, q in enumerate(a):
    d[i] = q
print(d)
layers = []
for key, attr in d .items():
    try:
        int(key)
        print(key)
        layers.append(attr)
    except:
        continue
=======

import numpy as np
import cv2
asset=[0,1,2,3,3,3,3,4,5,6,7,77,7,8,9]
arr = np.array(asset)
print(arr[:10])
>>>>>>> ba9d2cafe68164d5538263de6d62a4878f6fc883
