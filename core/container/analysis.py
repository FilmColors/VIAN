"""
:author Gaudenz Halter
"""

import cv2
import numpy as np
import bisect
from typing import List

from core.data.enums import ANALYSIS_NODE_SCRIPT, ANALYSIS_JOB_ANALYSIS
from .container_interfaces import IProjectContainer, IHasName, ISelectable
from core.data.computation import *
from .hdf5_manager import get_analysis_by_name


class AnalysisContainer(IProjectContainer, IHasName, ISelectable): #, IStreamableContainer):
    """
    This is the BaseClass of all AnalysisContainers in the VIAN Project.

    Member Attributes:
        :self.name : The Name of the Container (not the analysis)
        :self.notes : Additional Notes added in the Inspector
        :self.data : The Generic Data Dict defined by the respective Analysis
    """
    def __init__(self, name = "", data = None):
        """
        :param name:
        :param data:
        """
        IProjectContainer.__init__(self)
        self.name = name
        self.notes = ""
        self.data = data
        self.analysis_job_class = "Generic"

    def set_project(self, project):
        IProjectContainer.set_project(self, project)

        # The data is only set when the container is created,
        # else it should already be in the SQLite Database
        if self.data is not None:
            self.set_adata(self.data)

    def unload_container(self, data=None, sync=False):
        super(AnalysisContainer, self).unload_container(self.get_adata(), sync=sync)
        self.data = None

    def get_adata(self):
        return self.data

    def set_adata(self, d):
        self.data = d

    def get_name(self):
        return self.name

    def get_preview(self):
        pass

    def serialize(self):
        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            notes=self.notes,
            data = self.data,
            analysis_job_class = self.analysis_job_class
        )

        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']
        self.data = serialization['data']
        self.analysis_job_class = serialization['analysis_job_class']

    def delete(self):
        self.project.remove_analysis(self)


class NodeScriptAnalysis(AnalysisContainer):# , IStreamableContainer):
    """

    """
    def __init__(self, name = "NewNodeScriptResult", results = "None", script_id = -1, final_nodes_ids = None):
        super(NodeScriptAnalysis, self).__init__(name, results)
        self.script_id = script_id
        self.final_node_ids = final_nodes_ids
        self.analysis_job_class = "NodeScript"

    def get_type(self):
        return ANALYSIS_NODE_SCRIPT

    def serialize(self):
        data_json = []

        try:
            #Loop over each final node of the Script
            for i, n in enumerate(self.data):
                node_id = self.final_node_ids[i]
                node_result = []
                result_dtypes = []

                # Loop over each result in the final node
                for d in n:
                    if isinstance(d, np.ndarray):
                        node_result.append(d.tolist())
                        result_dtypes.append(str(d.dtype))
                    elif isinstance(d, list):
                        node_result.append(d)
                        result_dtypes.append("list")
                    else:
                        node_result.append(np.array(d).tolist())
                        result_dtypes.append(str(np.array(d).dtype))
                data_json.append([node_id, node_result, result_dtypes])

            # We want to store the analysis container if it is not already stored

            # self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data_json)
        except Exception as e:
            print("Exception in NodeScriptAnalysis.serialize(): ", str(e))

        data = dict(
            name=self.name,
            analysis_container_class = self.__class__.__name__,
            unique_id=self.unique_id,
            script_id=self.script_id,
            # data_json=data_json,
            notes=self.notes
        )

        return data

    def deserialize(self, serialization, streamer):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']
        self.script_id = serialization['script_id']

        self.final_node_ids = []
        self.data = []
        try:
            # data_json = self.project.numpy_data_manager.sync_load(self.unique_id)
            data_json = None
            #TODO Numpy Storing obsolete for Scripts
            # Loop over each final node of the Script
            for r in data_json:

                node_id = r[0]
                node_results = r[1]
                result_dtypes = r[2]

                node_data = []
                self.final_node_ids.append(node_id)

                # Loop over each Result of the Final Node
                for j, res in enumerate(node_results):
                    if result_dtypes[j] == "list":
                        node_data.append(res)
                    else:
                        node_data.append(np.array(res, dtype=result_dtypes[j]))

                    self.data.append(node_data)
        except Exception as e:
            print(e)

        return self


