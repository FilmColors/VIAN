import os
import glob
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QComboBox, QHBoxLayout, QMessageBox
from PyQt5 import QtWidgets

from core.data.plugin import *
from core.data.interfaces import IConcurrentJob

class RenamerExtension(GAPlugin):
    def __init__(self, main_window):
        super(RenamerExtension, self).__init__(main_window)
        self.plugin_name = "File Renamer"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self):
        wnd = RenamerWindow(self.main_window)
        wnd.show()


class RenamerWindow(QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__(parent)
        path = os.path.abspath("extensions/refactoring/qt_ui/renamer.ui")
        uic.loadUi(path, self)
        self.main_window = parent
        self.setWindowTitle("File Renamer")

        self.input_folder = None
        self.old_string = ""
        self.new_string = ""

        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Run.clicked.connect(self.rename)

        self.lineEdit_Path.setEnabled(False)
        self.lineEdit_Old.textChanged.connect(self.update_string)
        self.lineEdit_New.textChanged.connect(self.update_string)

    def on_browse(self):
        selected = QFileDialog.getExistingDirectory()
        self.input_folder = selected + "/"
        self.lineEdit_Path.setText(self.input_folder)

    def update_string(self):
        self.old_string = self.lineEdit_Old.text()
        self.new_string = self.lineEdit_New.text()

    def rename(self):
        try:
            if self.input_folder is not None:
                names = []
                dirs = []
                for path, subdirs, files in os.walk(self.input_folder):
                    for name in files:
                        name_old = os.path.join(path, name)
                        name_new = os.path.join(path, name.replace(self.old_string, self.new_string))
                        if self.old_string in name:
                            names.append([name_old, name_new])

                    for name in subdirs:
                        name_old = os.path.join(path, name)
                        name_new = os.path.join(path, name.replace(self.old_string, self.new_string))
                        if self.old_string in name:
                            dirs.append([name_old + "/", name_new + "/"])



                for n in names:
                    os.rename(n[0],n[1])

                dirs = reversed(dirs)
                for n in dirs:
                    os.rename(n[0], n[1])
        except Exception as e:
            print(e)
            QMessageBox.warning(self, "Error", e)



