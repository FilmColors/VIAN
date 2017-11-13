import sys
import time

import cv2
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QFrame, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal

from core.data.computation import parse_file_path
from core.data.interfaces import IProjectChangeNotify
from core.vlc import vlc
import os


class MacPlayerContainer(QtWidgets.QMainWindow):
    def __init__(self, parent, player):
        super(MacPlayerContainer, self).__init__()
        self.player = player
        self.main_window = parent
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.player.videoframe)
        self.player.videoframe.setParent(self)
        self.setLayout(self.layout)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.show()

    def synchronize(self):
        target = self.main_window.player_placeholder
        location = target.mapToGlobal(QtCore.QPoint(0, 0))
        self.move(location)
        self.resize(target.size())
        self.player.videoframe.resize(target.size())


class VideoPlayer(QtWidgets.QFrame, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    #SIGNALS
    movieOpened = pyqtSignal()
    started = pyqtSignal()
    stopped = pyqtSignal()
    timeChanged = pyqtSignal(long)

    def __init__(self, main_window):
        super(VideoPlayer, self).__init__()
        self.main_window = main_window
        self.media_descriptor = None
        # These Variables are initialized to be sure they exist in Classes inheriting from VideoPlayer
        self.movie_path = ""
        self.offset = 0
        self.start_time = 0
        self.stop_time = 0
        self.duration = 100
        self.orig_aspect_ratio = 0
        self.aspect_ratio = 0
        self.movie_size = (720,480)
        self.millis_per_sample = 0
        self.fps = 24
        self.playing = False
        self.volume = 0
        self.mute = False
        self.videoframe = QFrame(self)

    # *** EXTENSION METHODS *** #
    def get_frame(self):
        print NotImplementedError("Method <get_frame> not implemented")

    def init_ui(self):
        print NotImplementedError("Method <init_ui> not implemented")

    def get_size(self):
        print NotImplementedError("Method <get_size> not implemented")

    def set_initial_values(self):
        print NotImplementedError("Method <set_initial_values> not implemented")

    def play_pause(self):
        print NotImplementedError("Method <play_pause> not implemented")
    # *** ELAN INTERFACE METHODS *** #
    def open_movie(self, path):
        print NotImplementedError("Method <open_movie> not implemented")

    def play(self):
        print NotImplementedError("Method <play> not implemented")

    def pause(self):
        print NotImplementedError("Method <pause> not implemented")

    def stop(self):
        print NotImplementedError("Method <stop> not implemented")

    def is_playing(self):
        """
        :return: bool
        """
        print NotImplementedError("Method <is_playing> not implemented")

    def play_interval(self, start_ms, stop_ms):
        print NotImplementedError("Method <play_interval> not implemented")

    def set_offset(self):
        """
        
        :return: Long
        """
        print NotImplementedError("Method <set_offset> not implemented")

    def get_offset(self):
        print NotImplementedError("Method <get_offset> not implemented")

    def set_stop_time(self, time):
        print NotImplementedError("Method <set_stop_time> not implemented")

    def next_frame(self):
        print NotImplementedError("Method <next_frame> not implemented")

    def previous_frame(self):
        print NotImplementedError("Method <previous_frame> not implemented")

    def set_frame_steps_to_frame_begin(self, bool):
        print NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented")

    def set_media_time(self, time):
        print NotImplementedError("Method <set_media_time> not implemented")

    def get_media_time(self):
        print NotImplementedError("Method <get_media_time> not implemented")

    def set_rate(self, rate):
        print NotImplementedError("Method <set_rate> not implemented")

    def get_rate(self):
        print NotImplementedError("Method <get_rate> not implemented")

    def is_frame_rate_auto_detected(self):
        print NotImplementedError("Method <is_frame_rate_auto_detected> not implemented")

    def get_media_duration(self):
        print NotImplementedError("Method <get_media_duration> not implemented")

    def set_volume(self, volume):
        print NotImplementedError("Method <set_volume> not implemented")

    def get_volume(self):
        print NotImplementedError("Method <get_volume> not implemented")

    def set_sub_volume(self, volume):
        print NotImplementedError("Method <set_sub_volume> not implemented")

    def get_sub_volume(self):
        print NotImplementedError("Method <get_sub_colume> not implemented")

    def set_mute(self, mute):
        print NotImplementedError("Method <set_mute> not implemented")

    def get_mute(self):
        print NotImplementedError("Method <get_mute> not implemented")

    def get_source_width(self):
        print NotImplementedError("Method <get_source_width> not implemented")

    def get_source_height(self):
        print NotImplementedError("Method <get_source_height> not implemented")

    def get_aspect_ratio(self):
        print NotImplementedError("Method <get_aspect_ratio> not implemented")

    def set_aspect_ratio(self, ratio):
        print NotImplementedError("Method <set_aspect_ratio> not implemented")

    def get_miliseconds_per_sample(self):
        print NotImplementedError("Method <get_miliseconds_per_sample> not implemented")

    def set_miliseconds_per_sample(self, ms):
        print NotImplementedError("Method <set_miliseconds_per_sample> not implemented")

    def on_loaded(self, project):
        pass

    def on_changed(self, project, item):
        pass


class Player_VLC(VideoPlayer):
    def __init__(self, main_window):
        super(Player_VLC, self).__init__(main_window)
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()
        self.media = None
        self.init_ui()


        self.pause_timer = QtCore.QTimer()
        self.pause_timer.setInterval(1000)
        self.pause_timer.setSingleShot(True)
        self.pause_timer.timeout.connect(self.pause)

    # *** EXTENSION METHODS *** #

    def get_frame(self):
        fps = self.media_player.get_fps()
        pos = float(self.get_media_time()) / 1000 * fps
        vid = cv2.VideoCapture(self.movie_path)
        vid.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = vid.read()

        return frame

    def init_ui(self):

        # In this widget, the video will be drawn
        # self.videoframe = QtWidgets.QFrame()

        if sys.platform == "darwin":  # for MacOS
            self.mac_frame = QtWidgets.QFrame()
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0, self)

        else:
            self.videoframe = QtWidgets.QFrame()

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this

        if sys.platform.startswith('linux'):  # for Linux using the X Server
            self.media_player.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":  # for Windows
            self.media_player.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin":  # for MacOS
            self.media_player.set_nsobject(int(self.mac_frame.winId()))
            self.videoframe.setCocoaView(self.media_player.get_nsobject())

            self.videoframe.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.videoframe.setAttribute(Qt.WA_NativeWindow, True)
            # self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)


            self.setWindowFlags(Qt.ForeignWindow)
        self.videoframe.setParent(self)
        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)
        self.videoframe.setEnabled(False)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.setLayout(self.vboxlayout)

    def get_size(self):
        return self.media_player.video_get_size()

    def set_initial_values(self):
        self.offset = 0
        self.start_time = 0
        self.stop_time = self.media.get_duration()
        self.duration = self.stop_time
        self.orig_aspect_ratio = self.media_player.video_get_aspect_ratio()
        self.aspect_ratio = self.orig_aspect_ratio
        self.movie_size = self.media_player.video_get_size()
        self.millis_per_sample = 40
        self.volume = 50
        fps = self.media_player.get_fps()
        print "FPS:", self.media_player.get_fps()
        if fps != 0:
            self.fps = fps

    def get_subtitles(self):
        subs = self.media_player.video_get_spu_description()
        return subs

    def set_subtitle(self, index):
        self.media_player.video_set_spu(index)


    # *** ELAN INTERFACE METHODS *** #

    def open_movie(self, path, from_server = False):
        # create the media
        print "Opening Movie:", path

        if sys.version < '3':
            filename = unicode(path)

        self.movie_path = filename
        self.media = self.vlc_instance.media_new(self.movie_path)
        # put the media in the media player
        self.media_player.set_media(self.media)

        # parse the metadata of the file
        self.media.parse()

        # Running the movie, to ensure the initial values can be read by the VLC framework
        self.play()

        # Wait for a little
        # time.sleep(0.5)
        self.set_initial_values()

        # Setting the movie to Paused

        # Set the position to the beginning


        # We need to wait a little, otherwise, VLC will automatically start playing
        # time.sleep(1)
        # self.pause()

        if from_server:
            self.new_movie_loaded = True


        self.set_media_time(0)
        self.pause_timer.start()

        self.movieOpened.emit()

        if self.main_window.is_darwin:
            self.mac_frame.update()


    def play_pause(self):
        if not self.is_playing():
            self.play()
        else:
            self.pause()
        return self.is_playing()

    def play(self):
        self.media_player.play()
        self.playing = True
        self.started.emit()

    def pause(self):
        self.media_player.set_pause(-1)
        self.playing = False
        self.stopped.emit()

    def stop(self):
        self.media_player.stop()
        self.playing = False
        #self.update_timer.stop()

    def is_playing(self):
        """
        :return: bool
        """
        return self.playing

    def play_interval(self, start_ms, stop_ms):
        print NotImplementedError("Method <play_interval> not implemented")

    def set_offset(self):
        """

        :return: Long
        """
        print NotImplementedError("Method <set_offset> not implemented")

    def get_offset(self):
        print NotImplementedError("Method <get_offset> not implemented")

    def set_stop_time(self, time):
        print NotImplementedError("Method <set_stop_time> not implemented")

    def next_frame(self):
        self.media_player.next_frame()

    def previous_frame(self):
        pass

    def set_frame_steps_to_frame_begin(self, bool):
        print NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented")

    def set_media_time(self, time):
        self.media_player.set_time(long(time))
        self.timeChanged.emit(time)
        self.last_set_frame = time

    def get_media_time(self):
        return self.media_player.get_time()

    def set_rate(self, rate):
        self.media_player.set_rate(float(rate))

    def get_rate(self):
        return self.media_player.get_rate()

    def is_frame_rate_auto_detected(self):
        if self.get_rate() is not 0.0:
            return True
        return False

    def get_media_duration(self):
        if self.duration is 100:
            self.duration = self.media.get_duration()
            return self.duration
        else:
            return self.duration

    def set_volume(self, volume):
        self.media_player.audio_set_volume(volume)

    def get_volume(self):
        return self.media_player.audio_get_volume()

    def set_sub_volume(self, volume):
        return self.media_player.audio_set_volume(volume)

    def get_sub_volume(self):
        return self.get_volume()

    def set_mute(self, mute):
        self.media_player.audio_set_mute(bool(mute))

    def get_mute(self):
        return self.media_player.audio_get_mute()

    def get_source_width(self):
        return self.media_player.video_get_size()[0]

    def get_source_height(self):
        return self.media_player.video_get_size()[1]

    def get_aspect_ratio(self):
        t = self.media_player.video_get_aspect_ratio()
        if t is None:
            return float(4)/3
        return t

    def set_aspect_ratio(self, ratio):
        print NotImplementedError("Method <set_aspect_ratio> not implemented")

    def get_miliseconds_per_sample(self):
        return 0

    def set_miliseconds_per_sample(self, ms):
        print NotImplementedError("Method <set_miliseconds_per_sample> not implemented")

    def get_fps(self):
        return self.media_player.get_fps()

    def on_loaded(self, project):
        path = project.movie_descriptor.movie_path
        self.media_descriptor = project.movie_descriptor

        if path is "" or not os.path.isfile(path):
            path = QtWidgets.QFileDialog.getOpenFileName(self)[0]
            project.movie_descriptor.movie_path = path

        self.open_movie(path)
        self.media_descriptor.set_duration(self.get_media_duration())

    def on_changed(self, project, item):
        pass

    def get_frame_pos_by_time(self, time):
        fps = self.get_fps()
        pos = float(time) / 1000 * fps
        return int(pos)

    def on_selected(self,sender, selected):
        pass



