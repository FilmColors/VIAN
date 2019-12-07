import os
from typing import Optional
from PyQt5.QtWidgets import QWidget, QSplitter, QVBoxLayout, QTabWidget, \
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QSpacerItem, QSizePolicy, \
    QFileDialog, QMessageBox, QFrame, QStackedWidget, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5 import uic

from core.gui.ewidgetbase import EDockWidget, EditableListWidget
from core.gui.filmography_widget import FilmographyWidget2
from core.container.corpus import Corpus
from core.container.project import VIANProject
from core.data.log import log_error


class CorpusDockWidget(EDockWidget):
    onCorpusChanged = pyqtSignal(object)
    onSelectionChanged = pyqtSignal(object)

    def __init__(self, main_window):
        super(CorpusDockWidget, self).__init__(main_window, False)
        self.setWindowTitle("Corpus")
        self.w = QSplitter(Qt.Horizontal, self)
        self.in_template_mode = False
        self.last_project = None

        self.list = CorpusList(self.w, self)
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
        self.a_create_project.triggered.connect(self.on_create_project)
        self.a_load.triggered.connect(self.on_load_corpus)
        self.general_widget.btn_EditTemplate.clicked.connect(self.on_edit_template)
        self.general_widget.btn_CloseTemplate.clicked.connect(self.on_close_template)
        self.general_widget.btn_SaveTemplate.clicked.connect(self.on_save_template)

        self.a_import_project.triggered.connect(self.on_import_projects)

        self.onCorpusChanged.connect(self.list.on_corpus_loaded)
        self.onCorpusChanged.connect(self.general_widget.on_corpus_loaded)

        self.general_widget.btn_ImportTemplate.clicked.connect(self.import_template)
        self.filmography.onFilmographyChanged.connect(self.save_current_project)

        self.list.onSelectionChanged.connect(self.on_selection_changed)

        self.corpus = None  # type: Optional[Corpus]
        self.current_project = None # type: Optional[VIANProject]

    def on_new_corpus(self):
        location = QFileDialog().getExistingDirectory(self, directory=self.main_window.settings.DIR_CORPORA)
        if os.path.isdir(location):
            self.corpus = Corpus("New Corpus", location, template_movie_path="data/template.mp4")
            self.corpus.save(os.path.join(self.corpus.directory, self.corpus.name))
            self.onCorpusChanged.emit(self.corpus)
            self.show()
            self.raise_()

    def on_save_corpus(self):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return
        else:
            self.corpus.save()
            self.main_window.settings.add_recent_corpus2(self.corpus)

    def on_create_project(self):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return

        file = QFileDialog.getOpenFileName(self, caption="Select a Movie File")[0]
        if not os.path.isfile(file):
            return
        self.main_window.on_new_project(file, add_to_current_corpus=True)

    def on_remove_project(self, name, item):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return
        project = item.meta
        if project is None:
            return
        self.corpus.remove_project(project)

    def on_load_corpus(self):
        if self.corpus is not None:
            self.corpus.save(os.path.join(self.corpus.directory, self.corpus.name))
        file = QFileDialog.getOpenFileName(directory=self.main_window.settings.DIR_CORPORA)[0]
        if not os.path.isfile(file):
            return
        self.load_corpus(file)

    def load_corpus(self, file):
        self.corpus = Corpus("NewCorpus").load(file)
        self.show()
        self.raise_()
        self.main_window.settings.add_recent_corpus2(self.corpus)
        self.onCorpusChanged.emit(self.corpus)
        return self.corpus

    def on_import_projects(self):
        if self.corpus is None:
            QMessageBox.warning(self, "No Corpus loaded", "No corpus has been loaded yet. Either load one or create "
                                                          "a new one in the file menu")
            return
        file = QFileDialog.getOpenFileName(directory=self.main_window.settings.DIR_CORPORA)[0]
        if not os.path.isfile(file):
            return
        self.corpus.add_project(file=file)

        self.corpus.save()
        self.main_window.settings.add_recent_corpus2(self.corpus)

    def on_edit_template(self):
        if self.corpus is None:
            return
        if self.main_window.project is not None:
            self.main_window.on_save_project()
            self.last_project = self.main_window.project.path
        self.main_window.project = self.corpus.template
        self.main_window.dispatch_on_loaded()
        self.set_in_template_mode(True)

    def on_close_template(self):
        if self.main_window.project is self.corpus.template:
            self.corpus.save()
        if self.last_project is not None:
            self.main_window.load_project(self.last_project)
        self.set_in_template_mode(False)
        self.last_project = None

    def on_save_template(self):
        if self.corpus is not None:
            self.corpus.reload()
            self.corpus.apply_template_to_all()
        self.on_close_template()

    def import_template(self):
        file = QFileDialog.getOpenFileName(self, directory="data/templates", filter="*.viant")[0]
        if not os.path.isfile(file):
            return
        self.corpus.import_template(file)
        self.on_save_triggered()

    def on_selection_changed(self, selection):
        try:
            if len(selection) > 0:
                project = selection[0].meta
                if project is None:
                    return
                self.filmography.set_filmography(project.movie_descriptor.meta_data)
                self.onSelectionChanged.emit(project)
                self.current_project = project
                self.general_widget.on_project_changed(self.current_project)
            else:
                self.current_project = None
        except Exception as e:
            raise e

    def save_current_project(self):
        if self.current_project is not None:
            self.current_project.movie_descriptor.meta_data = self.filmography.get_filmography()
            self.current_project.store_project()
            self.corpus.reload(self.current_project)

    def on_save_triggered(self):
        if self.corpus is not None:
            self.on_save_corpus()
            self.main_window.settings.add_recent_corpus2(self.corpus)
            self.corpus.reload()

    def on_close_corpus(self):
        if self.corpus is not None:
            self.corpus.save(os.path.join(self.corpus.directory, self.corpus.name))
            self.corpus = None
            self.onCorpusChanged.emit(None)

    def set_in_template_mode(self, state):
        if state:
            self.general_widget.templateStack.setCurrentIndex(1)
        else:
            self.general_widget.templateStack.setCurrentIndex(0)
        self.in_template_mode = state


