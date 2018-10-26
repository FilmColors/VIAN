import cv2
import json
import datetime
from core.corpus.shared.enums import *
try:
    from core.analysis.analysis_import import *
except:
    pass
try:
    from core.container.project import *
    from core.data.settings import Contributor
except Exception as e:
    raise e
    class IProjectContainer: pass
    class VIANProject: pass
    class AnnotationLayer: pass
    class Segmentation: pass
    class Segment: pass
    class Annotation: pass
    class ScreenshotGroup: pass
    class Screenshot: pass
    class ClassificationObject: pass
    class Vocabulary: pass
    class VocabularyWord: pass
    class Experiment: pass
    class AnalysisContainer: pass
    class IAnalysisJobAnalysis: pass
    class NodeScriptAnalysis: pass
    class ColormetryAnalysis: pass
    class MovieDescriptor: pass

SCR_DIR = "/screenshots/"
MOVIE_DIR = "/movie/"
ANALYSIS_DIR = "/analysis/"
PROJECTS_DIR = "/projects/"
EXPERIMENTS_DIR = "/experiments/"
FTP_DIR = "/ftp/"
MASK_DIR = "/masks/"
THUMBNAILS = "/thumbnails/"

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
        return self

    def to_dict(self):
        pass

    def to_database(self, include_id = False):
        pass


class DBProject(DBEntity):
    def __init__(self):
        self.project_id = -1

        # FILEMAKER ID
        self.corpus_id = -1
        self.manifestation_id = -1
        self.copy_id = -1

        #Fields
        self.name = ""
        self.is_checked_out = False
        self.checked_out_user = -1
        self.last_modified = 0

        self.folder = ""
        self.path = ""
        self.archive = ""
        self.thumbnail_path = ""

    def from_project(self, project: VIANProject, thumbnail_path = ""):
        self.name = project.name

        if isinstance(project.movie_descriptor.movie_id, list):
            project.movie_descriptor.movie_id = "_".join(project.movie_descriptor.movie_id)

        self.project_id = project.movie_descriptor.movie_id.split("_")[0]
        self.manifestation_id = project.movie_descriptor.movie_id.split("_")[1]
        self.copy_id = project.movie_descriptor.movie_id.split("_")[2]

        self.corpus_id = project.movie_descriptor.movie_id
        self.last_modified = str(get_current_time())
        self.path = project.path
        self.folder = project.folder
        self.archive = project.folder + ".zip"
        self.thumbnail_path = thumbnail_path
        return self

    def from_database(self, movie_entry):
        self.project_id = movie_entry['id']
        self.corpus_id = movie_entry['corpus_id']
        self.name = movie_entry['name']
        self.is_checked_out = movie_entry['is_checked_out'] == 1
        self.last_modified = movie_entry['last_modified']
        self.path = movie_entry['path']
        self.folder = movie_entry['folder']
        self.archive = movie_entry['archive']
        self.checked_out_user = movie_entry['checked_out_user']
        try:
            self.thumbnail_path = movie_entry['thumbnail_path']
        except:
            pass
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
                archive = self.archive,
                thumbnail_path = self.thumbnail_path
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
                archive = self.archive,
                thumbnail_path=self.thumbnail_path
            )

        return result


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
        return str(self.movie_id) + " " + self.movie_name + " " + str(self.year)


class DBAnnotationLayer(DBEntity):
    def __init__(self, name = ""):
        # Key
        self.layer_id = -1

        self.name = name
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
    def __init__(self, name = ""):
        # Key
        self.segmentation_id = 0

        self.name = name
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
        self.segment_id = entry['id']

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
        self.classification_object_id = -1
        # Key
        self.screenshot_id = -1

        # Fields
        self.file_path = ""
        self.pixmap = None
        self.time_ms = -1

    def from_project(self, s: Screenshot, project_id, movie_id, screenshot_group_id, db_root, filepath, classification_object_id = -1):
        self.movie_id = movie_id
        self.project_id = project_id
        self.time_ms = s.movie_timestamp
        self.screenshot_group_id = screenshot_group_id
        self.classification_object_id = classification_object_id
        self.file_path = filepath
        return self

    def from_database(self, entry):
        self.screenshot_id = entry['id']
        self.movie_id = entry['movie_id']
        self.screenshot_group_id = entry['screenshot_group_id']
        self.project_id = entry['project_id']
        self.time_ms = entry['time_ms']
        self.file_path = entry['file_path']
        self.classification_object_id = entry['classification_object_id']
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
                classification_object_id = self.classification_object_id
            )
        else:
            result = dict(
                movie_id=self.movie_id,
                project_id=self.project_id,
                screenshot_group_id=self.screenshot_group_id,

                time_ms=self.time_ms,
                file_path=self.file_path,
                classification_object_id=self.classification_object_id
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
        self.category = ""
        self.name = ""

    def from_project(self, obj: Vocabulary):
        self.name = obj.name
        self.category = obj.category
        return self

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.vocabulary_id,
                name=self.name,
                category=self.category
            )
        else:
            result = dict(
                name=self.name,
                category=self.category
            )
        return result

    def from_database(self, entry):
        self.vocabulary_id = entry['id']
        self.name = entry['name']
        self.category = entry['category']
        return self


