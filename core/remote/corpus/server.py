import datetime
import json
import os
import pickle
import socket
import sys

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QApplication, QDialog, QTreeWidget, QTreeWidgetItem, QTableWidget

from core.remote.corpus.corpus import MasterClientData, ProjectData, Corpus
from core.data.containers import MovieDescriptor
CORPUS_Connect = 0
CORPUS_Disconnect = 1
CORPUS_DoesMovieExist = 2
CORPUS_GetMovie = 3
CORPUS_UpdateMovie = 4
COPPUS_PING = 5

def set_style_sheet(app, path):
    style_sheet = open(os.path.abspath(path), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)


def set_attributes(app):
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if sys.platform == "darwin":
        app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)


class CorpusPreferences():
    def __init__(self, port_ID = 5006, backup_Interval = 15, corpus_password = "CorpusPassword"):
        self.port_ID = port_ID
        self.backup_Interval = backup_Interval
        self.corpus_password = corpus_password

    def store(self):
        path = os.path.abspath("../../../user/corpus_pref.json")
        data = dict(
            port_ID=self.port_ID,
            backup_Interval= self.backup_Interval,
            corpus_password = self.corpus_password
        )
        with open(path, "wb") as file:
            json.dump(data, file)

    def load(self):
        path = os.path.abspath("../../../user/corpus_pref.json")
        try:
            with open(path, "rb") as file:
                data = json.load(file)
                self.port_ID = data['port_ID']
                self.backup_Interval = data['backup_Interval']
                self.corpus_password = data['corpus_password']
        except:
            print("No Settings Found")
            self.store()


class CorpusServer(QThread):
    do_connect = pyqtSignal(list)
    do_disconnect = pyqtSignal(list)
    project_exists = pyqtSignal(list)
    update_project = pyqtSignal(list)


    def __init__(self, tcp_ip = '127.0.0.1', port=5006 , password = "CorpusPassword"):
        super(CorpusServer, self).__init__()
        self.TCP_IP = tcp_ip
        self.TCP_PORT = port
        self.BUFFER_SIZE = 1024
        self.active = True
        self.is_connected = False
        self.handle_threads = []
        self.connection_id_counter = 0
        self.password = password

    def run(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.TCP_IP, self.TCP_PORT))
        while self.active:
            self.listen()


    def listen(self):
        self.s.listen(5)
        conn, addr = self.s.accept()
        print("MasterServer:\t New Connection")

        try:
            print("MasterServer:\t New Connection")
            self.is_connected = True
            handler = QServerHandler(conn, self, self.connection_id_counter)
            handler.do_connect.connect(self.on_connect)
            handler.do_disconnect.connect(self.on_disconnect)
            handler.project_exists.connect(self.on_project_exists)
            handler.update_project.connect(self.on_update_project)
            self.handle_threads.append(handler)
            handler.start()
            self.connection_id_counter += 1
            # self.handle_threads.append(handler)
        except IOError as e:
            print(e)

    def on_connect(self,info):
        self.do_connect.emit(info)

    def on_disconnect(self,info):
        self.do_disconnect.emit(info)

    def on_update_project(self,info):
        self.update_project.emit(info)

    def on_project_exists(self,info):
        self.project_exists.emit(info)


class QServerHandler(QThread):
    do_connect = pyqtSignal(list)
    do_disconnect = pyqtSignal(list)
    project_exists = pyqtSignal(list)
    update_project = pyqtSignal(list)

    def __init__(self, conn, server, ID):
        super(QServerHandler, self).__init__()
        self.conn = conn
        self.server = server
        self.is_active = True
        self.ID = ID

    def run(self):
        while (self.is_active):
            try:
                data = self.conn.recv(self.server.BUFFER_SIZE)
                if not data: break
                ret = self.parse_msg(data)
                ret = self.parse_answer(ret)
                print(ret)
                self.conn.send(ret)
            except IOError as e:
                self.conn.close()
                self.is_active = False
                self.server.handle_threads.remove(self)
                break

    def parse_msg(self, msg):
        sep = ';'
        msg_split = msg.split(sep)
        cmd = int(msg_split[0])

        args = msg_split[1:len(msg_split)]
        if cmd == CORPUS_Connect:
            if args[1] == self.server.password:
                args.append(self.ID)
                self.do_connect.emit(args)
                return str(self.ID) + ";" + str(True)
            else:
                print("Wrong Password")
                return str(self.ID) + ";" + str(False)
                self.conn.close()


        elif cmd == CORPUS_Disconnect:
            args.append(self.ID)
            self.do_disconnect.emit(args)
        elif cmd == CORPUS_DoesMovieExist:
            self.project_exists.emit(args)
        elif cmd == CORPUS_UpdateMovie:
            self.update_project.emit(args)


        return "OK"

    def parse_answer(self, answer):
        return str(answer) + "\n"


