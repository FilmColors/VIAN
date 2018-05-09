from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from core.data.containers import VIANProject
from core.corpus.shared.entities import *
from core.corpus.shared.corpusdb import *

import socket
import ftplib

class CorpusInterface(QObject):
    onConnected = pyqtSignal(bool, object, object)
    onCommited = pyqtSignal(bool, object, object)
    onCheckedIn = pyqtSignal(bool, object)
    onCheckedOut = pyqtSignal(bool, object)
    onReceivedProjects = pyqtSignal(object)
    onReadyForExtraction = pyqtSignal(bool, object, str)
    onEmitProgress = pyqtSignal(float, str)

    def __init__(self):
        super(CorpusInterface, self).__init__()
        self.name = ""

    @pyqtSlot(object, object)
    def connect_user(self, user, options):
        pass

    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project:VIANProject):
        pass

    @pyqtSlot(object, object)
    def checkout_project(self, user, project:DBProject):
        pass

    @pyqtSlot(object, object)
    def checkin_project(self, user, project:DBProject):
        pass

    @pyqtSlot(object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        pass


class LocalCorpusInterface(CorpusInterface):
    def __init__(self):
        super(LocalCorpusInterface, self).__init__()
        self.local_corpus = DatasetCorpusDB()

    @pyqtSlot(object, object)
    def connect_user(self, user:DBContributor, options):
        try:
            self.local_corpus = DatasetCorpusDB().load(options)
            self.name = self.local_corpus.name

            user = self.local_corpus.connect_user(user)

            self.onConnected.emit(True, self.local_corpus.get_projects(), user)
        except:
            self.onConnected.emit(False, None, None)

    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project:VIANProject):
        success, dbproject = self.local_corpus.commit_project(project, user)
        if success:
            self.onCommited.emit(True, dbproject, project)
        else:
            self.onCommited.emit(False, None, project)

    @pyqtSlot(object, object)
    def checkout_project(self, user, project:DBProject):
        success, archive = self.local_corpus.checkout_project(project.project_id, user)
        if success:
            self.onCheckedOut.emit(True, self.local_corpus.get_projects())
        else:
            self.onCheckedOut.emit(False, None)

    @pyqtSlot(object, object)
    def checkin_project(self, user, project:DBProject):
        success = self.local_corpus.checkin_project(project.project_id, user)
        if success:
            self.onCheckedIn.emit(True, self.local_corpus.get_projects())
        else:
            self.onCheckedIn.emit(False, None)

    @pyqtSlot(object, object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        archive = self.local_corpus.get_project_path(project)
        print("Download Project:", project.project_id, archive)
        if archive is not None:
            self.onReadyForExtraction.emit(True, project, archive)
        else:
            self.onReadyForExtraction.emit(False, None, None)


class RemoteCorpusInterface(CorpusInterface):
    def __init__(self, corpora_dir):
        super(RemoteCorpusInterface, self).__init__()
        self.tcp_ip = "127.0.0.1"
        self.tcp_port = 5005
        self.socket = None
        self.corpora_dir = corpora_dir
        self.ftp_password = "Password"
        self.ftp_username = "Gaudenz"
        self.ftp_server_ip = "127.0.0.1"
        self.ftp_server_port = 12345

    @pyqtSlot(object, object)
    def connect_user(self, user:DBContributor, options):
        try:
            self.tcp_ip = options[0]
            self.tcp_port = options[1]
            self.ftp_server_ip = options[2]
            self.ftp_server_ip = options[3]

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.tcp_ip, self.tcp_port))
            answer_encoded = self.send_message(ServerCommands.Connect, dict(user=user.to_database(True)))
            answer = json.loads(answer_encoded.decode())

            success = answer['success']
            if success:
                self.name = answer['corpus_name']
                self.onConnected.emit(success, self.to_project_list(answer['projects']), DBContributor().from_database(answer['user']))
            else:
                self.onConnected.emit(False, None, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.onConnected.emit(False, None, None)

    def to_project_list(self, dlist):
        result = []
        for d in dlist:
            result.append(DBProject().from_database(d))
        return result

    def send_message(self, command: ServerCommands, message=None):
        try:
            if message is None:
                message = dict()
            if self.socket is not None:
                msg = (str(command.value) + SPLIT_ITEM + json.dumps(message)).encode()
                self.socket.send(msg)
            return self.socket.recv(BUFFER_SIZE)
        except Exception as e:
            raise e

    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project: VIANProject):
        try:
            ftp_path = json.loads(self.send_message(ServerCommands.Commit_Inquiry, dict(user=user.to_database(True))).decode())['path']

            file_name = project.name + ".zip"
            archive_file = self.corpora_dir + "/" + project.name
            project_obj = DBProject().from_project(project)
            shutil.make_archive(archive_file, 'zip', project.folder)
            project_obj.archive = archive_file + ".zip"

            ftp_connection = ftplib.FTP()
            ftp_connection.connect(self.ftp_server_ip, self.ftp_server_port)
            ftp_connection.login(self.ftp_username, self.ftp_password)
            ftp_connection.cwd(os.path.split("/ftp/")[1])
            fh = open(archive_file + ".zip", 'rb')
            ftp_connection.storbinary('STOR '+ file_name, fh)
            fh.close()
            os.remove(archive_file + ".zip")

            commit_result = json.loads(self.send_message(ServerCommands.Commit_Finished, dict(archive=file_name, user=user.to_database(True))).decode())

            if commit_result['success']:
                self.onCommited.emit(True, DBProject().from_database(commit_result['dbproject']), project)
            else:
                self.onCommited.emit(False, None, project)

        except Exception as e:
            print("Exception in RemoteCorpusClient.commit_project(): ", str(e))
            self.onCommited.emit(False, None, project)


    @pyqtSlot(object, object)
    def checkout_project(self, user, project: DBProject):
        try:
            result = json.loads(self.send_message(ServerCommands.Check_Out_Inquiry,
                                                  dict(
                                                      user=user.to_database(True),
                                                      dbproject=project.to_database(True)
                                                  )).decode())
            if result['success']:
                self.onCheckedOut.emit(True, self.to_project_list(result['dbprojects']))
            else:
                self.onCheckedOut.emit(False, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.checkout_project(): ", str(e))
            self.onCheckedOut.emit(False, None)

    @pyqtSlot(object, object)
    def checkin_project(self, user, project: DBProject):
        try:
            result = json.loads(self.send_message(ServerCommands.Check_In_Project,
                                  dict(
                                      user=user.to_database(True),
                                      dbproject=project.to_database(True)
                                  )).decode())
            if result['success']:
                self.onCheckedIn.emit(True,  self.to_project_list(result['dbprojects']))
            else:
                self.onCheckedIn.emit(False, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.checkin_project(): ", str(e))
            self.onCheckedIn.emit(False, None)

    @pyqtSlot(object, object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        try:
            result = json.loads(self.send_message(ServerCommands.Download_Project,
                                                  dict(
                                                      user=user.to_database(True),
                                                      dbproject=project.to_database(True)
                                                  )).decode())

            if result['success']:
                ftp_connection = ftplib.FTP()
                ftp_connection.connect(self.ftp_server_ip, self.ftp_server_port)
                ftp_connection.login(self.ftp_username, self.ftp_password)
                ftp_connection.cwd(os.path.split("/ftp/")[1])

                archive = self.corpora_dir + result['path'] # replace with your file in the directory ('directory_name')
                print("Downloading File: ", archive)
                localfile = open(archive, 'wb')
                ftp_connection.retrbinary('RETR ' + result['path'], localfile.write, 1024)
                ftp_connection.quit()
                localfile.close()

                print("Downloaded Project:", project.project_id, archive)
                if archive is not None:
                    self.onReadyForExtraction.emit(True, project, archive)
                else:
                    self.onReadyForExtraction.emit(False, None, None)
            else:
                self.onReadyForExtraction.emit(False, None, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.download_project(): ", str(e))
            self.onReadyForExtraction.emit(False, None, None)