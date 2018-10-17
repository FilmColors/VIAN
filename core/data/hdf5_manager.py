import h5py
import os
import importlib
import sys
import numpy as np
import inspect
from core.data.interfaces import IAnalysisJob

def load_analysis():
    file_list = []
    for root, dirs, files in os.walk("core/analysis/", topdown=False):
        for name in files:
            if ".py" in name and not "__init__.py" in name and not "__pycache__" in name:
                path = os.path.join(root, name)
                path = path.replace("\\", "/")
                path = path.replace(".py", "")
                path = path.replace("/", ".")

                file_list.append(path)
    analyses = []
    for f in file_list:
        try:
            my_module = importlib.import_module(f)
            for name, obj in inspect.getmembers(sys.modules[my_module.__name__]):
                if inspect.isclass(obj) and issubclass(obj, IAnalysisJob):
                    if obj is not IAnalysisJob and obj not in analyses:
                        analyses.append(obj)

        except Exception as e:
            continue
    return analyses


DEFAULT_SIZE = (50,)
DS_COL_HIST = "col_histograms"
DS_COL_PAL = "col_palettes"
DS_COL_FEAT = "col_features"
DS_COL_TIME = "col_time_ms"

class HDF5Manager():
    def __init__(self):
        self.path = None
        self.h5_file = None
        self._index = dict()
        self._uid_index = dict()

    #region -- Generic --
    def set_path(self, path):
        self.path = path
        init = False
        print("HDF5: ", self.path)
        if not os.path.isfile(self.path):
            h5py.File(self.path, "w")
            init = True
        self.h5_file = h5py.File(self.path, "r+")
        print(list(self.h5_file.keys()))
        return init


    def initialize_all(self):
        for a in load_analysis():
            c = a()
            self.initialize_dataset(c.dataset_name, DEFAULT_SIZE + c.dataset_shape, c.dataset_dtype)

    def initialize_dataset(self, name, shape, dtype):
        if name not in self.h5_file:
            self.h5_file.create_dataset(name=name, shape=shape, dtype=dtype, maxshape=(None, ) + shape[1:], chunks=True)
            self._index[name] = 0

    def dump(self, d, dataset_name, unique_id):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
        if dataset_name not in self.h5_file:
            self.initialize_all()
        pos = self._index[dataset_name]
        if pos > 0 and pos % DEFAULT_SIZE[0] == 0:
            self.h5_file[dataset_name].resize((pos + DEFAULT_SIZE[0], ) + self.h5_file[dataset_name].shape[1:])
        self.h5_file[dataset_name][pos] = d

        self._uid_index[unique_id] = (dataset_name, pos)
        self._index[dataset_name] += 1

    def load(self, unique_id):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
        pos = self._uid_index[unique_id]
        return self.h5_file[pos[0]][pos[1]]

    def set_indices(self, d):
        for k, v in dict(d['curr_pos']).items():
            self._index[k] = v

        for k, v in dict(d['uidmapping']).items():
            self._uid_index[int(k)] = v
    #endregion

    #region Colorimetry
    def has_colorimetry(self):
        if DS_COL_HIST in list(self.h5_file) and DS_COL_PAL in list(self.h5_file) and DS_COL_FEAT in list(self.h5_file):
            return True
        else:
            return False

    def initialize_colorimetry(self, length):
        print("Initializing Colorimetry")
        for n in [DS_COL_FEAT, DS_COL_HIST, DS_COL_PAL, DS_COL_TIME]:
            if n in self.h5_file:
                del self.h5_file[n]
        self._index['col'] = 0

        self.h5_file.create_dataset(DS_COL_HIST, shape=(length, 16, 16, 16), dtype=np.float16)
        self.h5_file.create_dataset(DS_COL_FEAT, shape=(length, 8), dtype=np.float16)
        self.h5_file.create_dataset(DS_COL_PAL, shape=(length, 1000, 6), dtype=np.float16)
        self.h5_file.create_dataset(DS_COL_TIME, shape=(length, 1), dtype=np.uint64)
        self.h5_file.flush()

    def dump_colorimetry(self, d, idx):
        self.h5_file[DS_COL_PAL][idx] = d['palette']
        self.h5_file[DS_COL_HIST][idx] = d['hist']
        self.h5_file[DS_COL_FEAT][idx] = d['features']
        self.h5_file[DS_COL_TIME][idx] = d['time_ms']
        self.h5_file.flush()

    def get_colorimetry_length(self):
        return np.where(np.array(self.h5_file[DS_COL_TIME])> 0)[0].shape[0] + 1

    def get_colorimetry_times(self):
        t = np.reshape(self.h5_file[DS_COL_TIME], newshape=self.h5_file[DS_COL_TIME].shape[0])
        return t

    def get_colorimetry_pal(self, idx):
        return self.h5_file[DS_COL_PAL][idx]

    def col_histograms(self):
        return self.h5_file[DS_COL_HIST]
    #endregion

    def get_indices(self):
        return dict(curr_pos=self._index, uidmapping=self._uid_index)

    def on_close(self):
        self.h5_file.close()
