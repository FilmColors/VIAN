import os
import librosa
from core.container.project import VIANProject
from moviepy.editor import *

def get_audio_for_project(project:VIANProject):
    p = os.path.join(project.data_dir, "audio.mp3")
    if not os.path.isfile(p):
        _videoclip = VideoFileClip(project.movie_descriptor.movie_path).audio



    y, sr = librosa.load(librosa.ex('nutcracker'), duration=30)
    return y, sr