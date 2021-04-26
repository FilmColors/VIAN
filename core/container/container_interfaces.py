"""
In this Module, all interfaces used by VIAN are defined.
"""
import os
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.enums import GENERIC
from core.data.log import log_error, log_warning
from .annotation_body import AnnotationBody


_VIAN_ROOT = os.path.abspath(os.path.split( __file__)[0] + "/../..")
print(_VIAN_ROOT,  os.path.split( __file__)[0] + "/../..")


class IClassifiable():
    onQueryHighlightChanged = pyqtSignal(bool)
    onClassificationChanged = pyqtSignal(object)

    def __init__(self):
        self.tag_keywords = []
        self.is_query_highlighted = False

    def set_classification_highlight(self, state):
        self.onQueryHighlightChanged.emit(state)

    def get_parent_container(self):
        return None

    def has_word(self, keyword):
        return keyword in self.tag_keywords

    def toggle_word(self, keyword):
        if self.has_word(keyword):
            self.remove_word(keyword)
        else:
            self.add_word(keyword)

    def add_word(self, keyword):
        if keyword not in self.tag_keywords:
            self.tag_keywords.append(keyword)
            self.onClassificationChanged.emit(self.tag_keywords)

    def remove_word(self, keyword):
        if keyword in self.tag_keywords:
            self.tag_keywords.remove(keyword)
            self.onClassificationChanged.emit(self.tag_keywords)


class IProjectContainer(QObject):
    onAnalysisAdded = pyqtSignal(object)
    onAnalysisRemoved = pyqtSignal(object)

    onSelectedChanged = pyqtSignal(bool)

    def __init__(self, unique_id = -1):
        QObject.__init__(self)
        self.project = None #type: VIANProject
        self.outliner_expanded = False
        self.outliner_highlighted = False
        self.unique_id = unique_id
        self.notes = ""

        self.connected_analyses = []

    def get_id(self):
        return self.unique_id

    def get_annotation_body(self):
        return AnnotationBody("", "text/plain")

    def set_expanded(self, expanded):
        self.outliner_expanded = expanded

    def add_analysis(self, analysis):
        existing = self.has_analysis(analysis.analysis_job_class,
                                     analysis.target_classification_object,
                                     ret_analysis=True)
        if existing is not None:
            self.project.remove_analysis(existing)

        self.connected_analyses.append(analysis)
        analysis.set_project(self.project)
        self.onAnalysisAdded.emit(analysis)

    def remove_analysis(self, analysis):
        if analysis in self.connected_analyses:
            self.connected_analyses.remove(analysis)
            self.onAnalysisRemoved.emit(analysis)

    def delete_analyses(self):
        to_remove = [a for a in self.connected_analyses]
        for a in to_remove:
            self.project.remove_analysis(a)

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

    def has_analysis(self, class_type, classification_object=None, ret_analysis = True):
        """
        Checks if a given analysis class is already present for this container.
        If so it returns True/False when ret_analysis is False, else it returns the analysis or None.
        """
        if isinstance(class_type, str):
            class_name = class_type
        else:
            class_name = class_type.__name__

        result = None
        for r in self.connected_analyses:
            if classification_object is None \
                    or classification_object == r.target_classification_object:
                if r.analysis_job_class == class_name:
                    result = r
                    break

        if result is not None:
            return result if ret_analysis else True
        else:
            return None if ret_analysis else False

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
        log_error("Not Implemented in ", self)

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
        self.project.undo_manager.to_undo((self.set_notes, [notes]),
                                          (self.set_notes, [self.notes]))
        self.notes = notes

    def copy_event(self, target):
        """
        This Event is raised when the user wants to copy this container into some.
        :param containers:
        :return:
        """
        pass

    def get_type(self):
        return -1

    def select(self, multi_select=False):
        if self.project is not None:
            if multi_select:
                self.project.add_selected(self)
            else:
                self.project.set_selected(None, self)
            self.onSelectedChanged.emit(True)

    def deselect(self):
        if self.project is not None:
            self.project.remove_selected(self)
            self.onSelectedChanged.emit(False)


class ITimeRange():

    def get_start(self):
        log_warning("ITimelineItem: Not implemented", self)

    def get_end(self):
        log_warning("ITimelineItem: Not Implemented", self)

    def set_start(self, start):
        log_warning("ITimelineItem: Not Implemented", self)

    def set_end(self, end):
        log_warning("ITimelineItem: Not Implemented", self)

    def move(self, start, end, dispatch = True):
        log_warning("ITimelineItem: Not Implemented", self)


class ILockable():
    onLockChanged = pyqtSignal(bool)
    def __init__(self):
        self.locked = False

    def lock(self):
        self.onLockChanged.emit(True)
        self.locked = True

    def unlock(self):
        self.onLockChanged.emit(False)
        self.locked = False

    def is_locked(self):
        return self.locked


class ITimelineItem:

    def get_type(self):
        return GENERIC

    def get_name(self):
        return "No Name"

    def get_notes(self):
        return ""

    def set_timeline_visibility(self, visibility):
        log_warning("ITimelineItem: Not Implemented", self)

    def get_timeline_visibility(self):
        log_warning("ITimelineItem: Not Implemented", self)


class IHasName():
    def __init__(self, dummy=None):
        dummy = dummy

    def get_name(self):
        log_warning("IHasName: Not Implemented by", self)

    def set_name(self, name):
        log_warning("IHasName: Not Implemented by", self)


class IHasMediaObject():
    onMediaAdded = pyqtSignal(object)
    onMediaRemoved = pyqtSignal(object)

    def __init__(self):
        self.media_objects = []

    def add_media_object(self, media_object):
        if media_object not in self.media_objects:
            self.media_objects.append(media_object)
            self.onMediaAdded.emit(media_object)

    def remove_media_object(self, media_object):
        if media_object in self.media_objects:
            media_object.delete()
            self.media_objects.remove(media_object)
            self.onMediaRemoved.emit(media_object)
        self.project.dispatch_changed()


class ISelectable():
    def __init__(self, dummy=None):
        dummy = dummy

    def get_type(self):
        log_warning("ISelectable: Not Implemented by", self)


class AutomatedTextSource():
    def get_source_properties(self):
        return None

    def get_auto_text(self, property_name, time_ms, fps):
        return ""


def deprecation_serialization(d, keys):
    for k in keys:
        if k in d:
            return d[k]
    return None