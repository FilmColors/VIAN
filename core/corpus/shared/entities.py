from core.data.containers import *
from core.corpus.shared.enums import *
import cv2
import datetime

SCR_DIR = "/screenshots/"
MOVIE_DIR = "/movie/"
ANALYSIS_DIR = "/analysis/"
PROJECTS_DIR = "/projects/"
EXPERIMENTS_DIR = "/experiments/"
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
        self.movie_id_db = -1

        # Fields
        self.movie_name = ""
        self.movie_path = ""
        self.movie_id = (0, 0, 0)
        self.year = -1
        self.source = ""
        self.duration = -1
        self.notes = ""
        self.fps = -1

    def from_project(self, m: MovieDescriptor):
        self.movie_id_db = m.movie_id
        self.movie_name = m.movie_name
        self.movie_path = m.movie_path
        try:
            split = m.movie_id.split("_")
            self.movie_id = (split[0], split[1], split[2])
        except:
            self.movie_id = "0_0_0".split("_")
        self.year = m.year
        self.source = m.source
        self.duration = m.duration
        self.notes = m.notes
        self.fps = m.fps
        return self

    def from_database(self, movie_entry):
        self.movie_id_db = movie_entry['id']
        self.movie_name = movie_entry['movie_name']
        self.movie_path = movie_entry['movie_path']
        self.movie_id = (movie_entry['movie_id_a'], movie_entry['movie_id_b'], movie_entry['movie_id_c'])
        self.year = movie_entry['year']
        self.source = movie_entry['source']
        self.duration = movie_entry['duration']
        self.notes = movie_entry['notes']
        self.fps = movie_entry['fps']
        return self

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.movie_id_db,
                movie_name = self.movie_name,
                movie_path = self.movie_path,
                movie_id_a = self.movie_id[0],
                movie_id_b = self.movie_id[1],
                movie_id_c = self.movie_id[2],
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
                movie_id_a = self.movie_id[0],
                movie_id_b = self.movie_id[1],
                movie_id_c = self.movie_id[2],
                year=self.year,
                source=self.source,
                duration=self.duration,
                notes=self.notes,
                fps=self.fps,
            )
        return result

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
        return self

    def from_database(self, entry):
        self.name = entry['name']
        self.layer_id = entry['id']
        return self

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
        return self

    def from_database(self, entry):
        self.name = entry['name']
        self.segmentation_id = entry['id']
        return self

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
        return self

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

        return self

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

        self.ann_type = a.a_type.name
        self.ann_pos = a.orig_position
        self.ann_size = a.size
        self.ann_text = a.text
        return self

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

    def from_database(self, entry):
        self.movie_id = entry['movie_id']
        self.annotation_layer_id = entry['annotation_layer_id']

        self.ann_type = entry['ann_type']
        self.ann_pos = to_tuple2(entry['ann_pos'], cast=float)
        self.ann_size = to_tuple2(entry['ann_size'],cast=float)
        self.ann_text = entry['ann_text']


class DBScreenshotGroup(DBEntity):
    def __init__(self):
        self.group_id = -1

        self.name = ""

    def to_database(self, include_id = False):
        if include_id:
           result = dict(
               id = self.group_id,
               name = self.name
           )
        else:
            result = dict(
                name = self.name
            )
        return result

    def from_project(self, obj: ScreenshotGroup):
        self.name = obj.name
        return self

    def from_database(self, entry):
        self.group_id = entry['id']
        self.name = entry['name']
        return self


class DBScreenshot(DBEntity):
    def __init__(self):
        # Foreign Keys
        self.movie_id = -1
        self.segment_id = -1
        self.project_id = -1
        self.screenshot_group_id = -1

        # Key
        self.screenshot_id = -1

        # Fields
        self.file_path = ""
        self.pixmap = None
        self.time_ms = -1

    def from_project(self, s: Screenshot, project_id, movie_id, screenshot_group_id, db_root):
        self.movie_id = movie_id
        self.project_id = project_id
        self.time_ms = s.movie_timestamp
        self.screenshot_group_id = screenshot_group_id
        self.file_path = db_root \
                         + SCR_DIR \
                         + str(self.movie_id) + "_" \
                         + str(self.segment_id) + "_" \
                         + str(s.shot_id_segm) + ".png"

        cv2.imwrite(self.file_path, s.img_movie)
        return self

    def from_database(self, entry):
        self.screenshot_id = entry['id']
        self.movie_id = entry['movie_id']
        self.screenshot_group_id = entry['screenshot_group_id']
        self.project_id = entry['project_id']
        self.time_ms = entry['time_ms']
        self.file_path = entry['file_path']
        return self

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.screenshot_id,

                movie_id = self.movie_id,
                project_id = self.project_id,
                screenshot_group_id  = self.screenshot_group_id,

                time_ms = self.time_ms,
                file_path = self.file_path,
            )
        else:
            result = dict(
                movie_id=self.movie_id,
                project_id=self.project_id,
                screenshot_group_id=self.screenshot_group_id,

                time_ms=self.time_ms,
                file_path=self.file_path,
            )
        return result


