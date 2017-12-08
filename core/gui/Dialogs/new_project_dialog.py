import glob
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog

from core.data.containers import ElanExtensionProject
from core.data.enums import MovieSource
from core.gui.ewidgetbase import EDialogWidget


class NewProjectDialog(EDialogWidget):
    def __init__(self, parent, settings, movie_path):
        super(NewProjectDialog, self).__init__(parent, parent, "_docs/build/html/step_by_step/project_management/create_project.html")
        path = os.path.abspath("qt_ui/DialogNewProject.ui")
        uic.loadUi(path, self)
        self.settings = settings
        self.templates = []

        self.project_name = "project_name"
        if movie_path is "":
            self.project_dir = settings.DIR_PROJECT
        else:
            mp = movie_path.replace("\\", "/")
            mp = movie_path.split("/")
            path = ""
            for i in range(len(mp) -1):
                path += mp[i] + "/"
            self.project_dir = path
        self.project = ElanExtensionProject(parent, path = "", name="")

        self.path_set_from_dialog = False

        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)

        self.find_templates()

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

    def find_templates(self):
        templates = glob.glob(self.settings.DIR_TEMPLATES + "*")
        self.templates.append(None)
        self.comboBox_Template.addItem("No Template")
        for t in templates:
            self.templates.append(t)
            self.comboBox_Template.addItem(t.replace("\\" , "/").split("/").pop().replace(".viant", ""))

    def set_project_path(self):
        self.project.path = self.project_dir
        self.project.name = self.project_name
        self.lineEdit_ProjectPath.setText(self.project.path + self.project_name + self.settings.PROJECT_FILE_EXTENSION)

    def parse_project_path(self, path):
        path = path.split('/')
        directory = ""
        if path[len(path) - 1] == self.settings.PROJECT_FILE_EXTENSION:
            path = path[0:len(path) - 2]

        project_name = path[len(path) - 1]
        for i in range(len(path) - 1):
            directory += path[i] + "/"

        return directory, project_name

    def on_proj_name_changed(self):
        self.project_name = self.lineEdit_ProjectName.text()
        if not self.path_set_from_dialog:
            self.set_project_path()

    def on_proj_path_changed(self):
        path = self.lineEdit_ProjectPath.text()
        p_dir, p_name = self.parse_project_path(path)
        self.project_dir = p_dir
        self.project_name = p_name

    def on_browse_project_path(self):
        path = QFileDialog.getSaveFileName(directory=self.project_dir)[0]
        p_dir, p_name = self.parse_project_path(path)
        self.project_dir = p_dir
        self.project_name = p_name

        self.lineEdit_ProjectPath.setText(p_dir + p_name)

    def on_browse_movie_path(self):
        path = QFileDialog.getOpenFileName()[0]
        self.project.movie_descriptor.movie_path = path
        self.lineEdit_MoviePath.setText(path)
        self.path_set_from_dialog = True

    def on_desc_name_changed(self):
        self.project.movie_descriptor.movie_name = self.lineEdit_Name.text()

    def on_desc_id_changed(self):
        self.project.movie_descriptor.movie_id = self.lineEdit_ID.text()

    def on_desc_year_changed(self):
        self.project.movie_descriptor.year = self.lineEdit_Year.text()

    def on_desc_ource_changed(self):
        self.project.movie_descriptor.source = self.comboBox_Source.currentText()

    def on_desc_movie_path_changed(self):
        if not os.path.isfile(self.lineEdit_MoviePath.text()):
            self.lineEdit_MoviePath.setText("Not a Path")
            return
        self.project.movie_descriptor.movie_path = self.lineEdit_MoviePath.text()

    def on_cancel(self):
        self.close()

    def on_ok(self):
        try:
            if not os.path.isdir(self.project.path):
                os.mkdir(self.project.path)
        except OSError as e:
            print(e)
            print("Forced silencing as Hotfix, if this statement is necessary is currently unclear anyway")
            #TODO

        template = self.templates[self.comboBox_Template.currentIndex()]
        self.project.path = self.project_dir + self.project_name
        self.main_window.new_project(self.project, template)
        self.close()