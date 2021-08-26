from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5 import uic
from functools import partial
import os

from vian.core.data.log import log_info, log_debug

from vian.core.gui.perspectives import *
import threading

class StatusBar(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusBar, self).__init__(main_window)

        self.main_window = main_window
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.stage_selector = StageSelector(self, main_window)
        self.layout.addWidget(self.stage_selector)
        self.stage_selector.hide()

        self.layout.addItem(QSpacerItem(100, 10))

        self.label_selection = QtWidgets.QLabel(self)
        self.label_selection.setText("Selection: ")
        self.label_selection.setStyleSheet("QLabel{background: transparent;}")

        self.label_selection_length = QtWidgets.QLabel("0 Items", self)
        self.label_selection_length.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.label_selection)
        self.layout.addWidget(self.label_selection_length)
        self.layout.addItem(QSpacerItem(20,10))

        self.show()

    def closeEvent(self, QCloseEvent):
        self.main_window.elan_status = None
        super(StatusBar, self).closeEvent(QCloseEvent)

    def set_selection(self, selection):
        self.label_selection_length.setText(str(len(selection)) + " Items")


class OutputLine(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(OutputLine, self).__init__(main_window)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.main_window = main_window

        self.text_line = QtWidgets.QLabel(self)
        self.text_line.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.text_line)
        self.message_log = []

        self.text_time = QtCore.QTimer(self)
        self.text_time.setInterval(5000)
        self.text_time.timeout.connect(self.on_timeout)
        self.setMinimumWidth(100)

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
            if len(self.message_queue) > 10:
                self.text_time.setInterval(10)
            else:
                self.text_time.setInterval(5000)

            curr_msg = self.message_queue[0]
            self.message_queue.remove(curr_msg)

            color = curr_msg[1]
            msg = curr_msg [0]

            self.text_line.setText(str(msg))
            if color != "":
                self.setStyleSheet("QLabel{color : " + color + ";}")

            self.message_log.append(curr_msg)
            self.text_time.start()
            if self.log_wnd is not None:
                self.log_wnd.update_log()
        else:
            self.text_line.setText("")


class StatusVideoSource(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusVideoSource, self).__init__(main_window)
        self.main_window = main_window
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        lbl = QtWidgets.QLabel("Video Source: ")
        lbl.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(lbl)
        self.lbl_source = QtWidgets.QLabel("VLC")
        self.lbl_source.setFixedWidth(100)
        self.lbl_source.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.lbl_source)
        self.setStyleSheet("QWiget{background: transparent;}")

    @pyqtSlot(str)
    def on_source_changed(self, source):
        if source == "VLC":
            self.lbl_source.setText("VLC")
            self.lbl_source.setStyleSheet("QLabel{color:Orange; background: transparent;}")
        else:
            self.lbl_source.setText("OpenCV")
            self.lbl_source.setStyleSheet("QLabel{color:Green; background: transparent;}")

    def mousePressEvent(self, a0: QMouseEvent):
        menu = QMenu(self)
        current = self.main_window.settings.OPENCV_PER_FRAME
        a_vlc = menu.addAction("\tAlways VLC")
        a_vlc.setCheckable(True)
        a_opencv = menu.addAction("\tAlways OpenCV")
        a_opencv.setCheckable(True)
        a_scale_depending = menu.addAction("\tTimeline Scale Depending")
        a_scale_depending.setCheckable(True)

        if current == 0:
            a_vlc.setChecked(True)
        elif current == 1:
            a_opencv.setChecked(True)
        else:
            a_scale_depending.setChecked(True)

        a_vlc.triggered.connect(partial(self.set_source, 0))
        a_opencv.triggered.connect(partial(self.set_source, 1))
        a_scale_depending.triggered.connect(partial(self.set_source, 2))

        menu.popup(self.mapToGlobal(a0.pos())- QtCore.QPoint(0, 100))

    def set_source(self, idx):
        self.main_window.settings.OPENCV_PER_FRAME = idx

        # Apply the change to the drawing widget, while this should work
        # we are only going to try.
        try:
            if idx == 0:
                self.main_window.onOpenCVFrameVisibilityChanged.emit(False)

            elif idx == 1 and not self.main_window.player.is_playing():
                self.main_window.onOpenCVFrameVisibilityChanged.emit(True)

            elif (idx == 2 and not self.main_window.player.is_playing()
                  and self.main_window.timeline.timeline.scale < self.main_window.timeline.timeline.opencv_frame_scale_threshold):
                self.main_window.onOpenCVFrameVisibilityChanged.emit(True)
            else:
                self.main_window.onOpenCVFrameVisibilityChanged.emit(False)
        except:
            pass


