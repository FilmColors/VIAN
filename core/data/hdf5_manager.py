import h5py
import os
import importlib
import sys
import gc
import numpy as np
import inspect
from core.data.interfaces import IAnalysisJob
# from core.analysis.analysis_import import \
#     SemanticSegmentationAnalysis, \
#     BarcodeAnalysisJob, ColorPaletteAnalysis, ColorFeatureAnalysis, \
#     ColormetryAnalysis, MovieMosaicAnalysis, ColorHistogramAnalysis

# ANALYSES = [SemanticSegmentationAnalysis,
#             BarcodeAnalysisJob,
#             ColorPaletteAnalysis,
#             ColorFeatureAnalysis,
#             ColormetryAnalysis,
#             MovieMosaicAnalysis,
#             ColorHistogramAnalysis]
import shutil


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
                        print(obj)

        except Exception as e:
            print(e)
            continue
    global ANALYSES
    ANALYSES = analyses
    return analyses

# def load_analysis():
#     return [
#             eval("SemanticSegmentationAnalysis"),
#             eval("BarcodeAnalysisJob"),
#             eval("ColorPaletteAnalysis"),
#             eval("ColorFeatureAnalysis"),
#             eval("ColormetryAnalysis"),
#             eval("MovieMosaicAnalysis")
#         ]
ANALYSES = []
DEFAULT_SIZE = (50,)
DS_MOVIE = "movie"
DS_COL_HIST = "col_histograms"
DS_COL_PAL = "col_palettes"
DS_COL_FEAT = "col_features"
DS_COL_TIME = "col_time_ms"
DS_COL_SPATIAL_EDGE = "col_spatial_edge"
DS_COL_SPATIAL_COLOR = "col_spatial_color"
DS_COL_SPATIAL_HUE = "col_spatial_hue"
DS_COL_SPATIAL_LUMINANCE = "col_spatial_luminance"

