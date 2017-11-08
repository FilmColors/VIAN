from random import randint
from PyQt5.QtWidgets import *
class IProjectChangeNotify():
    def __init__(self, dummy = None):
        dummy = dummy

    def on_loaded(self, project):
        print "IProjectChangeNotify: Not Implemented", self

    def on_changed(self, project, item):
        print "IProjectChangeNotify: Not Implemented", self

    def get_project(self):
        print "IProjectChangeNotify: Not Implemented", self

    def on_selected(self, sender, selected):
        print "IProjectChangeNotify: Not Implemented by ",self


class IProjectContainer:
    def __init__(self):
        self.project = None
        self.outliner_expanded = False
        self.outliner_highlighted = False
        self.unique_id = -1

    def set_expanded(self, expanded):
        self.outliner_expanded = expanded

    def delete(self):
        print "Not Implemented in ", self

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
        self.dispatch_on_changed(item=self)


class ITimeRange():

    def get_start(self):
        print "ITimelineItem: Not implemented" , self

    def get_end(self):
        print "ITimelineItem: Not Implemented", self

    def set_start(self, start):
        print "ITimelineItem: Not Implemented", self

    def set_end(self, end):
        print "ITimelineItem: Not Implemented", self

    def move(self, start, end):
        print "ITimelineItem: Not Implemented", self


class ITimelineItem:
    def set_timeline_visibility(self, visibility):
        print "ITimelineItem: Not Implemented", self

    def get_timeline_visibility(self):
        print "ITimelineItem: Not Implemented", self


class IHasName():
    def __init__(self,dummy = None):
        dummy = dummy

    def get_name(self):
        print "IHasName: Not Implemented by", self

    def set_name(self, name):
        print "IHasName: Not Implemented by", self


class ITimeStepDepending():
    def __init__(self,dummy = None):
        dummy = dummy

    def on_timestep_update(self, time):
        print "ITimeStepDepending: Not Implemented by", self


class ISelectable():
    def __init__(self,dummy = None):
        dummy = dummy

    def get_type(self):
        print "ISelectable: Not Implemented by", self


class IAnalysisJob():
    source_types = []
    def get_name(self):
        print "get_name not implemented by", self

    def prepare(self, movie_path, targets):
        print "prepare not implemented by", self
        return None

    def process(self, target_id, args, sign_progress):
        print "get_name not implemented by", self

    def get_preferences(self):
        widget = QWidget()
        widget.setLayout(QHBoxLayout(widget))
        widget.layout().addWidget(QPushButton(widget))
        widget.layout().addWidget(QPushButton(widget))
        widget.layout().addWidget(QPushButton(widget))

        return widget

    def get_visualization(self, parent, analysis):
        print "get_name not implemented by", self

    def get_source_types(self):
        return self.source_types


class IConcurrentJob():
    def __init__(self, args):
        self.args = args
        self.task_id = randint(10000000, 99999999)

    def prepare(self):
        self.args = self.args

    def run_concurrent(self, args, sign_progress):
        print "run_concurrent not implemented by", self

    def modify_project(self, project, result):
        print "modify_project not implemented by", self

