from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
import pickle
from collections import namedtuple
import numpy as np
from typing import List
from functools import partial
from glob import glob
import cv2
import json
from sys import stdout
from random import shuffle

from extensions.plugins.fiwi_tools.fiwi_visualizer.movie_list import *
from extensions.plugins.fiwi_tools.fiwi_visualizer.query_dock import *
from extensions.plugins.fiwi_tools.fiwi_visualizer.filmcolors_db import *
from core.visualization.graph_plots import *

from core.data.plugin import *
from core.concurrent.worker import SimpleWorker
from core.data.computation import create_icon

#region -- Definitions --
VOC_PATH = "C:\\Users\\Gaudenz Halter\\Desktop\\Glossar_DB_exp_11022018_2.CSV"
ROOT_FILE_EXT = "*.vian_db"
DATABASE_FILE_EXT = "*.db"

MODE_MOVIE = 0
MODE_CORPUS = 1

class FiwiVisualizerExtension(GAPlugin):
    def __init__(self, main_window):
        super(FiwiVisualizerExtension, self).__init__(main_window)
        self.plugin_name = "FIWI Database Visualizer"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = FiwiVisualizer(parent, self)
        wnd.show()


class FiwiVisualizer(QMainWindow):
    onImagePosScaleChanged = pyqtSignal(float)
    onCurrentCorpusChanged = pyqtSignal(object)
    onCorporasChange = pyqtSignal(object)
    onModeChanged = pyqtSignal(int)

    def __init__(self, parent, plugin: GAPlugin):
        super(FiwiVisualizer, self).__init__(parent)
        path = os.path.abspath("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/WindowFiwiDatabase.ui")
        uic.loadUi(path, self)

        self.plugin = plugin
        self.actionOpen_Database.triggered.connect(partial(self.on_load_database, None, None))
        self.actionCorpus_Manager.triggered.connect(self.create_movie_list)

        self.database = FilmColorsDatabase()
        self.database_file = None

        self.all_movies = []
        self.root_dir = None
        self.node_matrix = None

        self.corporas = []
        self.current_corpora = None
        self.current_segments = []
        self.current_stills = []
        self.current_movie = None

        self.n_stills_max = 50
        self.threads_worker = []

        self.central = QStackedWidget(self)
        self.setCentralWidget(self.central)
        self.current_widget = None

        self.info_dock = None
        self.create_info_dock()

        self.color_dt_plots = ColorDTWidget(self.central, self.info_dock)
        self.color_space_plots = ColorSpacePlots(self.central, self)
        self.color_space_plane = ColorSpaceLPlanePlots(self.central, self)
        self.node_graph = VocabularyGraph(self)
        self.feature_plot = FeaturePlot(self)


        self.visualization_widgets = [
            self.node_graph,
            self.color_dt_plots,
            self.color_space_plots,
            self.color_space_plane,
            self.feature_plot
        ]

        self.central.addWidget(self.node_graph)
        self.central.addWidget(self.color_dt_plots)
        self.central.addWidget(self.color_space_plots)
        self.central.addWidget(self.color_space_plane)
        self.central.addWidget(self.feature_plot)

        self.central.setCurrentIndex(0)

        self.query_dock = None
        self.movie_list_dock = None

        self.create_movie_list()
        self.create_query_dock()
        self.movie_list_dock.hide()

        self.onModeChanged.connect(self.query_dock.on_mode_changed)
        self.onCurrentCorpusChanged.connect(self.query_dock.on_corpus_changed)

        self.actionQuery_Window.triggered.connect(self.create_query_dock)
        self.actionFilm_List.triggered.connect(self.create_movie_list)

        self.mode = MODE_CORPUS
        self.files = []

        # self.ctrl_node_graph = self.node_graph.get_controls()

        # self.info_dock.inner.addWidget(self.ctrl_node_graph)
        # self.info_dock.inner.addWidget(self.color_dt_plots_params)
        # self.info_dock.inner.addWidget(QWidget())
        # self.info_dock.inner.addWidget(QWidget())

        self.vis_toolbar = VisualizationToolbar(self)
        self.onModeChanged.connect(self.vis_toolbar.mode_changed)

        self.level_toolbar = LevelToolbar(self)
        self.addToolBar(Qt.LeftToolBarArea, self.level_toolbar)
        self.addToolBar(Qt.LeftToolBarArea, self.vis_toolbar)

        self.unique_keywords = []
        self.thread_pool = QThreadPool(self)

        self.is_querying = False

        self.progress_bar = QProgressBar(self)
        self.statusBar().addWidget(self.progress_bar)

        self.onCorporasChange.connect(self.query_dock.update_corpora_list)
        self.actionSave_Corpora.triggered.connect(self.save_corpora)
        self.actionLoad_Corpora.triggered.connect(self.load_corpora)

        self.showMaximized()
        # E:\Programming\Datasets\FilmColors\database_root\database_root

        # self.on_load_database("E:\\Programming\\Git\\filmpalette\\results\\filemaker_db.db",
        #                       "\\\\130.60.131.134\\fiwi_datenbank\\database_root\\FilmColors_Database_Root.vian_db")
        db_path, root_path = self.load_settings()
        if db_path is not None:
            self.on_load_database(db_path, root_path)

    def set_central(self, widget):
        if self.current_widget is not None:
            self.current_widget.hide()
            self.central.layout().removeWidget(self.current_widget)
        self.current_widget = widget
        self.central.layout().addWidget(self.current_widget)

    def set_current_plot(self, idx):
        self.central.setCurrentIndex(idx)
        if self.visualization_widgets[idx] is self.color_dt_plots:
            self.color_dt_plots.on_tab_changed()
        elif self.visualization_widgets[idx] is self.color_space_plots:
            self.color_space_plots.on_tab_changed()

        elif self.visualization_widgets[idx] is self.node_graph:
            self.info_dock.set_widget(self.node_graph.get_controls(), "Node Graph")

        # self.info_dock.inner.setCurrentIndex(idx)

    def sync_on_load_database(self, sqlite_path = None, root_path = None):
        try:
            if sqlite_path is None:
                QMessageBox.information(self, "Open Database", "After clicking \'OK\',\nPlease select the database File, "
                                                               "this is usually named <DATE>_FilmColors_Database.db")
                sqlite_path = QFileDialog.getOpenFileName(filter=DATABASE_FILE_EXT)[0]

            self.database_file = sqlite_path
            self.database.connect("sqlite:///" + sqlite_path)
            keywords, segm_table_names, segm_table_words = self.database.get_filters()
            self.query_dock.create_filter_menu(keywords)

            self.unique_keywords = keywords
            if root_path is None:
                QMessageBox.information(self, "Open Root",
                                        "After clicking \'OK\',\nPlease select the Root File, "
                                        "this is usually named FilmColors_Database_Root.vian_db"
                                        "and located in /server/fiwi_datenbank/")

                root_path = QFileDialog.getOpenFileName(filter=ROOT_FILE_EXT)[0]

            with open(root_path, "r") as f:
                if "root" in f.readline():
                    self.root_dir = os.path.split(root_path)[0] + "/"

            self.node_matrix = np.loadtxt(self.root_dir + "node_matrix.csv", delimiter=";")

            labels = [k.to_string() for k in self.unique_keywords]

            self.node_graph.create_graph(self.node_matrix, labels, self.unique_keywords)

            print("Loaded Database")

            self.store_settings(sqlite_path, root_path)

        except Exception as e:
            print(e)
            QMessageBox.warning(self,"Could Not Open File", "Sorry, there has gone something wrong with the file opening")

    def on_load_database(self, sqlite_path = None, root_path = None):
        if sqlite_path is None:
            QMessageBox.information(self, "Open Database",
                                    "After clicking \'OK\',\nPlease select the database File, "
                                    "this is usually named <DATE>_FilmColors_Database.db")
            sqlite_path = QFileDialog.getOpenFileName(filter=DATABASE_FILE_EXT)[0]

        if root_path is None:
            QMessageBox.information(self, "Open Root",
                                    "After clicking \'OK\',\nPlease select the Root File, "
                                    "this is usually named FilmColors_Database_Root.vian_db"
                                    "and located in /server/fiwi_datenbank/")
            root_path = QFileDialog.getOpenFileName(filter=ROOT_FILE_EXT)[0]

        args = [sqlite_path, root_path]
        worker = SimpleWorker(self.async_load_database, self.on_load_finished, self.on_progress, args = args)
        self.thread_pool.start(worker)

    def async_load_database(self, args, on_progress):

        sqlite_path = args[0]
        root_path = args[1]

        on_progress(0.0)
        database = FilmColorsDatabase()
        database.connect("sqlite:///" + sqlite_path)
        unique_keywords, segm_table_names, segm_table_words = database.get_filters()

        on_progress(0.2)
        with open(root_path, "r") as f:
            if "root" in f.readline():
                root_dir = os.path.split(root_path)[0] + "/"

        on_progress(0.5)
        node_matrix = np.loadtxt(root_dir + "node_matrix.csv", delimiter=";")

        on_progress(0.9)
        labels = [k.to_string() for k in unique_keywords]

        all_movies = database.get_movies_objs()
        all_movies = sorted(all_movies, key=lambda x:x.name)

        #FILTERING NON USED MOVIES
        # movies_with_results = []
        # for i, m in enumerate(all_movies):
        #     on_progress(i / len(all_movies))
        #     if database.has_segments("Global:Literal", dict(Item_ID=m.fm_id)):
        #         movies_with_results.append(m)
        #         print("OK", m.name)
        #     else:
        #         print("False", m.name)
        # all_movies = movies_with_results

        on_progress(1.0)
        return [root_dir,
                unique_keywords,
                node_matrix,
                labels,
                sqlite_path,
                root_path,
                all_movies
                ]

    def on_load_finished(self, result):
        self.root_dir = result[0]
        self.unique_keywords = result[1]
        self.node_matrix = result[2]
        self.node_graph.create_graph(self.node_matrix, result[3], self.unique_keywords)
        self.query_dock.create_filter_menu(self.unique_keywords)
        self.database_file = result[4]
        self.store_settings(result[4], result[5])
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

        self.all_movies = result[6]

        default_corpus = Corpus("Complete Database")
        for m in self.all_movies:
            default_corpus.add_movie(m)
        self.add_corpus(default_corpus)
        self.set_current_corpus(0)

        self.movie_list_dock.list_files(self.all_movies)
        self.raise_()
    #region Query
    def on_start_query(self):
        if self.mode == MODE_CORPUS:
            self.on_start_corpus_query()
        else:
            self.on_start_movie_query()

    def on_start_corpus_query(self):
        if self.is_querying:
            return

        self.query_dock.setEnabled(False)
        curr_corpus = None

        if self.current_corpora is not None and self.current_corpora.name != "Complete Database":
            curr_corpus = self.current_corpus().to_fm_ids()

        if self.mode == MODE_MOVIE and self.current_movie is not None:
            fm_id = self.current_movie.fm_id
        else:
            fm_id = self.query_dock.lineEdit_fm_id.text()

        print(curr_corpus, fm_id)
        worker = SimpleWorker(self.on_query, self.on_query_finished,
                              self.on_progress,
                              args=[self.query_dock.current_filters,
                                    self.root_dir,
                                    fm_id,
                                    self.database_file,
                                    self.n_stills_max,
                                    curr_corpus
                                    ])
        self.thread_pool.start(worker)
        self.progress_bar.show()

    def on_query(self, args, on_progress):
        # filters = self.query_dock.current_filters

        filters = args[0]
        root_dir = args[1]
        fm_id = args[2]
        database_path = args[3]
        n_stills_max = args[4]
        corpus = args[5]

        database = FilmColorsDatabase()
        database.connect("sqlite:///" + database_path)

        tables = [f[0] for f in filters]
        words = [f[1] for f in filters]

        queries_tables = []
        queries_words = []
        on_progress(0.01)
        print("Query Segments")
        for i, t in enumerate(tables):
            on_progress(0.01 + (i/len(tables) * 0.2))
            if t not in queries_tables:
                queries_tables.append(t)
                queries_words.append([words[i]])
            else:
                queries_words[queries_tables.index(t)].append(words[i])

        res = []
        # Query the current filemaker ID
        # if self.query_dock.lineEdit_fm_id.text() != "":
        if fm_id != "":
            res.extend([database.get_segments("Global:Literal", dict(Item_ID=self.query_dock.lineEdit_fm_id.text()))])

        elif corpus is not None:
            res.extend([database.get_segments("Global:Literal", dict(Item_ID=corpus))])

        # Query the current Year Range
        res.extend([database.get_segments("Global:Literal", dict(Filmdaten_FilmsColors_2_Year=self.query_dock.years))])

        # Query each table individually
        for i, q in enumerate(queries_tables):
            on_progress(0.2 + (i / len(tables) * 0.2))
            d = dict(zip(queries_words[i], [1] * len(queries_words[i])))
            res.extend([database.get_segments(queries_tables[i], d)])


        # Merge the results, only pick those segments that are present in all tables
        ids = []
        for r in res:
            n = []
            for t in r:
                n.append(t['id'])
            ids.append(n)
        ids = sorted(ids, key=lambda x:len(x))

        result_ids = []
        for id in ids[0]:
            in_all = True
            for d in ids:
                if id not in d:
                    in_all = False
            if in_all:
                result_ids.append(id)

        # Query the Main Table again for the merged results
        segments = []
        for i in range(int(np.clip(int(len(result_ids) / 500), 1, None))):
            segments.extend(database.get_segments("Global:Literal", dict(id=result_ids[i*500:i*500+500])))
        r_segments = [DBSegment(s['Item_ID'], s['Segment_ID'], s["Sequence_Start"], s['Sequence_End']) for s in segments]

        current_stills = []
        current_segments = r_segments
        paths = []

        if len(r_segments) <= 0:
            return

        grouped_segments = []
        r_segments = sorted(r_segments, key = lambda x: x.fm_id)
        curr_group = [r_segments[0].fm_id, []]
        for r in r_segments:
            if r.fm_id == curr_group[0]:
                curr_group[1].append(r.segm_id)
            else:
                grouped_segments.append(curr_group)
                curr_group = [r.fm_id, [r.segm_id]]
        grouped_segments.append(curr_group)

        print("Query Stills")
        for type in [TB_STILL_GLOB, TB_STILL_FG, TB_STILL_BG]:

            r_stills_loc = []
            for i, r in enumerate(grouped_segments):
                on_progress(0.6 + (i / len(grouped_segments) * 0.4))
                stills = database.get_stills(dict(FM_ID=r[0], SEGM_ID=r[1]), type=type)
                for rs in stills:
                    r_stills_loc.append(DBStill(rs, type))

            shuffle(r_stills_loc)
            r_stills_loc = r_stills_loc[:n_stills_max]

            for st in r_stills_loc:
                paths.append(root_dir + "db_stills/" + st.rel_path)

            current_stills.extend(r_stills_loc)

        print("Loading Stills")
        for i, s in enumerate(current_stills):
            stdout.write("\r" + str(i))
            on_progress(i / len(current_stills))
            try:
                img = cv2.imread(paths[i])
                if s.t_type in [TB_STILL_FG, TB_STILL_BG]:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
                    indices = np.where(img[:, :, :3] == [0, 0, 0])
                    img[indices[0], indices[1]] = [0, 0, 0, 0]
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                s.pixmap = img
            except Exception as e:
                print("Failed", e)
                s.pixmap = np.zeros(shape =(5,5,3), dtype=np.uint8)


        return [current_stills, current_segments]

    def on_query_finished(self, result):
        if result is None:
            return
        self.is_querying = False
        self.query_dock.setEnabled(True)
        self.current_stills = result[0]
        self.current_segments = result[1]
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.update_plots()

    def on_start_movie_query(self):
        # if self.current_movie is None:
        #     return

        if self.current_movie is None:
            for m in self.all_movies:
                if self.query_dock.lineEdit_fm_id.text() in m.fm_id:
                    self.current_movie = m
                    break

        print("Querying Movie Database: ", self.current_movie.name)
        worker = SimpleWorker(self.query_movie, self.on_movie_query_finished,
                              self.on_progress,
                              args=[
                                  self.current_movie,
                                  self.query_dock.current_filters,
                                  self.database_file,
                                  self.root_dir
                              ])
        self.thread_pool.start(worker)
        self.progress_bar.show()

    def on_movie_query_finished(self, result):
        dbsegments = result[0]
        feature_segments = [SegmentTuple(x.segm_id, x.t_start, x.t_end) for x in dbsegments]
        self.feature_plot.plot(feature_segments, result[1])
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.current_stills = result[2]
        self.update_plots()

    def query_movie(self, args, on_progress):
        on_progress(0.1)
        movie = args[0]
        filters = args[1]
        database_path = args[2]
        root_dir = args[3]

        database = FilmColorsDatabase()
        database.connect("sqlite:///" + database_path)

        qsegments = database.get_segments("Global:Literal", dict(Item_ID=movie.fm_id))

        all_segments = []
        qsegm_db_ids = []
        for s in qsegments:
            all_segments.append(DBSegment(s['Item_ID'], s['Segment_ID'], s["Sequence_Start"], s['Sequence_End']))
            qsegm_db_ids.append(s['id'])

        on_progress(0.5)
        features = []
        # Query each table individually

        for f in filters:
            d = dict(zip(["id", f[1]], [qsegm_db_ids, 1]))
            # print(f[0], d)
            res = database.get_segments(f[0], d)
            ids = []
            for r in res:
                try:
                    ids.append(all_segments[qsegm_db_ids.index(r['id'])].segm_id)
                except:
                    continue

            if len(ids) > 0:
                features.append(FeatureTuple(name = str(f[0]) + ":" + str(f[1]), segment_ids = ids))

        still_objs = database.get_stills_of_movie(movie)
        result_stills = []
        for group in still_objs:
            for i, s in enumerate(group):
                stdout.write("\r" + str(root_dir + s.rel_path))
                on_progress(i / len(group))
                try:
                    img = cv2.imread(root_dir + "db_stills/" + s.rel_path)
                    if s.t_type in [TB_STILL_FG, TB_STILL_BG]:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
                        indices = np.where(img[:, :, :3] == [0, 0, 0])
                        img[indices[0], indices[1]] = [0, 0, 0, 0]
                    else:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    s.pixmap = img
                except Exception as e:
                    print("Failed", e)
                    s.pixmap = np.zeros(shape=(5, 5, 3), dtype=np.uint8)
                result_stills.append(s)
        return [all_segments, features, result_stills]
    #endregion

    def add_corpus(self, corpus):
        self.corporas.append(corpus)
        self.onCorporasChange.emit(self.corporas)

    def remove_corpus(self, corpus):
        if corpus in self.corporas:
            self.corporas.remove(corpus)
            self.onCorporasChange.emit(self.corporas)

    def set_current_movie(self, movie: DBMovie):
        self.current_movie = movie

    def on_progress(self, float):
        integer = int(float[0])
        self.progress_bar.setValue(integer)

    @pyqtSlot(object)
    def on_image_loaded(self, object):
        idx = object[0]
        img = object[1]
        self.current_stills[idx].pixmap = img

    def update_plots(self):
        print("UPDATING")
        if len(self.current_stills) == 0:
            return
        s_glob = []
        s_fg = []
        s_bg = []

        for s in self.current_stills:
            if s.t_type == TB_STILL_GLOB:
                s_glob.append(s)
            elif s.t_type == TB_STILL_BG:
                s_bg.append(s)
            else:
                s_fg.append(s)

        self.color_dt_plots.update_view(s_glob, s_fg, s_bg)
        self.color_space_plots.update_view(s_glob, s_fg, s_bg)
        self.color_space_plane.update_view(s_glob, s_fg, s_bg)

    def create_plot(self, item):
        pass

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Escape:
            self.showNormal()
        elif a0.key() == Qt.Key_Up:
            self.onImagePosScaleChanged.emit(0.1)
        elif a0.key() == Qt.Key_Down:
            self.onImagePosScaleChanged.emit(-0.1)

    def set_current_corpus(self, idx):
        try:
            self.current_corpora = self.corporas[idx]
            self.onCurrentCorpusChanged.emit(self.current_corpora)
        except:
            self.current_corpora = None
            pass

    def current_corpus(self):
        return self.current_corpora

    def set_mode(self, mode):
        self.mode = mode
        self.onModeChanged.emit(mode)

    #region Widget Creation
    def create_query_dock(self):
        if self.query_dock is None:
            self.query_dock = QueryDock(self)
            self.addDockWidget(Qt.RightDockWidgetArea, self.query_dock)
        else:
            self.addDockWidget(Qt.RightDockWidgetArea, self.query_dock)
            self.query_dock.show()

    def create_movie_list(self):
        if self.movie_list_dock is None:
            self.movie_list_dock = MovieList(self)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.movie_list_dock)
        else:
            self.addDockWidget(Qt.LeftDockWidgetArea, self.movie_list_dock)
            self.movie_list_dock.show()

    def create_info_dock(self):
        if self.info_dock is None:
            self.info_dock = InfoDock(self, self)
            self.addDockWidget(Qt.RightDockWidgetArea, self.info_dock, Qt.Vertical)
        else:
            self.addDockWidget(Qt.RightDockWidgetArea, self.info_dock, Qt.Vertical)
            self.movie_list_dock.show()
    #endregion

    #region IO
    def store_settings(self, db_path, root_path):
        data = dict(db_path = db_path, root_path=root_path)
        self.plugin.store_plugin_settings(data)

    def load_settings(self):
        data = self.plugin.load_plugin_settings()
        if data is None:
            return None, None

        return data["db_path"], data['root_path']

    def save_corpora(self):
        path = QFileDialog.getExistingDirectory()
        print(path, self.corporas)
        for c in self.corporas:
            with open(path + "/" + c.name + ".vian_corpus", "w") as f:
                json.dump(c.serialize(), f)

    def load_corpora(self):
        paths = QFileDialog.getOpenFileNames(filter="*.vian_corpus")[0]
        for p in paths:
            with open(p, "r") as f:
                self.corporas.append(Corpus("").deserialize(json.load(f), self.all_movies))
        self.onCorporasChange.emit(self.corporas)
    #endregion
    pass


