import sys
import time
import requests
from functools import partial
import cv2
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QFrame, QFileDialog, QMessageBox, QMenu
# from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
# from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from core.gui.ewidgetbase import EDockWidget
from core.data.computation import parse_file_path
from core.data.interfaces import IProjectChangeNotify
from core.data.log import log_error, log_info, log_debug

import vlc
# from core.vlc.v3_0_3 import vlc
import os


class PlayerDockWidget(EDockWidget):
    onSpacialFrequencyChanged = pyqtSignal(bool, str)
    onFaceRecognitionChanged = pyqtSignal(bool)

    def __init__(self, main_window):
        super(PlayerDockWidget, self).__init__(main_window=main_window, limit_size=False)
        self.setWindowTitle("Player")
        self.video_player = None
        self.setMinimumWidth(100)
        self.setMinimumHeight(100)
        self.vis_menu = self.inner.menuBar().addMenu("Visualization")
        self.spatial_frequency_menu = QMenu("Spatial Frequency")
        self.vis_menu.addMenu(self.spatial_frequency_menu)

        self.a_spacial_frequency = self.spatial_frequency_menu.addAction("Edge Mean")
        self.a_spacial_frequency.setCheckable(True)
        self.a_spacial_frequency.triggered.connect(partial(self.on_spacial_frequency_changed, "edge-mean"))

        self.a_spacial_frequency_col_var = self.spatial_frequency_menu.addAction("Color Variance")
        self.a_spacial_frequency_col_var.setCheckable(True)
        self.a_spacial_frequency_col_var.triggered.connect(partial(self.on_spacial_frequency_changed, "color-var"))

        self.a_spacial_frequency_hue_var = self.spatial_frequency_menu.addAction("Hue Variance")
        self.a_spacial_frequency_hue_var.setCheckable(True)
        self.a_spacial_frequency_hue_var.triggered.connect(partial(self.on_spacial_frequency_changed, "hue-var"))

        self.a_spacial_frequency_lum_var = self.spatial_frequency_menu.addAction("Luminance Variance")
        self.a_spacial_frequency_lum_var.setCheckable(True)
        self.a_spacial_frequency_lum_var.triggered.connect(partial(self.on_spacial_frequency_changed, "luminance-var"))

        self.setFeatures(EDockWidget.NoDockWidgetFeatures | EDockWidget.DockWidgetClosable)



    def on_spacial_frequency_changed(self, method):
        state = self.sender().isChecked()
        self.a_spacial_frequency.setChecked(False)
        self.a_spacial_frequency_col_var.setChecked(False)
        self.a_spacial_frequency_lum_var.setChecked(False)
        self.a_spacial_frequency_hue_var.setChecked(False)
        self.sender().setChecked(True)
        self.onSpacialFrequencyChanged.emit(state, method)


    def on_face_rec_changed(self):
        self.onFaceRecognitionChanged.emit(self.a_face_rec.isChecked())

    def set_player(self, video_player):
        self.setWidget(video_player)
        self.video_player = video_player
        self.video_player.show()

    def resizeEvent(self, *args, **kwargs):
        super(PlayerDockWidget, self).resizeEvent(*args, **kwargs)
        self.main_window.drawing_overlay.update()

    # def dockLocationChanged(self, Qt_DockWidgetArea):
    #     super(PlayerDockWidget, self).dockLocationChanged(Qt_DockWidgetArea)
    #     self.main_window.drawing_overlay.raise_()


