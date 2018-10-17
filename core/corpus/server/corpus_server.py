from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
import os
from PyQt5 import uic
import json
import socket
import threading
import shutil

from glob import glob


from core.corpus.shared.enums import *
from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.entities import *

try:
    from core.data.headless import load_project_headless
except:
    def load_project_headless(*args, **kwargs): pass


from core.corpus.server.corpus_server_http import *
import dataset as ds


class CorpusServerWindow(QMainWindow):
    def __init__(self):
        super(CorpusServerWindow, self).__init__()
        path = os.path.abspath("qt_ui/CorpusServerWindow.ui")
        uic.loadUi(path, self)

        self.server = CorpusServer(None)

        self.server_thread = QThread(self)
        self.server.moveToThread(self.server_thread)
        self.server_thread.start()
        self.actionRun.triggered.connect(self.server.listen)
        self.actionLoad_Dataset.triggered.connect(self.on_open)
        self.show()

    def on_open(self):
        try:
            path = QFileDialog.getOpenFileName(self, filter="*.vian_corpus")[0]
            self.server.local_corpus.load(path)
            self.server.ftp_path =self.server.local_corpus.root_dir + "/ftp/"
            if not os.path.isdir( self.server.ftp_path):
                os.mkdir( self.server.ftp_path)

        except Exception as e:
            print(e)

