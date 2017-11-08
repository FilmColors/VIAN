import os
import sys

from PyQt5 import uic, QtWidgets

from core.remote.ELAN.client.client import elan_client

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024

class ClientControl(QtWidgets.QMainWindow):
    def __init__(self):
        super(ClientControl, self).__init__()
        path = os.path.abspath("../../qt_ui/ClientControl.ui")
        uic.loadUi(path,self)

        self.client = elan_client()
        self.client.connect('127.0.0.1',5005)

        #self.client.send_open_movie("C:/Users/Gaudenz Halter/Desktop216_1_1_LesParapluiesDeCherbourg_1964_DVD.mov")
        self.client.send_open_movie("E:/Video/DowntonAbbey/Downton Abbey S02/Downton Abbey S02E02.mp4")
        self.show()

    def send_pos(self,position):
        self.client.send_position(long(float(position)/50000*self.duration))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    main = ClientControl()


    sys.exit(app.exec_())