class IAnalysisJobAnalysis(AnalysisContainer): #, IStreamableContainer):
    def __init__(self, name = "NewAnalysisJobResult", results = None, analysis_job_class = None, parameters = None, container = None, target_classification_object = None):
        super(IAnalysisJobAnalysis, self).__init__(name, results)
        self.target_container = container
        if analysis_job_class is not None:
            self.analysis_job_class = analysis_job_class.__name__
        else:
            self.analysis_job_class = None

        if parameters is not None:
            self.parameters = parameters
        else:
            self.parameters = []

        self.target_classification_object = target_classification_object
        # Evaluated self.analysis-job_class
        self.a_class = None

    def get_preview(self):
        try:
            #return self.project.main_window.eval_class(self.analysis_job_class)().get_preview(self)
            return get_analysis_by_name(self.analysis_job_class)().get_preview(self)
        except Exception as e:
            print("Preview:", e)

    def get_visualization(self, main_window):
        try:
            # return self.project.main_window.eval_class(self.analysis_job_class)().get_visualization(self,
            #                                                                                  self.project.results_dir,
            #                                                                                  self.project.data_dir,
            #                                                                                  self.project,
            #                                                                                  self.project.main_window)
            return get_analysis_by_name(self.analysis_job_class)().get_visualization(self,
                 self.project.results_dir,
                 self.project.data_dir,
                 self.project,
                 main_window
            )
        except Exception as e:
            print("Exception in get_visualization()", e)
            # QMessageBox.warning(self.project.main_window,"Error in Visualization", "The Visualization of " + self.name +
            #                     " has thrown an Exception.\n\n Please send the Console Output to the Developer.")

    def get_type(self):
        return ANALYSIS_JOB_ANALYSIS

    def set_target_container(self, container):
        self.target_container = container
        self.target_container.add_analysis(self)

    def set_target_classification_obj(self, class_obj):
        self.target_classification_object = class_obj

    def serialize(self):
        if self.target_classification_object is not None:
            class_obj_id = self.target_classification_object.unique_id
        else:
            class_obj_id = -1

        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            analysis_container_class=self.__class__.__name__,
            analysis_job_class=self.analysis_job_class,
            parameters=self.parameters,

            notes=self.notes,
            container = self.target_container.unique_id,
            classification_obj = class_obj_id
        )

        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.analysis_job_class = serialization['analysis_job_class']
        self.notes = serialization['notes']

        # VERSION > 0.6.8
        try:
            if serialization['classification_obj'] > 0:
                self.target_classification_object = project.get_by_id(serialization['classification_obj'])
        except Exception as e:
            print(e)
            pass

        # self.data = []
        # t = streamer.project.main_window.eval_class(self.analysis_job_class)
        # self.data = t().deserialize(streamer.sync_load(self.unique_id))
        self.parameters = serialization['parameters']

        self.set_target_container(project.get_by_id(serialization['container']))

        return self

    def unload_container(self, data = None, sync = False):
        if data is not None:
            self.data = data
        if self.data is None:
            return

    def get_adata(self):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        return self.a_class().from_hdf5(self.project.hdf5_manager.load(self.unique_id))

    def set_adata(self, d):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        self.project.hdf5_manager.dump(self.a_class().to_hdf5(d), self.a_class().dataset_name, self.unique_id)
        self.data = None


class SemanticSegmentationAnalysisContainer(IAnalysisJobAnalysis):
    def __init__(self, name = "NewAnalysisJobResult", results = None, analysis_job_class = None, parameters = None, container = None, target_classification_object = None, dataset = ""):
        super(SemanticSegmentationAnalysisContainer, self).__init__(name, results , analysis_job_class, parameters, container, target_classification_object)
        self.dataset = dataset
        self.entry_shape = None

    def get_adata(self):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        data = self.a_class().from_hdf5(self.project.hdf5_manager.load(self.unique_id))
        return data[0:self.entry_shape[0], 0:self.entry_shape[1]]

    def set_adata(self, d):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        d, self.entry_shape = self.a_class().to_hdf5(d)
        self.project.hdf5_manager.dump(d, self.a_class().dataset_name, self.unique_id)
        self.data = None

    def serialize(self):
        d = super(SemanticSegmentationAnalysisContainer, self).serialize()
        d['dataset'] = self.dataset
        d['entry_shape'] = self.entry_shape
        d['analysis_container_class'] = SemanticSegmentationAnalysisContainer.__name__
        return d

    def deserialize(self, serialization, project):
        super(SemanticSegmentationAnalysisContainer, self).deserialize(serialization, project)
        self.dataset = serialization['dataset']
        try:
            self.entry_shape = serialization['entry_shape']
        except:
            self.entry_shape = (512, 512)
        return self


