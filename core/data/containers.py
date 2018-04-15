import datetime
import json
import cv2
from shutil import copy2
import os
from random import randint
import shelve
from .computation import blend_transparent
import numpy as np
from core.data.interfaces import IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable
from core.data.undo_redo_manager import UndoRedoManager
from core.data.computation import *
from core.gui.vocabulary import VocabularyItem
from core.data.project_streaming import ProjectStreamer, NUMPY_NO_OVERWRITE
from core.data.enums import *

from core.data.project_streaming import IStreamableContainer

from core.node_editor.node_editor import *
from shutil import copy2
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


class VIANProject(IHasName, IHasVocabulary):
    def __init__(self, main_window, path = "", name = "", folder=""):
        IHasVocabulary.__init__(self)
        self.undo_manager = UndoRedoManager()
        self.main_window = main_window
        # self.streamer = main_window.project_streamer
        self.inhibit_dispatch = True

        self.path = path
        self.name = name
        self.folder = folder
        self.data_dir = ""
        self.results_dir = ""
        self.shots_dir = ""
        self.export_dir = ""

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
        # self.experiments = []

        self.current_script = None
        self.node_scripts = []
        self.create_script(dispatch=False)

        self.add_screenshot_group("All Shots", initial=True)
        self.active_screenshot_group = self.screenshot_groups[0]
        self.active_screenshot_group.is_current = True

        self.folder = path.split("/")[len(path.split("/")) - 1]
        self.notes = ""

        self.colormetry_analysis = None

        self.add_vocabulary(get_default_vocabulary())
        # self.create_default_experiment()

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

    def create_file_structure(self):
        root = self.folder

        self.data_dir = root + "/data"
        self.results_dir = root + "/results"
        self.shots_dir = root + "/shots"
        self.export_dir = root + "/export"

        if not os.path.isdir(self.data_dir):
            os.mkdir(self.data_dir)
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        if not os.path.isdir(self.shots_dir):
            os.mkdir(self.shots_dir)
        if not os.path.isdir(self.export_dir):
            os.mkdir(self.export_dir)

    def get_all_containers(self):
        result = []
        for itm in self.id_list:
            result.append(itm[1])
        return result

    def unload_all(self):
        for c in self.get_all_containers():
            if isinstance(c, IStreamableContainer):
                c.unload_container(sync=True)

    def print_all(self, type = None):
        for c in self.get_all_containers():
            if type is not None and type == c.get_type():
                print(str(c.unique_id).ljust(20), c)

    #region Segmentation
    def create_segmentation(self, name = None, dispatch = True):
        s = Segmentation(name)
        self.add_segmentation(s, dispatch)
        return s

    def add_segmentation(self, segmentation, dispatch=True):
        self.segmentation.append(segmentation)
        segmentation.set_project(self)

        if dispatch:
            self.undo_manager.to_undo((self.add_segmentation, [segmentation]), (self.remove_segmentation, [segmentation]))
            self.dispatch_changed()

    def copy_segmentation(self, segmentation):
        new = self.create_segmentation(name = segmentation.name + "_Copy")

        for s in segmentation.segments:
            segm = new.create_segment(start = s.get_start(), stop = s.get_end(), dispatch=False)
            segm.annotation_body = s.annotation_body

        print("Dispatching")
        self.undo_manager.to_undo((self.copy_segmentation, [segmentation]), (self.remove_segmentation, [new]))
        self.dispatch_changed(item = new)

    def remove_segmentation(self, segmentation):
        if self.segmentation[self.main_segmentation_index] is segmentation:
            main_segmentation = self.segmentation[0]
        else:
            main_segmentation = self.segmentation[self.main_segmentation_index]

        self.segmentation.remove(segmentation)
        # for exp in self.experiments:
        #     exp.clear_from_deleted_containers()
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

    def get_segment_of_main_segmentation(self, index):
        """
        Returns the segment of the Main Segmentation that is at index "index". 
        Be aware, that the segment_id == index + 1. Since Segment IDS are counted from 1
        :param index: 
        :return: 
        """
        try:
            return self.get_main_segmentation().segments[index]
        except:
            return None
    # endregion

    # region Screenshots
    def create_screenshot(self, name, image, time_ms):
        new = Screenshot(name,image,timestamp=time_ms)
        self.add_screenshot(new)

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

        return grp

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
    def create_node_analysis(self, name, result, script_id, final_node_ids):
        analysis = NodeScriptAnalysis(name, result, script_id, final_node_ids)
        self.add_analysis(analysis)
        return analysis

    def add_analysis(self, analysis):
        analysis.set_project(self)
        self.analysis.append(analysis)
        self.undo_manager.to_undo((self.add_analysis, [analysis]), (self.remove_analysis, [analysis]))
        self.dispatch_changed()

    def remove_analysis(self, analysis):
        self.analysis.remove(analysis)
        self.undo_manager.to_undo((self.remove_analysis, [analysis]), (self.add_analysis, [analysis]))
        self.dispatch_changed()

    def get_analyzes_of_item(self, item):
        result = []
        for a in self.analysis:
            if isinstance(a, IAnalysisJobAnalysis) and item.unique_id in a.parameters.target_items:
                result.append(item)
        return item

    def get_job_analyses(self):
        result = []
        for a in self.analysis:
            if isinstance(a, IAnalysisJobAnalysis):
                result.append(a)
        return result

    def has_analysis(self, class_name):
        for a in self.analysis:
            if isinstance(a, IAnalysisJobAnalysis):
                if a.analysis_job_class == class_name:
                    return True
        return False

    def get_colormetry(self):
        if self.colormetry_analysis is None:
            return False, None
        else:
            return self.colormetry_analysis.has_finished, self.colormetry_analysis

    def create_colormetry(self):
        colormetry = ColormetryAnalysis()
        self.add_analysis(colormetry)
        self.colormetry_analysis = colormetry
        return colormetry

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
            self.remove_from_id_list(script)
        self.dispatch_changed()

    def set_current_script(self, script, dispatch = True):
        self.current_script = script

        if dispatch:
            self.dispatch_changed()
    #endregion

    #region IO
    def store_project(self, settings, path = None):
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
            results_dir = self.results_dir,
            export_dir=self.export_dir,
            shots_dir=self.shots_dir,
            data_dir=self.data_dir,
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

        # remove the default Experiment

        # self.remove_experiment(self.experiments[0])


        self.path = my_dict['path']
        self.path = path
        self.name = my_dict['name']
        self.main_segmentation_index = my_dict['main_segmentation_index']

        try:
            self.notes = my_dict['notes']
        except:
            self.notes = ""

        splitted = path.split("/")[0:len(path.split("/")) - 1]
        self.folder = ""
        for f in splitted:
            self.folder += f + "/"

        self.results_dir = self.folder + "/results"
        self.export_dir = self.folder + "/export"
        self.shots_dir = self.folder + "/shots"
        self.data_dir = self.folder + "/data"

        self.main_window.numpy_data_manager.project = self


        move_project_to_directory_project = False
        try:
            version = my_dict['version']
            version = version.split(".")
            print("Loaded Project Version:", version)

            # We know that versions before 0.2.10 have no folder structure
            if version_check([0,2,10], version):
                move_project_to_directory_project = True

            # If the Root folder does not exist, something is very odd, we need to recreate the project
            elif not os.path.isdir(self.folder):
                move_project_to_directory_project = True

        except Exception as e:
            print("Exception occured during loading:", str(e))
            move_project_to_directory_project = True

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

        for i, b in enumerate(my_dict['screenshots']):
            new = Screenshot().deserialize(b, self)
            self.add_screenshot(new)

        for c in my_dict['segmentation']:
            new = Segmentation().deserialize(c, self)
            self.add_segmentation(new)

        for d in my_dict['analyzes']:
            if d is not None:
                new = eval(d['analysis_container_class'])().deserialize(d, self.main_window.numpy_data_manager)
                self.add_analysis(new)
                if isinstance(new, ColormetryAnalysis):
                    self.colormetry_analysis = new


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


        # Finalizing the Project, Hooking up the ID Connections
        # Connecting the NodeScriptAnalysis Objects to their Final Nodes
        for a in self.analysis:
            if isinstance(a, NodeScriptAnalysis):
                for i, res in enumerate(a.data):
                    node = self.get_by_id(a.final_node_ids[i])
                    if node is not None:
                        node.operation.result = res

        # try:
        #     for g in my_dict['experiments']:
        #         new = Experiment().deserialize(g, self)
        #         # self.add_experiment(new)
        # except Exception as e:
        #     # raise e
        #     print(e)

        # Migrating the Project to the new FileSystem
        if move_project_to_directory_project:
            answer = QMessageBox.question(self.main_window, "Project Migration", "This Project seems to be older than 0.2.9.\n\n"
                                                            "VIAN uses a directory System since 0.2.10,\n "
                                                            "do you want to move the Project to the new System now?")
            if answer == QMessageBox.Yes:
                try:
                    old_path = self.path

                    folder = QFileDialog.getExistingDirectory()
                    self.folder = folder + "/" + self.name
                    self.path = self.folder + "/" + self.name
                    os.mkdir(self.folder)
                    self.create_file_structure()
                    copy2(old_path, self.path + settings.PROJECT_FILE_EXTENSION)

                except Exception as e:
                    print(e)
        # Check the FileStructure integrity anyway
        else:
            self.create_file_structure()

        self.sort_screenshots()
        self.undo_manager.clear()

    def get_template(self, segm, voc, ann, scripts): #, experiment, experiment_exporter):
        segmentations = []
        vocabularies = []
        layers = []
        node_scripts = []
        experiments = []
        if segm:
            for s in self.segmentation:
                segmentations.append([s.get_name(), s.unique_id])
        if voc:
            for v in self.vocabularies:
                vocabularies.append(v.serialize())
        if ann:
            for l in self.annotation_layers:
                layers.append([l.get_name(), l.get_start(), l.get_end(), l.unique_id])
        if scripts:
            for n in self.node_scripts:
                node_scripts.append(n.serialize())

        # if experiment:
        #     for e in self.experiments:
        #         experiments.append(experiment_exporter.export(None, e, return_dict = True))

        template = dict(
            segmentations = segmentations,
            vocabularies = vocabularies,
            layers = layers,
            node_scripts=node_scripts,
            # experiments = experiments

        )
        return template

    def apply_template(self, template_path, experiment_importer):

        try:
            with open(template_path, "r") as f:
                template = json.load(f)
        except:
            print("Importing Template Failed")
            return

        for s in template['segmentations']:
            new = Segmentation(s[0])
            new.unique_id = s[1]
            self.add_segmentation(new, False)

        for v in template['vocabularies']:
            voc = Vocabulary("voc").deserialize(v, self)
            self.add_vocabulary(voc)

        for l in template['layers']:
            self.create_annotation_layer(l[0], int(l[1]), int(l[2]))

        for n in template['node_scripts']:
            new = NodeScript().deserialize(n, self)
            self.add_script(new)

        for e in template['experiments']:
            experiment_importer.import_experiment(None, self, e)


    #endregion

    #region Vocabularies
    def create_vocabulary(self, name="New Vocabulary"):
        voc = Vocabulary(name)
        self.add_vocabulary(voc)
        return voc

    def add_vocabulary(self, voc, dispatch = True):
        not_ok = True
        counter = 0
        name = voc.name
        duplicate = None
        while(not_ok):
            has_duplicate = False
            for v in self.vocabularies:
                if v.name == name and v.derived_vocabulary == False:
                    name = voc.name + "_" + str(counter).zfill(2)
                    has_duplicate = True
                    counter += 1
                    duplicate = v
                    break
            if not has_duplicate:
                not_ok = False
                break
            else:
                # If the Vocabulares are duplicates, we might want to replace the IDS in the Caller,
                # Therefore we create a replacement table
                x = [w.name for w in voc.words_plain]
                y = [w.name for w in duplicate.words_plain]

                if set(x) == set(y):
                    print("RETURN")
                    return duplicate

        voc.name = name
        voc.set_project(self)

        self.vocabularies.append(voc)

        if dispatch:
            self.dispatch_changed()

        return voc

    def remove_vocabulary(self, voc):
        if voc in self.vocabularies:
            self.vocabularies.remove(voc)
            self.remove_from_id_list(voc)
        self.dispatch_changed()

    def copy_vocabulary(self, voc, add_to_global = True):
        """
        Copies an existing Vocabulary
        :param voc: the Vocabulary to copy
        :param add_to_global: If True, the Copied Vocabualry is added to the Projects List
        :return: A Copy of an existing Vocabulary
        """
        self.inhibit_dispatch = True
        voc.export_vocabulary(self.data_dir + "/temp_voc.json")
        new = self.import_vocabulary(self.data_dir + "/temp_voc.json", add_to_global)
        os.remove(self.data_dir + "/temp_voc.json")
        self.inhibit_dispatch = False
        return new

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

    def get_word_object_from_name(self, name, experiment = None):
        if experiment is not None:
            vocabularies = experiment.get_vocabulary_list()
        else:
            vocabularies = self.vocabularies

        for v in vocabularies:
            for w in v.words_plain:
                if w.name == name:
                    return w

    def import_vocabulary(self, path, add_to_global = True, serialization = None, return_id_table = False):
        """
        Importing a Vocabulary from json
        :param path: Path to the Vocabulary Json
        :param add_to_global: if True, the Vocabulary is added to the Projects Vocabulary List
        :return: An imported Vocabulary Object
        """
        new_voc, id_table = Vocabulary("New").import_vocabulary(path, self, serialization)
        if add_to_global:
            self.add_vocabulary(new_voc)

        if return_id_table:
            return new_voc, id_table
        else:
            return new_voc

    #endregion

    #region Experiments
    # def create_experiment(self, dispatch = True):
    #     new = Experiment()
    #     self.add_experiment(new, dispatch)
    #     return new
    #
    # def add_experiment(self, experiment, dispatch = True):
    #     experiment.set_project(self)
    #     self.experiments.append(experiment)
    #
    #     self.undo_manager.to_undo((self.add_experiment, [experiment]),
    #                               (self.remove_experiment, [experiment]))
    #
    #     if dispatch:
    #         self.dispatch_changed(item=experiment)
    #
    # def remove_experiment(self, experiment):
    #     if experiment in self.experiments:
    #         self.experiments.remove(experiment)
    #         self.remove_from_id_list(experiment)
    #         self.undo_manager.to_undo((self.remove_experiment, [experiment]),
    #                                   (self.add_experiment, [experiment]))
    #         self.dispatch_changed()
    #
    # def create_default_experiment(self):
    #     default = self.create_experiment()
    #     default.set_name("Default Experiment")
    #     default.create_class_object("Global")

    #endregion

    #region MediaObjects
    def create_media_object(self, name ,data, container: IHasMediaObject):
        if ".pdf" in data:
            o_type = MediaObjectType.PDF
        elif ".png" in data or ".jpg" in data:
            o_type = MediaObjectType.IMAGE
        else:
            o_type = MediaObjectType.EXTERNAL

        if o_type in [MediaObjectType.HYPERLINK, MediaObjectType.SOURCE]:
            new = DataMediaObject(name, data, container, o_type)

        else:
            fdir, fname = os.path.split(data)
            is_file = True
            counter = 0
            while(is_file):
                fdir, fname = os.path.split(data)
                new_path = self.data_dir + "/" + str(counter) + "_" + fname
                if not os.path.isfile(new_path):
                    is_file = False

            copy2(data, new_path)
            new = FileMediaObject(fname, new_path, container, o_type)

        self.add_media_object(new, container)


    def add_media_object(self, media_object, container:IHasMediaObject, dispatch = True):
        media_object.set_project(self)
        container.add_media_object(media_object)
        self.dispatch_changed(item = container)

    #endregion

    # region Setters/Getters
    def cleanup(self):
        self.main_window.numpy_data_manager.clean_up([f[0] for f in self.id_list])
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

    def clean_id_list(self):
        for itm in self.id_list:
            if itm[0] != itm[1].unique_id:
                self.id_list.remove(itm)
                print(itm, " removed from ID-List")

    def replace_ids(self):
        for itm in self.id_list:
            if itm[0] != itm[1].unique_id:
                old = itm[0]
                itm[0] = itm[1].unique_id
                print("Updated ", old, " --> ", itm[1].unique_id, itm[1])

    def get_object_list(self):
        string = ""
        for ids in self.id_list:
            string += str(ids[0]).ljust(20) + str(ids[1]) + "\n"
        return string

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
class Segmentation(IProjectContainer, IHasName, ISelectable, ITimelineItem, ILockable, AutomatedTextSource, IHasVocabulary):
    def __init__(self, name = None, segments = None):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IHasVocabulary.__init__(self)
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

    def get_segment_of_time(self, time_ms):
        for s in self.segments:
            if s.get_start() <= time_ms < s.get_end():
                return s
        return None

    def create_segment(self, start, stop, ID = None, from_last_threshold = 100, forward_segmenting = False,
                       inhibit_overlap = True,  dispatch = True, annotation_body = ""):


        # Are we fast segmenting?
        if stop - start < from_last_threshold:

            # Forward Segmentation: Create a Segment from Position to next Segment or End
            # If the new overlaps with the last: shorten the last
            if forward_segmenting:
                # Find the next Segment if there is one and create a segment from start to the next segment start
                next = None
                last = None
                for s in self.segments:
                    if s.start < start:
                        last = s
                    if s.start > start and next is None:
                        next = s
                    if last is not None and next is not None:
                        break

                if next is None:
                    stop = self.project.movie_descriptor.duration
                else:
                    stop = next.get_start() - 1

                if last is not None and last.end > start:
                    last.set_end(start - 1)

            # Backwards Segmentation: Create a Segment from the Last to current Position
            else:
                last = None
                for i, s in enumerate(self.segments):
                    if s.start < start:
                        last = s
                if last is not None:
                    start = last.end
                else:
                    start = 0

        if inhibit_overlap:
            last = None
            next = None

            for i, s in enumerate(self.segments):
                if s.start < start:
                    last = s
                    if len(self.segments) > i + 1:
                        next = self.segments[i + 1]
                    else:
                        next = None

            if last is not None and last.end > start:
                start = last.end
            if next is not None and next.start < stop:
                stop = next.start - 1

        if ID is None:
            ID = len(self.segments) + 1

        # IF the Segment is to small, we don't want to create it
        if start > stop - 100:
            return

        # if the Segment does still overlap, we don't want to create it
        last = None
        next = None
        for i, s in enumerate(self.segments):
            if s.start < start:
                last = s
                if len(self.segments) > i + 1:
                    next = self.segments[i + 1]
                else:
                    next = None

        if last is not None and last.end > start:
            return
        if next is not None and next.start < stop:
            return

        new_seg = Segment(ID = ID, start = start, end = stop, name=str(ID),
                          segmentation = self, annotation_body=annotation_body)
        new_seg.set_project(self.project)

        self.add_segment(new_seg, dispatch)

        return new_seg

    def add_segment(self, segment, dispatch = True):
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

        if dispatch:
            self.project.undo_manager.to_undo((self.add_segment, [segment]), (self.remove_segment, [segment]))
            self.dispatch_on_changed()

    def remove_segment(self, segment, dispatch = True):
        self.segments.remove(segment)

        self.update_segment_ids()
        self.project.sort_screenshots()
        if dispatch:
            self.project.undo_manager.to_undo((self.remove_segment, [segment]), (self.add_segment, [segment]))
            self.dispatch_on_changed()

    def cut_segment(self, segm, time):
        if segm in self.segments:
            old_end = segm.get_end()
            segm.end = time
            new = self.create_segment(time, old_end)
            self.project.undo_manager.to_undo((self.cut_segment, [segm, time]), (self.merge_segments, [segm, new]))

    def merge_segments(self, a, b):
        if abs(a.ID - b.ID) <= 1:
            if a.ID < b.ID:
                start = a.get_start()
                end = b.get_end()
                # self.remove_segment(b, dispatch=False)
                # a.end = int(b.get_end())
                cut_t = b.get_start()
                # segm = a
            else:
                start = b.get_start()
                end = a.get_end()
                # self.remove_segment(a, dispatch=False)
                # b.end = int(a.get_end())
                cut_t = b.get_start()
                # segm = b

            media_objects = a.media_objects
            media_objects.extend(b.media_objects)

            self.remove_segment(b, dispatch=False)
            self.remove_segment(a, dispatch=False)

            segm = self.create_segment(start, end)
            segm.media_objects = media_objects
            self.project.undo_manager.to_undo((self.merge_segments, [a, b]), (self.cut_segment, [segm, cut_t]))
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

    def remove_unreal_segments(self, length = 1):
        for s in self.segments:
            if s.start >= s.end or s.end - s.start < length:
                self.remove_segment(s, dispatch=False)
        self.dispatch_on_changed()

    def cleanup_borders(self):
        self.remove_unreal_segments(length = 1)
        for i, s in enumerate(self.segments):
            if i < len(self.segments) - 1:
                end = s.get_end()
                start = self.segments[i + 1].get_start()
                center = int(round((start + end) / 2, 0))
                s.end = center
                self.segments[i + 1].start = center

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
            new.deserialize(s, self.project)
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

    def get_source_properties(self):
        return ["Segment ID", "Segment Text", "Segment Name"]

    def get_auto_text(self, property_name, time_ms, fps):
        segm = self.get_segment_of_time(time_ms)
        if segm is not None:
            if property_name == "Segment ID":
                return str(segm.ID)
            elif property_name == "Segment Text":
                return str(segm.annotation_body)
            elif property_name == "Segment Name":
                return str(segm.get_name())
            else:
                return "Invalid Property"
        return ""