class HDF5Manager():
    def __init__(self):
        self.path = None
        self.h5_file = None
        self._index = dict()
        self._uid_index = dict()

        #Cached
        self.col_edge_max = None
        self.col_hue_max = None
        self.col_color_max = None
        self.col_lum_max = None

    #region -- Generic --
    def set_path(self, path):
        self.path = path
        init = False
        print("HDF5: ", self.path)
        if not os.path.isfile(self.path):
            h5py.File(self.path, "w")
            init = True
        self.h5_file = h5py.File(self.path, "r+")
        print("Datasets in HDF5 File:")
        for k in self.h5_file.keys():
            print("\t-- ", k)
            if k == "ColorPalettes" and self.h5_file["ColorPalettes"].shape[1] != 1024:
                print("Deleting Palettes")
                del self.h5_file["ColorPalettes"]
        return init

    def initialize_all(self, analyses = None):
        if analyses is None or len(analyses) == 0:
            analyses = load_analysis()
        for a in analyses:
            c = a()
            self.initialize_dataset(c.dataset_name, DEFAULT_SIZE + c.dataset_shape, c.dataset_dtype)

    def initialize_dataset(self, name, shape, dtype):
        if name not in self.h5_file:
            print("Init:", name, shape, dtype)
            self.h5_file.create_dataset(name=name, shape=shape, dtype=dtype, maxshape=(None, ) + shape[1:], chunks=True)
            self._index[name] = 0

    def dump(self, d, dataset_name, unique_id):
        if self.h5_file is None:
            raise IOError("HDF5 File not opened yet")
        if dataset_name not in self.h5_file:
            self.initialize_all()
        if not dataset_name in self._index:
            self._index[dataset_name] = 0

        pos = self._index[dataset_name]
        if pos > 0 and pos % DEFAULT_SIZE[0] == 0:
            self.h5_file[dataset_name].resize((pos + DEFAULT_SIZE[0], ) + self.h5_file[dataset_name].shape[1:])
        self.h5_file[dataset_name][pos] = d

        self._uid_index[unique_id] = (dataset_name, pos)
        self._index[dataset_name] += 1
        self.h5_file.flush()

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

    def initialize_colorimetry(self, length, remove = True):
        if remove:
            for n in [DS_COL_FEAT,
                      DS_COL_HIST,
                      DS_COL_PAL,
                      DS_COL_TIME,
                      DS_COL_SPATIAL_EDGE,
                      DS_COL_SPATIAL_LUMINANCE,
                      DS_COL_SPATIAL_HUE,
                      DS_COL_SPATIAL_COLOR]:
                if n in self.h5_file:
                    del self.h5_file[n]
            self._index['col'] = 0

            gc.collect()
            self.h5_file.flush()
            self.cleanup()

        if DS_COL_HIST not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_HIST, shape=(length, 16, 16, 16), dtype=np.float16)
        if DS_COL_FEAT not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_FEAT, shape=(length, 8), dtype=np.float16)
        if DS_COL_PAL not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_PAL, shape=(length, 1000, 6), dtype=np.float16)
        if DS_COL_TIME not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_TIME, shape=(length, 1), dtype=np.uint64)

        if DS_COL_SPATIAL_COLOR not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_SPATIAL_COLOR, shape=(length, 2), dtype=np.float32)
        if DS_COL_SPATIAL_EDGE not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_SPATIAL_EDGE, shape=(length, 2), dtype=np.float32)
        if DS_COL_SPATIAL_HUE not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_SPATIAL_HUE, shape=(length, 2), dtype=np.float32)
        if DS_COL_SPATIAL_LUMINANCE not in self.h5_file:
            self.h5_file.create_dataset(DS_COL_SPATIAL_LUMINANCE, shape=(length, 2), dtype=np.float32)

        self.h5_file.flush()

    def dump_colorimetry(self, d, idx, length):
        self.initialize_colorimetry(length, remove=False)
        self.h5_file[DS_COL_PAL][idx] = d['palette']
        self.h5_file[DS_COL_HIST][idx] = d['hist']
        self.h5_file[DS_COL_FEAT][idx] = d['features']
        self.h5_file[DS_COL_TIME][idx] = d['time_ms']
        self.h5_file[DS_COL_SPATIAL_EDGE][idx] = d['spatial_edge']
        self.h5_file[DS_COL_SPATIAL_COLOR][idx] = d['spatial_color']
        self.h5_file[DS_COL_SPATIAL_HUE][idx] = d['spatial_hue']
        self.h5_file[DS_COL_SPATIAL_LUMINANCE][idx] = d['spatial_luminance']

        self.h5_file.flush()

    def get_colorimetry_length(self):
        return np.where(np.array(self.h5_file[DS_COL_TIME])> 0)[0].shape[0] + 1

    def get_colorimetry_times(self):
        t = np.reshape(self.h5_file[DS_COL_TIME], newshape=self.h5_file[DS_COL_TIME].shape[0])
        return t

    def get_colorimetry_pal(self, idx = None):
        if idx is not None:
            return self.h5_file[DS_COL_PAL][idx]
        else:
            return self.h5_file[DS_COL_PAL]

    def get_colorimetry_hist(self, idx):
        return self.h5_file[DS_COL_HIST][idx]

    def get_colorimetry_spatial_max(self):
        if self.h5_file is None:
            return None
        if self.col_edge_max is None:
            if DS_COL_SPATIAL_EDGE in self.h5_file:
                self.col_edge_max = np.amax(self.h5_file[DS_COL_SPATIAL_EDGE][:, 0])
                self.col_color_max = np.amax(self.h5_file[DS_COL_SPATIAL_COLOR][:, 0])
                self.col_hue_max = np.amax(self.h5_file[DS_COL_SPATIAL_HUE][:, 0])
                self.col_lum_max = np.amax(self.h5_file[DS_COL_SPATIAL_LUMINANCE][:, 0])
        return dict(edge=self.col_edge_max,
                    color=self.col_color_max,
                    hue=self.col_hue_max,
                    luminance=self.col_lum_max)

    def get_colorimetry_spatial(self, idx = None):
        if idx is None:
            col_edge =self.h5_file[DS_COL_SPATIAL_EDGE]
            col_color = self.h5_file[DS_COL_SPATIAL_COLOR]
            col_hue = self.h5_file[DS_COL_SPATIAL_HUE]
            col_lum= self.h5_file[DS_COL_SPATIAL_LUMINANCE]
        else:
            col_edge =self.h5_file[DS_COL_SPATIAL_EDGE][idx]
            col_color = self.h5_file[DS_COL_SPATIAL_COLOR][idx]
            col_hue = self.h5_file[DS_COL_SPATIAL_HUE][idx]
            col_lum= self.h5_file[DS_COL_SPATIAL_LUMINANCE][idx]

        return dict(edge=col_edge,
                    color=col_color,
                    hue=col_hue,
                    luminance=col_lum)

    def col_histograms(self):
        return self.h5_file[DS_COL_HIST]
    #endregion

    def cleanup(self):
        new_file = h5py.File(self.path.replace("analyses", "temp"), mode="w")
        for name in self.h5_file.keys():
            ds = self.h5_file[name]
            nds = new_file.create_dataset(name, ds.shape, ds.dtype, maxshape=(None, ) + ds.shape[1:], chunks = True)
            nds[:] = ds[:]
        new_file.close()
        self.h5_file.close()
        os.remove(self.path)
        os.rename(self.path.replace("analyses", "temp"), self.path)
        self.h5_file = h5py.File(self.path, "r+")


    def get_indices(self):
        return dict(curr_pos=self._index, uidmapping=self._uid_index)

    def on_close(self):
        self.h5_file.close()

        self.col_edge_max = None
        self.col_hue_max = None
        self.col_color_max = None
        self.col_lum_max = None

        self.path = None
        self.h5_file = None
        self._index = dict()
        self._uid_index = dict()

