from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from visualizer.presentation.vis_home_widget import *
from visualizer.presentation.vis_movie_widget import *
from visualizer.presentation.vis_screenshot_widget import *
from visualizer.presentation.vis_search_widget import *
from visualizer.presentation.vis_segment_widget import *
from visualizer.widgets.header_bar import *

class VIANVisualizer(QMainWindow):
    def __init__(self, parent = None):
        super(VIANVisualizer, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisMainWindow.ui")
        uic.loadUi(path, self)

        self.center = QWidget(self)
        self.center.setLayout(QVBoxLayout())
        self.setCentralWidget(self.center)

        self.stack = QStackedWidget()
        self.header = VisHeaderBar(self.center, self)

        self.home_widget = VisHomeWidget(self.stack, self)
        self.movie_widget = VisMovieLayout(self.stack, self)
        self.screenshot_widget = VisScreenshotLayout(self.stack, self)
        self.search_widget = VisSearchLayout(self.stack, self)
        self.segment_widget = VisSegmentLayout(self.stack, self)

        self.stack.addWidget(self.home_widget)
        self.stack.addWidget(self.movie_widget)
        self.stack.addWidget(self.screenshot_widget)
        self.stack.addWidget(self.search_widget)
        self.stack.addWidget(self.segment_widget)

        self.center.layout().addWidget(self.header)
        self.center.layout().addWidget(self.stack)

        self.show()