class Segment(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable, IHasVocabulary, IHasMediaObject):
    def __init__(self, ID = None, start = 0, end  = 1000, duration  = None, segmentation=None, annotation_body = "", name = "New Segment"):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IHasVocabulary.__init__(self)
        IHasMediaObject.__init__(self)

        self.MIN_SIZE = 10
        self.ID = ID
        self.start = start
        self.end = end
        self.name = name

        self.duration = duration
        self.annotation_body = annotation_body
        self.timeline_visibility = True
        self.segmentation = segmentation
        self.notes = ""

    def set_id(self, ID):
        self.ID = ID
        self.dispatch_on_changed(item=self)

    def set_start(self, start):
        if start > self.end - self.MIN_SIZE :
            start = self.end - self.MIN_SIZE
        self.project.undo_manager.to_undo((self.set_start, [start]), (self.set_start, [self.start]))
        self.start = start
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()
        self.dispatch_on_changed(item=self)

    def set_end(self, end):
        print("TEST, END SET")
        if end < self.start + self.MIN_SIZE :
            end = self.start + self.MIN_SIZE

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
        return str(self.ID)

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]), (self.set_name, [self.name]))
        self.name = name
        self.dispatch_on_changed(item=self)

    def set_annotation_body(self, annotation):
        self.project.undo_manager.to_undo((self.set_annotation_body, [annotation]), (self.set_annotation_body, [self.annotation_body]))
        self.annotation_body = annotation
        self.dispatch_on_changed(item=self)

    def get_annotation_body(self):
        return self.annotation_body

    def serialize(self):
        words = []

        media_objects = []
        for obj in self.media_objects:
            media_objects.append(obj.serialize())


        for w in self.voc_list:
            words.append(w.unique_id)

        r = dict(
             scene_id = self.ID,
             unique_id = self.unique_id,
             start = self.start,
             end = self.end,
             duration = self.duration,
             name = self.name,
            annotation_body = self.annotation_body,
            notes = self.notes,
            locked = self.locked,
            words = words,
            media_objects = media_objects
        )
        return r

    def deserialize(self, serialization, project):
        self.project = project
        self.ID = serialization["scene_id"]
        self.unique_id = serialization['unique_id']
        self.start = serialization["start"]
        self.end = serialization["end"]
        self.duration = serialization["duration"]

        self.notes = serialization['notes']

        # Name has been introduced in 0.4.14
        try:
            self.name = serialization['name']
        except:
            self.name = str(self.ID)

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
            print(e)

        try:
            for w in serialization["media_objects"]:
                o_type = w['dtype']
                if o_type in [MediaObjectType.HYPERLINK, MediaObjectType.SOURCE]:
                    new = DataMediaObject(None, None, None, None).deserialize(w)

                else:
                    new = FileMediaObject(None, None, None, None).deserialize(w)
                self.media_objects.append(new)
        except Exception as e:
            print(e)

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