class DBClassificationObject(DBEntity):
    def __init__(self):
        self.classification_object_id = -1
        self.experiment_id = -1
        self.name = ""

    def from_project(self, obj: ClassificationObject, experiment_id):
        self.name = obj.name
        self.experiment_id = experiment_id
        return self

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.classification_object_id,
                experiment_id=self.experiment_id,
                name=self.name
            )
        else:
            result = dict(
                experiment_id=self.experiment_id,
                name=self.name
            )
        return result

    def from_database(self, entry):
        self.classification_object_id = entry['id']
        self.experiment_id = entry['experiment_id']
        self.name = entry['name']
        return self


class DBVocabulary(DBEntity):
    def __init__(self):
        self.vocabulary_id = -1
        self.name = ""

    def from_project(self, obj: Vocabulary):
        self.name = obj.name
        return self

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.vocabulary_id,
                name=self.name
            )
        else:
            result = dict(
                name=self.name
            )
        return result

    def from_database(self, entry):
        self.vocabulary_id = entry['id']
        self.name = entry['name']
        return self


class DBVocabularyWord(DBEntity):
    def __init__(self):
        self.word_id = -1

        self.vocabulary_id = -1

        self.name = ""

    def from_project(self, obj:VocabularyWord, vocabulary_id):
        self.vocabulary_id = vocabulary_id
        self.name = obj.name
        return self

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.word_id,
                vocabulary_id = self.vocabulary_id,
                name = self.name
            )
        else:
            result = dict(
                vocabulary_id = self.vocabulary_id,
                name = self.name
            )
        return result

    def from_database(self, entry):
        self.word_id = entry['id']
        self.vocabulary_id = entry['vocabulary_id']
        self.name = entry['name']
        return self


class DBUniqueKeyword(DBEntity):
    def __init__(self):
        self.unique_keyword_id = -1

        self.vocabulary_id = -1
        self.word_id = -1
        self.class_obj_id = -1
        self.word_name = ""

    def from_project(self, obj: VocabularyWord, vocabulary_id, word_id, class_obj_id):
        self.vocabulary_id = vocabulary_id
        self.word_id = word_id
        self.class_obj_id = class_obj_id
        self.word_name = obj.get_name()
        return self

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.vocabulary_id,
                vocabulary_id=self.vocabulary_id,
                word_id=self.word_id,
                class_obj_id=self.class_obj_id,
                word_name=self.word_name
            )
        else:
            result = dict(
                vocabulary_id=self.vocabulary_id,
                word_id=self.word_id,
                class_obj_id=self.class_obj_id,
                word_name=self.word_name
            )
        return result

    def from_database(self, entry):
        self.unique_keyword_id = entry['unique_keyword_id']
        self.vocabulary_id = entry['vocabulary_id']
        self.word_id = entry['word_id']
        self.class_obj_id = entry['class_obj_id']
        self.word_name = entry['word_name']
        return self


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


class DBExperiment(DBEntity):
    def __init__(self, db_root):
        self.experiment_id = -1

        # DATABASE Stored
        self.name = ""
        self.descriptor_path = ""

        # JSON Stored
        self.classification_objects = []
        self.analyses_names = []
        self.analyses_params = []

        self.db_root = db_root

    def from_database(self, entry):
        self.experiment_id = entry['id']
        self.descriptor_path = entry['path']
        self.name = entry['name']

        self.load_descriptor()
        return self

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.experiment_id,
                path = self.descriptor_path,
                name = self.name
            )
        else:
            result = dict(
                path = self.descriptor_path,
                name = self.name
            )
        self.store_descriptor()
        return result

    def from_project(self, obj: Experiment):
        self.name = obj.name
        self.descriptor_path = self.db_root + EXPERIMENTS_DIR + obj.name + ".json"

        all_cobj = obj.get_classification_objects_plain()
        self.classification_objects = []
        for c in all_cobj:
            voc_names = [v.get_name() for v in c.get_vocabularies()]
            self.classification_objects.append([c.get_name(), c.parent.get_name(), voc_names])
        self.analyses_names = obj.analyses
        self.analyses_params = [p.serialize() for p in obj.analyses_parameters]

        return self

    def store_descriptor(self):
        with open(self.descriptor_path, "w") as f:
            json.dump(self.__dict__, f)

    def load_descriptor(self):
        try:
            with open(self.descriptor_path, "r") as f:
                data = json.load(f)
                for attr, val in data.items():
                    setattr(self, attr, val)
        except Exception as e:
            print("Experiment Descriptor not found")
            print(e)


class KeywordMappingEntry(DBEntity):
    def __init__(self, project_id=-1, container_type=-1, keyword_id=-1):
        self.entry_id = -1

        self.project_id = project_id
        self.container_type = container_type
        self.keyword_id = keyword_id

    def from_database(self, entry):
        self.entry_id = entry['id']
        self.project_id = entry['project_id']
        self.container_type = entry['container_type']
        self.keyword_id = entry['keyword_id']

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.entry_id,
                project_id=self.project_id,
                keyword_id=self.keyword_id,
                container_type=self.container_type,
            )
        else:
            result = dict(
                project_id=self.project_id,
                keyword_id=self.keyword_id,
                container_type=self.container_type,
            )
        return result


#endregion



