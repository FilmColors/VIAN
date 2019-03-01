"""
In this Module, all interfaces used by VIAN are defined. 
"""

from random import randint
from collections import namedtuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.enums import DataSerialization
#
# from core.data.project_streaming import STREAM_DATA_IPROJECT_CONTAINER
VisualizationTab = namedtuple("VisualizationTab", ["name", "widget", "use_filter", "controls"])

class IProjectChangeNotify():
    def __init__(self, dummy = None):
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


class IClassifiable():
    onQueryHighlightChanged = pyqtSignal(bool)

    def __init__(self):
        self.voc_list = []
        self.is_query_highlighted = False

    def set_classification_highlight(self, state):
        self.onQueryHighlightChanged.emit(state)

    def get_parent_container(self):
        return None

    def has_word(self, word):
        pass
        # return word in self.voc_list

    def toggle_word(self, word):
        pass
        # if word in self.voc_list:
        #     self.remove_word(word)
        # else:
        #     self.add_word(word)

    def add_word(self, word):
        pass
        # if word not in self.voc_list:
        #     self.voc_list.append(word)
        #     word.add_connected_item(self)

    def remove_word(self, word):
        pass
        # if word in self.voc_list:
        #     self.voc_list.remove(word)
        # word.remove_connected_item(self)


class IProjectContainer(QObject):
    onAnalysisAdded = pyqtSignal(object)
    onAnalysisRemoved = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)
        self.project = None
        self.outliner_expanded = False
        self.outliner_highlighted = False
        self.unique_id = -1
        self.notes = ""

        self.connected_analyses = []

    def get_id(self):
        return self.unique_id

    def set_expanded(self, expanded):
        self.outliner_expanded = expanded

    def add_analysis(self, analysis):
        self.connected_analyses.append(analysis)
        analysis.set_project(self.project)
        self.onAnalysisAdded.emit(analysis)

    def remove_analysis(self, analysis):
        if analysis in self.connected_analyses:
            self.connected_analyses.remove(analysis)
            self.onAnalysisRemoved.emit(analysis)

    def get_connected_analysis(self, class_type=None, as_clobj_dict = False):
        """
        Returns a List of AnalysesResults that are of class_type, and attached to this container
        
        :param class_type: 
        :return: 
        """
        if class_type is None:
            to_return = self.connected_analyses
        else:
            to_return = []
            if isinstance(class_type, str):
                class_name = class_type
            else:
                class_name = class_type.__name__
            for r in self.connected_analyses:
                if r.analysis_job_class == class_name:
                    to_return.append(r)

        if as_clobj_dict:
            result = dict()
            for t in to_return:
                cl_obj =  t.target_classification_object
                if cl_obj is None:
                    cl_obj = "default"
                elif cl_obj.name == "Global":
                    if "default" not in result:
                        result["default"] = []
                    result["default"].append(t)

                if cl_obj not in result:
                    result[cl_obj] = []
                result[cl_obj].append(t)
            return result

        else:
            return to_return

    def delete(self):
        print("Not Implemented in ", self)

    def set_project(self, project):
        if project is not None:
            self.project = project
            if self.unique_id == -1:
                self.unique_id = self.project.create_unique_id()
            if self.project.get_by_id(self.unique_id) is None:
                self.project.add_to_id_list(self, self.unique_id)

    def dispatch_on_changed(self, receiver = None, item = None):
        if self.project is not None:
            self.project.dispatch_changed(receiver, item = item)

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes
        # self.dispatch_on_changed(item=self)

    def copy_event(self, target):
        """
        This Event is raised when the user wants to copy this container into some. 
        :param containers: 
        :return: 
        """
        pass

    def get_type(self):
        return -1


class ITimeRange():

    def get_start(self):
        print("ITimelineItem: Not implemented" , self)

    def get_end(self):
        print("ITimelineItem: Not Implemented", self)

    def set_start(self, start):
        print("ITimelineItem: Not Implemented", self)

    def set_end(self, end):
        print("ITimelineItem: Not Implemented", self)

    def move(self, start, end):
        print("ITimelineItem: Not Implemented", self)


