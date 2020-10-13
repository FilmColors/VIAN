from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QLabel, QCheckBox
from PyQt5 import uic
from core.gui.ewidgetbase import EDialogWidget
from core.data.exporters import SegmentationExporter
import os
import json

class ExportSegmentationDialog(EDialogWidget):
    def __init__(self, main_window):
        super(ExportSegmentationDialog, self).__init__(main_window, main_window, "https://www.vian.app/static/manual/step_by_step/project_management/export_segmentation.html")
        path = os.path.abspath("qt_ui/DialogExportSegmentation.ui")
        uic.loadUi(path, self)
        self.settings = main_window.settings

        self.lineEdit_Path.setText(os.path.join(self.main_window.project.export_dir, "segmentation.csv"))
        self.segm_cBs = []
        for s in self.main_window.project.segmentation:
            cb = QCheckBox(self)
            cb.setText(s.get_name())
            cb.setChecked(True)
            self.layout_Segmentations.addWidget(cb)
            self.segm_cBs.append(cb)

        self.checkBox_Timestamp.stateChanged.connect(self.on_timestamp_toggle)
        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_Help.clicked.connect(self.on_help)

    def on_timestamp_toggle(self):
        state = self.checkBox_Timestamp.isChecked()
        self.comboBox_Format.setEnabled(state)
        self.label_Format.setEnabled(state)

    def on_browse(self):
        path = QFileDialog.getSaveFileName(caption="Select Path", directory=self.main_window.project.export_dir, filter="*.csv")[0]
        self.lineEdit_Path.setText(path)

    def on_export(self):
        text = self.cB_AnnotationText.isChecked()
        frame = self.cB_FramePosition.isChecked()
        timestamp = self.checkBox_Timestamp.isChecked()
        mode = self.comboBox_Format.currentText()

        milli = False
        formated = False
        formated_ms = False
        formated_frame = False

        if timestamp:
            if mode == "MS":
                milli = True
            elif mode == "HH:MM:SS":
                formated = True
            elif mode == "HH:MM:SS:MS":
                formated_ms = True
            elif mode == "HH:MM:SS:FRAME":
                formated_frame = True
            else:
                timestamp = False

        t_start = self.cB_Start.isChecked()
        t_end = self.cB_End.isChecked()
        t_duration = self.cB_Duration.isChecked()

        path = self.lineEdit_Path.text()

        segmentations = []
        for i, c in enumerate(self.segm_cBs):
            if c.isChecked():
                segmentations.append(self.main_window.project.segmentation[i])


        exporter = SegmentationExporter(path, milli, formated, formated_ms, formated_frame, text, frame, t_start,
                                        t_end, t_duration, self.main_window.player.get_fps(), segmentations)

        self.main_window.project.export(exporter, path)


        self.close()


