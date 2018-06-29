from core.container.media_objects import FileMediaObject, DataMediaObject
from core.data.enums import SegmentCreationMode, SEGMENTATION, MediaObjectType, SEGMENT
from core.data.interfaces import IProjectContainer, IHasName, ISelectable, ITimelineItem, ILockable, \
    AutomatedTextSource, ITimeRange, IClassifiable, IHasMediaObject


class Segmentation(IProjectContainer, IHasName, ISelectable, ITimelineItem, ILockable, AutomatedTextSource):
    """
    :var name: The Name of the Segmentation
    :var segments: A List of Segments
    :var timeline_visibility: if it is visible in the timeline or not
    :var notes: Additional Notes that can be added to describe it in the Inspector
    :var is_main_segmentation: If this is the main Segmentation

    """
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

    def get_segment_of_time(self, time_ms):
        for s in self.segments:
            if s.get_start() <= time_ms < s.get_end():
                return s
        return None

    # @OC
    # def create_segment(self, start, stop, ID = None, from_last_threshold = 1, forward_segmenting = False,
    #                    inhibit_overlap = True,  dispatch = True, annotation_body = ""):
    #     """
    #     Creates a new Segment
    #     :param start:
    #     :param stop:
    #     :param ID:
    #     :param from_last_threshold:
    #     :param forward_segmenting:
    #     :param inhibit_overlap:
    #     :param dispatch:
    #     :param annotation_body:
    #     :return:
    #     """
    #
    #     # Is the Segment longer than the minimal Threshold (in ms)?
    #     if stop - start < from_last_threshold:
    #
    #         # Forward Segmentation: Create a Segment from Position to next Segment or End
    #         # If the new overlaps with the last: shorten the last
    #         if forward_segmenting:
    #             # Find the next Segment if there is one and create a segment from start to the next segment start
    #
    #             next = None
    #             last = None
    #             for s in self.segments:
    #                 if s.start < start:
    #                     last = s
    #                 if s.start > start and next is None:
    #                     next = s
    #                 if last is not None and next is not None:
    #                     break
    #
    #             if next is None:
    #                 stop = self.project.movie_descriptor.duration
    #             else:
    #                 stop = next.get_start() - 1
    #
    #             if last is not None and last.end > start:
    #                 last.set_end(start - 1)
    #
    #         # Backwards Segmentation: Create a Segment from the Last to current Position
    #         else:
    #             last = None
    #             for i, s in enumerate(self.segments):
    #                 if s.start < start:
    #                     last = s
    #             if last is not None:
    #                 start = last.end
    #             else:
    #                 start = 0
    #
    #     if inhibit_overlap:
    #         last = None
    #         next = None
    #
    #         for i, s in enumerate(self.segments):
    #             if s.start < start:
    #                 last = s
    #                 if len(self.segments) > i + 1:
    #                     next = self.segments[i + 1]
    #                 else:
    #                     next = None
    #
    #         if last is not None and last.end > start:
    #             start = last.end
    #         if next is not None and next.start < stop:
    #             stop = next.start - 1
    #
    #     if ID is None:
    #         ID = len(self.segments) + 1
    #
    #     # IF the Segment is to small, we don't want to create it
    #     if start > stop - 100:
    #         return
    #
    #     # if the Segment does still overlap, we don't want to create it
    #     last = None
    #     next = None
    #     for i, s in enumerate(self.segments):
    #         if s.start < start:
    #             last = s
    #             if len(self.segments) > i + 1:
    #                 next = self.segments[i + 1]
    #             else:
    #                 next = None
    #
    #     if last is not None and last.end > start:
    #         return
    #     if next is not None and next.start < stop:
    #         return
    #
    #     new_seg = Segment(ID = ID, start = start, end = stop, name=str(ID),
    #                       segmentation = self, annotation_body=annotation_body)
    #     new_seg.set_project(self.project)
    #
    #     self.add_segment(new_seg, dispatch)
    #
    #     return new_seg


    # TODO repace old create_segment method

    def create_segment2(self, start, stop, mode:SegmentCreationMode = SegmentCreationMode.BACKWARD,
                        body = "",
                        dispatch  = True,
                        inhibit_overlap = True, minimal_length = 5):

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
            return

        ID = len(self.segments) + 1
        new_seg = Segment(ID=ID, start=start, end=stop, name=str(ID),
                          segmentation=self, annotation_body=body)
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
            self.dispatch_on_changed(item=self)

    def remove_segment(self, segment, dispatch = True):
        self.segments.remove(segment)

        self.update_segment_ids()
        self.project.sort_screenshots()
        if dispatch:
            self.project.undo_manager.to_undo((self.remove_segment, [segment]), (self.add_segment, [segment]))
            self.dispatch_on_changed(item=self)

    def cut_segment(self, segm, time):
        if segm in self.segments:
            old_end = segm.get_end()
            segm.end = time
            # new = self.create_segment(time, old_end)
            new = self.create_segment2(time, old_end, mode=SegmentCreationMode.INTERVAL, dispatch=False)
            self.project.undo_manager.to_undo((self.cut_segment, [segm, time]), (self.merge_segments, [segm, new]))
            self.dispatch_on_changed(item=self)

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

            # segm = self.create_segment(start, end)
            segm = self.create_segment2(start, end, mode=SegmentCreationMode.INTERVAL, dispatch=False)
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

        try:
            self.locked = serialization['locked']
        except:
            self.locked = False

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


class Segment(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable, IClassifiable, IHasMediaObject):
    """
    :var MIN_SIZE: The Shortest size in MS
    :var ID: The Segments ID in the Segmentation {0, ..., n}
    :var start: Time start in MS
    :var end: Time end in MS
    :var name: the Name of the Segment

    :var duration: The Duration of the Segment in MS
    :var annotation_body: The Annotation Content Text
    :var timeline_visibility: If it is visible in the Timeline
    :var segmentation: it's parent Timeline
    :var notes: Additional Notes that can be set in the Inspector

    """
    def __init__(self, ID = None, start = 0, end  = 1000, duration  = None, segmentation=None, annotation_body = "", name = "New Segment"):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IClassifiable.__init__(self)
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

        media_objects = []
        for obj in self.media_objects:
            media_objects.append(obj.serialize())

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
            for w in serialization["media_objects"]:
                o_type = w['dtype']
                if o_type in [MediaObjectType.HYPERLINK, MediaObjectType.SOURCE]:
                    new = DataMediaObject(None, None, self, None).deserialize(w)
                else:
                    new = FileMediaObject(None, None, self, None).deserialize(w)
                print(self.project)
                new.set_project(self.project)
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

    def get_parent_container(self):
        return self.segmentation
