import cv2
import sys
import numpy as np

from vian.core.data.enums import SCREENSHOT, SCREENSHOT_GROUP
from .container_interfaces import BaseProjectEntity, IHasName, ITimeRange, ISelectable, ITimelineItem, IClassifiable, \
    deprecation_serialization
from vian.core.data.computation import numpy_to_qt_image, apply_mask, numpy_to_pixmap
from .analysis import SemanticSegmentationAnalysisContainer
from .annotation_body import Annotatable
from PyQt5.QtCore import pyqtSignal
import datetime
from vian.core.data.computation import resize_with_aspect

CACHE_WIDTH = 250


class Screenshot(BaseProjectEntity, IHasName, ITimeRange, ISelectable, ITimelineItem, IClassifiable, Annotatable):
    """
    :var title: The name of this Screenshot
    :var frame_pos: The Position of this Frame in Frames
    :var movie_timestamp: The Time in MS
    :var creation_timestamp: The Time of Creation in time.now() format
    :var screenshot_group: The ScreenshotGroup this is associated to

    :var scene_id: The Index of this Screenshot within the Main Segmentation of the Project
    :var shot_id_global: The Index of this screenshot over all Screenshots
    :var shot_id_segm: The Index of this shot within the segment

    :var notes: Additional Notes set in the Inspector

    Application Variables:

    :var img_movie: Image Data of the complete frame
    :var img_blend: Image Data of the Annotated Frame if Any
    :var annotation_item_ids: The Annotations that have been there while rendering the img_blend
    :var curr_size: The size of the loaded Image relative to it's original Size
    """

    # TODO Refactor title > name
    # TODO Refactor movie-timestamp > start_ms

    onScreenshotChanged = pyqtSignal(object)
    onImageSet = pyqtSignal(object, object, object)  # Screenshot, ndarray, QPixmap

    def __init__(self, title="", image=None,
                 img_blend=None, timestamp="", scene_id=0, frame_pos=0, display_width = None, display_height = None,
                 shot_id_global=-1, shot_id_segm=-1, annotation_item_ids=None, unique_id=-1):

        BaseProjectEntity.__init__(self, unique_id=unique_id)
        IClassifiable.__init__(self)
        Annotatable.__init__(self)

        self.title = title

        self.display_width = display_width
        self.display_height = display_height

        self.img_movie = None
        self.set_img_movie(image)

        # TODO this is related to containers.Annotations and no longer of any use,
        #  it contained the rendered svg over the image
        self.img_blend = img_blend
        self.annotation_item_ids = annotation_item_ids
        self.frame_pos = frame_pos
        self.scene_id = scene_id
        self.shot_id_global = shot_id_global
        self.shot_id_segm = shot_id_segm
        self.movie_timestamp = timestamp
        self.creation_timestamp = str(datetime.datetime.now())
        self.screenshot_group = None
        self.notes = ""
        self.annotation_is_visible = False
        self.timeline_visibility = True

        self.preview_cache = None
        self.curr_size = 1.0

        self.masked_cache = dict()

    def set_title(self, title):
        self.title = title
        self.onScreenshotChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_project(self, project):
        super(Screenshot, self).set_project(project)
        self.display_width = self.project.movie_descriptor.display_width
        self.display_height = self.project.movie_descriptor.display_height

    def set_annotation_visibility(self, visibility):
        self.annotation_is_visible = visibility

    def get_start(self):
        return self.movie_timestamp

    def get_end(self):
        return self.movie_timestamp

    def get_name(self):
        return self.title

    def resize(self, scale=1.0):
        streamed = self.project.streamer.from_stream(self.unique_id)
        self.img_movie = cv2.resize(streamed['img_movie'], None, None, scale, scale, cv2.INTER_CUBIC)
        try:
            self.img_blend = cv2.resize(streamed['img_blend'], None, None, scale, scale, cv2.INTER_CUBIC)
        except:
            self.img_blend = np.zeros_like(self.img_movie)

    def get_preview(self, scale=0.2):
        """
        Returns a resized tuple (qimage, qpixmap) from the movie-image. 
        THe Preview will be cached for fast updated
        :param scale: 
        :return: 
        """
        if self.preview_cache is None and self.img_movie.shape[0] > 100:
            self.preview_cache = numpy_to_qt_image(self.img_movie)
        if self.preview_cache is None:
            return numpy_to_qt_image(self.img_movie)
        return self.preview_cache

    def set_classification_object(self, clobj, recompute=False, hdf5_cache=None):
        if not recompute and clobj.unique_id in self.masked_cache:
            result = self.masked_cache[clobj.unique_id]
        elif clobj is None or clobj.semantic_segmentation_labels[0] == "":
            result = self.img_movie
        else:
            result = None
            cached = hdf5_cache.get_screenshot(clobj.get_id(), self.unique_id)
            if cached is None:
                a = self.get_semantic_segmentations(clobj.semantic_segmentation_labels[0])
                lbls = clobj.semantic_segmentation_labels[1]
                if len(clobj.semantic_segmentation_labels[0]) == len(lbls):
                    result = self.img_movie
                if a is not None:
                    mask = a.get_adata()
                    masked = apply_mask(self.img_movie, mask, lbls)
                    h = CACHE_WIDTH / masked.shape[0] * masked.shape[1]
                    masked = cv2.resize(masked, (int(h), CACHE_WIDTH), interpolation=cv2.INTER_CUBIC)
                    hdf5_cache.dump_screenshot(clobj.get_id(), self.unique_id, masked)
                    result = masked
            else:
                result = cached
        if result is not None:
            self.masked_cache[clobj.unique_id] = result
            self.onImageSet.emit(self, result, numpy_to_pixmap(result, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True))
        return result

    def get_img_movie(self, ignore_cl_obj=False):
        if not ignore_cl_obj:
            try:
                return self.masked_cache[self.project.active_classification_object.unique_id]
            except:
                return self.img_movie
        else:
            return self.img_movie

    def set_img_movie(self, img):
        if img is None:
            self.img_movie = None
            return

        if self.project is not None and self.project.headless_mode:
            return

        # Resize the image to the correct display aspect
        if self.display_width is not None and self.display_height is not None:
            img = cv2.resize(img, (self.display_width, self.display_height),
                                        interpolation=cv2.INTER_CUBIC)

        # Resize the image to the CACHE_WIDTH (250px wide)
        self.img_movie = resize_with_aspect(img, width = CACHE_WIDTH)

        if self.receivers(self.onImageSet) > 0:
            if img.shape[2] == 3:
                self.onImageSet.emit(self, self.img_movie, numpy_to_pixmap(img))
            elif img.shape[2] == 4:
                self.onImageSet.emit(self, self.img_movie, numpy_to_pixmap(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True))

    def get_img_movie_orig_size(self):
        """
        Returns the screenshots image data in the original size.
        :return:
        """

        cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_pos)

        ret, frame = cap.read()
        frame = cv2.resize(frame, (self.display_width, self.display_height), interpolation=cv2.INTER_CUBIC)
        cap.release()
        return frame

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
        segment = segmentation.get_segment_of_time(self.movie_timestamp)
        if segment is not None:
            self.scene_id = segment.ID
        return segment

    def serialize(self, bake=False):
        result = dict(
            name=self.title,
            unique_id=self.unique_id,
            annotation_item_ids=self.annotation_item_ids,
            frame_pos=self.frame_pos,

            start_ms=self.movie_timestamp,
            end_ms=self.movie_timestamp,

            creation_timestamp=self.creation_timestamp,
            notes=self.notes,

            vian_webapp_scene_id=self.scene_id,
            vian_webapp_shot_id_global=self.shot_id_global,
            vian_webapp_shot_id_segm=self.shot_id_segm,

        )

        if bake:
            img = resize_with_aspect(self.get_img_movie_orig_size(), width=750)
            result['bake_path'] = self.project.get_bake_path(self, ".jpg")
            cv2.imwrite(result['bake_path'], img)
        # images = [self.img_movie.astype(np.uint8)]
        images = None
        return result, images

    def deserialize(self, serialization, project):
        self.project = project

        self.title = deprecation_serialization(serialization, ['name', 'title'])

        self.unique_id = serialization['unique_id']
        self.movie_timestamp = deprecation_serialization(serialization, ['start_ms', 'movie_timestamp'])

        self.creation_timestamp = serialization['creation_timestamp']
        self.annotation_item_ids = serialization['annotation_item_ids']

        self.notes = serialization['notes']
        self.frame_pos = serialization['frame_pos']

        self.img_movie = np.zeros(shape=(30, 50, 3), dtype=np.uint8)
        self.img_blend = None

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

    def load_screenshots(self, cap: cv2.VideoCapture = None):
        if cap is None:
            cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_pos)
        ret, frame = cap.read()
        self.set_img_movie(frame)


