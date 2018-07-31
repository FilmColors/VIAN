from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from core.visualization.image_plots import *
from visualizer.presentation.presentation_widget import *

class VisSegmentLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSegmentLayout, self).__init__(parent, visualizer)#, "qt_ui/visualizer/VisSegmentsLayout.ui")
        self.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Vertical, self)
        self.layout().addWidget(self.vsplit)
        self.upper_widget = QSplitter(self)
        self.lower_widget = QSplitter(self)
        # self.lower_right = QSplitter(self.lower_widget)
        # self.lower_left = QSplitter(self.lower_widget)
        # self.lower_widget.addWidget(self.lower_left)
        # self.lower_widget.addWidget(self.lower_right)

        self.plot_la_space = ImagePlotPlane(self)
        self.plot_ab_space = ImagePlotCircular(self)

        self.upper_widget.addWidget(VisualizerVisualization(self, self.plot_la_space, self.plot_ab_space.get_param_widget()))
        self.upper_widget.addWidget(VisualizerVisualization(self, self.plot_ab_space, self.plot_ab_space.get_param_widget()))

        self.vsplit.addWidget(self.upper_widget)
        self.vsplit.addWidget(self.lower_widget)

    @pyqtSlot(object)
    def on_screenshot_loaded(self, scr):
        pass
        # self.screenshots[scr['screenshot_id']][1] = scr['image']

    def clear(self):
        pass

    def on_query_result(self, obj):
        if obj['type'] == "segments":
            self.clear()
