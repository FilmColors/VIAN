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
from sys import stdout
from random import shuffle

from extensions.plugins.fiwi_tools.fiwi_visualizer.movie_list import *
from extensions.plugins.fiwi_tools.fiwi_visualizer.query_dock import *
from extensions.plugins.fiwi_tools.fiwi_visualizer.filmcolors_db import *
from core.visualization.graph_plots import *

from core.data.plugin import *
from core.concurrent.worker import SimpleWorker


#region -- Definitions --
VOC_PATH = "C:\\Users\\Gaudenz Halter\\Desktop\\Glossar_DB_exp_11022018_2.CSV"
ROOT_FILE_EXT = "*.vian_db"
DATABASE_FILE_EXT = "*.db"

MODE_FOREGROUND = 0

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

    def __init__(self, parent, plugin: GAPlugin):
        super(FiwiVisualizer, self).__init__(parent)
        path = os.path.abspath("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/WindowFiwiDatabase.ui")
        uic.loadUi(path, self)
        self.plugin = plugin
        self.actionOpen_Database.triggered.connect(partial(self.on_load_database, None, None))

        self.database = FilmColorsDatabase()
        self.database_file = None

        self.root_dir = None
        self.node_matrix = None

        self.current_segments = []
        self.current_stills = []

        self.n_stills_max = 50
        self.threads_worker = []

        self.central = QStackedWidget(self)
        self.setCentralWidget(self.central)
        self.current_widget = None

        self.color_dt_plots = ColorDTWidget(self.central)
        self.color_space_plots = ColorSpacePlots(self.central, self)
        self.color_space_plane = ColorSpaceLPlanePlots(self.central, self)
        self.node_graph = VocabularyGraph(self)

        self.central.addWidget(self.node_graph)
        self.central.addWidget(self.color_dt_plots)
        self.central.addWidget(self.color_space_plots)
        self.central.addWidget(self.color_space_plane)

        self.central.setCurrentIndex(0)

        self.query_dock = None
        self.movie_list_dock = None
        self.info_dock = None

        self.create_movie_list()
        self.create_query_dock()
        self.movie_list_dock.hide()
        self.create_info_dock()

        self.actionQuery_Window.triggered.connect(self.create_query_dock)
        self.actionFilm_List.triggered.connect(self.create_movie_list)

        self.mode = None
        self.files = []

        self.vis_toolbar = self.addToolBar("Visualizations")
        self.a_node_graph = self.vis_toolbar.addAction("Node-Graph")
        self.a_colordt = self.vis_toolbar.addAction("Color-DT Plots")
        self.a_color_ab = self.vis_toolbar.addAction("AB-Plane Plots")
        self.a_color_la = self.vis_toolbar.addAction("LA-Plane Plots")

        self.ctrl_node_graph = self.node_graph.get_controls()

        self.info_dock.inner.addWidget(self.ctrl_node_graph)
        self.info_dock.inner.addWidget(QWidget())
        self.info_dock.inner.addWidget(QWidget())
        self.info_dock.inner.addWidget(QWidget())

        self.a_node_graph.triggered.connect(partial(self.central.setCurrentIndex, 0))
        self.a_colordt.triggered.connect(partial(self.central.setCurrentIndex, 1))
        self.a_color_ab.triggered.connect(partial(self.central.setCurrentIndex, 2))
        self.a_color_la.triggered.connect(partial(self.central.setCurrentIndex, 3))


        self.unique_keywords = []
        self.thread_pool = QThreadPool(self)

        self.is_querying = False

        self.progress_bar = QProgressBar(self)
        self.statusBar().addWidget(self.progress_bar)

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
        self.info_dock.inner.setCurrentIndex(idx)

    def on_load_database(self, sqlite_path = None, root_path = None):
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

            print(len(self.unique_keywords), self.node_matrix.shape)
            labels = [k.to_string() for k in self.unique_keywords]

            self.node_graph.create_graph(self.node_matrix, labels, self.unique_keywords)

            print("Loaded Database")

            self.store_settings(sqlite_path, root_path)

        except Exception as e:
            print(e)
            QMessageBox.warning(self,"Could Not Open File", "Sorry, there has gone something wrong with the file opening")


    def on_start_query(self):
        worker = SimpleWorker(self.on_query, self.on_query_finished,
                              self.on_progress,
                              args=[self.query_dock.current_filters,
                                    self.root_dir,
                                    self.query_dock.lineEdit_fm_id.text(),
                                    self.database_file,
                                    self.n_stills_max
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

        database = FilmColorsDatabase()
        database.connect("sqlite:///" + database_path)

        tables = [f[0] for f in filters]
        words = [f[1] for f in filters]

        queries_tables = []
        queries_words = []
        on_progress(0.01)
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
            res.extend([database.get_segments("Global:Literal", dict(FileMaker_ID=self.query_dock.lineEdit_fm_id.text()))])

        # Query the current Year Range
        res.extend([database.get_segments("Global:Literal", dict(Filmdaten_FilmsColors_2_Year=self.query_dock.years))])

        # Query each table individually
        for i, q in enumerate(queries_tables):
            on_progress(0.2 + (i / len(tables) * 0.2))
            print("Querying", queries_tables[i])
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
        r_segments = [DBSegment(s['FileMaker_ID'], s['Segment_ID']) for s in segments]

        current_stills = []
        current_segments = r_segments
        paths = []
        for type in [TB_STILL_GLOB, TB_STILL_FG, TB_STILL_BG]:

            r_stills_loc = []
            for i, r in enumerate(r_segments):
                on_progress(0.6 + (i / len(r_segments) * 0.4))
                if i % 10 == 0:
                    stdout.write("\r" + str(round(i / len(r_segments) * 100, 2)))
                stills = database.get_stills(dict(FM_ID=r.fm_id, SEGM_ID=r.segm_id), type=type)
                for rs in stills:
                    r_stills_loc.append(DBStill(rs, type))

            shuffle(r_stills_loc)
            r_stills_loc = r_stills_loc[:n_stills_max]


            for st in r_stills_loc:
                paths.append(root_dir + "db_stills/" + st.rel_path)

            current_stills.extend(r_stills_loc)

        # self.threads_worker.append(run_minimal_worker(ImageLoaderThreadWorker(paths, self.on_image_loaded)))
        for i, s in enumerate(current_stills):
            stdout.write("\r" + str(i))
            try:
                img = cv2.imread(paths[i])
                s.pixmap = img
            except:
                print("Failed")
                s.pixmap = np.zeros(shape =(5,5,3), dtype=np.uint8)

        return [current_stills, current_segments]


    def on_query_finished(self, result):
        self.current_stills = result[0]
        self.current_segments = result[1]
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.update_plots()

    def on_progress(self, float):
        integer = int(float[0])
        self.progress_bar.setValue(integer)


    @pyqtSlot(object)
    def on_image_loaded(self, object):
        idx = object[0]
        img = object[1]
        self.current_stills[idx].pixmap = img
        print(self.current_stills[idx].pixmap)

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


    def store_settings(self, db_path, root_path):
        data = dict(db_path = db_path, root_path=root_path)
        self.plugin.store_plugin_settings(data)

    def load_settings(self):
        data = self.plugin.load_plugin_settings()
        if data is None:
            return None, None

        return data["db_path"], data['root_path']


class InfoDock(QDockWidget):
    def __init__(self, parent, visualizer):
        super(InfoDock, self).__init__(parent)
        self.setWindowTitle("Inspector")
        self.visualizer = visualizer

        self.inner = QStackedWidget(self)
        self.setWidget(self.inner)


