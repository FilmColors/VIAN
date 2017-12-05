import datetime
import json
import cv2
import os
from random import randint
import shelve
from .computation import blend_transparent
import numpy as np
from core.data.interfaces import IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable
from core.data.undo_redo_manager import UndoRedoManager
from core.data.computation import *
from core.gui.vocabulary import VocabularyItem
from core.data.project_streaming import ProjectStreamer
from core.data.enums import *

from core.node_editor.node_editor import *

from enum import Enum
# from PyQt4 import QtCore, QtGui
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QPoint, QRect, QSize
#
# PROJECT = -1
# SEGMENTATION = 0
# SEGMENT = 1
# ANNOTATION = 2
# ANNOTATION_LAYER = 3
# SCREENSHOT = 4
# MOVIE_DESCRIPTOR = 5
# ANALYSIS = 6
# SCREENSHOT_GROUP = 7
# NODE = 8
# NODE_SCRIPT = 9


class ElanExtensionProject(IHasName, IHasVocabulary):
    def __init__(self, main_window, path = "", name = ""):
        IHasVocabulary.__init__(self)
        self.undo_manager = UndoRedoManager()
        self.main_window = main_window
        # self.streamer = main_window.project_streamer
        self.inhibit_dispatch = True

        self.path = path
        self.name = name
        self.id_list = []

        self.annotation_layers = []
        self.current_annotation_layer = None
        self.screenshots = []
        self.segmentation = []
        self.main_segmentation_index = 0
        self.movie_descriptor = MovieDescriptor(project=self)
        self.analysis = []
        self.screenshot_groups = []
        self.vocabularies = []

        self.current_script = None
        self.node_scripts = []
        self.create_script(dispatch=False)


        self.add_screenshot_group("All Shots", initial=True)
        self.active_screenshot_group = self.screenshot_groups[0]
        self.active_screenshot_group.is_current = True

        self.folder = path.split("/")[len(path.split("/")) - 1]
        self.notes = ""



        self.add_vocabulary(get_default_vocabulary())
        self.inhibit_dispatch = False
        self.selected = []

    def highlight_types(self, types):

        for s in self.segmentation:
            if SEGMENTATION in types:
                s.outliner_highlighted = True
            else:
                s.outliner_highlighted = False

            for segm in s.segments:
                if SEGMENT in types:
                    segm.outliner_highlighted = True
                else:
                    segm.outliner_highlighted = False

        for s in self.screenshots:
            if SCREENSHOT in types:
                s.outliner_highlighted = True
            else:
                s.outliner_highlighted = False

        for s in self.annotation_layers:
            if ANNOTATION_LAYER in types:
                s.outliner_highlighted = True
            else:
                s.outliner_highlighted = False

                for ann in s.annotations:
                    if ANNOTATION in types:
                        ann.outliner_highlighted = True
                    else:
                        ann.outliner_highlighted = False

        for s in self.analysis:
            if ANALYSIS in types:
                s.outliner_highlighted = True
            else:
                s.outliner_highlighted = False

        if MOVIE_DESCRIPTOR in types:
            self.movie_descriptor.outliner_highlighted = True
        else:
            self.movie_descriptor.outliner_highlighted = False

        self.dispatch_changed()

    def get_type(self):
        return PROJECT

    #region Segmentation
    def create_segmentation(self, name = None):
        s = Segmentation(name)

        self.add_segmentation(s)
        return s

    def add_segmentation(self, segmentation):
        self.segmentation.append(segmentation)
        segmentation.set_project(self)

        self.undo_manager.to_undo((self.add_segmentation, [segmentation]), (self.remove_segmentation, [segmentation]))
        self.dispatch_changed()

    def remove_segmentation(self, segmentation):
        if self.segmentation[self.main_segmentation_index] is segmentation:
            main_segmentation = self.segmentation[0]
        else:
            main_segmentation = self.segmentation[self.main_segmentation_index]

        self.segmentation.remove(segmentation)
        self.undo_manager.to_undo((self.remove_segmentation, [segmentation]), (self.add_segmentation, [segmentation]))


        if main_segmentation in self.segmentation:
            self.main_segmentation_index = self.segmentation.index(main_segmentation)
            for s in self.screenshots:
                 s.update_scene_id(self.segmentation[self.main_segmentation_index])
        else:
            self.main_segmentation_index = 0
        self.dispatch_changed()

    def has_segmentation(self):
        if len(self.segmentation) > 0:
            return True
        return False

    def set_main_segmentation(self, segm):
        if len(self.segmentation) > 1:
            self.segmentation[self.main_segmentation_index].is_main_segmentation = False
            self.undo_manager.to_undo((self.set_main_segmentation, [self.get_main_segmentation()]),
                                      (self.set_main_segmentation, [segm]))

            # self.segmentation.remove(segm)
            # t = self.segmentation
            # self.segmentation = [segm]
            # self.segmentation.extend(t)
            index = self.segmentation.index(segm)
            self.main_segmentation_index = index
            self.segmentation[index].is_main_segmentation = True

            # for s in self.screenshots:
            #     s.update_scene_id(self.segmentation[0])
            for s in self.screenshots:
                s.update_scene_id(self.segmentation[index])
                s.update_scene_id(self.segmentation[index])


        self.dispatch_changed()

    def get_main_segmentation(self):
        if len(self.segmentation) > 0:
            return self.segmentation[self.main_segmentation_index]
            # return self.segmentation[0]
        else:
            return None

    def remove_segment(self, segment):
        for s in self.segmentation:
            if segment in s.segments:
                s.remove_segment(segment)
                break

    def get_segmentations(self):
        return self.segmentation

    # endregion

    # region Screenshots

    def add_screenshot(self, screenshot, group = 0):
        self.screenshots.append(screenshot)
        screenshot.set_project(self)

        self.screenshot_groups[0].add_screenshots(screenshot)
        if group == 0 and self.active_screenshot_group is not None and self.active_screenshot_group is not self.screenshot_groups[0]:
            self.active_screenshot_group.add_screenshots(screenshot)


        self.sort_screenshots()
        self.undo_manager.to_undo((self.add_screenshot, [screenshot]),(self.remove_screenshot, [screenshot]))


        # screenshot.to_stream(self)
        self.dispatch_changed()

    def sort_screenshots(self):
        if self.get_main_segmentation():
            self.get_main_segmentation().update_segment_ids()
            self.screenshots.sort(key=lambda x: x.movie_timestamp, reverse=False)

            for grp in self.screenshot_groups:
                grp.screenshots.sort(key=lambda x: x.movie_timestamp, reverse=False)

            for s in self.screenshots:
                s.update_scene_id(self.get_main_segmentation())

            shot_id_global = 1
            shot_id_segm = 1
            current_segm = 1
            for s in self.screenshots:
                while current_segm < s.scene_id:
                    current_segm += 1
                    shot_id_segm = 1

                s.shot_id_global = shot_id_global
                s.shot_id_segm = shot_id_segm

                shot_id_segm += 1
                shot_id_global += 1

    def remove_screenshot(self, screenshot):
        for grp in self.screenshot_groups:
            for s in grp.screenshots:
                if s not in self.screenshots:
                    self.screenshots.append(s)

        if screenshot in self.screenshots:
            for grp in self.screenshot_groups:
                grp.remove_screenshots(screenshot)


            self.screenshots.remove(screenshot)
            self.sort_screenshots()
            self.undo_manager.to_undo((self.remove_screenshot, [screenshot]),(self.add_screenshot, [screenshot]))
            self.dispatch_changed()
        else:
            print("Not Found")

    def get_screenshots(self):
        return self.screenshots

    def add_screenshot_group(self, name="New Screenshot Group", initial=False, group=None):
        if not group:
            grp = ScreenshotGroup(self, name)
        else:
            grp = group

        self.screenshot_groups.append(grp)
        if not initial:
            self.dispatch_changed()

    def remove_screenshot_group(self, grp):
        if grp is not self.screenshot_groups[0]:
            self.screenshot_groups.remove(grp)
            self.dispatch_changed()

    def get_screenshots_of_segment(self, main_segm_id):
        segmentation = self.get_main_segmentation()
        result = []
        if segmentation is not None:
            start = segmentation.segments[main_segm_id].get_start()
            end = segmentation.segments[main_segm_id].get_end()

            for s in self.screenshots:
                if start <= s.movie_timestamp < end:
                    result.append(s)

        return result


    def set_current_screenshot_group(self, grp):
        self.active_screenshot_group.is_current = False
        self.active_screenshot_group = grp
        grp.is_current = True
        self.dispatch_changed()

    def get_active_screenshots(self):
        return self.active_screenshot_group.screenshots
    #endregion

    #region Analysis
    def add_analysis(self, analyze):
        analyze.set_project(self)
        self.analysis.append(analyze)
        self.undo_manager.to_undo((self.add_analysis, [analyze]), (self.remove_analysis, [analyze]))
        self.dispatch_changed()

    def remove_analysis(self, analysis):
        self.analysis.remove(analysis)
        self.undo_manager.to_undo((self.remove_analysis, [analysis]), (self.add_analysis, [analysis]))
        self.dispatch_changed()

    def get_analyzes_of_item(self, item):
        result = []
        for a in self.analysis:
            if a.target_id == item.unique_id:
                result.append(item)
        return item
    #endregion


    # Getters for easier changes later in the project
    def set_selected(self,sender, selected = []):

        if not isinstance(selected, list):
            selected = [selected]

        self.selected = selected

        # Setting the current annotation layer
        l = None
        for s in selected:
            if s.get_type() == ANNOTATION_LAYER:
                l = s
            if s.get_type() == NODE_SCRIPT:
                self.set_current_script(s)

        if l is not None:
            self.current_annotation_layer = l


        self.dispatch_selected(sender)

    def get_selected(self, types = None):
        result = []
        if types != None:
            for s in self.selected:
                if s.get_type() in types:
                    result.append(s)
            return result
        else:
            return self.selected

    def get_movie(self):
        return self.movie_descriptor

    #region Annotations
    def create_annotation_layer(self, name, t_start, t_stop):
        layer = AnnotationLayer(name, t_start, t_stop)
        self.add_annotation_layer(layer)
        return layer

    def add_annotation_layer(self, layer):
        layer.set_project(self)
        self.annotation_layers.append(layer)
        self.current_annotation_layer = layer

        self.undo_manager.to_undo((self.add_annotation_layer, [layer]),
                                  (self.remove_annotation_layer, [layer]))
        self.dispatch_changed()

    def remove_annotation_layer(self, layer):
        if layer is self.current_annotation_layer:
            self.current_annotation_layer = None

        self.selected = None
        for a in layer.annotations:
            layer.remove_annotation(a)
        self.annotation_layers.remove(layer)


        if len(self.annotation_layers) > 0:
            self.current_annotation_layer = self.annotation_layers[0]


        self.dispatch_changed()

    def remove_annotation(self, annotation):
        for l in self.annotation_layers:
            l.remove_annotation(annotation)

    def get_annotation_layers(self):
        return self.annotation_layers
    #endregion

    #region NodeScripts
    def create_script(self, dispatch = True):
        script = NodeScript("New Script")
        self.add_script(script)

        if dispatch:
            self.dispatch_changed()

    def add_script(self, script):
        script.set_project(self)
        self.node_scripts.append(script)
        self.current_script = script

    def remove_script(self, script):
        if script in self.node_scripts:
            self.node_scripts.remove(script)
        self.dispatch_changed()

    def set_current_script(self, script, dispatch = True):
        self.current_script = script

        if dispatch:
            self.dispatch_changed()
    #endregion


    def store_project(self, settings, global_settings, path = None):
        """
        DEPRECATED
        :param settings: 
        :param global_settings: 
        :param path: 
        :return: 
        """
        a_layer = []
        screenshots = []
        screenshots_img = []
        screenshots_ann = []
        segmentations = []
        analyzes = []
        scripts = []
        vocabularies = []

        for v in self.vocabularies:
            vocabularies.append(v.serialize())

        for a in self.annotation_layers:
            a_layer.append(a.serialize())

        for b in self.screenshots:
            src, img = b.serialize()
            screenshots.append(src)
            screenshots_img.append(img[0])
            screenshots_ann.append(img[1])

        for c in self.segmentation:
            segmentations.append(c.serialize())

        for d in self.analysis:
            analyzes.append(d.serialize())

        for e in self.node_scripts:
            scripts.append(e.serialize())


        data = dict(
            path = self.path,
            name = self.name,
            notes=self.notes,
            annotation_layers = a_layer,
            current_annotation_layer = None,
            main_segmentation_index = self.main_segmentation_index,
            screenshots = screenshots,
            segmentation = segmentations,
            analyzes = analyzes,
            movie_descriptor = self.movie_descriptor.serialize(),
            scripts = scripts,
            vocabularies=vocabularies
        )

        if path is None:
            path = self.path.replace(settings.PROJECT_FILE_EXTENSION, "")

        numpy_path = path + "_scr"
        project_path = path + ".eext"

        if settings.SCREENSHOTS_STATIC_SAVE:
            np.savez(numpy_path, imgs = screenshots_img, annotations = screenshots_ann, empty=[True])


        global_settings.add_project(self)

        try:
            with open(project_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            print(Exception)

    def load_project(self, settings, path):

        if not settings.PROJECT_FILE_EXTENSION in path:
            path += settings.PROJECT_FILE_EXTENSION

        if not os.path.isfile(path):
            return

        with open(path) as f:
            my_dict = json.load(f)

        self.path = my_dict['path']
        self.path = path
        self.name = my_dict['name']
        self.main_segmentation_index = my_dict['main_segmentation_index']

        try:
            self.notes = my_dict['notes']
        except:
            self.notes = ""

        try:
            version = my_dict['locked']
        except:
            pass


        splitted = path.split("/")[0:len(path.split("/")) - 1]
        self.folder = ""
        for f in splitted:
            self.folder += f + "/"

        self.current_annotation_layer = None
        self.movie_descriptor = MovieDescriptor(project=self).deserialize(my_dict['movie_descriptor'])

        # Attempt to load the Vocabularies, this might fail if the save is from VIAN 0.1.1
        try:
            self.vocabularies = []
            for v in my_dict['vocabularies']:
                voc = Vocabulary("voc").deserialize(v, self)
                self.add_vocabulary(voc)

        except Exception as e:
            self.main_window.print_message("Loading Vocabularies failed", "Red")
            self.main_window.print_message(e, "Red")


        for a in my_dict['annotation_layers']:
            new = AnnotationLayer().deserialize(a, self)
            self.add_annotation_layer(new)

        # THIS IS OLD CODE AND SHOULD BE REMOVED
        # if settings.SCREENSHOTS_STATIC_SAVE:
        #     screenshots_path = path.replace(settings.PROJECT_FILE_EXTENSION, "_scr.npz")
        #     loaded_scr = np.load(screenshots_path)
        #     # screenshot_imgs = loaded_scr['imgs']
        #     # screenshot_ann = loaded_scr['annotations']
        #     for i, b in enumerate(my_dict['screenshots']):
        #         new = Screenshot().deserialize(b)
        #         self.add_screenshot(new)
        #
        # else:
        for i, b in enumerate(my_dict['screenshots']):
            new = Screenshot().deserialize(b, self)
            self.add_screenshot(new)

        for c in my_dict['segmentation']:
            new = Segmentation().deserialize(c, self)
            self.add_segmentation(new)

        for d in my_dict['analyzes']:
            new = Analysis().deserialize(d)
            self.add_analysis(new)

        try:
            old = self.screenshot_groups
            self.screenshot_groups = []

            for e in my_dict['screenshot_groups']:
                new = ScreenshotGroup(self).deserialize(e, self)
                self.add_screenshot_group(group=new)

            self.active_screenshot_group = self.screenshot_groups[0]
            self.screenshot_groups[0].is_current = True

        except Exception as e:
            self.screenshot_groups = old
            print(e)
            self.main_window.print_message("Loading Screenshot Group failed.", "Red")

        try:
            old_script = self.node_scripts[0]
            self.node_scripts = []

            for f in my_dict['scripts']:
                new = NodeScript().deserialize(f, self)
                self.add_script(new)

            if len(self.node_scripts) == 0:
                self.add_script(old_script)
                self.current_script = old_script
        except Exception as e:
            self.main_window.print_message("Loading Node Scripts failed", "Red")
            self.main_window.print_message(e, "Red")


        self.sort_screenshots()
        self.undo_manager.clear()

    def get_template(self, segm, voc, ann, scripts):
        segmentations = []
        vocabularies = []
        layers = []
        node_scripts = []
        if segm:
            for s in self.segmentation:
                segmentations.append(s.get_name())
        if voc:
            for v in self.vocabularies:
                vocabularies.append(v.serialize())
        if ann:
            for l in self.annotation_layers:
                layers.append([l.get_name(), l.get_start(), l.get_end()])
        if scripts:
            for n in self.node_scripts:
                node_scripts.append(n.serialize())

        template = dict(
            segmentations = segmentations,
            vocabularies = vocabularies,
            layers = layers,
            node_scripts=node_scripts
        )
        return template

    def apply_template(self, template_path):

        try:
            with open(template_path, "rb") as f:
                template = json.load(f)
        except:
            print("Importing Template Failed")
            return

        for s in template['segmentations']:
            self.create_segmentation(s)

        for v in template['vocabularies']:
            voc = Vocabulary("voc").deserialize(v, self)
            self.add_vocabulary(voc)

        for l in template['layers']:
            self.create_annotation_layer(l[0], int(l[1]), int(l[2]))

        for n in template['node_scripts']:
            new = NodeScript().deserialize(n, self)
            self.add_script(new)


    #region Vocabularies
    def create_vocabulary(self, name="New Vocabulary"):
        voc = Vocabulary(name)
        self.add_vocabulary(voc)

    def add_vocabulary(self, voc):
        voc.set_project(self)
        self.vocabularies.append(voc)
        self.dispatch_changed()

    def remove_vocabulary(self, voc):
        if voc in self.vocabularies:
            self.vocabularies.remove(voc)
        self.dispatch_changed()

    def get_auto_completer_model(self):
        """
        :return: Returns a model of words for the QCompleter, non-tree-like!
        """
        model = QStandardItemModel()
        words = []
        for v in self.vocabularies:
            words.extend(v.get_vocabulary_as_list())
        for w in words:
            model.appendRow(QStandardItem(w.name))
        return model

    def get_word_object_from_name(self, name):
        for v in self.vocabularies:
            for w in v.words_plain:
                if w.name == name:
                    return w
    #endregion

    # region Setters/Getters
    def cleanup(self):
        for l in self.annotation_layers:
            for w in l.annotations:
                w.widget.close()

    def get_time_ranges_of_selected(self):
        result = []
        for s in self.selected:
            if isinstance(s, ITimeRange):
                result.append([s.get_start(), s.get_end()])
        return result

    def get_name(self):
        return self.name

    def create_unique_id(self):
        is_unique = False
        item_id = 0
        while is_unique is False:
            item_id = randint(1000000000, 9999999999)
            if self.get_by_id(item_id) is None:
                is_unique = True

        return item_id

    def add_to_id_list(self, container_object, item_id):
        self.id_list.append((item_id, container_object))
        self.id_list = sorted(self.id_list, key=lambda x: x[0])

    def remove_from_id_list(self, container_object):
        for d in self.id_list:
            if d[1] == container_object:
                self.id_list.remove(d)
                break

    def get_by_id(self, item_id):
        """
        Binary Search
        :param id: 
        :return: 
        """
        first = 0
        last = len(self.id_list) - 1
        while first <= last:
            mid_point = (first + last) // 2
            if self.id_list[mid_point][0] == item_id:
                return self.id_list[mid_point][1]
            else:
                if self.id_list[mid_point][0] > item_id:
                    last = mid_point - 1
                else:
                    first = mid_point + 1

        return None

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes
    #endregion

    #region Dispatchers
    def dispatch_changed(self, receiver = None, item = None):
        if self.inhibit_dispatch == False:
            self.main_window.dispatch_on_changed(receiver, item = item)

    def dispatch_loaded(self):
        if self.inhibit_dispatch == False:
            self.main_window.dispatch_on_loaded()

    def dispatch_selected(self, sender):
        if self.inhibit_dispatch == False:
            self.main_window.dispatch_on_selected(sender,self.selected)
    #endregion

    pass

#region Segmentaion
class Segmentation(IProjectContainer, IHasName, ISelectable, ITimelineItem, ILockable):
    def __init__(self, name = None, segments = None):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        self.name = name
        if segments is None:
            segments = []
        self.segments = segments
        self.timeline_visibility = True
        self.notes = ""
        self.is_main_segmentation = False
        for s in self.segments:
            s.segmentation = self

    def get_segmentation_Id_list(self):
        if self.segments is not None and len(self.segments) > 0:
            return (str(s.ID) for s in self.segments)
        else:
            return None

    def create_segment(self, start, stop, ID = None, from_last_threshold = 100):
        if stop-start < from_last_threshold:
            last = None
            for s in self.segments:
                if s.end < start:
                    last = s
            if last is None:
                start = 0
            else:
                start = last.end

        if ID is None:
            ID = len(self.segments) + 1

        new_seg = Segment(ID = ID, start = start, end = stop, additional_identifiers=[str(ID)], segmentation = self)
        new_seg.set_project(self.project)

        self.add_segment(new_seg)

    def add_segment(self, segment):
        # Finding the Segments location

        if len(self.segments) == 0:
            self.segments.append(segment)
        else:
            for i, s in enumerate(self.segments):
                if s.start > segment.start:
                    self.segments.insert(i, segment)
                    break

                if i == len(self.segments) - 1:
                    self.segments.append(segment)
                    break

        self.update_segment_ids()
        self.project.sort_screenshots()


        self.project.undo_manager.to_undo((self.add_segment, [segment]), (self.remove_segment, [segment]))
        self.dispatch_on_changed()

    def remove_segment(self, segment):
        self.segments.remove(segment)

        self.update_segment_ids()
        self.project.sort_screenshots()
        self.project.undo_manager.to_undo((self.remove_segment, [segment]), (self.add_segment, [segment]))
        self.dispatch_on_changed()

    def update_segment_ids(self):
        self.segments = sorted(self.segments, key=lambda x: x.start)
        for i, s in enumerate(self.segments):
            s.ID = i + 1

    def get_segment(self, time):
        for s in self.segments:
            if s.start < time < s.end:
                return s

        return None

    def cleanup_borders(self):
        for i, s in enumerate(self.segments):
            if i < len(self.segments) - 1:
                end = s.get_end()
                start = self.segments[i + 1].get_start()
                center = (start + end) / 2
                s.end = center
                self.segments[i + 1].start = center + 1

        self.dispatch_on_changed()

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]), (self.set_name, [self.name]))
        self.name = name
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return self.name

    def serialize(self):
        s_segments = []
        for s in self.segments:
            s_segments.append(s.serialize())

        words = []
        for w in self.voc_list:
            words.append(w.unique_id)

        result = dict(
            name = self.name,
            unique_id = self.unique_id,
            segments = s_segments,
            notes = self.notes,
            locked = self.locked,
            words = words
        )

        return result

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization["name"]
        self.segments = []
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']
        for s in serialization["segments"]:
            new = Segment()
            new.deserialize(s, self)
            new.segmentation = self
            self.segments.append(new)

        try:
            self.locked = serialization['locked']

        except:
            self.locked = False

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        return self

    def get_type(self):
        return SEGMENTATION

    def lock(self):
        ILockable.lock(self)
        for s in self.segments:
            s.lock()
        self.dispatch_on_changed(item=self)

    def unlock(self):
        ILockable.unlock(self)
        for s in self.segments:
            s.unlock()
        self.dispatch_on_changed(item=self)

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def set_project(self, project):
        IProjectContainer.set_project(self, project)
        for s in self.segments:
            s.set_project(project)

    def delete(self):
        self.project.remove_segmentation(self)


