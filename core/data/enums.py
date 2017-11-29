from enum import Enum


PROJECT = -1
SEGMENTATION = 0
SEGMENT = 1
ANNOTATION = 2
ANNOTATION_LAYER = 3
SCREENSHOT = 4
MOVIE_DESCRIPTOR = 5
ANALYSIS = 6
SCREENSHOT_GROUP = 7
NODE = 8
NODE_SCRIPT = 9
VOCABULARY = 10
VOCABULARY_WORD = 11

class AnnotationType(Enum):
    Rectangle = 0
    Ellipse = 1
    Line = 2
    Text = 3
    Image = 4
    FreeHand = 5


class ScreenshotNamingConventionOptions(Enum):
    empty = (None, 0)
    # Screenshot Attributes
    Screenshot_Title = ("Screenshot", "title")
    Scene_ID = ("Screenshot", "scene_id")
    Timestamp = ("Screenshot", "movie_timestamp")
    Creation_Timestamp = ("Screenshot", "creation_timestamp")
    Shot_ID_Global = ("Screenshot", "shot_id_global")
    Shot_ID_Segment = ("Screenshot", "shot_id_segm")
    Shot_Group = ("Screenshot", "screenshot_group")

    # Movie Attributes
    Movie_ID = ("Movie", "movie_id")
    Movie_Name = ("Movie", "movie_name")
    Movie_Year = ("Movie", "year")
    Movie_Source= ("Movie", "source")


def get_enum_value(enum, name):
    for s in enum:
        if name == s.name:
            return s.value

def get_enum(enum, name):
    for s in enum:
        if name == s.name:
            return s


class MovieSource(Enum):
    VHS = 0,
    DVD = 1,
    BluRay = 2,
    Web = 3


class AspectRatio(Enum):
    ASPECT_16_9 = ("16/9")
    ASPECT_16_10 = (str(float(5)/4))


class ImageType(Enum):
    JPG = 0
    PNG = 1

