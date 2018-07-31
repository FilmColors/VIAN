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
from visualizer.data.query_worker import QueryWorker
from visualizer.data.screenshot_worker import ScreenshotWorker

class VIANVisualizer(QMainWindow):
    onQuery = pyqtSignal(str, object, object, object, object)
    onLoadScreenshots = pyqtSignal(object)

    def __init__(self, parent = None):
        super(VIANVisualizer, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisMainWindow.ui")
        uic.loadUi(path, self)

        self.query_worker = QueryWorker()
        self.query_thread = QThread()
        self.query_worker.moveToThread(self.query_thread)
        self.query_thread.start()
        self.onQuery.connect(self.query_worker.on_query)

        self.screenshot_loader = ScreenshotWorker()
        self.screenshot_loader_thread = QThread()
        self.screenshot_loader.moveToThread(self.screenshot_loader_thread)
        self.screenshot_loader_thread.start()
        self.onLoadScreenshots.connect(self.screenshot_loader.on_load_screenshots)


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

        self.actionHome.triggered.connect(partial(self.set_current_perspective, 0))
        self.actionQuery.triggered.connect(partial(self.set_current_perspective, 1))
        self.actionMovie.triggered.connect(partial(self.set_current_perspective, 2))
        self.actionScreenshots.triggered.connect(partial(self.set_current_perspective, 3))
        self.actionSegments.triggered.connect(partial(self.set_current_perspective, 4))
        self.actionLast.triggered.connect(self.on_last_view)
        #endregion

        self.last_views = []
        self.connected = False
        self.show()
        self.db_root = None

        # This is set during startup in the vis_search_widget #TUPLE (kwd, voc, cl_obj, word)
        self.all_keywords = dict()
        self.on_query("projects")
        self.on_query("keywords")

    @pyqtSlot(object)
    def on_project_selected(self, dbproject):
        self.on_query("movie_info", project_filters = [dbproject.project_id])
        self.set_current_perspective(2)

    def set_current_perspective(self, index):
        # HOME
        self.last_views.append(self.stack.currentIndex())

        if index == 0:
            self.header.show()
            self.stack.setCurrentIndex(0)
        # Query
        elif index == 1:
            self.header.hide()
            self.stack.setCurrentIndex(1)
        # Movie
        elif index == 2:
            self.header.show()
            self.stack.setCurrentIndex(2)
        # Screenshots
        elif index == 3:
            self.header.show()
            self.stack.setCurrentIndex(3)
        # Segments
        elif index == 4:
            self.header.show()
            self.stack.setCurrentIndex(4)

    def on_last_view(self):
        """
        Sets the current view to the last we have switched from
        :return: 
        """
        if len(self.last_views) > 0:
            self.stack.setCurrentIndex(self.last_views.pop())

    def on_query(self, query_type, filter_filmography=None, filter_keywords=None, filter_classification_objects=None, project_filters = None):
        self.onQuery.emit(query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters)

    def on_load_screenshots(self, db_shots, callback):
        self.screenshot_loader.signals.onScreenshotLoaded.connect(callback)
        self.onLoadScreenshots.emit(db_shots)