class Segment(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable):
    def __init__(self, ID = None, start = None, end  = None, duration  = None, additional_identifiers = None, segmentation=None):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)

        self.ID = ID
        self.start = start
        self.end = end
        self.duration = duration
        if additional_identifiers is None:
            additional_identifiers = []
        self.additional_identifiers = additional_identifiers
        self.annotation_body = ""
        self.timeline_visibility = True
        self.segmentation = segmentation
        self.notes = ""

    def set_id(self, ID):
        self.ID = ID
        self.dispatch_on_changed(item=self)

    def set_start(self, start):
        self.project.undo_manager.to_undo((self.set_start, [start]), (self.set_start, [self.start]))
        self.start = start
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()
        self.dispatch_on_changed(item=self)

    def set_end(self, end):
        self.project.undo_manager.to_undo((self.set_end, [end]), (self.set_end, [self.end]))
        self.end = end
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    def move(self, start, end):
        self.project.undo_manager.to_undo((self.move, [start, end]), (self.move, [self.start, self.end]))
        self.start = start
        self.end = end
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return str(self.additional_identifiers[0])

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]), (self.set_name, [self.additional_identifiers[0]]))
        self.additional_identifiers[0] = name
        self.dispatch_on_changed(item=self)

    def set_annotation_body(self, annotation):
        self.project.undo_manager.to_undo((self.set_annotation_body, [annotation]), (self.set_annotation_body, [self.annotation_body]))
        self.annotation_body = annotation
        self.dispatch_on_changed(item=self)

    def get_annotation_body(self):
        return self.annotation_body
    def set_additional_identifiers(self, additional):
        self.additional_identifiers = additional
        self.dispatch_on_changed(item=self)

    def serialize(self):
        words = []
        for w in self.voc_list:
            words.append(w.unique_id)

        r = dict(
             scene_id = self.ID,
             unique_id = self.unique_id,
             start = self.start,
             end = self.end,
             duration = self.duration,
             additional_identifiers = self.additional_identifiers,
            annotation_body = self.annotation_body,
            notes = self.notes,
            locked = self.locked,
            words = words
        )
        return r

    def deserialize(self, serialization, project):
        self.project = project
        self.ID = serialization["scene_id"]
        self.unique_id = serialization['unique_id']
        self.start = serialization["start"]
        self.end = serialization["end"]
        self.duration = serialization["duration"]
        self.additional_identifiers = serialization["additional_identifiers"]
        self.notes = serialization['notes']

        try:
            self.locked = serialization['locked']
        except:
            self.locked = False

        try:
            self.annotation_body = serialization['annotation_body']
        except:
            self.annotation_body = ""

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        return self

    def get_type(self):
        return SEGMENT

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def delete(self):
        self.segmentation.remove_segment(self)


