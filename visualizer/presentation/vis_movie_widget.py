from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from core.visualization.image_plots import ImagePlotTime
from visualizer.presentation.presentation_widget import *
from core.visualization.graph_plots import VocabularyGraph
from core.visualization.feature_plot import GenericFeaturePlot
class VisMovieLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisMovieLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisMovieLayout.ui")
        self.plot_color_dt = ImagePlotTime(self)
        self.plot_network = VocabularyGraph(self)
        self.plot_features = GenericFeaturePlot(self)
        self.vbox_Upper.addWidget(self.plot_color_dt)
        self.vbox_LowerRight.addWidget(self.plot_network)
        self.vbox_LowerLeft.addWidget(self.plot_features)
