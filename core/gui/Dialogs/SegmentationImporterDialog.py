from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
# from core.data.importers import import_elan_segmentation, get_elan_segmentation_identifiers
from core.gui.ewidgetbase import EDialogWidget
import os

class SegmentationImporterDialog(EDialogWidget):
    """
    TODO
    The SegmentationImporter is deprecated and should be removed at some Point
    """
    def __init__(self, parent, project, main_window):
        super(SegmentationImporterDialog, self).__init__(main_window, parent)
        path = os.path.abspath("qt_ui/DialogSegmentImporter.ui")
        uic.loadUi(path, self)
        self.project = project
        self.main_window = main_window
        self.path = ""
        self.identifiers = ["Select csv File first"]

        self.comboBox_ID.addItems(self.identifiers)
        self.additional_comboboxes = []

        self.btn_Browse.clicked.connect(self.update_identifiers)
        self.btn_Import.clicked.connect(self.on_import)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_AddAdditional.clicked.connect(self.add_identifier)
        self.btn_RemoveAdditional.clicked.connect(self.remove_identifier)
        self.btn_AddAll.clicked.connect(self.add_all_identifiers)
        self.btn_removeAll.clicked.connect(self.remove_all_identifiers)
        self.lineEdit_Path.editingFinished.connect(self.update_path)

        self.show()


    def update_identifiers(self):
        path = QFileDialog.getOpenFileName()
        self.path = path[0]
        self.lineEdit_Path.setText(self.path)
        self.identifiers = ["None"]

        res, ident = get_elan_segmentation_identifiers(self.path)
        if res is False:
            self.lineEdit_Path.setText("File Invalid: No identifiers found")
            self.path = ""
            return

        self.identifiers.extend(ident)

        self.comboBox_ID.clear()
        self.comboBox_ID.addItems(self.identifiers)

        for cb in self.additional_comboboxes:
            cb.clear()
            cb.addItems(self.identifiers)

        self.comboBox_ID.setCurrentIndex(1)

    def update_path(self):
        if not (".txt" or ".csv") in self.lineEdit_Path.text():
            return
        self.path = self.lineEdit_Path.text()

        self.identifiers = ["None"]
        self.identifiers.extend(get_elan_segmentation_identifiers(self.path)[1])

        self.comboBox_ID.clear()
        self.comboBox_ID.addItems(self.identifiers)

        for cb in self.additional_comboboxes:
            cb.clear()
            cb.addItems(self.identifiers)

    def add_identifier(self):
        idx = self.formFrame_AdditionalIdentifiers.layout().count()/2
        cb = QComboBox()
        cb.addItems(self.identifiers)

        self.additional_comboboxes.append(cb)
        self.formFrame_AdditionalIdentifiers.layout().addRow("Additional " + str(idx), cb)
        return cb

    def remove_identifier(self):
        last = self.formFrame_AdditionalIdentifiers.layout().count() - 1
        if last < 0:
            return
        item1 = self.formFrame_AdditionalIdentifiers.layout().itemAt(last)
        item2 = self.formFrame_AdditionalIdentifiers.layout().itemAt(last -1)

        self.formFrame_AdditionalIdentifiers.layout().removeItem(item1)
        self.formFrame_AdditionalIdentifiers.layout().removeItem(item2)

        item1.widget().close()
        item2.widget().close()

        self.update()

    def remove_all_identifiers(self):
        for cb in self.additional_comboboxes:
            self.remove_identifier()
        self.additional_comboboxes = []

    def on_import(self):
        prevent_overlap = self.checkBox_CleanBorders.isChecked()
        id_identifiers = [self.comboBox_ID.currentText()]
        for cb in self.additional_comboboxes:
            id_identifiers.append(cb.currentText())

        segmentations = []
        for a in id_identifiers:
            res, segmentation = import_elan_segmentation(self.path, a, a, prevent_overlap)
            segmentations.append(segmentation)

            if res is False:
                alert = QMessageBox(self)
                alert.setWindowTitle("Import Failed")
                alert.setText(segmentation)
                alert.show()
                return

        for s in segmentations:
            self.project.add_segmentation(s)
        self.close()

        for shot in self.project.get_screenshots():
            shot.update_scene_id(self.project.get_main_segmentation())
        # self.main_window.screenshots_editor.on_screenshot_changed()

    def add_all_identifiers(self):
        # Zero Element is "None" we don't want to add this
        for i in range(1, len(self.identifiers), 1):
            if self.comboBox_ID.currentIndex() != i:
                cb = self.add_identifier()
                cb.setCurrentIndex(i)

    def on_cancel(self):
        self.close()