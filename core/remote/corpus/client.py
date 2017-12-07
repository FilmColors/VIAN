import time
import socket
from core.remote.corpus.corpus import CorpusMovie, ProjectData
from core.data.containers import MovieDescriptor
from random import randint
from .server import *
TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024


class CorpusClient(QThread):
    def __init__(self, user_name):
        super(CorpusClient, self).__init__()
        self.ip = '127.0.0.1'
        self.port = 6006
        self.buffer_size = 1024
        self.s = None
        self.ID = -1
        self.is_connected = False
        self.is_active = True
        self.user_name = user_name
        self.password = "CP"

    def run(self):
        while(self.is_active):

            self.ping(self.user_name)
            self.sleep(1)
        # ping_timer = QTimer()
        # ping_timer.setInterval(1000)
        # ping_timer.timeout.connect(self.ping(self.user_name))
        # ping_timer.start()

    def connect(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.ip, self.port))
            self.is_connected = True
        except:
            self.is_connected = False


    def send_connect(self, user_name):
        self.connect()
        if self.is_connected:
            msg = self.create_message(CORPUS_Connect, [user_name, self.password])
            self.s.send(msg.encode())
            ret = self.s.recv(BUFFER_SIZE)
            ret = ret.replace("\n", "").split(";")

            if ret[1] == "True":
                self.ID = int(ret[0])
            else:
                print("CORPUS Connection Failed")
                self.is_connected = False
                self.is_active = False


    def send_disconnect(self, user_name):
        if self.is_connected:
            msg = self.create_message(CORPUS_Disconnect, [user_name])
            self.s.send(msg)
            ret = self.s.recv(BUFFER_SIZE)

    def send_project_exists(self, project_path):
        if self.is_connected:
            msg = self.create_message(CORPUS_DoesMovieExist, [project_path])
            self.s.send(msg)
            ret = self.s.recv(BUFFER_SIZE)
            return ret
        else:
            return False

    def send_update_project(self, p):
        if self.is_connected:
            m = p.movie_descriptor
            args = [str(p.project_ID), p.project_name, p.project_path, p.movie_path,
                    m.movie_path, m.movie_name, str(m.movie_id), str(m.year), m.source, str(m.duration)]


            msg = self.create_message(CORPUS_UpdateMovie, args)
            self.s.send(msg)
            ret = self.s.recv(BUFFER_SIZE)

    def ping(self, UserName):
        if self.is_connected:
            try:
                msg = self.create_message(COPPUS_PING)
                self.s.send(msg)
            except:
                self.is_connected = False
        else:
            self.send_connect(UserName)

    def create_message(self,command_id, args = []):
        sep = ';'
        raw = [str(command_id)] + args
        return sep.join(raw)

if __name__ == '__main__':
    c = CorpusClient()
    c.connect()
    c.send_connect("Barbara")
    time.sleep(2)
    for i in range(2):
        c.send_update_project(ProjectData(0, "Some Project", "hello/movie.eext", "hello/movie.mp4",MovieDescriptor(None, "HelloMovie", "hello/movie.mp4")))
        time.sleep(2)
    c.send_disconnect("Barbara")
