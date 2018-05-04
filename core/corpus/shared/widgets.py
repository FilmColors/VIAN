from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
from core.gui.ewidgetbase import *
import os
from PyQt5 import uic

from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.entities import *
import json
import socket
import threading


class CreateCorpusDialog(EDialogWidget):
    onCreated = pyqtSignal(object)

    def __init__(self, main_window):
        super(CreateCorpusDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogCreateCorpus.ui")
        uic.loadUi(path, self)

        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Help.clicked.connect(self.on_help)
        self.btn_OK.clicked.connect(self.on_create)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.lineEdit_Root.setText(self.main_window.settings.DIR_CORPORA)

    def on_browse(self):
        root = QFileDialog.getExistingDirectory(self, directory=self.main_window.settings.DIR_CORPORA)
        self.lineEdit_Root.setText(root)

    def on_create(self):
        if self.lineEdit_Name.text() != "" and os.path.isdir(self.lineEdit_Root.text()):
            database = DatasetCorpusDB()
            database.initialize(self.lineEdit_Name.text(), self.lineEdit_Root.text())
            self.close()
            self.onCreated.emit(database)
        else:
            QMessageBox.warning(self, "Missing Values", "Please fill out the Form")

    def on_cancel(self):
        self.close()

class CorpusUserDialog(EDialogWidget):
    onContributorUpdate = pyqtSignal(object)

    def __init__(self, main_window, contributor:DBContributor):
        super(CorpusUserDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogCorpusUser.ui")
        uic.loadUi(path, self)

        self.contributor = contributor
        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)

        self.lineEdit_Name.setText(self.contributor.name)
        self.lineEdit_Affiliation.setText(self.contributor.affiliation)

        self.image_path = ""
        if os.path.isfile(self.contributor.image_path):
            self.image_path = self.contributor.image_path
            img_bgr = cv2.imread(self.image_path)
            img = numpy_to_pixmap(img_bgr, target_width=128)
            self.lbl_Image.setPixmap(img)

    def on_browse(self):
        path = QFileDialog.getOpenFileName(self, filter="*.png *.jpg")[0]
        if os.path.isfile(path):
            img_bgr = cv2.imread(path)
            img = numpy_to_pixmap(img_bgr, target_width=128)
            self.lbl_Image.setPixmap(img)
            self.image_path = path

    def on_ok(self):
        self.contributor.name = self.lineEdit_Name.text()
        if os.path.isfile(self.image_path):
            cv2.imwrite(self.main_window.settings.DIR_CORPORA + "/user_img.jpg", cv2.imread(self.image_path))
        self.contributor.image_path = self.image_path
        self.onContributorUpdate.emit(self.contributor)
        self.close()

    def on_cancel(self):
        self.close()