class Annotation(IProjectContainer, ITimeRange, IHasName, ISelectable, ILockable, IHasVocabulary, IHasMediaObject):
    def __init__(self, a_type = None, size = None, color = (255,255,255), orig_position = (50,50), t_start = 0, t_end = -1,
                 name = "New Annotation", text = "" , line_w = 2 ,font_size = 10, resource_path = "", tracking="Static"):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IHasVocabulary.__init__(self)
        IHasMediaObject.__init__(self)

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

        self.is_automated = False
        self.automated_source = -1
        self.automate_property = None

        self.tracking = tracking

        self.annotation_layer = None

        self.is_visible = False
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
        self.t_start = start
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
        media_objects = []
        for obj in self.media_objects:
            media_objects.append(obj.serialize())

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
            t_end = self.t_end,
            size = self.size,
            curr_size = self.size,
            color = self.color,
            orig_position = self.orig_position,
            line_w = self.line_w,
            text = self.text,
            font_size = self.font_size,
            font = self.font,
            widget = None,
            keys = self.keys,
            resource_path = self.resource_path,
            free_hand_paths = self.free_hand_paths,
            notes = self.notes,
            words=words,
            tracking = self.tracking,
            is_automated = self.is_automated,
            automated_source = self.automated_source,
            automate_property = self.automate_property,
            media_objects = media_objects

        )
        return result

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.a_type = AnnotationType(serialization['a_type'])
        self.t_start = serialization['t_start']
        try:
            self.t_end = serialization['t_end']
        except:
            pass
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
            self.font = serialization['font']
        except:
            pass
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

        try:
            self.is_automated = serialization['is_automated']
            self.automated_source = serialization['automated_source']
            self.automate_property = serialization['automate_property']

        except:
            pass

        try:
            for w in serialization["media_objects"]:
                o_type = w['dtype']
                if o_type in [MediaObjectType.HYPERLINK, MediaObjectType.SOURCE]:
                    new = DataMediaObject(None, None, None, None).deserialize(w)

                else:
                    new = FileMediaObject(None, None, None, None).deserialize(w)
                self.media_objects.append(new)
        except Exception as e:
            print(e)

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


