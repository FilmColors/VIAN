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
ANALYSIS_NODE_SCRIPT = 12
ANALYSIS_JOB_ANALYSIS = 13
EXPERIMENT = 14
CLASSIFICATIONOBJECT = 15


FILE_EXT_PROJECT = ".eext"
FILE_EXT_EXPERIMENT = ".vian_experiment"


def get_type_as_string(type):
    if type == PROJECT:
        return "PROJECT"
    elif type == SEGMENTATION:
        return "SEGMENTATION"
    elif type == SEGMENT:
        return "SEGMENT"
    elif type == ANNOTATION:
        return "ANNOTATION"
    elif type == ANNOTATION_LAYER:
        return "ANNOTATION_LAYER"
    elif type == SCREENSHOT:
        return "SCREENSHOT"
    elif type == MOVIE_DESCRIPTOR:
        return "MOVIE_DESCRIPTOR"
    elif type == ANALYSIS:
        return "ANALYSIS"
    elif type == SCREENSHOT_GROUP:
        return "SCREENSHOT_GROUP"
    elif type == NODE:
        return "NODE"
    elif type == NODE_SCRIPT:
        return "NODE_SCRIPT"
    elif type == VOCABULARY:
        return "VOCABULARY"
    elif type == VOCABULARY_WORD:
        return "VOCABULARY_WORD"
    elif type == ANALYSIS_NODE_SCRIPT:
        return "ANALYSIS_NODE_SCRIPT"
    elif type == ANALYSIS_JOB_ANALYSIS:
        return "ANALYSIS_JOB_ANALYSIS"
    elif type == EXPERIMENT:
        return "EXPERIMENT"
    elif type == CLASSIFICATIONOBJECT:
        return "CLASSIFICATION_OBJECT"
    else:
        return "Mehh, Whatever this should be"


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
    Web = 3,
    Film = 4


class AspectRatio(Enum):
    ASPECT_16_9 = ("16/9")
    ASPECT_16_10 = (str(float(5)/4))


class ImageType(Enum):
    JPG = 0
    PNG = 1


class ProjectType(Enum):
    DEFAULT = 0
    SIMPLE_ANNOTATION = 1
    FILM_COLORS = 2