class DBVocabularyWord(DBEntity):
    def __init__(self):
        self.word_id = -1

        self.vocabulary_id = -1

        self.name = ""

    def get_name(self):
        return self.name

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
        self.unique_keyword_id = entry['id']
        self.vocabulary_id = entry['vocabulary_id']
        self.word_id = entry['word_id']
        self.class_obj_id = entry['class_obj_id']
        self.word_name = entry['word_name']
        return self


class DBContributor(DBEntity):
    def __init__(self, name = "", image_path = "", affiliation = "", password="", email = ""):
        self.contributor_id = -1

        self.name = name
        self.image_path = image_path
        self.n_contributions = 0
        self.password = password
        self.email = email

        self.affiliation = affiliation

    def to_database(self, include_id = False):
        if include_id:
            result = dict(
                id = self.contributor_id,
                name = self.name,
                image_path = self.image_path,
                n_contributions = self.n_contributions,
                affiliation = self.affiliation,
                password = self.password,
                email = self.email
            )
        else:
            result = dict(
                name=self.name,
                image_path=self.image_path,
                n_contributions=self.n_contributions,
                affiliation=self.affiliation,
                password=self.password,
                email = self.email
            )
        return result

    def from_vian_user(self, user:Contributor):
        self.contributor_id = 0
        self.name = user.name
        self.email = user.email
        self.affiliation = user.affiliation
        self.password = user.password
        return self

    def from_database(self, entry):
        self.contributor_id = entry['id']
        self.name = entry['name']
        self.image_path = entry['image_path']
        self.n_contributions = entry['n_contributions']
        self.affiliation = entry['affiliation']
        self.password = entry['password']
        self.email = entry['email']
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
        # self.analyses_names = obj.analyses['class_name']
        # self.analyses_params = [p.serialize() for p in obj.analyses_parameters]

        return self

    def store_descriptor(self):
        with open(self.descriptor_path, "w") as f:
            json.dump(self.__dict__, f)

    def load_descriptor(self):
        try:
            exp_id = self.experiment_id
            with open(self.descriptor_path, "r") as f:
                data = json.load(f)
                for attr, val in data.items():
                    setattr(self, attr, val)
            self.experiment_id  = exp_id
        except Exception as e:
            print("Experiment Descriptor not found")
            print(e)


class KeywordMappingEntry(DBEntity):
    def __init__(self, project_id=-1, container_type=-1, keyword_id=-1):
        self.entry_id = -1

        self.project_id = project_id
        self.container_type = container_type
        self.target_id = -1
        self.keyword_id = keyword_id

    def from_database(self, entry):
        try:
            self.entry_id = entry['id']
            self.target_id = entry['segment_id']
            self.container_type = "SegmentMapping"
        except Exception as e:
            try:
                self.target_id = entry['screenshot_id']
                self.container_type = "ScreenshotMapping"
            except:
                print("Mapping not found", entry['id'], e)

        self.project_id = entry['project_id']
        # self.container_type = entry['container_type']
        self.keyword_id = entry['keyword_id']
        return self

    def to_database(self, include_id=False):
        # TODO How the differentiate the Target
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


