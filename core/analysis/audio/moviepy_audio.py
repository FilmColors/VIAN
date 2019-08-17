import numpy as np
from moviepy.editor import *

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


class AudioHandler(QObject):

    def __init__(self, resolution = 0.5):
        super(AudioHandler, self).__init__()
        self.videoclip = None
        self.audioclip = None       #type: AudioClip
        self.audio_volume = None    #type: np.ndarray

    def set_movie_path(self, path):
        self._read(path)
        self._sample_audio(self.resolution, self.callback)

    @pyqtSlot(str)
    def _read(self, path):
        self.videoclip = VideoFileClip(path)
        self.audioclip = self.videoclip.audio

    @pyqtSlot(float, object)
    def _sample_audio(self, resolution = 0.5, callback = None):
        vals = []
        for i in range(int(self.audioclip.duration / resolution)):
            vals.append(self.audioclip.get_frame(i))
            if callback is not None and  i % 100 == 0:
                callback(i / int(self.audioclip.duration / resolution))
        return np.array(vals)
        # for r in self.audioclip.duration:



handle = AudioHandler()
p = "C:/Users/gaude/Documents/VIAN/projects/1_1_1_NetflixTrailer_1900_VHS/trailer.mp4"
p = "E:/Torrent/James Bond Complete Collection (1962-2015) [1080p]/13. For Your Eyes Only (1981) [1080p]/For.Your.Eyes.Only.1981.1080p.BluRay.x264.anoXmous_.mp4"
handle.read(p)
sample = handle.sample_audio(callback = print)