class AnnotationLayer(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable, IHasVocabulary):
    def __init__(self, name = None, t_start = None, t_end = None):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IHasVocabulary.__init__(self)

        self.name = name
        self.t_start = t_start
        self.t_end = t_end
        self.annotations = []
        self.is_current_layer = False
        self.is_visible = True
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

    def create_annotation(self, type = AnnotationType.Rectangle, position = (150,150), size=(100,100),
                          color = (255,255,255), line_width = 5, name = "New Annotation", font_size = 10,
                          resource_path = ""):
        annotation = Annotation(type, size = size, color=color, line_w=line_width, name=name,
                                orig_position=position, font_size=font_size, resource_path=resource_path)

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
            words=words,
            is_visible = self.is_visible
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

        try:
            self.is_visible = serialization['is_visible']
        except Exception as e:
            print("No Visibility Found")
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

    def set_visibility(self, state):
        self.is_visible = state

        for a in self.annotations:
            if state:
                a.widget.show()
            else:
                a.widget.hide()

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def set_project(self, project):
        IProjectContainer.set_project(self, project)
        for a in self.annotations:
            a.set_project(project)

    def delete(self):
        self.project.remove_annotation_layer(self)
#endregion

#region Screenshots

class Screenshot(IProjectContainer, IHasName, ITimeRange, ISelectable, ITimelineItem, IHasVocabulary):
    def __init__(self, title = "", image = None,
                 img_blend = None, timestamp = "", scene_id = 0, frame_pos = 0,
                 shot_id_global = -1, shot_id_segm = -1, annotation_item_ids = None):
        IProjectContainer.__init__(self)
        IHasVocabulary.__init__(self)
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

        self.curr_size = 1.0


    def to_stream(self, project = None):
        obj = dict(
            img_movie = self.img_movie,
            img_blend=self.img_blend,
        )

        if project is None:
            project = self.project
        project.main_window.project_streamer.async_store(self.unique_id, obj)

    def from_stream(self, project = None):
        if project is None:
            project = self.project

        obj = project.streamer.from_stream(self.unique_id)


    pyqtSlot(object)
    def on_images_loaded(self, obj):
        self.img_movie = cv2.resize(obj['img_movie'], None, self.curr_size, self.curr_size, cv2.INTER_CUBIC)
        self.img_blend = cv2.resize(obj['img_blend'], None, self.curr_size, self.curr_size, cv2.INTER_CUBIC)

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


