from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.enums import *
from core.corpus.shared.entities import *
from core.corpus.shared.widgets import CorpusUserDialog

from core.data.interfaces import IConcurrentJob
from core.data.computation import extract_zip

import socket
import json
import shutil

class CorpusClient(QObject, IProjectChangeNotify):
    onCorpusConnected = pyqtSignal(object)
    onCorpusDisconnected = pyqtSignal(object)
    onCorpusChanged = pyqtSignal(object)
    onCurrentDBProjectChanged = pyqtSignal(object)

    def __init__(self, parent):
        super(CorpusClient, self).__init__(parent)
        self.tcp_ip = "127.0.0.1"
        self.tcp_port = 5005
        self.is_remote = False
        self.local_corpus = None
        self.connected = False
        self.main_window = parent

        self.current_dbproject = None

        self.metadata_path = parent.settings.DIR_CORPORA + "corpora_metadata.json"
        self.metadata = CorpusMetaDataList(self.metadata_path)
        self.metadata.load(self.metadata_path)

    @pyqtSlot()
    def connect(self, remote = False):
        pass

    def connect_local(self, file_path):
        self.is_remote = False
        self.local_corpus = DatasetCorpusDB().load(file_path)
        self.local_corpus.connect_user(self.metadata.contributor)
        if self.local_corpus is not None:
            self.connected = True
            self.onCorpusConnected.emit(self.local_corpus)
            self.metadata.on_connect(self.tcp_ip, self.local_corpus.name, self.tcp_port, self.local_corpus.get_projects(), "local")
            self.metadata.synchronize_corpus(self.local_corpus.name, self.get_corpus().get_projects())
            self.onCorpusChanged.emit(self)

    def connect_remote(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tcp_ip, self.tcp_port))
            s.send(self.make_message(ServerCommands.Connect))
            data = s.recv(BUFFER_SIZE)
            print(data)
            s.close()
        except Exception as e:
            print(e)

    def on_commit_project(self, project):
        self.commit_project(project)

    def commit_project(self, project: VIANProject):
        if not self.connected:
            return

        if self.is_remote:
            pass
        else:
            old_dir = project.folder
            self.main_window.on_save_project(sync=True)
            success, dbproject = self.local_corpus.commit_project(project, self.metadata.contributor)
            # The Path might have changed

            if success:
                answer = QMessageBox.question(self.main_window, "Remove Local Project", "The Project has been commited.\n "
                                                    "It is now located in <YourCorpus/projects/<Your_Project.zip>\n\n "
                                                    "Do you want to remove the working project just commited?\n "
                                                    "It can later be downloaded again")
                if answer == QMessageBox.Yes:
                    shutil.rmtree(old_dir, True, print)
                dbproject.path = project.path
                dbproject.folder = project.folder
                self.metadata.update_project(self.local_corpus.name, dbproject)

        self.on_commit_finished()

    def on_commit_finished(self):
        self.metadata.store()
        self.onCorpusChanged.emit(self)

    def disconnect(self):
        self.connected = False

    def get_project_path(self, dbproject: DBProject):
        if not self.connected:
            return
        if self.is_remote:
            pass
        else:
            success, path = self.metadata.has_local_file(self.local_corpus.name, dbproject)
            print("TEST GET PATH ", success, path)
            print("ProjectID: ", dbproject.project_id)
            if success:
                self.onCorpusChanged.emit(self)
                return path
            else:
                answer = QMessageBox.question(self.main_window, "No Local File Found", "There is no local file of " + dbproject.name + ".\n"
                                      "do you want to download it from the Corpus?")
                if answer == QMessageBox.Yes:
                    archive = self.local_corpus.get_project_path(dbproject)
                    if archive is not None:
                        dbproject.path = self.main_window.settings.DIR_PROJECT + "/" + dbproject.name + "/" + dbproject.name + ".eext"
                        dbproject.folder = self.main_window.settings.DIR_PROJECT + "/" + dbproject.name
                        extract_zip(archive, self.main_window.settings.DIR_PROJECT + "/" + dbproject.name)
                        self.onCorpusChanged.emit(self)
                        self.metadata.synchronize_corpus(self.get_corpus().name, self.local_corpus.get_projects())
                        return dbproject.path
        return None

    def checkout_project(self, dbproject: DBProject):
        if not self.connected:
            return
        if self.is_remote:
            pass
        else:
            success, location = self.local_corpus.checkout_project(dbproject.project_id, self.metadata.contributor)

            # if success:
            #     extract_zip(location, self.main_window.settings.DIR_PROJECT + "/" + dbproject.name + "/")
            print("CheckOut: ", success, location)

            self.metadata.synchronize_corpus(self.local_corpus.name, self.local_corpus.get_projects())
        self.onCorpusChanged.emit(self)

    def checkin_project(self, dbproject:DBProject):
        if not self.connected:
            return
        if self.is_remote:
            pass
        else:
            success = self.local_corpus.checkin_project(dbproject.project_id, self.metadata.contributor)
            print("CheckIn: ", success)

        self.metadata.synchronize_corpus(self.local_corpus.name, self.get_corpus().get_projects())
        self.onCorpusChanged.emit(self)

    def get_project_from_corpus(self, corpus_id):
        if not self.connected:
            return

        if self.is_remote:
            pass
        else:
            return self.local_corpus.get_project(corpus_id)

    def synchronize(self):
        self.metadata.synchronize_corpus(self.get_corpus(), self.get_corpus().get_projects())
        self.onCorpusChanged.emit(self)

    #region Querying

    def remove_project(self, dbproject:DBProject):
        if not self.connected:
            return
        if self.is_remote:
            pass
        else:
            self.local_corpus.remove_project(dbproject)
        self.onCorpusChanged.emit(self)

    def get_projects(self, filters = None):
        if not self.connected:
            return []

        if self.is_remote:
            return []
        else:
            return self.local_corpus.get_projects(filters)

    def get_annotation_layers(self, filters = None):
        pass

    def get_segmentations(self, filters = None):
        pass

    def get_segments(self, filters = None):
        pass

    def get_screenshots(self, filters = None):
        pass

    def get_annotations(self, filters = None):
        pass

    def get_vocabularies(self = None):
        pass

    def get_analysis_results(self, filters = None):
        pass

    def get_words(self = None):
        pass

    def get_settings(self = None):
        pass
    #endregion

    def get_corpus(self) -> DatasetCorpusDB:
        if self.is_remote:
            pass
        else:
            return self.local_corpus

    def make_message(self, command: ServerCommands, message=None):
        if message is None:
            message = dict()
        return (str(command.value) + SPLIT_ITEM + json.dumps(message)).encode()

    def on_loaded(self, project):
        if not self.connected:
            return
        print("Project CorpusID: ", project.corpus_id)
        if project.corpus_id == -1:
            # Try to find it  by the Path
            self.current_dbproject = self.metadata.get_project_by_path(self.get_corpus().name, project.path)
            if self.current_dbproject is not None:
                project.corpus_id = self.current_dbproject.project_id
            pass
        else:
            self.current_dbproject = self.get_project_from_corpus(project.corpus_id)
        self.onCurrentDBProjectChanged.emit(self.current_dbproject)

    def on_closed(self):
        pass

    def on_selected(self, sender, selected):
        pass