class CorpusList(EditableListWidget):
    def __init__(self, parent, corpus_widget):
        super(CorpusList, self).__init__(parent)
        self.corpus_widget = corpus_widget
        self.projects = dict()
        super(CorpusList, self).add_item("No Corpus Loaded", None)
        self.onItemDeleted.connect(self.remove_from_corpus)

    def on_corpus_loaded(self, corpus:Corpus):
        if corpus is None:
            self.setEnabled(False)
            self.add_item("No Corpus Loaded", None)
        else:
            try:
                self.remove_item("No Corpus Loaded")
            except:
                pass
            if len(corpus.projects_loaded) == 0:
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

    def on_project_removed(self, project):
        if project.uuid in self.projects:
            itm = self.projects[project.uuid]
            self.projects.pop(project.uuid)
            if project.name in self.item_index:
                self.remove_item(itm.name)

    def remove_from_corpus(self, name, item):
        if item.meta is not None:
            self.corpus_widget.corpus.remove_project(item.meta)


class CorpusGeneralWidget(QWidget):
    def __init__(self, parent):
        super(CorpusGeneralWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())

        self.layout().addWidget(QLabel("Corpus Information", self))
        self.w_corpus = QFrame(self)
        self.w_corpus.setWindowTitle("Corpus Information")
        self.w_corpus.setLayout(QVBoxLayout())

        self.layout().addWidget(self.w_corpus)
        self.lt_actions = QHBoxLayout(self)
        self.layout().addWidget(QLabel("Template", self))
        self.layout().addItem(self.lt_actions)

        self.layout().addWidget(QLabel("Project Information", self))
        self.w_movie = CorpusMovieWidget(self)
        self.layout().addWidget(self.w_movie)

        self.w_name = QWidget(self)
        self.w_name.setLayout(QHBoxLayout())
        self.w_name.layout().addWidget(QLabel("Corpus Name"))
        self.textEdit_Name = QLineEdit(self.w_name)
        self.textEdit_Name.editingFinished.connect(self.on_name_changed)
        self.w_name.layout().addWidget(self.textEdit_Name)

        self.w_corpus.layout().addWidget(self.w_name)

        self.templateStack = QStackedWidget(self)
        self.templateStack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.lt_actions.addWidget(self.templateStack)
        self.template_widget_manage = QWidget(self.templateStack)
        self.template_widget_edit = QWidget(self.templateStack)
        self.templateStack.addWidget(self.template_widget_manage)
        self.templateStack.addWidget(self.template_widget_edit)

        self.template_widget_manage.setLayout(QGridLayout())
        self.template_widget_edit.setLayout(QGridLayout())

        self.btn_EditTemplate = QPushButton("Edit Template", self)
        self.template_widget_manage.layout().addWidget(self.btn_EditTemplate, 0, 0)

        self.btn_ImportTemplate = QPushButton("Import Template", self)
        self.template_widget_manage.layout().addWidget(self.btn_ImportTemplate, 0, 1)

        self.btn_SaveTemplate = QPushButton("Save Template", self)
        self.template_widget_edit.layout().addWidget(self.btn_SaveTemplate, 0, 0)

        self.btn_CloseTemplate = QPushButton("Close Template", self)
        self.template_widget_edit.layout().addWidget(self.btn_CloseTemplate, 0, 1)

        self.layout().addItem(QSpacerItem(1,1,QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.corpus = None
        self.setEnabled(False)

    def on_corpus_loaded(self, corpus):
        self.corpus = corpus
        if self.corpus is not None:
            self.textEdit_Name.setText(self.corpus.name)
            self.setEnabled(True)
        else:
            self.setEnabled(False)

    def on_name_changed(self):
        if self.corpus is not None:
            if self.textEdit_Name.text() != "":
                self.corpus.name = self.textEdit_Name.text()
            self.corpus.save()

    def on_project_changed(self, project):
        self.w_movie.set_project(project)


class CorpusMovieWidget(QWidget):
    def __init__(self, parent):
        super(CorpusMovieWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/CorpusEditorGeneral.ui")
        uic.loadUi(path, self)

        self.setLayout(QVBoxLayout())
        self.goto_dir = None
        self.btn_OpenDirectory.clicked.connect(self.on_goto)

    def set_project(self, project:VIANProject):
        if project is not None:
            self.lineEdit_Name.setText(project.name)
            self.lbl_Location.setText(project.path)
            self.goto_dir = project.folder
            try:
                self.spinBox_ItemID.setValue(int(project.movie_descriptor.movie_id.split("_")[0]))
                self.spinBox_ManifestationID.setValue(int(project.movie_descriptor.movie_id.split("_")[1]))
                self.spinBox_CopyID.setValue(int(project.movie_descriptor.movie_id.split("_")[2]))
            except Exception as e:
                log_error(e)
        else:
            self.lineEdit_Name.setText("")
            self.lbl_Location.setText("")
            self.goto_dir = None
            self.spinBox_ItemID.setValue(0)
            self.spinBox_ManifestationID.setValue(0)
            self.spinBox_CopyID.setValue(0)

    def on_goto(self):
        import sys, subprocess
        if self.goto_dir is not None:
            if sys.platform == "win32":
                subprocess.run("explorer " + self.goto_dir, shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", self.goto_dir])
            else:
                try:
                    subprocess.run(["nautilus", self.goto_dir])
                except:
                    pass
