from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip

import os
from PyQt5 import uic

from core.corpus.client.webapp_corpus import CorpusClient

from core.gui.ewidgetbase import *
from core.corpus.shared.entities import *
from core.gui.tools import StringList
import json
import socket
import threading
import hashlib, uuid

class CorpusClientToolBar(QToolBar):
    def __init__(self, parent, corpus_client:CorpusClient):
        super(CorpusClientToolBar, self).__init__(parent)
        self.setWindowTitle("Corpus Toolbar")
        self.spacer = QWidget()
        self.spacer.setLayout(QHBoxLayout())
        self.spacer.layout().addItem(QSpacerItem(1,1,QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.addWidget(self.spacer)

        self.addAction(CorpusClientWidgetAction(self, corpus_client, parent))

    def get_client(self):
        return self.corpus_client


class CorpusClientWidgetAction(QWidgetAction):
    def __init__(self, parent, corpus_client:CorpusClient, main_window):
        super(CorpusClientWidgetAction, self).__init__(parent)
        self.p = parent
        self.corpus_client = corpus_client
        self.main_window = main_window

    def createWidget(self, parent: QWidget):
        return CorpusClientWidget(parent,  self.corpus_client, self.main_window)


class CorpusClientWidget(QWidget):
    def __init__(self, parent, corpus_client:CorpusClient, main_window):
        super(CorpusClientWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/CorpusClientWidget.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        self.main_window = main_window

        self.dbproject = None
        self.checkout_state = 0

        self.corpus_client.onCorpusConnected.connect(self.on_connected)
        self.corpus_client.onCorpusDisconnected.connect(self.on_disconnected)
        self.corpus_client.onCurrentDBProjectChanged.connect(self.on_project_changed)
        self.corpus_client.onCheckOutStateChanged.connect(self.checkout_state_changed)
        self.contributor = self.main_window.settings.CONTRIBUTOR

        self.btn_Commit.clicked.connect(self.on_commit)
        self.btn_CheckOut.clicked.connect(self.on_check_out)
        self.btn_Person.clicked.connect(self.open_contributor_editor)
        self.btn_Update.clicked.connect(self.on_update)
        self.btn_Commit.setEnabled(False)
        self.btn_CheckOut.setEnabled(False)
        self.btn_Update.setEnabled(False)

        self.comboBox_Corpora.addItem("ERC FilmColors") #type:QComboBox
        self.comboBox_Corpora.currentTextChanged.connect(self.on_corpus_changed)

        #  self.btn_.clicked.connect(self.corpus_client.connect)

        self.on_contributor_update(self.main_window.settings.CONTRIBUTOR)
        self.show()

    @pyqtSlot(object)
    def on_connected(self, corpus):
        self.lbl_Status.setText("\tConnected")
        self.lbl_Status.setStyleSheet("QLabel{color:green;}")
        self.btn_Commit.setEnabled(True)
        self.btn_CheckOut.setEnabled(True)
        self.btn_Update.setEnabled(True)

    @pyqtSlot(object)
    def on_disconnected(self, corpus):
        self.lbl_Status.setText("\tDisconnected")
        self.lbl_Status.setStyleSheet("QLabel{color:red;}")
        self.btn_Commit.setEnabled(False)
        self.btn_CheckOut.setEnabled(False)
        self.btn_Update.setEnabled(False)

    def on_corpus_changed(self):
        name = self.comboBox_Corpora.currentText()
        if name == "ERC FilmColors":
            self.corpus_client.on_connect_webapp(None)

    def open_contributor_editor(self):
        dialog = CorpusUserDialog(self.main_window, self.main_window.settings.CONTRIBUTOR)
        dialog.onContributorUpdate.connect(self.on_contributor_update)
        dialog.show()

    def on_contributor_update(self, contributor):
        self.contributor = contributor
        if os.path.isfile(self.contributor.image_path):
            self.btn_Person.setIcon(create_icon(contributor.image_path))
        self.corpus_client.metadata.store(self.corpus_client.metadata.path)

    def on_commit(self):
        if self.main_window.project is not None:
            self.corpus_client.on_commit_project(self.main_window.project)

    def on_update(self):
        pass
        # self.corpus_client.synchronize()

    def checkout_state_changed(self, value):
        print("RECIEVED", value)
        self.btn_CheckOut.clicked.disconnect()
        if value == CHECK_OUT_SELF:
            self.btn_CheckOut.setEnabled(True)
            self.btn_Commit.setEnabled(True)
            self.btn_CheckOut.setChecked(True)
        elif value == CHECK_OUT_NO:
            self.btn_CheckOut.setEnabled(True)
            self.btn_Commit.setEnabled(True)
            self.btn_CheckOut.setChecked(False)
        else:
            self.btn_CheckOut.setEnabled(False)
            self.btn_Commit.setEnabled(False)
        self.btn_CheckOut.clicked.connect(self.on_check_out)
        self.checkout_state = value

    def on_project_changed(self, dbproject):
        self.dbproject = dbproject
        if self.dbproject is None:
            return
        # self.btn_CheckOut.clicked.disconnect()
        # if self.dbproject.is_checked_out:
        #     self.btn_CheckOut.setChecked(True)
        # else:
        #     self.btn_CheckOut.setChecked(False)
        # self.btn_CheckOut.clicked.connect(self.on_check_out)

    def on_check_out(self):
        print("Current DBProject:", self.dbproject)
        if self.dbproject is not None:
            if self.btn_CheckOut.isChecked():
                self.corpus_client.checkout_project(self.dbproject)
            else:
                self.corpus_client.checkin_project(self.dbproject)


class CreateCorpusDialog(EDialogWidget):
    onCreated = pyqtSignal(object)

    def __init__(self, main_window):
        super(CreateCorpusDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogCreateCorpus.ui")
        uic.loadUi(path, self)

        self.sl_segm = StringList(self)
        self.sl_segm.setTitle("Add all Default Segmentation Names:")
        self.wc_segm.layout().addWidget(self.sl_segm)

        self.sl_layers = StringList(self)
        self.sl_layers.setTitle("Add all Default Annotation Layer Names:")
        self.wc_ann.layout().addWidget(self.sl_layers)

        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Help.clicked.connect(self.on_help)
        self.btn_OK.clicked.connect(self.on_create)
        self.btn_Cancel.clicked.connect(self.on_cancel)
        self.lineEdit_Root.setText(self.main_window.settings.DIR_CORPORA)


    def on_browse(self):
        root = QFileDialog.getExistingDirectory(self, directory=self.main_window.settings.DIR_CORPORA)
        self.lineEdit_Root.setText(root)

    def on_create(self):
        # TODO Deprecated
        pass
        # if self.lineEdit_Name.text() != "" and os.path.isdir(self.lineEdit_Root.text()):
        #     database = DatasetCorpusDB()
        #     database.allow_movie_upload = self.cB_AllowUpload.isChecked()
        #     database.allow_project_download = self.cb_AllowDownload.isChecked()
        #
        #     database.constrain_segmentations = self.cB_ConstrSegmentation.isChecked()
        #     database.constrain_analyses = self.cB_ConstrAnalyses.isChecked()
        #     database.constrain_class_objs = self.cB_ConstrClassObj.isChecked()
        #     database.constrain_vocabularies = self.cB_ConstrVocabularies.isChecked()
        #     database.constrain_experiments = self.cB_ConstrExperiments.isChecked()
        #
        #     database.default_segmentations = self.sl_segm.get_entries()
        #     database.default_annotation_layers = self.sl_layers.get_entries()
        #
        #     database.initialize(self.lineEdit_Name.text(), self.lineEdit_Root.text())
        #
        #     self.close()
        #     self.onCreated.emit(database)
        # else:
        #     QMessageBox.warning(self, "Missing Values", "Please fill out the Form")

    def on_cancel(self):
        self.close()


class CorpusUserDialog(EDialogWidget):
    onContributorUpdate = pyqtSignal(object)

    def __init__(self, main_window, contributor:Contributor):
        super(CorpusUserDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogCorpusUser.ui")
        uic.loadUi(path, self)

        self.contributor = contributor
        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)

        self.lineEdit_Name.setText(self.contributor.user_name)
        self.lineEdit_FullName.setText(self.contributor.full_name)
        self.lineEdit_Affiliation.setText(self.contributor.affiliation)
        self.lineEdi_Email.setText(self.contributor.email)
        self.widget_image.setLayout(QHBoxLayout(self))

        self.preview = EGraphicsView(self, auto_frame=True)
        self.widget_image.layout().addWidget(self.preview)

        self.image_path = ""
        if os.path.isfile(self.contributor.image_path):
            self.image_path = self.contributor.image_path
            img_bgr = cv2.imread(self.image_path)
            img = numpy_to_pixmap(img_bgr, target_width=128)
            self.preview.set_image(img)
        else:
            self.image_path = os.path.abspath("qt_ui/images/Blank_woman_placeholder.png")
            img_bgr = cv2.imread(self.image_path)
            img = numpy_to_pixmap(img_bgr, target_width=128)
            self.preview.set_image(img)

    def on_browse(self):
        path = QFileDialog.getOpenFileName(self, filter="*.png *.jpg")[0]
        if os.path.isfile(path):
            img_bgr = cv2.imread(path)
            img = numpy_to_pixmap(img_bgr, target_width=128)
            self.preview.set_image(img)
            self.image_path = path

    def on_ok(self):
        salt = uuid.uuid4().hex

        self.contributor.name = self.lineEdit_Name.text()
        # self.contributor.password = hashlib.sha512((self.lineEdi_Password.text() + salt).encode()).hexdigest()
        # self.contributor.email = hashlib.sha512((self.lineEdi_Email.text() + salt).encode()).hexdigest()
        self.contributor.password = self.lineEdi_Password.text()
        self.contributor.email = self.lineEdi_Email.text()
        self.contributor.full_name = self.lineEdit_FullName.text()

        if os.path.isfile(self.image_path):
            cv2.imwrite(self.main_window.settings.DIR_CORPORA + "/user_img.jpg", cv2.imread(self.image_path))
        self.contributor.image_path = self.image_path
        self.onContributorUpdate.emit(self.contributor)
        self.close()

    def on_cancel(self):
        self.close()


class CorpusConnectRemoteDialog(EDialogWidget):
    onConnectRemote = pyqtSignal(str, int, str, int)

    def __init__(self, main_window, contributor:DBContributor):
        super(CorpusConnectRemoteDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogConnectRemoteCorpus.ui")
        uic.loadUi(path, self)

        self.contributor = contributor
        self.btn_Connect.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)

    def on_ok(self):
        self.onConnectRemote.emit(self.lineEdit.text(), self.spinBox.value(),
                                  self.lineEdit_FTPIP.text(), self.spinBox_FTPPORT.value())
        self.close()

    def on_cancel(self):
        self.close()