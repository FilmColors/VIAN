"""
This file contains the AudioHandle to read audio data from the movie file using
moviepy.
"""

import sys
import os
import librosa
import numpy as np
from core.misc.ffmpeg_executor import ffmpeg_convert
from moviepy.editor import *
from typing import List, Tuple
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.interfaces import TimelineDataset
from core.data.log import log_error, log_info, log_warning, log_debug
from core.container.project import VIANProject
from core.container.hdf5_manager import HDF5_FILE_LOCK
from scipy.signal import savgol_filter


class AudioHandler(QObject):
    """
    Handles reading audio data from the movie file.
    Since moviepy locks all files referenced in the environment,
    self.videoclip and self.audioclip are released right after the audio data is extracted.

    After the processing is done, audioProcessed is emitted and self.audio_samples and self.audio_volume
    are set.
    """
    audioExtractingStarted = pyqtSignal()
    audioExtractingProgress = pyqtSignal(float)
    audioExtractingEnded = pyqtSignal()
    audioProcessed = pyqtSignal(object)
    audioExtracted = pyqtSignal(str)

    def __init__(self, resolution = 0.1, callback=None):
        super(AudioHandler, self).__init__()
        self.resolution = resolution
        self.callback = callback

        self.audio_samples = None   #type: np.ndarray
        self.audio_volume = None    #type: np.ndarray

        self.project = None
        self.export_audio = True

    @pyqtSlot(object)
    def project_changed(self, project: VIANProject):
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
        if self.project is None:
            self.audioExtractingEnded.emit()

    def on_extraction_progress(self, flt):
        print("Progress",flt)
        self.audioExtractingProgress.emit(flt)

    @pyqtSlot()
    def extract(self):
        self.audioExtractingStarted.emit()

        project_audio_path = os.path.join(self.project.data_dir, "audio.mp3")
        if not os.path.isfile(project_audio_path):
            print("Extracting Audio from Movie")
            ffmpeg_convert(input = self.project.movie_descriptor.get_movie_path(),
                           output=project_audio_path,
                           callback=self.on_extraction_progress)

        print("Storing Audio in HDF5")
        y, sr = librosa.load(project_audio_path)
        self.project.hdf5_manager.dump_audio(y)
        print("Audio Ready")
        self.audioExtractingEnded.emit()

    @pyqtSlot(str)
    def _read(self, path: str):
        """
        Reads a movie into memory
        :param path: Path to the movie file as string
        """
        self._videoclip = VideoFileClip(path)
        self._audioclip = self._videoclip.audio

    @pyqtSlot(float, object)
    def _sample_audio(self, callback=None) -> np.ndarray:
        """
        Samples a audio source of a movie into a numpy array
        :param callback: a function to call for signalling progress
        :return: an array of shape (length, 2) stereo signal, np.ndarray
        """
        try:
            length = int(self._audioclip.duration / self.resolution)
            arr = np.zeros(shape=(length, 2), dtype=np.float32)
            for i in range(int(self._audioclip.duration / self.resolution)):
                arr[i] = self._audioclip.get_frame(i / (1.0 / self.resolution))
                if callback is not None and i % 100 == 0:
                    callback("Audio Extraction:\t" + str(
                        round(i / int(self._audioclip.duration / self.resolution) * 100, 2)) + "%")
        except Exception as e:
            print(e)
            return None
        return arr

    @pyqtSlot(object, str, object)
    def export_segments(self, segments: List[Tuple[int, int, str]], directory, callback=None):
        """
        Writes a number of given segments to new movie files
        :param segments: A list of Tuples (t_start_ms, t_end_ms) given in milliseconds.
        :return:
        """
        if self.project is None:
            return

        with HDF5_FILE_LOCK:
            bitrate = 3.0

            self._read(self.project.movie_descriptor.get_movie_path())
            for i, s in enumerate(segments):
                clip = self._videoclip.subclip(s[0] / 1000, s[1] / 1000)
                name = os.path.join(directory, s[2] + ".mp4")
                if sys.platform == "darwin":
                    clip.write_videofile(name,
                                         codec='libx264',
                                         audio_codec='aac',
                                         bitrate=str(bitrate * 10 ** 6))
                else:
                    clip.write_videofile(name,
                                         codec="libx264",
                                         bitrate=str(bitrate * 10 ** 6))
                clip.close()
                if callback is not None:
                    callback(i / len(segments))
            self._videoclip.close()