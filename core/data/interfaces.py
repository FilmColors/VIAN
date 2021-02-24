"""
In this Module, all interfaces used by VIAN are defined. 
"""
from typing import List, Union, Dict, Tuple

import numpy as np
from random import randint
from collections import namedtuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor
from core.data.enums import DataSerialization
from scipy.signal import savgol_filter, resample
from core.data.log import log_debug, log_info, log_error
from core.container.container_interfaces import ITimelineItem
from core.container.analysis import AnalysisContainer
from core.container.project import Screenshot, ScreenshotGroup, Segment, Segmentation, Annotation, AnnotationLayer, \
    ITimeRange
from core.data.computation import ms_to_frames

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.container.project import VIANProject
    from core.container.analysis import AnalysisContainer

VisualizationTab = namedtuple("VisualizationTab", ["name", "widget", "use_filter", "controls"])


class IProjectChangeNotify():
    def __init__(self, dummy=None):
        dummy = dummy

    def on_loaded(self, project):
        pass

    def on_changed(self, project, item):
        pass

    def get_project(self):
        return None

    def on_selected(self, sender, selected):
        pass

    def on_closed(self):
        pass


class ITimeStepDepending():
    def __init__(self, dummy=None):
        dummy = dummy

    def on_timestep_update(self, time):
        log_debug("ITimeStepDepending: Not Implemented by", self)


class SpatialOverlayDataset:
    """
    A SpatialOverlayDataset is a entity to register overlays over the player view.
    As such, IAnalysisJob instances which contain analyses with spatial and temporal quantities,
    can return a list of SpatialOverlayDataset which can be selected by the user in the player widget.

    """
    VIS_TYPE_HISTOGRAM = 0
    VIS_TYPE_HEATMAP = 1
    VIS_TYPE_COLOR_RGBA = 2
    VIS_TYPE_POINTS = 3

    def __init__(self, name, ms_to_idx, project, analysis, vis_type=VIS_TYPE_HEATMAP):
        self.name = name
        self.ms_to_idx = ms_to_idx
        self.project = project
        self.analysis = analysis
        self.vis_type = vis_type

    def get_data_for_time(self, time_ms, frame):
        raise NotImplementedError("SpatialOverlayDataset:get_data_for_time not implemented")


class TimelineDataset(ITimelineItem):
    """
    A Dataset which can be displayed in the timeline.
    The get_data_range function has to be overwritten accordingly.

    """
    VIS_TYPE_AREA = 0
    VIS_TYPE_LINE = 1

    def __init__(self, name, data, ms_to_idx=1.0, vis_type=VIS_TYPE_LINE, vis_color=QColor(98, 161, 169)):
        self.data = data
        self.d_max = np.amax(self.data)
        self.strip_height = 45
        self.name = name
        self.ms_to_idx = ms_to_idx
        self.vis_type = vis_type
        self.vis_color = vis_color

    def get_data_range(self, t_start, t_end, norm=True, filter_window=1):
        idx_a = int(np.floor(t_start / self.ms_to_idx))
        idx_b = int(np.ceil(t_end / self.ms_to_idx))

        offset = (t_start / self.ms_to_idx) - int(np.floor(t_start / self.ms_to_idx))

        ms = np.array(list(range(idx_a, idx_b)))
        ms = np.multiply(ms, self.ms_to_idx)
        ms = np.subtract(ms, offset)

        data = np.array(self.data[idx_a:idx_b].copy())

        if data.shape[0] == 0:
            return np.array([]), np.array([])

        frac = data.shape[0] / 20
        if data.shape[0] > frac:
            k = filter_window

            data = resample(data, data[0::k].shape[0])
            ms = ms[0::k]
        if norm:
            tmax = np.amax([np.amax(resample(self.data, data[0::filter_window].shape[0])), np.amax(data)])
            data /= tmax
        try:
            return data, ms
        except Exception as e:
            log_error(e)
        return np.array([]), np.array([])

    def get_value_at_time(self, ms):
        ms = np.multiply(ms, self.ms_to_idx)
        ms = np.clip(int(ms), 0, self.data.shape[0] - 1)

        return self.data[int(ms)] # / self.d_max

    def get_name(self):
        return self.name

    def get_notes(self):
        return ""


