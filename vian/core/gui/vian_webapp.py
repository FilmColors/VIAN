import numpy as np
from vian.core.data.log import log_debug
from vian.core.data.computation import create_icon
from vian.core.data.webapp import WebAppCorpusInterface
from vian.core.data.interfaces import IProjectChangeNotify
from vian.core.gui.ewidgetbase import *
from vian.extensions.pipelines.ercfilmcolors import ERCFilmColorsVIANPipeline
from vian.core.gui.misc.filmography_widget import FilmographyWidget2
from vian.core.container.project import VIANProject

from vian.core.data.log import log_warning, log_info


class WebAppCorpusDock(EDockWidget, IProjectChangeNotify):
    runAllAnalyses = pyqtSignal()
    onRunAnalysis = pyqtSignal(object)

    def __init__(self, main_window):
        super(WebAppCorpusDock, self).__init__(main_window, False)
        self.setWindowTitle("WebApp")
        self.central = QWidget(self)
        self.setWidget(self.central)
        self.central.setLayout(QVBoxLayout())

        self.corpus_widget = CorpusClientWidget(self, main_window)
        self.central.layout().addWidget(self.corpus_widget)
        self.stack = QStackedWidget(self)
        self.central.layout().addWidget(self.stack)
        self.progress_widget = CorpusProgressWidget(self, self, main_window)
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
        # self.progress_widget.btn_RunAll.setEnabled(False)

    def on_threshold_reached(self):
        self.btn_Commit.setEnabled(True)


class CorpusProgressWidget(QWidget):
    onThresholdReached = pyqtSignal()
    onRunAll = pyqtSignal()


    def __init__(self, parent, corpus_widget, main_window):
        super(CorpusProgressWidget, self).__init__(parent)
        self.main_window = main_window
        self.corpus_widget = corpus_widget

        self.setLayout(QVBoxLayout())
        self.btn_checkFiles = QPushButton("1. Check Project")
        self.btn_checkFiles.clicked.connect(self.update_state)

        self.btn_runAll = QPushButton("2. Run All Analyses")
        self.btn_runAll.clicked.connect(self.compute_missing)

        self.layout().addWidget(self.btn_checkFiles)
        self.list_widget = QWidget(self)
        self.list_widget.setLayout(QVBoxLayout())
        self.layout().addWidget(self.list_widget)
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.layout().addWidget(self.spacer)
        self.layout().addWidget(self.btn_runAll)

        # self.lbl_Instructions = QLabel("The webapp requires a specific set of analyses performed before upload. "
        #                                "Currently these requirements are not met. To perform these analyses do the following:\n "
        #                                "1. Go to the pipeline manager\n"
        #                                "2. Select the ERCFilmColors Pipeline\n"
        #                                "3. In the Dropdown, select the ERC Advanced Grant FilmColors Experiment\n"
        #                                "4. Press 'Run All Missing Analyses'")
        # self.lbl_Instructions.setWordWrap(True)

        self.requirements = ERCFilmColorsVIANPipeline.requirements
        # self.layout().addWidget(self.lbl_Instructions)
        self.items = dict()
        self.missing_analyses = dict()

    @pyqtSlot()
    def update_state(self):
        data = self.requirements
        log_debug("Requirements:", data)
        if data is None:
            return
        self.missing_analyses = dict()

        res = dict()
        if self.main_window.project is not None:
            missing = self.main_window.project.get_missing_analyses(self.requirements)

            u = [
                ("ScreenshotAnalyses", "screenshot_analyses", "progress_screenshots"),
                ("SegmentAnalyses", "segment_analyses", "progress_segmentation")
            ]

            # Apply the result to the three progress bars
            for (bar_name, item_name, var) in u:
                n_analyses = missing[item_name][1]
                n_analyses_done = missing[item_name][2]
                # t = missing[item_name]
                if bar_name not in self.items:
                    bar = ProgressItem(bar_name)
                    self.list_widget.layout().addWidget(bar)
                    self.items[bar_name] = bar
                else:
                    bar = self.items[bar_name]

                bar.progress_bar.setValue(n_analyses_done / np.clip(n_analyses, 1, None) * 100)
                res[var] = n_analyses_done / np.clip(n_analyses, 1, None)
                bar.progress_bar.setValue(n_analyses_done / np.clip(n_analyses, 1, None) * 100)

            if res["progress_screenshots"] >= ERCFilmColorsVIANPipeline.finished_threshold and \
                res["progress_segmentation"] >= ERCFilmColorsVIANPipeline.finished_threshold:
                self.onThresholdReached.emit()
                # self.lbl_Instructions.setVisible(False)
            else:
                pass
                # self.lbl_Instructions.setVisible(True)
        else:
            QMessageBox.information(self, "No Project loaded.", "You first have to load a project to analyse it.")

    def compute_missing(self):
        missing = self.main_window.project.get_missing_analyses(ERCFilmColorsVIANPipeline.requirements)
        p = self.main_window.project #type:VIANProject

        for k, (container_type, _, _) in missing.items():
            for priority, by_priority in container_type.items():
                for analysis_name, by_cl_obj in by_priority.items():
                    analysis = self.main_window.eval_class(analysis_name)
                    for clobj_name, containers in by_cl_obj.items():
                        clobj = p.get_classification_object_global(clobj_name)
                        if clobj is None:
                            log_warning("Classification Object not found")
                            continue
                        d = dict(
                            analysis=analysis(),
                            targets=containers,
                            parameters=None,
                            classification_objs=clobj
                        )
                        log_info("Pipeline Analysis: ", priority, analysis_name, clobj_name)
                        self.corpus_widget.onRunAnalysis.emit(d)


