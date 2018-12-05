import os
import h5py
import numpy as np
from threading import Lock

COLOR_PALETTES_MAX_LENGTH = 1024

# Chunk Size
DEFAULT_SIZE = (200,)

# Analyses Definitions for the datasets in the HDF5 File
DS_COL_HIST = dict(dataset_name="histograms", dataset_shape=(16, 16, 16), dataset_dtype=np.float32)
DS_COL_PAL = dict(dataset_name="palettes", dataset_shape=(COLOR_PALETTES_MAX_LENGTH, 6), dataset_dtype=np.float16)
DS_COL_FEAT = dict(dataset_name="features", dataset_shape=(8,), dataset_dtype=np.float16)
DS_COL_TIME = dict(dataset_name="time_ms", dataset_shape=(1,), dataset_dtype=np.uint32)
DS_MASKS = dict(dataset_name="masks", dataset_shape=(512,512), dataset_dtype=np.uint8)

ALL_ANALYSES = [
    DS_COL_HIST,
    DS_COL_PAL,
    DS_COL_FEAT,
    DS_COL_TIME,
    DS_MASKS
]

HDF5_LOCK = Lock()


class HDF5ManagerDatabase():
    def __init__(self, filepath = None):
        self.path = None
        self.h5_file = None
        self._index = dict()
        if filepath is not None:
            self.set_path(filepath)

    # region -- IO --
    def set_path(self, path):
        self.path = path
        init = False
        if not os.path.isfile(self.path):
            self.h5_file = h5py.File(self.path, "w")
            self.h5_file.close()
        self.h5_file = h5py.File(self.path, "r+")
        self.initialize_all()
        print(self._index)
        return init

    def initialize_all(self):
        for a in ALL_ANALYSES:
            self.initialize_dataset(a['dataset_name'], DEFAULT_SIZE + a['dataset_shape'], a['dataset_dtype'])

    def initialize_dataset(self, name, shape, dtype):
        if name not in self.h5_file:
            with HDF5_LOCK:
                self.h5_file.create_dataset(name=name, shape=shape, dtype=dtype, maxshape=(None,) + shape[1:],
                                            chunks=True)
                self._index[name] = 0
                self.h5_file[name].attrs['cursor_pos'] = 0
        else:
            with HDF5_LOCK:
                self._index[name] = self.h5_file[name].attrs['cursor_pos']
                print("Cursor Pos:", name, self._index[name])

    def dump(self, d, dataset_name, flush = True):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
        if dataset_name not in self.h5_file:
            raise IOError("HDF5 File doesnt contain ", dataset_name)

        with HDF5_LOCK:
            pos = self._index[dataset_name]
            if pos > 0 and pos % DEFAULT_SIZE[0] == 0:
                self.h5_file[dataset_name].resize((pos + DEFAULT_SIZE[0],) + self.h5_file[dataset_name].shape[1:])
            self.h5_file[dataset_name][pos] = d
            self._index[dataset_name] += 1
            self.h5_file[dataset_name].attrs['cursor_pos'] = self._index[dataset_name]

            if flush:
                self.h5_file.flush()
        return int(pos)

    def load(self, dataset_name, pos):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
        return self.h5_file[dataset_name][pos]

    # endregion

    # region Getter
    def palettes(self):
        return self.h5_file[DS_COL_PAL['dataset_name']]

    def features(self):
        return self.h5_file[DS_COL_FEAT['dataset_name']]

    def time_ms(self):
        return self.h5_file[DS_COL_TIME['dataset_name']]

    def histograms(self):
        return self.h5_file[DS_COL_HIST['dataset_name']]
    # endregion

    def on_close(self):
        self.h5_file.close()
