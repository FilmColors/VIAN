# from core.node_editor.node_editor import *
from shutil import copy2
from typing import Union
from threading import Lock
from uuid import uuid4

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileDialog
from random import randint

from core import version
from core.data.enums import *
from .media_descriptor import MovieDescriptor
from .hdf5_manager import HDF5Manager
from .undo_redo_manager import UndoRedoManager
from .annotation import *
from .segmentation import *
from .screenshot import *
from .experiment import *
from .analysis import *
from .media_objects import *
from .node_scripts import *

# from core.data.importers import ImportDevice
# from core.data.exporters import ExportDevice
VIAN_PROJECT_EXTENSION = ".eext"



class VIANProject(QObject, IHasName, IClassifiable):
    """
    This Class hold the Complete VIAN Project.
    As such it is the owner of all subsequent IProjectContainers, directly or indirectly

    A VIANProject is a FileSystem and a json File that is located inside this folder.

    :var path: The Path to the Projects .eext file (absolute)
    :var name: The Name of the Project
    :var folder: The Root Directory of the Project where the eext file lies inside

    :var movie_descriptor: The Movie Descriptor of this Project
    :var annotation_layers: A List of Annotation Layers
    :var screenshots: A List of all Screenshots, without grouping
    :var segmentation: A List of all Segmentations
    :var analysis: A List of IAnalysisResult
    :var screenshot_groups: All Screenshot Groups
    :var vocabularies: All Vocabularies (deprecated these are now global)
    :var experiments: A List of all Experiments
    :var colormetry_analysis: The ColorimetryAnalysis Reference


    Application Variables:
    :var active_screenshot_group = self.screenshot_groups[0]
    :var active_screenshot_group.is_current = True
    :var main_segmentation_index: The index of the main Segmentation Layer in self.segmentations, by which Screenshots are sorted
    :var current_annotation_layer: The Currently Selected Annotation Layer
    :var id_list: A list of [Unique-ID, IProjectContainer] tuples
    :var corpus_id: this is the VIANCorpus id of this project (default: -1)
    :var undo_manager = UndoRedoManager()
    :var main_window: A Reference to the Main Window
    :var inhibit_dispatch: if Dispatch should be inhibited
    :var selected: A List of Currently Selected IProjectContainers
    :var data_dir: the path to the data dir
    :var results_dir: the path to the result dir
    :var shots_dir: the path to the shot dir
    :var export_dir: the path to the export dir
    """

    onScreenshotGroupAdded = pyqtSignal(object)
    onScreenshotGroupRemoved = pyqtSignal(object)
    onScreenshotsHighlighted = pyqtSignal(object)
    onSegmentationAdded = pyqtSignal(object)
    onSegmentationRemoved = pyqtSignal(object)
    onAnnotationLayerAdded = pyqtSignal(object)
    onAnnotationLayerRemoved = pyqtSignal(object)
    onAnalysisAdded = pyqtSignal(object)
    onAnalysisRemoved = pyqtSignal(object)
    onExperimentAdded = pyqtSignal(object)
    onExperimentRemoved = pyqtSignal(object)
    onVocabularyAdded = pyqtSignal(object)
    onVocabularyRemoved = pyqtSignal(object)

    onScreenshotAdded = pyqtSignal(object)
    onAnnotationAdded = pyqtSignal(object)
    onSegmentAdded = pyqtSignal(object)

    onSelectionChanged = pyqtSignal(object, object)
    onProjectLoaded = pyqtSignal()
    onProjectChanged = pyqtSignal(object, object)

    def __init__(self, name = "NewProject", path = None, folder=None, movie_path = None):
        if path is None and name is None:
            raise ValueError("Either name or path has to be given to VIANProject.")
        elif name is None:
            name = os.path.split(path)[1].replace(VIAN_PROJECT_EXTENSION, "")

        if folder is None and path is not None:
            folder = os.path.split(path)[0]
        if folder is not None and path is None:
            path = os.path.join(folder, name + VIAN_PROJECT_EXTENSION)

        if folder is not None and not os.path.isdir(folder):
            if not os.path.isdir(os.path.split(folder)[0]):
                raise NotADirectoryError("The directory " + os.path.split(folder)[0] + " does not exist.")
            else:
                os.mkdir(folder)

        IClassifiable.__init__(self)
        QObject.__init__(self)
        self.undo_manager = UndoRedoManager()
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
        self.uuid = str(uuid4())
        self.id_list = dict()

        self.meta_data = dict()

        self.annotation_layers = []             # type: List[AnnotationLayer]
        self.current_annotation_layer = None    # type: AnnotationLayer
        self.screenshots = []                   # type: List[Screenshot]
        self.segmentation = []                  # type: List[Segmentation]
        self.main_segmentation_index = 0
        self.movie_descriptor = MovieDescriptor(project=self)
        self.analysis = []                      # type: List[AnalysisContainer]
        self.screenshot_groups = []             # type: List[ScreenshotGroup]
        self.vocabularies = []                  # type: List[Vocabulary]

        self.experiments = []                   # type: List[Experiment]

        self.current_script = None              # type: NodeScript
        self.node_scripts = []                  # type: List[NodeScript]
        self.create_script(dispatch=False)

        self.active_pipeline_script = None
        self.compute_pipeline_settings = dict(segments=False, screenshots=False, annotations=False)
        self.pipeline_scripts = []              # type: List[PipelineScript]

        self.add_screenshot_group("All Shots", initial=True)
        self.active_screenshot_group = self.screenshot_groups[0]
        self.active_screenshot_group.is_current = True

        self.active_classification_object = None
        # self.folder = path.split("/")[len(path.split("/")) - 1]
        self.notes = ""

        self.colormetry_analysis = None         # type: Union[ColormetryAnalysis|None]
        self.global_analyses = dict()

        self.hdf5_manager = None
        self.hdf5_indices_loaded = dict(curr_pos=dict(), uidmapping=dict())

        self.inhibit_dispatch = False
        self.selected = []
        self.segment_screenshot_mapping = dict()
        self.headless_mode = False

        self.project_lock = Lock()

        if movie_path is not None:
            if os.path.isfile(movie_path):
                self.movie_descriptor.set_movie_path(movie_path)
            else:
                raise FileNotFoundError("Could not open movie at: " + movie_path)

        if self.path is not None and self.folder is not None:
            self.sanitize_paths()
            self.create_file_structure()

    def get_type(self):
        return PROJECT

    def reset_file_paths(self, folder, file):
        self.path = file
        self.folder = folder
        root = self.folder

        self.data_dir = root + "/data"
        self.results_dir = root + "/results"
        self.shots_dir = root + "/shots"
        self.export_dir = root + "/export"
        self.hdf5_path = self.data_dir + "/analyses.hdf5"

    def create_file_structure(self):
        self.reset_file_paths(self.folder, self.path)
        if not os.path.isdir(self.data_dir):
            os.mkdir(self.data_dir)
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        if not os.path.isdir(self.shots_dir):
            os.mkdir(self.shots_dir)
        if not os.path.isdir(self.export_dir):
            os.mkdir(self.export_dir)

    def get_bake_path(self, entity, file_extension):
        directory = os.path.join(self.export_dir, "bake")
        if not os.path.isdir(directory):
            os.mkdir(directory)
        if isinstance(entity, str):
            return os.path.join(directory, entity + file_extension)
        else:
            return os.path.join(directory, str(entity.unique_id) + file_extension)

    def get_all_containers(self, types = None):
        result = []
        if types is None:
            for itm in self.id_list.values():
                result.append(itm)
        else:
            for itm in self.id_list.values():
                if itm.get_type() in types:
                    result.append(itm)
        return result

    def get_annotations(self):
        res = []
        for s in self.segmentation:
            res.extend(s.segments)
        for a in self.annotation_layers:
            res.extend(a.annotations)
        res.extend(self.screenshots)
        return res

    def print_all(self, type = None):
        for c in self.get_all_containers():
            if type is not None and type == c.get_type():
                print(str(c.unique_id).ljust(20), c)

    def sanitize_paths(self):
        """
        Makes sure that all paths are clean and do not contain any os specific forms using
        os.path.normpath()

        :return:None
        """
        self.path = os.path.normpath(self.path)
        self.name = os.path.normpath(self.name)
        self.folder = os.path.normpath(self.folder)
        self.data_dir = os.path.normpath(self.data_dir)
        self.results_dir = os.path.normpath(self.results_dir)
        self.shots_dir = os.path.normpath(self.shots_dir)
        self.export_dir = os.path.normpath(self.export_dir)
        self.movie_descriptor.movie_path = os.path.normpath(self.movie_descriptor.movie_path)

    def connect_hdf5(self) -> HDF5Manager:
        """
        Opens the project associated HDF5Manager.

        :return: a HDF5Manager instance
        """
        self.hdf5_manager = HDF5Manager()
        needs_init = self.hdf5_manager.set_path(self.hdf5_path)
        if needs_init:
            self.hdf5_manager.initialize_all()
        return self.hdf5_manager

    def set_active_classification_object(self, cl_obj:ClassificationObject) -> ClassificationObject:
        """
        Set the currently active (therefore in the gui visualized) classification object.

        :param cl_obj:
        :return: the given ClassificationObject instance
        """
        self.active_classification_object = cl_obj
        return cl_obj

    #region Segmentation
    def create_segmentation(self, name = None, dispatch = True, unique_id=-1) -> Segmentation:
        """
        Creates a new Segmentation with a given name.

        :param name: The name of the Segmentation.
        :param dispatch: If the creation should be signaled through the GUI
        :return: a new Segmentation instance.
        """
        s = Segmentation(name, unique_id=unique_id)
        self.add_segmentation(s, dispatch)
        return s

    def add_segmentation(self, segmentation:Segmentation, dispatch=True) -> Segmentation:
        """
        Adds a Segmentation instance to the project.

        :param segmentation: an instance of a Segmentation
        :param dispatch: If the creation should be signaled through the GUI
        :return: the segemntation instance added
        """
        self.segmentation.append(segmentation)
        segmentation.set_project(self)

        if dispatch:
            self.undo_manager.to_undo((self.add_segmentation, [segmentation]), (self.remove_segmentation, [segmentation]))
            self.dispatch_changed()
        self.onSegmentationAdded.emit(segmentation)
        return segmentation

    def copy_segmentation(self, segmentation:Segmentation) -> Segmentation:
        """
        Copies an existing Segmentation.

        :param segmentation: The Segmentation isntance to copy
        :return: a copy of the existing segmentation
        """
        new = self.create_segmentation(name = segmentation.name + "_Copy")

        for s in segmentation.segments:
            # segm = new.create_segment(start = s.get_start(), stop = s.get_end(), dispatch=False)
            segm = new.create_segment2(start = s.get_start(), stop = s.get_end(),
                                       dispatch=False, body=s.annotation_body,
                                       mode=SegmentCreationMode.INTERVAL)
            if segm is None:
                continue
            # segm.annotation_body = s.annotation_body

        self.undo_manager.to_undo((self.copy_segmentation, [segmentation]), (self.remove_segmentation, [new]))
        self.dispatch_changed(item = new)
        return segmentation

    def remove_segmentation(self, segmentation:Segmentation):
        """
        Removes a given segmentation from the project.

        :param segmentation: THe instance to be removed.
        :return: None
        """
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
        self.onSegmentationRemoved.emit(segmentation)
        self.dispatch_changed()

    def has_segmentation(self):
        """
        Checks if any segmentation is existend within the project.

        :return: True if a segmentation is present, else false.
        """
        if len(self.segmentation) > 0:
            return True
        return False

    def set_main_segmentation(self, segm:Segmentation) -> Segmentation:
        """
        Sets the current main segmentation.
        The main segmentation is used to sort the screenshots within the screenshot manager.

        :param segm: The segmentation instance to make as main segmentation
        :return: the given segmentation instance
        """
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
        return segm

    def get_main_segmentation(self) -> Segmentation:
        """
        Returns the main segmentation if any exists

        :return: The main segmentation if any exists, else returns None
        """
        if len(self.segmentation) > 0:
            return self.segmentation[self.main_segmentation_index]
            # return self.segmentation[0]
        else:
            return None

    def remove_segment(self, segment:Segment):
        """
        Removes a given segment instance from any segmentation it is in within the project.

        :param segment: the Segment instance to remove
        :return: None
        """
        for s in self.segmentation:
            if segment in s.segments:
                s.remove_segment(segment)
                break

    def get_segmentations(self) -> List[Segmentation]:
        """
        Returns a list of segmentations, the same as VIANProject.segmentation

        :return: A list of Segmentations
        """
        return self.segmentation

    def get_segment_of_main_segmentation(self, index) -> Segment:
        """
        Returns the segment of the Main Segmentation that is at index "index".
        Be aware, that the segment_id = <list_index> + 1. Since Segment IDS are counted from 1

        :param index: the index of the segment to choose within the main segmentation
        :return: a given Segment if exists, else returns None
        """
        # Main Segmentation can be None or index can be out of range
        try:
            return self.get_main_segmentation().segments[index]
        except Exception as e:
            return None
    # endregion

    # region Screenshots
    def create_screenshot(self, name, frame_pos = None, time_ms = None, unique_id=-1) -> Screenshot:
        """
        Creates a Screenshot within the project.
        Either frame_pos or time_ms has to be given,
        if a time_ms is given, the frame pos is calculated internally into the frame position.

        :param name: The name of the new screenshot
        :param frame_pos: The frame position of the new screenshot
        :param time_ms: The time in milliseconds of the new screenshot
        :return: a new instance of Screenshot
        """
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

            new = Screenshot(name, frame, img_blend = None, timestamp=time_ms, frame_pos=frame_pos, unique_id=unique_id)
            self.add_screenshot(new)
            return new
        return None

    def create_screenshot_headless(self, name, frame_pos = None, time_ms = None, fps = 29.0):
        #TODO do we still need this?

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

    def add_screenshot(self, screenshot, group = 0) -> Screenshot:
        """
        Adds a screenshot instance to the project.

        :param screenshot: the instance to add
        :param group: the group
        :return: returns the given screenshot instance
        """
        self.screenshots.append(screenshot)
        screenshot.set_project(self)

        self.screenshot_groups[0].add_screenshots(screenshot)
        if group == 0 and self.active_screenshot_group is not None and self.active_screenshot_group is not self.screenshot_groups[0]:
            self.active_screenshot_group.add_screenshots(screenshot)

        self.sort_screenshots()
        self.undo_manager.to_undo((self.add_screenshot, [screenshot]),(self.remove_screenshot, [screenshot]))

        return screenshot

    def sort_screenshots(self):
        """
        Sorts the screenshot by their position within the media descriptor (movie).

        """
        self.segment_screenshot_mapping = dict()
        if self.get_main_segmentation():
            self.get_main_segmentation().update_segment_ids()
            self.screenshots.sort(key=lambda x: x.movie_timestamp, reverse=False)

            for grp in self.screenshot_groups:
                grp.screenshots.sort(key=lambda x: x.movie_timestamp, reverse=False)

            for s in self.screenshots:
                segment = s.update_scene_id(self.get_main_segmentation())
                if segment not in self.segment_screenshot_mapping:
                    self.segment_screenshot_mapping[segment] = []
                self.segment_screenshot_mapping[segment].append(s)

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
        """
        Removes a given screenshot from the project.

        :param screenshot: The screenshot instance to remove
        :return: None
        """
        if screenshot in self.screenshots:
            for grp in self.screenshot_groups:
                grp.remove_screenshots(screenshot)

            self.screenshots.remove(screenshot)
            self.remove_from_id_list(screenshot)
            self.sort_screenshots()
            self.undo_manager.to_undo((self.remove_screenshot, [screenshot]),(self.add_screenshot, [screenshot]))

    def get_screenshots(self) -> List[Screenshot]:
        """
        Returns all screenshots.
        Equivalent to VIANProject.screenshots

        :return: A list of screenshots
        """
        return self.screenshots

    def add_screenshot_group(self, name="New Screenshot Group", initial=False, group=None) -> ScreenshotGroup:
        """
        Creates a new screenshot group and adds it to the project.
        if a group is given, it is only added to the project.

        @TODO this should be refactored to a create_screenshot_group and add function_screenshot_group at some point.

        :param name: The name of the group
        :param initial: if the change should be dispatched to the main window.
        :param group: instance of a ScreenshotGroup, if given no group is created but the given is added to the project.

        :return: A screenshot group instance
        """
        if not group:
            grp = ScreenshotGroup(self, name)
        else:
            grp = group
        grp.set_project(self)
        self.screenshot_groups.append(grp)
        if not initial:
            self.dispatch_changed()
        self.onScreenshotGroupAdded.emit(grp)
        return grp

    def remove_screenshot_group(self, grp):
        """
        Removes a ScreenshotGroup instance from the project.

        :param grp: The instance to remove.
        :return: None
        """
        if grp is not self.screenshot_groups[0]:
            self.screenshot_groups.remove(grp)
            self.remove_from_id_list(grp)
            self.dispatch_changed()
            self.onScreenshotGroupRemoved.emit(grp)

    def get_screenshots_of_segment(self, segment: Segment) -> List[Screenshot]:
        """
        Returns all screenshots which are within a segment.

        :param main_segm_id: The id of the segment do retrieve the screenshots from.

        :param segmentation:
        :return:
        """
        result = []
        start = segment.get_start()
        end = segment.get_end()

        for s in self.screenshots:
            if start <= s.movie_timestamp < end:
                result.append(s)

        return result

    def set_current_screenshot_group(self, grp) -> ScreenshotGroup:
        """
        Sets the current screenshot group within the project.
        This is only for GUI visualization.

        :param grp: The ScreenshotGroup instance to be set
        :return: the given ScreenshotGroup
        """
        self.active_screenshot_group.is_current = False
        self.active_screenshot_group = grp
        grp.is_current = True
        self.dispatch_changed()
        return grp

    # def get_active_screenshots(self):
    #     return self.active_screenshot_group.screenshots
    #endregion

    #region Analysis
    # def create_node_analysis(self, name, result, script_id, final_node_ids):
    #     analysis = NodeScriptAnalysis(name, result, script_id, final_node_ids)
    #     self.add_analysis(analysis)
    #     return analysis

    def add_analysis(self, analysis:AnalysisContainer, dispatch = False) -> AnalysisContainer:
        """
        Adds an AnalysisContainer instance to the project.

        :param analysis: The AnalysisContainer instance to add.
        :param dispatch: if the main window should be informed.
        :return: The AnalysisContainer instance given.
        """

        analysis.set_project(self)
        self.analysis.append(analysis)

        # if the analysis has no target, it is global, thus we have to check such an analysis has
        # already been created before and replace it if so.
        if isinstance(analysis, IAnalysisJobAnalysis) and analysis.target_container is None:
            if analysis.analysis_job_class in self.global_analyses:
                self.remove_analysis(self.global_analyses[analysis.analysis_job_class])
                self.global_analyses.pop(analysis.analysis_job_class)
            self.global_analyses[analysis.analysis_job_class] = analysis

        self.undo_manager.to_undo((self.add_analysis, [analysis]), (self.remove_analysis, [analysis]))

        if dispatch:
            self.dispatch_changed()

        self.onAnalysisAdded.emit(analysis)
        return analysis

    def remove_analysis(self, analysis:AnalysisContainer):
        """
        Removes a given analysis from the project.

        :param analysis: The AnalysisContainer instance to remove.
        :return: None
        """
        if analysis in self.analysis:
            self.analysis.remove(analysis)

            if isinstance(analysis, IAnalysisJobAnalysis):
                analysis.cleanup()

            self.remove_from_id_list(analysis)
            self.undo_manager.to_undo((self.remove_analysis, [analysis]), (self.add_analysis, [analysis]))
            self.dispatch_changed()

            self.onAnalysisRemoved.emit(analysis)

    def get_job_analyses(self) -> List[IAnalysisJobAnalysis]:
        """
        Returns a list of all IAnalysisJobAnalysis derived instances within the project.
        @TODO this is obsolete and should be refactored.

        :return: a list of IAnalysisJobAnalysis instances within the project.
        """
        result = []
        for a in self.analysis:
            if isinstance(a, IAnalysisJobAnalysis):
                result.append(a)
        return result

    # def has_analysis(self, class_name):
    #     for a in self.analysis:
    #         if isinstance(a, IAnalysisJobAnalysis):
    #             if a.analysis_job_class == class_name:
    #                 return True
    #     return False

    def get_colormetry(self):
        """
        Checks if a colorimetry exists and if it has already been computed to the end of the movie.

        :return: If a colorimetry exists, it returns tuple (colorimetry_has_finished, ColorimetryAnalysis instance)
        else it returns (False, None)
        """
        if self.colormetry_analysis is None:
            return False, None
        else:
            return self.colormetry_analysis.has_finished, self.colormetry_analysis

    def create_colormetry(self, resolution=30) -> ColormetryAnalysis:
        """
        Creates a new colorimetry and adds the instance to the project.

        :return: The ColormetryAnalysis instance created.
        """
        print("Create Colorimetry Analysis, ", resolution)
        colormetry = ColormetryAnalysis(resolution=resolution)
        self.add_analysis(colormetry)
        self.colormetry_analysis = colormetry
        # self.colormetry_analysis.clear()
        return colormetry

    #endregion

    # Getters for easier changes later in the project
    def set_selected(self,sender, selected = None):
        """
        Sets the current selected containers within the project.

        :param sender: The widget who sent the selection
        :param selected: A list of IProjectContainer
        :return:
        """

        # if self.selected is None:
        #     self.selected = []

        for t in self.selected:
            if not isinstance(t, VIANProject):
                t.onSelectedChanged.emit(False)


        if not isinstance(selected, list):
            selected = [selected]

        self.selected = selected

        # Setting the current annotation layer
        l = None
        for s in selected:
            if s is None:
                continue

            if s.get_type() == ANNOTATION_LAYER:
                l = s
            if s.get_type() == NODE_SCRIPT:
                self.set_current_script(s)
            if hasattr(s, "onSelectedChanged"):
                s.onSelectedChanged.emit(True)

        if l is not None:
            self.current_annotation_layer = l

        self.dispatch_selected(sender)

    def add_selected(self, sel):
        if sel not in self.selected:
            self.selected.append(sel)
            self.dispatch_selected(None)

    def remove_selected(self, sel):
        if sel in self.selected:
            self.selected.remove(sel)
            self.dispatch_selected(None)

    def get_selected(self, types = None) -> List[IProjectContainer]:
        """
        Returns all currently selected containers.

        :param types: if a type is given the result is filtered.
        :return: List[IProjectContainer]
        """
        result = []
        if types != None:
            for s in self.selected:
                if s.get_type() in types:
                    result.append(s)
            return result
        else:
            return self.selected

    def get_movie(self):
        """
        Equivalent to VIANProject.movie_descriptor.

        :return: Returns the movie descriptor of a project.
        """
        return self.movie_descriptor

    #region Annotations
    def create_annotation_layer(self, name, t_start = 0, t_stop = 0, unique_id=-1) -> AnnotationLayer:
        """
        Creates a new AnnotationLayer instance and returns it.

        :param name: The name of the layer
        :param t_start: time of the start in milliseconds
        :param t_stop: time of the end in milliseconds
        :return: AnnotationLayer instance
        """
        layer = AnnotationLayer(name, t_start, t_stop, unique_id=unique_id)
        self.add_annotation_layer(layer)
        return layer

    def add_annotation_layer(self, layer) -> AnnotationLayer:
        """
        Adds an AnnotationLayer instance to the project.

        :param layer: The AnnotationLayer instance to add.
        :return: AnnotationLayer instance given.
        """
        layer.set_project(self)
        self.annotation_layers.append(layer)
        self.current_annotation_layer = layer

        self.undo_manager.to_undo((self.add_annotation_layer, [layer]),
                                  (self.remove_annotation_layer, [layer]))

        self.onAnnotationLayerAdded.emit(layer)
        self.dispatch_changed()
        return layer

    def remove_annotation_layer(self, layer):
        """
        Removes a given AnnotationLayer instance from the project.

        :param layer: The AnnotationLayer instance to remove.
        :return: None
        """
        if layer is self.current_annotation_layer:
            self.current_annotation_layer = None

        self.selected = None

        for a in layer.annotations:
            layer.remove_annotation(a)
        self.annotation_layers.remove(layer)

        if len(self.annotation_layers) > 0:
            self.current_annotation_layer = self.annotation_layers[0]

        self.remove_from_id_list(layer)
        self.onAnnotationLayerRemoved.emit(layer)
        self.dispatch_changed()

    def remove_annotation(self, annotation):
        """
        Removes an annotation from any annotation layer it belongs to.

        :param annotation: Annotation instance to remove.
        :return: None
        """
        for l in self.annotation_layers:
            l.remove_annotation(annotation)

    def get_annotation_layers(self):
        """
        Returns all annotation layers in the project.
        Equivalent to VIANProject.annotation_layers.

        :return:
        """
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

    #region Python Scripts
    # def create_pipeline_script(self, name:str, author="no_author", path = None, script = None, unique_id=-1) -> PipelineScript:
    #     """
    #     Creates a new PipelineScript given a name and a script content
    #     :param name: The name of the script
    #     :param script: The actual python script text
    #     :return: a PipelineScript class
    #     """
    #     pipeline_script = PipelineScript(name, author, path=path, script=script, unique_id=unique_id)
    #     return self.add_pipeline_script(pipeline_script)
    #
    # def add_pipeline_script(self, script:PipelineScript) -> PipelineScript:
    #     """
    #     Adds a script at a given path to the project.
    #
    #     :param path: Path to the pipeline python script.
    #     :return: None
    #     """
    #     for s in self.pipeline_scripts:
    #         if s.name == script.name and s.script == script.script:
    #             return s
    #
    #     self.pipeline_scripts.append(script)
    #     script.set_project(self)
    #     return script
    #
    # def remove_pipeline_script(self, script:PipelineScript):
    #     """
    #     Removes a given script path from the project.
    #
    #     :param path: The path to remove.
    #     :return: None
    #     """
    #
    #     if script in self.pipeline_scripts:
    #         self.pipeline_scripts.remove(script)

    def get_missing_analyses(self, requirements, segments = None, screenshots=None, annotations = None):
        # requirements = script.pipeline_type.requirements
        result = dict()
        if segments is None:
            segments = []
            for s in self.segmentation:
                segments.extend(s.segments)
        if screenshots is None:
            screenshots = self.screenshots

        if annotations is None:
            annotations = []
            for l in self.annotation_layers:
                annotations.extend(l.annotations)

        if "segment_analyses" in requirements:
            result["segment_analyses"] = self._get_missing_analyses_for_container(
                segments, requirements["segment_analyses"]
            )
        if "screenshot_analyses" in requirements:
            result["screenshot_analyses"] = self._get_missing_analyses_for_container(
                screenshots, requirements["screenshot_analyses"]
            )

        if "annotation_analyses" in requirements:
            result["annotation_analyses"] = self._get_missing_analyses_for_container(
                annotations, requirements["annotation_analyses"]
            )
        return result

    def _get_missing_analyses_for_container(self, containers, requirements):
        missing_analyses = dict()
        n_analyses = len(containers) * len(requirements)
        n_analyses_done = 0

        for c in containers:
            for (analysis_name, class_obj_name, priority) in requirements:
                found = False

                for a in c.connected_analyses:
                    if a.target_classification_object is None:
                        continue
                    if a.analysis_job_class == analysis_name and a.target_classification_object.name == class_obj_name:
                        found = True
                        break
                if found:
                    n_analyses_done += 1
                else:
                    if priority not in missing_analyses:
                        missing_analyses[priority] = dict()
                    if analysis_name not in missing_analyses[priority]:
                        missing_analyses[priority][analysis_name] = dict()
                    if class_obj_name not in missing_analyses[priority][analysis_name]:
                        missing_analyses[priority][analysis_name][class_obj_name] = []
                    missing_analyses[priority][analysis_name][class_obj_name].append(c)

        return (missing_analyses, n_analyses, n_analyses_done)

    # def get_pipeline_script_by_uuid(self, uuid):
    #     for p in self.pipeline_scripts:
    #         if p.uuid == uuid:
    #             return p
    #     return None
    #endregion

    #region IO
    def store_project(self, path = None, return_dict = False, bake=False):
        """
        Stores the project json to the given filepath.
        if no path is given, the default path is used.

        :param settings:
        :param path:
        :param bake:
        :return:
        """
        project = self

        a_layer = []
        screenshots = []
        segmentations = []
        analyses = []
        screenshot_groups = []
        scripts = []
        experiments = []
        vocabularies = []

        for v in project.vocabularies:
            vocabularies.append(v.serialize())

        for a in project.annotation_layers:
            a_layer.append(a.serialize())

        for b in project.screenshots:
            src, img = b.serialize(bake=bake)
            screenshots.append(src)

        for c in project.segmentation:
            segmentations.append(c.serialize())

        for d in project.analysis:
            analyses.append(d.serialize(bake=bake))

        for e in project.screenshot_groups:
            screenshot_groups.append(e.serialize())

        for f in project.node_scripts:
            scripts.append(f.serialize())

        for g in project.experiments:
            experiments.append(g.serialize())

        if project.hdf5_manager is None:
            hdf_indices = self.hdf5_indices_loaded
        else:
            hdf_indices = project.hdf5_manager.get_indices()

        data = dict(
            path=project.path,
            name=project.name,
            corpus_id=project.corpus_id,
            uuid = project.uuid,
            annotation_layers=a_layer,
            notes=project.notes,
            main_segmentation_index=project.main_segmentation_index,
            screenshots=screenshots,
            segmentation=segmentations,
            analyses=analyses,
            movie_descriptor=project.movie_descriptor.serialize(),
            version=version.__version__,
            screenshot_groups=screenshot_groups,
            scripts=scripts,
            vocabularies=vocabularies,
            experiments=experiments,
            meta_data = project.meta_data,
            hdf_indices = hdf_indices,
        )

        if return_dict:
            return data
        else:
            if path is None:
                path = project.path
            path = path.replace(VIAN_PROJECT_EXTENSION, "")

            numpy_path = path + "_scr"
            project_path = path + ".eext"

            try:
                if bake:
                    with open(self.get_bake_path(self.name, ".json"), 'w') as f:
                        json.dump(data, f)
                else:
                    with open(project_path, 'w') as f:
                        json.dump(data, f)
            except Exception as e:
                print("Exception during Storing: ", str(e))
                raise e
        log_info("Project Stored to", path)

    def load_project(self, path=None, main_window = None, serialization = None):
        """
        Loads a project from a given file.

        :param settings:
        :param path:
        :return:
        """
        if path is not None:
            has_file = True
            if not VIAN_PROJECT_EXTENSION in path:
                path += VIAN_PROJECT_EXTENSION

            if not os.path.isfile(path):
                print("File not Found: ", path)
                return

            print("Reading From", os.path.abspath(path))
            with open(path) as f:
                my_dict = json.load(f)
        else:
            has_file = False
            my_dict = serialization

        self.path = my_dict['path']
        self.path = path
        self.name = my_dict['name']
        self.main_segmentation_index = my_dict['main_segmentation_index']

        if "uuid" in my_dict:
            self.uuid = my_dict['uuid']
        else:
            self.uuid = str(uuid4())

        if 'corpus_id' in my_dict:
            self.corpus_id = my_dict['corpus_id']

        if 'notes' in my_dict:
            self.notes = my_dict['notes']

        if 'meta_data' in my_dict:
            self.meta_data = my_dict['meta_data']

        if self.meta_data is None:
            self.meta_data = dict()

        if path is None and serialization is not None:
            path = "no-path" + VIAN_PROJECT_EXTENSION
        self.folder = os.path.split(path)[0] + "/"
        self.results_dir = self.folder + "/results/"
        self.export_dir = self.folder + "/export/"
        self.shots_dir = self.folder + "/shots/"
        self.data_dir = self.folder + "/data/"
        self.hdf5_path = self.data_dir + "analyses.hdf5"

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
            if main_window is not None:

                answer = QMessageBox.question(main_window, "Project Migration", "This Project seems to be older than 0.2.9.\n\n"
                                                            "VIAN uses a directory System since 0.2.10,\n "
                                                            "do you want to move the Project to the new System now?")
            else:
                answer = QMessageBox.Yes
            if answer == QMessageBox.Yes:
                try:
                    old_path = self.path

                    folder = QFileDialog.getExistingDirectory(caption="Select Directory to migrate the Project into")
                    self.folder = folder + "/" + self.name
                    self.path = self.folder + "/" + self.name
                    os.mkdir(self.folder)
                    self.create_file_structure()
                    copy2(old_path, self.path + VIAN_PROJECT_EXTENSION)

                except Exception as e:
                    print(e)
        # Check the FileStructure integrity anyway
        else:
            if has_file:
                self.create_file_structure()

        try:
            self.hdf5_indices_loaded = my_dict['hdf_indices']
        except Exception as e:
            print(e)
            pass
        if has_file:
            self.hdf5_manager = HDF5Manager()
            self.hdf5_manager.set_path(self.hdf5_path)
            try:
                self.hdf5_manager.set_indices(my_dict['hdf_indices'])
            except Exception as e:
                print("Exception during hdf5_manager.set_indices(): ", e)
                self.hdf5_manager.initialize_all()
        else:
            print("No HDF5 File")

        self.current_annotation_layer = None
        self.movie_descriptor = MovieDescriptor(project=self).deserialize(my_dict['movie_descriptor'])

        self.vocabularies = []
        for v in my_dict['vocabularies']:
            voc = Vocabulary("voc").deserialize(v, self)
            self.add_vocabulary(voc)

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
            # self.main_window.print_message("Loading Screenshot Group failed.", "Red")
            print("Loading Vocabulary failed", e)

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
            print("Loading Node Scripts failed", e)
            # self.main_window.print_message("Loading Node Scripts failed", "Red")
            # self.main_window.print_message(e, "Red")

        # try:
        #     [self.add_pipeline_script(PipelineScript().deserialize(q, self.folder)) for q in my_dict['pipeline_scripts']]
        #     self.active_pipeline_script = self.get_by_id(my_dict['active_pipeline_script'])
        #     self.compute_pipeline_settings = my_dict['compute_pipeline_settings']
        # except Exception as e:
        #     print("Exception in Load Pipelines", str(e))

        try:
            for e in my_dict['experiments']:
                new = Experiment().deserialize(e, self)
                self.add_experiment(new)

        except Exception as e:
            print("Exception in Load Experiment", e)

        # Renaming the old analyzes to analyses due to a typo
        analyses_fix = "analyses"
        if analyses_fix not in my_dict:
            analyses_fix = "analyzes"
        for d in my_dict[analyses_fix]:
            if d is not None:
                try:
                    t = deprecation_serialization(d, ['vian_serialization_type', 'analysis_container_class'])
                    new = eval(t)().deserialize(d, self)
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

        if self.colormetry_analysis is not None:
            if not self.hdf5_manager.has_colorimetry():
                self.colormetry_analysis.clear()
        else:
            self.create_colormetry()
        self.sort_screenshots()
        self.undo_manager.clear()

        if has_file:
            self.sanitize_paths()

        return self

    def get_template(self, segm = True, voc = True, ann = True, scripts = False, experiment = True, pipeline=True):
        """
        Returns a template dictionary from this projects.

        :param segm: If segmentation info should be included
        :param voc: If vocabulary info should be included
        :param ann: If annotation layer info should be included
        :param scripts: If node scripts info should be included
        :param experiment: If experiment info should be included
        :param pipeline: If pipeline info should be included
        :return: a dict to be serialized.
        """
        segmentations = []
        vocabularies = []
        layers = []
        node_scripts = []
        experiments = []
        pipelines = []

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

        active_pipeline = None
        if pipeline:
            for p in self.pipeline_scripts:
                pipelines.append(p.serialize())
            if self.active_pipeline_script is not None:
                active_pipeline = self.active_pipeline_script.unique_id

        template = dict(
            segmentations = segmentations,
            vocabularies = vocabularies,
            layers = layers,
            node_scripts=node_scripts,
            experiments = experiments,
            pipelines=pipelines,
            compute_pipeline_settings = self.compute_pipeline_settings,
            active_pipeline = active_pipeline
        )
        return template

    def apply_template(self, template_path = None, template = None, script_export=None, merge=True, merge_drop = False):
        """
        Loads a template from agiven path and applies it to the project.

        :param template_path: Path to the json
        :param template: a template dict as returned from VIANProject.get_template()
        :param export_scripts: If the PipelineScripts should be exported into a py file
        :param merge: if the new template should be merge into an already existing one
        :param merge_drop: if data which is not present in the new template during merge should be dropped
        :return: merge results, a list of printable string describing the merge changes,
        returns an empty list if merge has been false
        """
        merge_results = []
        log_info("Applying Template")
        if template is None and template_path is None:
            raise ValueError("Either template_path or template has to be given.")
        if template_path is not None and template is None:
            try:
                with open(template_path, "r") as f:
                    template = json.load(f)
            except Exception as e:
                print("Importing Template Failed", e)
                raise e
                return
        else:
            template = template

        for s in template['segmentations']:
            new = None
            if merge:
                new = self.get_by_id(s[1])

            if new is None:
                merge_results.append(("Created Segmentation", s))
                new = Segmentation(s[0])
                new.unique_id = s[1]
                self.add_segmentation(new)

        for v in template['vocabularies']:
            voc = Vocabulary("voc").deserialize(v, self)
            self.add_vocabulary(voc)

        for l in template['layers']:
            new = None
            if merge:
                new = self.get_by_id(l[1])

            if new is None:
                merge_results.append(("Created Annotation Layer", l))
                new = AnnotationLayer(l[0])
                new.unique_id = l[1]
                self.add_annotation_layer(new)

        for n in template['node_scripts']:
            new = NodeScript().deserialize(n, self)
            self.add_script(new)

        for e in template['experiments']:
            # If we want to merge the experiments, we need to create a temporary project, since Experiment relies on
            # the id introspection of a project (get_by_id())
            if merge:
                with VIANProject("Temp") as temp_propj:
                    for v in template['vocabularies']:
                        voc = Vocabulary("voc").deserialize(v, temp_propj)
                        temp_propj.add_vocabulary(voc)

                    new = Experiment().deserialize(e, temp_propj)
                    temp_propj.add_experiment(new)

                    exp = self.get_by_id(new.unique_id)
                    if exp is not None and isinstance(exp, Experiment):
                        merge_results.append(("Merged Experiment", exp.name))
                        t = merge_experiment(exp, new, drop=merge_drop)
                        merge_results.extend(t)
                    else:
                        new = Experiment().deserialize(e, self)
                        self.add_experiment(new)
                        merge_results.append(("Added Experiment", new.name))
            else:
                new = Experiment().deserialize(e, self)
                self.add_experiment(new)
        return merge_results

    def export(self, device, path):
        device.export(self, path)

    def import_(self, device, path):
        device.import_(self, path)

    def __enter__(self):
        if self.folder is not None:
            self.create_file_structure()
            self.connect_hdf5()
            self.store_project()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.hdf5_manager is not None:
            self.hdf5_manager.on_close()
    #endregion

    #region Vocabularies
    def create_vocabulary(self, name="New Vocabulary", unique_id=-1) -> Vocabulary:
        """
        Creates a new Vocabulary instance and adds it to the project.

        :param name: The name of the Vocabulary
        :return: Vocabulary instance created.
        """

        base = name
        counter = 0
        while name in [v.name for v in self.vocabularies]:
            counter += 1
            name = base + "_" + str(counter).zfill(2)

        voc = Vocabulary(name, unique_id=unique_id)
        self.add_vocabulary(voc)
        return voc

    def add_vocabulary(self, voc, dispatch = True) -> Vocabulary:
        """
        Adds a given vocabulary to the project.
        if the vocabulary is identical to a given vocabulary it is omited.

        :param voc: The Vocabulary instance to add
        :param dispatch:
        :return: Vocabulary added
        """
        not_ok = True
        counter = 0
        name = voc.name
        duplicate = None

        # while(not_ok):
        #     has_duplicate = False
        #     for v in self.vocabularies:
        #     #     if v.name == name:
        #     #         name = voc.name + "_" + str(counter).zfill(2)
        #     #         has_duplicate = True
        #     #         counter += 1
        #     #         duplicate = v
        #     #         break
        #     # if not has_duplicate:
        #     #     not_ok = False
        #     #     break
        #     # else:
        #         # If the Vocabulares are duplicates, we might want to replace the IDS in the Caller,
        #         # Therefore we create a replacement table
        #         x = [w.name for w in voc.words_plain]
        #         y = [w.name for w in duplicate.words_plain]
        #
        #         if set(x) == set(y):
        #             print("Vocabulary is duplicate")
        #             return duplicate

        voc.name = name
        voc.set_project(self)

        self.vocabularies.append(voc)

        if dispatch:
            self.dispatch_changed()

        self.onVocabularyAdded.emit(voc)

        return voc

    def remove_vocabulary(self, voc):
        """
        Removes a given vocabulary from the project and cleans up all references to it.

        :param voc:
        :return:
        """
        if voc in self.vocabularies:
            # We first need to remove the vocabulary from all classification objects
            # (it might be used for classification)

            clobjs = []
            [clobjs.extend(e.classification_objects) for e in self.experiments]
            for c in clobjs:
                c.remove_vocabulary(voc)

            # Remove it from the project
            self.vocabularies.remove(voc)
            self.remove_from_id_list(voc)
            self.onVocabularyRemoved.emit(voc)
        self.dispatch_changed()

    def copy_vocabulary(self, voc, add_to_global = True, replace_uuid = False):
        """
        Copies an existing Vocabulary

        :param voc: the Vocabulary to copy
        :param add_to_global: If True, the Copied Vocabualry is added to the Projects List
        :return: A Copy of an existing Vocabulary
        """
        self.inhibit_dispatch = True
        new = self.import_vocabulary(None, add_to_global, serialization=voc.serialize())

        if replace_uuid:
            new.uuid = str(uuid4())
            for w in new.words_plain:
                w.uuid = str(uuid4())
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

    def import_vocabulary(self, path, add_to_global = True, serialization = None, return_id_table = False) -> Vocabulary:
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
    def create_media_object(self, name, data, container: IHasMediaObject, unique_id=-1):
        """
        Creates a media object and adds it to the project.

        :param name: Name of the MediaObject
        :param data:
        :param container:
        :return:
        """
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
            new = FileMediaObject(fname, new_path, container, o_type, unique_id=unique_id)

        self.add_media_object(new, container)

    def add_media_object(self, media_object, container:IHasMediaObject, dispatch = True):
        media_object.set_project(self)
        container.add_media_object(media_object)
        self.dispatch_changed(item = container)

    #endregion

    #region Experiments

    def create_experiment(self, name="New Experiment", unique_id=-1) -> Experiment:
        """
        Creates a new Experiment instance to the project.
        :return: Experiment instance created
        """
        new = Experiment(name=name, unique_id=unique_id)
        self.add_experiment(new)
        return new
        pass

    def add_experiment(self, experiment) -> Experiment:
        """
        Adds an existing Experiment instance to the project.

        :param experiment: Experiment instance to add
        :return: Experiment instance added
        """
        names = [e.get_name() for e in self.experiments]

        c = 0
        while experiment.get_name() in names:
            experiment.name = "New Experiment_" + str(c).zfill(2)
            c += 1

        experiment.set_project(self)
        self.experiments.append(experiment)

        self.undo_manager.to_undo((self.add_experiment, [experiment]),
                                  (self.remove_experiment, [experiment]))
        self.onExperimentAdded.emit(experiment)
        self.dispatch_changed(item=experiment)

    def remove_experiment(self, experiment):
        """
        Removes an existing experiment instance from the project.

        :param experiment: Experiment instance to remove
        :return: None
        """
        if experiment in self.experiments:
            self.experiments.remove(experiment)
            self.remove_from_id_list(experiment)
            self.undo_manager.to_undo((self.remove_experiment, [experiment]),
                                      (self.add_experiment, [experiment]))
            self.onExperimentRemoved.emit(experiment)
            self.dispatch_changed()

    def get_classification_object_global(self, name) -> ClassificationObject:
        """
        Looks in all experiments if a specific classification object is present.
        If no experiment is present or no classification object with given name,
        the experiment and classification object is created.

        :return: a classification object
        """
        cl_obj = None
        for e in self.experiments:
            t = e.get_classification_object_by_name(name)
            if t is not None:
                cl_obj = t
                break
        if cl_obj is None:
            exp = self.create_experiment("Default Experiment")
            cl_obj = exp.create_class_object(name)

        return cl_obj

    def get_experiment_by_name(self, name):
        for e in self.experiments:
            if e.name == name:
                return e
        return None
    #endregion

    def cleanup(self):
        """
        Clean up the project, this includes the removal of all references annotation widgets.

        :return:
        """
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
        """
        Copies all analyses still relevant to a new HDF5 file.
        This is necessary since hdf5 files do not allow removal of single entries.

        :param analyses: Analyses to initialize.
        :return:
        """
        new_h5 = HDF5Manager()
        new_h5.set_path(self.data_dir + "/clean_temp.hdf5")
        new_h5.initialize_all(analyses)
        for a in self.analysis:
            try:
                if isinstance(a, SemanticSegmentationAnalysisContainer):
                    if a.a_class is None:
                        # a.a_class = self.main_window.eval_class(a.analysis_job_class)
                        a.a_class = get_analysis_by_name(a.analysis_job_class)
                    data, shape = a.a_class().to_hdf5(a.get_adata())
                    new_h5.dump(data, a.a_class().dataset_name, a.unique_id)
                elif isinstance(a, IAnalysisJobAnalysis):
                    if a.a_class is None:
                        # a.a_class = self.main_window.eval_class(a.analysis_job_class)
                        a.a_class = get_analysis_by_name(a.analysis_job_class)
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

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def create_unique_id(self):
        """
        Creates a new unique id for a given IProjectContainer within the project.
        This should not be used from the outside.

        :return: a unique id
        """
        is_unique = False
        item_id = 0
        while is_unique is False:
            # item_id = randint(1000000000, 9999999999)
            item_id = str(uuid4())
            if self.get_by_id(item_id) is None:
                is_unique = True

        return item_id

    def add_to_id_list(self, container_object, item_id):
        self.id_list[item_id] = container_object

    def remove_from_id_list(self, container_object):
        if container_object.unique_id in self.id_list:
            self.id_list.pop(container_object.unique_id)

    def clean_id_list(self):
        new = dict()
        for itm, val in self.id_list.items():
            if itm == val.unique_id:
                new[itm] = val
        self.id_list = new

    def get_by_id(self, item_id) -> IProjectContainer:
        """
        Returns an item given by its IProjectContainer.unique_id

        :param id: IProjectContainer.unique_id
        :return:
        """
        if item_id in self.id_list:
            return self.id_list[item_id]
        else:
            return None

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes

    def get_experiment(self, name) -> Experiment:
        """
        Get experiment by name.

        :param name: The name of the experiment.
        :return: the Experiment instance if any exists, else None
        """
        for exp in self.experiments:
            if exp.name == name:
                return exp
        return None
    #endregion

    #region Dispatchers
    def dispatch_changed(self, receiver = None, item = None):
        if self.inhibit_dispatch is False:
            self.onProjectChanged.emit(receiver, item)

    def dispatch_loaded(self):
        if self.inhibit_dispatch is False:
            self.onProjectLoaded.emit()

    def dispatch_selected(self, sender):
        if self.inhibit_dispatch is False:
            self.onSelectionChanged.emit(sender, self.selected)
    #endregion






