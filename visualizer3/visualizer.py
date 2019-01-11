from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from core.gui.classification import CheckBoxGroupWidget
from PyQt5 import uic
import os
import cv2
from typing import List

from core.corpus.shared.sqlalchemy_entities import *
from visualizer3.worker import QueryWorker, CORPUS_PATH
from functools import partial
from visualizer3.plot_widget import PlotWidget, PlotResultsWidget, feature_changed
from visualizer3.screenshot_worker import ScreenshotWorker
from core.visualization.image_plots import ImagePlotCircular, ImagePlotPlane, ImagePlotTime
from core.visualization.dot_plot import DotPlot
from core.visualization.palette_plot import MultiPaletteLABWidget



class ProgressBar(QWidget):
    def __init__(self, parent, singal):
        super(ProgressBar, self).__init__(parent)
        self.pbar = QProgressBar(self)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.pbar)
        singal.connect(self.on_progress)

    @pyqtSlot(float)
    def on_progress(self, f):
        self.pbar.setValue(int(f * 100))
        if f == 1.0:
            self.close()


class VIANVisualizer2(QMainWindow):
    onSegmentQuery = pyqtSignal(object, object, object, int, object, object)
    onMovieQuery = pyqtSignal(object)
    onCorpusQuery = pyqtSignal()
    onLoadScreenshots = pyqtSignal(object, object, int)
    onChangeScreenshotClObj = pyqtSignal(object, int)
    onCorpusChanged = pyqtSignal(object)

    def __init__(self, parent = None):
        super(VIANVisualizer2, self).__init__(parent)
        self.query_widget = KeywordWidget(self, self)
        self.setCentralWidget(QWidget(self))
        self.setWindowTitle("VIAN Visualizer")
        self.menu_file = self.menuBar().addMenu("File")
        self.a_open = self.menu_file.addAction("Open")
        self.a_open.triggered.connect(self.load_corpus)
        self.menu_windows = self.menuBar().addMenu("Windows")
        self.a_subcorpus_view = self.menu_windows.addAction("SubCorpus View")
        self.a_segment_view = self.menu_windows.addAction("Segment View")
        self.MAX_WIDTH = 300

        self.corpus_view = CorpusWidget(self)
        self.onCorpusChanged.connect(self.corpus_view.on_corpus_changed)
        self.addDockWidget(Qt.RightDockWidgetArea, self.corpus_view)
        self.corpus_view.hide()
        self.a_subcorpus_view.triggered.connect(self.corpus_view.show)

        self.segment_view = SegmentWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.segment_view)
        self.segment_view.hide()
        self.a_segment_view.triggered.connect(self.segment_view.show)

        self.worker = QueryWorker(CORPUS_PATH)
        self.query_thread = QThread()
        self.worker.moveToThread(self.query_thread)
        self.query_thread.start()

        self.onSegmentQuery.connect(self.worker.on_query_segments)
        self.worker.signals.onCorpusQueryResult.connect(self.on_corpus_result)
        self.worker.signals.onSegmentQueryResult.connect(self.on_segment_query_result)
        self.onCorpusQuery.connect(self.worker.on_corpus_info)

        self.screenshot_loader = ScreenshotWorker(self)
        self.screenshot_thread = QThread()
        self.screenshot_loader.moveToThread(self.screenshot_thread)
        self.screenshot_thread.start()
        self.onLoadScreenshots.connect(self.screenshot_loader.on_load_screenshots)
        self.onChangeScreenshotClObj.connect(self.screenshot_loader.on_change_classification_object)

        self.centralWidget().setLayout(QVBoxLayout())

        self.cb_corpus = QComboBox(self)
        self.cb_corpus.addItem("Complete")
        self.cb_query_type = QComboBox(self)
        self.cb_query_type.addItems(["Segments"])#, "Movies"])

        self.centralWidget().layout().addWidget(self.cb_corpus)
        self.centralWidget().layout().addWidget(self.cb_query_type)
        self.centralWidget().layout().addWidget(self.query_widget)

        self.btn_query = QPushButton("Query")
        self.btn_query.clicked.connect(self.on_query)

        self.classification_objects = dict()

        self.result_wnd = PlotResultsWidget(self)

        # Plottypes Widget
        self.w_plot_types = QWidget(self)
        lt = QGridLayout(self.w_plot_types)
        self.w_plot_types.setLayout(lt)
        self.cb_segm_ab_plot = QCheckBox("AB Screenshots Plot", self.w_plot_types)
        self.cb_segm_lc_plot = QCheckBox("LC Screenshots Plot", self.w_plot_types)
        self.cb_segm_ab_dot_plot = QCheckBox("AB Dot Plot", self.w_plot_types)
        self.cb_segm_lc_dot_plot = QCheckBox("LC Dot Plot", self.w_plot_types)
        self.cb_segm_palette_dot_plot = QCheckBox("Palette Dot Plot", self.w_plot_types)

        self.cb_segm_dt_plot = QCheckBox("Color-dT", self.w_plot_types)
        self.cb_segm_ab_plot.setChecked(True)
        self.cb_segm_lc_plot.setChecked(True)
        self.cb_segm_ab_dot_plot.setChecked(True)
        self.cb_segm_lc_dot_plot.setChecked(True)
        self.cb_segm_dt_plot.setChecked(False)
        self.cb_segm_palette_dot_plot.setChecked(False)
        lt.addWidget(QLabel("Plot Types", self.w_plot_types), 0, 0)
        lt.addWidget(self.cb_segm_ab_plot, 1, 0)
        lt.addWidget(self.cb_segm_lc_plot, 2, 0)
        lt.addWidget(self.cb_segm_ab_dot_plot, 3, 0)
        lt.addWidget(self.cb_segm_lc_dot_plot, 4, 0)
        lt.addWidget(self.cb_segm_dt_plot, 1, 1)
        lt.addWidget(self.cb_segm_palette_dot_plot, 2, 1)
        hbox_k = QHBoxLayout()
        hbox_k.addWidget(QLabel("K-Images", self.centralWidget()))
        self.sp_box_K = QSpinBox(self.centralWidget())
        self.sp_box_K.setRange(1, 10000)
        self.sp_box_K.setValue(400)
        hbox_k.addWidget(self.sp_box_K)

        self.centralWidget().layout().addWidget(self.w_plot_types)

        self.centralWidget().layout().addItem(hbox_k)
        self.centralWidget().layout().addWidget(self.btn_query)

        self.cb_corpus.currentTextChanged.connect(self.on_corpus_changed)
        self.sub_corpora = dict()
        # SegmentsData
        self.segments = dict()
        self.segm_scrs = dict()
        self.show()

    def load_corpus(self):
        path = "F:\\_corpus\\ERCFilmColors_V2\\database.db"
        path = QFileDialog.getOpenFileName(filter="*.db")[0]
        root = os.path.split(path)[0]
        hdf5_path = path.replace("database.db", "analyses.hdf5")
        sql_path = "sqlite:///" + path
        self.worker.load(path, root)
        self.screenshot_loader.db_root = root
        self.onCorpusQuery.emit()

    def on_query(self):
        progress = ProgressBar(self, self.worker.signals.onProgress)
        progress.show()
        progress.resize(self.width(), 100)
        progress.move(0, (0.5 * self.height()))
        self.btn_query.setEnabled(False)
        if self.cb_query_type.currentText() == "Segments":
            self.query_segments()
        else:
            self.query_movies()

    def query_segments(self):
        subcorpus = None
        if self.cb_corpus.currentText() != "Complete":
            subcorpus = self.sub_corpora[self.cb_corpus.currentText()]
        settings = dict(
            get_features = (self.cb_segm_ab_plot.isChecked()
                            or self.cb_segm_lc_plot.isChecked()
                            or self.cb_segm_ab_dot_plot.isChecked()
                            or self.cb_segm_lc_dot_plot.isChecked()
                            or self.cb_segm_dt_plot.isChecked()),
            get_palettes = self.cb_segm_palette_dot_plot.isChecked()
        )
        self.onSegmentQuery.emit(*self.query_widget.get_keyword_filters(),
                                 subcorpus,
                                 self.sp_box_K.value(),
                                 self.query_widget.filmography_widget.get_filmography_query(),
                                 settings)
        pass

    def query_movies(self):
        pass

    def on_corpus_changed(self):
        if self.cb_corpus.currentText() in self.sub_corpora:
            curr = self.sub_corpora[self.cb_corpus.currentText()]
            self.onCorpusChanged.emit(curr)

    def on_segment_query_result(self, segments:List[DBSegment], screenshots:List[DBScreenshot]):
        self.btn_query.setEnabled(True)
        self.segm_scrs = dict()
        self.segments = dict()
        if self.cb_segm_ab_plot.isChecked():
            p_ab = ImagePlotCircular(self.result_wnd)
        else:
            p_ab = None

        if self.cb_segm_lc_plot.isChecked():
            p_lc = ImagePlotPlane(self, range_y=[0, 255])
        else:
            p_lc = None

        if self.cb_segm_lc_dot_plot.isChecked():
            plot_lc_dot = DotPlot(self)
            plot_lc_dot.add_grid("LA")
        else:
            plot_lc_dot = None

        if self.cb_segm_ab_dot_plot.isChecked():
            plot_ab_dot = DotPlot(self)
            plot_ab_dot.add_grid("AB")
        else:
            plot_ab_dot = None

        if self.cb_segm_dt_plot.isChecked():
            p_dt = ImagePlotTime(self.result_wnd)
        else:
            p_dt = None

        if self.cb_segm_palette_dot_plot.isChecked():
            p_palette_dot = MultiPaletteLABWidget(self.result_wnd)
            palettes = []
            for scr in screenshots.values():
                if scr.current_palette is not None:
                    palettes.append(scr.current_palette)
            p_palette_dot.set_palettes(palettes)
        else:
            p_palette_dot = None

        for scr in screenshots.values():
            try:
                data = scr.features[1]
                img = scr.current_image
                # img = cv2.imread(self.worker.root + "/shots/" + scr.dbscreenshot.file_path)
                l = data[0]
                tx = scr.dbscreenshot.time_ms
                ty = data[7]
                x = data[1]
                y = data[2]
                c = QColor(data[5], data[4],data[3], 200)

                if p_ab is not None:
                    scr.onImageChanged.connect(p_ab.add_image(-x, -y, img, True, mime_data=scr, z=l, uid=scr.dbscreenshot.id).setPixmap)
                    scr.onFeatureChanged.connect(partial(feature_changed, scr, p_ab))
                if p_lc is not None:
                    scr.onImageChanged.connect(p_lc.add_image(-x, l, img, False, mime_data=scr, z=y, uid=scr.dbscreenshot.id).setPixmap)
                    scr.onFeatureChanged.connect(partial(feature_changed, scr, p_lc))
                if p_dt is not None:
                    scr.onImageChanged.connect(p_dt.add_image(tx, ty, img, False, mime_data=scr, index_id=scr.dbscreenshot.id).setPixmap)
                    scr.onFeatureChanged.connect(partial(feature_changed, scr,  p_dt))
                if plot_ab_dot is not None:
                    plot_ab_dot.add_point(x, -y, z=l, col=c, uid=scr.dbscreenshot.id)
                    scr.onFeatureChanged.connect(partial(feature_changed, scr, plot_ab_dot))
                if plot_lc_dot is not None:
                    plot_lc_dot.add_point(-x, l, z=-y, col=c, uid=scr.dbscreenshot.id)
                    scr.onFeatureChanged.connect(partial(feature_changed, scr, plot_lc_dot))
                    #

            except Exception as e:
                pass

        plots = []
        if p_ab is not None:
            plots.append(PlotWidget(self.result_wnd, p_ab, "AB-Screenshots"))
        if p_dt is not None:
            plots.append(PlotWidget(self.result_wnd, p_dt, "dT-Screenshots"))
        if p_lc is not None:
            plots.append(PlotWidget(self.result_wnd, p_lc, "LC-Screenshots"))
        if plot_ab_dot is not None:
            plots.append(PlotWidget(self.result_wnd, plot_ab_dot, "LC-Dot"))
        if plot_lc_dot is not None:
            plots.append(PlotWidget(self.result_wnd, plot_lc_dot, "LC-Dot"))
        if p_palette_dot is not None:
            plots.append(PlotWidget(self.result_wnd, p_palette_dot, "Palette-Dot"))

        self.result_wnd.add_plots(plots, self.classification_objects, screenshots)
        self.result_wnd.show()

        labels = []
        for clobj in self.classification_objects.values():
            t = [lbl.mask_idx - 1 for lbl in clobj.semantic_segmentation_labels]
            labels.append([clobj.id, t])
        self.segm_scrs = screenshots
        self.segment_view.set_segments(segments)

        if p_ab is not None or p_dt is not None or p_lc is not None:
            self.onLoadScreenshots.emit(screenshots.values(),labels, 1)

    def on_corpus_result(self, autofill, projects:List[DBProject], keywords:List[DBUniqueKeyword], classification_objects: List[DBClassificationObject], subcorpora):
        self.classification_objects = dict()
        for clobj in classification_objects:
            self.classification_objects[clobj.name] = clobj
        self.query_widget.clear()
        for kwd in keywords:
            voc = kwd.word.vocabulary
            cl_obj =kwd.classification_object
            word = kwd.word
            self.query_widget.add_unique_keyword(kwd, cl_obj, voc, word)
        self.query_widget.add_spacers()
        for c in subcorpora:
            self.cb_corpus.addItem(c.name)
            self.sub_corpora[c.name] = c
        self.query_widget.filmography_widget.apply_autofill(autofill)


