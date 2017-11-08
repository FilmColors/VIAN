from PyQt5.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox
from PyQt5 import uic
from core.data.importers import import_elan_segmentation, get_elan_segmentation_identifiers
from core.gui.ewidgetbase import EDialogWidget
from core.data.settings import UserSettings
from core.data.enums import ScreenshotNamingConventionOptions
import os

class DialogPreferences(EDialogWidget):
    def __init__(self, parent):
        super(DialogPreferences, self).__init__(parent, parent)
        path = os.path.abspath("qt_ui/DialogPreferences.ui")
        uic.loadUi(path, self)

        self.settings = parent.settings
        # self.settings = UserSettings()


        self.naming_cbs = [self.cB_Naming1, self.cB_Naming2,
                           self.cB_Naming3, self.cB_Naming4,
                           self.cB_Naming5, self.cB_Naming6]

        for i, cb in enumerate(self.naming_cbs):
            for s in ScreenshotNamingConventionOptions:
                cb.addItem(s.name)

            index = cb.findText(self.settings.SCREENSHOTS_EXPORT_NAMING[i])
            cb.setCurrentIndex(index)

        self.checkBox_Autosave.stateChanged.connect(self.set_autosave)
        self.spinBox_AutosaveTime.valueChanged.connect(self.set_autosave_time)

        self.btn_Ok.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)

        for cb in self.naming_cbs:
            cb.currentIndexChanged.connect(self.set_screenshot_export_naming)

        self.spinBox_GridSize.valueChanged.connect(self.set_grid_size)


        self.lineEdit_ProjectsFolder.setText(self.settings.DIR_PROJECT)
        self.checkBox_Autosave.setCheckState(self.settings.AUTOSAVE)
        self.spinBox_AutosaveTime.setValue(self.settings.AUTOSAVE_TIME)


        self.spinBox_GridSize.setValue(self.settings.GRID_SIZE)
        self.lineEdit_CorpusIP.setText(self.settings.CORPUS_IP)
        self.lineEdit_CorpusPort.setText(str(self.settings.COPRUS_PORT))
        self.lineEdit_CorpusPW.setText(self.settings.COPRUS_PW)

    def set_autosave(self):
        state = self.checkBox_Autosave.isChecked()
        self.settings.AUTOSAVE = state

    def set_autosave_time(self):
        value = self.spinBox_AutosaveTime.value()
        self.settings.AUTOSAVE_TIME = value

    def set_grid_size(self):
        self.settings.GRID_SIZE = self.spinBox_GridSize.value()


    def set_screenshot_export_naming(self):

        n1 = self.cB_Naming1.currentText()
        n2 = self.cB_Naming2.currentText()
        n3 = self.cB_Naming3.currentText()
        n4 = self.cB_Naming4.currentText()
        n5 = self.cB_Naming5.currentText()
        n6 = self.cB_Naming6.currentText()

        naming = [n1, n2, n3, n4, n5, n6]
        self.settings.SCREENSHOTS_EXPORT_NAMING = naming

    def on_ok(self):
        self.settings.store()
        self.close()

    def on_cancel(self):
        self.settings.load()
        self.close()