class ScreenshotGroup(IProjectContainer, IHasName, ISelectable, IHasVocabulary):
    def __init__(self, project, name = "New Screenshot Group"):
        IProjectContainer.__init__(self)
        IHasVocabulary.__init__(self)
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

        self.dispatch_on_changed()

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

    def delete(self):
        self.project.remove_screenshot_group(self)
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
        node.node_script = self
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

    def delete(self):
        self.project.remove_script(self)


class NodeDescriptor(IProjectContainer, IHasName, ISelectable):
    def __init__(self, operation = None, pos = (0, 0), unique_id = -1):
        IProjectContainer.__init__(self)
        self.unique_id = unique_id
        self.node_size = (200,200)
        self.node_script = None
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

    def delete(self):
        self.node_script.remove_node(self)


class ConnectionDescriptor(IProjectContainer):
    def __init__(self, input_pin=None, output_pin=None, input_pin_id=None, output_pin_id=None):
        IProjectContainer.__init__(self)
        if input_pin is not None:
            self.input_node = input_pin.node.node_object.unique_id
        if output_pin is not None:
            self.output_node = output_pin.node.node_object.unique_id
        self.input_pin_id = input_pin_id
        self.output_pin_id = output_pin_id

    def get_type(self):
        return -1

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

#region MovieDescriptor
class MovieDescriptor(IProjectContainer, ISelectable, IHasName, ITimeRange, AutomatedTextSource, IHasVocabulary):
    def __init__(self, project, movie_name="No Movie Name", movie_path="", movie_id=-0o001, year=1800, source="",
                 duration=100, fps = 30):
        IProjectContainer.__init__(self)
        IHasVocabulary.__init__(self)
        self.set_project(project) # TODO This should be changed
        self.movie_name = movie_name
        self.movie_path = movie_path
        self.movie_id = movie_id
        self.year = year
        self.source = source
        self.duration = duration
        self.notes = ""
        self.fps = fps

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
        # Dirty but should work, since the movie is the only Container that is added during Project Creation
        # we have to remove it from the id-list
        self.project.remove_from_id_list(self)

        for key, value in list(serialization.items()):
            try:
                setattr(self, key, value)
            except:
                continue

        self.set_project(self.project)
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

    def get_source_properties(self):
        return ["Current Time", "Current Frame", "Movie Name", "Movie Path", "Movie ID", "Year", "Source", "Duration", "Notes"]

    def get_auto_text(self, property_name, time_ms, fps):
        if property_name == "Current Time":
            return ms_to_string(time_ms)
        elif property_name == "Current Frame":
            return str(ms_to_frames(time_ms, fps))
        elif property_name == "Movie Name":
            return self.movie_name
        elif property_name == "Movie Path":
            return self.movie_path
        elif property_name == "Movie ID":
            return self.movie_id
        elif property_name == "Year":
            return self.year
        elif property_name == "Source":
            return self.source
        elif property_name == "Duration":
            return ms_to_string(self.duration)
        elif property_name == "Notes":
            return self.notes
        else:
            return "Invalid Property"

#endregion

#region Analysis


class AnalysisContainer(IProjectContainer, IHasName, ISelectable, IStreamableContainer):
    def __init__(self, name = "", data = None):
        IProjectContainer.__init__(self)
        self.name = name
        self.notes = ""
        self.data = data

    def unload_container(self, data=None, sync=False):
        super(AnalysisContainer, self).unload_container(self.data, sync=sync)
        self.data = None

    def apply_loaded(self, obj):
        self.data = obj

    def get_name(self):
        return self.name

    def get_preview(self):
        pass

    def serialize(self):
        data_json = []
        for d in self.data:
            data_json.append(np.array(d).tolist())


        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            notes=self.notes
        )

        return data

    def deserialize(self, serialization, streamer):
        pass

    def delete(self):
        self.project.remove_analysis(self)


class NodeScriptAnalysis(AnalysisContainer, IStreamableContainer):
    def __init__(self, name = "NewNodeScriptResult", results = "None", script_id = -1, final_nodes_ids = None):
        super(NodeScriptAnalysis, self).__init__(name, results)
        self.script_id = script_id
        self.final_node_ids = final_nodes_ids

    # def unload_container(self, data = None):
    #     super(NodeScriptAnalysis, self).unload_container(self.data)
    #     self.data = None
    #
    # def apply_loaded(self, obj):
    #     self.data = obj
    #
    def get_type(self):
        return ANALYSIS_NODE_SCRIPT

    def serialize(self):
        data_json = []

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

        self.project.main_window.numpy_data_manager.sync_store(self.unique_id, self.data)

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
        # Loop over each final node of the Script
        for r in serialization['data_json']:

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

        return self