class CorpusWidget(QDockWidget):
    def __init__(self, visualizer):
        super(CorpusWidget, self).__init__(visualizer)
        self.list = QListWidget(self)
        self.setWidget(self.list)

    def on_corpus_changed(self, corpus:DBSubCorpus):
        self.list.clear()
        for c in sorted(corpus.projects, key=lambda x:x.movie.name): #type:DBProject
            self.list.addItem(c.movie.name)


class SegmentWidget(QDockWidget):
    def __init__(self, visualizer):
        super(SegmentWidget, self).__init__(visualizer)
        self.visualizer = visualizer
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.setWidget(self.table)

    def add_header(self):
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("FM-ID"))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem("Segm-ID"))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem("Start"))
        self.table.setHorizontalHeaderItem(3, QTableWidgetItem("Stop"))
        self.table.setHorizontalHeaderItem(4, QTableWidgetItem("Text"))
        self.table.verticalHeader().hide()

    def set_segments(self, segments:List[DBSegment]):
        self.table.clear()
        self.table.setRowCount(0)
        self.add_header()
        if len(segments) == 0:
            return
        for i, s in enumerate(sorted(segments, key = lambda x:x.project.corpus_id)):
            fm_id = "_".join([str(s.project.corpus_id),
                              str(s.project.manifestation_id),
                              str(s.project.copy_id)])

            self.table.setRowCount(self.table.rowCount() + 1)
            self.table.setItem(i, 0, QTableWidgetItem(fm_id))
            self.table.setItem(i, 1, QTableWidgetItem(str(s.movie_segm_id)))
            self.table.setItem(i, 2, QTableWidgetItem(str(s.start_ms)))
            self.table.setItem(i, 3, QTableWidgetItem(str(s.end_ms)))
            self.table.setItem(i, 4, QTableWidgetItem(str(s.body)))


