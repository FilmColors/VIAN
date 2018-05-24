from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
import os
from PyQt5 import uic
import json
import socket
import threading

from glob import glob

from core.corpus.shared.enums import *
from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.entities import *

from core.data.headless import load_project_headless

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

import dataset as ds


class CorpusServerWindow(QMainWindow):
    def __init__(self):
        super(CorpusServerWindow, self).__init__()
        path = os.path.abspath("qt_ui/CorpusServerWindow.ui")
        uic.loadUi(path, self)

        self.server = CorpusServer(None, '127.0.0.1', 5005)

        self.server_thread = QThread(self)
        self.server.moveToThread(self.server_thread)
        self.server_thread.start()
        self.actionRun.triggered.connect(self.server.listen)
        self.actionLoad_Dataset.triggered.connect(self.on_open)


    def on_open(self):
        try:
            path = QFileDialog.getOpenFileName(self, filter="*.vian_corpus")[0]
            self.server.local_corpus.load(path)
            self.server.ftp_path =self.server.local_corpus.root_dir + "/ftp/"
            if not os.path.isdir( self.server.ftp_path):
                os.mkdir( self.server.ftp_path)

        except Exception as e:
            print(e)

class CorpusServer(QObject):
    def __init__(self, parent, host, port):
        super(CorpusServer, self).__init__(parent)
        self.host = host
        self.port = port

        self.ftp_ip = host
        self.ftp_port = 12345
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        self.active = True

        self.ftp_path = ""
        self.local_corpus = DatasetCorpusDB()

        self.dir_corpus = os.path.expanduser("~") + "/Documents" + "/VIAN/" + "server/"
        if not os.path.isdir(os.path.expanduser("~") + "/Documents" + "/VIAN/"):
            os.mkdir(os.path.expanduser("~") + "/Documents" + "/VIAN/")
        if not os.path.isdir(self.dir_corpus):
            os.mkdir(self.dir_corpus)


    @pyqtSlot()
    def listen(self):
        self.run()

    @pyqtSlot()
    def run(self):
        print("OK RUNNING")
        authorizer = DummyAuthorizer()
        authorizer.add_user("Gaudenz", "Password", self.ftp_path, perm="elradfmw")

        handler = FTPHandler
        handler.authorizer = authorizer

        server = FTPServer((self.ftp_ip, self.ftp_port), handler)
        threading.Thread(target=server.serve_forever).start()
        while self.active:

            try:
                print("Listening...")
                self.sock.listen(5)
                client, address = self.sock.accept()
                client.settimeout(60)
                threading.Thread(target=self.listen_to_client, args=(client, address)).start()
            except Exception as e:
                print(e)


    def listen_to_client(self, client, address):
        size = 1024
        while True:
            try:
                data = client.recv(size)
                print(data)
                if data:
                    # Set the response to echo back the recieved data
                    response = self.parse_message(data)
                    client.send(response)
                else:
                    raise ConnectionError('Client disconnected')
            except Exception as e:
                print(e)
                client.close()
                return False


    def parse_message(self, msg):
        msg = msg.decode()
        msg = msg.split(SPLIT_ITEM)

        task = ServerCommands(int(msg[0]))
        data = json.loads(msg[1])

        response_type = ServerResponses.Failed
        response_data = dict()

        if task == ServerCommands.Connect:
            try:
                in_user = DBContributor().from_database(data['user'])

                response_data = dict(
                    success = True,
                    projects = [p.to_database(True) for p in self.local_corpus.get_projects()],
                    user = self.local_corpus.connect_user(in_user).to_database(True),
                    corpus_name=self.local_corpus.name
                )


            except Exception as e:
                print("Exception in ServerCommands.Connect" + str(e))
                response_data =  dict(
                    success = False,
                    projects = None,
                    user = None,
                    corpus_name=None
                )

        elif task == ServerCommands.Disconnect:
            try:
                in_user = DBContributor().from_database(data['user'])
                response_data = dict(path=self)
            except Exception as e:
                print("Exception in ServerCommands.Disconnect" + str(e))
        # Creates a new remote Project from a local project.
        elif task == ServerCommands.Commit_Inquiry:
            try:
                in_user = DBContributor().from_database(data['user'])
                response_data = dict(success=True, path=self.ftp_path)
            except Exception as e:
                print("Exception in ServerCommands.Commit_Inquiry" + str(e))
                response_data = dict(success=False, path="")

        elif task == ServerCommands.Commit_Finished:
            try:
                archive = data['archive']
                contributor = DBContributor().from_database(data['user'])
                target = os.path.basename(archive).replace(".zip", "")
                shutil.unpack_archive(self.ftp_path + "/" + archive, self.ftp_path + target)
                file = glob(self.ftp_path + target + "/*.eext")[0]
                project = load_project_headless(file)
                project.reset_file_paths(self.ftp_path + target, file)

                success, dbproject = self.local_corpus.commit_project(project, contributor)

                response_data = dict(success=success, path=self.ftp_path, dbproject=dbproject.to_database(True))

            except Exception as e:
                response_data = dict(success=False, path="")
                print("Exception in ServerCommands.Commit_Finished: " + str(e))


        # Removes a remote Project
        elif task == ServerCommands.Remove_Project:
            pass

        # Clones a remote Project to the local machine
        elif task == ServerCommands.Check_Out_Inquiry:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                success, archive = self.local_corpus.checkout_project(project.project_id, user)

                response_data = dict(
                    success=success,
                    dbprojects=[p.to_database(True) for p in self.local_corpus.get_projects()],
                )
            except Exception as e:
                print("Exception in ServerCommands.Check_Out_Inquiry: " + str(e))
                response_data = dict(
                    success=False,
                    projects=None,
                )

        # Unlocks a Remote Project for other Users
        elif task == ServerCommands.Check_In_Project:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                success = self.local_corpus.checkin_project(project.project_id, user)

                response_data = dict(
                        success = success,
                        dbprojects = [p.to_database(True) for p in self.local_corpus.get_projects()],
                    )
            except Exception as e:
                print("Exception in ServerCommands.Check_In_Project: " + str(e))
                response_data = dict(
                    success=False,
                    projects=None,
                )


        elif task == ServerCommands.Download_Project:

            try:
                project = DBProject().from_database(data['dbproject'])
                user = DBContributor().from_database(data['user'])
                archive = self.local_corpus.get_project_path(project)
                download_file = self.ftp_path + os.path.split(archive)[1]
                print("Download File: ", download_file)
                copy2(archive, download_file)
                response_data = dict(
                    success=True,
                    path = os.path.split(archive)[1],
                )
            except Exception as e:
                print("Exception in ServerCommands.Download_Project: " + str(e))
                response_data = dict(
                    success=False,
                    path = ""
                )


        elif task == ServerCommands.Get_CheckOut_State:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                db_project = self.local_corpus.get_project(project.project_id)

                if db_project is None:
                    response_data = dict(
                        success=False,
                        dbproject=None,
                    )
                else:
                    response_data = dict(
                        success=True,
                        dbproject=db_project.to_database(True),
                    )
            except Exception as e:
                print("Exception in ServerCommands.Get_CheckOut_State: " + str(e))
                response_data = dict(
                    success=False,
                    dbproject=None,
                )

        result = json.dumps(response_data).encode()
        return result

    # def on_commit_asked(self, project: DBProject):
    #     """
    #     Returns true if the project is not checked out by another user,
    #     :param project:
    #     :return: [True, [Files Needed]]
    #     """
    #
    # def on_commit_finished(self):
    #     """
    #     After the Client has finished copying all data,
    #     it informs the server to have finished
    #     :return:
    #     """
    #
    # def on_check_out_inquiry(self):
    #     """
    #     returns true if the project may be checked out
    #     :return:
    #     """
    #
    # def on_check_in(self):
    #     pass
    #
    # def on_get_project(self):
    #     """
    #
    #     :return:
    #     """
    #
    # def on_checkout_state_asked(self):
    #     pass










