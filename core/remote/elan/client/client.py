"""

Commands:           Arguments
0 = Play        
1 = Pause       
2 = Stop           
3 = SetPosition 
4 = OpenMovie
5 = SetVolume

"""

import socket

from core.remote.server import TCPCommands

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024
MESSAGE = "Hello World"



class elan_client():
    def __init__(self):
        self.ip = '127.0.0.1'
        self.port = 5005
        self.buffer_size = 1024


    def connect(self, ip, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((ip, port))


    def send_play(self):
        msg = self.create_message(TCPCommands.PLAY)
        self.s.send(msg)
        ret = self.s.recv(BUFFER_SIZE)

    def send_pause(self):
        msg = self.create_message(TCPCommands.PAUSE)
        self.s.send(msg)
        ret = self.s.recv(BUFFER_SIZE)

    def send_position(self,position):
        msg = self.create_message(TCPCommands.SET_MEDIA_TIME, [str(position)])
        self.s.send(msg)
        ret = self.s.recv(BUFFER_SIZE)


    def send_open_movie(self,abs_path):
        msg = self.create_message(TCPCommands.OPEN_MOVIE, [str(abs_path)])
        self.s.send(msg)
        ret = self.s.recv(BUFFER_SIZE)

    def get_duration(self):
        msg = self.create_message(TCPCommands.GET_MEDIA_DURATION)
        self.s.send(msg)
        ret = self.s.recv(BUFFER_SIZE)
        return int(ret)

    def create_message(self,command_id, args = []):
        sep = ';'
        raw = [str(command_id.value)] + args
        return sep.join(raw)




