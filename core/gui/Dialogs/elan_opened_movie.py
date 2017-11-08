from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QLabel
from PyQt5 import uic
from core.gui.ewidgetbase import EDialogWidget
from core.gui.tools import DialogPrompt
import os

class ELANMovieOpenDialog(EDialogWidget):
    def __init__(self, main_window, master_file, movie_path):
        super(ELANMovieOpenDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogElanOpenedMovie.ui")
        uic.loadUi(path, self)
        self.movie_path = movie_path.replace("file:///", "")
        self.buttons = []
        self.path = ""

        self.btn_new.clicked.connect(self.on_new_project)
        self.btn_other.clicked.connect(self.on_other_project)
        self.btn_cancel.clicked.connect(self.on_cancel)

        for p in master_file.projects:

            btn = QPushButton(self)
            btn.setText(p["name"])
            self.widget_existing.layout().addWidget(btn)

            if p['movie_path'] == self.movie_path:
                btn.setStyleSheet("QPushButton{color : green;}")
                is_correct_movie = True
            else:
                btn.setStyleSheet("QPushButton{color : red;}")
                is_correct_movie = False

            self.buttons.append([btn, is_correct_movie, p['path'], p['name']])
            btn.clicked.connect(self.on_previous_clicked)

    def on_previous_clicked(self, button):
        s = self.sender()
        for b in self.buttons:
            if b[0] is s:
                button = b
                is_correct_movie = b[1]

        if is_correct_movie:
            self.main_window.load_project(button[2])
            self.close()
        else:
            self.path = button.text()
            self.dialog = DialogPrompt(self, "This Project does not contain the movie opened by ELAN, "
                                        "do you want to open it anyway?")
            self.dialog.on_ok.triggered.connect(self.on_accept_anyway)
            self.dialog.on_cancel.triggered.connect(self.on_cancel_dialog)

    def on_new_project(self):
        self.main_window.on_new_project(self.movie_path)
        self.close()

    def on_other_project(self):
        self.main_window.on_load_project()
        self.close()

    def on_accept_anyway(self):
        self.dialog.close()
        self.main_window.load_project(self.path)
        self.close()

    def on_cancel_dialog(self):
        self.dialog.close()

    def on_cancel(self):
        self.close()

