from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
from core.data.settings import Contributor
import os
import numpy as np
from PyQt5 import uic
from core.data.log import log_warning, log_info, log_error, log_debug
from core.data.computation import create_icon
from core.corpus.client.corpus_client import CorpusClient
# from core.gui.Dialogs.new_project_dialog import FilmographyWidget2
from functools import partial
from core.data.interfaces import IProjectChangeNotify
from core.gui.ewidgetbase import *
from core.gui.tools import StringList
import json
import socket
import threading
import hashlib, uuid
from extensions.pipelines.ercfilmcolors import ERCFilmColorsVIANPipeline
from core.gui.filmography_widget import FilmographyWidget2


class WebAppCorpusDock(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(WebAppCorpusDock, self).__init__(main_window, False)
        self.setWindowTitle("WebApp")
        self.central = QWidget(self)
        self.setWidget(self.central)
        self.central.setLayout(QVBoxLayout())
        self.corpus_client = corpus_client
        self.corpus_widget = CorpusClientWidget(self, corpus_client, main_window)
        # self.corpus_widget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.central.layout().addWidget(self.corpus_widget)
        self.stack = QStackedWidget(self)
        self.central.layout().addWidget(self.stack)
        self.progress_widget = CorpusProgressWidget(self, main_window)
        self.filmography_widget = FilmographyWidget2(self)
        self.stack.addWidget(self.progress_widget)
        self.stack.addWidget( self.filmography_widget)
        self.btn_Commit = QPushButton("3. Commit Project", self.central)
        self.central.layout().addWidget(self.btn_Commit)
        self.btn_Commit.clicked.connect(partial(self.corpus_widget.on_commit))
        self.btn_Commit.setEnabled(False)

        self.progress_widget.onThresholdReached.connect(self.on_threshold_reached)

    @pyqtSlot()
    def on_analyses_changed(self):
        self.progress_widget.update_state()
        pass

    def on_loaded(self, project):
        self.btn_Commit.setEnabled(False)
        self.progress_widget.btn_RunAll.setEnabled(False)

    def on_threshold_reached(self):
        self.btn_Commit.setEnabled(True)


class CorpusProgressWidget(QWidget):
    onThresholdReached = pyqtSignal()

    def __init__(self, parent, main_window):
        super(CorpusProgressWidget, self).__init__(parent)
        self.main_window = main_window
        self.setLayout(QVBoxLayout())
        self.btn_checkFiles = QPushButton("1. Check Project")
        self.btn_checkFiles.clicked.connect(self.update_state)
        self.layout().addWidget(self.btn_checkFiles)
        self.list_widget = QWidget(self)
        self.list_widget.setLayout(QVBoxLayout())
        self.layout().addWidget(self.list_widget)
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.btn_RunAll = QPushButton("2. Run all Missing Analyses")
        self.btn_RunAll.clicked.connect(self.run_all)
        self.layout().addWidget(self.spacer)
        self.layout().addWidget(self.btn_RunAll)

        self.requirements = ERCFilmColorsVIANPipeline.requirements
        self.items = dict()
        self.missing_analyses = dict()


    @pyqtSlot()
    def update_state(self):
        data = self.requirements
        log_debug("Requirements:", data)
        if data is None:
            return
        self.missing_analyses = dict()

        progress_segmentation = 0.0
        progress_screenshots = 0.0

        if self.main_window.project is not None:
            if "segment_analyses" in data and self.main_window.project.get_main_segmentation() is not None:
                n_analyses = len(self.main_window.project.get_main_segmentation().segments) * len(data["segment_analyses"])
                n_analyses_done = 0
                analyses_to_do = data["segment_analyses"]
                for s in self.main_window.project.get_main_segmentation().segments:
                    for q in analyses_to_do:
                        found = False
                        for a in s.connected_analyses:
                            if a.target_classification_object is None:
                                continue
                            if a.analysis_job_class == q[0] and a.target_classification_object.name == q[1]:
                                found = True
                                break
                        if found:
                            n_analyses_done += 1
                        else:
                            if q[2] not in self.missing_analyses:
                                self.missing_analyses[q[2]] = dict()
                            if q[0] not in self.missing_analyses[q[2]]:
                                self.missing_analyses[q[2]][q[0]] = dict()
                            if q[1] not in self.missing_analyses[q[2]][q[0]]:
                                self.missing_analyses[q[2]][q[0]][q[1]] = []
                            self.missing_analyses[q[2]][q[0]][q[1]] .append(s)

                if "SegmentAnalyses" not in self.items:
                    bar = ProgressItem("SegmentAnalyses")
                    self.list_widget.layout().addWidget(bar)
                    self.items["SegmentAnalyses"] = bar
                else:
                    bar = self.items["SegmentAnalyses"]
                bar.progress_bar.setValue(n_analyses_done / np.clip(n_analyses, 1, None) * 100)
                progress_segmentation = n_analyses_done /  np.clip(n_analyses, 1, None)

            if "screenshot_analyses" in data:
                n_analyses = len(self.main_window.project.screenshots) * len(data["screenshot_analyses"])
                n_analyses_done = 0
                analyses_to_do = data["screenshot_analyses"]
                for s in self.main_window.project.screenshots:
                    for q in analyses_to_do:
                        found = False
                        for a in s.connected_analyses:
                            if a.target_classification_object is None:
                                continue
                            if a.analysis_job_class == q[0] and a.target_classification_object.name == q[1]:
                                found = True
                                break
                        if found:
                            n_analyses_done += 1
                        else:
                            if q[2] not in self.missing_analyses:
                                self.missing_analyses[q[2]] = dict()
                            if q[0] not in self.missing_analyses[q[2]]:
                                self.missing_analyses[q[2]][q[0]] = dict()
                            if q[1] not in self.missing_analyses[q[2]][q[0]]:
                                self.missing_analyses[q[2]][q[0]][q[1]] = []
                            self.missing_analyses[q[2]][q[0]][q[1]].append(s)

                if "ScreenshotAnalyses" not in self.items:
                    bar = ProgressItem("ScreenshotAnalyses")
                    self.list_widget.layout().addWidget(bar)
                    self.items["ScreenshotAnalyses"] = bar
                else:
                    bar = self.items["ScreenshotAnalyses"]
                bar.progress_bar.setValue(n_analyses_done / np.clip(n_analyses, 1, None) * 100)
                progress_screenshots = n_analyses_done / np.clip(n_analyses, 1, None)

            if progress_screenshots >= ERCFilmColorsVIANPipeline.finished_threshold and \
                progress_segmentation >= ERCFilmColorsVIANPipeline.finished_threshold:
                self.onThresholdReached.emit()
                self.btn_RunAll.setEnabled(False)
            else:
                self.btn_RunAll.setEnabled(True)
        else:
            QMessageBox.information(self, "No Project loaded.", "You first have to load a project to analyse it.")

    def run_all(self):
        if self.main_window.project is None:
            QMessageBox.information(self, "No Project loaded.", "You first have to load a project to analyse it.")
            return
        if self.main_window.project.active_pipeline_script.uuid != ERCFilmColorsVIANPipeline.uuid:
            self.main_window.project.active_pipeline_script = self.main_window.project\
                .get_pipeline_script_by_uuid(ERCFilmColorsVIANPipeline.uuid)

        experiment = self.main_window.project.get_experiment_by_name("ERC Advanced Grant FilmColors")
        if experiment is None:
            QMessageBox.information(self, "No Experiment created.",
                                    "You first have to create a experiment with the"
                                    + ERCFilmColorsVIANPipeline.experiment.name + " template")
            return

        for priority in sorted(self.missing_analyses.keys()):
            for analysis_name in self.missing_analyses[priority].keys():
                analysis = self.main_window.eval_class(analysis_name)
                for clobj_name, containers in self.missing_analyses[priority][analysis_name].items():
                    clobj = experiment.get_classification_object_by_name(clobj_name)

                    if clobj is None:
                        log_warning("Classification Object not found")
                        continue
                    d = dict(
                        analysis= analysis(),
                        targets = containers,
                        parameters = None,
                        classification_objs = clobj
                    )
                    log_info("Pipeline Analysis: ", priority, analysis_name, clobj_name)
                    self.main_window.on_start_analysis(d)


class ProgressItem(QWidget):
    def __init__(self, name):
        super(ProgressItem, self).__init__()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel(name, self))
        self.progress_bar = QProgressBar(self)
        self.layout().addWidget(self.progress_bar)


