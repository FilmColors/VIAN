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


DEFAULT_SIZE = (5,)

class HDF5Manager():
    def __init__(self):
        self.path = None
        self.h5_file = None
        self._index = dict()
        self._uid_index = dict()

    def set_path(self, path):
        self.path = path
        if not os.path.isfile(self.path):
            h5py.File(self.path, "w")
        self.h5_file = h5py.File(self.path, "r+")

    def initialize_all(self):
        for a in load_analysis():
            c = a()
            self.initialize_dataset(c.dataset_name, DEFAULT_SIZE + c.dataset_shape, c.dataset_dtype)

    def initialize_dataset(self, name, shape, dtype):
        self.h5_file.create_dataset(name=name, shape=shape, dtype=dtype, maxshape=(None, ) + shape[1:], chunks=True)
        self._index[name] = 0

    def dump(self, d, dataset_name, unique_id):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
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


    def get_indices(self):
        return dict(curr_pos=self._index, uidmapping=self._uid_index)