#endregion

#region Annotation
# class AnnotationType(Enum):
#     Rectangle = 0
#     Ellipse = 1
#     Line = 2
#     Text = 3
#     Image = 4
#     FreeHand = 5
#

class Annotation(IProjectContainer, ITimeRange, IHasName, ISelectable, ILockable):
    def __init__(self, a_type = None, size = None, color = (255,255,255), orig_position = (50,50), t_start = 0, t_end = -1,
                 name = "New Annotation", text = "" , line_w = 2 ,font_size = 10, resource_path = "", tracking="Static"):
        IProjectContainer.__init__(self)
        self.name = name
        self.a_type = a_type
        self.t_start = t_start
        self.size = size
        self.curr_size = size
        self.color = color
        self.orig_position = orig_position
        self.line_w = line_w
        self.resource_path = resource_path
        self.text = text
        self.font_size = font_size
        self.font = None
        self.has_key = False
        self.keys = []
        self.free_hand_paths = []
        self.notes = ""

        self.tracking = tracking

        self.annotation_layer = None

        self.widget = None
        self.image = None


        # if t_end is not set, it shall be one second after t_start
        if t_end is -1:
            self.t_end = t_start + 1000
        else:
            self.t_end = t_end

        if self.a_type == AnnotationType.Image and self.resource_path is not "":
            self.load_image()

    def add_key(self, time, position):
        self.has_key = True
        self.keys.append([time, position])
        self.keys = sorted(self.keys, key=lambda x: x[0])
        self.project.undo_manager.to_undo((self.add_key, [time, position]), (self.remove_key, [time]))
        self.project.dispatch_changed()

    def remove_key(self, time):
        for k in self.keys:
            if k[0] == time:
                self.keys.remove(k)
                return
        if len(self.keys) == 0:
            self.has_key = False
        self.dispatch_on_changed()

    def remove_keys(self):
        self.keys = []
        self.dispatch_on_changed()

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]), (self.set_name, [self.name]))
        self.name = name
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return self.name

    def set_start(self, start):
        self.project.undo_manager.to_undo((self.set_start, [start]), (self.set_start, [self.t_start]))
        self.start = start
        self.dispatch_on_changed(item=self)

    def set_end(self, end):
        self.project.undo_manager.to_undo((self.set_end, [end]), (self.set_end, [self.t_end]))
        self.t_end = end
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return self.t_start

    def get_end(self):
        return self.t_end

    def move(self, start, end):
        self.project.undo_manager.to_undo((self.move, [start, end]), (self.move, [self.t_start, self.t_end]))
        self.t_start = start
        self.t_end = end
        self.dispatch_on_changed(item=self)

    def set_color(self, color):
        self.project.undo_manager.to_undo((self.set_color, [color]), (self.set_color, [self.color]))
        self.color = color
        self.dispatch_on_changed(item=self)

    def set_line_width(self, width):
        self.project.undo_manager.to_undo((self.set_line_width, [width]), (self.set_line_width, [self.line_w]))
        self.line_w = width
        self.dispatch_on_changed(item=self)

    def set_font_size(self, size):
        self.project.undo_manager.to_undo((self.set_font_size, [size]), (self.set_font_size, [self.font_size]))
        self.font_size = size
        self.dispatch_on_changed(item=self)

    def set_font(self, font_family):
        self.project.undo_manager.to_undo((self.set_font, [font_family]), (self.set_font, [self.font]))
        self.font = font_family
        self.dispatch_on_changed(item=self)

    def set_position(self, qpoint):
        self.project.undo_manager.to_undo((self.set_position, [qpoint]),
                                          (self.set_position, [QtCore.QPoint(self.orig_position[0], self.orig_position[1])]))
        self.orig_position = (qpoint.x(), qpoint.y())
        # self.dispatch_on_changed()

    def get_position(self):
        return QtCore.QPoint(self.orig_position[0],self.orig_position[1])

    def transform(self, size, position, old_pos, old_size):

        self.project.undo_manager.to_undo((self.transform, [size, position, old_pos, old_size]),
                                          (self.transform, [old_size, old_pos, position, size]))
        self.orig_position = position
        self.size = size
        # self.dispatch_on_changed(self.project.main_window.drawing_overlay)

    def set_size(self, width, height):
        self.project.undo_manager.to_undo((self.set_size, [width, height]),
                                          (self.set_size, [self.size[0], self.size[1]]))
        self.size = (width, height)
        # self.dispatch_on_changed()

    def get_size(self):
        return self.size

    def get_text(self):
        if self.a_type == AnnotationType.Text:
            return self.text
        else:
            print("get_text() called on non-text annotation")
            return self.text

    def set_text(self, text):
        self.project.undo_manager.to_undo((self.set_text, [text]),
                                          (self.set_text, [self.text]))
        self.text = text
        self.dispatch_on_changed(item=self)

    def get_color(self):
        return QtGui.QColor(self.color[0], self.color[1], self.color[1])

    def add_path(self, path, color, width):
        self.free_hand_paths.append([path, color, width])

        self.project.undo_manager.to_undo((self.add_path, [path, color, width]),
                                          (self.remove_path, [[path, color, width]]))
        self.widget.update_paths()

    def remove_path(self, path):
        to_remove = None
        for p in self.free_hand_paths:
            if p[0] == path[0]:
                to_remove = p
                break
        self.free_hand_paths.remove(to_remove)
        self.project.undo_manager.to_undo((self.remove_path, [to_remove]),
                                          (self.add_path, [[to_remove]]))
        self.widget.update_paths()

    def serialize(self):
        words = []


        for w in self.voc_list:
            if w is not None:
                words.append(w.unique_id)
            else:
                self.voc_list.remove(w)

        result = dict(
            name = self.name,
            unique_id=self.unique_id,
            a_type = self.a_type.value,
            t_start = self.t_start,
            size = self.size,
            curr_size = self.size,
            color = self.color,
            orig_position = self.orig_position,
            line_w = self.line_w,
            text = self.text,
            font_size = self.font_size,
            widget = None,
            keys = self.keys,
            resource_path = self.resource_path,
            free_hand_paths = self.free_hand_paths,
            notes = self.notes,
            words=words,
            tracking = self.tracking


        )
        return result

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.a_type = AnnotationType(serialization['a_type'])
        self.t_start = serialization['t_start']
        self.size = serialization['size']
        self.curr_size = serialization['curr_size']
        self.color = serialization['color']
        self.orig_position = serialization['orig_position']
        self.line_w = serialization['line_w']

        self.text = serialization['text']
        self.font_size = serialization['font_size']
        self.keys = serialization['keys']
        self.resource_path = serialization['resource_path']
        self.free_hand_paths = serialization['free_hand_paths']
        self.notes = serialization['notes']

        try:
            self.tracking = serialization['tracking']
        except:
            self.tracking = "Static"

        try:
            self.locked = serialization['locked']
        except:
            self.locked = False

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        if len(self.keys)>0:
            self.has_key = True
        self.widget = None

        if self.a_type is AnnotationType.Image:
            self.load_image()


        return self

    def get_type(self):
        return ANNOTATION

    def load_image(self):
        img = cv2.imread(self.resource_path, -1)
        if img is not None:
            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            qimage, qpixmap = numpy_to_qt_image(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True)
            self.image = qimage

    def delete(self):
        self.annotation_layer.remove_annotation(self)


