import os

import numpy as np
from PyQt5 import QtCore, uic

from core.data.computation import ms_to_string
from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import IProjectChangeNotify


class PlayerControls(EDockWidget):
    def __init__(self,main_window):
        super(PlayerControls, self).__init__(main_window)
        path = os.path.abspath("qt_ui/PlayerControls.ui")
        uic.loadUi(path,self)

        self.main_window = main_window
        self.is_clicked = False
        self.is_connected = False
        self.slider_is_hidden = False

        self.btn_HideSlider.clicked.connect(self.on_hide_slider)
        self.btn_play.clicked.connect(self.on_play)
        self.sl_volume.valueChanged.connect(self.on_volume_change)
        self.sl_position.valueChanged.connect(self.on_position_change)

        self.sl_position.sliderPressed.connect(self.on_mouse_press)
        self.sl_position.sliderReleased.connect(self.on_mouse_release)

        self.comboBox_Subs.currentIndexChanged.connect(self.on_subs_changed)


        # Slider Update Timer

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)
        #
        self.main_window.player.movieOpened.connect(self.update_movie)
        self.main_window.player.started.connect(self.timer.start)
        self.main_window.player.stopped.connect(self.timer.stop)
        #self.main_window.player.timeChanged.connect(self.update_ui)

        self.initial_values_timer = QtCore.QTimer(self)
        self.initial_values_timer.setSingleShot(True)
        self.initial_values_timer.setInterval(1000)
        self.initial_values_timer.timeout.connect(self.update_movie)
        self.on_hide_slider()

        self.main_window.player.movieOpened.connect(self.initial_values_timer.start)
        self.show()


    def on_hide_slider(self):
        if self.slider_is_hidden:
            self.slidercontainer.show()
            self.slider_is_hidden = False
            self.btn_HideSlider.setText("Hide Slider")
        else:
            self.slidercontainer.hide()
            self.slider_is_hidden = True
            self.btn_HideSlider.setText("Show Slider")

    def on_position_change(self, position):
        if not self.is_connected:
            if self.is_clicked:
                self.main_window.player.set_media_time(long(float(position) / 10000.0 * self.main_window.player.duration))

    def on_volume_change(self, Volume):
        if not self.is_connected:
            self.main_window.player.set_volume(Volume)

    def on_mouse_press(self):
        self.is_clicked = True

    def on_mouse_release(self):
        self.is_clicked = False

    def on_play(self):
        isPaused = self.main_window.player.play_pause()
        if isPaused:
            self.btn_play.setText(" Play ")
        else:
            self.btn_play.setText("Pause ")
        self.main_window.player.set_subtitle(1)

    def update_ui(self):
        self.lbl_Rate.setText(str(round(self.main_window.player.get_rate(),1)))
        self.is_connected = self.main_window.server.is_connected
        if self.main_window.player.media is not None:
            t = self.main_window.timeline.timeline.curr_movie_time
            d = np.clip(self.main_window.player.duration, 1, None)
            vlc_position = float(t)/d
            vlc_volume = float(self.main_window.player.get_volume())
            self.sl_position.setValue(vlc_position * 10000)
            self.lbl_position_time.setText(ms_to_string(t))
            self.lbl_position_frame.setText(str(int(float(t) / 1000 * 30)))
            self.sl_volume.setValue(vlc_volume)

    def closeEvent(self, QCloseEvent):
        self.main_window.player_controls = None
        super(PlayerControls, self).closeEvent(QCloseEvent)

    def update_movie(self):
        self.subs = self.main_window.player.get_subtitles()
        self.comboBox_Subs.clear()
        if len(self.subs) == 0:
            self.comboBox_Subs.addItem("No Subtitles")
        else:
            if len(self.subs) > 0:
                for s in self.subs:
                    self.comboBox_Subs.addItem(s[1])

    def on_subs_changed(self, index):
        if len(self.subs) > 0:
            self.main_window.player.set_subtitle(self.subs[index - 1][0])