class IAnalysisJob(QObject):
    """
    This is the BaseClass for all Analyses. 
    Subclass it to implement your own Analyses. 
    
    """

    def __init__(self, name, source_types,
                 dataset_name=None, dataset_shape=None, dataset_dtype=None,
                 help_path="",
                 author="No Author",
                 version="0.0.1",
                 multiple_result=False,
                 data_serialization=DataSerialization.HDF5_MULTIPLE):
        """
        
        :param name: The name of the Analysis, used in the UI.
        :param source_types: A list of ProjectContainers which are allowed as input-type for the Analysis
        :param help_path: A optional path to the doc-html.
        :param author: The Authors Name
        :param version: The Version of the Analysis Implementation
        :param multiple_result: Whether the Analysis should run for each input container 
        seperately or once for all input containers
        """
        super(IAnalysisJob, self).__init__()
        if (dataset_name is None or dataset_dtype is None or dataset_shape is None) and \
                (data_serialization == DataSerialization.HDF5_MULTIPLE
                 or data_serialization == DataSerialization.HDF5_SINGLE):
            raise ValueError("For HDF5 stored analyses a dataset has to be given")

        self.name = name
        self.source_types = source_types
        self.dataset_name = dataset_name
        self.dataset_shape = dataset_shape
        self.dataset_dtype = dataset_dtype
        self.help_path = help_path
        self.author = author
        self.version = version
        self.multiple_result = multiple_result
        self.data_serialization = data_serialization
        self.hdf5_manager = None

        self.target_class_obj = None
        self.aborted = False

        self.max_width = 1920

    def get_name(self):
        return self.name

    def prepare(self, project, targets, fps, class_objs=None) -> Tuple[
        List[Union[Screenshot, Annotation, Segment]], Dict]:
        """
        A step that should be performed in the main-thread before the processing takes place. 
        This is a good point to fetch all necessary data from the project and pack it to your needs.
        
        :param project: The current Project
        :param targets: The Target IProjectContainer Objects
        :param parameters: Additional Parameters as returned from your ParameterWidget.get_parameters()
        :param fps: The FPS of the Movie. (This is used to convert Timestamps into Frame-Position)
        :param class_objs: The Classification Object assigned if any. (This is important to determine on which semantic segmentation mask label the analysis operates)
        :return: A List of packed Data which will be handed to the IAnalysisJob.process()
        """
        self.target_class_obj = class_objs

        res_targets = []
        for t in targets:
            if isinstance(t, Screenshot) or isinstance(t, Annotation) or isinstance(t, Segment):
                res_targets.append(t)
            elif isinstance(t, ScreenshotGroup):
                res_targets.extend(t.screenshots)
            elif isinstance(t, AnnotationLayer):
                res_targets.extend(t.annotations)
            elif isinstance(t, Segmentation):
                res_targets.extend(t.segments)

        targets, args = [], []
        for t in list(set(res_targets)):
            semseg = None
            if isinstance(t, Screenshot):
                if class_objs is not None:
                    semantic_segmentations = t.get_connected_analysis("SemanticSegmentationAnalysis")
                    if len(semantic_segmentations) > 0:
                        semseg = semantic_segmentations[0]
            targets.append(t)
            args.append(
                dict(
                    start=ms_to_frames(t.get_start(), fps),
                    end=ms_to_frames(t.get_end(), fps),
                    movie_path=project.movie_descriptor.movie_path,
                    target=t.get_id(),
                    margins=project.movie_descriptor.get_letterbox_rect(),
                    semseg=semseg
                ))
        return targets, args

    def process(self, args, sign_progress):
        """
        The Processing function, this will be executed in a seperate thread. 
        Make sure to **NOT** use the ProjectContainers within this Operation.
        
        Also, for User-Convenience call the sign_progress function regularilly to indicate the current progress:
        
        *Example*:
        progress is a number E [0.0, ... , 1.0]
        sign_progress(0.5)
        
        
        :param args: the Arguments as packed in IAnalysisJob.prepare()
        :param sign_progress: a function to signal the current Progress. usage: sign_progress(float E[0.0,..1.0])
        :return: AnalysisJobAnalysis Object
        """
        if sign_progress is None:
            sign_progress = self.dummy_callback
        return args, sign_progress
        # log_debug("get_name not implemented by", self)

    def modify_project(self, project, result, main_window=None):
        """
        If your Analysis should perform any modifications to the project, except storing the analysis,
        this is the place to perform them. 
        
        :param project: The Current Project to perform modifications on
        :param result: The resulting AnalysisJobAnalysis as returned from IAnalysisJob.process()
        :return: None
        """
        if isinstance(result, list):
            for r in result:
                r.set_target_classification_obj(self.target_class_obj)
                r.set_target_container(project.get_by_id(r.target_container))

        else:
            result.set_target_classification_obj(self.target_class_obj)
            result.set_target_container(project.get_by_id(result.target_container))

    def get_parameter_widget(self):
        """
        If your Analysis has additional parameters which can be set by the User, Subclass the ParameterWidget, 
        and return it in this Function. 
        
        :return: A Subclass of ParameterWidget
        """
        return ParameterWidget()

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function is called by VIAN if the User wants to display the complete Visualization of the Data. 
        While you may essentially use any type Type of Visualization, you should either: 
        
        1. subclass QMainWindow and implement your visualization into it.
        2. if you use a WebBased visualization use 
            
            save your visualitations into the results/ directory of the project
            during the IAnalysisJob.modify_project() or IAnalysisJob.process()
            
            and in this function:
            import webbrowser
            webbrowser.open(url/to/your/result.html)
        
        When using a QMainWindow, don't forget to call QMainWindow.show() at the end of your __init__()
        
        :param analysis: The IAnalysisJobAnalysis Object created in IAnalysisJob.process()
        :param result_path: The Path to the results directory of the project
        :param data_path: The Path to the data directory of the project
        :return: A QWidget which will be added to the Visualizations Tab
        """
        log_debug("get_name not implemented by", self)

    def get_timeline_datasets(self, analysis, project) -> List[TimelineDataset]:
        """
        This function is called by VIAN after the creation of the Analysis to register any new datasets
        which should be displayed in the Timeline.

        If the data is not time dependent, this function should not be overloaded.
        :return: A list of TimelineDataset
        """
        return []

    def get_spatial_overlays(self, analysis, project) -> List[SpatialOverlayDataset]:
        return []

    def get_preview(self, analysis):
        """
        The Preview should be a visual representation of your analysis data, which can be displayed in the 
        Inspector, when the Analysis is selected. 
        
        Make sure, that the creation of this widget should be fast.
        Easiest would be to render your data into an Image, convert it into a qpixamp and 
        attach it to a QLabel using QLabel(your_pixmap).
        
        
        :param analysis: The IAnalysisJobAnalysis Object created in IAnalysisJob.process()
        :return: A QWidget serving as a preview
        """
        pass

    def get_source_types(self):
        """
        Returns a list of allowed type enum-entries
        :return: 
        """
        return self.source_types

    def serialization_type(self):
        return self.data_serialization

    def serialize(self, data_dict):
        """
        Override this Method if there needs to be a custom serialization
        :param data_dict: 
        :return: 
        """
        return data_dict

    def deserialize(self, data_dict):
        """
        Override this Method if there needs to be a custom deserialization
        :param data_dict: 
        :return: 
        """
        return data_dict

    def get_hdf5_description(self):
        """
        Returns an HDF5.Attributes dictionary describing the content of the HDF5 file.

        :return: dict
        """
        return dict()

    def fit(self, targets, class_objs=None, callback=None) -> AnalysisContainer:
        """
        Performs the analysis for given target containers and classification objects.
        If no classification object is given, a default one with the name "Global" is created.

        :param targets: The Target IProjectContainer Objects
        :param class_objs: The Classification Object assigned if any. (This is important to determine on which semantic segmentation mask label the analysis operates)
        """
        if isinstance(targets, list):
            project = targets[0].project  # type:VIANProject
        else:
            project = targets.project
            targets = [targets]

        if callback is None:
            callback = self.dummy_callback

        if class_objs is None:
            clobj = project.get_classification_object_global("Global")
            X = self._fit_single(project, targets, clobj, callback=callback)
        else:
            if not isinstance(class_objs, list):
                class_objs = [class_objs]
            X = [self._fit_single(project, targets, clobj, callback=callback) for clobj in class_objs]

        return X

    def _fit_single(self, project, targets, clobj, callback):
        fps = project.movie_descriptor.fps
        args = self.prepare(project, targets, fps, clobj)

        res = []
        if self.multiple_result:
            for i, arg in enumerate(args):
                res.append(self.process(arg, callback))
        else:
            res = self.process(args, callback)

        if isinstance(res, list):
            for r in res:
                if r is None:
                    continue
                with project.project_lock:
                    self.modify_project(project, r)
                    project.add_analysis(r)
        else:
            if res is None:
                return None
            with project.project_lock:
                self.modify_project(project, res)
                project.add_analysis(res)
        return res

    def from_hdf5(self, db_data):
        return db_data

    def to_hdf5(self, data):
        return data

    def to_file(self, data, file_path):
        return file_path

    def from_file(self, file_path):
        return None

    def get_file_path(self, file_path):
        return file_path

    def abort(self):
        pass

    def dummy_callback(*args):
        pass


class ParameterWidget(QWidget):
    """
    The ParameterWidget is an additional widget which will be added to the Analysis Dialog. 
    Make sure to override the ParameterWidget.get_parameters() function to return the parameters in your 
    desired form.
    
    """

    def __init__(self):
        super(ParameterWidget, self).__init__(None)

    def get_parameters(self):
        """
        This is called on_analyse, bundles your parameters and hands them to the IAnalysisJob.process()
        
        :return: A List of Parameters
        """
        return None


class IConcurrentJob():
    def __init__(self, args, show_modify_progress=False):
        self.show_modify_progress = show_modify_progress
        self.args = args
        self.task_id = randint(10000000, 99999999)
        self.aborted = False

    def prepare(self, project):
        pass

    def run_concurrent(self, args, sign_progress):
        log_debug("run_concurrent not implemented by", self)

    def modify_project(self, project, result, sign_progress=None, main_window=None):
        pass

    def abort(self):
        self.aborted = True
