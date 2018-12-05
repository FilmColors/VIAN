from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from functools import partial
from visualizer2.presentation.vis_home_widget import *
from visualizer2.presentation.vis_movie_widget import *
from visualizer2.presentation.vis_screenshot_widget import *
from visualizer2.presentation.vis_search_widget import *
from visualizer2.presentation.vis_segment_widget import *
from visualizer2.widgets.header_bar import *
from core.corpus.shared.sqlalchemy_entities import *
from visualizer2.data.query_worker import QueryWorker, CORPUS_PATH
from visualizer2.data.screenshot_worker import ScreenshotWorker
from visualizer2.presentation.vis_favorites import VisFavoritesWindow
from visualizer2.presentation.screenshot_inspector import ScreenshotInspectorPopup

class VIANVisualizer(QMainWindow):
    onQuery = pyqtSignal(str, object, object, object, object, object, object)
    onSegmentsQuery = pyqtSignal()
    onKeywordsQuery = pyqtSignal()
    onProjectQuery = pyqtSignal(object)
    onCorpusQuery = pyqtSignal()
    onAbortAllWorker = pyqtSignal()
    onLoadScreenshots = pyqtSignal(object, bool)

    def __init__(self, parent = None, contributor=None):
        super(VIANVisualizer, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/VisMainWindow.ui")
        uic.loadUi(path, self)

        if not os.path.isfile(CORPUS_PATH):
            path = QFileDialog.getOpenFileName(self, filter="*.vian_corpus")[0]
            if not os.path.isfile(path):
                print("No Corpus File Selected")
                raise FileExistsError("No Corpus File Selected")
        else:
            path = CORPUS_PATH

        if not os.path.isfile(path.replace(".vian_corpus", ".vian_corpus_sql")):
            sql_path = "sqlite:///" + QFileDialog.getOpenFileName(self, filter="*.vian_corpus_sql")[0]
        else:
            sql_path = None
        self.query_worker = QueryWorker(path, contributor)
        self.query_worker.corpus.sql_path = sql_path

        # self.query_thread = QThread()
        # self.query_worker.moveToThread(self.query_thread)
        # self.query_thread.start()
        self.onQuery.connect(self.query_worker.on_query)
        self.onCorpusQuery.connect(self.query_worker.on_corpus_info)
        self.onProjectQuery.connect(self.query_worker.on_project_query)

        self.query_worker.signals.onQueryResult.connect(self.on_query_result)
        self.query_worker.signals.onStartQuery.connect(self.on_query_started)
        self.query_worker.signals.onFinishedQuery.connect(self.on_query_finished)

        # self.query_worker.initialize(contributor)

        self.screenshot_loader = ScreenshotWorker(self)
        self.screenshot_loader_thread = QThread()
        self.screenshot_loader.moveToThread(self.screenshot_loader_thread)
        self.screenshot_loader_thread.start()
        self.onLoadScreenshots.connect(self.screenshot_loader.on_load_screenshots)
        self.onAbortAllWorker.connect(self.screenshot_loader.abort)

        self.stbar = QStatusBar(self)
        self.stlabel = QLabel(self)
        self.stbar.addPermanentWidget(self.stlabel)
        self.setStatusBar(self.stbar)

        #region Layout
        self.center = QWidget(self)
        self.center.setLayout(QVBoxLayout())
        self.setCentralWidget(self.center)

        self.stack = QStackedWidget()
        self.vis_favorites = VisFavoritesWindow(self, self)

        self.header = VisHeaderBar(self.center, self)
        self.header.onShowPlots.connect(self.show_favorites)
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
        self.actionFavorites.triggered.connect(self.show_favorites)
        self.actionPreferences.triggered.connect(self.on_preferences)
        #endregion


        self.query_worker.signals.onCorpusQueryResult.connect(self.home_widget.on_corpus_result)

        self.last_views = []
        self.connected = False
        self.show()
        self.db_root = None


        self.K = 10000
        self.K_IMAGES = 300
        self.MAX_WIDTH = 500

        self.classification_object_filter_indices = dict()
        # This is set during startup in the vis_search_widget #TUPLE (kwd, voc, cl_obj, word)
        self.all_keywords = dict()
        self.onCorpusQuery.emit()
        # self.on_query("projects")
        # self.on_query("keywords")

    @pyqtSlot(str)
    def on_query_started(self, string):
        print("Querying, " + string)
        try:
            self.stlabel.setText("Querying, " + string)
            self.stlabel.setStyleSheet("QLabel{color: orange;}")
        except:
            pass

    @pyqtSlot(str)
    def on_query_finished(self, string):
        try:
            self.stlabel.setText("Finished, " + string)
            self.stlabel.setStyleSheet("QLabel{color: green;}")
        except:
            pass

    @pyqtSlot(object)
    def on_project_selected(self, dbproject):
        # self.onProjectQuery.emit(dbproject)
        self.movie_widget.set_project(dbproject)
        # self.on_query("movie_info", project_filters = [dbproject.project_id])
        self.set_current_perspective(2)

    @pyqtSlot(object)
    def on_segment_selected(self, dbsegment:DBSegment):
        self.on_query("segments", segment_filters=[dbsegment.segment_id])
        self.set_current_perspective(4)

    def set_current_perspective(self, index):
        # HOME
        self.last_views.append(self.stack.currentIndex())

        if index == 0:
            self.header.show()
            self.stack.setCurrentIndex(0)
            self.header.set_header_name("Home")
        # Query
        elif index == 1:
            self.header.hide()
            self.stack.setCurrentIndex(1)
            self.header.set_header_name("Query")
        # Movie
        elif index == 2:
            self.header.show()
            self.stack.setCurrentIndex(2)
            self.header.set_header_name("Movie")

        # Screenshots
        elif index == 3:
            self.header.show()
            self.stack.setCurrentIndex(3)
            self.header.set_header_name("Screenshots")
        # Segments
        elif index == 4:
            self.header.show()
            self.stack.setCurrentIndex(4)
            self.header.set_header_name("Segments")

    def show_favorites(self):
        self.vis_favorites.show()

    def on_last_view(self):
        """
        Sets the current view to the last we have switched from
        :return: 
        """
        if len(self.last_views) > 0:
            self.stack.setCurrentIndex(self.last_views.pop())

    def on_query(self, query_type, filter_filmography=None, filter_keywords=None, filter_classification_objects=None, project_filters = None, segment_filters = None, shot_id = None):
        self.onQuery.emit(query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters, shot_id)

    def on_corpus_info_result(self, projects, keywords:List[DBUniqueKeyword]):
        cl_objs = []
        for k in keywords:
            cl_objs.append(k.classification_object)

        for cl in cl_objs:
            self.classification_object_filter_indices[cl.name] = cl.classification_object_id


    @pyqtSlot(object)
    def on_query_result(self, obj):
        pass

    def on_load_screenshots(self, db_shots, callback, by_segment=True):
        self.screenshot_loader.signals.onScreenshotLoaded.connect(callback)
        self.onLoadScreenshots.emit(db_shots, by_segment)

    def on_screenshot_inspector(self, db_screenshot:DBScreenshot):
        print(self.db_root + db_screenshot.file_path)
        img = cv2.imread(self.db_root + db_screenshot.file_path)
        screenshot_inspector = ScreenshotInspectorPopup(self, db_screenshot, img, None, self.classification_object_filter_indices)
        screenshot_inspector.show()

    def on_preferences(self):
        dialog = VisualizerPreferences(self)
        dialog.show()

class VisualizerPreferences(QDialog):
    def __init__(self, visualizer):
        super(VisualizerPreferences, self).__init__(visualizer)
        path = os.path.abspath("qt_ui/visualizer/VisPreferences.ui")
        uic.loadUi(path, self)
        self.visualizer = visualizer
        self.spinBox_KSegments.setValue(self.visualizer.K)
        self.spinBox_KImages.setValue(self.visualizer.K_IMAGES)
        self.spinBox_ImageWidth.setValue(self.visualizer.MAX_WIDTH)

        self.btn_OK.clicked.connect(self.on_values_changed)
        self.btn_Cancel.clicked.connect(self.close)

    def on_values_changed(self):
        self.visualizer.K = self.spinBox_KSegments.value()
        self.visualizer.K_IMAGES = self.spinBox_KImages.value()
        self.visualizer.MAX_WIDTH = self.spinBox_ImageWidth.value()
        self.close()


