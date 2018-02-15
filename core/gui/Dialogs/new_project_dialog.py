import glob
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QCheckBox, QVBoxLayout, QHBoxLayout,QSpacerItem, QSizePolicy, QWidget, QScrollArea

from core.data.containers import VIANProject
from core.data.enums import MovieSource
from core.gui.ewidgetbase import EDialogWidget


class NewProjectDialog(EDialogWidget):
    def __init__(self, parent, settings, movie_path, vocabularies):
        super(NewProjectDialog, self).__init__(parent, parent, "_docs/build/html/step_by_step/project_management/create_project.html")
        path = os.path.abspath("qt_ui/DialogNewProject.ui")
        uic.loadUi(path, self)
        self.settings = settings
        self.templates = []
        self.vocabularies = vocabularies
        self.project_name = "project_name"
        self.auto_naming = False

        if movie_path is "":
            self.project_dir = settings.DIR_PROJECT
        else:
            mp = movie_path.replace("\\", "/")
            mp = movie_path.split("/")
            path = ""
            for i in range(len(mp) -1):
                path += mp[i] + "/"
            self.project_dir = path

        self.project = VIANProject(parent, path ="", name="")

        self.path_set_from_dialog = False

        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)

        self.vocabulary_inner = QWidget(self)
        self.vocabulary_inner.setLayout(QHBoxLayout(self))
        self.vocabulary_scroll = QScrollArea(self)
        self.vocabulary_scroll.setWidget(self.vocabulary_inner)
        self.frame_Vocabularies.layout().addWidget(self.vocabulary_scroll)
        self.vocabulary_inner.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        n_per_col = int(len(self.vocabularies) / 3)
        self.voc_cbs = []
        vbox = QVBoxLayout(self.vocabulary_inner)
        counter = 0

        for voc in self.vocabularies:
            cb = QCheckBox(voc.replace("\\", "/").split("/").pop().replace(".txt", ""), self.vocabulary_inner)
            cb.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
            cb.setStyleSheet("QCheckBox:unchecked{ color: #b1b1b1; }QCheckBox:checked{ color: #3f7eaf; }")
            cb.setChecked(True)
            vbox.addWidget(cb)
            self.voc_cbs.append([cb, voc])
            counter += 1
            if counter == n_per_col:
                vbox.setSpacing(10)
                self.vocabulary_inner.layout().addItem(vbox)
                vbox = QVBoxLayout(self.vocabulary_inner)
                counter = 0
        if counter != 0:
            vbox.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Fixed))
            self.vocabulary_inner.layout().addItem(vbox)

        self.vocabulary_inner.resize(self.vocabulary_inner.sizeHint())

        self.find_templates()

        self.cB_AutomaticNaming.stateChanged.connect(self.on_automatic_naming_changed)
        self.lineEdit_ProjectName.textChanged.connect(self.on_proj_name_changed)
        self.lineEdit_ProjectPath.editingFinished.connect(self.on_proj_path_changed)
        self.btn_BrowseProject.clicked.connect(self.on_browse_project_path)

        self.lineEdit_Name.editingFinished.connect(self.on_desc_name_changed)
        self.lineEdit_ID.editingFinished.connect(self.on_desc_id_changed)
        self.lineEdit_Year.editingFinished.connect(self.on_desc_year_changed)
        self.comboBox_Source.currentIndexChanged.connect(self.on_desc_ource_changed)
        self.btn_BrowseMovie.clicked.connect(self.on_browse_movie_path)

        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)

        self.lineEdit_MoviePath.setText(movie_path)
        self.project.movie_descriptor.movie_path = movie_path

        self.lineEdit_ProjectName.setText(self.project_name)
        self.set_project_path()

        self.show()

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
        templates = glob.glob(self.settings.DIR_TEMPLATES + "*")
        self.templates.append(None)
        self.comboBox_Template.addItem("No Template")
        for t in templates:
            self.templates.append(t)
            self.comboBox_Template.addItem(t.replace("\\" , "/").split("/").pop().replace(".viant", ""))

    def set_project_path(self):
        #OLD System
        # self.project.path = self.project_dir


        self.project.folder = self.project_dir
        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name

        if self.auto_naming:
            self.project_name = self.lineEdit_ID.text() + "_" + \
                                self.lineEdit_Name.text().replace(" ", "_") + "_" + \
                                self.lineEdit_Year.text() + "_" + \
                                self.comboBox_Source.currentText()
            self.lineEdit_ProjectName.setText(self.project_name)
            # self.lineEdit_ProjectPath.setText(self.project.path + self.project_name + self.settings.PROJECT_FILE_EXTENSION)

            self.lineEdit_ProjectPath.setText(self.project.folder)
        else:
            self.project.name = self.project_name
            # self.lineEdit_ProjectPath.setText(self.project.path + self.project_name + self.settings.PROJECT_FILE_EXTENSION)
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
        path = QFileDialog.getOpenFileName()[0]
        # self.project.movie_descriptor.movie_path = path
        self.lineEdit_MoviePath.setText(path)
        self.path_set_from_dialog = True

    def on_desc_name_changed(self):
        self.project.movie_descriptor.movie_name = self.lineEdit_Name.text()
        self.set_project_path()

    def on_desc_id_changed(self):
        self.project.movie_descriptor.movie_id = self.lineEdit_ID.text()
        self.set_project_path()

    def on_desc_year_changed(self):
        self.project.movie_descriptor.year = self.lineEdit_Year.text()
        self.set_project_path()

    def on_desc_ource_changed(self):
        self.project.movie_descriptor.source = self.comboBox_Source.currentText()
        self.set_project_path()

    def on_desc_movie_path_changed(self):
        if not os.path.isfile(self.lineEdit_MoviePath.text()):
            self.lineEdit_MoviePath.setText("Not a Path")
            return
        self.project.movie_descriptor.movie_path = self.lineEdit_MoviePath.text()

    def on_cancel(self):
        self.close()

    def on_ok(self):
        template = self.templates[self.comboBox_Template.currentIndex()]

        # Checking if the project dir is existing
        if not os.path.isdir(self.project_dir):
            self.settings.integritiy_check()
            self.project_dir = self.settings.DIR_PROJECT
        try:
            os.mkdir(self.project_dir + "/" + self.project_name)
        except:
            QMessageBox.warning(self, "Could not Find Root Directory",
                                "The Root directory of your projects could not be found, please set it manually.")
            self.project_dir = QFileDialog.getExistingDirectory()
            try:
                os.mkdir(self.project_dir + "/" + self.project_name)
            except:
                self.main_window.print_message("Project Creating failed due to an error in the settings file")
                return

        self.project.path = self.project_dir + "/" + self.project_name + "/" + self.project_name
        self.project.folder = self.project_dir + "/" + self.project_name + "/"
        self.project.movie_descriptor.movie_path = self.lineEdit_MoviePath.text()
        print(self.project.folder, "\n",
              self.project.path, "\n",
              self.settings.DIR_PROJECT)

        vocabularies = []
        for c in self.voc_cbs:
            if c[0].isChecked:
                vocabularies.append(c[1])

        self.main_window.new_project(self.project, template, vocabularies)
        self.close()