class ProgressItem(QWidget):
    def __init__(self, name):
        super(ProgressItem, self).__init__()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel(name, self))
        self.progress_bar = QProgressBar(self)
        self.layout().addWidget(self.progress_bar)


class CorpusClientWidget(QWidget):
    def __init__(self, parent, main_window):
        super(CorpusClientWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/CorpusClientWidget2.ui")
        uic.loadUi(path, self)

        self.corpus_client = WebAppCorpusInterface()
        self.corpus_client_thread = QThread()
        self.corpus_client.moveToThread(self.corpus_client_thread)
        self.corpus_client_thread.start()

        self.main_window = main_window
        self.btn_Connect.setStyleSheet("QPushButton{background-color: rgb(17, 17, 17);}")
        self.dbproject = None
        self.checkout_state = 0

        self.corpus_client.signals.onConnected.connect(self.on_connected)
        self.corpus_client.signals.onConnectionFailed.connect(self.on_disconnected)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))
        self.btn_login.clicked.connect(self.on_connect)
        self.btn_Connect.setEnabled(True)
        self.btn_Connect.clicked.connect(self.on_connect)

        self.show()

    def on_connect(self):
        if self.corpus_client.connected():
            QMessageBox.information(self, "Already Connected", "You are already connected to the WebApp.")
            self.on_connected()
            return

        ret = False
        if self.main_window.settings.CONTRIBUTOR is not None:
            ret = self.corpus_client.login(self.main_window.settings.CONTRIBUTOR)['success']

        if ret is False:
            dialog = WebAppLoginDialog(self.main_window, self.corpus_client)
            dialog.show()

    @pyqtSlot(object)
    def on_connected(self):
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp.png"))

    @pyqtSlot(object)
    def on_disconnected(self):
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))

    def on_commit(self):
        if self.corpus_client is None:
            QMessageBox.information(self, "Not Connected", "Please login to the WebApp first.")
        dialog = CorpusCommitDialog(self.main_window, self.corpus_client)
        dialog.show()


class WebAppLoginDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:WebAppCorpusInterface):
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
        res = self.corpus_client.login(self.main_window.settings.CONTRIBUTOR)

        if not res['success']:
            QMessageBox.warning(self, "Could not Establish Connection",
                                "It has not been possible to login on the FilmColors Webapp, "
                                "check your credentials again or create an account.")

    def on_cancel(self):
        self.close()


# class CorpusOptionMenu(QMenu):
#     def __init__(self, parent, corpus_client:CorpusClient):
#         super(CorpusOptionMenu, self).__init__(parent)
#         self.corpus_client = corpus_client
#         self.a_disconnect = self.addAction("Disconnect")
#         self.a_disconnect.triggered.connect(self.corpus_client.disconnect_corpus)
#

class CorpusCommitDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:WebAppCorpusInterface):
        super(CorpusCommitDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogHLayout.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        try:
            self.movies = self.corpus_client.get_movies()
            self.persons = self.corpus_client.get_persons()
            self.processes = self.corpus_client.get_color_processes()
            self.genres = self.corpus_client.get_genres()
            self.countries = self.corpus_client.get_countries()
            self.companies = self.corpus_client.get_companies()
            self.corporas = self.corpus_client.get_corpora()
        except Exception as e:
            self.persons = []
            self.persons = []
            self.processes = []
            self.genres = []
            self.countries = []
            self.companies = []
            self.corporas = []
            log_error(e)

        self.lineEdit_Corpus = QLineEdit(self)
        q = QCompleter([p['name'] for p in self.corporas])
        self.lineEdit_Corpus.setCompleter(q)


        self.filmography = FilmographyWidget2(self, main_window.project, persons=self.persons,
                                              processes=self.processes, genres=self.genres,
                                              countries = self.countries, companies=self.companies)

        self.lineEditMovieName = QLineEdit(self)
        if main_window.project is not None:
            self.lineEditMovieName.setText(self.main_window.project.movie_descriptor.movie_name)
        self.lt = QHBoxLayout()
        self.lt.addWidget(QLabel("Corpus", self))
        self.lt.addWidget(self.lineEdit_Corpus)
        self.lt2 = QHBoxLayout()
        self.lt2.addWidget(QLabel("Full Movie Name", self))
        self.lt2.addWidget(self.lineEditMovieName)

        self.horizontalLayoutUpper.addItem(self.lt)
        self.horizontalLayoutUpper.addItem(self.lt2)
        self.horizontalLayoutUpper.addWidget(self.filmography)
        self.pushButton_Commit.clicked.connect(self.on_commit)
        self.pushButton_Cancel.clicked.connect(self.close)

    def on_check(self):

        pass

    def on_commit(self):
        for k, v in self.filmography.get_filmography().items():
            self.main_window.project.movie_descriptor.meta_data[k] = v
        self.main_window.project.movie_descriptor.movie_name = self.lineEditMovieName.text()
        self.main_window.project.meta_data['corpus_name'] = self.lineEdit_Corpus.text()

        if self.main_window.project is not None:
            self.corpus_client.commit(self.main_window.project, self.main_window.settings.CONTRIBUTOR)
        self.close()