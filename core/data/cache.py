import h5py
import os
import gc
import numpy as np
import shutil


DEFAULT_SIZE = (50, )
class HDF5Cache():
    def __init__(self, file):
        self.path = None
        self.h5_file = None
        self._index = dict()
        self._uid_index = dict()
        self.set_path(file)
        self._uid_scr = dict()

    # region -- Generic --
    def set_path(self, path):
        self.path = path
        init = False
        if not os.path.isfile(self.path):
            h5py.File(self.path, "w")
            init = True
        self.h5_file = h5py.File(self.path, "r+")
        return init

    def create_screenshot_cache(self, clobj, size):
        self.initialize_dataset(clobj, size, np.uint8)

    def dump_screenshot(self, uid_clobj, uid_scr, scr):
        uid_clobj = str(uid_clobj)
        uid_scr = str(uid_scr)
        if uid_clobj not in self._uid_scr:
            self._uid_scr[uid_clobj] = dict()
        if uid_clobj not in self.h5_file:
            self.create_screenshot_cache(uid_clobj, DEFAULT_SIZE + scr.shape)
            self._index[uid_clobj] = 0
        pos = self._index[uid_clobj]
        if pos > 0 and pos % DEFAULT_SIZE[0] == 0:
            self.h5_file[uid_clobj].resize((pos + DEFAULT_SIZE[0],) + self.h5_file[uid_clobj].shape[1:])
        self.h5_file[uid_clobj][pos] = scr
        self._uid_scr[uid_clobj][uid_scr] = pos
        self._index[uid_clobj] += 1

    def get_screenshot(self, uid_clobj, uid_scr):
        uid_clobj = str(uid_clobj)
        uid_scr = str(uid_scr)

        if uid_clobj in self._uid_scr:
            if uid_scr in self._uid_scr[uid_clobj]:
                pos = self._uid_scr[uid_clobj][uid_scr]
                return self.h5_file[uid_clobj][pos]
            return None
        else:
            return None

    def initialize_dataset(self, name, shape, dtype):
        if name not in self.h5_file:
            print("Init:", name, shape, dtype)
            self.h5_file.create_dataset(name=name, shape=shape, dtype=dtype, maxshape=(None,) + shape[1:], chunks=True)
            self._index[name] = 0

    def dump(self, d, dataset_name, unique_id):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")

        pos = self._index[dataset_name]
        if pos > 0 and pos % DEFAULT_SIZE[0] == 0:
            self.h5_file[dataset_name].resize((pos + DEFAULT_SIZE[0],) + self.h5_file[dataset_name].shape[1:])
        self.h5_file[dataset_name][pos] = d

        self._uid_index[unique_id] = (dataset_name, pos)
        self._index[dataset_name] += 1

    def cleanup(self):
        try:
            for n in self.h5_file.keys():
                del self.h5_file[n]

            new_file = h5py.File(self.path.replace("cache", "temp"), mode="w")
            for name in self.h5_file.keys():
                ds = self.h5_file[name]
                nds = new_file.create_dataset(name, ds.shape, ds.dtype)
                nds[:] = ds[:]
            new_file.close()
            self.h5_file.close()
            os.remove(self.path)
            os.rename(self.path.replace("cache", "temp"), self.path)
            self.h5_file = h5py.File(self.path, "r+")
        except:
            pass

    def get_indices(self):
        return dict(curr_pos=self._index, uidmapping=self._uid_index)

    def on_close(self):
        self.h5_file.close()
        if os.path.isfile(self.path):
            os.remove(self.path)
        self.set_path(self.path)
        self.h5_file = None
        self._index = dict()
        self._uid_scr = dict()
        self._uid_index = dict()