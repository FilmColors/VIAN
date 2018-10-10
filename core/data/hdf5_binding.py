import h5py
import os


class HDF5Database():
    def __init__(self, path):
        self.h5file_path = path
        if not os.path.isfile(self.h5file_path):
            self.h5file = h5py.File(self.h5file_path, 'w')
            self.h5file.close()
        self.h5file = h5py.File(self.h5file_path, 'r+')

        # the index_ has for each table the next index that should be written
        self.index_ = dict()

        # maps a unique id to a database and entry
        self.unique_id_map = dict()

    def initialize_dataset(self, name, shape, dtype, data = None):
        self.h5file.create_dataset(name, shape, dtype, data)
        self.index_[name] = None

    def store(self, data, database, unique_id):
        idx = self.index_[database]
        self.h5file[database][idx] = data
        self.unique_id_map[unique_id] = dict(index=idx, database=database)
        self.index_[database] += 1
        return idx

    def load(self, unique_id):
        meta = self.unique_id_map[unique_id]
        return self.h5file[meta['database']][meta['index']]