class IAnalysisJobAnalysis(AnalysisContainer, IStreamableContainer):
    def __init__(self, name = "NewAnalysisJobResult", results = None, analysis_job_class = None, parameters = None):
        super(IAnalysisJobAnalysis, self).__init__(name, results)
        if analysis_job_class is not None:
            self.analysis_job_class = analysis_job_class.__name__
        else:
            self.analysis_job_class = None

        if parameters is not None:
            self.parameters = parameters
        else:
            self.parameters = []

    def get_preview(self):
        try:
            return self.project.main_window.eval_class(self.analysis_job_class)().get_preview(self)
        except Exception as e:
            print("Preview:", e)
            # QMessageBox.warning(self.project.main_window,"Error in Visualization", "The Visualization of " + self.name +
            #                     " has thrown an Exception.\n\n Please send the Console Output to the Developer.")

    def get_visualization(self):
        try:
            return self.project.main_window.eval_class(self.analysis_job_class)().get_visualization(self,
                                                                                             self.project.results_dir,
                                                                                             self.project.data_dir,
                                                                                             self.project,
                                                                                             self.project.main_window)
        except Exception as e:
            print("Exception in get_visualization()", e)
            QMessageBox.warning(self.project.main_window,"Error in Visualization", "The Visualization of " + self.name +
                                " has thrown an Exception.\n\n Please send the Console Output to the Developer.")

    def get_type(self):
        return ANALYSIS_JOB_ANALYSIS

    def serialize(self):

        self.data = self.project.main_window.project_streamer.sync_load(self.unique_id)
        # Store the data as numpy if it does not already exist (since it is immutable)
        # TODO sync_load may fail from time to time (Not yet known why), so we want to make sure that
        # TODO the file is not overwritten if the loaded data is None
        if self.data is not None:
            self.project.main_window.numpy_data_manager.sync_store(self.unique_id, self.data, data_type=NUMPY_NO_OVERWRITE)

        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            analysis_container_class=self.__class__.__name__,
            analysis_job_class=self.analysis_job_class,
            parameters=self.parameters,
            # data_dtypes=data_dtypes,
            # data_json=data_json,
            notes=self.notes
        )


        return data

    def deserialize(self, serialization, streamer):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.analysis_job_class = serialization['analysis_job_class']
        self.notes = serialization['notes']

        self.data = []
        self.data = streamer.sync_load(self.unique_id)
        self.parameters = serialization['parameters']

        return self


class ColormetryAnalysis(AnalysisContainer):
    def __init__(self, results = None):
        super(ColormetryAnalysis, self).__init__(name = "Colormetry", data = results)
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []
        self.histograms = []
        self.avg_colors = []
        self.palettes = []
        self.resolution = 30
        self.has_finished = False

        self.linear_colors = []
        for x in range(16):
            for y in range(16):
                for z in range(16):
                    self.linear_colors.append([x * 16, y * 16, z * 16])
        self.linear_colors = np.array([self.linear_colors] * 2, dtype=np.uint8)
        self.linear_colors = cv2.cvtColor(self.linear_colors, cv2.COLOR_LAB2RGB)[0]

    def get_histogram(self, time_ms):
        pass

    def get_palette(self, time_ms):
        pass

    def append_data(self, data):
        try:
            self.time_ms.append(data['time_ms'])
            self.histograms.append(data['hist'])
            self.frame_pos.append(data['frame_pos'])
            self.avg_colors.append(data['avg_color'])
        except Exception as e:
            print("append_data() raised ", str(e))

    def get_update(self, time_ms):
        try:
            frame_idx = int(ms_to_frames(time_ms, self.project.movie_descriptor.fps) / self.resolution)
            if len(self.histograms) > 0:
                hist_data =self.histograms[frame_idx]

                hist_data_pal = np.resize(hist_data, new_shape=(hist_data.shape[0] ** 3))
                pal_indices = np.argsort(hist_data_pal)[-6:]
                pal_cols = self.linear_colors[pal_indices]
                palette_values = hist_data_pal[pal_indices]

                return dict(hist=hist_data, palette = dict(val=palette_values, col=pal_cols))

        except Exception as e:
            print(e)
            pass

    def set_finished(self, obj):
        self.has_finished = True

    def serialize(self):
        data = dict(
            curr_location = self.curr_location,
            time_ms = self.time_ms,
            frame_pos=self.frame_pos,
            histograms=self.histograms,
            avg_colors=self.avg_colors,
            palettes=self.palettes,
            resolution=self.resolution,
        )

        if self.has_finished:
            self.project.main_window.numpy_data_manager.sync_store(self.unique_id, data, data_type=NUMPY_NO_OVERWRITE)

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
                self.curr_location = data['curr_location']
                self.time_ms = data['time_ms']
                self.frame_pos =  data['frame_pos']
                self.histograms =  data['histograms']
                self.avg_colors =  data['avg_colors']
                self.palettes =  data['palettes']
                self.resolution =  data['resolution']
            else:
                self.curr_location = 0
                self.time_ms = []
                self.frame_pos = []
                self.histograms = []
                self.avg_colors = []
                self.palettes = []
                self.resolution = 30
                self.has_finished = False
        except Exception as e:
            raise(e)


        return self

class AnalysisParameters():
    def __init__(self, target_items):
        self.target_items = []
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


# class AnalysisResult():
#     def __init__(self, data):
#         self.data = data
#
#     def get_visualization(self):
#         pass
#
#     def get_preview(self):
#         pass
#
#     def serialize(self):
#         data_json = []
#         for d in self.data:
#             data_json.append(np.array(d).tolist())
#
#         data = dict(
#             result_class=self.__class__.__name__,
#             data_json=data_json,
#         )
#
#         return data
#
#     def deserialize(self, serialization):
#         for d in serialization['data']:
#             self.data.append(np.array(d))
#         return self





# OLD CODE
# class Analysis(IProjectContainer, ITimeRange, IHasName, ISelectable):
#     def __init__(self, name=None, data=None, procedure_id=None, target_id=None):
#         IProjectContainer.__init__(self)
#         self.name = name
#         self.data = data
#         self.visualizations = []
#         self.procedure_id = procedure_id
#         self.target_id = target_id
#         self.notes = ""
#
#     def get_target_item(self):
#         return self.project.get_by_id(self.target_id)
#
#     def add_visualization(self, visualization):
#         self.visualizations.append(visualization)
#
#     def get_type(self):
#         return ANALYSIS
#
#     def get_start(self):
#         return self.time_range_item.get_start()
#
#     def get_end(self):
#         return self.time_range_item.get_start()
#
#     def set_name(self, name):
#         self.project.undo_manager.to_undo((self.set_name, [name]),
#                                           (self.set_name, [self.name]))
#         self.name = name
#         self.dispatch_on_changed(item=self)
#
#     def get_name(self):
#         return self.name
#
#     def serialize(self):
#         data_json = []
#         for d in self.data:
#             data_json.append(np.array(d).tolist())
#         data = dict(
#             name=self.name,
#             unique_id=self.unique_id,
#             data=data_json,
#             procedure_id=self.procedure_id,
#             target_id=self.target_id,
#             notes=self.notes
#         )
#
#         return data
#
#     def deserialize(self, serialization):
#
#         self.name = serialization['name']
#         self.unique_id = serialization['unique_id']
#         self.target_id = serialization['target_id']
#         self.notes = serialization['notes']
#         data = []
#         for d in serialization['data']:
#             data.append(np.array(d))
#         self.data = data
#         self.procedure_id = serialization['procedure_id']
#
#         return self
#
#     def delete(self):
#         self.project.remove_analysis(self)

#endregion

