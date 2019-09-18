import glob
import os
import cv2

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter, QFileDialog, QMessageBox, QTabWidget, QCheckBox, QLineEdit, QVBoxLayout, QHBoxLayout,QSpacerItem, QSizePolicy, QWidget, QScrollArea
from core.container.project import VIANProject, VIAN_PROJECT_EXTENSION
from core.data.enums import MovieSource
from core.gui.ewidgetbase import EDialogWidget
from core.data.importers import ELANProjectImporter
from core.data.computation import images_to_movie
from core.gui.filmography_widget import FilmographyWidget2

class NewProjectDialog(EDialogWidget):
    def __init__(self, parent, settings, movie_path = "", vocabularies = None, elan_segmentation = None, add_to_current_corpus=False):
        super(NewProjectDialog, self).__init__(parent, parent, "_docs/build/html/step_by_step/project_management/create_project.html")
        path = os.path.abspath("qt_ui/DialogNewProject.ui")
        uic.loadUi(path, self)
        self.settings = settings
        self.templates = []
        self.vocabularies = vocabularies
        self.project_name = "project_name"
        self.auto_naming = False

        self.elan_segmentation = elan_segmentation
        if movie_path is "":
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

        self.find_templates()

        self.tabWidget.removeTab(1)
        # self.filmography_widget = FilmographyWidget(self)
        # self.tabWidget.addTab(self.filmography_widget, "Filmography")
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

        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)

        self.lineEdit_MoviePath.setText(movie_path)
        self.project.movie_descriptor.set_movie_path(movie_path)
        self.checkBox_FromImages.stateChanged.connect(self.on_from_images_changed)

        self.lineEdit_ProjectName.setText(self.project_name)
        self.set_project_path()

        self.image_paths = []

        self.show()

    def on_from_images_changed(self):
        if self.checkBox_FromImages.isChecked():
            self.moviePathLabel.setText("Image Files")
        else:
            self.moviePathLabel.setText("Media Path")

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
        templates.extend(glob.glob("data/templates/" + "*.viant"))

        self.templates.append(None)
        self.comboBox_Template.addItem("No Template")
        for t in templates:
            self.templates.append(t)
            self.comboBox_Template.addItem(t.replace("\\" , "/").split("/").pop().replace(".viant", ""))

    def set_project_path(self):
        #OLD System
        # self.project.path = self.project_dir


        self.project.folder = self.project_dir
        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name + VIAN_PROJECT_EXTENSION

        if self.auto_naming:
            self.project_name = self.get_movie_id() + "_" + \
                                self.lineEdit_Name.text().replace(" ", "_") + "_" + \
                                str(self.spinBox_Year.value()) + "_" + \
                                self.comboBox_Source.currentText()
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
        path = QFileDialog.getExistingDirectory(directory=self.project_dir)
        self.project_dir = path
        self.lineEdit_ProjectPath.setText(self.project.folder)

    def on_browse_movie_path(self):
        if self.checkBox_FromImages.isChecked() is False:
            path = QFileDialog.getOpenFileName()[0]
            # self.project.movie_descriptor.movie_path = path
            self.lineEdit_MoviePath.setText(path)
            self.path_set_from_dialog = True
        else:
            self.image_paths = QFileDialog.getOpenFileNames()[0]

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
            if not os.path.isdir(self.project_dir + "/" + self.project_name):
                try:
                    os.mkdir(self.project_dir + "/" + self.project_name)
                except Exception as e:
                    raise Exception("Access denied, the directory is probably locked.")
            else:
                raise Exception("Directory already exists.")
        except Exception as e:
            QMessageBox.warning(self, str(e),"The Root directory of your project could not be created because the " + str(e) +", please set it manually.")
            self.project_dir = QFileDialog.getExistingDirectory()
            try:
                os.mkdir(self.project_dir + "/" + self.project_name)
            except:
                self.main_window.print_message("Project Creating failed due to an error in the settings file")
                return

        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name + VIAN_PROJECT_EXTENSION
        self.project.folder = self.project_dir + "/" + self.project_name + "/"

        if self.checkBox_FromImages.isChecked():
            if len(self.image_paths) == 0:
                QMessageBox.warning(self, "No Images added",
                                    "There are no images selected to generate a movie from.")
                return
            imgs = []
            for p in self.image_paths:
                try:
                    imgs.append(cv2.imread(p))
                except Exception as e:
                    continue
            if len(imgs) == 0:
                QMessageBox.warning(self, "Failed to read Images",
                                    "Failed to read images, are these files really images?")
                return
            path = self.project.folder + self.project_name + ".avi"
            images_to_movie(imgs, path, size = (imgs[0].shape[0], imgs[0].shape[1]))
            self.lineEdit_MoviePath.setText(path)

        self.project.movie_descriptor.set_movie_path(self.lineEdit_MoviePath.text())

        # vocabularies = []
        # for c in self.voc_cbs:
        #     if c[0].isChecked:
        #         vocabularies.append(c[1])

        # self.main_window.new_project(self.project, template, vocabularies)
        if self.elan_segmentation is not None:
            ELANProjectImporter(self.main_window).apply_import(self.project, self.elan_segmentation)
        self.main_window.new_project(self.project, template, copy_movie=copy_movie)
        self.close()


