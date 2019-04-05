from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
from core.data.settings import Contributor
import os
from PyQt5 import uic
from core.data.computation import create_icon
from core.corpus.client.corpus_client import CorpusClient
from core.gui.Dialogs.new_project_dialog import FilmographyWidget

from core.gui.ewidgetbase import *
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
        path = os.path.abspath("qt_ui/CorpusClientWidget2.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        self.main_window = main_window

        self.dbproject = None
        self.checkout_state = 0

        self.corpus_client.onConnectionEstablished.connect(self.on_connected)
        self.corpus_client.onDisconnect.connect(self.on_disconnected)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))
        self.btn_Options.clicked.connect(self.on_options)
        self.btn_Commit.clicked.connect(self.on_commit)
        self.btn_Commit.setEnabled(False)
        self.btn_Connect.setEnabled(True)
        self.btn_Connect.clicked.connect(self.on_connect)

        # self.comboBox_Corpora.addItem("ERC FilmColors") #type:QComboBox
        # self.comboBox_Corpora.currentTextChanged.connect(self.on_corpus_changed)
        #
        # #  self.btn_.clicked.connect(self.corpus_client.connect)
        #
        # self.on_contributor_update(self.main_window.settings.CONTRIBUTOR)
        self.show()

    def on_connect(self):
        self.on_connected(None)
        ret = False
        if self.main_window.settings.CONTRIBUTOR.token is not None:
            ret = self.corpus_client.connect_webapp(self.main_window.settings.CONTRIBUTOR)['success']

        if self.main_window.settings.CONTRIBUTOR.token is None or ret is False:
            dialog = WebAppLoginDialog(self.main_window, self.corpus_client)
            dialog.show()

    def on_options(self):
        menu = CorpusOptionMenu(self, self.corpus_client)
        menu.popup(QCursor.pos())

    @pyqtSlot(object)
    def on_connected(self, corpus):
        self.btn_Commit.setEnabled(True)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp.png"))

    @pyqtSlot(object)
    def on_disconnected(self, corpus):
        self.btn_Commit.setEnabled(False)
        self.btn_Connect.setIcon(create_icon("qt_ui/icons/icon_webapp_off.png"))

    def on_commit(self):
        dialog = CorpusCommitDialog(self.main_window, self.corpus_client)
        dialog.show()
        # if self.main_window.project is not None:
        #     self.corpus_client.commit(self.main_window.project, self.main_window.settings.CONTRIBUTOR)
        # pass


class WebAppLoginDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(WebAppLoginDialog, self).__init__(main_window)
        path = os.path.abspath("qt_ui/CorpusLoginDialog.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.corpus_client = corpus_client
        self.btn_Login.clicked.connect(self.on_ok)
        self.lineEdit_Email.setText(self.main_window.settings.CONTRIBUTOR.email)
        self.lineEdit_Password.setText(self.main_window.settings.CONTRIBUTOR.password)

    def on_ok(self):
        self.main_window.settings.CONTRIBUTOR.email = self.lineEdit_Email.text()
        self.main_window.settings.CONTRIBUTOR.password = self.lineEdit_Password.text()
        res = self.corpus_client.connect_webapp(self.main_window.settings.CONTRIBUTOR)['success']
        if res:
            self.corpus_client.onConnectionEstablished.emit(dict(success=True))
            self.close()
        else:
            QMessageBox.warning(self, "Could not Establish Connection",
                                "It has not been possible to login on the FilmColors Webapp, check your credentials again or create an account.")





    def on_login_tried(self):
        pass

    def on_cancel(self):
        self.close()


class CorpusOptionMenu(QMenu):
    def __init__(self, parent, corpus_client:CorpusClient):
        super(CorpusOptionMenu, self).__init__(parent)
        self.corpus_client = corpus_client
        self.a_disconnect = self.addAction("Disconnect")
        self.a_disconnect.triggered.connect(self.corpus_client.disconnect_corpus)


class CorpusCommitDialog(EDialogWidget):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(CorpusCommitDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogHLayout.ui")
        uic.loadUi(path, self)
        self.corpus_client = corpus_client
        try:
            self.movies = self.corpus_client.corpus_interface.get_movies()
            self.persons = self.corpus_client.corpus_interface.get_persons()
            self.processes = self.corpus_client.corpus_interface.get_color_processes()
        except Exception as e:
            self.persons = None
            print(e)

        self.filmography = FilmographyWidget(self, main_window.project, persons=self.persons, processes=self.processes)
        self.horizontalLayoutUpper.addWidget(self.filmography)
        self.pushButton_Commit.clicked.connect(self.on_commit)
        self.pushButton_Cancel.clicked.connect(self.close)

    def on_commit(self):
        if self.main_window.project is not None:
            self.corpus_client.commit(self.main_window.project, self.main_window.settings.CONTRIBUTOR)
        pass