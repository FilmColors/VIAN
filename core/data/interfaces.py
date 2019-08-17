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


class ITimeStepDepending():
    def __init__(self,dummy = None):
        dummy = dummy

    def on_timestep_update(self, time):
        print("ITimeStepDepending: Not Implemented by", self)


class IAnalysisJob(QObject):
    """
    This is the BaseClass for all Analyses. 
    Subclass it to implement your own Analyses. 
    
    """
    def __init__(self, name, source_types,
                 dataset_name, dataset_shape, dataset_dtype,
                 help_path = "",
                 author="No Author",
                 version = "0.0.1",
                 multiple_result = False,
                 data_serialization = DataSerialization.JSON):
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
        # Apply the given parameters
        if parameters is None:
            return
        for k, v in parameters.items():
            if hasattr(self, k):
                setattr(self, k, v)

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


class TimelineDataset:
    """
    A Dataset which can be displayed in the timeline.
    The get_data_range function has to be overwritten accordingly.

    """
    def __init__(self, data):
        self.data = data

    def get_data_range(self, t_start, t_end):
        return None