class DBAnalysis(DBEntity):
    def __init__(self):
        self.analysis_id = -1
        self.project_id = -1
        self.classification_obj_id = -1

        self.analysis_class_name = ""
        self.analysis_data = ""
        self.analysis_type = -1 # 0: JobAnalysis, 1: ScriptAnalysis
        self.target_container_type = ""
        self.target_container_id = -1

    def from_database(self, entry):
        self.analysis_id = entry['id']
        self.project_id = entry['project_id']
        self.analysis_class_name = entry['analysis_name']
        self.analysis_type = entry['analysis_type']
        if self.analysis_type == 0:
            try:
                self.analysis_data = eval(self.analysis_class_name)().from_json(entry['data'])
            except:
                self.analysis_data = None
        else:
            self.analysis_data = entry['data']
        self.target_container_type = entry['target_container_type']
        self.target_container_id = entry['target_container_id']
        self.classification_obj_id = entry['classification_object_id']
        return self

    def from_project(self, obj: AnalysisContainer, project_id, class_obj_id = -1, target_container_id = -1):
        self.project_id = project_id
        self.classification_obj_id = class_obj_id
        self.target_container_id = target_container_id

        if isinstance(obj, IAnalysisJobAnalysis):
            self.analysis_class_name = obj.analysis_job_class
            self.analysis_data = obj.get_adata()
            self.analysis_type = 0
            if obj.target_container is not None:
                self.target_container_type = obj.target_container.__class__.__name__

        elif isinstance(obj, NodeScriptAnalysis):
            self.analysis_class_name = obj.project.get_by_id(obj.script_id).get_name()
            self.analysis_data = obj.data
            self.analysis_type = 1
        elif isinstance(obj, ColormetryAnalysis):
            self.analysis_class_name = "Colormetry"
            self.analysis_data = obj.data
            self.analysis_type = 2

        return self

    def to_database(self, include_id = False):
        data = ""
        if self.analysis_type == 0:
            analysis_class = eval(self.analysis_class_name)
            if analysis_class != SemanticSegmentationAnalysis:
                data = analysis_class().to_json(self.analysis_data)

        elif self.analysis_type == 1:
            # data = self.analysis_data
            pass

        elif self.analysis_type == 2:
            pass
            # data = self.analysis_data

        else:
            raise Exception("Analysis not identified")

        if include_id:
            result = dict(
                analysis_id = self.analysis_id,
                project_id = self.project_id,
                analysis_name=self.analysis_class_name,
                analysis_type=self.analysis_type,
                target_container_type = self.target_container_type,
                target_container_id = self.target_container_id,
                classification_object_id = self.classification_obj_id,
                data = data
            )
        else:
            result = dict(
                project_id=self.project_id,
                analysis_name=self.analysis_class_name,
                analysis_type=self.analysis_type,
                target_container_type=self.target_container_type,
                target_container_id=self.target_container_id,
                classification_object_id=self.classification_obj_id,
                data=data
            )
        return result


class DBSemanticSegmentationDatasetLabel(DBEntity):
    def __init__(self, dataset_name, label_idx, label_name):
        self.entry_id = -1

        self.dataset_name = dataset_name
        self.label_idx = label_idx
        self.label_name = label_name

    def from_database(self, entry):
        self.entry_id = entry['id']
        self.dataset_name = entry['dataset_name']
        self.label_idx = entry['label_idx']
        self.label_name = entry['label_name']

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.entry_id,
                dataset_name=self.dataset_name,
                label_idx=self.label_idx,
                label_name=self.label_name
            )
        else:
            result = dict(
                dataset_name=self.dataset_name,
                label_idx=self.label_idx,
                label_name=self.label_name
            )
        return result


class DBFilmographicalData(DBEntity):
    def __init__(self):
        self.filmography_id = -1
        self.project_id = -1

        # FIWI FIELDS
        self.imdb_id = -1
        self.color_process = ""
        self.director = ""
        self.genre = ""
        self.cinematography = ""
        self.color_consultant = ""
        self.production_design = ""
        self.art_director = ""
        self.costum_design = ""
        self.production_company = ""
        self.country = ""

    def from_project(self, obj: VIANProject, project_id):
        if obj.movie_descriptor.meta_data is None:
            return None
        if "ERC_FilmColorsFilmography" in obj.movie_descriptor.meta_data.keys():
            for attr, val in obj.movie_descriptor.meta_data['ERC_FilmColorsFilmography'].items():
                setattr(self, attr, val)
            self.project_id = project_id
            return self
        else:
            return None

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.filmography_id,
                project_id=self.project_id,

                imdb_id=self.imdb_id,
                color_process=self.color_process,
                director=self.director,
                genre=self.genre,
                cinematography=self.cinematography,
                color_consultant = self.color_consultant,
                art_director=self.art_director,
                production_design=self.production_design,
                costum_design=self.costum_design,
                production_company=self.production_company,
                country = self.country

            )
        else:
            result = dict(
                project_id=self.project_id,

                imdb_id=self.imdb_id,
                color_process=self.color_process,
                director=self.director,
                genre=self.genre,
                cinematography=self.cinematography,
                color_consultant=self.color_consultant,
                art_director = self.art_director,
                production_design=self.production_design,
                costum_design=self.costum_design,
                production_company=self.production_company,
                country=self.country
            )
        return result

    def from_database(self, entry):
        self.filmography_id = entry['id']
        self.project_id = entry['project_id']

        # FIWI FIELDS
        self.imdb_id = entry['imdb_id']
        self.color_process = entry['color_process']
        self.director = entry['director']
        self.genre = entry['genre']
        self.cinematography = entry['cinematography']
        try:
            self.color_consultant = entry['color_consultant']
            self.art_director = entry['art_director']
        except:
            pass
        self.production_design = entry['production_design']
        self.costum_design = entry['costum_design']
        self.production_company = entry['production_company']
        self.country = entry['country']
        return self

    def __str__(self):
        return (str(self.__dict__))


