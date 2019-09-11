"""
This file contains the AudioHandle to read audio data from the movie file using
moviepy.
"""
import gc

import numpy as np
from moviepy.editor import *
from typing import List, Tuple
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.interfaces import TimelineDataset
from core.data.log import log_error, log_info, log_warning, log_debug
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
    audioExtracted = pyqtSignal(str)

    def __init__(self, resolution = 0.1, callback=None):
        super(AudioHandler, self).__init__()
        self._videoclip = None       #type: VideoFileClip
        self._audioclip = None       #type: AudioClip
        self.resolution = resolution
        self.callback = callback

        self.audio_samples = None   #type: np.ndarray
        self.audio_volume = None    #type: np.ndarray
        self.project = None

        self.export_audio = False

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

        log_info("AudioHandlerPath:", project.movie_descriptor.get_movie_path())

        self.project = project

        with HDF5_FILE_LOCK:
            self._read(project.movie_descriptor.get_movie_path())
            self.audio_samples = self._sample_audio(self.callback)
            self.audio_volume = np.abs(np.mean(self.audio_samples, axis=1))

            log_info("Size", self.audio_samples.nbytes / 10 ** 6)
            log_info("Size", self.audio_volume.nbytes / 10 ** 6)
            project_audio_path = os.path.join(project.data_dir, "audio.mp3")
            self.audioProcessed.emit(
                TimelineDataset("Audio Volume", self.audio_volume, ms_to_idx=(self.resolution * 1000),
                                vis_type=TimelineDataset.VIS_TYPE_AREA))
            try:
                if not os.path.isfile(project_audio_path) and self.export_audio:
                    self._audioclip.write_audiofile(os.path.join(project.data_dir, "audio.mp3"))
            except Exception as e:
                log_error(e)
            self._videoclip.close()
            self._audioclip.close()

    @pyqtSlot(str)
    def _read(self, path:str):
        """
        Reads a movie into memory
        :param path: Path to the movie file as string
        """
        self._videoclip = VideoFileClip(path)
        self._audioclip = self._videoclip.audio

    @pyqtSlot(float, object)
    def _sample_audio(self, callback = None) -> np.ndarray:
        """
        Samples a audio source of a movie into a numpy array
        :param callback: a function to call for signalling progress
        :return: an array of shape (length, 2) stereo signal, np.ndarray
        """
        length = int(self._audioclip.duration / self.resolution)
        arr = np.zeros(shape=(length, 2), dtype=np.float32)
        for i in range(int(self._audioclip.duration / self.resolution)):
            arr[i] = self._audioclip.get_frame(i / (1.0 / self.resolution))
            if callback is not None and  i % 100 == 0:
                callback("Audio Extraction:\t" + str(round(i / int(self._audioclip.duration / self.resolution)* 100, 2)) + "%")
        return arr


    @pyqtSlot(object, str, object)
    def export_segments(self, segments:List[Tuple[int, int]], directory, callback = None):
        """
        Writes a number of given segments to new movie files
        :param segments: A list of Tuples (t_start_ms, t_end_ms) given in milliseconds.
        :return:
        """
        if self.project is None:
            return

        with HDF5_FILE_LOCK:
            self._read(self.project.movie_descriptor.get_movie_path())
            for i, s in enumerate(segments):
                clip = self._videoclip.subclip(s[0] / 1000, s[1] / 1000)
                name = os.path.join(directory, str(i + 1) + ".mp4")
                clip.write_videofile(name)
                if callback is not None:
                    callback(i / len(segments))
            self._videoclip.close()