class ClassificationObjectList(QListWidget):
    def __init__(self, parent):
        super(ClassificationObjectList, self).__init__(parent)
        self.item_entries = []
        self.clear_list()

    def clear_list(self):
        self.clear()
        self.item_entries = []
        itm = QListWidgetItem("Filmography")
        self.addItem(itm)

    def get_item(self, cl_obj):
        for item in self.item_entries:
            if item[0] == cl_obj:
                return item[2]

    def add_item(self, class_obj):
        itm = QListWidgetItem(class_obj.name)
        itm.setCheckState(Qt.Unchecked)
        self.addItem(itm)
        self.item_entries.append((class_obj, len(self.item_entries), itm))
        return itm


class KeywordWidget(QWidget):
    def __init__(self,parent, visualizer):
        super(KeywordWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.setLayout(QHBoxLayout(self))
        self.class_obj_list = ClassificationObjectList(self)
        self.class_obj_list.setMaximumWidth(300)
        self.class_obj_list.currentItemChanged.connect(self.on_classification_object_changed)
        self.stack_widget = QStackedWidget(self)
        # self.stack_widget.setStyleSheet("QWidget{background: rgb(30,30,30);}")

        self.stack_map = dict()
        self.tabs_map = dict()
        self.voc_map = dict()
        self.keyword_map = dict()
        self.keyword_cl_obj_map = dict()
        self.layout().addWidget(self.class_obj_list)
        self.layout().addWidget(self.stack_widget)
        self.filmography_widget = None
        self.add_filmography_widget()

    def add_filmography_widget(self):
        stack = FilmographyWidget(self)
        self.stack_map["Filmography"] = stack
        self.stack_widget.addWidget(stack)
        self.filmography_widget = stack

    def on_classification_object_changed(self):
        self.stack_widget.setCurrentIndex(self.class_obj_list.currentIndex().row())

    def clear(self):
        self.class_obj_list.clear_list()
        for s in self.stack_map.keys():
            self.stack_map[s].deleteLater()
        self.stack_map = dict()
        self.tabs_map = dict()
        self.voc_map = dict()
        self.keyword_map = dict()
        self.keyword_cl_obj_map = dict()

        self.add_filmography_widget()

    def add_spacers(self):
        for x in self.tabs_map.keys():
            for y in self.tabs_map[x].keys():
                self.tabs_map[x][y].widget().layout().addItem(QSpacerItem(2,2,QSizePolicy.Fixed, QSizePolicy.Expanding))

    def add_unique_keyword(self, ukw: DBUniqueKeyword, cl_obj: DBClassificationObject, voc: DBVocabulary, voc_word: DBVocabularyWord):
        if cl_obj.name not in self.tabs_map:
            stack = QTabWidget()
            self.stack_map[cl_obj.name] = stack
            self.stack_widget.addWidget(stack)
            self.tabs_map[cl_obj.name] = dict()
            self.voc_map[cl_obj.name] = dict()
            cl_obj_item = self.class_obj_list.add_item(cl_obj)
            stack.show()
        else:
            stack = self.stack_map[cl_obj.name]
            cl_obj_item = self.class_obj_list.get_item(cl_obj)

        if voc.vocabulary_category.name not in self.tabs_map[cl_obj.name]:
            tab = QScrollArea(stack)
            tab.setWidgetResizable(True)
            tab.setWidget(QWidget(tab))
            tab.widget().setLayout(QVBoxLayout(tab.widget()))
            stack.addTab(tab, voc.vocabulary_category.name)
            self.stack_map[cl_obj.name].addTab(tab, voc.vocabulary_category.name)
            self.tabs_map[cl_obj.name][voc.vocabulary_category.name] = tab
            self.voc_map[cl_obj.name][voc.vocabulary_category.name] = dict()
            tab.show()
        else:
            tab = self.tabs_map[cl_obj.name][voc.vocabulary_category.name]

        if voc.name not in self.voc_map[cl_obj.name][voc.vocabulary_category.name]:
            group = CheckBoxGroupWidget(self, voc.name)
            tab.widget().layout().addWidget(group)
            self.voc_map[cl_obj.name][voc.vocabulary_category.name][voc.name] = group
            group.show()
        else:
            group = self.voc_map[cl_obj.name][voc.vocabulary_category.name][voc.name]

        checkbox = WordCheckBox(None, ukw)
        checkbox.setTristate(True)
        self.keyword_map[ukw.id] = checkbox
        self.keyword_cl_obj_map[ukw.id] = cl_obj_item
        group.add_checkbox(checkbox)
        checkbox.show()

    def get_keyword_filters(self):
        result_include = []
        result_exclude = []
        for k in self.keyword_map.keys():
            cb = self.keyword_map[k]
            if cb.checkState() == Qt.Checked:
                result_include.append(cb.word.id)
            elif cb.checkState() == Qt.PartiallyChecked:
                result_exclude.append(cb.word.id)
        return result_include, result_exclude

    def get_classification_object_filters(self):
        result = []
        for item in self.class_obj_list.item_entries:
            try:
                if item[2].checkState() == Qt.Checked:
                    result.append(item[0].classification_object_id)
                print("ok")
            except Exception as e:
                print(e)
        return result


class WordCheckBox(QCheckBox):
    def __init__(self, parent, word):
        super(WordCheckBox, self).__init__(parent)
        self.word = word
        self.setText(word.word.name)


class FilmographyWidget(QWidget):
    def __init__(self,parent):
        super(FilmographyWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/FilmographyQueryWidget.ui")
        uic.loadUi(path, self)
        self.genre_map = dict()

    def apply_autofill(self, a):
        self.comboBox_Genre.clear()
        self.comboBox_Genre.addItem("None")
        self.genre_map = dict()
        for g in a['genres']:
            self.comboBox_Genre.addItem(g.name)
            self.genre_map[g.name] = g.id

        completer_imdb = QCompleter(a["imdb_id"])
        completer_production_company = QCompleter(a["production_company"])
        completer_cinematography = QCompleter(a["cinematography"])
        completer_color_consultant = QCompleter(a["color_consultant"])
        completer_costum_design = QCompleter(a["costum_design"])
        completer_art_director = QCompleter(a["art_director"])
        completer_country = QCompleter(a["country"])
        completer_production_design = QCompleter(a["production_design"])
        completer_color_process = QCompleter(a["color_process"])

        for c in [completer_imdb, completer_production_company, completer_art_director, completer_color_consultant,
                  completer_costum_design, completer_cinematography, completer_costum_design, completer_country,
                  completer_production_design, completer_color_process]:
            c.setCaseSensitivity(False)
            c.setCompletionMode(QCompleter.PopupCompletion)

        self.lineEdit_IMDB.setCompleter(completer_imdb)
        self.lineEdit_Cinematography.setCompleter(completer_cinematography)
        self.lineEdit_ColorConsultant.setCompleter(completer_color_consultant)
        self.lineEdit_ProductionDesign.setCompleter(completer_production_design)
        self.lineEdit_ArtDirector.setCompleter(completer_art_director)
        self.lineEdit_CostumDesign.setCompleter(completer_costum_design)
        self.lineEdit_ArtDirector.setCompleter(completer_art_director)
        self.lineEdit_ProductionCompany.setCompleter(completer_production_company)
        self.lineEdit_ProductionCountry.setCompleter(completer_country)

    def get_filmography_query(self):
        query = FilmographyQuery()
        if self.lineEdit_IMDB.text() != "":
            query.imdb_id = self.lineEdit_IMDB.text().split(",")
        if self.spinBox_Corpus_A.value() > 0:
            query.corpus_id = self.spinBox_Corpus_A.value()
        if self.spinBox_Corpus_B.value() > 0:
            query.manifestation_id = self.spinBox_Corpus_B.value()
        if self.spinBox_Corpus_C.value() > 0:
            query.copy_id = self.spinBox_Corpus_C.value()
        if self.comboBox_ColorProcess.currentText() != "":
            query.color_process = self.comboBox_ColorProcess.text().split(",")
        if self.lineEdit_Director.text() != "":
            query.director = self.lineEdit_Director.text().split(",")
        if self.lineEdit_Cinematography.text() != "":
            query.cinematography = self.lineEdit_Cinematography.text().split(",")
        if self.lineEdit_ColorConsultant.text() != "":
            query.color_consultant = self.lineEdit_ColorConsultant.text().split(",")
        if self.lineEdit_ProductionDesign.text() != "":
            query.production_design = self.lineEdit_ProductionDesign.text().split(",")
        if self.lineEdit_ArtDirector.text() != "":
            query.art_director = self.lineEdit_ArtDirector.text().split(",")
        if self.lineEdit_CostumDesign.text() != "":
            query.costum_design = self.lineEdit_CostumDesign.text().split(",")
        if self.lineEdit_ProductionCompany.text() != "":
            query.production_company = self.lineEdit_ProductionCompany.text().split(",")
        if self.lineEdit_ProductionCountry.text() != "":
            query.country = self.lineEdit_ProductionCountry.text().split(",")
        if self.spinBox_YearA.value() > 0:
            query.year_start = self.spinBox_YearA.value()
        if self.spinBox_YearB.value() > 0:
            query.year_end = self.spinBox_YearB.value()
        if self.comboBox_Genre.currentText() != "None":
            query.genre = [self.genre_map[self.comboBox_Genre.currentText()]]

        return query



