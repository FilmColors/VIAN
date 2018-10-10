"""
:author Gaudenz Halter
"""

import cv2
import numpy as np
import bisect
from typing import List
# from PyQt5.QtWidgets import QMessageBox

from core.data.enums import ANALYSIS_NODE_SCRIPT, ANALYSIS_JOB_ANALYSIS
from core.data.interfaces import IProjectContainer, IHasName, ISelectable
from core.data.project_streaming import *
from core.data.computation import *


class AnalysisContainer(IProjectContainer, IHasName, ISelectable, IStreamableContainer):
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

    def apply_loaded(self, obj):
        self.set_adata(obj)

    def sync_load(self):
        self.set_adata(self.project.main_window.project_streamer.sync_load(self.unique_id))

    def get_name(self):
        return self.name

    def get_preview(self):
        pass

    def serialize(self):
        data_json = []
        for d in self.get_adata():
            data_json.append(np.array(d).tolist())


        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            notes=self.notes,
        )

        return data

    def deserialize(self, serialization, streamer):
        pass

    def delete(self):
        self.project.remove_analysis(self)


class NodeScriptAnalysis(AnalysisContainer, IStreamableContainer):
    """

    """
    def __init__(self, name = "NewNodeScriptResult", results = "None", script_id = -1, final_nodes_ids = None):
        super(NodeScriptAnalysis, self).__init__(name, results)
        self.script_id = script_id
        self.final_node_ids = final_nodes_ids

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

            self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data_json)
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
            data_json = self.project.numpy_data_manager.sync_load(self.unique_id)

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


class IAnalysisJobAnalysis(AnalysisContainer, IStreamableContainer):
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
            return self.project.main_window.eval_class(self.analysis_job_class)().get_preview(self)
        except Exception as e:
            print("Preview:", e)

    def get_visualization(self):
        try:
            return self.project.main_window.eval_class(self.analysis_job_class)().get_visualization(self,
                                                                                             self.project.results_dir,
                                                                                             self.project.data_dir,
                                                                                             self.project,
                                                                                             self.project.main_window)
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

    def deserialize(self, serialization, streamer:ProjectStreamer):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.analysis_job_class = serialization['analysis_job_class']
        self.notes = serialization['notes']
        # VERSION > 0.6.8
        try:
            if serialization['classification_obj'] > 0:
                self.target_classification_object = streamer.project.get_by_id(serialization['classification_obj'])
        except Exception as e:
            print(e)
            pass

        # self.data = []
        # t = streamer.project.main_window.eval_class(self.analysis_job_class)
        # self.data = t().deserialize(streamer.sync_load(self.unique_id))
        self.parameters = serialization['parameters']

        self.set_target_container(streamer.project.get_by_id(serialization['container']))

        return self

    def unload_container(self, data = None, sync = False):
        if data is not None:
            self.data = data
        if self.data is None:
            return

        if sync:
            self.project.main_window.project_streamer.sync_store(self.unique_id, self.project.main_window.eval_class(self.analysis_job_class)().serialize(self.data))
        else:
            self.project.main_window.project_streamer.async_store(self.unique_id, self.project.main_window.eval_class(self.analysis_job_class)().serialize(self.data))

    def apply_loaded(self, obj):
        self.set_adata(self.project.main_window.eval_class(self.analysis_job_class)().deserialize(obj))

    def get_adata(self):
        if self.a_class is None:
            self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
        return self.a_class().from_json(self.project.main_window.project_streamer.sync_load(self.unique_id, data_type=self.a_class().serialization_type()))

    def set_adata(self, d):
        if self.a_class is None:
            self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
        self.project.main_window.project_streamer.sync_store(self.unique_id, self.a_class().to_json(d), data_type=self.a_class().serialization_type())
        self.data = None


