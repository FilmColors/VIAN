from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
from core.data.importers import import_elan_segmentation, get_elan_segmentation_identifiers
from core.gui.ewidgetbase import EDialogWidget
from core.data.enums import MovieSource
import os

class MovieDescriptorDialog(EDialogWidget):
    def __init__(self, parent, movie_descriptor, def_name = None, def_year = None):
        super(MovieDescriptorDialog, self).__init__(parent, parent)
        path = os.path.abspath("qt_ui/MovieDescriptorDialog.ui")
        uic.loadUi(path, self)
        self.movie_descriptor = movie_descriptor


        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)
        if def_name is not None:
            self.movie_descriptor.movie_name = def_name
        if def_year is not None:
            self.movie_descriptor.movie_year = def_year


        self.init_name = self.movie_descriptor.movie_name
        self.init_id = self.movie_descriptor.movie_id
        self.init_year = self.movie_descriptor.year
        self.init_source = self.movie_descriptor.source


        self.lineEdit_Name.setText(self.init_name)
        self.lineEdit_ID.setText("Enter Movie ID")
        self.lineEdit_Year.setText("1896")


        self.lineEdit_Name.editingFinished.connect(self.on_name_changed)
        self.lineEdit_ID.editingFinished.connect(self.on_id_changed)
        self.lineEdit_Year.editingFinished.connect(self.on_year_changed)
        self.comboBox_Source.currentIndexChanged.connect(self.on_source_changed)

        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_ok)

    def on_name_changed(self):
        self.movie_descriptor.movie_name = self.lineEdit_Name.text()
    def on_id_changed(self):
        self.movie_descriptor.movie_id = self.lineEdit_ID.text()
    def on_year_changed(self):
        self.movie_descriptor.year = self.lineEdit_Year.text()
    def on_source_changed(self):
        self.movie_descriptor.source = self.comboBox_Source.currentText()

    def on_cancel(self):
        self.movie_descriptor.movie_name = self.init_name
        self.movie_descriptor.movie_id = self.init_id
        self.movie_descriptor.year = self.init_year
        self.movie_descriptor.source = self.init_source

        self.close()

    def on_ok(self):
        self.close()
