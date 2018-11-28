import cv2
import numpy as np

from core.data.enums import SCREENSHOT, SCREENSHOT_GROUP
from core.data.interfaces import IProjectContainer, IHasName, ITimeRange, ISelectable, ITimelineItem, IClassifiable
from core.data.computation import numpy_to_qt_image, apply_mask
from core.container.analysis import SemanticSegmentationAnalysisContainer

from PyQt5.QtCore import pyqtSignal
import datetime

CACHE_WIDTH = 250

class Screenshot(IProjectContainer, IHasName, ITimeRange, ISelectable, ITimelineItem, IClassifiable):
    """
    :var title: The Name of this Screenshot
    :var img_movie: Image Data of the complete frame
    :var img_blend: Image Data of the Annotated Frame if Any
    :var annotation_item_ids: The Annotations that have been there while rendering the img_blend
    :var frame_pos: THe Position of this Frame in Frames
    :var scene_id: The Id of this Screenshot within the Main Segmentation of the Project
    :var shot_id_global: The Id of this screenshot over all Screenshots
    :var shot_id_segm: The Id of this shot within the segment
    :var movie_timestamp: The Time in MS
    :var creation_timestamp: The Time of Creation in time.now() format
    :var screenshot_group: The Screenshot Groupd this is asociated to
    :var notes: Additional Notes set in the Inspector
    :var curr_size: The size of the loaded Image relative to it's original Size
    """
    onScreenshotChanged = pyqtSignal(object)
    onImageSet = pyqtSignal(object)

    def __init__(self, title = "", image = None,
                 img_blend = None, timestamp = "", scene_id = 0, frame_pos = 0,
                 shot_id_global = -1, shot_id_segm = -1, annotation_item_ids = None):
        IProjectContainer.__init__(self)
        IClassifiable.__init__(self)
        self.title = title
        self.img_movie = None
        self.set_img_movie(image)
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

        self.preview_cache = None
        self.curr_size = 1.0

        self.hdf5_cache = dict()

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

    def set_title(self, title):
        self.title = title
        self.onScreenshotChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_scene_id(self, scene_id):
        self.scene_id = scene_id
        self.onScreenshotChanged.emit(self)

    def set_shot_id_global(self, global_id):
        self.shot_id_global = global_id
        self.onScreenshotChanged.emit(self)

    def set_shot_id_segm(self, segm_id):
        self.shot_id_segm = segm_id
        self.onScreenshotChanged.emit(self)

    def set_notes(self, notes):
        self.project.undo_manager.to_undo((self.set_notes, [notes]),
                                          (self.set_notes, [self.notes]))
        self.notes = notes
        self.onScreenshotChanged.emit(self)
        self.dispatch_on_changed(item=self)

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
        """
        Returns a resized tuple (qimage, qpixmap) from the movie-image. 
        THe Preview will be cached for fast updated
        :param scale: 
        :return: 
        """
        if (self.preview_cache is None or self.preview_cache[0] != scale) and self.img_movie.shape[0] > 100:
            self.preview_cache = (scale, numpy_to_qt_image(cv2.resize(self.img_movie, None, None, scale, scale, cv2.INTER_CUBIC)))
            return self.preview_cache[1]
        else:
            return numpy_to_qt_image(cv2.resize(self.img_movie, None, None, scale, scale, cv2.INTER_CUBIC))

    def get_img_movie(self, ignore_cl_obj = False):
        # If the CL obje should be igrnoer there is none or it has no semantic-segmentation:
        if ignore_cl_obj or self.project.active_classification_object is None or self.project.active_classification_object.semantic_segmentation_labels[0] == "":
            return self.img_movie
        else:
            clobj = self.project.active_classification_object
            cached = self.project.main_window.hdf5_cache.get_screenshot(clobj.get_id(), self.unique_id)
            if cached is None:
                a = self.get_semantic_segmentations(clobj.semantic_segmentation_labels[0])
                lbls = clobj.semantic_segmentation_labels[1]
                if len(clobj.semantic_segmentation_labels[0]) == len(lbls):
                    return self.img_movie
                if a is not None:
                    mask = a.get_adata()
                    masked = apply_mask(self.img_movie, mask, lbls)
                    h = CACHE_WIDTH / masked.shape[0] * masked.shape[1]
                    masked = cv2.resize(masked, (int(h), CACHE_WIDTH), interpolation=cv2.INTER_CUBIC)
                    self.project.main_window.hdf5_cache.dump_screenshot(clobj.get_id(), self.unique_id, masked)
                    return apply_mask(self.img_movie, mask, lbls)
            else:
                return cached
        return self.img_movie

    def set_img_movie(self, img):
        self.img_movie = img
        self.onImageSet.emit(self)

    def get_semantic_segmentations(self, dataset=None):
        """
        Returns a dict {dataset_name: SemanticSegmentationAnalysisContainer}
        :return: 
        """
        if dataset is not None:
            for d in self.connected_analyses:
                if isinstance(d, SemanticSegmentationAnalysisContainer):
                    if d.dataset == dataset:
                        return d
            return None
        else:
            result = dict()
            for d in self.connected_analyses:
                if isinstance(d, SemanticSegmentationAnalysisContainer):
                    result[d.dataset] = d
            return result

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_title, [name]),
                                          (self.set_title, [self.title]))
        self.title = name
        self.onScreenshotChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def update_scene_id(self, segmentation):
        segment = segmentation.get_segment(self.movie_timestamp)
        if segment is not None:
            self.scene_id = segment.ID

    def serialize(self):
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
        )


        # images = [self.img_movie.astype(np.uint8)]
        images = None
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

        # try:
        #     for w in serialization["words"]:
        #         word = self.project.get_by_id(w)
        #         if word is not None:
        #             self.add_word(self.project.get_by_id(w))
        #
        # except Exception as e:
        #     pass

        return self

    def get_type(self):
        return SCREENSHOT

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.onScreenshotChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def delete(self):
        self.project.remove_screenshot(self)

    def get_parent_container(self):
        return self.screenshot_group


