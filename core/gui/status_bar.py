from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QTextBrowser, QTextEdit
from PyQt5.QtGui import QColor
class StatusBar(QtWidgets.QWidget):
    def __init__(self,main_window,server):
        super(StatusBar, self).__init__(main_window)

        self.main_window = main_window
        self.server = server
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Preferred)

        self.label_server = QtWidgets.QLabel(self)
        self.label_server.setText("ELAN: ")
        self.lbl_connection_status = QtWidgets.QLabel(self)
        self.layout.addWidget(self.label_server)
        self.layout.addWidget(self.lbl_connection_status)

        self.label_corpus = QtWidgets.QLabel(self)
        self.label_corpus.setText("Corpus: ")
        self.lbl_corpus_status = QtWidgets.QLabel(self)
        self.layout.addWidget(self.label_corpus)
        self.layout.addWidget(self.lbl_corpus_status)


        self.update_timer = QtCore.QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.check_server_info)
        self.update_timer.start()
        self.check_server_info()
        # self.label_server.setFixedWidth(130)
        # self.lbl_connection_status.setFixedWidth(110)
        self.label_server.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.show()

    def closeEvent(self, QCloseEvent):
        self.main_window.elan_status = None
        super(StatusBar, self).closeEvent(QCloseEvent)

    def check_server_info(self):
        if self.server.is_connected == True:
            self.lbl_connection_status.setText("Online")
            self.lbl_connection_status.setStyleSheet("QLabel {color : green; }")
        else:
            self.lbl_connection_status.setText("Offline")
            self.lbl_connection_status.setStyleSheet("QLabel {color : red; }")

        if self.main_window.corpus_client.is_connected == True:
            self.lbl_corpus_status.setText("Online")
            self.lbl_corpus_status.setStyleSheet("QLabel {color : green; }")
        else:
            self.lbl_corpus_status.setText("Offline")
            self.lbl_corpus_status.setStyleSheet("QLabel {color : red; }")

class OutputLine(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(OutputLine, self).__init__(main_window)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.text_line = QtWidgets.QLabel(self)
        self.layout.addWidget(self.text_line)
        self.message_log = []

        self.text_time = QtCore.QTimer(self)
        self.text_time.setInterval(2000)
        self.text_time.timeout.connect(self.on_timeout)
        self.setMinimumWidth(300)
        # self.setFixedWidth(400)
        self.text_line.setMargin(0)
        self.message_queue = []
        self.log_wnd = None
        self.print_message("Ready")


    def print_message(self, msg = "", color = "white"):

        self.message_queue.append([msg, color])
        if self.text_time.remainingTime() < 0:
            self.on_timeout()

    def mouseDoubleClickEvent(self, QMouseEvent):
        log_wnd = MessageLogWindow(self)
        log_wnd.update_log()
        log_wnd.show()
        self.log_wnd = log_wnd



    def on_timeout(self):
        self.text_time.stop()
        if len(self.message_queue) > 0:
            curr_msg = self.message_queue[0]
            self.message_queue.remove(curr_msg)

            color = curr_msg[1]
            msg = curr_msg [0]

            self.text_line.setText(msg)
            if color is not "":
                self.setStyleSheet("QLabel{color : " + color + ";}")

            self.message_log.append(curr_msg)
            self.text_time.start()
            if self.log_wnd is not None:
                self.log_wnd.update_log()
        else:
            self.text_line.setText("")


class StatusProgressBar(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusProgressBar, self).__init__(main_window)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.layout.addWidget(self.progress_bar)

        self.hide()


    def set_progress(self, float):
        if self.isVisible() is False:
            self.show()
        self.progress_bar.setValue(float * 100)

    def on_finished(self):
        self.progress_bar.setValue(0)
        self.hide()

class MessageLogWindow(QMainWindow):
    def __init__(self, parent):
        super(MessageLogWindow, self).__init__(parent)
        self.message_bar = parent
        self.view = QTextEdit(self)
        self.setWindowTitle("Message Log")
        self.setCentralWidget(self.view)
        self.resize(600,400)

    def update_log(self):
        self.view.clear()
        self.messages = self.message_bar.message_log
        header = "Visual Movie Annotation (VIMA)" \
               "\n##############################" \
                 "\n###########OutputLog##########\n\n\n"
        # for msg in self.messages:
        #     text += "<font color=\"" + msg[1] + "\">"
        #     text += msg[0] + "\n"
        # self.view.setPlainText(text)
        self.view.append(header)
        for i, msg in enumerate(self.messages):
            self.view.setTextColor(QColor(msg[1]))
            self.view.append(str(i) + ".  " + msg[0])