# class FilmographyWidget(QWidget):
#     def __init__(self, parent, project = None, persons = None, processes = None):
#         super(FilmographyWidget, self).__init__(parent)
#         path = os.path.abspath("qt_ui/FilmographyWidget.ui")
#         uic.loadUi(path, self)
#         if persons is not None:
#             q = QCompleter([p['name'] for p in persons])
#             self.lineEdit_Director.setCompleter(q)
#             self.lineEdit_Cinematography.setCompleter(q)
#             self.lineEdit_ColorConsultant.setCompleter(q)
#             self.lineEdit_ProductionDesign.setCompleter(q)
#             self.lineEdit_ArtDirector.setCompleter(q)
#             self.lineEdit_CostumDesign.setCompleter(q)
#         if processes is not None:
#             self.comboBox_ColorProcess.addItems(sorted([p['name'] for p in processes]))
#
#
#         # if project is not None:
#
#
#     def get_filmography(self):
#         filmography_meta = dict()
#         if self.lineEdit_IMDB.text() != "":
#             filmography_meta['imdb_id'] = self.lineEdit_IMDB.text().split(",")
#         if self.lineEdit_Genre.text() != "":
#             filmography_meta['genre'] = self.lineEdit_Genre.text().split(",")
#         if self.comboBox_ColorProcess.currentText() != "":
#             filmography_meta['color_process'] = self.comboBox_ColorProcess.text().split(",")
#         if self.lineEdit_Director.text() != "":
#             filmography_meta['director'] = self.lineEdit_Director.text().split(",")
#         if self.lineEdit_Cinematography.text() != "":
#             filmography_meta['cinematography'] = self.lineEdit_Cinematography.text().split(",")
#         if self.lineEdit_ColorConsultant.text() != "":
#             filmography_meta['color_consultant'] = self.lineEdit_ColorConsultant.text().split(",")
#         if self.lineEdit_ProductionDesign.text() != "":
#             filmography_meta['production_design'] = self.lineEdit_ProductionDesign.text().split(",")
#         if self.lineEdit_ArtDirector.text() != "":
#             filmography_meta['art_director'] = self.lineEdit_ArtDirector.text().split(",")
#         if self.lineEdit_CostumDesign.text() != "":
#             filmography_meta['costum_design'] = self.lineEdit_CostumDesign.text().split(",")
#         if self.lineEdit_ProductionCompany.text() != "":
#             filmography_meta['production_company'] = self.lineEdit_ProductionCompany.text().split(",")
#         if self.lineEdit_ProductionCountry.text() != "":
#             filmography_meta['country'] = self.lineEdit_ProductionCountry.text().split(",")
#
#         return filmography_meta
