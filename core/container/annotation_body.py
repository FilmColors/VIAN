from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from uuid import uuid4


class AnnotationBody(QObject):
    MIMETYPE_TEXT_PLAIN = "text/plain"
    MIMETYPE_TEXT_RICH = "text/rich"

    def __init__(self, content=None, mime_type=None):
        super(AnnotationBody, self).__init__()
        self.unique_id = str(str(uuid4()))
        self.content = content

        if mime_type is None:
            mime_type = self.MIMETYPE_TEXT_PLAIN
        self.mime_type = mime_type

    def serialize(self):
        return dict(
            unique_id=self.unique_id,
            content=self.content,
            mime_type=self.mime_type
        )

    def deserialize(self, s):
        self.unique_id = s['unique_id']
        self.content = s['content']
        self.mime_type = s['mime_type']
        return self


class Annotatable:
    def add_annotation(self, a: AnnotationBody):
        pass

    def remove_annotation(self, a: AnnotationBody):
        pass
