from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sip
import os
from PyQt5 import uic
import json
import socket
import threading

from core.corpus.shared.enums import *
from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.entities import *

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


class CorpusServer(QObject):
    def __init__(self, parent, host, port):
        super(CorpusServer, self).__init__(parent)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        self.active = True

        self.db = DatasetCorpusDB()

    @pyqtSlot()
    def listen(self):
        self.run()

    @pyqtSlot()
    def run(self):
        print("OK RUNNING")
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
        print (msg)
        msg = msg.decode()
        msg = msg.split(SPLIT_ITEM)

        task = ServerCommands(int(msg[0]))
        data = msg[1]

        response_type = ServerResponses.Failed
        response_data = dict()

        if task == ServerCommands.Connect:
            pass

        elif task == ServerCommands.Disconnect:
            pass

        # Creates a new remote Project from a local project.
        elif task == ServerCommands.Add_Project:
            pass

        # Removes a remote Project
        elif task == ServerCommands.Remove_Project:
            pass

        # Clones a remote Project to the local machine
        elif task == ServerCommands.Pull_Project:
            pass

        # Updates a remote Project from a local Project
        elif task == ServerCommands.Push_Project:
            pass

        elif task == ServerCommands.Get_Project_List:
            pass

        elif task == ServerCommands.Checkout_Project:
            pass

        result = (str(response_type.value) + SPLIT_ITEM + json.dumps(response_data)).encode()
        return result

    def on_commit_asked(self, project: DBProject):
        """
        Returns true if the project is not checked out by another user, 
        :param project: 
        :return: [True, [Files Needed]]
        """

    def on_commit_finished(self):
        """
        After the Client has finished copying all data, 
        it informs the server to have finished
        :return: 
        """

    def on_check_out_inquiry(self):
        """
        returns true if the project may be checked out
        :return: 
        """

    def on_get_project(self):
        """
        
        :return: 
        """








