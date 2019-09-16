import time
from threading import Lock
import numpy as np
import librosa as lr
from moviepy.editor import *

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

"""
This Lock has to be used to make sure that VIAN does not attempt to delete 
files since moviepy seems to lock all files currently referenced while having its own file open. 
"""
MOVIEPY_LOCK = Lock()

class AudioHandler(QObject):
    RES_22K = 1.0 / 22

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

    def _write_audio(self, path = "test_audio.mp3"):
        self.audioclip.write_audiofile(path, bitrate="22050")

    @pyqtSlot(float, object)
    def _sample_audio(self, resolution = 0.5, callback = None):
        length = int(self.audioclip.duration / resolution)
        arr = np.zeros(shape=(length, 2), dtype=np.float32)
        for i in range(length):
            arr[i] = self.audioclip.get_frame(i)
            if callback is not None and  i % 100 == 0:
                callback(i / int(self.audioclip.duration / resolution))
        return arr



# handle = AudioHandler()
# p = "C:/Users/gaude/Documents/VIAN/projects/1_1_1_NetflixTrailer_1900_VHS/trailer.mp4"
# p = "E:/Torrent/James Bond Complete Collection (1962-2015) [1080p]/13. For Your Eyes Only (1981) [1080p]/For.Your.Eyes.Only.1981.1080p.BluRay.x264.anoXmous_.mp4"
# handle._read(p)
# # sample = handle._sample_audio(callback = print)
# # print(sample)
#
# handle._write_audio()
t = time.time()
y, sr = lr.load("test_audio.mp3")
print("Loading", time.time() - t)
t = time.time()
print(y.nbytes/1000000)
chroma = lr.feature.chroma_cqt(y=y, sr=sr)
print("Feature", time.time() - t)
t = time.time()
bounds = lr.segment.agglomerative(chroma, 20)
bound_times = lr.frames_to_time(bounds, sr=sr)
print(bound_times)
print("Clustering", time.time() - t)
t = time.time()