#region Vocabulary
class Vocabulary(IProjectContainer, IHasName):
    def __init__(self, name):
        IProjectContainer.__init__(self)
        self.name = name
        self.comment = ""
        self.info_url = ""
        self.words = []
        self.words_plain = []
        self.was_expanded = False
        self.category = "default"

        self.derived_vocabulary = False
        self.experiment = None
        self.base_vocabulary = None

    def create_word(self, name, parent_word = None, unique_id = -1, dispatch = True):
        word = VocabularyWord(name, vocabulary=self)
        word.unique_id = unique_id
        self.add_word(word, parent_word, dispatch)
        return word

    def add_word(self, word, parent_word = None, dispatch = True):
        """
        
        :param word: the Word object to add
        :param parent_word: the parent Word, either as String or Word Object
        :return: 
        """
        if parent_word is None:
            word.parent = self
            self.words.append(word)
            self.words_plain.append(word)
            word.set_project(self.project)
        else:
            if isinstance(parent_word, str):
                parent = self.get_word_by_name(parent_word)
            else:
                parent = parent_word
            if parent is not None:
                word.parent = parent
                parent.add_children(word)
                self.words_plain.append(word)
                word.set_project(self.project)

        if dispatch:
            self.dispatch_on_changed(item=self)

    def remove_word(self, word, dispatch = True):
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

        self.project.remove_from_id_list(word)

        if dispatch:
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

        if self.base_vocabulary is not None:
            base = self.base_vocabulary.unique_id
        else:
            base = -1

        voc_data = dict(
            name = self.name,
            category = self.category,
            unique_id = self.unique_id,
            words = words_data,
            derived = self.derived_vocabulary,
            base = base
        )

        return voc_data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.category = serialization['category']
        for w in serialization['words']:
            parent = self.project.get_by_id(w['parent'])
            # If this is a root node in the Vocabulary
            if isinstance(parent, Vocabulary):
                self.create_word(w['name'], unique_id=w['unique_id'], dispatch=False)

            else:
                self.create_word(w['name'], parent, unique_id=w['unique_id'], dispatch=False)

        try:
            self.derived_vocabulary = serialization['derived']
            self.base_vocabulary = project.get_by_id(serialization['base'])
        except:
            self.derived_vocabulary = False
            self.base_vocabulary = None
        return self

    def export_vocabulary(self, path):
        try:
            data = self.serialize()
            with open(path, "w") as f:
                json.dump(data, f)
        except:
            print("Export_Vocabulary() failed with:", path)

    def import_vocabulary(self, path = None, project = None, serialization = None):
        if serialization is None:
            with open(path, "r") as f:
                serialization = json.load(f)

        id_replacing_table = []

        self.project = project
        self.name = serialization['name']
        self.category = serialization['category']

        old_id = serialization['unique_id']
        new_id = project.create_unique_id()
        self.unique_id = new_id

        id_replacing_table.append([old_id, new_id])


        # Replace all IDs with new one:
        for w in serialization['words']:
            old = w['unique_id']
            new = self.project.create_unique_id()
            id_replacing_table.append([old, new])

        for w in serialization['words']:
            old_parent = w['parent']

            new_parent = -1
            for tpl in id_replacing_table:
                if tpl[0] == old_parent:
                    new_parent = tpl[1]
                    break

            old_id = w['unique_id']
            new_id = -1
            for tpl in id_replacing_table:
                if tpl[0] == old_id:
                    new_id = tpl[1]
                    break


            parent = self.project.get_by_id(new_parent)
            # If this is a root node in the Vocabulary
            if isinstance(parent, Vocabulary):
                self.create_word(w['name'], unique_id=new_id)

            else:
                self.create_word(w['name'], parent, unique_id=new_id)

        return self, id_replacing_table

    def get_vocabulary_id(self):
        vid = self.name
        for w in self.get_vocabulary_as_list():
            try:
                vid += w.name[0]
            except:
                continue
        print("Vocabulary ID: ", vid)
        return vid

    # def set_experiment(self, experiment, base_vocabulary):
    #     self.experiment = experiment
    #     self.base_vocabulary = base_vocabulary
    #     self.derived_vocabulary = True

    def get_type(self):
        return VOCABULARY

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def delete(self):
        for w in self.words_plain:
            self.remove_word(w, dispatch=False)
        self.project.remove_vocabulary(self)

class VocabularyWord(IProjectContainer, IHasName):
    def __init__(self, name, vocabulary, parent = None, is_checkable = False):
        IProjectContainer.__init__(self)
        self.name = name
        self.comment = ""
        self.info_url = ""
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

    def get_name(self):
        return self.name

    def delete(self):
        self.project.remove_from_id_list(self)
        self.vocabulary.remove_word(self)

def get_default_vocabulary():
    voc = Vocabulary("Scene Locations")
    voc.create_word("House")
    voc.create_word("Kitchen", "House")
    voc.create_word("Bedroom", "House")
    voc.create_word("Toilet", "House")


    return voc
#endregion

#region Experiment
# class Experiment(IProjectContainer, IHasName):
#     """
#     An Experiment defines a specific set of rules, with which the user wants to perform a classification of a film.
#
#     Example:
#         A User wants to analyze the Color Features of a Film. To do so, he wants to segment Films into temporal Segments
#         each one is a Scene.
#         He then wants to classify the Foreground and the Background Color for each Segment based on his homemade
#         Vocabulary called "ColorVocabulary". At the end, he also wants to generate some automated ColorFeature Extractions
#         based on this Segmentation.
#
#     """
#
#     def __init__(self, name="New Experiment"):
#         IProjectContainer.__init__(self)
#
#         self.name = name
#         self.classification_sources = []
#         self.classification_objects = []
#         self.analyses_templates = []
#
#         self.classified_containers = []
#
#     def remove_class_object(self, classification_target):
#         if classification_target in self.classification_objects:
#             self.classification_objects.remove(classification_target)
#             self.project.remove_from_id_list(classification_target)
#
#     def create_class_object(self, name, parent = None):
#         new = ClassificationObjects(name, experiment=self)
#
#         if parent == self or parent is None:
#             self.add_class_object(new)
#         else:
#             parent.add_child(new)
#
#         return new
#
#     def clear_from_deleted_containers(self):
#         for root in self.classification_objects:
#             objects = []
#             root.get_children_plain(objects)
#             for obj in objects:
#                 obj.clear_deleted_containers()
#
#     def add_class_object(self, classification_object):
#         self.classification_objects.append(classification_object)
#         classification_object.set_project(self.project)
#         classification_object.parent = self
#
#     def get_type(self):
#         return EXPERIMENT
#
#     def get_name(self):
#         return self.name
#
#     def set_name(self, name):
#         self.name = name
#         self.dispatch_on_changed(item = self)
#
#     def serialize(self):
#
#         serializations = []
#         for cls in self.classification_objects:
#             plain = []
#             cls.get_children_plain(plain)
#             for c in plain:
#                 serializations.append(c.serialize())
#
#         serialization = dict(
#             name = self.name,
#             unique_id = self.unique_id,
#             classification_objects = serializations,
#             classification_sources = self.classification_sources,
#             analyses_templates = self.analyses_templates,
#
#         )
#         return serialization
#
#     def deserialize(self, serialization, project):
#         self.name = serialization['name']
#         self.unique_id = serialization['unique_id']
#         self.classification_sources = serialization['classification_sources']
#         self.analyses_templates = serialization['analyses_templates']
#         project.add_experiment(self)
#
#         for obj in serialization['classification_objects']:
#             ClassificationObjects("NONAME", self).deserialize(obj, project)
#
#         return self
#
#     def get_classification_objects_plain(self):
#         result = []
#         for c in self.classification_objects:
#             r = [c]
#             c.get_children_plain(r)
#             result.extend(r)
#
#         return result
#
#     def get_vocabulary_list(self, container = None):
#         if container is None:
#             result = []
#             for obj in self.get_classification_objects_plain():
#                 for voc in obj.classification_vocabularies:
#                     result.append(voc)
#             return result
#         else:
#             result = []
#             for obj in self.get_classification_objects_plain():
#                 if obj.has_container(container):
#                     for voc in obj.classification_vocabularies:
#                         result.append(voc)
#             return result
#
#     def delete(self):
#         self.project.remove_experiment(self)
#         self.dispatch_on_changed()

