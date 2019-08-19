"""
This file contains the AudioHandle to read audio data from the movie file using
moviepy.
"""

import numpy as np
from moviepy.editor import *

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.interfaces import TimelineDataset
from core.container.project import VIANProject
from core.container.hdf5_manager import HDF5_FILE_LOCK

class AudioHandler(QObject):
    """
    Handles reading audio data from the movie file.
    Since moviepy locks all files referenced in the environment,
    self.videoclip and self.audioclip are released right after the audio data is extracted.

    After the processing is done, audioProcessed is emitted and self.audio_samples and self.audio_volume
    are set.
    """
    audioProcessed = pyqtSignal(object)

    def __init__(self, resolution = 0.1, callback=None):
        super(AudioHandler, self).__init__()
        self._videoclip = None       #type: VideoFileClip
        self._audioclip = None       #type: AudioClip
        self.resolution = resolution
        self.callback = callback

        self.audio_samples = None   #type: np.ndarray
        self.audio_volume = None    #type: np.ndarray

    @pyqtSlot(object)
    def project_changed(self, project:VIANProject):
        """
        Reads the audio from the projects moviefile, extracts the audio samples
        and stores a complete audio copy (mp3) in the project data structure.

        :param project: the current vian project
        :return:
        """

        # We have to aquire a Lock from the HDF5Manager, since moviepy (or its dependencies)
        # Lock all files references by the process, we have to make sure that the HDF5 manager doesn't
        # try to clean (replace) the HDF5 file during reading the audio samples.

        with HDF5_FILE_LOCK:
            self._read(project.movie_descriptor.movie_path)
            self.audio_samples = self._sample_audio(self.callback)
            self.audio_volume = np.abs(np.mean(self.audio_samples, axis=1))

            project_audio_path = os.path.join(project.data_dir, "audio.mp3")
            self.audioProcessed.emit(
                TimelineDataset("Audio Volume", self.audio_volume, ms_to_idx=(self.resolution * 1000),
                                vis_type=TimelineDataset.VIS_TYPE_AREA))
            if not os.path.isfile(project_audio_path):
                self._audioclip.write_audiofile(os.path.join(project.data_dir, "audio.mp3"))

            self._videoclip.close()

    @pyqtSlot(str)
    def _read(self, path:str):
        self._videoclip = VideoFileClip(path)
        self._audioclip = self._videoclip.audio

    @pyqtSlot(float, object)
    def _sample_audio(self, callback = None):
        vals = []
        for i in range(int(self._audioclip.duration / self.resolution)):
            vals.append(self._audioclip.get_frame(i / (1.0 / self.resolution)))
            if callback is not None and  i % 100 == 0:
                callback(i / int(self._audioclip.duration / self.resolution))
        return np.array(vals)