class DBContributorMapping(DBEntity):
    def __init__(self, project_id=-1, contributor_id=-1):
        self.entry_id = -1

        self.project_id = project_id
        self.contributor_id = contributor_id

    def from_database(self, entry):
        try:
            self.entry_id = entry['id']
            self.project_id = entry['project_id']
            self.contributor_id = entry['contributor_id']
        except Exception as e:
            print("Mapping not found", entry['id'], e)
        return self

    def to_database(self, include_id=False):
        if include_id:
            result = dict(
                id=self.entry_id,
                project_id=self.project_id,
                contributor_id=self.contributor_id,
            )
        else:
            result = dict(
                project_id=self.project_id,
                contributor_id=self.contributor_id,
            )
        return result

#endregion

#region Query
class QueryRequestData():
    """
    A container for query parameters in the DatasetDB. 
    
    An instance of QueryRequestData can be passed to the DatasetDB.parse_query() function to perform a query. 
    
    The type of information that is retrieved can be set by the query_type field. 
    The return is as follows:
        projects -> dict(query.query_type, data=dict(projects=r:Dict, 
                                                     contributors=c:Dict, 
                                                     root=self.root_dir:str, 
                                                     filmographies = f:Dict))
                                                     
        keywords -> dict(type=query.query_type, data=dict(keywords=keywords,
                                                             cl_objs=hashm_cl_objs: Dict(key: cl_obj_id, val: cl_obj),
                                                             vocabularies=hashm_vocabularies: Dict(key: voc_id, val: voc),
                                                             vocabulary_words=hashm_vocabulary_words: Dict(key: word_id, val: word)))
                                                             
        movies ->  dict(type=query.query_type, data=dict(projects=dbprojects, 
                                                         filmographies=dbfilmographies))    
        
        movie-info -> dict(type="movie_info", data = dict(segments=rsegms,
                                                   keywords=rkeyw,
                                                   movie=rmovie,
                                                   screenshots=scrs,
                                                   features=features,
                                                   project=project,
                                                   screenshot_segm_mapping=screenshot_segm_mapping))
                                                                                         
    
    :ivar query_type: Defines the result of the query, can be "projects", "segments", "movies", "screenshots", 
                      "projects", "keywords", "movie_info", "screenshot_info"
    :ivar filter_filmography: A dict of filter options for the filmography
    :ivar filter_keywords: A dict of Keyword IDS assigned to the container
    :ivar filter_classification_objects: A List of ClassificationObject IDS to filter
    """
    def __init__(self, query_type, filter_filmography = None, filter_keywords = None,
                 filter_classification_objects = None, project_filter = None, segment_filters = None, shot_id = None):
        """
        
        :param query_type: 
        :param filter_filmography: dict(include:[] exclude:[])
        :param filter_keywords: dict(include:[] exclude:[])
        :param filter_classification_objects: dict(include:[] exclude:[])
        """
        self.query_type = query_type
        self.project_filter = project_filter
        self.filter_filmography = filter_filmography
        self.filter_keywords = filter_keywords
        self.filter_classification_objects = filter_classification_objects
        self.segment_filters = segment_filters
        self.shot_id = shot_id


class FilmographyQuery():
    def __init__(self, imdb_id = None, corpus_id = None, color_process = None, director = None, genre = None, cinematography = None,
                 color_consultant = None, production_design = None, art_director= None, costum_design= None,
                 production_company= None, country= None, year_start= None, year_end= None):

        self.imdb_id = imdb_id
        self.corpus_id = corpus_id
        self.color_process = color_process
        self.director = director
        self.genre = genre
        self.cinematography = cinematography
        self.color_consultant = color_consultant
        self.production_design = production_design
        self.art_director = art_director
        self.costum_design = costum_design
        self.production_company = production_company
        self.country = country
        self.year_start = year_start
        self.year_end = year_end
#
# class QueryResult:
#     def __init__(self):
#         pass
#
#
#
#
# class MovieQueryResult(QueryResult):
#     def __init__(self):
#         super(MovieQueryResult, self).__init__()
#         self.filmography = None
#         self.db_segments = []
#         self.keyword_mapping = []
#         self.db_screenshots = []
#         self.color_features = []
#
#
# class SegmentQueryResult(QueryResult):
#     def __init__(self):
#         super(SegmentQueryResult, self).__init__()
#         self.db_segments = []
#         self.db_screenshots = []
#         self.keyword_mapping = []
#         self.db_movies = []
#
#
# class ScreenshotQueryResult(QueryResult):
#     def __init__(self):
#         super(ScreenshotQueryResult, self).__init__()
#         self.db_screenshots = []
#         self.db_segments = []
#

#endregion

