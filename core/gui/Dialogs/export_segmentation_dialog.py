from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QLabel, QCheckBox
from PyQt5 import uic
from core.gui.ewidgetbase import EDialogWidget
from core.gui.tools import DialogPrompt
from core.data.exporters import SegmentationExporter
import os
import json

class ExportSegmentationDialog(EDialogWidget):
    def __init__(self, main_window):
        super(ExportSegmentationDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogExportSegmentation.ui")
        uic.loadUi(path, self)
        self.settings = main_window.settings

        self.segm_cBs = []
        for s in self.main_window.project.segmentation:
            cb = QCheckBox(self)
            cb.setText(s.get_name())
            cb.setChecked(True)
            self.layout_Segmentations.addWidget(cb)
            self.segm_cBs.append(cb)


        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.close)



    def on_browse(self):
        path = QFileDialog.getSaveFileName(directory=self.main_window.project.path, filter="*.txt")[0]
        if ".txt" not in path:
            path += ".txt"
        self.lineEdit_Path.setText(path)

    def on_export(self):
        text = self.cB_AnnotationText.isChecked()
        frame = self.cB_FramePosition.isChecked()
        milli = self.cB_Miliseconds.isChecked()
        formated = self.cB_FormatedTime.isChecked()

        t_start = self.cB_Start.isChecked()
        t_end = self.cB_End.isChecked()
        t_duration = self.cB_Duration.isChecked()

        path = self.lineEdit_Path.text()

        segmentations = []
        for i, c in enumerate(self.segm_cBs):
            if c.isChecked():
                segmentations.append(self.main_window.project.segmentation[i].serialize())


        exporter = SegmentationExporter(path, milli, formated, text, frame, t_start,
                                        t_end, t_duration, self.main_window.player.get_fps())
        # segmentations = []
        # for s in self.main_window.project.segmentation:
        #     segmentations.append(s.serialize())

        result, exception = exporter.export(segmentations)
        if result:
            self.main_window.print_message("Segmentation Exported to: " + path, "Green")
        else:
            self.main_window.print_message("Segmentation Export Failed: " + path, "Red")
            self.main_window.print_message(str(exception), "Red")

        self.close()


