from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from uuid import uuid4

from typing import List


class AnnotationBody(QObject):
    onAnnotationChanged = pyqtSignal(object)

    MIMETYPE_TEXT_PLAIN = "text/plain"
    MIMETYPE_TEXT_RICH = "text/rich"
    MIMETYPE_URL = "text/uri-list"
    MIMETYPE_BIBTEX = "application/x-bibtex"

    def __init__(self, content=None, mime_type=None, name = None):
        super(AnnotationBody, self).__init__()
        self.name = name
        self.unique_id = str(str(uuid4()))
        self.content = content

        if mime_type is None:
            mime_type = self.MIMETYPE_TEXT_PLAIN
        self.mime_type = mime_type
        if self.name is None:
            self.name = self.mime_type

    def set_content(self, c):
        self.content = c
        self.onAnnotationChanged.emit(self)

    def set_mime_type(self, m):
        self.mime_type = m
        self.onAnnotationChanged.emit(self)

    def set_name(self, n):
        self.name = n
        self.onAnnotationChanged.emit(self)

    def from_string(self, s):
        self.content = s
        self.mime_type = self.MIMETYPE_TEXT_PLAIN
        return self

    def to_string(self):
        return str(self.content)

    def serialize(self):
        return dict(
            unique_id=self.unique_id,
            name= self.name,
            content=self.content,
            mime_type=self.mime_type
        )

    def deserialize(self, s):
        self.unique_id = s['unique_id']
        self.content = s['content']
        self.mime_type = s['mime_type']
        if 'name' in s:
            self.name = s['name']
        return self


class Annotatable:
    onAnnotationsChanged = pyqtSignal(object)

    def __init__(self):
        self._annotations = [] #type: List[AnnotationBody]

    def get_first_annotation_string(self, mime_type = None):
        if mime_type is None:
            q = self._annotations
        else:
            q = [a for a in self._annotations if a.mime_type == mime_type]

        if len(q) > 0:
            return q[0].to_string()
        else:
            return ""

    def serialize_annotations(self):
        return [s.serialize() for s in  self._annotations]

    def deserialize_annotations(self, t):
        for an in t:
            a = AnnotationBody().deserialize(an)
            self.add_annotation(a)
        return self._annotations

    def get_annotations(self, mime_type = None, name = None):
        if mime_type is None and name is None:
            return self._annotations
        elif name is not None:
            return [a for a in self._annotations if a.name == name]
        else:
            return [a for a in self._annotations if a.mime_type == mime_type]

    def add_annotation(self, a: AnnotationBody):
        self._annotations.append(a)
        a.onAnnotationChanged.connect(self._emit_change)
        a.onAnnotationChanged.emit(a)
        return a

    def remove_annotation(self, a: AnnotationBody):
        if a in self._annotations:
            self._annotations.remove(a)
        return a

    def deprecate_string_to_annotation(self, a, rt = ""):
        if not isinstance(a, list):
            annotations = [a]
        else:
            annotations = a

        ret = rt
        for a in annotations:
            if isinstance(a, str):
                if a != "":
                    ret = self.add_annotation(AnnotationBody().from_string(a))
            elif isinstance(a, AnnotationBody):
                ret = self.add_annotation(a)

        return ret

    def _emit_change(self):
        self.onAnnotationsChanged.emit(self)