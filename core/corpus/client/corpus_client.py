from core.corpus.client.webapp_corpus_interface import *
from core.corpus.shared.widgets import CorpusUserDialog
from core.data.settings import Contributor

try:
    from core.data.interfaces import IConcurrentJob
    from core.data.computation import extract_zip
except:
    class IConcurrentJob: pass
    class IProjectChangeNotify: pass
    def extract_zip(*args, **kwargs): pass
    def create_icon(*args, **kwargs): pass

import json
import shutil


class CorpusClient(QObject, IProjectChangeNotify):
    """
    The CorpusClient class manages the specific subclass of corpus_interface.CorpusInterface that is 
    initialised during connecting. 
    """

    #SIGNALS to the VIAN GUI
    onCorpusConnected = pyqtSignal(object)
    onCorpusDisconnected = pyqtSignal(object)
    onCorpusChanged = pyqtSignal(object)
    onCurrentDBProjectChanged = pyqtSignal(object)
    onCheckOutStateChanged = pyqtSignal(int)

    #SIGNALS to the CorpusInterface subclass
    onConnectUser = pyqtSignal(object, object)
    onDisconnectUser = pyqtSignal(object)
    onCommitProject = pyqtSignal(object, object)
    onCheckOutProject = pyqtSignal(object, object)
    onCheckInProject = pyqtSignal(object, object)
    onDownloadProject = pyqtSignal(object, object)
    onCheckCheckOutState = pyqtSignal(object, object)

    def __init__(self, parent):
        super(CorpusClient, self).__init__(parent)
        self.tcp_ip = "127.0.0.1"
        self.tcp_port = 5005
        self.is_remote = False
        self.corpus_interface = CorpusInterface()
        self.connected = False
        self.main_window = parent

        self.execution_thread = None

        self.current_dbproject = None

        #Loading the Meta data from previous sessions
        self.metadata_path = parent.settings.DIR_CORPORA + "corpora_metadata.json"
        self.metadata = CorpusMetaDataList(self.metadata_path, contributor=self.main_window.settings.CONTRIBUTOR)
        self.metadata.load(self.metadata_path)

        WebAppCorpusInterface().ping()
        # self.on_connect_webapp("http://127.0.0.1:5000/vian_login")

    @pyqtSlot()
    def connect(self, remote = False):
        pass

    def on_connect_local(self, file_path):
        try:
            self.is_remote = False
            self.corpus_interface = LocalCorpusInterface()
            self.connect_signals()
            self.execution_thread = QThread()
            self.corpus_interface.moveToThread(self.execution_thread)
            self.execution_thread.start()

            self.onConnectUser.emit(self.main_window.settings.CONTRIBUTOR, file_path)
        except Exception as e:
            print(e)

    @pyqtSlot(str, int, str, int)
    def connect_remote(self, tcp_ip, tcp_port, ftp_ip, ftp_port):
        try:
            self.is_remote = True
            self.corpus_interface = RemoteCorpusInterface(self.main_window.settings.DIR_CORPORA)
            self.connect_signals()
            self.execution_thread = QThread()
            self.corpus_interface.moveToThread(self.execution_thread)
            self.execution_thread.start()
            self.onConnectUser.emit(self.main_window.settings.CONTRIBUTOR, [tcp_ip, tcp_port, ftp_ip, ftp_port])

        except Exception as e:
            print(e)

    @pyqtSlot(str)
    def on_connect_webapp(self, endpoint):
        """
        Signal Cascade: self.on_connect_webapp() -> CorpusInterface.connect_user() -> self.on_connect_finished()
        
        :param endpoint: The endpoint that is currently hardcoded in the constructor
        :return: 
        """
        # TODO @SILAS This is where the WebAppCorpusInterface is initialized and the autentification starts
        # TODO Remember that the WebAppCorpusInterface is handled by another Thread, no direct invoking of Functions is allowed
        # TODO everything has to be done with Signal Slots communication, but I think all messages are already setup.

        self.is_remote = True
        self.corpus_interface = WebAppCorpusInterface()

        # Connecting all Signals to the Slots of the WebAppCorpusInterface
        self.connect_signals()

        # Run it on a new Thread
        self.execution_thread = QThread()
        self.corpus_interface.moveToThread(self.execution_thread)
        self.execution_thread.start()

        # Emit the onConnectUser to the WebAppCorpusInterface, this initiates the authentification process
        # Every thing GUI related to the Login has to happen HERE
        contributor = self.main_window.settings.CONTRIBUTOR  # type: Contributor
        self.onConnectUser.emit(contributor, endpoint)

    def connect_signals(self):
        try:
            self.onConnectUser.disconnect()
            self.onCommitProject.disconnect()
            self.onCheckOutProject.disconnect()
            self.onCheckInProject.disconnect()
            self.onDownloadProject.disconnect()

            self.corpus_interface.onConnected.disconnect()
            self.corpus_interface.onCheckedIn.disconnect()
            self.corpus_interface.onCheckedOut.disconnect()
            self.corpus_interface.onCommited.disconnect()
            self.corpus_interface.onReceivedProjects.disconnect()
        except:
            pass

        self.onConnectUser.connect(self.corpus_interface.connect_user)
        self.onDisconnectUser.connect(self.corpus_interface.disconnect_user)
        self.onCommitProject.connect(self.corpus_interface.commit_project)
        self.onCheckOutProject.connect(self.corpus_interface.checkout_project)
        self.onCheckInProject.connect(self.corpus_interface.checkin_project)
        self.onDownloadProject.connect(self.corpus_interface.download_project)
        self.onCheckCheckOutState.connect(self.corpus_interface.check_checkout_state)

        self.corpus_interface.onConnected.connect(self.on_connect_finished)
        self.corpus_interface.onCheckedIn.connect(self.on_check_in_finished)
        self.corpus_interface.onCheckedOut.connect(self.on_check_out_finished)
        self.corpus_interface.onCommited.connect(self.on_commit_finished)
        self.corpus_interface.onReceivedProjects.connect(self.on_received_projects)
        self.corpus_interface.onReadyForExtraction.connect(self.on_project_downloaded)
        self.corpus_interface.onCheckOutStateRecieved.connect(self.on_check_out_state_recieved)

    @pyqtSlot(bool, object, object)
    def on_connect_finished(self, success, dbprojects, user):
        """
        Signal Cascade: self.on_connect_webapp() -> CorpusInterface.connect_user() -> self.on_connect_finished()
        
        This slot is called by the CorpusInterface after an attempt to connect
        :param success: 
        :param dbprojects: 
        :param user: 
        :return: 
        """
        if success:
            self.connected = True
            self.onCorpusConnected.emit(self.corpus_interface)

            # self.metadata.on_connect(self.tcp_ip, self.corpus_interface.name, self.tcp_port, dbprojects, "local")
            # self.synchronize(self.corpus_interface.name, dbprojects)
            # if self.get_project() is not None:
            #     self.get_check_out_state()
        else:
            print("Failed to connect")

    def on_commit_project(self, project):
        """
        This function is called when the user wants do commit a project. 
        Signal Cascade: self.on_commit_project() -> CorpusInterface.commit_project() -> self.on_commit_finished()
        :param project: VIANProject
        :return: 
        """
        try:
            self.main_window.on_save_project(sync=True)
            self.onCommitProject.emit(self.main_window.settings.CONTRIBUTOR, project)
        except Exception as e:
            print("Exception in CorpusClient::on_commit_project()", e)

    @pyqtSlot(bool, object, object)
    def on_commit_finished(self, success, dbproject, vian_project:VIANProject):
        if success:
            answer = QMessageBox.question(self.main_window, "Remove Local Project", "The Project has been commited.\n "
                                                        "Do you want to remove the working project just commited?\n "
                                                        "It can later be downloaded again")
            if answer == QMessageBox.Yes:
                shutil.rmtree(vian_project.folder, True, print)
            self.metadata.update_project(self.corpus_interface.name, dbproject)
            self.current_dbproject = dbproject
            vian_project.corpus_id = dbproject.project_id
            self.onCurrentDBProjectChanged.emit(dbproject)
            self.main_window.on_save_project()
        self.metadata.store()
        self.onCorpusChanged.emit(self)

    def on_disconnect_user(self):
        self.onDisconnectUser.emit(self.main_window.settings.CONTRIBUTOR)
        self.connected = False
        if self.execution_thread is not None:
            self.execution_thread.quit()

    def on_open_corpus_project(self, dbproject: DBProject):
        if self.connected:
            success, path = self.metadata.has_local_file(self.corpus_interface.name, dbproject)
            print("Project is Local: ", success, path)
            print("ProjectID: ", dbproject.project_id)
            if success:
                self.onCorpusChanged.emit(self)
                self.main_window.load_project(path)
            else:
                answer = QMessageBox.question(self.main_window, "No Local File Found", "There is no local file of " + dbproject.name + ".\n"
                                      "do you want to download it from the Corpus?")
                if answer == QMessageBox.Yes:
                    self.onDownloadProject.emit(self.main_window.settings.CONTRIBUTOR, dbproject)

    @pyqtSlot(object)
    def on_received_projects(self, dbprojects):
        pass

    @pyqtSlot(bool, object, str)
    def on_project_downloaded(self, success, dbproject, archive):
        print("Download:", success)
        if success:
            dbproject.path = self.main_window.settings.DIR_PROJECT + "/" + dbproject.name + "/" + dbproject.name + ".eext"
            dbproject.folder = self.main_window.settings.DIR_PROJECT + "/" + dbproject.name
            extract_zip(archive, self.main_window.settings.DIR_PROJECT + "/" + dbproject.name)
            self.onCorpusChanged.emit(self)
            answer = QMessageBox.question(self.main_window, "Download Complete",    "The download of " + dbproject.name + " is complete.\n "
                                                                                    "Do you want to open it now?")
            if answer == QMessageBox.Yes:
                self.main_window.load_project(dbproject.path)

    def checkout_project(self, dbproject: DBProject):
        if self.connected:
            self.onCheckOutProject.emit(self.main_window.settings.CONTRIBUTOR, dbproject)

    @pyqtSlot(bool, object)
    def on_check_out_finished(self, success, dbprojects: List[DBProject]):
        print("Checkout: ", success)
        if success:
            self.synchronize(self.corpus_interface.name, dbprojects)

    def checkin_project(self, dbproject:DBProject):
        if self.connected:
            self.onCheckInProject.emit(self.main_window.settings.CONTRIBUTOR, dbproject)

    @pyqtSlot(bool, object)
    def on_check_in_finished(self, success, project):
        print("CheckIn: ", success)
        pass

    def get_project_from_corpus(self, corpus_id):
        if not self.connected:
            return

        if self.is_remote:
            pass
        else:
            return self.corpus_interface.get_project(corpus_id)

    def get_check_out_state(self):
        if self.connected and self.current_dbproject is not None:
            self.onCheckCheckOutState.emit(self.main_window.settings.CONTRIBUTOR, self.current_dbproject)

    @pyqtSlot(int)
    def on_check_out_state_recieved(self, value):
        self.onCheckOutStateChanged.emit(value)

    def on_synchronize(self):
        pass

    def synchronize(self, corpus_name, dbprojects: List[DBProject]):
        self.metadata.synchronize_corpus(corpus_name, dbprojects)
        self.onCorpusChanged.emit(self)

    #region Querying
    def remove_project(self, dbproject:DBProject):
        if not self.connected:
            return
        if self.is_remote:
            pass
        else:
            self.corpus_interface.remove_project(dbproject)
        self.onCorpusChanged.emit(self)

    def get_projects(self, filters = None):
        if self.connected:
            return self.metadata.get_project(self.corpus_interface.name)
        else:
            return []

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

    def get_corpus(self):
        return self.corpus_interface

    def on_loaded(self, project):
        if not self.connected:
            return
        print("Project CorpusID: ", project.corpus_id)
        if project.corpus_id == -1:
            # Try to find it  by the Path
            self.current_dbproject = self.metadata.get_project_by_path(self.get_corpus().name, project.path)
            if self.current_dbproject is not None:
                project.corpus_id = self.current_dbproject.project_id
        else:
            self.current_dbproject = self.metadata.get_project(self.corpus_interface.name, project.corpus_id)
            self.get_check_out_state()
        self.onCurrentDBProjectChanged.emit(self.current_dbproject)

    def on_closed(self):
        pass

    def on_selected(self, sender, selected):
        pass

    def on_changed(self, project, item):
        pass


class CorpusClientToolBar(QToolBar):
    def __init__(self, parent, corpus_client: CorpusClient):
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


class CorpusMetaDataList():
    def __init__(self, path, contributor = None):
        self.corporas = []
        self.path = path
        # if contributor is None:
        #     contributor = DBContributor("Anonymous", "", "Hogwarts School of Witchcraft and Wizardry")
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

    def get_project(self, corpus_name, project_id = None, project_name = None):
        if project_id is not None and project_name is None:
            c = self.get_corpus(corpus_name)
            if c is not None:
                for p in c.projects:
                    if project_id is not None:
                        if p.project_id == project_id:
                            return p
                        elif project_name == p.name:
                            return p
            return None
        else:
            c = self.get_corpus(corpus_name)
            if c is not None:
                return c.projects
            else:
                return []

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
        if c is None or dbprojects is None:
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
                corporas = [c.serialize() for c in self.corporas]
            )
            json.dump(data, f)

    def load(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self.corporas = [CorpusMetaData(None, None, None, None).deserialize(s) for s in data['corporas']]
        except Exception as e:
            self.corporas = []
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

