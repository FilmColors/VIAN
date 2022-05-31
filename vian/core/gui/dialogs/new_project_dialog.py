import glob
import os
import hashlib
import threading
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCompleter, QFileDialog, QMessageBox, QTabWidget, QCheckBox, QLineEdit, QVBoxLayout, QHBoxLayout,QSpacerItem, QSizePolicy, QWidget, QScrollArea, QComboBox
from vian.core.container.project import VIANProject, VIAN_PROJECT_EXTENSION
from vian.core.data.enums import MovieSource
from vian.core.gui.ewidgetbase import EDialogWidget
from vian.core.data.importers import ELANProjectImporter
from vian.core.data.computation import images_to_movie
from vian.core.data.settings import get_vian_data
from vian.core.gui.misc.utils import dialog_with_margin


class NewProjectDialog(EDialogWidget):
    def __init__(self, parent, settings, movie_path = "", elan_segmentation = None, add_to_current_corpus = False):
        super(NewProjectDialog, self).__init__(parent, parent, "https://www.vian.app/static/manual/step_by_step/project_management/create_project.html")
        path = os.path.abspath("qt_ui/DialogNewProject.ui")
        uic.loadUi(path, self)
        self.settings = settings
        self.templates = []
        self.auto_naming = False
        self.movie_checksum = None
        self.checksum_thread = None

        self.elan_segmentation = elan_segmentation
        if movie_path == "":
            self.project_dir = settings.DIR_PROJECTS
        else:
            mp = movie_path.replace("\\", "/")
            mp = movie_path.split("/")
            path = ""
            for i in range(len(mp) -1):
                path += mp[i] + "/"
            self.project_dir = path

        self.project = VIANProject(path =None, name="New Project")
        self.path_set_from_dialog = False

        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)
        # Set DVD as default
        self.comboBox_Source.setCurrentText(MovieSource.DVD.name)

        self.find_templates()

        self.lineEdit_ProjectPath.setText(settings.DIR_PROJECTS)

        self.cB_AutomaticNaming.stateChanged.connect(self.on_automatic_naming_changed)
        self.lineEdit_ProjectName.textChanged.connect(self.on_proj_name_changed)
        self.lineEdit_ProjectPath.textChanged.connect(self.on_proj_path_changed)
        self.btn_BrowseProject.clicked.connect(self.on_browse_project_path)

        self.lineEdit_Name.editingFinished.connect(self.on_desc_name_changed)
        # self.lineEdit_ID.editingFinished.connect(self.on_desc_id_changed)

        self.spinBox_ID_0.valueChanged.connect(self.on_desc_id_changed)
        self.spinBox_ID_1.valueChanged.connect(self.on_desc_id_changed)
        self.spinBox_ID_2.valueChanged.connect(self.on_desc_id_changed)

        # self.lineEdit_Year.editingFinished.connect(self.on_desc_year_changed)
        self.spinBox_Year.valueChanged.connect(self.on_desc_year_changed)
        self.comboBox_Source.currentIndexChanged.connect(self.on_desc_ource_changed)
        self.btn_BrowseMovie.clicked.connect(self.on_browse_movie_path)

        self.comboBoxCorpus.addItems(self.settings.recent_corpora_2.keys())
        self.comboBoxCorpus.currentTextChanged.connect(self.on_corpus_changed)

        self.lineEdit_MoviePath.textChanged.connect(self.on_movie_path_changed)

        if add_to_current_corpus:
            if self.main_window.corpus_widget.corpus is not None:
                try:
                    self.comboBoxCorpus.setCurrentText(self.main_window.corpus_widget.corpus.name)
                except Exception as e:
                    print(e)

        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_ok)

        self.lineEdit_MoviePath.setText(movie_path)
        self.project.movie_descriptor.set_movie_path(movie_path)
        # self.checkBox_FromImages.stateChanged.connect(self.on_from_images_changed)

        self.set_project_path()

        self.image_paths = []

        self.setOkButtonFunc()

        self.show()

    def on_corpus_changed(self):
        if self.comboBoxCorpus.currentText() != "None":
            self.comboBox_Template.setEnabled(False)
        else:
            self.comboBox_Template.setEnabled(True)

    def on_automatic_naming_changed(self):
        auto = self.cB_AutomaticNaming.isChecked()
        if auto:
            self.lineEdit_ProjectName.setEnabled(False)
            self.lineEdit_ProjectName.textChanged.disconnect()
        else:
            self.lineEdit_ProjectName.setEnabled(True)
            self.lineEdit_ProjectName.textChanged.connect(self.on_proj_name_changed)
        self.auto_naming = auto
        self.set_project_path()

    def find_templates(self):
        templates = glob.glob(self.settings.DIR_TEMPLATES + "*.viant")
        templates.extend(glob.glob(get_vian_data("templates/" + "*.viant")))

        self.templates.append(None)
        self.comboBox_Template.addItem("No Template")
        erc_template = None
        for t in templates:
            self.templates.append(t)
            name = t.replace("\\" , "/").split("/").pop().replace(".viant", "")
            self.comboBox_Template.addItem(name)
            if "ERC" in name:
                erc_template = name
        if erc_template is not None:
            self.comboBox_Template.setCurrentText(erc_template)


    def set_project_path(self):
        #self.project.path = os.path.join(self.project_dir, self.project_name, self.project_name + VIAN_PROJECT_EXTENSION)

        if self.auto_naming:
            name = self.get_movie_id() + "_" + \
                                self.lineEdit_Name.text().replace(" ", "_") + "_" + \
                                str(self.spinBox_Year.value()) + "_" + \
                                self.comboBox_Source.currentText()

            self.lineEdit_ProjectName.setText(name)

    def on_proj_name_changed(self):
        self.setOkButtonFunc()

    def on_proj_path_changed(self):
        self.setOkButtonFunc()

    def on_browse_project_path(self):
        path = QFileDialog.getExistingDirectory(caption="Select Root Directory of the Project", directory=self.project_dir)
        self.project_dir = path
        self.lineEdit_ProjectPath.setText(self.project_dir)

    def on_browse_movie_path(self):
        path = QFileDialog.getOpenFileName()[0]
        self.lineEdit_MoviePath.setText(path)
        self.path_set_from_dialog = True
        name = os.path.splitext(os.path.split(path)[1])[0]
        self.lineEdit_Name.setText(name)

    def on_desc_name_changed(self):
        self.project.movie_descriptor.movie_name = self.lineEdit_Name.text()
        self.set_project_path()

    def get_movie_id(self):
        return str(self.spinBox_ID_0.value()) + "_" + str(self.spinBox_ID_1.value()) + "_" + str(self.spinBox_ID_2.value())

    def on_desc_id_changed(self):
        id_m = self.get_movie_id()
        self.project.movie_descriptor.movie_id = id_m
        self.set_project_path()

    def on_desc_year_changed(self):
        self.project.movie_descriptor.year = self.spinBox_Year.value()
        self.set_project_path()

    def on_desc_ource_changed(self):
        self.project.movie_descriptor.source = self.comboBox_Source.currentText()
        self.set_project_path()

    def calculate_checksum(self, path):
        self.movie_checksum = hashlib.md5(open(path,'rb').read()).hexdigest()
        self.setOkButtonFunc()

    def on_movie_path_changed(self):
        self.movie_checksum = None
        if not self.checksum_thread is None:
            self.checksum_thread.join()
        if os.path.isfile(self.lineEdit_MoviePath.text()):
            self.checksum_thread = threading.Thread(target=self.calculate_checksum, args=(self.lineEdit_MoviePath.text(),))
            self.checksum_thread.start()
        self.setOkButtonFunc()

    def setOkButtonFunc(self):
        status_text = ""

        if self.lineEdit_ProjectName.text() is "":
            self.btn_OK.setEnabled(False)
            status_text = "Set a project name"

        if not status_text == "": #if there is no project name, we set this message and return immediately
            self.label_status.setText(status_text)
            return

        if os.path.isdir(self.lineEdit_ProjectPath.text()):
            if not self.lineEdit_ProjectName.text() is "" and os.path.isdir(os.path.join(self.lineEdit_ProjectPath.text(), self.lineEdit_ProjectName.text())):
                self.btn_OK.setEnabled(False)
                status_text = "Change Project Name or Project Location. Folder already exists"
        else:
            self.btn_OK.setEnabled(False)
            status_text = "Project Location does not exist"

        if not status_text == "": #if there is an issue with the location, we set this message and return immediately
            self.label_status.setText(status_text)
            return

        if not os.path.isfile(self.lineEdit_MoviePath.text()):
            self.btn_OK.setEnabled(False)
            status_text = "Movie path not found"
        else:
            if self.movie_checksum == None:
                self.btn_OK.setEnabled(False)
                status_text = "Movie checksum being calculated"
            else:
                self.btn_OK.setEnabled(True)
                self.label_status.setText("")

        self.label_status.setText(status_text)

    def on_cancel(self):
        self.close()

    def on_ok(self):
        template = self.templates[self.comboBox_Template.currentIndex()]
        copy_movie = self.comboBox_Move.currentText()

        self.project.path = os.path.join(self.lineEdit_ProjectPath.text(), self.lineEdit_ProjectName.text(),
                                         self.lineEdit_ProjectName.text() + VIAN_PROJECT_EXTENSION)
        self.project.folder = os.path.join(self.lineEdit_ProjectPath.text(), self.lineEdit_ProjectName.text())

        self.project.movie_descriptor.set_movie_path(self.lineEdit_MoviePath.text())

        if self.elan_segmentation is not None:
            ELANProjectImporter(self.main_window).apply_import(self.project, self.elan_segmentation)

        corpus = None
        if self.comboBoxCorpus.currentText() != "None":
            corpus = self.main_window.settings.recent_corpora_2[self.comboBoxCorpus.currentText()]
        print(corpus)
        self.main_window.new_project(self.project, template, copy_movie=copy_movie, corpus_path=corpus)
        self.close()