class AnnotationLayer(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable):
    def __init__(self, name = None, t_start = None, t_end = None):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)

        self.name = name
        self.t_start = t_start
        self.t_end = t_end
        self.annotations = []
        self.is_current_layer = False
        self.is_visible = False
        self.timeline_visibility = True
        self.notes = ""

    def set_name(self, name):
        self.name = name
        self.project.undo_manager.to_undo((self.set_name, [name]),
                                          (self.set_name, [self.name]))
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return self.name

    def set_start(self, start):
        self.project.undo_manager.to_undo((self.set_start, [start]),
                                          (self.set_start, [self.t_start]))
        self.t_start = start
        self.dispatch_on_changed(item=self)

    def set_end(self, end):
        self.project.undo_manager.to_undo((self.set_end, [end]),
                                          (self.set_start, [self.t_end]))
        self.t_end = end
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return self.t_start

    def get_end(self):
        return self.t_end

    def move(self, start, end):
        self.project.undo_manager.to_undo((self.move, [start, end]), (self.move, [self.t_start, self.t_end]))
        self.t_start = start
        self.t_end = end
        self.dispatch_on_changed(item=self)

    def create_annotation(self, type = AnnotationType.Rectangle, position = (150,150), size=(100,100), color = (255,255,255), line_width = 5, name = "New Annotation") :
        annotation = Annotation(type, size = size, color=color, line_w=line_width, name=name,
                                orig_position=position)
        self.add_annotation(annotation)
        annotation.set_project(self.project)
        return annotation

    def add_annotation(self, annotation):
        self.annotations.append(annotation)
        annotation.annotation_layer = self
        self.project.undo_manager.to_undo((self.add_annotation, [annotation]),
                                          (self.remove_annotation, [annotation]))
        self.dispatch_on_changed()

    def remove_annotation(self, annotation):
        if annotation in self.annotations:
            annotation.widget.close()
            self.annotations.remove(annotation)
            self.project.undo_manager.to_undo((self.remove_annotation, [annotation]),
                                              (self.add_annotation, [annotation]))
            self.dispatch_on_changed()

    def set_is_current_layer(self, bool):
        self.is_current_layer = bool

    def serialize(self):
        s_annotations = []
        for a in self.annotations:
            s_annotations.append(a.serialize())

        words = []
        for w in self.voc_list:
            words.append(w.unique_id)

        result = dict(
            name = self.name,
            unique_id=self.unique_id,
            t_start = self.t_start,
            t_end = self.t_end,
            is_current_layer = self.is_current_layer,
            annotations = s_annotations,
            notes = self.notes,
            locked=self.locked,
            words=words
        )
        return result

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.t_start = serialization['t_start']
        self.t_end = serialization['t_end']
        self.is_current_layer = serialization['is_current_layer']
        self.notes = serialization['notes']

        try:
            self.locked = serialization['locked']
        except:
            self.locked = False

        for a in serialization['annotations']:
            new = Annotation()
            new.deserialize(a, self.project)
            new.annotation_layer = self
            self.annotations.append(new)

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        return self

    def get_type(self):
        return ANNOTATION_LAYER

    def lock(self):
        ILockable.lock(self)
        self.dispatch_on_changed(item=self)

    def unlock(self):
        ILockable.unlock(self)
        self.dispatch_on_changed(item=self)

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def set_project(self, project):
        IProjectContainer.set_project(self, project)
        for a in self.annotations:
            a.set_project(project)