class VideoPlayer(QtWidgets.QFrame, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    #SIGNALS
    movieOpened = pyqtSignal()
    started = pyqtSignal()
    stopped = pyqtSignal()
    timeChanged = pyqtSignal(int)

    def __init__(self, main_window):
        super(VideoPlayer, self).__init__(main_window)
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

        self.use_user_fps = False
        self.user_fps = 29.9999999


        self.videoframe = QFrame(self)

    # *** EXTENSION METHODS *** #
    def get_frame(self):
        log_debug(NotImplementedError("Method <get_frame> not implemented"))

    def init_ui(self):
        log_debug(NotImplementedError("Method <init_ui> not implemented"))

    def get_size(self):
        log_debug(NotImplementedError("Method <get_size> not implemented"))

    def set_initial_values(self):
        log_debug(NotImplementedError("Method <set_initial_values> not implemented"))

    def play_pause(self):
        log_debug(NotImplementedError("Method <play_pause> not implemented"))
    # *** ELAN INTERFACE METHODS *** #

    def open_movie(self, path):
        log_debug(NotImplementedError("Method <open_movie> not implemented"))

    def play(self):
        log_debug(NotImplementedError("Method <play> not implemented"))

    def pause(self):
        log_debug(NotImplementedError("Method <pause> not implemented"))

    def stop(self):
        log_debug(NotImplementedError("Method <stop> not implemented"))

    def is_playing(self):
        """
        :return: bool
        """
        log_debug(NotImplementedError("Method <is_playing> not implemented"))

    def play_interval(self, start_ms, stop_ms):
        log_debug(NotImplementedError("Method <play_interval> not implemented"))

    def set_offset(self):
        """
        
        :return: Long
        """
        log_debug(NotImplementedError("Method <set_offset> not implemented"))

    def get_offset(self):
        log_debug(NotImplementedError("Method <get_offset> not implemented"))

    def set_stop_time(self, time):
        log_debug(NotImplementedError("Method <set_stop_time> not implemented"))

    def next_frame(self):
        log_debug(NotImplementedError("Method <next_frame> not implemented"))

    def previous_frame(self):
        log_debug(NotImplementedError("Method <previous_frame> not implemented"))

    def set_frame_steps_to_frame_begin(self, bool):
        log_debug(NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented"))

    def set_media_time(self, time):
        log_debug(NotImplementedError("Method <set_media_time> not implemented"))

    def get_media_time(self):
        log_debug(NotImplementedError("Method <get_media_time> not implemented"))

    def set_rate(self, rate):
        log_debug(NotImplementedError("Method <set_rate> not implemented"))

    def get_rate(self):
        log_debug(NotImplementedError("Method <get_rate> not implemented"))

    def is_frame_rate_auto_detected(self):
        log_debug(NotImplementedError("Method <is_frame_rate_auto_detected> not implemented"))

    def get_media_duration(self):
        log_debug(NotImplementedError("Method <get_media_duration> not implemented"))

    def set_volume(self, volume):
        log_debug(NotImplementedError("Method <set_volume> not implemented"))

    def get_volume(self):
        log_debug(NotImplementedError("Method <get_volume> not implemented"))

    def set_sub_volume(self, volume):
        log_debug(NotImplementedError("Method <set_sub_volume> not implemented"))

    def get_sub_volume(self):
        log_debug(NotImplementedError("Method <get_sub_colume> not implemented"))

    def set_mute(self, mute):
        log_debug(NotImplementedError("Method <set_mute> not implemented"))

    def get_mute(self):
        log_debug(NotImplementedError("Method <get_mute> not implemented"))

    def get_source_width(self):
        log_debug(NotImplementedError("Method <get_source_width> not implemented"))

    def get_source_height(self):
        log_debug(NotImplementedError("Method <get_source_height> not implemented"))

    def get_aspect_ratio(self):
        log_debug(NotImplementedError("Method <get_aspect_ratio> not implemented"))

    def set_aspect_ratio(self, ratio):
        log_debug(NotImplementedError("Method <set_aspect_ratio> not implemented"))

    def get_miliseconds_per_sample(self):
        log_debug(NotImplementedError("Method <get_miliseconds_per_sample> not implemented"))

    def set_miliseconds_per_sample(self, ms):
        log_debug(NotImplementedError("Method <set_miliseconds_per_sample> not implemented"))

    def on_loaded(self, project):
        pass

    def on_changed(self, project, item):
        pass


class Player_VLC(VideoPlayer):
    def __init__(self, main_window):
        super(Player_VLC, self).__init__(main_window)

        self.vlc_arguments = "--no-keyboard-events --no-mouse-events --no-embedded-video --repeat --quiet"
        self.instance = vlc.Instance(self.vlc_arguments)

        self.media = None

        # Create an empty vlc media player
        self.media_player = self.instance.media_player_new()

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.vboxlayout)

        if sys.platform == "darwin":  # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0, None)
        else:
            self.videoframe = QtWidgets.QFrame()


        # self.videoframe.setParent(self)
        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)
        # self.videoframe.setEnabled(True)

        self.vboxlayout.addWidget(self.videoframe)

        self.init_ui()

        # self.pause_timer = QtCore.QTimer()
        # self.pause_timer.setInterval(1000)
        # self.pause_timer.setSingleShot(True)
        # self.pause_timer.timeout.connect(self.pause)

    # *** EXTENSION METHODS *** #
    def init_vlc(self):
        pass
        # self.vlc_instance = vlc.Instance(self.vlc_arguments)
        # if self.media_player is None:
        #     self.media_player = vlc.MediaPlayer()

        # self.init_ui()

    def release_player(self):
        if self.media_player is not None:
            self.stop()
            self.videoframe.hide()

    def get_frame(self):
        # fps = self.media_player.get_fps()
        pos = float(self.get_media_time()) / 1000 * self.fps
        vid = cv2.VideoCapture(self.movie_path)
        vid.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = vid.read()

        return frame

    def init_ui(self):

        # In this widget, the video will be drawn
        # self.videoframe = QtWidgets.QFrame()

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this
        if sys.platform.startswith('linux'):  # for Linux using the X Server
            self.media_player.set_xwindow(int(self.videoframe.winId()))
        elif sys.platform == "win32":  # for Windows
            self.media_player.set_hwnd(int(self.videoframe.winId()))
        elif sys.platform == "darwin":  # for MacOS
            self.media_player.set_nsobject(int(self.videoframe.winId()))
            # self.videoframe.setCocoaView(self.media_player.get_nsobject())

            self.videoframe.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            # self.videoframe.setAttribute(Qt.WA_NativeWindow, True)
            # self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)


            # self.setWindowFlags(Qt.ForeignWindow)

    def get_size(self):
        if self.media_player is not None:
            return self.media_player.video_get_size()
        else:
            return [1,1]

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

        capture = cv2.VideoCapture(self.movie_path)
        self.fps = capture.get(cv2.CAP_PROP_FPS)
        self.movie_size = (capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.main_window.project.movie_descriptor.fps = self.fps
        self.media_descriptor.set_duration(self.duration)
        self.user_fps = self.fps

    def get_subtitles(self):
        subs = self.media_player.video_get_spu_description()
        return subs

    def set_subtitle(self, index):
        self.media_player.video_set_spu(index)

    def open_movie(self, path, from_server = False):
        # create the media

        # if self.vlc_instance is None:
        self.init_vlc()

        if sys.version < '3':
            filename = str(path)
        else:
            filename = path

        self.movie_path = filename
        self.media = self.instance.media_new(self.movie_path)

        # put the media in the media player
        self.media_player.set_media(self.media)

        # parse the metadata of the file
        self.media.parse()

        self.videoframe.show()

        # Running the movie, to ensure the initial values can be read by the VLC framework
        self.play()

        # Wait for a little
        # time.sleep(0.5)
        self.set_initial_values()
        if from_server:
            self.new_movie_loaded = True

        self.set_media_time(0)
        # self.pause_timer.start()

        log_info("Opened Movie", self.movie_path)
        self.movieOpened.emit()

    def play_pause(self):
        if not self.is_playing():
            self.play()
        else:
            self.pause()
        return self.is_playing()

    def play(self):
        if self.media_player is None:
            return
        self.media_player.play()
        self.playing = True
        self.started.emit()

        # We want to check for the fps, since VLC sometimes gets it wrong at the beginning.
        fps = self.media_player.get_fps()
        if fps > 0:
            self.fps = fps

    def pause(self):
        if self.media_player is None:
            return
        self.media_player.set_pause(-1)
        self.playing = False
        self.stopped.emit()

    def stop(self):
        if self.media_player is None:
            return
        # self.media_player.stop()
        self.media_player.set_pause(-1)
        self.playing = False
        if self.media is not None:
            self.media.release()
            self.media = None
        #self.update_timer.stop()

    def is_playing(self):
        """
        :return: bool
        """
        return self.playing

    def play_interval(self, start_ms, stop_ms):
        log_debug(NotImplementedError("Method <play_interval> not implemented"))

    def set_offset(self):
        """

        :return: Long
        """
        log_debug(NotImplementedError("Method <set_offset> not implemented"))

    def get_offset(self):
        log_debug(NotImplementedError("Method <get_offset> not implemented"))

    def set_stop_time(self, time):
        log_debug(NotImplementedError("Method <set_stop_time> not implemented"))

    def next_frame(self):
        if self.media_player is None:
            return
        self.media_player.next_frame()

    def previous_frame(self):
        pass

    def set_frame_steps_to_frame_begin(self, bool):
        log_debug(NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented"))

    def set_media_time(self, time):
        if time > self.duration - 1:
            time = self.duration - 1
        if self.media_player is None:
            return

        self.media_player.set_time(int(time))
        self.timeChanged.emit(time)

        self.last_set_frame = time

    def get_media_time(self):
        if self.media_player is None:
            return 0

        return self.media_player.get_time()

    def set_rate(self, rate):
        if self.media_player is None:
            return 1.0
        self.media_player.set_rate(float(rate))

    def get_rate(self):
        if self.media_player is None:
            return 1.0
        return self.media_player.get_rate()

    def is_frame_rate_auto_detected(self):
        if self.get_rate() != 0.0:
            return True
        return False

    def get_media_duration(self):
        if self.media_player is None:
            return 0
        return self.media.get_duration()

    def set_volume(self, volume):
        if self.media_player is None:
            return
        self.media_player.audio_set_volume(volume)

    def get_volume(self):
        if self.media_player is None:
            return 0
        return self.media_player.audio_get_volume()

    def set_sub_volume(self, volume):
        if self.media_player is None:
            return
        return self.media_player.audio_set_volume(volume)

    def get_sub_volume(self):
        return self.get_volume()

    def set_mute(self, mute):
        if self.media_player is None:
            return
        self.media_player.audio_set_mute(bool(mute))

    def get_mute(self):
        if self.media_player is None:
            return 0
        return self.media_player.audio_get_mute()

    def get_source_width(self):
        if self.media_player is None:
            return 0
        return self.media_player.video_get_size()[0]

    def get_source_height(self):
        if self.media_player is None:
            return 0
        return self.media_player.video_get_size()[1]

    def get_aspect_ratio(self):
        if self.media_player is None:
            return 4/3

        t = self.media_player.video_get_aspect_ratio()
        if t is None:
            return float(4)/3
        return t

    def set_aspect_ratio(self, ratio):
        log_debug(NotImplementedError("Method <set_aspect_ratio> not implemented"))

    def get_miliseconds_per_sample(self):
        return 0

    def set_miliseconds_per_sample(self, ms):
        log_debug(NotImplementedError("Method <set_miliseconds_per_sample> not implemented"))

    def get_fps(self):
        if self.use_user_fps:
            return self.user_fps
        else:
            return self.fps

    def on_loaded(self, project):
        path = project.movie_descriptor.get_movie_path()
        self.media_descriptor = project.movie_descriptor

        if os.path.isfile(path):
            self.open_movie(path)
        else:
            raise FileNotFoundError("No Movie Selected")

    def on_changed(self, project, item):
        pass

    def get_frame_pos_by_time(self, time):
        fps = self.get_fps()
        # pos = round(round(float(time) / 1000, 0) * fps, 0)
        pos = round(float(time) * fps / 1000, 0)
        return int(pos)

    def frame_step(self, backward = False):
        if backward:
            self.set_media_time(self.media_player.get_time() - (1000 / self.fps))
        else:
            self.set_media_time(self.media_player.get_time() + (1000 / self.fps))

    def on_closed(self):
        self.release_player()


    def on_selected(self,sender, selected):
        pass

#endregion
