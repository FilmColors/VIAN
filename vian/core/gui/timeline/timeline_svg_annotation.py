from PyQt5.QtCore import pyqtSignal
from vian.core.gui.timeline.timeline_base import TimelineControl, TimelineBar, TimebarSlice


class TimelineAnnotationLayerControl(TimelineControl):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, item = None, name = "No Name"):
        super(TimelineAnnotationLayerControl, self).__init__(parent, timeline, item, name)
        self.layer = item

    def add_group(self, annotation):
        super(TimelineAnnotationLayerControl, self).add_group(annotation)
        # self.group_height = (self.height() - self.timeline.group_height) / np.clip(len(self.groups), 1, None)


class TimelineAnnotationBar(TimelineBar):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, annotation, height = 45):
        super(TimelineAnnotationBar, self).__init__(parent, timeline, control, height)
        self.annotation = annotation
        self.add_slice(annotation)

    def add_slice(self, item):
        slice = TimebarAnnotationSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        item.onQueryHighlightChanged.connect(slice.set_query_highlighted)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice


class TimebarAnnotationSlice(TimebarSlice):
    def __init__(self, parent:TimelineAnnotationBar, item, timeline):
        super(TimebarAnnotationSlice, self).__init__(parent, item, timeline, color = (133, 42, 42, 100))
