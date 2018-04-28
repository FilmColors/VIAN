from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
import sip
import json

class CorpusServer(QTcpServer):
    def __init__(self, parent):
        super(CorpusServer, self).__init__(parent)


    def incomingConnection(self, handle: sip.voidptr):
        thread = CorpusServerThread(handle, self)
        thread.finished.connect(thread.deleteLater)


class CorpusServerThread(QThread):
    def __init__(self, socketDescriptor, parent):
        super(CorpusServerThread, self).__init__(parent)
        self.socketDescriptor = socketDescriptor

    def run(self):
        socket = QTcpSocket(self)
        is_connected = socket.setSocketDescriptor(self.socketDescriptor)

        while(is_connected):
            message = socket.readAll()
            print(message)
            dict = json.load(message)
            socket.write(json.dump(dict(message = "Hello World")))

        socket.disconnectFromHost()
        socket.waitForDisconnected()

class  CorpusClientWidget(QWidget):
    def __init__(self, parent):
        super(CorpusClientWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.btn = QPushButton("Send Message" ,self)
        self.lbl = QLabel()
        self.layout().addWidget(self.btn)
        self.layout().addWidget(self.lbl)

        self.socket = QTcpSocket(self)


    def sendMessage(self):
        self.socket.connectToHost()