class StatusProgressBar(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusProgressBar, self).__init__(main_window)

        self.main_window = main_window
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setStyleSheet("QProgressBar{background: transparent;}")
        self.layout.addWidget(self.progress_bar)

        self.hide()

    def set_progress(self, float):
        if self.isVisible() is False:
            self.show()

        if float == 0.0:
            self.hide()

        self.progress_bar.setValue(float * 100)

    def on_finished(self):
        self.progress_bar.setValue(0)
        self.hide()

    def mouseDoubleClickEvent(self, a0: QMouseEvent):
        self.main_window.create_concurrent_task_viewer()


class MessageLogWindow(QMainWindow):
    def __init__(self, parent):
        super(MessageLogWindow, self).__init__(parent)
        self.message_bar = parent
        self.view = QTextEdit(self)
        self.widget = QWidget(self)
        self.widget.setLayout(QVBoxLayout(self.widget))
        self.widget.layout().addWidget(self.view)
        self.input_line = QLineEdit(self)
        self.widget.layout().addWidget(self.input_line)
        self.input_line.returnPressed.connect(self.parse_command)

        self.setWindowTitle("Message Log")
        self.setCentralWidget(self.widget)
        self.main_window = self.message_bar.main_window
        self.resize(600,400)

    def update_log(self):
        self.view.clear()
        self.messages = self.message_bar.message_log
        header = self.main_window.get_version_as_string()
        # for msg in self.messages:
        #     text += "<font color=\"" + msg[1] + "\">"
        #     text += msg[0] + "\n"
        # self.view.setPlainText(text)
        self.view.append(header)
        for i, msg in enumerate(self.messages):
            self.view.setTextColor(QColor(msg[1]))
            self.view.append(str(i) + ".  " + str(msg[0]))

    def parse_command(self):
        cmd = self.input_line.text()
        try:

            if cmd == "list_containers":
                self.main_window.project.print_object_list()

            elif cmd == "list_threads":
                log_info(threading.enumerate())

            elif cmd == "help":
                log_info("list_containers -- Listing all Container Objects of the Project")

            else:
                # cmd = cmd.replace("print", "self.main_window.print_message")
                cmd = cmd.replace("project", "self.main_window.project")

                eval(cmd)

        except Exception as e:
            log_debug (e)

        self.input_line.clear()


class StageSelector(QWidget):
    def __init__(self, parent, main_window):
        super(StageSelector, self).__init__(parent)
        path = os.path.abspath("qt_ui/StageSelector.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.setStyleSheet("QPushButton{background: transparent;} QWidget:focus{border: 0px solid #383838;}")

        self.btn_Annotation.hide()
        self.buttons = [
            (self.btn_Setup, Perspective.ExperimentSetup),
            (self.btn_Segmentation, Perspective.Segmentation),
            # (self.btn_Annotation, Perspective.SVGAnnotation),
            (self.btn_Classification, Perspective.Classification),
            (self.btn_Query, Perspective.Query),
            (self.btn_WebApp, Perspective.WebApp)
        ]

        self.btn_Segmentation.clicked.connect(partial(self.set_stage, Perspective.Segmentation))
        # self.btn_Annotation.clicked.connect(partial(self.set_stage, Perspective.SVGAnnotation))
        self.btn_Setup.clicked.connect(partial(self.set_stage, Perspective.ExperimentSetup))
        self.btn_Classification.clicked.connect(partial(self.set_stage, Perspective.Classification))
        self.btn_Query.clicked.connect(partial(self.set_stage, Perspective.Query))
        self.btn_WebApp.clicked.connect(partial(self.set_stage, Perspective.WebApp, True))

    def set_stage(self, idx:Perspective, dispatch = True):
        new_perspective = None
        for i, (btn, persp) in enumerate(self.buttons):
            if persp == idx:
                new_perspective = persp
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        if dispatch and new_perspective is not None:
            self.main_window.switch_perspective(new_perspective)
