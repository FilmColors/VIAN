from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QToolBar, QHBoxLayout, QSpacerItem, QSizePolicy, QWidgetAction
from core.data.settings import UserSettings, Contributor
from core.container.project import VIANProject

import os
import requests


class CorpusClient(QObject):
    onConnectionEstablished = pyqtSignal(object)
    onConnectionFailed = pyqtSignal(object)
    onCommitStarted = pyqtSignal(object)
    onCommitProgress = pyqtSignal(float)
    onCommitFinished = pyqtSignal(object)
    onCommitFailed = pyqtSignal(object)
    onDisconnect = pyqtSignal(object)

    def __init__(self):
        super(CorpusClient, self).__init__()
        self.corpus_interface = None
        self.execution_thread = None

    def mode(self):
        if isinstance(self.corpus_interface, WebAppCorpusInterface):
            return "webapp"
        elif isinstance(self.corpus_interface, LocalCorpusInterface):
            return "local"
        else:
            return None

    def connect_signals(self):
        if self.corpus_interface is not None:
            self.corpus_interface = LocalCorpusInterface

    @pyqtSlot(object, str)
    def connect_local(self, user: UserSettings, filepath):
        """
        Connects the user to a local Database of VIAN Projects at given database.db file
        :param user: the user object
        :param filepath: the file path to the sqlite file
        :return:
        """
        self.corpus_interface = LocalCorpusInterface()
        self.execution_thread = QThread()
        self.corpus_interface.moveToThread(self.execution_thread)
        self.execution_thread.start()
        pass

    @pyqtSlot(object, str)
    def connect_webapp(self, user: UserSettings, address):
        self.corpus_interface = WebAppCorpusInterface()
        self.execution_thread = QThread()
        self.corpus_interface.moveToThread(self.execution_thread)
        self.execution_thread.start()
        pass

    @pyqtSlot(object)
    def on_connect_finished(self, result):
        if result is not None:
            r = dict(
                corpus_name = result['corpus_name']
            )
            self.onConnectionEstablished.emit(r)
        else:
            self.onConnectionFailed.emit(result)

        pass

    @pyqtSlot(object)
    def commit(self, project:VIANProject):
        if self.mode() is not None:
            self.onCommitStarted.emit(project)
        else:
            self.onCommitFailed.emit()


    @pyqtSlot(object)
    def on_commit_finished(self):
        pass

    @pyqtSlot(object)
    def download(self, desc):
        pass

    @pyqtSlot(object)
    def on_download_finished(self):
        pass




class CorpusInterfaceSignals():
    onConnected = pyqtSignal()
    onConnectionFailed = pyqtSignal()
    onCommitFinished = pyqtSignal()
    onCommitProgress = pyqtSignal()

class WebAppCorpusInterface(QObject):
    def __init__(self, ep_root = "http://127.0.0.1:5000/api/"):
        super(WebAppCorpusInterface, self).__init__()
        self.ep_root = ep_root
        self.ep_upload = self.ep_root + "upload"
        self.ep_token = self.ep_root + "/get_token"
        self.ep_ping = self.ep_root + "vian/ping"
        self.ep_version = self.ep_root + "vian/version"
        self.signals = CorpusInterfaceSignals()

    @pyqtSlot()
    def ping(self):
        """
        performs a simple ping to the WebApp server
        :return: returns true if there was a response
        """
        pass

    @pyqtSlot(object)
    def login(self, user:Contributor):
        """
        Checks if a user exists on the WebApp, if so, connects and returns true
        else returns False
        :param user: The user to login
        :return: If the login was successful returns True, else returns False
        """
        try:
            # We need to get the identification token
            a = requests.post(self.ep_token, json=dict(email = user.email, password = user.password))
            print("Server Responded:", a.headers, a.text)
            success = not "failed" in a.text
            if success:
                # We don't want VIAN to see all Projects on the WebAppCorpus, thus returning an empty list
                all_projects = []
                user.token = a.text
                ret = dict()
                #Todo return a good success description object
                self.signals.onConnected.emit(ret)
            else:
                ret = dict()
                #Todo return a good faile descirption object
                self.signals.onConnectionFailed.emit(ret)
        except Exception as e:
            raise e
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.onConnected.emit(False, None, None)

        pass

    @pyqtSlot(object)
    def logout(self, user:UserSettings):
        pass

    @pyqtSlot(object)
    def commit_project(self, project:VIANProject):
        pass

    @pyqtSlot(object)
    def download_project(self, desc):
        pass

class LocalCorpusInterface():
    def __init__(self):
        pass