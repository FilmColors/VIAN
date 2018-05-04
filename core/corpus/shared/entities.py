from core.data.containers import *
from core.corpus.shared.enums import *
import cv2
import datetime

SCR_DIR = "/screenshots/"
MOVIE_DIR = "/movie/"
ANALYSIS_DIR = "/analysis/"
PROJECTS_DIR = "/projects/"
FTP_DIR = "/ftp/"

# region Functions

def to_tuple2(string, cast=int):
    split = string.split(";")
    if cast is None:
        return (split[0], split[1])
    return (cast(split[0]),  cast(split[1]))


def from_tuple2(tuple2):
    return str(tuple2[0]) + ";" + str(tuple2[1])


def get_current_time():
    t = datetime.datetime.now()
    return (t.year, t.month, t.day, t.hour, t.minute, t.second)

#endregion


#region Entities
class DBEntity():

    def from_project(self, obj: IProjectContainer):
        pass

    def from_database(self, entry):
        pass

    def from_dict(self, d):
        for key, value in d.items():
            setattr(self, key, value)

    def to_dict(self):
        pass

    def to_database(self, include_id = False):
        pass


class DBProject(DBEntity):
    def __init__(self):
        self.project_id = -1
        self.corpus_id = -1

        #Fields
        self.name = ""
        self.is_checked_out = False
        self.checked_out_user = -1
        self.last_modified = 0

        self.folder = ""
        self.path = ""
        self.archive = ""


    def from_project(self, project: VIANProject):
        self.name = project.name
        self.project_id = project.corpus_id
        self.corpus_id = project.movie_descriptor.movie_id
        self.last_modified = str(get_current_time())
        self.path = project.path
        self.folder = project.folder
        self.archive = project.folder + ".zip"
        return self

    def from_database(self, movie_entry):
        self.project_id = movie_entry['id']
        self.corpus_id = movie_entry['corpus_id']
        self.name = movie_entry['name']
        self.is_checked_out = movie_entry['is_checked_out'] == "True"
        self.last_modified = movie_entry['last_modified']
        self.path = movie_entry['path']
        self.folder = movie_entry['folder']
        self.archive = movie_entry['archive']
        self.checked_out_user = movie_entry['checked_out_user']
        return self

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.project_id,
                corpus_id = self.corpus_id,
                name = self.name,
                is_checked_out = self.is_checked_out,
                checked_out_user = self.checked_out_user,
                last_modified = self.last_modified,
                path = self.path,
                folder = self.folder,
                archive = self.archive
            )
        else:
            result =  dict(
                corpus_id = self.corpus_id,
                name = self.name,
                is_checked_out = self.is_checked_out,
                checked_out_user = self.checked_out_user,
                last_modified = self.last_modified,
                path = self.path,
                folder = self.folder,
                archive = self.archive
            )

        return result
    # def to_dict(self, include_id = True, id_override= None):
    #     if include_id:
    #         return self.__dict__
    #     else:
    #         if id_override is not None:
    #             self.id = id_override
    #         return dict(
    #             corpus_id = self.corpus_id,
    #             name = self.name,
    #             is_checked_out = self.is_checked_out,
    #             checked_out_user = self.checked_out_user,
    #             last_modified = self.last_modified,
    #             path = self.path,
    #             folder = self.folder,
    #             archive = self.archive
    #         )


class DBMovie(DBEntity):
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

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.movie_id,
                movie_name = self.movie_name,
                movie_path = self.movie_path,
                movie_id = self.movie_id,
                year = self.year,
                source = self.source,
                duration = self.duration,
                notes = self.notes,
                fps = self.fps,
            )
        else:
            result = dict(
                movie_name=self.movie_name,
                movie_path=self.movie_path,
                movie_id=self.movie_id,
                year=self.year,
                source=self.source,
                duration=self.duration,
                notes=self.notes,
                fps=self.fps,
            )


    def __str__(self):
        return self.movie_id + " " + self.name + " " + str(self.year)


class DBAnnotationLayer(DBEntity):
    def __init__(self):
        # Key
        self.layer_id = -1

        self.name = ""
        self.is_mandatory = False

    def from_project(self, l: AnnotationLayer):
        self.name = l.get_name()

    def from_database(self, entry):
        self.name = entry['name']
        self.layer_id = entry['id']

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.layer_id,
                name = self.name,
                is_mandatory = self.is_mandatory
            )
        else:
            result = dict(
                name=self.name,
                is_mandatory=self.is_mandatory
            )
        return result


class DBSegmentation(DBEntity):
    def __init__(self):
        # Key
        self.segmentation_id = 0

        self.name = ""
        self.is_mandatory = False

    def from_project(self, s: Segmentation):
        self.name = s.get_name()

    def from_database(self, entry):
        self.name = entry['name']
        self.segmentation_id = entry['id']

    def from_dict(self, d):
        pass

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.segmentation_id,
                name = self.name,
                is_mandatory = self.is_mandatory
            )
        else:
            result = dict(
                name=self.name,
                is_mandatory=self.is_mandatory
            )
        return result


