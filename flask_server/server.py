from PyQt5.QtCore import QThread, QObject, pyqtSlot, pyqtSignal
from flask import Flask

app = Flask(__name__)

class FlaskServer(QObject):
    def __init__(self, parent):
        super(FlaskServer, self).__init__(parent)
        self.app = app

    @pyqtSlot()
    def run_server(self):
        print("Running Server")
        self.app.run()


@app.route("/")
def index():
    return "hello world"