class ColormetryAnalysis(AnalysisContainer):
    def __init__(self, results = None, resolution = 30):
        super(ColormetryAnalysis, self).__init__(name = "Colormetry", data = results)
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []
        self.histograms = []
        self.avg_colors = []

        self.palette_bins = []
        self.palette_cols = []
        self.palette_layers = []

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

    def get_histogram(self, time_ms):
        pass

    def get_palette(self, time_ms):
        pass

    def append_data(self, data):
        try:
            if not isinstance(self.palette_cols, List):
                try:
                    self.time_ms = self.time_ms.tolist()
                    self.histograms = self.histograms.tolist()
                    self.frame_pos = self.frame_pos.tolist()
                    self.avg_colors = self.avg_colors.tolist()
                    self.palette_cols = self.palette_cols.tolist()
                    self.palette_layers = self.palette_layers.tolist()
                    self.palette_bins = self.palette_bins.tolist()
                except Exception as e:
                    print("Could not Convert Colormetry data to list in append_data()", e)

            self.time_ms.append(data['time_ms'])
            self.histograms.append(data['hist'])
            self.frame_pos.append(data['frame_pos'])
            self.avg_colors.append(data['avg_color'])

            self.palette_bins.append(data['palette'].tree[2])
            self.palette_cols.append(data['palette'].tree[1])
            self.palette_layers.append(data['palette'].tree[0])

            self.current_idx = len(self.time_ms)

        except Exception as e:
            print("ColormetryAnalysis.append_data() raised ", str(e))

    def get_update(self, time_ms):
        try:
            frame_idx = int(ms_to_frames(time_ms, self.project.movie_descriptor.fps) / self.resolution)
            if frame_idx == self.last_idx:
                return False
            self.last_idx = frame_idx
            return dict(palette = [np.array(self.palette_layers[frame_idx]), np.array(self.palette_cols[frame_idx]), np.array(self.palette_bins[frame_idx])])
        except Exception as e:
            pass

    def get_time_palette(self):
        time_palette_data = []
        for t in range(len(self.palette_layers) - 1):
            time_palette_data.append([
                np.array(self.palette_layers[t]),
                np.array(self.palette_cols[t]),
                np.array(self.palette_bins[t])
            ])
        return [time_palette_data, self.time_ms]

    def set_finished(self):
        if self.current_idx - 1 < len(self.time_ms):
            if self.time_ms[self.current_idx - 1] >= self.project.movie_descriptor.duration - (frame2ms(5 * self.resolution, self.project.movie_descriptor.fps)):
                if not isinstance(self.palette_cols, np.ndarray):
                    self.palette_cols = np.array(self.palette_cols, dtype=np.uint8)
                if not isinstance(self.palette_layers, np.ndarray):
                    self.palette_layers = np.array(self.palette_layers, dtype=np.uint16)
                if not isinstance(self.palette_bins, np.ndarray):
                    self.palette_bins = np.array(self.palette_bins, dtype=np.uint16)
                self.has_finished = True
                print("LOG: Colorimetry finished")

                data = dict(
                    curr_location=self.curr_location,
                    time_ms=self.time_ms,
                    frame_pos=self.frame_pos,
                    histograms=self.histograms,
                    avg_colors=self.avg_colors,
                    palette_colors=self.palette_cols,
                    palette_layers=self.palette_layers,
                    palette_bins=self.palette_bins,
                    resolution=self.resolution,
                )
                self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data, data_type=NUMPY_OVERWRITE)

    def clear(self):
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []
        self.histograms = []
        self.avg_colors = []

        self.palette_cols = []
        self.palette_layers = []
        self.palette_bins = []

        self.resolution = 30
        self.has_finished = False
        self.current_idx = 0

    def serialize(self):
        data = dict(
            curr_location = self.curr_location,
            time_ms = self.time_ms,
            frame_pos=self.frame_pos,
            histograms=self.histograms,
            avg_colors=self.avg_colors,
            palette_colors=self.palette_cols,
            palette_layers=self.palette_layers,
            palette_bins=self.palette_bins,
            resolution=self.resolution,
            current_idx = self.current_idx
        )

        if self.has_finished:
            self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data, data_type=NUMPY_OVERWRITE)
        else:
            self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data, data_type=NUMPY_OVERWRITE)

        serialization = dict(
            name=self.name,
            unique_id=self.unique_id,
            analysis_container_class=self.__class__.__name__,
            notes=self.notes,
            has_finished = self.has_finished

        )
        return serialization

    def deserialize(self, serialization, streamer):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        try:
            self.has_finished = serialization['has_finished']
            data = streamer.sync_load(self.unique_id)
            if data is not None:
                # self.current_idx = data['current_idx']
                self.curr_location = data['curr_location']
                self.time_ms = data['time_ms']

                self.frame_pos =  data['frame_pos']
                self.histograms =  data['histograms']
                self.avg_colors =  data['avg_colors']

                self.palette_cols = data['palette_colors']
                self.palette_layers = data['palette_layers']
                self.palette_bins = data['palette_bins']

                self.resolution =  data['resolution']

            else:
                self.curr_location = 0
                self.time_ms = []
                self.frame_pos = []
                self.histograms = []
                self.avg_colors = []

                self.palette_cols = []
                self.palette_layers = []
                self.palette_bins = []

                self.resolution = 30
                self.has_finished = False
                self.current_idx = 0

        except Exception as e:
            print("Exception in Loading Analysis", str(e))
        self.current_idx = len(self.time_ms)
        return self


class MaskAnalysis(IAnalysisJobAnalysis):
    def __init__(self, labels, analysis_job_class, parameters, container, name="Mask Segmentation", results = None):
        """
        :param name: The Name of the Segmentation as it should appear in the Outliner
        :param labels: A List of labels sorted by label index (implicit)
        :param results: 
        """

        super(MaskAnalysis, self).__init__(name=name, results = None, analysis_job_class=analysis_job_class, parameters=parameters, container=container)
        self.masks = []
        self.time_ms = []
        self.frame_pos = []
        self.labels = labels

    def insert(self, data):
        """
        Inserts a new mask sorted into the Analysis
        :param data: a dict(frame_pos, time_ms, mask)
        :return: 
        """

        bisect.insort(self.frame_pos, data['frame_pos'])
        idx = self.frame_pos.index(data['frame_pos'])
        self.time_ms.insert(idx, data['time_ms'])
        self.masks.insert(idx, data['mask'])

    def serialize(self):
        data = dict(
            masks = self.masks,
            time_ms = self.time_ms,
            frame_pos = self.frame_pos
        )

        self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data, data_type=NUMPY_OVERWRITE)
        serialization = dict(
            name=self.name,
            unique_id=self.unique_id,
            analysis_container_class=self.__class__.__name__,
            notes=self.notes,
        )

        return serialization

    def deserialize(self, serialization, streamer):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        data = streamer.sync_load(self.unique_id)
        self.frame_pos = data['frame_pos']
        self.masks = data['masks']
        self.time_ms = data['time_ms']

        return self


class AnalysisParameters():
    def __init__(self, target_items=None):
        self.target_items = []

        if target_items is not None:
            self.set_targets(target_items)

    def set_targets(self, project_container_list):
        for o in project_container_list:
            self.target_items.append(o.get_id())

    def serialize(self):
        data = dict(
            parameter_class=self.__class__.__name__,
            params=self.__dict__,
        )

        return data

    def deserialize(self, serialization):
        for key, val in serialization['params'].iter():
            setattr(self, key, val)
        return self

