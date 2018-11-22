import datetime
import json
import cv2
from shutil import copy2
import os
from random import randint
import shelve
from core.data.computation import blend_transparent
import numpy as np
from core.data.interfaces import IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable
from core.data.undo_redo_manager import UndoRedoManager
from core.data.computation import *
from core.gui.vocabulary import VocabularyItem
from core.data.project_streaming import ProjectStreamer, NUMPY_NO_OVERWRITE, NUMPY_OVERWRITE
from core.data.enums import *
from typing import List
from core.data.project_streaming import IStreamableContainer

from core.data.hdf5_manager import HDF5Manager

from core.node_editor.node_editor import *
from shutil import copy2
from enum import Enum
# from PyQt4 import QtCore, QtGui
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QPoint, QRect, QSize

from core.container.annotation import *
from core.container.segmentation import *
from core.container.screenshot import *
from core.container.experiment import *
from core.container.analysis import *
from core.container.media_objects import *
from core.container.node_scripts import *


class VIANProject(IHasName, IClassifiable):
    """
    This Class hold the Complete VIAN Project.
    As such it is the owner of all subsequent IProjectContainers, directly or indirectly

    A VIANProject is a FileSystem and a json File that is located inside this folder.

    :var undo_manager = UndoRedoManager()
    :var main_window: A Reference to the Main Window
    :var inhibit_dispatch: if Dispatch should be inhibited

    :var path: The Path to the Projects .eext file (absolute)
    :var name: The Name of the Project
    :var folder: The Root Directory of the Project where the eext file lies inside
    :var data_dir: the path to the data dir
    :var results_dir: the path to the result dir
    :var shots_dir: the path to the shot dir
    :var export_dir: the path to the export dir

    :var corpus_id: this is the VIANCorpus id of this project (default: -1)

    :var id_list: A list of [Unique-ID, IProjectContainer] tuples

    :var annotation_layers: A List of Annotation Layers
    :var current_annotation_layer: The Currently Selected Annotation Layer
    :var screenshots: A List of all Screenshots
    :var segmentation: A List of all Segmentations
    :var main_segmentation_index: The index of the main Segmentation Layer in self.segmentations
    :var movie_descriptor: The Movie Descriptor of this Project
    :var analysis: A List of IAnalysisResult
    :var screenshot_groups: All Screenshot Groups
    :var vocabularies: All Vocabularies (deprecated these are now global)

    :var experiments: A List of all Experiments

    :var current_script: The Currently Selected NodeScript
    :var node_scripts: A List of All Node Scripts

    :var add_screenshot_group("All Shots", initial=True)
    :var active_screenshot_group = self.screenshot_groups[0]
    :var active_screenshot_group.is_current = True

    :var colormetry_analysis: The ColorimetryAnalysis Reference

    :var selected: A List of Currently Selected IProjectContainers
    """
    def __init__(self, main_window, path = "", name = "", folder=""):
        IClassifiable.__init__(self)
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
        self.hdf5_path = ""

        self.corpus_id = -1

        self.id_list = []

        self.meta_data = None

        self.annotation_layers = []             #type: List[AnnotationLayer]
        self.current_annotation_layer = None    #type: AnnotationLayer
        self.screenshots = []                   #type: List[Screenshot]
        self.segmentation = []                  #type: List[Segmentation]
        self.main_segmentation_index = 0
        self.movie_descriptor = MovieDescriptor(project=self)
        self.analysis = []                      #type: List[AnalysisContainer]
        self.screenshot_groups = []             #type: List[ScreenshotGroup]
        self.vocabularies = []                  #type: List[Vocabulary]

        self.experiments = []                   #type: List[Experiment]

        self.current_script = None
        self.node_scripts = []                  #type: List[NodeScript]
        self.create_script(dispatch=False)

        self.add_screenshot_group("All Shots", initial=True)
        self.active_screenshot_group = self.screenshot_groups[0]
        self.active_screenshot_group.is_current = True

        self.active_classification_object = None
        # self.folder = path.split("/")[len(path.split("/")) - 1]
        self.notes = ""

        self.colormetry_analysis = None

        self.add_vocabulary(get_default_vocabulary())

        self.hdf5_manager = None

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

    def reset_file_paths(self, folder, file, main_window = None):
        self.path = file
        self.folder = folder
        root = self.folder

        self.data_dir = root + "/data"
        self.results_dir = root + "/results"
        self.shots_dir = root + "/shots"
        self.export_dir = root + "/export"
        self.hdf5_path = self.data_dir + "/analyses.hdf5"

        if main_window is not None:
            self.main_window.project_streamer.on_loaded(self)

    def create_file_structure(self):
        self.reset_file_paths(self.folder, self.path, None)
        if not os.path.isdir(self.data_dir):
            os.mkdir(self.data_dir)
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        if not os.path.isdir(self.shots_dir):
            os.mkdir(self.shots_dir)
        if not os.path.isdir(self.export_dir):
            os.mkdir(self.export_dir)

    def get_all_containers(self, types = None):
        result = []
        if types is None:
            for itm in self.id_list:
                result.append(itm[1])
        else:
            for itm in self.id_list:
                if itm[1].get_type() in types:
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

    def sanitize_paths(self):
        self.path = os.path.normpath(self.path)
        self.name = os.path.normpath(self.name)
        self.folder = os.path.normpath(self.folder)
        self.data_dir = os.path.normpath(self.data_dir)
        self.results_dir = os.path.normpath(self.results_dir)
        self.shots_dir = os.path.normpath(self.shots_dir)
        self.export_dir = os.path.normpath(self.export_dir)
        self.movie_descriptor.movie_path = os.path.normpath(self.movie_descriptor.movie_path)
        print(self.folder)

    def connect_hdf5(self):
        self.hdf5_manager = HDF5Manager()
        needs_init = self.hdf5_manager.set_path(self.hdf5_path)
        if needs_init:
            self.hdf5_manager.initialize_all()

    def set_active_classification_object(self, cl_obj):
        self.active_classification_object = cl_obj
        self.dispatch_changed(item=self)

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
            # segm = new.create_segment(start = s.get_start(), stop = s.get_end(), dispatch=False)
            segm = new.create_segment2(start = s.get_start(), stop = s.get_end(),
                                       dispatch=False,
                                       mode=SegmentCreationMode.INTERVAL)
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
        self.remove_from_id_list(segmentation)
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

    def get_main_segmentation(self) -> Segmentation:
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
    def create_screenshot(self, name, frame_pos = None, time_ms = None):
        if frame_pos is None and time_ms is None:
            print("Either frame or ms has to be given")
            return
        video_capture = cv2.VideoCapture(self.movie_descriptor.movie_path)

        if frame_pos is None:
            frame_pos = ms_to_frames(time_ms, video_capture.get(cv2.CAP_PROP_FPS))
        else:
            time_ms = frame2ms(frame_pos, video_capture.get(cv2.CAP_PROP_FPS))

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = video_capture.read()

        if ret:
            # shot = Screenshot(title="New Screenshot", image=frame, img_blend=frame_annotated, timestamp=time, frame_pos=frame_pos, annotation_item_ids=annotation_ids)

            new = Screenshot(name, frame, img_blend = None, timestamp=time_ms, frame_pos=frame_pos)
            self.add_screenshot(new)

    def create_screenshot_headless(self, name, frame_pos = None, time_ms = None, fps = 29.0):
        if frame_pos is None and time_ms is None:
            print("Either frame or ms has to be given")
            return

        if frame_pos is None:
            frame_pos = ms_to_frames(time_ms, fps)
        else:
            time_ms = frame2ms(frame_pos, fps)

        new = Screenshot(name, None, img_blend=None, timestamp=time_ms, frame_pos=frame_pos)
        self.add_screenshot(new)
        return new

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
            self.remove_from_id_list(screenshot)
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
        grp.set_project(self)
        self.screenshot_groups.append(grp)
        if not initial:
            self.dispatch_changed()

        return grp

    def remove_screenshot_group(self, grp):
        if grp is not self.screenshot_groups[0]:
            self.screenshot_groups.remove(grp)
            self.remove_from_id_list(grp)
            self.dispatch_changed()

    def get_screenshots_of_segment(self, main_segm_id, segmentation = None):
        if segmentation is None:
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

    def add_analyses(self, analyses):
        for a in analyses:
            try:
                self.add_analysis(a)
            except Exception as e:
                print(a.data)
                raise e
                print(e, a.analysis_job_class)

        # ids = []
        # objs = []
        # data_types = []
        #
        # for a in analyses:
        #     objs.append(self.main_window.eval_class(a.analysis_job_class)().to_json(a.data))
        #     a.data = None
        #     a.set_project(self)
        #     ids.append(a.unique_id)
        #     data_types.append(self.main_window.eval_class(a.analysis_job_class)().serialization_type())
        #     self.analysis.append(a)
        # self.main_window.project_streamer.bulk_store(ids, objs, data_types)

    def remove_analysis(self, analysis):
        if analysis in self.analysis:
            self.analysis.remove(analysis)
            self.remove_from_id_list(analysis)
            self.undo_manager.to_undo((self.remove_analysis, [analysis]), (self.add_analysis, [analysis]))
            self.dispatch_changed()

    # def get_analyzes_of_item(self, item):
    #     result = []
    #     for a in self.analysis:
    #         if isinstance(a, IAnalysisJobAnalysis) and item.unique_id in a.parameters.target_items:
    #             result.append(item)
    #     return item

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
        print("Create Colorimetry Analysis")
        colormetry = ColormetryAnalysis()
        self.add_analysis(colormetry)
        self.colormetry_analysis = colormetry
        # self.colormetry_analysis.clear()
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

    def get_mask_analyses(self):
        """
        Returns a list of all Analyses that are of type MaskAnalysis
        :return: A list of MaskAnalyses if any
        """
        result = []
        for a in self.analysis:
            if isinstance(a, MaskAnalysis):
                result.append(a)
        return result

    #region Annotations
    def create_annotation_layer(self, name, t_start = 0, t_stop = 0):
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

        self.remove_from_id_list(layer)
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
        project = self

        a_layer = []
        screenshots = []
        screenshots_img = []
        screenshots_ann = []
        segmentations = []
        analyzes = []
        screenshot_groups = []
        scripts = []
        experiments = []

        vocabularies = []

        for v in project.vocabularies:
            vocabularies.append(v.serialize())

        for a in project.annotation_layers:
            a_layer.append(a.serialize())

        for b in project.screenshots:
            src, img = b.serialize()
            screenshots.append(src)
            # screenshots_img.append(img[0])
            # screenshots_ann.append(img[1])

        for c in project.segmentation:
            segmentations.append(c.serialize())

        for d in project.analysis:
            analyzes.append(d.serialize())

        for e in project.screenshot_groups:
            screenshot_groups.append(e.serialize())

        for f in project.node_scripts:
            scripts.append(f.serialize())

        for g in project.experiments:
            experiments.append(g.serialize())

        data = dict(
            path=project.path,
            name=project.name,
            corpus_id=project.corpus_id,
            annotation_layers=a_layer,
            notes=project.notes,
            current_annotation_layer=None,
            results_dir=project.results_dir,
            export_dir=project.export_dir,
            shots_dir=project.shots_dir,
            data_dir=project.data_dir,
            main_segmentation_index=project.main_segmentation_index,
            screenshots=screenshots,
            segmentation=segmentations,
            analyzes=analyzes,
            movie_descriptor=project.movie_descriptor.serialize(),
            version=project.main_window.version,
            screenshot_groups=screenshot_groups,
            scripts=scripts,
            vocabularies=vocabularies,
            experiments=experiments,
            meta_data = project.meta_data,
            hdf_indices = project.hdf5_manager.get_indices()
        )
        if path is None:
            path = project.path
        path = path.replace(settings.PROJECT_FILE_EXTENSION, "")

        numpy_path = path + "_scr"
        project_path = path + ".eext"

        if settings.SCREENSHOTS_STATIC_SAVE:
            np.savez(numpy_path, imgs=screenshots_img, annotations=screenshots_ann, empty=[True])

        try:
            with open(project_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print("Exception during Storing: ", str(e))

    def load_project(self, settings, path):
        if not settings.PROJECT_FILE_EXTENSION in path:
            path += settings.PROJECT_FILE_EXTENSION

        if not os.path.isfile(path):
            print("File not Found: ", path)
            return

        print("Reading From", os.path.abspath(path))
        with open(path) as f:
            my_dict = json.load(f)

        self.path = my_dict['path']
        self.path = path
        self.name = my_dict['name']
        self.main_segmentation_index = my_dict['main_segmentation_index']

        try:
            self.corpus_id = my_dict['corpus_id']
        except:
            self.corpus_id = -1
        try:
            self.notes = my_dict['notes']
        except:
            self.notes = ""

        try:
            self.meta_data = my_dict['meta_data']
        except:
            pass

        # splitted = path.split("/")[0:len(path.split("/")) - 1]
        # self.folder = ""
        # for f in splitted:
        #     self.folder += f + "/"
        self.folder = os.path.split(path)[0] + "/"
        self.results_dir = self.folder + "/results/"
        self.export_dir = self.folder + "/export/"
        self.shots_dir = self.folder + "/shots/"
        self.data_dir = self.folder + "/data/"
        self.hdf5_path = self.data_dir + "analyses.hdf5"

        # self.main_window.numpy_data_manager.project = self




        move_project_to_directory_project = False
        version = [0,0,0]
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

        self.hdf5_manager = HDF5Manager()
        self.hdf5_manager.set_path(self.hdf5_path)

        try:
            self.hdf5_manager.set_indices(my_dict['hdf_indices'])
        except Exception as e:
            self.hdf5_manager.initialize_all()


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



        try:
            old = self.screenshot_groups
            for o in old:
                self.remove_screenshot_group(o)
            self.screenshot_groups = []

            for e in my_dict['screenshot_groups']:
                new = ScreenshotGroup(self).deserialize(e, self)
                self.add_screenshot_group(group=new)

            self.active_screenshot_group = self.screenshot_groups[0]
            self.screenshot_groups[0].is_current = True

        except Exception as e:
            self.screenshot_groups = old
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


        try:
            for e in my_dict['experiments']:
                new = Experiment().deserialize(e, self)

        except Exception as e:
            print(e)

        for d in my_dict['analyzes']:
            if d is not None:
                try:
                    new = eval(d['analysis_container_class'])().deserialize(d, self)
                    if isinstance(new, ColormetryAnalysis):
                        try:
                            # If the Project is older than 0.6.0 we want to explicitly override the Colorimetry
                            if int(version[1]) < 6:
                                new = ColormetryAnalysis()
                            self.colormetry_analysis = new
                            self.add_analysis(new)
                            new.check_finished()
                        except Exception as e:
                            self.create_colormetry()
                    else:
                        self.add_analysis(new)
                except Exception as e:
                    print("Exception in Load Analyses", str(e))
        # Finalizing the Project, Hooking up the ID Connections
        # Connecting the NodeScriptAnalysis Objects to their Final Nodes
        for a in self.analysis:
            if isinstance(a, NodeScriptAnalysis):
                for i, res in enumerate(a.data):
                    node = self.get_by_id(a.final_node_ids[i])
                    if node is not None:
                        node.operation.result = res

        self.movie_descriptor.set_movie_path(self.movie_descriptor.movie_path)


        if self.colormetry_analysis is not None:
            if not self.hdf5_manager.has_colorimetry():
                self.colormetry_analysis.clear()
        else:
            self.create_colormetry()
        self.sort_screenshots()
        self.undo_manager.clear()
        self.sanitize_paths()

    def get_template(self, segm = False, voc = False, ann = False, scripts = False, experiment = False):
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
                layers.append([l.get_name(), l.unique_id])
        if scripts:
            for n in self.node_scripts:
                node_scripts.append(n.serialize())

        if experiment:
            for e in self.experiments:
                experiments.append(e.to_template())


        template = dict(
            segmentations = segmentations,
            vocabularies = vocabularies,
            layers = layers,
            node_scripts=node_scripts,
            experiments = experiments
        )
        return template

    def apply_template(self, template_path):

        try:
            with open(template_path, "r") as f:
                template = json.load(f)
        except:
            print("Importing Template Failed")
            return

        for s in template['segmentations']:
            new = Segmentation(s[0])
            new.unique_id = s[1]
            self.add_segmentation(new)

        for v in template['vocabularies']:
            voc = Vocabulary("voc").deserialize(v, self)
            self.add_vocabulary(voc)

        for l in template['layers']:
            new = AnnotationLayer(l[0])
            new.unique_id = l[1]
            self.add_annotation_layer(new)

        for n in template['node_scripts']:
            new = NodeScript().deserialize(n, self)
            self.add_script(new)

        for e in template['experiments']:
            new = Experiment().deserialize(e, self)

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
                if v.name == name:
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
                    print("Vocabulary is duplicate")
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

    def get_word_object_from_name(self, name):

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
                new_path = self.data_dir + "/" + str(counter).zfill(2) + "_" + fname
                if not os.path.isfile(new_path):
                    is_file = False
                counter += 1

            copy2(data, new_path)
            new = FileMediaObject(fname, new_path, container, o_type)

        self.add_media_object(new, container)

    def add_media_object(self, media_object, container:IHasMediaObject, dispatch = True):
        media_object.set_project(self)
        container.add_media_object(media_object)
        self.dispatch_changed(item = container)

    #endregion

    #region Experiments

    def create_experiment(self):
        new = Experiment()
        self.add_experiment(new)
        return new
        pass

    def add_experiment(self, experiment):
        experiment.set_project(self)
        self.experiments.append(experiment)

        self.undo_manager.to_undo((self.add_experiment, [experiment]),
                                  (self.remove_experiment, [experiment]))
        self.dispatch_changed(item=experiment)

    def remove_experiment(self, experiment):
        if experiment in self.experiments:
            self.experiments.remove(experiment)
            self.remove_from_id_list(experiment)
            self.undo_manager.to_undo((self.remove_experiment, [experiment]),
                                      (self.add_experiment, [experiment]))

            self.dispatch_changed()



    #endregion

    # region Setters/Getters
    def cleanup(self):
        # self.main_window.numpy_data_manager.clean_up([f[0] for f in self.id_list])
        for l in self.annotation_layers:
            for w in l.annotations:
                if w.widget is not None:
                    w.widget.close()
        if self.hdf5_manager is not None:
            self.hdf5_manager.on_close()
        # if self.hdf5_manager is not None:
        #     self.clean_hdf5()

    def clean_hdf5(self, analyses = None):
        new_h5 = HDF5Manager()
        new_h5.set_path(self.data_dir + "/clean_temp.hdf5")
        new_h5.initialize_all(analyses)
        for a in self.analysis:
            try:
                if isinstance(a, SemanticSegmentationAnalysisContainer):
                    if a.a_class is None:
                        a.a_class = self.main_window.eval_class(a.analysis_job_class)
                    data, shape = a.a_class().to_hdf5(a.get_adata())
                    new_h5.dump(data, a.a_class().dataset_name, a.unique_id)
                elif isinstance(a, IAnalysisJobAnalysis):
                    if a.a_class is None:
                        a.a_class = self.main_window.eval_class(a.analysis_job_class)
                    data = a.a_class().to_hdf5(a.get_adata())
                    new_h5.dump(data, a.a_class().dataset_name, a.unique_id)
            except Exception as e:
                print(e)
                continue

        self.hdf5_manager.h5_file.close()
        new_h5.h5_file.close()
        os.remove(self.hdf5_manager.path)
        shutil.copy2(new_h5.path, self.hdf5_manager.path)
        os.remove(new_h5.path)
        self.hdf5_manager = HDF5Manager()
        self.hdf5_manager.set_path(self.hdf5_path)


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
                # print("Removed: ", d)
                break

    def clean_id_list(self):
        self.id_list = [itm for itm in self.id_list if itm[0] == itm[1].unique_id]

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

    def get_all_ids(self):
        return [itm[0] for itm in self.id_list]

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

#region MovieDescriptor
class MovieDescriptor(IProjectContainer, ISelectable, IHasName, ITimeRange, AutomatedTextSource, IClassifiable):
    """
    :var movie_name: The Name of the Movie
    :var movie_path: The Path of the Movie
    :var is_relative: If movie_path is relative or not
    :var movie_id: The Movie ID tuple (ID, )
    :var year: The Production Year of this Movie
    :var source: The SourceType Enum of this movie {DVD, VHS, FILM}
    :var duration: Duration of the Movie in MS
    :var notes: Additinoal notes added in the Inspector
    :var fps: The float FPS

    """
    def __init__(self, project, movie_name="No Movie Name", movie_path="", movie_id="0_0_0", year=1800, source="",
                 duration=100, fps = 30):
        IProjectContainer.__init__(self)
        IClassifiable.__init__(self)
        self.set_project(project)
        self.movie_name = movie_name
        self.movie_path = movie_path
        self.movie_id = movie_id
        self.year = year
        self.source = source
        self.duration = duration
        self.notes = ""
        self.fps = fps
        self.is_relative = False
        self.meta_data = dict()
        self.letterbox_rect = None

    def set_letterbox_rect(self, rect):
        self.letterbox_rect = rect

    def get_letterbox_rect(self):
        return self.letterbox_rect

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
            is_relative = self.is_relative,
            meta_data = self.meta_data,
            letterbox_rect = self.letterbox_rect
        )

        return data

    def set_duration(self, duration):
        self.duration = duration
        self.dispatch_on_changed(item=self)

    def deserialize(self, serialization):
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

    def get_movie_path(self):
        if self.is_relative:
            abs_path = os.path.normpath(self.project.folder + "/" + self.movie_path)
            if os.path.isfile(abs_path):
                return abs_path
            elif os.path.isfile(self.movie_path):
                self.is_relative = False
                return self.movie_path
            else:
                return ""

        else:
            return self.movie_path

    def set_movie_path(self, path):
        """
        Sets the movie path of this project. 
        If the movie is within the Projects directory it makes it relative, else it makes it absolut
        :param path: 
        :return: 
        """
        if self.project.folder in path:
            common = os.path.commonpath([self.project.path, path])
            self.movie_path = path.replace(common, "/")
            self.is_relative = True
        else:
            self.movie_path = os.path.normpath(path)
            self.is_relative = False
        print("New Final Moviepath", self.movie_path, "Relative:", self.is_relative)
        # try:
        #     if os.path.commonpath([self.project.folder]) == os.path.commonpath([self.project.folder, path]):
        #         self.movie_path = os.path.basename(path)
        #         self.is_relative = True
        #     else:
        #         self.movie_path = path
        #         self.is_relative = False
        # except Exception as e:
        #     print(e)
        #     self.movie_path = path
        #     self.is_relative = False

        cap = cv2.VideoCapture(self.get_movie_path())
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        print("MoviePath set: ", path, " to \"" ,self.movie_path, "\"  ", self.is_relative)

    def get_movie_id_list(self):
        return self.movie_id.split("_")

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

def get_default_vocabulary():
    voc = Vocabulary("Scene Locations")
    voc.create_word("House")
    voc.create_word("Kitchen", "House")
    voc.create_word("Bedroom", "House")
    voc.create_word("Toilet", "House")


    return voc






