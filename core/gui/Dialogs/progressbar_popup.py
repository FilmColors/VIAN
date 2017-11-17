from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
from PyQt5.QtCore import Qt
from core.data.importers import import_elan_segmentation, get_elan_segmentation_identifiers
from core.gui.ewidgetbase import EDialogWidget
from core.data.settings import UserSettings
from core.data.enums import ScreenshotNamingConventionOptions
import os


class DialogProgress(EDialogWidget):
    def __init__(self, main__window, message="This is a Progress Dialog"):
        super(DialogProgress, self).__init__(main__window, main__window)
        path = os.path.abspath("qt_ui/DialogProgressBar.ui")
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.Tool)
        uic.loadUi(path, self)
        self.lbl_Message.setText(message)
        self.show()

    def on_progress(self, value):
        self.progressBar.setValue(value)
        if value == 100:
            self.deleteLater()