class MasterWindow(QMainWindow):
    def __init__(self):
        super(MasterWindow, self).__init__()
        path = os.path.abspath("../../../qt_ui/master/master_window.ui")
        uic.loadUi(path, self)

        self.settings = CorpusPreferences()
        self.settings.load()

        self.master_file_path = os.path.abspath("master_file.meext")
        self.server = CorpusServer(port=self.settings.port_ID)
        self.server.project_exists.connect(self.does_project_exists)
        self.server.update_project.connect(self.update_project)
        self.server.do_connect.connect(self.do_connect)
        self.server.do_disconnect.connect(self.do_disconnect)
        self.server.start()

        self.connections = []
        self.connected_users = []
        self.project_list = []
        self.messageLog = []

        self.corpus = Corpus()
        self.tableWidget_connections.setColumnCount(2)
        self.tableWidget_connections.setHorizontalHeaderItem(0, QTableWidgetItem("User ID"))
        self.tableWidget_connections.setHorizontalHeaderItem(1, QTableWidgetItem("User Name"))


        self.actionPreferences.triggered.connect(self.open_preferences)

        self.backup_timer = QTimer(self)
        self.backup_timer.setInterval(self.settings.backup_Interval * 60 * 1000)
        self.backup_timer.timeout.connect(self.on_backup)
        self.backup_timer.start()
        # self.tableWidget_connections = QTableWidget()
        self.show()

    def does_project_exists(self, info):
        movie_path = info[0]
        project_path = info[1]

    def update_project(self, d):
        # args = [str(p.project_ID), p.project_name, p.project_path, p.movie_path,
        #         m.movie_path, m.movie_name, str(m.movie_id), str(m.year), m.source, str(m.duration)]

        desc = MovieDescriptor(None, d[5], d[4], d[6], d[7], d[8], d[9])
        project = ProjectData(d[0], d[1], d[2], d[3], desc)
        self.corpus.update_project(project)
        self.add_to_log("Project Updated")
        self.update_corpus_list()

    def do_connect(self, info):
        client_data = MasterClientData(user_name=str(info[0]), client_id=int(info[2]), project_data=None)
        curr_connection = len(self.connections)
        self.connected_users.append(client_data)
        self.update_user_list()
        self.add_to_log("New Connection: "+ client_data.user_name +"\t" + str(client_data.ID), color="Green")

    def update_user_list(self):

        self.tableWidget_connections.setRowCount(0)
        # self.tableWidget_connections.setItem(0, 0, QTableWidgetItem("User ID"))
        # self.tableWidget_connections.setItem(0, 1, QTableWidgetItem("User Name"))
        self.tableWidget_connections.clearContents()
        for i, user in enumerate(self.connected_users):
            self.tableWidget_connections.setRowCount(self.tableWidget_connections.rowCount() + 1)
            self.tableWidget_connections.setItem(i, 0, QTableWidgetItem(str(user.ID)))
            self.tableWidget_connections.setItem(i, 1, QTableWidgetItem(str(user.user_name)))
            # self.tableWidget_connections.setItem(i, 1, QTableWidgetItem(user.project_data.project_name))
            self.tableWidget_connections.resizeColumnsToContents()
            self.tableWidget_connections.resizeRowsToContents()

    def update_corpus_list(self):
        self.tree_Corpus.clear()

        for m in self.corpus.corpus_movies:
            r = QTreeWidgetItem(0)
            r.setText(0, m.movie_name)
            self.tree_Corpus.addTopLevelItem(r)
            for p in m.projects:
                c = QTreeWidgetItem(0)
                c.setText(0, p.project_name)
                r.addChild(c)

    def do_disconnect(self, info):
        user_ID = info[1]
        for i in self.connected_users:
            if i.ID == user_ID:
                self.connected_users.remove(i)
                self.add_to_log("Connection Closed: " + info[0] +"\t" + str(user_ID), color="Orange")
                self.update_user_list()
                return

    def add_to_log(self, string, color = "gray"):
        time_code = datetime.datetime.now()
        self.messageLog.append([time_code, string, color])

        self.textEdit_Log.clear()

        for i, msg in enumerate(self.messageLog):
            self.textEdit_Log.setTextColor(QColor(msg[2]))
            self.textEdit_Log.append(str(i) + ".  " + msg[1] + "\t" + str(msg[0]))

    def store_master_file(self):
        pass

    def on_backup(self):
        path = os.path.abspath("backup_" + datetime.datetime.now().strftime("%H-%M-%S_%d-%m-%y") + ".pickle")
        self.save(path)
        self.add_to_log("Backup Saved", color="Gray")

    def save(self, path):
        data = dict(
            message_log = self.messageLog,
            project_list = self.project_list
        )
        with open(path, "wb") as file:
            pickle.dump(data, file)

    def load(self, path):
        with open(path, "rb") as file:
            data = pickle.load(file)

        self.messageLog = data['message_Log']
        self.project_list = data['project_list']

    def open_preferences(self):
        preferences = PreferencesWindow(self, self.settings)
        preferences.show()


class PreferencesWindow(QDialog):
    def __init__(self,parent, settings):
        super(PreferencesWindow, self).__init__(parent)
        path = os.path.abspath("../../../qt_ui/master/coprus_preferences.ui")
        uic.loadUi(path, self)

        self.settings = settings

        self.sB_Backup.setValue(self.settings.backup_Interval)
        self.sB_Port.setValue(self.settings.port_ID)
        self.passwordLineEdit.setText(self.settings.corpus_password)

        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.close)



    def on_ok(self):
        self.settings.backup_Interval = self.sB_Backup.value()
        self.settings.port_ID = self.sB_Port.value()
        self.settings.corpus_password = self.passwordLineEdit.text()
        self.parent().backup_timer.setInterval(self.settings.backup_Interval * 60)
        self.close()


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)

if __name__ == '__main__':
    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    app = QApplication(sys.argv)
    main = MasterWindow()
    set_attributes(app)
    set_style_sheet(app, "../../../qt_ui/themes/qt_stylesheet_dark.css")

    sys.exit(app.exec_())


