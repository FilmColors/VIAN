from core.data.containers import *
import cv2

SCR_DIR = "/scr/"
MOVIE_DIR = "/movie/"
ANALYSIS_DIR = "/analysis/"


class DBSettings():
    def __init__(self, db_root, ann_layers, segmentations, vocabularies, classification_objects):
        self.db_root = db_root
        self.ann_layers = ann_layers
        self.segmentations = segmentations
        self.vocabularies = vocabularies
        self.classification_objecs = classification_objects


class DBMovie():
    def __init__(self):
        # Key
        self.movie_id = -1

        # Fields
        self.movie_name = ""
        self.movie_path = ""
        self.movie_id = -1
        self.year = -1
        self.source = ""
        self.duration = -1
        self.notes = ""
        self.fps = -1

    def from_project(self, m: MovieDescriptor):
        self.movie_id = m.movie_id
        self.movie_name = m.movie_name
        self.movie_path = m.movie_path
        self.movie_id = m.movie_id
        self.year = m.year
        self.source = m.source
        self.duration = m.duration
        self.notes = m.notes
        self.fps = m.fps

    def from_database(self, movie_entry):
        pass

    def __str__(self):
        return self.movie_id + " " + self.name + " " + str(self.year)


class DBAnnotationLayer():
    def __init__(self):
        # Key
        self.layer_id = 0

        self.name = ""
        self.is_mandatory = False

    def from_project(self, l: AnnotationLayer):
        self.name = l.name

    def from_database(self, layer_entry):
        pass


class DBSegment():
    def __init__(self):
        # Foreign Keys
        self.movie_id = 0
        self.segmentation_id = 0

        # Keys
        self.segment_id = 0

        # Fields
        self.movie_segm_id = 0
        self.segm_start = 0
        self.segm_end = 0
        self.segm_duration = 0
        self.segm_body = ""

    def from_project(self, s: Segment, movie_id, segmentation_id):
        self.movie_id = movie_id
        self.segmentation_id = segmentation_id

        self.movie_segm_id = s.ID
        self.segm_start = s.start
        self.segm_end = s.end
        self.segm_duration = s.duration
        self.segm_body = s.annotation_body

    def from_database(self, segment_entry):
        pass


class DBAnnotation():
    def __init__(self):
        # Foreign Keys
        self.movie_id = 0
        self.annotation_layer_id = 0

        # Key
        self.annotation_id = 0

        #Fields
        self.ann_type = 0
        self.ann_pos = (0,0)
        self.ann_size = (0,0)
        self.ann_text = ""

    def from_project(self, a: Annotation, movie_id, annotation_layer_id):
        self.movie_id = movie_id
        self.annotation_layer_id = annotation_layer_id

        self.ann_type = a.a_type
        self.ann_pos = a.orig_position
        self.ann_size = a.size
        self.ann_text = a.text


    def from_database(self, annotation_entry):
        pass


class DBScreenshot():
    def __init__(self):
        # Foreign Keys
        self.movie_id = 0
        self.segment_id = 0

        # Key
        self.screenshot_id = 0

        # Fields
        self.file_path = ""
        self.pixmap = None

    def from_project(self, s: Screenshot, movie_id, segment_id, db_root):
        self.movie_id = movie_id
        self.segment_id = segment_id

        self.file_path = db_root \
                         + SCR_DIR \
                         + str(self.movie_id) + "_" \
                         + str(self.segment_id) + "_" \
                         + str(s.shot_id_segm) + ".png"

        cv2.imwrite(self.file_path, s.img_movie)


    def from_database(self, screenshot_entry):
        pass


class UniqueKeyword():
    def __init__(self, voc, word, class_name, word_id=0):
        self.voc_name = voc
        self.word_name = word
        self.class_name = class_name
        self.word_id = word_id

    def to_query(self):
        table_name = self.class_name + ":" + self.voc_name
        return table_name, self.word_name

    def __str__(self):
        return self.class_name + ":" + self.voc_name + ":" + self.word_name