#endregion

#region Screenshots

class Screenshot(IProjectContainer, IHasName, ITimeRange, ISelectable, ITimelineItem):
    def __init__(self, title = "", image = None,
                 img_blend = None, timestamp = "", scene_id = 0, frame_pos = 0,
                 shot_id_global = -1, shot_id_segm = -1, annotation_item_ids = None):
        IProjectContainer.__init__(self)
        self.title = title
        self.img_movie = image
        self.img_blend = img_blend
        self.annotation_item_ids = annotation_item_ids
        self.frame_pos = frame_pos
        self.scene_id = scene_id
        self.shot_id_global = shot_id_global
        self.shot_id_segm = shot_id_segm
        self.movie_timestamp = timestamp
        self.creation_timestamp = str(datetime.datetime.now())
        self.screenshot_group = ""
        self.notes = ""
        self.annotation_is_visible = False
        self.timeline_visibility = True


    def to_stream(self, project = None):
        obj = dict(
            img_movie = self.img_movie,
            img_blend=self.img_blend,
        )

        if project is None:
            project = self.project
        project.streamer.to_stream(self.unique_id, obj)

    def from_stream(self, project = None):
        if project is None:
            project = self.project
        obj = project.streamer.from_stream(self.unique_id)
        self.img_movie = obj['img_movie']
        self.img_blend = obj['img_blend']

    def set_title(self, title):
        self.title = title
        self.dispatch_on_changed(item=self)

    def set_scene_id(self, scene_id):
        self.scene_id = scene_id

    def set_shot_id_global(self, global_id):
        self.shot_id_global = global_id

    def set_shot_id_segm(self, segm_id):
        self.shot_id_segm = segm_id

    def set_notes(self, notes):
        self.notes = notes
        self.project.undo_manager.to_undo((self.set_notes, [notes]),
                                          (self.set_notes, [self.notes]))
        # self.dispatch_on_changed(item=self)

    def set_annotation_visibility(self, visibility):
        self.annotation_is_visible = visibility

    def get_start(self):
        return self.movie_timestamp

    def get_end(self):
        return self.movie_timestamp

    def get_name(self):
        return self.title

    def resize(self, scale = 1.0):
        streamed = self.project.streamer.from_stream(self.unique_id)
        self.img_movie =  cv2.resize(streamed['img_movie'], None, None, scale, scale, cv2.INTER_CUBIC)

        try:
            self.img_blend =  cv2.resize(streamed['img_blend'], None, None, scale, scale, cv2.INTER_CUBIC)
        except:
            self.img_blend = np.zeros_like(self.img_movie)

    def get_preview(self, scale = 0.2):
        return cv2.resize(self.img_movie, None,None, scale, scale, cv2.INTER_CUBIC)

    def set_name(self, name):
        self.title = name
        self.project.undo_manager.to_undo((self.set_title, [name]),
                                          (self.set_title, [self.title]))
        self.dispatch_on_changed(item=self)

    def update_scene_id(self, segmentation):
        segment = segmentation.get_segment(self.movie_timestamp)
        if segment is not None:
            self.scene_id = segment.ID

    def serialize(self):

        words = []
        for w in self.voc_list:
            words.append(w.unique_id)

        result = dict(
            title = self.title,
            unique_id=self.unique_id,
            annotation_item_ids = self.annotation_item_ids,
            frame_pos = self.frame_pos,
            scene_id = self.scene_id,
            shot_id_global = self.shot_id_global,
            shot_id_segm = self.shot_id_segm,
            movie_timestamp = self.movie_timestamp,
            creation_timestamp = self.creation_timestamp,
            notes = self.notes,
            words=words
        )


        images = [self.img_movie.astype(np.uint8)]

        return result, images

    def deserialize(self, serialization, project):
        self.project = project
        self.title = serialization['title']
        self.unique_id = serialization['unique_id']
        self.scene_id = serialization['scene_id']
        self.movie_timestamp = serialization['movie_timestamp']
        self.creation_timestamp = serialization['creation_timestamp']
        self.annotation_item_ids = serialization['annotation_item_ids']

        self.notes = serialization['notes']
        self.shot_id_segm = serialization['shot_id_segm']
        self.shot_id_global = serialization['shot_id_global']
        self.frame_pos = serialization['frame_pos']

        #
        self.img_movie = np.zeros(shape=(30,50,3), dtype=np.uint8)
        self.img_blend = None

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        return self

    def get_type(self):
        return SCREENSHOT

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def delete(self):
        self.project.remove_screenshot(self)


