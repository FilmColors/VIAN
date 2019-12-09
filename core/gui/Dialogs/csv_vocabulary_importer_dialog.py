import glob
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QComboBox

from core.data.importers import VocabularyCSVImporter
from core.gui.ewidgetbase import EDialogWidget


class CSVVocabularyImportDialog(EDialogWidget):
    def __init__(self, parent, project):
        super(CSVVocabularyImportDialog, self).__init__(parent, parent, "https://www.vian.app/static/manual/step_by_step/project_management/create_project.html")
        path = os.path.abspath("qt_ui/DialogCSVVocabularyImporter.ui")
        uic.loadUi(path, self)
        self.project = project
        self.importer = VocabularyCSVImporter()
        self.path = ""

        self.btn_Help.clicked.connect(self.on_help)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_Browse.clicked.connect(self.on_browse)

        self.lineEdit_Path.textChanged.connect(self.on_path_changed)

        self.field_boxes = [
                            self.cB_WordName,
                            self.cB_ParentField,
                            self.cB_CategoryField,
                            self.cB_Comment,
                            self.cB_HelpURL
                            ]


    def on_ok(self):
        self.importer.import_voc(self.path, self.project,
                                 field_category=self.cB_CategoryField.currentText(),
                                 field_name=self.cB_WordName.currentText(),
                                 field_parent=self.cB_ParentField.currentText(),
                                 field_comment=self.cB_Comment.currentText(),
                                 field_help=self.cB_HelpURL.currentText())


    def on_cancel(self):
        self.close()

    def on_browse(self):
        file = QFileDialog.getOpenFileName(self, filter="*.csv *.txt *.tab")[0]
        self.lineEdit_Path.setText(str(file))

    def on_path_changed(self):
        path = self.lineEdit_Path.text()
        ret, fields = self.importer.get_fields(path)
        if ret:
            self.path = path
        else:
            self.path = None

        self.set_combobox_enabled(ret)
        self.update_combobox_entries(fields)

    def set_combobox_enabled(self, state):
        for cb in self.field_boxes:
            cb.setEnabled(state)

    def update_combobox_entries(self, fields):
        for cb in self.field_boxes:
            cb.clear()
            self.cB_Comment.addItem("")
            self.cB_HelpURL.addItem("")
            cb.addItems(fields)

        if "Term_EN" in fields:
            self.cB_WordName.setCurrentText("Term_EN")
        if "Field" in fields:
            self.cB_ParentField.setCurrentText("Field")
        if "Register" in fields:
            self.cB_CategoryField.setCurrentText("Register")






