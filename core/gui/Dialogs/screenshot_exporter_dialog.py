from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
from core.data.importers import import_elan_segmentation, get_elan_segmentation_identifiers
from core.gui.ewidgetbase import EDialogWidget
from core.data.enums import ScreenshotNamingConventionOptions, ImageType, get_enum, get_enum_value
import os
import cv2

class DialogScreenshotExporter(EDialogWidget):
    def __init__(self, parent, manager):
        super(DialogScreenshotExporter, self).__init__(parent, parent, "_docs/build/html/step_by_step/screenshots/export_screenshots.html")
        path = os.path.abspath("qt_ui/DialogScreenshotExport.ui")
        uic.loadUi(path, self)
        self.manager = manager
        self.folder_path = ""
        self.visibility = False
        self.override_visibility = False

        self.types = [(e.name) for e in ImageType]

        self.nomenclature = []
        self.naming_cbs = [self.cB_Naming1, self.cB_Naming2,
                           self.cB_Naming3, self.cB_Naming4,
                           self.cB_Naming5, self.cB_Naming6]

        for s in ScreenshotNamingConventionOptions:
            self.nomenclature.append(s.name)

        self.default = ["Scene_ID", "Shot_ID_Segment", "Shot_Group", "Movie_ID", "empty", "empty"]

        for i, cb in enumerate(self.naming_cbs):
            for s in ScreenshotNamingConventionOptions:
                cb.addItem(s.name)


            index = cb.findText(self.default[i])
            cb.setCurrentIndex(index)




        self.checkBox_OverrideV.stateChanged.connect(self.on_override_visibility_changed)
        self.checkBox_Visibility.setEnabled(self.override_visibility)
        self.cB_ImageFormat.addItems(self.types)

        self.folder_path = self.main_window.project.folder + self.main_window.settings.DIR_SCREENSHOTS
        self.lineEdit_Folder.setText(self.folder_path)
        self.lineEdit_Folder.editingFinished.connect(self.on_edit_path_finished)

        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_export)
        self.btn_Help.clicked.connect(self.on_help)

    def on_override_visibility_changed(self):
        self.override_visibility = self.checkBox_OverrideV.isChecked()
        self.checkBox_Visibility.setEnabled(self.override_visibility)

    def on_browse(self):
        self.folder_path = QFileDialog.getExistingDirectory()
        self.lineEdit_Folder.setText(self.folder_path)

    def on_edit_path_finished(self):
        self.folder_path =  self.lineEdit_Folder.text()

    def on_export(self):
        path = self.folder_path
        visibility = self.visibility
        image_type = get_enum(ImageType,self.types[self.cB_ImageFormat.currentIndex()])
        quality = self.QualitySlider.value()
        if not self.override_visibility:
            visibility = None

        n1 = self.cB_Naming1.currentText()
        n2 = self.cB_Naming2.currentText()
        n3 = self.cB_Naming3.currentText()
        n4 = self.cB_Naming4.currentText()
        n5 = self.cB_Naming5.currentText()
        n6 = self.cB_Naming6.currentText()

        naming = [n1, n2, n3, n4, n5, n6]

        smooth = self.checkBox_Antialiasing.isChecked()

        self.manager.export_screenshots(path, visibility, image_type, quality, naming, smooth)
        self.close()




    def on_cancel(self):
        self.close()