class ScreenshotGroup(IProjectContainer, IHasName, ISelectable):
    def __init__(self, project, name = "New Screenshot Group"):
        IProjectContainer.__init__(self)
        self.set_project(project)
        self.name = name
        self.screenshots = []
        self.notes = ""
        self.is_current = False

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        for s in self.screenshots:
            s.screenshot_group = self.name
        self.dispatch_on_changed()

    def add_screenshots(self, shots):
        if not isinstance(shots, list):
            shots = [shots]
        for s in shots:
            self.screenshots.append(s)
            s.screenshot_group = self.get_name()

    def remove_screenshots(self, shots):
        if not isinstance(shots, list):
            shots = [shots]
        for s in shots:
            if s in self.screenshots:
                self.screenshots.remove(s)

    def get_type(self):
        return SCREENSHOT_GROUP

    def serialize(self):
        shot_ids = []
        for s in self.screenshots:
            shot_ids.append(s.get_id())

        words = []
        for w in self.voc_list:
            words.append(w.unique_id)


        data = dict(
            name=self.name,
            shots = shot_ids,
            words=words
        )
        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']

        for s in serialization['shots']:
            shot = self.project.get_by_id(s)
            shot.screenshot_group = self.name
            self.screenshots.append(shot)

        try:
            for w in serialization["words"]:
                word = self.project.get_by_id(w)
                if word is not None:
                    self.add_word(self.project.get_by_id(w))

        except Exception as e:
            pass

        return self