class CorpusClientToolBar(QToolBar):
    def __init__(self, parent, corpus_client: CorpusClient):
        super(CorpusClientToolBar, self).__init__(parent)

        self.spacer = QWidget()
        self.spacer.setLayout(QHBoxLayout())
        self.spacer.layout().addItem(QSpacerItem(1,1,QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.addWidget(self.spacer)

        self.addAction(CorpusClientWidgetAction(self, corpus_client, parent))

    def get_client(self):
        return self.corpus_client


class CorpusClientWidgetAction(QWidgetAction):
    def __init__(self, parent, corpus_client, main_window):
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

        self.corpus_client.onCorpusConnected.connect(self.on_connected)
        self.corpus_client.onCorpusDisconnected.connect(self.on_disconnected)
        self.corpus_client.onCurrentDBProjectChanged.connect(self.on_project_changed)
        self.contributor = corpus_client.metadata.contributor

        self.btn_Commit.clicked.connect(self.on_commit)
        self.btn_CheckOut.clicked.connect(self.on_check_out)
        self.btn_Person.clicked.connect(self.open_contributor_editor)
        self.btn_Update.clicked.connect(self.on_update)
        self.btn_Commit.setEnabled(False)
        self.btn_CheckOut.setEnabled(False)
        self.btn_Update.setEnabled(False)

        #  self.btn_.clicked.connect(self.corpus_client.connect)

        self.on_contributor_update(self.corpus_client.metadata.contributor)
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

    def open_contributor_editor(self):
        dialog = CorpusUserDialog(self.main_window, self.corpus_client.metadata.contributor)
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
        self.corpus_client.synchronize()

    def on_project_changed(self, dbproject):
        self.dbproject = dbproject
        if self.dbproject is None:
            return

        self.btn_CheckOut.clicked.disconnect()
        if self.dbproject.is_checked_out:
            self.btn_CheckOut.setChecked(True)
        else:
            self.btn_CheckOut.setChecked(False)
        self.btn_CheckOut.clicked.connect(self.on_check_out)

    def on_check_out(self):
        if self.dbproject is not None:
            if self.btn_CheckOut.isChecked():
                self.corpus_client.checkout_project(self.dbproject)
            else:
                self.corpus_client.checkin_project(self.dbproject)


class CorpusMetaDataList():
    def __init__(self, path, contributor = None):
        self.corporas = []
        self.path = path
        if contributor is None:
            contributor = DBContributor("Anonymous", "", "Hogwarts School of Witchcraft and Wizardry")
        self.contributor = contributor

    def on_connect(self, ip, name, port, dbprojects, c_type):
        """
        Checks if a Corpus already exists, if so, update the local metadata, 
        else, add it to the Metadata
        :param ip: 
        :param name: 
        :param port: 
        :param dbprojects: 
        :param c_type: 
        :return: 
        """
        c = self.get_corpus(name)
        if c is None:
            self.corporas.append(CorpusMetaData(name, ip, port, dbprojects, c_type))
        else:
            self.synchronize_corpus(name, dbprojects)

        self.store(self.path)

    def get_corpus(self, name):
        for c in self.corporas:
            if c.name == name:
                return c
        return None

    def get_project(self, corpus_name, project_id):
        c = self.get_corpus(corpus_name)
        if c is None:
            for p in c.projects:
                if c.project_id == project_id:
                    return p
        return None

    def get_project_by_path(self, corpus_name, project_path):
        c = self.get_corpus(corpus_name)
        if c is not None:
            for p in c.projects:
                print(p.path, project_path)
                if p.path == project_path:
                    return p
        return None

    def synchronize_corpus(self, corpus, dbprojects):
        c = self.get_corpus(corpus)
        if c is None:
            print("Corpus not Found")
        else:
            resulting = []
            for p in dbprojects:
                for q in c.projects:
                    if p.project_id == q.project_id:
                        p.path = q.path
                        p.folder = q.folder
                        break
                resulting.append(p)
            c.projects = resulting
        self.store()
        pass

    def update_project(self, corpus_name, dbproject):
        c = self.get_corpus(corpus_name)
        if c is not None:
            idx = -1
            for i, m in enumerate(c.projects):
                if dbproject.project_id == m.project_id:
                    idx = i
            if idx > -1:
                c.projects.pop(idx)
                c.projects.insert(idx, dbproject)
            else:
                c.projects.append(dbproject)

            self.store(self.path)

    def has_local_file(self, corpus_name, dbproject: DBProject):
        c = self.get_corpus(corpus_name)
        if c is None:
            return False, None
        else:
            for i, meta in enumerate(c.projects):
                if dbproject.project_id == meta.project_id:
                    if os.path.isfile(dbproject.path):
                        return True, dbproject.path
                    else:
                        dbproject.path = ""
                        return False, None
            return False, None

    def store(self, path = None):
        if path is None:
            path = self.path

        with open(path, "w") as f:
            data = dict(
                contributor = self.contributor.to_database(True),
                corporas = [c.serialize() for c in self.corporas]
            )
            json.dump(data, f)

    def load(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self.corporas = [CorpusMetaData(None, None, None, None).deserialize(s) for s in data['corporas']]
                self.contributor = DBContributor().from_database(data['contributor'])
        except Exception as e:
            self.corporas = []
            self.contributor = DBContributor("Anonymous", "", "Hogwarts School of Witchcraft and Wizardry")
            print(e)


class CorpusMetaData():
    def __init__(self, name=None, ip=None, port=None, dbprojects:DBProject=None, c_type="local"):
        self.name = name
        self.ip = ip
        self.port = port
        self.c_type = c_type

        if dbprojects is not None:
            self.projects = dbprojects

    def serialize(self):
        data = dict(
            name = self.name,
            ip = self.ip,
            port = self.port,
            c_type = self.c_type,
            dbprojects = [p.to_database(True) for p in self.projects],

        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.ip = serialization['ip']
        self.port = serialization['port']
        self.c_type = serialization['c_type']
        self.projects =[DBProject().from_database(p) for p in serialization['dbprojects']]
        return self

