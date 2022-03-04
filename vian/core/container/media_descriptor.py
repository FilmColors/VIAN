import os
import typing

from pymediainfo import MediaInfo

from typing import Tuple

import cv2
from vian.core.data.computation import ms_to_string, ms_to_frames
from vian.core.data.enums import MOVIE_DESCRIPTOR

from vian.core.data.log import log_error
from .container_interfaces import BaseProjectEntity, ISelectable, IHasName, ITimeRange, \
    AutomatedTextSource, IClassifiable


# class MediaDescriptor():
#     """
#     TODO: BaseClass for MovieDescriptor and future media types
#     """
#     pass


class MovieDescriptor(BaseProjectEntity, ISelectable, IHasName, ITimeRange, AutomatedTextSource, IClassifiable):
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
        BaseProjectEntity.__init__(self, unique_id=unique_id)
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

        # Pixel coordinates of the four square points x0 x1 y0 y1
        self.letterbox_rect: typing.Tuple[int, int, int, int] | None = None

        self.display_width = None
        self.display_height = None

        self.frame_width = -1
        self.frame_height = -1
        self.frame_count: typing.Union[None, int] = None
        self.parse_movie()


    def set_letterbox_rect(self, rect:typing.Tuple[int, int, int, int]):
        """
        Can either be a tuple with (x1, y1, x2, y2) or a dictionary with
        dict(left:int, right:int, top:int, bottom:int)
        :param rect:
        :return:
        """
        if isinstance(rect, dict):
            rect = (rect['left'], rect['top'],  rect['right'], rect['bottom'])

        self.letterbox_rect = rect


    def get_letterbox_rect(self, as_coords=False) -> typing.Tuple[int, int, int, int]:
        """
        Get the letterbox rect which marks the dark borders of a frame.

        :param bool as_coords: if true, returns the extends as coordinates instead of width and height. default: False
        :return tuple: returns the letterbox rect.
                either as Tuple[x, y, width, height]
                ort as Tuple[x1, y1, x2, y2] if as_coords is set to True
        """
        x, y, w, h = self.letterbox_rect
        if as_coords:
            return x, y, x + w, y + h

        return x, y, w, h

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
        self.parse_movie()
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
        return os.path.normpath(self.movie_path)

    def set_movie_path(self, path):
        """
        Sets the movie path of this project.
        If the movie is within the Projects directory it makes it relative, else it makes it absolut
        :param path:
        :return:
        """

        self.movie_path = os.path.normpath(path)
        self.parse_movie()
        return self.movie_path

    def parse_movie(self):
        if os.path.isfile(self.get_movie_path()):
            cap = cv2.VideoCapture(self.get_movie_path())
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            self.display_width, self.display_height = self.get_frame_dimensions()
        else:
            self.fps = 30
            self.display_height = None
            self.display_width = None
            self.frame_count = None

    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Returns the display dimension of the movie based on the meta data.
        if the meta data could not be parsed, it returns the storage dimensions.

        :return: Tuple(width, height)
        """
        try:
            media_info = MediaInfo.parse(self.movie_path)

            height = None
            display_aspect = None

            for t in media_info.to_data()['tracks']:
                if t['track_type'] == "Video":
                    height = int(t['sampled_height'])
                    display_aspect = float(t['display_aspect_ratio'])
                    break
            return int(height * display_aspect), height

        except RuntimeError as e:
            log_error("Exception in MovieDescriptor.get_frame_dimensions", e)

            cap = cv2.VideoCapture(self.movie_path)
            cap.read()

            return int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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