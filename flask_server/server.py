from PyQt5.QtCore import QThread, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView

from flask import Flask

from core.gui.ewidgetbase import EDockWidget

app = Flask(__name__)

class FlaskServer(QObject):
    def __init__(self, parent):
        super(FlaskServer, self).__init__(parent)
        self.app = app

    @pyqtSlot()
    def run_server(self):
        print("Running Server")
        self.app.run()


class FlaskWebWidget(EDockWidget):
    def __init__(self, main_window):
        super(FlaskWebWidget, self).__init__(main_window, False)
        self.setWindowTitle("WebView Debug")
        self.view = QWebEngineView(self)
        self.setWidget(self.view)


@app.route("/")
def index():
    return "hello world"
