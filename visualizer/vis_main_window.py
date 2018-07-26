from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from functools import partial
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

        #region Layout
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
        self.stack.addWidget(self.search_widget)
        self.stack.addWidget(self.movie_widget)
        self.stack.addWidget(self.screenshot_widget)
        self.stack.addWidget(self.segment_widget)

        self.center.layout().addWidget(self.header)
        self.center.layout().addWidget(self.stack)

        self.actionHome.triggered.connect(partial(self.set_layout, 0))
        self.actionQuery.triggered.connect(partial(self.set_layout, 1))
        self.actionMovie.triggered.connect(partial(self.set_layout, 2))
        self.actionScreenshots.triggered.connect(partial(self.set_layout, 3))
        self.actionSegments.triggered.connect(partial(self.set_layout, 4))
        #endregion

        self.connected = False
        self.show()

    def set_layout(self, index):
        print(index)
        # HOME
        if index == 0:
            self.header.show()
            self.stack.setCurrentIndex(0)
        elif index == 1:
            self.header.hide()
            self.stack.setCurrentIndex(1)
        elif index == 2:
            self.header.show()
            self.stack.setCurrentIndex(2)
        elif index == 3:
            self.header.show()
            self.stack.setCurrentIndex(3)
        elif index == 4:
            self.header.show()
            self.stack.setCurrentIndex(4)