class ClassificationObjects(IProjectContainer, IHasName):
    """
    A ClassificationTarget is an Object that one wants to classify by a set of Vocabularies.
    Several ClassificationTargets may form a Tree. 
    
    Example: Say one wants to analyse the Foreground and Background Color of a given Film using his homemade 
    Vocabulary called "ColorVocabulary". 
    
    The ClassificationTargets would therefore be "Foreground" and "Background", both will have "ColorVocabulary". 
    """
    def __init__(self, name, experiment, parent = None):
        IProjectContainer.__init__(self)

        self.name = name
        self.experiment = experiment
        self.parent = parent
        self.children = []
        self.classification_vocabularies = []

        self.target_container = []
        self.target_containers_string = "All"
        self.target_container_type = TargetContainerType.ALL

    def add_vocabulary(self, voc: Vocabulary, dispatch = True):
        new_voc = self.project.copy_vocabulary(voc, add_to_global=False)
        new_voc.set_name(self.name + ":" + new_voc.get_name())
        self.project.add_vocabulary(new_voc, dispatch)
        new_voc.set_experiment(self.experiment, voc)
        self.classification_vocabularies.append(new_voc)
        self.dispatch_on_changed()

    def remove_vocabulary(self, voc):
        self.classification_vocabularies.remove(voc)
        self.project.remove_vocabulary(voc)

    def get_base_vocabularies(self):
        """
        Returns a list of all Base Vocabularies used in this Object
        :param voc: The Base Vocabulary
        :return: list of all Base Vocabularies
        """
        result = []
        for v in self.classification_vocabularies:
            if v is not None:
                result.append(v.base_vocabulary)
        return result

    def clear_deleted_containers(self):
        for tgt in self.target_container:
            if tgt not in self.project.segmentation and \
                tgt not in self.project.annotation_layers and \
                    tgt not in self.project.screenshot_groups:
                self.target_container.remove(tgt)

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def has_container(self, container):
        """
        :param container: 
        :return: returns True if the input container is target of this Classification Object
        """
        if self.target_container_type == TargetContainerType.EXPLICIT_ANNOTATIONS:
            if container in self.target_container[0].annotations:
                return True
        elif self.target_container_type == TargetContainerType.EXPLICIT_SCREENSHOTS:
            if container in self.target_container[0].screenshots:
                return True

        elif self.target_container_type == TargetContainerType.EXPLICIT_SEGMENTS:
            if container in self.target_container[0].segments:
                return True

        elif self.target_container_type is TargetContainerType.ALL_SEGMENTS:
            if container.get_type() == SEGMENT:
                return True
        elif self.target_container_type is TargetContainerType.ALL_SCREENSHOTS:
            if container.get_type() == SCREENSHOT:
                return True
        elif self.target_container_type is TargetContainerType.ALL_ANNOTATIONS:
            if container.get_type() == ANNOTATION:
                return True
        else:
            return True
        return False

    def add_child(self, classification_object):
        classification_object.parent = self
        classification_object.set_project(self.project)
        self.children.append(classification_object)

    def remove_child(self, classification_object):
        if classification_object in self.children:
            self.children.remove(classification_object)
            self.project.remove_from_id_list(classification_object)
        else:
            print("NOT FOUND")

    def set_target_container(self, container: IProjectContainer, type = TargetContainerType.ALL):
        if not isinstance(container, list):
            container = [container]
        if container == [None]:
            self.target_container = []
            self.target_containers_string = "All"
        else:
            self.target_container = container
            self.target_containers_string = str(self.target_container)

        self.target_container_type = type
        self.dispatch_on_changed(item=self)

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def get_type(self):
        return CLASSIFICATION_OBJECT

    def serialize(self):
        serialization = dict(
            name=self.name,
            unique_id = self.unique_id,
            parent = self.parent.unique_id,
            children = [c.unique_id for c in self.children],
            classification_vocabularies = [v.unique_id for v in self.classification_vocabularies],
            classification_vocabularies_vid = [v.base_vocabulary.get_vocabulary_id() for v in self.classification_vocabularies],
            target_container = [c.unique_id for c in self.target_container],
            target_container_type = self.target_container_type.value

        )
        return serialization

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        p = project.get_by_id(serialization['parent'])

        if isinstance(p, ClassificationObjects):
            p.add_child(self)
        else:
            p.add_class_object(self)

        self.classification_vocabularies = [project.get_by_id(uid) for uid in serialization['classification_vocabularies']]
        try:
            self.target_container = [project.get_by_id(uid) for uid in serialization['target_container']]
            self.target_container_type = TargetContainerType(serialization['target_container_type'])
        except:
            self.target_container = []
            self.target_container_type = TargetContainerType.ALL

        return self
#endregion

#region MediaObject
class AbstractMediaObject(IProjectContainer, IHasName):
    def __init__(self, name, container:IHasMediaObject, dtype):
        IProjectContainer.__init__(self)
        self.name = name
        self.container = container
        self.dtype = dtype

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_type(self):
        return MEDIA_OBJECT

    def serialize(self):
        data = dict(
            name = self.name,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self

    def preview(self):
        pass

class FileMediaObject(AbstractMediaObject):
    def __init__(self, name, file_path, container, dtype):
        super(FileMediaObject, self).__init__(name, container, dtype)
        self.file_path = file_path

    def serialize(self):
        data = dict(
            name = self.name,
            file_path = self.file_path,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.file_path = serialization['file_path']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self

    def preview(self):
        try:
            open_file(self.file_path)
        except Exception as e:
            print(e)


class DataMediaObject(AbstractMediaObject):
    def __init__(self, name, data, container, dtype):
        super(DataMediaObject, self).__init__(name, container, dtype)
        self.data = data

    def serialize(self):
        data = dict(
            name = self.name,
            data = self.data,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.data = serialization['data']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self

#endregion