class ILockable():
    def __init__(self):
        self.locked = False

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def is_locked(self):
        return self.locked


class ITimelineItem:
    def set_timeline_visibility(self, visibility):
        print("ITimelineItem: Not Implemented", self)

    def get_timeline_visibility(self):
        print("ITimelineItem: Not Implemented", self)


class IHasName():
    def __init__(self,dummy = None):
        dummy = dummy

    def get_name(self):
        print("IHasName: Not Implemented by", self)

    def set_name(self, name):
        print("IHasName: Not Implemented by", self)


class IHasMediaObject():
    def __init__(self):
        self.media_objects = []

    def add_media_object(self, media_object):
        if media_object not in self.media_objects:
            self.media_objects.append(media_object)

    def remove_media_object(self, media_object):
        if media_object in self.media_objects:
            media_object.delete()
            self.media_objects.remove(media_object)
        self.project.dispatch_changed()


class ITimeStepDepending():
    def __init__(self,dummy = None):
        dummy = dummy

    def on_timestep_update(self, time):
        print("ITimeStepDepending: Not Implemented by", self)


class ISelectable():
    def __init__(self,dummy = None):
        dummy = dummy

    def get_type(self):
        print("ISelectable: Not Implemented by", self)


class ILiveWidgetExposing():
    def get_live_widget(self):
        pass
    def compute_widget(self, frame, data):
        pass


class IAnalysisJob(ILiveWidgetExposing):
    """
    This is the BaseClass for all Analyses. 
    Subclass it to implement your own Analyses. 
    
    """
    def __init__(self, name, source_types,
                 dataset_name, dataset_shape, dataset_dtype,
                 help_path = "", author="No Author", version = "0.0.1",
                 multiple_result = False, data_serialization = DataSerialization.JSON):
        """
        
        :param name: The name of the Analysis, used in the UI.
        :param source_types: A list of ProjectContainers which are allowed as input-type for the Analysis
        :param help_path: A optional path to the doc-html.
        :param author: The Authors Name
        :param version: The Version of the Analysis Implementation
        :param multiple_result: Whether the Analysis should run for each input container 
        seperately or once for all input containers
        """
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

    def get_name(self):
        return self.name

    def prepare(self, project, targets, parameters, fps, class_objs = None):
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

        return None

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
        print("get_name not implemented by", self)

    def modify_project(self, project, result, main_window = None):
        """
        If your Analysis should perform any modifications to the project, except storing the analysis,
        this is the place to perform them. 
        
        :param project: The Current Project to perform modifications on
        :param result: The resulting AnalysisJobAnalysis as returned from IAnalysisJob.process()
        :return: None
        """
        pass

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
        print("get_name not implemented by", self)

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

    def to_json(self, container_data):
        """
        Base Method which should return a dict of byte serialized 
        nump arrays if necessary, or a dict of simple key value pairs.

        For numpy arrays use following: 
        byte_array = numpy_array.tostring()

        :return: 
        """
        return dict()

    def from_json(self, database_data):
        """
        The inverse of the to_database() implementation. 

        For numpy arrays:
        numpy_array = numpy.fromstring(byte_array)

        :return: 
        """

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

    def from_hdf5(self, db_data):
        return db_data

    def to_hdf5(self, data):
        return data

    def abort(self):
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


class AutomatedTextSource():
    def get_source_properties(self):
        return None

    def get_auto_text(self, property_name, time_ms, fps):
        return ""


class IConcurrentJob():
    def __init__(self, args, show_modify_progress= False):
        self.show_modify_progress = show_modify_progress
        self.args = args
        self.task_id = randint(10000000, 99999999)
        self.aborted = False

    def prepare(self, project):
        pass

    def run_concurrent(self, args, sign_progress):
        print("run_concurrent not implemented by", self)

    def modify_project(self, project, result, sign_progress = None, main_window = None):
        pass

    def abort(self):
        self.aborted = True


