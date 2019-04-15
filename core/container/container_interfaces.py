"""
In this Module, all interfaces used by VIAN are defined.
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


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

    def get_connected_analysis(self, class_type=None, as_clobj_dict=False):
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
                cl_obj = t.target_classification_object
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

    def save_delete(self):
        """
        This function is called in the GUI and is ment to wrap the self.delete() function, such
        that the a GUI event can be raised if necessary, for example if the delete should raise a warning of
        unexpected bevhaviour for the user.

        If not overriden, it calls the delete() function directly.

        :return:
        """
        self.delete()

    def delete(self):
        print("Not Implemented in ", self)

    def set_project(self, project):
        if project is not None:
            self.project = project
            if self.unique_id == -1:
                self.unique_id = self.project.create_unique_id()
            if self.project.get_by_id(self.unique_id) is None:
                self.project.add_to_id_list(self, self.unique_id)

    def dispatch_on_changed(self, receiver=None, item=None):
        if self.project is not None:
            self.project.dispatch_changed(receiver, item=item)

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
        print("ITimelineItem: Not implemented", self)

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
    def __init__(self, dummy=None):
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


class ISelectable():
    def __init__(self, dummy=None):
        dummy = dummy

    def get_type(self):
        print("ISelectable: Not Implemented by", self)


class AutomatedTextSource():
    def get_source_properties(self):
        return None

    def get_auto_text(self, property_name, time_ms, fps):
        return ""





