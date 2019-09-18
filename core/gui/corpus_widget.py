import os

from PyQt5.QtWidgets import QWidget, QSplitter, QVBoxLayout, QTabWidget, \
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QSpacerItem, QSizePolicy, \
    QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal


from core.gui.ewidgetbase import EDockWidget, EditableListWidget
from core.gui.filmography_widget import FilmographyWidget2
from core.container.corpus import Corpus
from core.container.project import VIANProject


class CorpusDockWidget(EDockWidget):
    onCorpusChanged = pyqtSignal(object)

    def __init__(self, main_window):
        super(CorpusDockWidget, self).__init__(main_window, False)
        self.setWindowTitle("Corpus")
        self.w = QSplitter(Qt.Horizontal, self)

        self.list = CorpusList(self.w)
        self.info_widget = QTabWidget(self.w)
        self.general_widget = CorpusGeneralWidget(self.w)
        self.general_widget.setLayout(QVBoxLayout())
        self.filmography = FilmographyWidget2(self.w)
        self.w.addWidget(self.list)
        self.w.addWidget(self.info_widget)

        self.info_widget.addTab(self.general_widget, "General")
        self.info_widget.addTab(self.filmography, "Filmography")
        self.setWidget(self.w)

        self.file_menu = self.inner.menuBar().addMenu("File")
        self.a_new = self.file_menu.addAction("New Corpus")
        self.a_save = self.file_menu.addAction("Save Corpus")
        self.a_load = self.file_menu.addAction("Load Corpus")
        self.a_create_project = self.file_menu.addAction("Create Projects")
        self.a_import_project = self.file_menu.addAction("Import Projects")

        self.a_new.triggered.connect(self.on_new_corpus)
        self.a_save.triggered.connect(self.on_save_corpus)
        self.a_load.triggered.connect(self.on_load_corpus)
        self.general_widget.btn_EditTemplate.clicked.connect(self.on_edit_template)
        self.a_import_project.triggered.connect(self.on_import_projects)

        self.onCorpusChanged.connect(self.list.on_corpus_loaded)
        self.list.onSelectionChanged.connect(self.on_selection_changed)
        self.corpus = None

    def on_new_corpus(self):
        location = QFileDialog().getExistingDirectory(self, directory=self.main_window.settings.DIR_CORPORA)
        if os.path.isdir(location):
            self.corpus = Corpus("New Corpus", location, template_movie_path="data/template.mp4")
            self.onCorpusChanged.emit(self.corpus)

    def on_save_corpus(self):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return
        else:
            self.corpus.save(os.path.join(self.corpus.directory, self.corpus.name))

    def on_load_corpus(self):
        if self.corpus is not None:
            self.corpus.save(os.path.join(self.corpus.directory, self.corpus.name))
        file = QFileDialog.getOpenFileName(directory=self.main_window.settings.DIR_CORPORA)[0]
        if not os.path.isfile(file):
            return

        self.corpus = Corpus("NewCorpus").load(file)
        self.onCorpusChanged.emit(self.corpus)

    def on_import_projects(self):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return
        file = QFileDialog.getOpenFileName(directory=self.main_window.settings.DIR_CORPORA)[0]
        if not os.path.isfile(file):
            return
        self.corpus.add_project(file=file)

    def on_edit_template(self):
        if self.corpus is None:
            return
        if self.main_window.project is not None:
            self.main_window.on_save_project()
        self.main_window.project = self.corpus.template
        self.main_window.dispatch_on_loaded()

    def on_selection_changed(self, selection):
        if len(selection) > 0:
            project = selection[0].meta
            print(project.name, project)

    def on_save_triggered(self):
        if self.corpus is not None:
            self.on_save_corpus()

class CorpusList(EditableListWidget):
    def __init__(self, parent):
        super(CorpusList, self).__init__(parent)
        self.projects = dict()
        super(CorpusList, self).add_item("No Corpus Loaded", None)


    def on_corpus_loaded(self, corpus:Corpus):
        if corpus is None:
            self.setEnabled(False)
            self.add_item("No Corpus Loaded", None)
        else:
            try:
                self.remove_item("No Corpus Loaded")
            except:
                pass
            self.add_item("No Projects Added yet.", None)
            for uuid, p in corpus.projects_loaded.items():
                self.on_project_added(p)
            self.setEnabled(True)

        corpus.onProjectAdded.connect(self.on_project_added)
        corpus.onProjectRemoved.connect(self.on_project_removed)

    def on_project_added(self, project:VIANProject):
        if len(self.projects.keys()) == 0:
            try:
                self.remove_item("No Projects Added yet.")
            except:
                pass
        if project.uuid not in self.projects:
            itm = self.add_item(project.name, project)
            self.projects[project.uuid] = itm
        pass

    def on_project_removed(self, project):
        if project.uuid in self.projects:
            itm = self.projects[project.uuid]
            self.remove_item(itm.name)
            self.projects.pop(project.uuid)
        pass

class CorpusGeneralWidget(QWidget):
    def __init__(self, parent):
        super(CorpusGeneralWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())

        self.w_name = QWidget(self)
        self.w_name.setLayout(QHBoxLayout())
        self.w_name.layout().addWidget(QLabel("Corpus Name"))
        self.textEdit_Name = QLineEdit(self.w_name)
        self.w_name.layout().addWidget(self.textEdit_Name)
        self.layout().addWidget(self.w_name)
        
        self.btn_EditTemplate = QPushButton("Edit Template", self)
        self.layout().addWidget(self.btn_EditTemplate)

        self.layout().addItem(QSpacerItem(1,1,QSizePolicy.Preferred, QSizePolicy.Expanding))
        # self.w_name = QWidget(self)
        # self.w_name.setLayout(QHBoxLayout())
        # self.w_name.layout().addWidget(QLabel("Corpus Name"))
        # self.textEdit_Name = QTextEdit(self.w_name)
        # self.w_name.layout().addWidget(self.textEdit_Name)


