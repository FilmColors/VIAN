import numpy as np
from moviepy.editor import *

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from core.data.interfaces import TimelineDataset

class AudioHandler(QObject):
    audioProcessed = pyqtSignal(object)

    def __init__(self, resolution = 0.1, callback=None):
        super(AudioHandler, self).__init__()
        self.videoclip = None
        self.audioclip = None       #type: AudioClip
        self.resolution = resolution
        self.callback = callback

        self.audio_samples = None
        self.audio_volume = None

    @pyqtSlot(object)
    def project_changed(self, project):
        self._read(project.movie_descriptor.movie_path)
        self.audio_samples = self._sample_audio(self.callback)
        self.audio_volume = np.abs(np.mean(self.audio_samples, axis=1))

        self.audioProcessed.emit(TimelineDataset("Audio Volume", self.audio_volume, ms_to_idx=(self.resolution * 1000)))

    @pyqtSlot(str)
    def _read(self, path):
        self.videoclip = VideoFileClip(path)
        self.audioclip = self.videoclip.audio

    @pyqtSlot(float, object)
    def _sample_audio(self, callback = None):
        vals = []
        for i in range(int(self.audioclip.duration / self.resolution)):
            vals.append(self.audioclip.get_frame(i / (1.0 / self.resolution)))
            if callback is not None and  i % 100 == 0:
                callback(i / int(self.audioclip.duration / self.resolution))
        return np.array(vals)
        # for r in self.audioclip.duration:



# handle = AudioHandler()
# p = "C:/Users/gaude/Documents/VIAN/projects/1_1_1_NetflixTrailer_1900_VHS/trailer.mp4"
# p = "E:/Torrent/James Bond Complete Collection (1962-2015) [1080p]/13. For Your Eyes Only (1981) [1080p]/For.Your.Eyes.Only.1981.1080p.BluRay.x264.anoXmous_.mp4"
# handle.read(p)
# sample = handle.sample_audio(callback = print)



