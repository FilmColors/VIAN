import os

import cv2
from core.data.computation import ms_to_string, ms_to_frames
from core.data.enums import MOVIE_DESCRIPTOR

from .container_interfaces import IProjectContainer, ISelectable, IHasName, ITimeRange, \
    AutomatedTextSource, IClassifiable

class MediaDescriptor():
    """
    TODO: BaseClass for MovieDescriptor and future media types
    """
    pass

class MovieDescriptor(IProjectContainer, ISelectable, IHasName, ITimeRange, AutomatedTextSource, IClassifiable):
    """
    :var movie_name: The Name of the Movie
    :var movie_path: The Path of the Movie
    :var is_relative: If movie_path is relative or not
    :var movie_id: The Movie ID tuple (ID, )
    :var year: The Production Year of this Movie
    :var source: The SourceType Enum of this movie {DVD, VHS, FILM}
    :var duration: Duration of the Movie in MS
    :var notes: Additinoal notes added in the Inspector
    :var fps: The float FPS

    """
    def __init__(self, project, movie_name="No Movie Name", movie_path="", movie_id="0_0_0", year=1800, source="",
                 duration=100, fps = 30, unique_id = -1):
        IProjectContainer.__init__(self, unique_id=unique_id)
        IClassifiable.__init__(self)
        self.set_project(project)
        self.movie_name = movie_name
        self.movie_path = movie_path
        self.movie_id = movie_id
        self.year = year
        self.source = source
        self.duration = duration
        self.notes = ""
        self.fps = fps
        # self.is_relative = False
        self.meta_data = dict()
        self.letterbox_rect = None

    def set_letterbox_rect(self, rect):
        self.letterbox_rect = rect

    def get_letterbox_rect(self):
        return self.letterbox_rect

    def serialize(self):
        data = dict(
            movie_name=self.movie_name,
            unique_id=self.unique_id,
            movie_path=self.movie_path,
            movie_id=self.movie_id,
            year=self.year,
            source=self.source,
            duration=self.duration,
            notes=self.notes,
            # is_relative = self.is_relative,
            meta_data = self.meta_data,
            letterbox_rect = self.letterbox_rect
        )

        return data

    def set_duration(self, duration):
        self.duration = duration
        self.dispatch_on_changed(item=self)

    def deserialize(self, serialization):
        self.project.remove_from_id_list(self)

        for key, value in list(serialization.items()):
            try:
                setattr(self, key, value)
            except:
                continue

        self.set_project(self.project)
        return self

    def get_type(self):
        return MOVIE_DESCRIPTOR

    def get_name(self):
        return self.movie_name

    def set_name(self, name):
        self.movie_name = name
        self.project.undo_manager.to_undo((self.set_name, [name]),
                                          (self.set_name, [self.movie_name]))
        self.dispatch_on_changed(item=self)

    def get_start(self):
        return 0

    def get_end(self):
        cap = cv2.VideoCapture(self.movie_path)
        return cap.get(cv2.CAP_PROP_FRAME_COUNT)

    def get_source_properties(self):
        return ["Current Time", "Current Frame", "Movie Name", "Movie Path", "Movie ID", "Year", "Source", "Duration", "Notes"]

    def get_movie_path(self):
        # if self.is_relative:
        #     abs_path = os.path.normpath(self.project.folder + "/" + self.movie_path)
        #     if os.path.isfile(abs_path):
        #         return abs_path
        #     elif os.path.isfile(self.movie_path):
        #         self.is_relative = False
        #         return self.movie_path
        #     else:
        #         return ""
        # else:
        return os.path.normpath(self.movie_path)

    def set_movie_path(self, path):
        """
        Sets the movie path of this project.
        If the movie is within the Projects directory it makes it relative, else it makes it absolut
        :param path:
        :return:
        """
        # if self.project.folder is not None and os.path.normpath(self.project.folder) in os.path.normpath(path):
        #     common = os.path.commonpath([self.project.path, path])
        #     self.movie_path = path.replace(common, "/")
        #     self.is_relative = True
        # else:
        self.movie_path = os.path.normpath(path)
        # self.is_relative = False
        # print("MoviePath set", self.movie_path, "Relative:", self.is_relative)

        cap = cv2.VideoCapture(self.get_movie_path())
        self.fps = cap.get(cv2.CAP_PROP_FPS)

    def get_movie_id_list(self):
        return self.movie_id.split("_")

    def get_auto_text(self, property_name, time_ms, fps):
        if property_name == "Current Time":
            return ms_to_string(time_ms)
        elif property_name == "Current Frame":
            return str(ms_to_frames(time_ms, fps))
        elif property_name == "Movie Name":
            return self.movie_name
        elif property_name == "Movie Path":
            return self.movie_path
        elif property_name == "Movie ID":
            return self.movie_id
        elif property_name == "Year":
            return self.year
        elif property_name == "Source":
            return self.source
        elif property_name == "Duration":
            return ms_to_string(self.duration)
        elif property_name == "Notes":
            return self.notes
        else:
            return "Invalid Property"