from random import randint
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject
class IProjectChangeNotify():
    def __init__(self, dummy = None):
        dummy = dummy

    def on_loaded(self, project):
        print("IProjectChangeNotify: Not Implemented", self)

    def on_changed(self, project, item):
        print("IProjectChangeNotify: Not Implemented", self)

    def get_project(self):
        print("IProjectChangeNotify: Not Implemented", self)

    def on_selected(self, sender, selected):
        print("IProjectChangeNotify: Not Implemented by ",self)


class IHasVocabulary():
    def __init__(self):
        self.voc_list = []

    def has_word(self, word):
        return word in self.voc_list

    def toggle_word(self, word):
        if word in self.voc_list:
            self.remove_word(word)
        else:
            self.add_word(word)

    def add_word(self, word):
        if word not in self.voc_list:
            self.voc_list.append(word)
            word.add_connected_item(self)

    def remove_word(self, word):
        if word in self.voc_list:
            self.voc_list.remove(word)
        word.remove_connected_item(self)


class IProjectContainer(IHasVocabulary, QObject):
    def __init__(self):
        QObject.__init__(self)
        IHasVocabulary.__init__(self)
        self.project = None
        self.outliner_expanded = False
        self.outliner_highlighted = False
        self.unique_id = -1
        self.notes = ""

    def get_id(self):
        return self.unique_id

    def set_expanded(self, expanded):
        self.outliner_expanded = expanded

    def delete(self):
        print("Not Implemented in ", self)

    def set_project(self, project):
        if project is not None:
            self.project = project
            if self.unique_id == -1:
                self.unique_id = self.project.create_unique_id()
            self.project.add_to_id_list(self, self.unique_id)

    def dispatch_on_changed(self, receiver = None, item = None):
        if self.project is not None:
            self.project.dispatch_changed(receiver, item = item)

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes
        # self.dispatch_on_changed(item=self)


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
    def __init__(self, name, source_types, help_path = "", author="No Author", version = "0.0.1", multiple_result = False):
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
        self.help_path = help_path
        self.author = author
        self.version = version
        self.multiple_result = multiple_result

    def get_name(self):
        return self.name

    def prepare(self, project, targets, parameters, fps):
        """
        A step that should be performed in the main-thread before the processing takes place. 
        This is a good point to fetch all necessary data from the project and pack it to your needs.
        
        :param project: The current Project
        :param targets: The Target IProjectContainer Objects
        :param parameters: Additional Parameters as returned from your ParameterWidget.get_parameters()
        :param fps: The FPS of the Movie. (This is used to convert Timestamps into Frame-Position)
        :return: A List of packed Data which will be handed to the IAnalysisJob.process()
        """
        print("prepare not implemented by", self)
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

    def modify_project(self, project, result):
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
        :return: 
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
        return self.source_types


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

    def prepare(self):
        self.args = self.args

    def run_concurrent(self, args, sign_progress):
        print("run_concurrent not implemented by", self)

    def modify_project(self, project, result, sign_progress = None):
        pass
        # print "modify_project not implemented by", self

    def abort(self):
        self.aborted = True


