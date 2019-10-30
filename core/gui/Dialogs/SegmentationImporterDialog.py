from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
from core.data.importers import SegmentationImporter
from core.gui.ewidgetbase import EDialogWidget
from core.container.project import *
import os

class SegmentationImporterDialog(EDialogWidget):
    """
    TODO
    The SegmentationImporter is deprecated and should be removed at some Point
    """
    def __init__(self, parent, project:VIANProject, main_window):
        super(SegmentationImporterDialog, self).__init__(main_window, parent)
        path = os.path.abspath("qt_ui/DialogSegmentationImport.ui")
        uic.loadUi(path, self)
        self.project = project
        self.main_window = main_window
        self.path = ""
        self.importer = SegmentationImporter()

        self.btn_browse.clicked.connect(self.on_browse)
        self.btn_ok.clicked.connect(self.on_import)
        self.btn_help.clicked.connect(self.on_help)
        self.comboBox_Seperator.currentIndexChanged.connect(self.check_file)
        self.btn_cancel.clicked.connect(self.close)

    def on_browse(self):


        path = QFileDialog.getOpenFileName(filter="*.txt *.csv")[0]
        self.path = path
        self.check_file()

    def check_file(self):
        path = self.path
        if os.path.isfile(path):
            if self.comboBox_Seperator.currentIndex() == 0:
                delimiter = ";"
            else:
                delimiter = "\t"

            success, fields = self.importer.get_fields(path, delimiter=delimiter)

            if success:
                self.comboBox_startField.clear()
                self.comboBox_endField.clear()
                self.comboBox_annotationField.clear()

                self.comboBox_startField.addItems(fields)
                self.comboBox_endField.addItems(fields)
                self.comboBox_annotationField.addItems(fields)

                self.path = path
                self.lineEdit_Path.setText(self.path)
                return True
            else:
                self.path = ""
                self.lineEdit_Path.setText("")
                QMessageBox.warning(self, "Error", "Could not parse file. Is this really a tabular csv?")
                return False


    def on_import(self):
        if self.path != "":
            self.importer.import_segmentation(self.path, self.project, self.project.movie_descriptor.fps,
                                              self.checkBox_HasHeader.isChecked(),
                                              self.comboBox_startField.currentText(),
                                              self.comboBox_endField.currentText(),
                                              self.comboBox_annotationField.currentText(),
                                              self.comboBox_tType.currentText(),
                                              self.comboBox_Mode.currentText())

            self.close()