class VisualizationToolbar(QToolBar):
    def __init__(self, visualizer: FiwiVisualizer):
        super(VisualizationToolbar, self).__init__(visualizer)
        self.visualizer = visualizer

        self.setIconSize(QSize(64,64))
        self.a_node_graph = self.addAction(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_node_vis.png"), "")
        self.a_color_ab = self.addAction(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_color_ab.png"), "")
        self.a_color_la = self.addAction(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_color_la.png"), "")
        self.a_colordt = self.addAction(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_color_dt.png"), "")
        self.a_features = self.addAction(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_features.png"), "")


        # self.a_node_graph.triggered.connect(partial(self.visualizer.central.setCurrentIndex, 0))
        # self.a_colordt.triggered.connect(partial(self.visualizer.central.setCurrentIndex, 1))
        # self.a_color_ab.triggered.connect(partial(self.visualizer.central.setCurrentIndex, 2))
        # self.a_color_la.triggered.connect(partial(self.visualizer.central.setCurrentIndex, 3))
        # self.a_features.triggered.connect(partial(self.visualizer.central.setCurrentIndex, 4))
        self.a_node_graph.triggered.connect(partial(self.visualizer.set_current_plot, 0))
        self.a_colordt.triggered.connect(partial(self.visualizer.set_current_plot, 1))
        self.a_color_ab.triggered.connect(partial(self.visualizer.set_current_plot, 2))
        self.a_color_la.triggered.connect(partial(self.visualizer.set_current_plot, 3))
        self.a_features.triggered.connect(partial(self.visualizer.set_current_plot, 4))

        self.mode_changed(MODE_CORPUS)

    @pyqtSlot(int)
    def mode_changed(self, mode):
        if mode == MODE_CORPUS:
            self.a_colordt.setVisible(False)
            self.a_features.setVisible(False)
        else:
            self.a_colordt.setVisible(True)
            self.a_features.setVisible(True)


class LevelToolbar(QToolBar):
    def __init__(self, visualizer: FiwiVisualizer):
        super(LevelToolbar, self).__init__(visualizer)
        self.visualizer = visualizer
        self.setIconSize(QSize(64, 64))
        self.a_corpus = self.addAction(
            create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_corpus_level_active.png"), "")

        self.a_film = self.addAction(
            create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_film_level.png"), "")

        self.a_corpus.triggered.connect(partial(self.on_set_mode, MODE_CORPUS))
        self.a_film.triggered.connect(partial(self.on_set_mode, MODE_MOVIE))

    def on_set_mode(self, mode):
        self.visualizer.set_mode(mode)
        if mode == MODE_CORPUS:
            self.a_corpus.setIcon(create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_corpus_level_active.png"))
            self.a_film.setIcon(
                create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_film_level.png"))
        else:
            self.a_corpus.setIcon(
                create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_corpus_level.png"))
            self.a_film.setIcon(
                create_icon("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/icon_film_level_active.png"))


class InfoDock(QDockWidget):
    def __init__(self, parent, visualizer):
        super(InfoDock, self).__init__(parent)
        self.setWindowTitle("Inspector")
        self.visualizer = visualizer

    def set_widget(self, widget, title):
        self.setWindowTitle("Settings: " + title)
        self.setWidget(widget)