class ColormetryAnalysis(AnalysisContainer):
    def __init__(self, results = None, resolution = 30):
        super(ColormetryAnalysis, self).__init__(name = "Colormetry", data = results)
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []
        self.end_idx = 0

        self.analysis_job_class = "Colormetry"

        print("Colormetry Analysis Constructor", resolution)
        self.resolution = resolution
        self.has_finished = False

        self.current_idx = 0
        self.current_junk_idx = 0

        self.linear_colors = []
        for x in range(16):
            for y in range(16):
                for z in range(16):
                    self.linear_colors.append([x * 16, y * 16, z * 16])
        self.linear_colors = np.array([self.linear_colors] * 2, dtype=np.uint8)
        self.linear_colors = cv2.cvtColor(self.linear_colors, cv2.COLOR_LAB2RGB)[0]

        self.last_idx = 0

    def get_histogram(self):
        return self.project.hdf5_manager.col_histograms()
        pass

    def get_palette(self, time_ms):
        pass

    def get_frame_pos(self):
        times = self.project.hdf5_manager.get_colorimetry_times()
        frames = np.multiply(np.divide(times, 1000), self.project.movie_descriptor.fps).astype(np.int).tolist()
        return frames

    def append_data(self, data):
        try:
            self.time_ms.append(data['time_ms'])
            self.current_idx = self.project.hdf5_manager.get_colorimetry_length() - 1
            self.project.hdf5_manager.dump_colorimetry(data, self.current_idx, self.end_idx)
            self.check_finished()

        except Exception as e:
            print("ColormetryAnalysis.append_data() raised ", str(e))

    def get_update(self, time_ms):
        try:
            frame_idx = int(ms_to_frames(time_ms, self.project.movie_descriptor.fps) / self.resolution)
            if frame_idx == self.last_idx or frame_idx > self.current_idx:
                return None
            self.last_idx = frame_idx
            d = self.project.hdf5_manager.get_colorimetry_pal(frame_idx)
            hist = self.project.hdf5_manager.get_colorimetry_hist(frame_idx)
            spatial = self.project.hdf5_manager.get_colorimetry_spatial()
            times = self.project.hdf5_manager.get_colorimetry_times()
            layers = [
                d[:, 1].astype(np.int),
                d[:, 2:5].astype(np.uint8),
                d[:, 5].astype(np.int)
            ]
            return dict(palette = layers, histogram=hist, spatial=spatial, times=times, frame_idx = frame_idx, current_idx = self.current_idx)
        except Exception as e:
            print(e)
            pass

    def get_time_palette(self):
        time_palette_data = []
        d = self.project.hdf5_manager.get_colorimetry_pal()
        palette_layers = d[:, :, 1].astype(np.int)
        palette_cols = d[:, :, 2:5].astype(np.uint8)
        palette_bins = d[:, :, 5].astype(np.int)
        for t in range(palette_layers.shape[0] - 1):
            time_palette_data.append([
                np.array(palette_layers[t]),
                np.array(palette_cols[t]),
                np.array(palette_bins[t])
            ])
        return [time_palette_data, self.time_ms]

    def check_finished(self):
        # print("IDX", self.current_idx, self.end_idx, self.current_idx == self.end_idx)
        if int(self.current_idx) >= int(self.end_idx - 1):
            self.has_finished = True
        return self.has_finished

    def clear(self):
        print("Clearing Colorimetry, Resolution:", self.resolution)
        n_frames = int(np.floor(ms_to_frames(self.project.movie_descriptor.duration, self.project.movie_descriptor.fps) / self.resolution))
        print(ms_to_frames(self.project.movie_descriptor.duration, self.project.movie_descriptor.fps) , self.resolution)
        self.project.hdf5_manager.initialize_colorimetry(n_frames)
        self.end_idx = n_frames
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []

        self.has_finished = False
        self.current_idx = 0

    def serialize(self):
        serialization = dict(
            name=self.name,
            unique_id=self.unique_id,
            analysis_container_class=self.__class__.__name__,
            resolution = self.resolution,
            curr_idx = self.current_idx,
            time_ms = self.time_ms,
            end_idx = self.end_idx,
            notes=self.notes,
            has_finished = self.has_finished

        )
        return serialization

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        try:
            self.has_finished = serialization['has_finished']
            self.resolution = serialization['resolution']
            self.time_ms = serialization['time_ms']
            self.current_idx = len(self.time_ms)
            self.end_idx = serialization['end_idx']

        except Exception as e:
            print("Exception in Loading Analysis", str(e))
        self.current_idx = project.hdf5_manager.get_colorimetry_length() - 1
        self.time_ms = project.hdf5_manager.get_colorimetry_times()[:self.current_idx + 1].tolist()
        self.check_finished()
        return self


