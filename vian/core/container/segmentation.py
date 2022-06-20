import numpy as np

from vian.core.container.media_objects import FileMediaObject, DataMediaObject
from vian.core.data.enums import SegmentCreationMode, SEGMENTATION, MediaObjectType, SEGMENT
from vian.core.container.container_interfaces import BaseProjectEntity, IHasName, ISelectable, ITimelineItem, ILockable, \
    AutomatedTextSource, ITimeRange, IClassifiable, IHasMediaObject, deprecation_serialization
from vian.core.data.log import log_error
from PyQt6.QtCore import pyqtSignal
from .annotation_body import AnnotationBody, Annotatable


class Segmentation(BaseProjectEntity, IHasName, ISelectable, ITimelineItem, ILockable, AutomatedTextSource):
    """
    :var name: The Name of the Segmentation
    :var segments: A List of Segments
    :var notes: Additional Notes that can be added to describe it in the Inspector

    Application Variables

    :var timeline_visibility: if it is visible in the timeline or not
    :var is_main_segmentation: If this is the main Segmentation

    """
    onSegmentAdded = pyqtSignal(object)
    onSegmentDeleted = pyqtSignal(object)
    onSegmentationChanged = pyqtSignal(object)

    def __init__(self, name = None, segments = None, unique_id=-1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        ILockable.__init__(self)
        self.name = name

        if segments is None:
            segments = []

        self.segments = segments

        self.notes = ""
        self.is_main_segmentation = False

        # Timeline
        self.timeline_visibility = True
        self.strip_height = -1

        for s in self.segments:
            s.segmentation = self

    def get_segment_of_time(self, time_ms):
        """
        Returns a Segment containing the given time ms, if none exists returns None
        :param time_ms:
        :return:
        """
        for s in self.segments:
            if s.get_start() <= time_ms < s.get_end():
                return s
        return None

    def create_segment2(self, start, stop, mode:SegmentCreationMode = SegmentCreationMode.BACKWARD,
                        body = "",
                        dispatch  = True,
                        inhibit_overlap = True, minimal_length = 5, unique_id = -1):

        # If the Segment is smaller than the minimal_length, don't do anything
        if mode == SegmentCreationMode.BACKWARD:
            last = None
            for i, s in enumerate(self.segments):
                if s.start < start:
                    last = s
            if last is not None:
                start = last.end
            else:
                start = 0
        # Find the next Segment if there is one and
        # create a segment from position to the next segment or the movies end if none exists
        elif mode == SegmentCreationMode.FORWARD:
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
                stop = next.get_start()

            if last is not None and last.end > start:
                last.set_end(start)

        elif mode == SegmentCreationMode.INTERVAL:
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
                    stop = next.start

        if stop - start < minimal_length:
            log_error("Segment to small. SegmentSize:", stop - start, "MinimalSize:" ,minimal_length)
            return

        ID = len(self.segments) + 1
        new_seg = Segment(ID=ID,
                          start=start,
                          end=stop,
                          name=str(ID),
                          segmentation=self,
                          annotation_body=body,
                          unique_id=unique_id)
        new_seg.set_project(self.project)

        self.add_segment(new_seg, dispatch)
        return new_seg

    def add_segment(self, segment, dispatch = True):
        # Finding the Segments location
        if self.project is not None:
            segment.set_project(self.project)

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
            self.dispatch_on_changed(item=self)
        self.onSegmentAdded.emit(segment)
        self.project.onSegmentAdded.emit(segment)

    def remove_segment(self, segment, dispatch = True):
        import time
        t = time.time()
        self.segments.remove(segment)

        print("Remove Segment", time.time() - t)
        t = time.time()
        self.update_segment_ids()
        print("update_segment_ids Segment", time.time() - t)
        t = time.time()
        self.project.sort_screenshots()
        print("sort_screenshots Segment", time.time() - t)
        t = time.time()
        if dispatch:
            self.project.undo_manager.to_undo((self.remove_segment, [segment]), (self.add_segment, [segment]))
            self.dispatch_on_changed(item=self)
        print("dispatch_on_changed Segment", time.time() - t)

        self.onSegmentDeleted.emit(segment)

    def cut_segment(self, segm, time):
        """
        Cuts one segment at given time into two different segments

        :param segm: The Segment to cut
        :param time: the time to cut the segment (absolute)
        :return: None
        """
        if segm in self.segments:
            old_end = segm.get_end()
            segm.end = time
            # new = self.create_segment(time, old_end)
            new = self.create_segment2(time, old_end, mode=SegmentCreationMode.INTERVAL, dispatch=False)
            self.project.undo_manager.to_undo((self.cut_segment, [segm, time]), (self.merge_segments, [segm, new]))
            self.dispatch_on_changed(item=self)

    def merge_segments(self, a, b):
        """
        Merges two segments into one
        :param a: The first segment
        :param b: the second segment
        :return:
        """
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

            # segm = self.create_segment(start, end)
            segm = self.create_segment2(start, end, mode=SegmentCreationMode.INTERVAL, dispatch=False)
            segm.media_objects = media_objects
            self.project.undo_manager.to_undo((self.merge_segments, [a, b]), (self.cut_segment, [segm, cut_t]))
            self.dispatch_on_changed()

    def update_segment_ids(self):
        for i, s in enumerate(self.segments):
            s.ID = i + 1

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
        self.onSegmentationChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return self.name

    def serialize(self):
        s_segments = []
        for s in self.segments:
            s_segments.append(s.serialize())

        result = dict(
            name = self.name,
            unique_id = self.unique_id,
            segments = s_segments,
            notes = self.notes,
            locked = self.locked,
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

        if 'locked' in serialization:
            self.locked = serialization['locked']
        else:
            self.locked = False

        self.update_segment_ids()
        return self

    def get_type(self):
        return SEGMENTATION

    def lock(self):
        ILockable.lock(self)
        for s in self.segments:
            s.lock()
        self.onSegmentationChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def unlock(self):
        ILockable.unlock(self)
        for s in self.segments:
            s.unlock()
        self.onSegmentationChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.onSegmentationChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def set_project(self, project):
        BaseProjectEntity.set_project(self, project)
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
                return str(segm.get_annotations(AnnotationBody.MIMETYPE_TEXT_PLAIN))
            elif property_name == "Segment Name":
                return str(segm.get_name())
            else:
                return "Invalid Property"
        return ""

    def copy_event(self, target = None):
        """
        This Event is raised when the user wants to copy this container into some target. 
        :param containers: 
        :return: 
        """
        # TODO New AnnotationBody
        if target is None or target == self.project or target == self or not isinstance(target, Segmentation):
            new_seg = self.project.create_segmentation(self.name)
            for s in self.segments:
                new_seg.create_segment2(s.get_start(), s.get_end(), body=s.get_annotations())
        else:
            for s in self.segments:
                target.create_segment2(s.get_start(), s.get_end(), body=s.get_annotations())


class Segment(BaseProjectEntity, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable, IClassifiable, IHasMediaObject, Annotatable):
    """
    :var name: the Name of the Segment
    :var start: Time start in MS
    :var end: Time end in MS
    :var segmentation: it's parent Segmentation, which it is grouped in
    :var ID: The Segments Index within the Segmentation {0, ..., n}
    :var annotation_body: The AnnotationBody as string

    Application Variables:

    :var duration: The Duration of the Segment in MS
    :var timeline_visibility: If it is visible in the Timeline
    :var notes: Additional Notes that can be set in the Inspector

    """
    onSegmentChanged = pyqtSignal(object)

    def __init__(self, ID = None, start = 0, end  = 1000, segmentation=None,
                 annotation_body = "", name = "New Segment", unique_id = -1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        ILockable.__init__(self)
        IClassifiable.__init__(self)
        IHasMediaObject.__init__(self)
        Annotatable.__init__(self)

        self.MIN_SIZE = 10
        self.ID = ID

        # Ensure that start and end is not an nd.array
        self.start: int = max(0, start)
        self.end: int = int(end)
        self.name: str = name

        self.annotation_body = self.deprecate_string_to_annotation(annotation_body)

        self.timeline_visibility = True
        self.segmentation = segmentation
        self.notes = ""

    @property
    def duration(self):
        return self.end - self.start

    def set_id(self, ID):
        self.ID = ID
        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_start(self, start):
        if start > self.end - self.MIN_SIZE :
            start = self.end - self.MIN_SIZE
        self.project.undo_manager.to_undo((self.set_start, [start]), (self.set_start, [self.start]))
        self.start = start
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()

        # Since the region has changed, we delete the analysis
        self.delete_analyses()

        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_end(self, end):
        if end < self.start + self.MIN_SIZE :
            end = self.start + self.MIN_SIZE

        self.project.undo_manager.to_undo((self.set_end, [end]), (self.set_end, [self.end]))

        # Since the region has changed, we delete the analysis
        self.delete_analyses()

        self.end = end
        self.segmentation.update_segment_ids()
        self.project.sort_screenshots()
        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return np.clip(self.start, 0, None)

    def get_end(self):
        return np.clip(self.end, self.start + 1, None)

    def move(self, start, end, dispatch=True):
        self.project.undo_manager.to_undo((self.move, [start, end]), (self.move, [self.start, self.end]))
        self.start = start
        self.end = end

        # Since the region has changed, we delete the analysis
        self.delete_analyses()
        self.onSegmentChanged.emit(self)

        import time
        t = time.time()
        if dispatch:
            self.segmentation.update_segment_ids()
            self.project.sort_screenshots()
        self.dispatch_on_changed(item=self)

    def get_name(self):
        return str(self.name)

    def set_name(self, name):
        self.project.undo_manager.to_undo((self.set_name, [name]), (self.set_name, [self.name]))
        self.name = name
        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def set_annotation_body(self, annotation):
        self.project.undo_manager.to_undo((self.set_annotation_body, [annotation]), (self.set_annotation_body, [self.get_annotations()]))
        self.annotation_body = self.deprecate_string_to_annotation(annotation)
        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_annotation_body(self):
        t = self.get_annotations(AnnotationBody.MIMETYPE_TEXT_PLAIN)
        if len(t) > 0:
            return t[0].content
        else:
            return ""

    def serialize(self):

        media_objects = []
        for obj in self.media_objects:
            media_objects.append(obj.serialize())

        r = dict(
             scene_id = self.ID,
             unique_id = self.unique_id,
             start_ms = self.start,
             end_ms = self.end,

             name = self.name,
             # annotation_body = [AnnotationBody(content=self.annotation_body).serialize()],
             annotation_body = self.serialize_annotations(),
             notes = self.notes,
             locked = self.locked,
             media_objects = media_objects
        )
        return r

    def deserialize(self, serialization, project):
        self.project = project
        self.ID = serialization["scene_id"]
        self.unique_id = serialization['unique_id']

        self.start = deprecation_serialization(serialization, ["start_ms", "start"])
        self.end = deprecation_serialization(serialization, ["end_ms", "end"])

        # self.duration = self.end - self.start
        self.notes = serialization['notes']

        # Backwards Compatibility
        if 'name' in serialization:
            self.name = serialization['name']
        else:
            self.name = str(self.ID)

        if 'locked' in serialization:
            self.locked = serialization['locked']
        else:
            self.locked = False

        if 'annotation_body' in serialization:
            try:

                if isinstance(serialization['annotation_body'], str):
                    if serialization['annotation_body'] != "":
                        self.annotation_body = serialization['annotation_body']
                        self.add_annotation(AnnotationBody(serialization['annotation_body'], AnnotationBody.MIMETYPE_TEXT_PLAIN))
                    else:
                        self.annotation_body = ""

                elif isinstance(serialization['annotation_body'], dict):
                    ann = self.deserialize_annotations([serialization['annotation_body']])
                    self.annotation_body = self.get_first_annotation_string()
                else:
                    ann = self.deserialize_annotations(serialization['annotation_body'])
                    self.annotation_body = self.get_first_annotation_string()
            except Exception as e:
                log_error("Couldn't parse annotation body", e)
                self.annotation_body = ""
        else:
            self.annotation_body = ""


        try:
            for w in serialization["media_objects"]:
                o_type = w['dtype']
                if o_type in [MediaObjectType.HYPERLINK, MediaObjectType.SOURCE]:
                    new = DataMediaObject(None, None, self, None).deserialize(w)
                else:
                    new = FileMediaObject(None, None, self, None).deserialize(w)
                new.set_project(self.project)
                self.media_objects.append(new)
        except Exception as e:
            log_error(e)

        return self

    def get_type(self):
        return SEGMENT

    def set_timeline_visibility(self, visibility):
        self.timeline_visibility = visibility
        self.onSegmentChanged.emit(self)
        self.dispatch_on_changed(item=self)

    def get_timeline_visibility(self):
        return self.timeline_visibility

    def delete(self):
        self.segmentation.remove_segment(self)

    def get_parent_container(self):
        return self.segmentation