class CorpusClientWidget(QWidget):
    def __init__(self, parent, corpus_client:CorpusClient, main_window):
        super(CorpusClientWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/CorpusClientWidget2.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        self.main_window = main_window
        self.btn_Connect.setStyleSheet("QPushButton{background-color: rgb(17, 17, 17);}")
        self.dbproject = None
        self.checkout_state = 0

        self.corpus_client.onConnectionEstablished.connect(self.on_connected)
        self.corpus_client.onDisconnect.connect(self.on_disconnected)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))
        self.btn_Options.clicked.connect(self.on_options)
        self.btn_Commit.clicked.connect(self.on_commit)
        self.btn_Commit.setEnabled(False)
        self.btn_Connect.setEnabled(True)
        self.btn_Connect.clicked.connect(self.on_connect)

        # self.comboBox_Corpora.addItem("ERC FilmColors") #type:QComboBox
        # self.comboBox_Corpora.currentTextChanged.connect(self.on_corpus_changed)
        #
        # #  self.btn_.clicked.connect(self.corpus_client.connect)
        #
        # self.on_contributor_update(self.main_window.settings.CONTRIBUTOR)
        self.show()

    def on_connect(self):
        if self.corpus_client.is_connected:
            QMessageBox.information(self, "Already Connected", "You are already connected to the WebApp.")
            self.on_connected()
            return

        ret = False
        if self.main_window.settings.CONTRIBUTOR.token is not None:
            ret = self.corpus_client.connect_webapp(self.main_window.settings.CONTRIBUTOR)['success']

        if self.main_window.settings.CONTRIBUTOR.token is None or ret is False:
            dialog = WebAppLoginDialog(self.main_window, self.corpus_client)
            dialog.show()
        else:
            self.on_disconnected()

    def on_options(self):
        menu = CorpusOptionMenu(self, self.corpus_client)
        menu.popup(QCursor.pos())

    @pyqtSlot(object)
    def on_connected(self):
        self.btn_Commit.setEnabled(True)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp.png"))

    @pyqtSlot(object)
    def on_disconnected(self):
        self.btn_Commit.setEnabled(False)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))

    def on_commit(self):
        dialog = CorpusCommitDialog(self.main_window, self.corpus_client)
        dialog.show()
        # if self.main_window.project is not None:
        #     self.corpus_client.commit(self.main_window.project, self.main_window.settings.CONTRIBUTOR)
        # pass


class WebAppLoginDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(WebAppLoginDialog, self).__init__(main_window)
        path = os.path.abspath("qt_ui/CorpusLoginDialog.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.corpus_client = corpus_client
        self.btn_Login.clicked.connect(self.on_ok)
        self.lineEdit_Email.setText(self.main_window.settings.CONTRIBUTOR.email)
        self.lineEdit_Password.setText(self.main_window.settings.CONTRIBUTOR.password)
        self.lineEdit_Password.setEchoMode(QLineEdit.Password)

    def on_ok(self):
        self.main_window.settings.CONTRIBUTOR.email = self.lineEdit_Email.text()
        self.main_window.settings.CONTRIBUTOR.password = self.lineEdit_Password.text()
        res = self.corpus_client.connect_webapp(self.main_window.settings.CONTRIBUTOR)['success']
        if res:
            self.corpus_client.onConnectionEstablished.emit(dict(success=True))
            self.close()
        else:
            QMessageBox.warning(self, "Could not Establish Connection",
                                "It has not been possible to login on the FilmColors Webapp, check your credentials again or create an account.")

    def on_login_tried(self):
        pass

    def on_cancel(self):
        self.close()


class CorpusOptionMenu(QMenu):
    def __init__(self, parent, corpus_client:CorpusClient):
        super(CorpusOptionMenu, self).__init__(parent)
        self.corpus_client = corpus_client
        self.a_disconnect = self.addAction("Disconnect")
        self.a_disconnect.triggered.connect(self.corpus_client.disconnect_corpus)


class CorpusCommitDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(CorpusCommitDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogHLayout.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        try:
            self.movies = self.corpus_client.corpus_interface.get_movies()
            self.persons = self.corpus_client.corpus_interface.get_persons()
            self.processes = self.corpus_client.corpus_interface.get_color_processes()
            self.genres = self.corpus_client.corpus_interface.get_genres()
            self.countries = self.corpus_client.corpus_interface.get_countries()
            self.companies = self.corpus_client.corpus_interface.get_companies()
        except Exception as e:
            self.persons = []
            self.persons = []
            self.processes = []
            self.genres = []
            self.countries = []
            self.companies = []
            log_error(e)

        self.filmography = FilmographyWidget2(self, main_window.project, persons=self.persons,
                                              processes=self.processes, genres=self.genres,
                                              countries = self.countries, companies=self.companies)

        self.lineEditMovieName = QLineEdit(self)
        if main_window.project is not None:
            self.lineEditMovieName.setText(self.main_window.project.movie_descriptor.movie_name)
        self.lt = QHBoxLayout()
        self.lt.addWidget(QLabel("Full Movie Name", self))
        self.lt.addWidget(self.lineEditMovieName)

        self.horizontalLayoutUpper.addItem(self.lt)
        self.horizontalLayoutUpper.addWidget(self.filmography)
        self.pushButton_Commit.clicked.connect(self.on_commit)
        self.pushButton_Cancel.clicked.connect(self.close)

    def on_check(self):

        pass

    def on_commit(self):
        for k, v in self.filmography.get_filmography().items():
            self.main_window.project.movie_descriptor.meta_data[k] = v
        self.main_window.project.movie_descriptor.movie_name = self.lineEditMovieName.text()
        if self.main_window.project is not None:
            self.corpus_client.commit(self.main_window.project, self.main_window.settings.CONTRIBUTOR)
        self.close()