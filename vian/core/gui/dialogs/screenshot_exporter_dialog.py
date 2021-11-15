import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog

from vian.core.data.enums import ScreenshotNamingConventionOptions, ImageType, get_enum
from vian.core.gui.ewidgetbase import EDialogWidget
from vian.core.data.exporters import ScreenshotExporter


class DialogScreenshotExporter(EDialogWidget):
    def __init__(self, parent, project):
        super(DialogScreenshotExporter, self).__init__(parent, parent, "https://www.vian.app/static/manual/step_by_step/screenshots/export_screenshots.html")
        path = os.path.abspath("qt_ui/DialogScreenshotExport.ui")
        uic.loadUi(path, self)
        self.project = project
        self.folder_path = ""

        self.default = "{SceneID}_{ShotID}_{ShotGroup}_{MovieID}.jpg"
        self.lineEdit_Nomenclature.setText(self.default)

        self.comboBox_SemanticSegmentation.addItems([
            ScreenshotExporter.SemSeg_None,
            ScreenshotExporter.SemSeg_Outlines,
            ScreenshotExporter.SemSeg_Filled
        ])

        self.QualitySlider.valueChanged.connect(self.on_quality_changed)

        self.folder_path = self.main_window.project.shots_dir
        self.lineEdit_Folder.setText(self.folder_path)
        self.lineEdit_Folder.editingFinished.connect(self.on_edit_path_finished)

        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.btn_OK.clicked.connect(self.on_export)
        self.btn_Help.clicked.connect(self.on_help)

        self.on_quality_changed()

    def on_browse(self):
        self.folder_path = QFileDialog.getExistingDirectory(caption="Select Directory to export Screenshots into")
        self.lineEdit_Folder.setText(self.folder_path)

    def on_edit_path_finished(self):
        self.folder_path =  self.lineEdit_Folder.text()

    def on_quality_changed(self):
        self.lbl_Quality.setText((str(self.QualitySlider.value()) + " %").ljust(6))

    def on_export(self):
        path = self.folder_path
        quality = self.QualitySlider.value()
        selection = self.project.selected

        device = ScreenshotExporter(naming=self.lineEdit_Nomenclature.text(),
                                    selection=selection,
                                    quality=quality,
                                    semantic_segmentation = self.comboBox_SemanticSegmentation.currentText(),
                                    apply_letterbox = self.checkBox_ApplyLetterbox.isChecked())
        self.project.export(device, path)
        self.close()


    def on_cancel(self):
        self.close()

