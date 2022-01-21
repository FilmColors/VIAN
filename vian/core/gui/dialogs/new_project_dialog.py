import glob
import os
import cv2

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
        self.project_name = "project_name"
        self.auto_naming = False

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

        self.tabWidget.removeTab(1)
        self.cB_AutomaticNaming.stateChanged.connect(self.on_automatic_naming_changed)
        self.lineEdit_ProjectName.textChanged.connect(self.on_proj_name_changed)
        self.lineEdit_ProjectPath.editingFinished.connect(self.on_proj_path_changed)
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

        if add_to_current_corpus:
            if self.main_window.corpus_widget.corpus is not None:
                try:
                    self.comboBoxCorpus.setCurrentText(self.main_window.corpus_widget.corpus.name)
                except Exception as e:
                    print(e)

        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)

        self.lineEdit_MoviePath.setText(movie_path)
        self.project.movie_descriptor.set_movie_path(movie_path)
        # self.checkBox_FromImages.stateChanged.connect(self.on_from_images_changed)

        self.lineEdit_ProjectName.setText(self.project_name)
        self.set_project_path()

        self.image_paths = []

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
        self.project.folder = self.project_dir
        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name + VIAN_PROJECT_EXTENSION

        if self.auto_naming:
            self.project_name = self.get_movie_id() + "_" + \
                                self.lineEdit_Name.text().replace(" ", "_") + "_" + \
                                str(self.spinBox_Year.value()) + "_" + \
                                self.comboBox_Source.currentText()
            self.project.name = self.project_name
            self.lineEdit_ProjectName.setText(self.project_name)
            self.lineEdit_ProjectPath.setText(self.project.folder)

        else:
            self.project.name = self.project_name
            self.lineEdit_ProjectPath.setText(self.project.folder)

    def on_proj_name_changed(self):
        self.project_name = self.lineEdit_ProjectName.text()
        if not self.path_set_from_dialog:
            self.set_project_path()

    def on_proj_path_changed(self):
        path = self.lineEdit_ProjectPath.text()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Directory not Found", "The inserted path doesn't seem to be a valid directory. "
                                      "\n\n Please insert a valid Directory path, or use the \"Browse\" Button.")
            self.project_dir = ""
            self.lineEdit_ProjectPath.setText("None")
        else:
            self.project_dir = path

    def on_browse_project_path(self):
        path = QFileDialog.getExistingDirectory(caption="Select Root Directory of the Project", directory=self.project_dir)
        self.project_dir = path
        self.lineEdit_ProjectPath.setText(self.project_dir)

    def on_browse_movie_path(self):
        # if self.checkBox_FromImages.isChecked() is False:
            path = QFileDialog.getOpenFileName()[0]
            # self.project.movie_descriptor.movie_path = path
            self.lineEdit_MoviePath.setText(path)
            self.path_set_from_dialog = True
            name = os.path.splitext(os.path.split(path)[1])[0]
            self.lineEdit_Name.setText(name)
        # else:
        #     self.image_paths = QFileDialog.getOpenFileNames()[0]

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

    def on_desc_movie_path_changed(self):
        if not os.path.isfile(self.lineEdit_MoviePath.text()):
            self.lineEdit_MoviePath.setText("Not a Path")
            return
        self.project.movie_descriptor.set_movie_path(self.lineEdit_MoviePath.text())

    def on_cancel(self):
        self.close()

    def on_ok(self):
        template = self.templates[self.comboBox_Template.currentIndex()]
        copy_movie = self.comboBox_Move.currentText()

        # Checking if the project dir is existing
        if not os.path.isdir(self.project_dir):
            self.settings.integritiy_check()
            self.project_dir = self.settings.DIR_PROJECTS
        try:
            if not os.path.isdir(os.path.join(self.project_dir, self.project_name)):
                try:
                    os.makedirs(os.path.join(self.project_dir, self.project_name))
                except Exception as e:
                    raise Exception("Access denied, the directory is probably locked.")
            else:
                raise Exception("Directory already exists.")
        except Exception as e:
            QMessageBox.warning(self, str(e),"The Root directory of your project could not be created because the " + str(e) +", please set it manually.")
            self.project_dir = QFileDialog.getExistingDirectory(caption="Select Root Directory of the Project")
            try:
                os.mkdir(self.project_dir + "/" + self.project_name)
            except:
                self.main_window.print_message("Project Creating failed due to an error in the settings file")
                return

        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name + VIAN_PROJECT_EXTENSION
        self.project.folder = self.project_dir + "/" + self.project_name + "/"

        self.project.movie_descriptor.set_movie_path(self.lineEdit_MoviePath.text())

        if self.elan_segmentation is not None:
            ELANProjectImporter(self.main_window).apply_import(self.project, self.elan_segmentation)

        corpus = None
        if self.comboBoxCorpus.currentText() != "None":
            corpus = self.main_window.settings.recent_corpora_2[self.comboBoxCorpus.currentText()]
        print(corpus)
        self.main_window.new_project(self.project, template, copy_movie=copy_movie, corpus_path=corpus)
        self.close()
