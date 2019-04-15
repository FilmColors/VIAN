import cv2
from PyQt5.QtCore import pyqtSignal
from core.data.computation import numpy_to_qt_image
from core.container.media_objects import FileMediaObject, DataMediaObject
from core.data.enums import AnnotationType, MediaObjectType, ANNOTATION, ANNOTATION_LAYER
from .container_interfaces import IProjectContainer, ITimeRange, IHasName, ISelectable, ILockable, IClassifiable, \
    IHasMediaObject, ITimelineItem


class Annotation(IProjectContainer, ITimeRange, IHasName, ISelectable, ILockable, IClassifiable, IHasMediaObject):
    """
    :ivar name: name
    :ivar a_type: An AnnotationType Enum value:  { Rectangle = 0, Ellipse = 1, Line = 2, Text = 3, Image = 4, FreeHand = 5 }
    :ivar t_start: The Start Time in MS
    :ivar size: The Rect Size In original space
    :ivar curr_size: The Rect Size in relative space to the currently displayed movie frame
    :ivar color: The Color of the Annotation
    :ivar orig_position: The Position in original space
    :ivar line_w: The Line thickness
    :ivar resource_path: Ressource Path if there should be one (Image Annotation)
    :ivar text: Text if any (TextAnnotation)
    :ivar font_size: Font Size if any (Text Annotation)
    :ivar font: FontFamily Name if any (Text Anntotation)
    :ivar has_key: If it is Keyed or not
    :ivar keys: A List of (Time, Position) Tuples
    :ivar free_hand_paths: A List of drawing Paths in form [path, color, width]
    :ivar notes: Additional notes set in the Inspector
    :ivar is_automated: If this Annotation content is driven by another variable
    :ivar automated_source: The Source object hat is used in driving this ones content
    :ivar automate_property: The Source object's property that is driving this ones content
    :ivar tracking: tracking
    :ivar annotation_layer: A Reference to it's parent Annotation Layer
    :ivar is_visible: If this is globaly visible or not
    :ivar widget: A Reference to it's widget in the DrawingOverlay
    :ivar image: An Image data if there is any (Image Annotation)

    """
    def __init__(self, a_type = None, size = None, color = (255,255,255), orig_position = (50,50), t_start = 0, t_end = -1,
                 name = "New Annotation", text = "" , line_w = 2 ,font_size = 10, resource_path = "", tracking="Static"):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)
        IClassifiable.__init__(self)
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
        self.dispatch_on_changed(item=self)

    def remove_keys(self):
        self.keys = []
        self.dispatch_on_changed(item=self)

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
                                          (self.set_position, [(self.orig_position[0], self.orig_position[1])]))
        self.orig_position = (qpoint.x(), qpoint.y())
        # self.dispatch_on_changed()

    def get_position(self):
        return (self.orig_position[0],self.orig_position[1])

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
        """
        Returns the annotations color as QColor
        :return: QColor(self.color)
        """
        if self.color is None:
            self.color = [255, 255, 255]
        return (self.color[0], self.color[1], self.color[2])

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
        media_objects = []
        for obj in self.media_objects:
            media_objects.append(obj.serialize())

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

        # try:
        #     for w in serialization["words"]:
        #         word = self.project.get_by_id(w)
        #         if word is not None:
        #             self.add_word(self.project.get_by_id(w))
        #
        # except Exception as e:
        #     pass

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
                    new = DataMediaObject(None, None, self, None).deserialize(w)
                else:
                    new = FileMediaObject(None, None, self, None).deserialize(w)
                new.set_project(self.project)
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
        try:
            img = cv2.imread(self.resource_path, -1)
            print("DONE")
            if img is not None:
                if img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                qimage, qpixmap = numpy_to_qt_image(img, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True)
                self.image = qimage
        except Exception as e:
            print(e)

    def delete(self):
        self.annotation_layer.remove_annotation(self)

    def get_parent_container(self):
        return self.annotation_layer


class AnnotationLayer(IProjectContainer, ITimeRange, IHasName, ISelectable, ITimelineItem, ILockable):
    """
    Member Variables:
    :var name: The Name of this Annotation Layer
    :var t_start: Start Time in MS
    :var t_end: End Time in MS
    :var annotations: A List of Annotations
    :var is_current_layer: If this is the current layer to edit
    :var is_visible: if this layer is currently visible or hidden
    :var timeline_visibility: If the layer should be shown in the Timeline or not
    :var notes: Additional notes set in the Inspector

    """
    onAnnotationAdded = pyqtSignal(object)
    onAnnotationRemoved = pyqtSignal(object)
    onAnnotationLayerChanged = pyqtSignal(object)

    def __init__(self, name = None, t_start = 0, t_end = 0):
        IProjectContainer.__init__(self)
        ILockable.__init__(self)

        self.name = name
        self.t_start = t_start
        self.t_end = t_end
        self.annotations = []
        self.is_current_layer = False
        self.is_visible = True
        self.timeline_visibility = True
        self.notes = ""
        self.strip_height = -1

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
        self.dispatch_on_changed(item=self)
        self.onAnnotationAdded.emit(annotation)
        self.project.onAnnotationAdded.emit(annotation)

    def remove_annotation(self, annotation):
        if annotation in self.annotations:
            annotation.widget.close()
            self.annotations.remove(annotation)
            self.project.undo_manager.to_undo((self.remove_annotation, [annotation]),
                                              (self.add_annotation, [annotation]))
            self.dispatch_on_changed(item=self)
            self.onAnnotationRemoved.emit(annotation)

    def set_is_current_layer(self, bool):
        self.is_current_layer = bool

    def serialize(self):
        s_annotations = []
        for a in self.annotations:
            s_annotations.append(a.serialize())

        result = dict(
            name = self.name,
            unique_id=self.unique_id,
            t_start = self.t_start,
            t_end = self.t_end,
            is_current_layer = self.is_current_layer,
            annotations = s_annotations,
            notes = self.notes,
            locked=self.locked,
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

        # try:
        #     for w in serialization["words"]:
        #         word = self.project.get_by_id(w)
        #         if word is not None:
        #             self.add_word(self.project.get_by_id(w))
        #
        # except Exception as e:
        #     pass

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
