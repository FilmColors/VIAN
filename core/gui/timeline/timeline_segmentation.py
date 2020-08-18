from PyQt5.QtCore import pyqtSlot
from core.gui.timeline.timeline_base import TimelineControl, TimelineBar, TimebarSlice

from core.analysis.color.average_color import ColorFeatureAnalysis
from core.container.project import *

class TimelineSegmentationControl(TimelineControl):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, item=None, name="No Name"):
        super(TimelineSegmentationControl, self).__init__(parent, timeline, item, name)
        self.segmentation = item


class TimelineSegmentationBar(TimelineBar):
    onHeightChanged = pyqtSignal(int)

    def __init__(self, parent, timeline, control, segmentation, height = 45):
        super(TimelineSegmentationBar, self).__init__(parent, timeline, control, height)
        self.segmentation = segmentation
        self.segmentation.onSegmentDeleted.connect(self.remove_slice)
        self.segmentation.onSegmentAdded.connect(self.add_slice)

    def add_slice(self, item):
        slice = TimebarSegmentationSlice(self, item, self.timeline)
        self.onHeightChanged.connect(slice.on_height_changed)
        item.onQueryHighlightChanged.connect(slice.set_query_highlighted)
        slice.move(int(round(item.get_start() / self.timeline.scale,0)), 0)
        slice.resize(int(round((item.get_end() - item.get_start()) / self.timeline.scale, 0)), self.height())
        self.slices.append(slice)
        self.slices_index[item.get_id()] = slice


class TimebarSegmentationSlice(TimebarSlice):
    def __init__(self, parent:TimelineSegmentationBar, item:Segment, timeline):
        super(TimebarSegmentationSlice, self).__init__(parent, item, timeline, color = (54,146,182, 100))
        self.default_color = (54, 146, 182, 100)
        self.col_selected = (54, 146, 182, 200)
        self.col_hovered = (54, 146, 182, 240)
        item.onSegmentChanged.connect(self.update_text)
        item.onAnalysisAdded.connect(self.set_color)
        item.onAnnotationsChanged.connect(self.update_text)

        self.set_color(None)

    @pyqtSlot(object)
    def set_color(self, analysis):
        color_analysis = self.item.get_connected_analysis(ColorFeatureAnalysis, None)
        try:
            if len(color_analysis) > 0 and self.timeline.use_color_features is True:
                color_analysis = color_analysis[0]
                data = color_analysis.get_adata()['color_bgr']
                self.color = (data[2], data[1], data[0], 100)
            else:
                self.color = self.default_color
        except:
            self.color = self.default_color