class DBSegment(DBEntity):
    def __init__(self):
        # Foreign Keys
        self.movie_id = -1
        self.segmentation_id = -1
        self.project_id = -1

        # Keys
        self.segment_id = -1

        # Fields
        self.movie_segm_id = -1
        self.segm_start = -1
        self.segm_end = -1
        self.segm_duration = -1
        self.segm_body = ""

    def from_project(self, s: Segment, project_id ,movie_id, segmentation_id):
        self.movie_id = movie_id
        self.segmentation_id = segmentation_id
        self.project_id = project_id

        self.movie_segm_id = s.ID
        self.segm_start = s.start
        self.segm_end = s.end
        self.segm_duration = s.duration
        self.segm_body = s.annotation_body

    def from_database(self, entry):
        self.segment_id = entry['a']

        self.movie_id = entry['movie_id']
        self.segmentation_id = entry['segmentation_id']
        self.project_id = entry['project_id']

        self.movie_segm_id = entry['movie_segm_id']
        self.segm_start = entry['segm_start']
        self.segm_end = entry['segm_end']
        self.segm_duration = entry['segm_duration']
        self.segm_body = entry['segm_body']

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.segment_id,

                movie_id = self.movie_id,
                segmentation_id = self.segmentation_id,
                project_id = self.project_id,

                movie_segm_id = self.movie_segm_id,
                segm_start = self.segm_start,
                segm_end = self.segm_end,
                segm_duration = self.segm_duration,
                segm_body = self.segm_body
            )
        else:
            result = dict(
                movie_id=self.movie_id,
                segmentation_id=self.segmentation_id,
                project_id=self.project_id,

                movie_segm_id=self.movie_segm_id,
                segm_start=self.segm_start,
                segm_end=self.segm_end,
                segm_duration=self.segm_duration,
                segm_body=self.segm_body
            )
        return result


class DBAnnotation(DBEntity):
    def __init__(self):
        # Foreign Keys
        self.project_id = -1
        self.movie_id = -1
        self.annotation_layer_id = -1

        # Key
        self.annotation_id = -1

        #Fields
        self.ann_type = 0
        self.ann_pos = (0,0)
        self.ann_size = (0,0)
        self.ann_text = ""

    def from_project(self, project_id, a: Annotation, movie_id, annotation_layer_id):
        self.project_id = project_id

        self.movie_id = movie_id
        self.annotation_layer_id = annotation_layer_id

        self.ann_type = a.a_type
        self.ann_pos = a.orig_position
        self.ann_size = a.size
        self.ann_text = a.text

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id = self.annotation_id,

                movie_id = self.movie_id,
                annotation_layer_id = self.annotation_layer_id,
                project_id = self.project_id,

                ann_type = self.ann_type,
                ann_pos = from_tuple2(self.ann_pos),
                ann_size = from_tuple2(self.ann_size),
                ann_text =self.ann_text,
            )
        else:
            result = dict(

                movie_id=self.movie_id,
                annotation_layer_id=self.annotation_layer_id,
                project_id=self.project_id,

                ann_type=self.ann_type,
                ann_pos=from_tuple2(self.ann_pos),
                ann_size=from_tuple2(self.ann_size),
                ann_text=self.ann_text,
            )
        return result

    def from_database(self, annotation_entry):
        pass


class DBScreenshot(DBEntity):
    def __init__(self):
        # Foreign Keys
        self.movie_id = -1
        self.segment_id = -1
        self.project_id = -1

        # Key
        self.screenshot_id = -1

        # Fields
        self.file_path = ""
        self.pixmap = None
        self.time_ms = -1

    def from_project(self, s: Screenshot, project_id, movie_id, segment_id, db_root):
        self.movie_id = movie_id
        self.segment_id = segment_id
        self.project_id = project_id
        self.time_ms = s.movie_timestamp
        self.file_path = db_root \
                         + SCR_DIR \
                         + str(self.movie_id) + "_" \
                         + str(self.segment_id) + "_" \
                         + str(s.shot_id_segm) + ".png"

        cv2.imwrite(self.file_path, s.img_movie)

    def from_database(self, entry):
        self.screenshot_id = entry['id']
        self.movie_id = entry['movie_id']
        self.segment_id = entry['segment_id']
        self.project_id = entry['project_id']
        self.time_ms = entry['time_ms']
        self.file_path = entry['file_path']

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.screenshot_id,

                movie_id = self.movie_id,
                segment_id = self.segment_id,
                project_id = self.project_id,

                time_ms = self.time_ms,
                file_path = self.file_path,
            )
        else:
            result = dict(
                movie_id=self.movie_id,
                segment_id=self.segment_id,
                project_id=self.project_id,

                time_ms=self.time_ms,
                file_path=self.file_path,
            )
        return result


class DBClassificationObject(DBEntity):
    def __init__(self):
        pass

    def from_project(self, obj: ClassificationObject):
        pass

    def from_dict(self, d):
        pass

    def to_dict(self):
        pass


class DBVocabulary(DBEntity):
    def __init__(self):
        pass

    def from_project(self, obj: Vocabulary):
        pass

    def from_database(self, entry):
        pass

    def from_dict(self, d):
        for key, value in d.items():
            setattr(self, key, value)

    def to_dict(self):
        pass


class UniqueKeyword(DBEntity):
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


class DBContributor(DBEntity):
    def __init__(self, name = "", image_path = "", affiliation = ""):
        self.contributor_id = -1

        self.name = name
        self.image_path = image_path
        self.n_contributions = 0

        self.affiliation = affiliation

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.contributor_id,
                name = self.name,
                image_path = self.image_path,
                n_contributions = self.n_contributions,
                affiliation = self.affiliation
            )
        else:
            result = dict(
                name=self.name,
                image_path=self.image_path,
                n_contributions=self.n_contributions,
                affiliation=self.affiliation
            )
        return result

    def from_database(self, entry):
        self.contributor_id = entry['id']
        self.name = entry['name']
        self.image_path = entry['image_path']
        self.n_contributions = entry['n_contributions']
        self.affiliation = entry['affiliation']
        return self

#endregion



