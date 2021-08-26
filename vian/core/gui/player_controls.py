import os

import numpy as np
from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QComboBox, QSpinBox, QLayout

from core.data.log import log_error, log_info
from core.data.computation import ms_to_string
from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import ITimeStepDepending


class PlayerControls(EDockWidget, ITimeStepDepending):
    def __init__(self,main_window):
        super(PlayerControls, self).__init__(main_window, height=100)
        path = os.path.abspath("qt_ui/PlayerControls.ui")
        uic.loadUi(path,self)

        self.main_window = main_window
        self.is_clicked = False
        self.is_connected = False
        self.slider_is_hidden = False
        self.fast_forward = True

        self.duration = 0

        self.btn_HideSlider.clicked.connect(self.on_hide_slider)
        self.btn_play.clicked.connect(self.on_play)
        self.btn_ToStart.clicked.connect(self.on_to_start)
        self.btn_FastBackwards.clicked.connect(self.on_fast_backward)
        self.btn_FastForward.clicked.connect(self.on_fast_forward)
        self.btn_ToEnd.clicked.connect(self.on_to_end)

        self.sl_volume.valueChanged.connect(self.on_volume_change)
        self.sl_position.valueChanged.connect(self.on_position_change)

        self.sl_position.sliderPressed.connect(self.on_mouse_press)
        self.sl_position.sliderReleased.connect(self.on_mouse_release)

        self.comboBox_Subs.currentIndexChanged.connect(self.on_subs_changed)

        self.sp_fps.valueChanged.connect(self.on_fps_changed)
        self.cB_fps_Mode.currentIndexChanged.connect(self.on_fps_changed)


        self.main_window.player.movieOpened.connect(self.update_movie)
        self.main_window.player.started.connect(self.on_start)
        self.main_window.player.stopped.connect(self.on_stopped)
        self.main_window.onTimeStep.connect(self.on_timestep_update)

        self.initial_values_timer = QtCore.QTimer(self)
        self.initial_values_timer.setSingleShot(True)
        self.initial_values_timer.setInterval(1000)
        self.initial_values_timer.timeout.connect(self.update_movie)

        self.on_hide_slider()
        self.subs = []

        self.fast_step_timer = QtCore.QTimer()
        self.fast_step_timer.setInterval(200)
        self.fast_step_timer.timeout.connect(self.on_fast_step)

        self.update()

        self.main_window.player.movieOpened.connect(self.initial_values_timer.start)
        self.show()

    @QtCore.pyqtSlot(int)
    def on_timestep_update(self, time):
        if not self.is_clicked:
            d = np.clip(self.main_window.player.duration, 1, None)
            vlc_position = float(time) / d
            self.sl_position.setValue(vlc_position * 10000)

        self.lbl_position_time.setText(ms_to_string(time))
        self.lbl_position_frame.setText(str(int(float(time) / 1000 * self.main_window.player.get_fps())))

    def on_to_start(self):
        self.main_window.player.set_media_time(0)

    def on_to_end(self):
        self.main_window.player.set_media_time(self.main_window.player.duration - 1)

    def on_start(self):
        self.fast_step_timer.stop()
        self.btn_play.setChecked(True)

    def on_stopped(self):
        self.btn_play.setChecked(False)

    def on_fast_step(self):
        if self.fast_forward:
            self.main_window.player.set_media_time(np.clip(self.main_window.player.get_media_time() + 10000,0,self.main_window.player.duration))
        else:
            self.main_window.player.set_media_time(np.clip(self.main_window.player.get_media_time() - 10000,0,self.main_window.player.duration))

    def on_fast_forward(self):
        if self.btn_FastForward.isChecked():
           self.fast_forward = True
           self.main_window.player.pause()
           self.fast_step_timer.start()
        else:
            self.fast_step_timer.stop()

    def on_fast_backward(self):
        if self.btn_FastBackwards.isChecked():
            self.fast_forward = False
            self.main_window.player.pause()
            self.fast_step_timer.start()
        else:
            self.fast_step_timer.stop()

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
                self.main_window.player.set_media_time(int(float(position) / 10000.0 * self.main_window.player.duration))

    def on_volume_change(self, Volume):
        if not self.is_connected:
            self.main_window.player.set_volume(Volume)

    def on_mouse_press(self):
        self.is_clicked = True

    def on_mouse_release(self):
        self.is_clicked = False

    def on_play(self):
        self.btn_FastBackwards.setChecked(False)
        self.btn_FastForward.setChecked(False)
        self.fast_step_timer.stop()

        isPaused = self.main_window.player.play_pause()
        self.main_window.player.set_subtitle(1)

    def on_fps_changed(self):
        # self.cB_fps_Mode = QComboBox()
        if self.cB_fps_Mode.currentIndex() == 0:
            self.main_window.player.use_user_fps = False
        else:
            self.main_window.player.use_user_fps = True
            self.main_window.player.user_fps = self.sp_fps.value()

    def update_rate(self):
        self.lbl_Rate.setText(str(round(self.main_window.player.get_rate(), 1)))

    def setState(self, state):
        for c in self.controlsContainer.children():
            if not isinstance(c, QLayout):
                c.setEnabled(state)

    def update_movie(self):
        self.setState(True)

        self.subs = self.main_window.player.get_subtitles()
        self.comboBox_Subs.clear()

        if len(self.subs) == 0:
            self.comboBox_Subs.addItem("No Subtitles")
        else:
            if len(self.subs) > 0:
                for s in self.subs:
                    self.comboBox_Subs.addItem(str(s[1]))

    def on_subs_changed(self, index):
        try:
            if len(self.subs) > 0:
                self.main_window.player.set_subtitle(self.subs[index][0])
        except Exception as e:
            log_error("PlayerControls.on_subs_changed(): Could not set Subtitles:", e)


