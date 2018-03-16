from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QLabel
from PyQt5 import uic
from core.gui.ewidgetbase import EDialogWidget
from core.gui.tools import DialogPrompt
from core.data.exporters import ExperimentExporter
import os
import json

class ExportTemplateDialog(EDialogWidget):
    def __init__(self, main_window):
        super(ExportTemplateDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogExportTemplate.ui")
        uic.loadUi(path, self)
        self.settings = main_window.settings

        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.close)


    def on_export(self):
        name = self.lineEdit_Name.text()
        segmentation = self.cB_Segmentation.isChecked()
        vocabulary = self.cB_Vocabulary.isChecked()
        annotation_layers = self.cB_AnnotationLayers.isChecked()
        node_scripts = self.cB_NodeScripts.isChecked()
        experiments = self.cB_Experiments.isChecked()

        template = self.main_window.project.get_template(segmentation, vocabulary,
                                                         annotation_layers, node_scripts,
                                                         experiments, ExperimentExporter())

        path = self.settings.DIR_TEMPLATES + name + ".viant"
        try:
            with open(path, "w") as f:
                json.dump(template, f)
        except Exception as e:
            self.main_window.print_message("Template Export Failed:", "Red")
            self.main_window.print_message(e, "Red")

        self.close()