#endregion

#region NodeScripts

class NodeScript(IProjectContainer, IHasName, ISelectable):
    def __init__(self, name = ""):
        IProjectContainer.__init__(self)
        self.name = name
        self.notes = ""
        self.nodes = []
        self.connections = []

    def create_node(self, operation, pos, unique_id = -1):
        new = NodeDescriptor(operation, pos, unique_id)
        new.set_project(self.project)
        self.add_node(new)
        return new

    def add_node(self, node):
        self.nodes.append(node)
        self.dispatch_on_changed()

    def remove_node(self, node, dispatch = True):
        if node in self.nodes:
            self.nodes.remove(node)
            self.project.remove_from_id_list(node)

            if dispatch:
                self.dispatch_on_changed()
            print("Removed")
        else:
            print("Not Found")

    def create_connection(self, connection, unique_id = -1):
        new = ConnectionDescriptor(connection.input_field, connection.output_field,
                                   connection.input_field.field_id, connection.output_field.field_id)

        new.unique_id = unique_id
        new.set_project(self.project)
        self.connections.append(new)
        return new

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)
            self.project.remove_from_id_list(connection)

    def clear(self):
        for c in self.connections:
            self.connections.remove(c)
        for n in self.nodes:
            self.nodes.remove(n)

    #region IProjectContainer
    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.project.dispatch_changed(item=self)

    def get_type(self):
        return NODE_SCRIPT

    def serialize(self):
        nodes = []
        connections = []

        for n in self.nodes:
            nodes.append(n.serialize())

        for c in self.connections:
            connections.append(c.serialize())

        data = dict(
            name = self.name,
            unique_id = self.unique_id,
            nodes=nodes,
            connections=connections,
            notes = self.notes
        )

        return data

    def deserialize(self, serialization, project):
        self.project = project
        nodes = serialization['nodes']
        connections = serialization['connections']

        # node_editor = self.project.main_window.node_editor_dock.node_editor
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        for n in nodes:
            node = NodeDescriptor().deserialize(n, self.project)
            node.set_project(self.project)
            self.add_node(node)
            # pos = QPoint(n['pos'][0] * node_editor.scale, n['pos'][1] * node_editor.scale)
            # node.scale(node_editor.scale)
            # node.node_pos = pos

            # node.move(pos)

        for c in connections:
            conn = ConnectionDescriptor().deserialize(c, self.project)
            conn.set_project(self.project)
            self.add_connection(conn)

        return self


class NodeDescriptor(IProjectContainer, IHasName, ISelectable):
    def __init__(self, operation = None, pos = (0, 0), unique_id = -1):
        IProjectContainer.__init__(self)
        self.unique_id = unique_id
        self.node_size = (200,200)
        if isinstance(pos, tuple):
            self.node_pos = pos
        else:
            self.node_pos = (pos.x(), pos.y())
        self.operation = operation

        if operation is not None:
            self.name = operation.name

        self.node_widget = None

    def set_position(self, qpoint):
        self.node_pos = (qpoint.x(), qpoint.y())

    def set_size(self, qsize):
        self.node_size = (qsize.width(), qsize.height())

    def get_position(self):
        return QPoint(self.node_pos[0], self.node_pos[1])

    def get_size(self):
        return QSize(self.node_size[0], self.node_size[1])

    #region IProjectContainer
    def get_type(self):
        return NODE

    def get_name(self):
        return self.operation.name

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes

    #endregion
    def serialize(self):
        default_values = []
        for s in self.operation.input_slots:
            value = s.default_value
            if value is None:
                value = -1
            if isinstance(value, np.ndarray):
                value = value.tolist()
            default_values.append(value)


        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            node_pos = self.node_pos,
            node_size = self.node_size,
            default_values = default_values,
            operation = self.operation.__class__.__name__,
            notes=self.notes
        )

        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.node_pos = serialization['node_pos']
        self.node_size = serialization['node_size']
        self.notes = serialization['notes']

        self.operation = eval(serialization['operation'])()
        default_values = serialization['default_values']

        for i, s in enumerate(self.operation.input_slots):
            if default_values[i] == -1:
                s.default_value = None
            else:
                s.default_value = default_values[i]

        return self


class ConnectionDescriptor(IProjectContainer):
    def __init__(self, input_pin=None, output_pin=None, input_pin_id=None, output_pin_id=None):
        IProjectContainer.__init__(self)
        if input_pin is not None:
            self.input_node = input_pin.node.node_object.unique_id
        if output_pin is not None:
            self.output_node = output_pin.node.node_object.unique_id
        self.input_pin_id = input_pin_id
        self.output_pin_id = output_pin_id

    def serialize(self):
        data = dict(
            input_node = self.input_node,
            output_node=self.output_node,
            input_pin_id=self.input_pin_id,
            output_pin_id=self.output_pin_id
        )
        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.input_node = serialization['input_node']
        self.output_node = serialization['output_node']
        self.input_pin_id = serialization['input_pin_id']
        self.output_pin_id = serialization['output_pin_id']

        return self