class ScreenshotGroup(IProjectContainer, IHasName, ISelectable):
    onScreenshotGroupDeleted = pyqtSignal(object)
    onScreenshotAdded = pyqtSignal(object)
    onScreenshotRemoved = pyqtSignal(object)
    onScreenshotGroupChanged = pyqtSignal(object)

    def __init__(self, project, name = "New Screenshot Group"):
        IProjectContainer.__init__(self)
        self.set_project(project)
        self.name = name
        self.screenshots = []
        self.notes = ""
        self.is_current = False
        self.strip_height = -1

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        for s in self.screenshots:
            s.screenshot_group = self.name
        self.onScreenshotGroupChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def add_screenshots(self, shots):
        if not isinstance(shots, list):
            shots = [shots]
        for s in shots:
            self.screenshots.append(s)
            s.screenshot_group = self.get_name()
            self.onScreenshotAdded.emit(s)
        # self.dispatch_on_changed(item=self)

    def remove_screenshots(self, shots):
        if not isinstance(shots, list):
            shots = [shots]
        for s in shots:
            if s in self.screenshots:
                self.screenshots.remove(s)
                self.onScreenshotRemoved.emit(s)

    def get_type(self):
        return SCREENSHOT_GROUP

    def serialize(self):
        shot_ids = []
        for s in self.screenshots:
            shot_ids.append(s.get_id())

        data = dict(
            name=self.name,
            unique_id = self.unique_id,
            shots = shot_ids,
        )
        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        try:
            self.unique_id = serialization['unique_id']
        except:
            pass

        for s in serialization['shots']:
            shot = self.project.get_by_id(s)
            shot.screenshot_group = self.name
            self.screenshots.append(shot)

        # try:
        #     for w in serialization["words"]:
        #         word = self.project.get_by_id(w)
        #         if word is not None:
        #             self.add_word(self.project.get_by_id(w))
        #
        # except Exception as e:
        #     pass

        return self

    def delete(self):
        self.project.remove_screenshot_group(self)
        self.onScreenshotGroupDeleted.emit(self)