class ScreenshotGroup(BaseProjectEntity, IHasName, ISelectable):
    """
    :var name: The name of the ScreenshotGroup
    :var screenshots: A list of Screenshots
    :var notes: Additional Notes set in the Inspector

    """
    onScreenshotGroupDeleted = pyqtSignal(object)
    onScreenshotAdded = pyqtSignal(object)
    onScreenshotRemoved = pyqtSignal(object)
    onScreenshotGroupChanged = pyqtSignal(object)

    def __init__(self, project, name="New Screenshot Group", unique_id=-1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
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
            s.screenshot_group = self
        self.onScreenshotGroupChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def add_screenshots(self, shots):
        if not isinstance(shots, list):
            shots = [shots]
        for s in shots:
            self.screenshots.append(s)
            s.screenshot_group = self
            self.onScreenshotAdded.emit(s)
            self.project.onScreenshotAdded.emit(s)
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
            unique_id=self.unique_id,
            shots=shot_ids,
        )
        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']

        self.unique_id = serialization['unique_id']

        for s in serialization['shots']:
            shot = self.project.get_by_id(s)
            shot.screenshot_group = self
            self.screenshots.append(shot)

        return self

    def delete(self):
        self.project.remove_screenshot_group(self)
        self.onScreenshotGroupDeleted.emit(self)