#endregion

#region Analysis/MovieDescriptor
class MovieDescriptor(IProjectContainer, ISelectable, IHasName, ITimeRange):
    def __init__(self, project, movie_name="No Movie Name", movie_path="", movie_id=-0o001, year=1800, source="",
                 duration=100):
        IProjectContainer.__init__(self)
        self.set_project(project)
        self.movie_name = movie_name
        self.movie_path = movie_path
        self.movie_id = movie_id
        self.year = year
        self.source = source
        self.duration = duration
        self.notes = ""

    def serialize(self):
        data = dict(
            movie_name=self.movie_name,
            unique_id=self.unique_id,
            movie_path=self.movie_path,
            movie_id=self.movie_id,
            year=self.year,
            source=self.source,
            duration=self.duration,
            notes=self.notes,
        )
        return data

    def set_duration(self, duration):
        self.duration = duration
        self.dispatch_on_changed(item=self)

    def deserialize(self, serialization):
        for key, value in list(serialization.items()):
            setattr(self, key, value)
        return self

    def get_type(self):
        return MOVIE_DESCRIPTOR

    def get_name(self):
        return self.movie_name

    def set_name(self, name):
        self.movie_name = name
        self.project.undo_manager.to_undo((self.set_name, [name]),
                                          (self.set_name, [self.movie_name]))
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return 0

    def get_end(self):
        cap = cv2.VideoCapture(self.movie_path)
        return cap.get(cv2.CAP_PROP_FRAME_COUNT)


class Analysis(IProjectContainer, ITimeRange, IHasName, ISelectable):
    def __init__(self, name=None, t_start=None, t_end=None, data=None, procedure_id=None, target_id=None):
        IProjectContainer.__init__(self)
        self.name = name
        self.data = data
        self.visualizations = []
        self.procedure_id = procedure_id
        self.target_id = target_id
        self.notes = ""

    def get_target_item(self):
        return self.project.get_by_id(self.target_id)

    def add_visualization(self, visualization):
        self.visualizations.append(visualization)

    def get_type(self):
        return ANALYSIS

    def get_start(self):
        return self.time_range_item.get_start()

    def get_end(self):
        return self.time_range_item.get_start()

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]),
                                          (self.set_name, [self.name]))
        self.name = name
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return self.name

    def serialize(self):
        data_json = []
        for d in self.data:
            data_json.append(np.array(d).tolist())
        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            data=data_json,
            procedure_id=self.procedure_id,
            target_id=self.target_id,
            notes=self.notes
        )

        return data

    def deserialize(self, serialization):

        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.target_id = serialization['target_id']
        self.notes = serialization['notes']
        data = []
        for d in serialization['data']:
            data.append(np.array(d))
        self.data = data
        self.procedure_id = serialization['procedure_id']

        return self

    def delete(self):
        self.project.remove_analysis(self)

#endregion

#region Vocabulary
class Vocabulary(IProjectContainer, IHasName):
    def __init__(self, name):
        IProjectContainer.__init__(self)
        self.name = name
        self.words = []
        self.words_plain = []
        self.was_expanded = False


    def create_word(self, name, parent_word = None, unique_id = -1):
        word = VocabularyWord(name, vocabulary=self)
        word.unique_id = unique_id
        self.add_word(word, parent_word)
        return word

    def add_word(self, word, parent_word = None):
        if parent_word is None:
            word.parent = self
            self.words.append(word)
            self.words_plain.append(word)
            word.set_project(self.project)
        else:
            parent = self.get_word_by_name(parent_word)
            if parent is not None:
                word.parent=parent
                parent.add_children(word)
                self.words_plain.append(word)
                word.set_project(self.project)

        self.dispatch_on_changed(item=self)

    def remove_word(self, word):
        children = []
        word.get_children_plain(children)

        for itm in word.connected_items:
            itm.remove_word(word)

        for w in children:
            self.words_plain.remove(w)
            for itm in w.connected_items:
                itm.remove_word(w)

        if word in self.words:
            self.words.remove(word)
        else:
            if word in word.parent.children:
                word.parent.children.remove(word)

        if word in self.words_plain:
            self.words_plain.remove(word)

        self.dispatch_on_changed()

    def get_word_by_name(self, name):
        for w in self.words_plain:
            if w.name == name:
                return w
        return None

    def get_vocabulary_item_model(self):
        root = VocabularyItem(self.name, self)
        for w in self.words:
            w.get_children(root)
        return root

    def get_vocabulary_as_list(self):
        result = []
        for w in self.words:
            w.get_children_plain(result)
        return result

    def serialize(self):
        words = []
        for w in self.words:
            w.get_children_plain(words)

        words_data = []
        for w in words:
            data = dict(
                name = w.name,
                unique_id = w.unique_id,
                parent = w.parent.unique_id,
                children = [a.unique_id for a in w.children]
            )
            words_data.append(data)

        voc_data = dict(
            name = self.name,
            unique_id = self.unique_id,
            words = words_data
        )

        return voc_data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']

        for w in serialization['words']:
            parent = self.project.get_by_id(w['unique_id'])

            # If this is a root node in the Vocabulary
            if isinstance(parent, Vocabulary):
                self.create_word(w['name'], unique_id=w['unique_id'])

            else:
                self.create_word(w['name'], parent, unique_id=w['unique_id'])

        return self

    def get_type(self):
        return VOCABULARY


class VocabularyWord(IProjectContainer, IHasName):
    def __init__(self, name, vocabulary, parent = None, is_checkable = False):
        IProjectContainer.__init__(self)
        self.name = name
        self.vocabulary = vocabulary
        self.is_checkable = is_checkable
        self.was_expanded = False
        self.parent = parent
        self.children = []
        self.connected_items = []

    def add_connected_item(self, item):
        self.connected_items.append(item)

    def remove_connected_item(self, item):
        if item in self.connected_items:
            self.connected_items.remove(item)

    def add_children(self, children):
        print(self.name, [c.name for c in self.children])
        if isinstance(children, list):
            for c in children:
                self.children.append(c)
                c.parent = self
        else:
            self.children.append(children)

    def get_children(self, parent_item):

        item = VocabularyItem(self.name, self)
        parent_item.appendRow(item)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children(item)

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def get_type(self):
        return VOCABULARY_WORD

def get_default_vocabulary():
    voc = Vocabulary("Scene Locations")
    voc.create_word("House")
    voc.create_word("Kitchen", "House")
    voc.create_word("Bedroom", "House")
    voc.create_word("Toilet", "House")


    return voc
#endregion

pass