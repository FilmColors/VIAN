from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table, TypeDecorator, Unicode, Text, Float
from sqlalchemy.orm import relationship, joinedload
import json

"""
    User - Upload: One to Many
    Upload - Vian_Project One to One
"""

use_postgres = False

Base = declarative_base()

import cProfile
from io import StringIO
import pstats
import contextlib

@contextlib.contextmanager
def profiled():
    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    # uncomment this to see who's calling what
    # ps.print_callers()
    print(s.getvalue())

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
        self.copy_id = None
        self.manifestation_id = None


class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedDict(255)

    """

    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value.__dict__)

        return value

    def process_result_value(self, value, dialect):
        point = None
        if value is not None:
            value = json.loads(value)
            point = Point(value['x'], value['y'])
        return point



UKW_Annotation_association_table = Table('ukw_annotation_association', Base.metadata,
                                         Column('unique_keyword_id', Integer, ForeignKey("db_unique_keywords.id")),
                                         Column('annotation_id', Integer, ForeignKey("db_annotations.id"))
                                         )

UKW_Segment_association_table = Table('ukw_segment_association', Base.metadata,
                                      Column('unique_keyword_id', Integer, ForeignKey("db_unique_keywords.id")),
                                      Column('segment_id', Integer, ForeignKey("db_segments.id"))
                                      )

UKW_Screenshot_association_table = Table('ukw_screenshot_association', Base.metadata,
                                         Column('unique_keyword_id', Integer, ForeignKey("db_unique_keywords.id")),
                                         Column('screenshots_id', Integer, ForeignKey("db_screenshots.id"))
                                         )

Subcorpora_project_association_table = Table('subcorpora_project_association', Base.metadata,
                                         Column('project_id', Integer, ForeignKey("db_projects.id")),
                                         Column('subcorpora_id', Integer, ForeignKey("db_sub_corpora.id"))
                                         )

Subcorpora_subscibed_user_association_table = Table('subcorpora_user_association', Base.metadata,
                                                    Column('user_id', Integer, ForeignKey("users.id")),
                                                    Column('subcorpora_id', Integer, ForeignKey("db_sub_corpora.id"))
                                                    )


SemanticSegmentationLabel_clobj_association_table = Table('semseglabel_clobj_association', Base.metadata,
                                                    Column('semantic_segmentation_label_id', Integer, ForeignKey("db_semantic_segmentation_label.id")),
                                                    Column('classification_object_id', Integer, ForeignKey("db_classification_objects.id"))
                                                    )

Segment_distances_association_table = Table('segment_distances_association', Base.metadata,
                                                    Column('segment', Integer, ForeignKey("db_segments.id")),
                                                    Column('segment_dist_metric', Integer, ForeignKey("db_segment_distance.id"))
                                                    )

Genre_association_table = Table('genre_association', Base.metadata,
                                                    Column('movie', Integer, ForeignKey("db_movies.id")),
                                                    Column('genre', Integer, ForeignKey("db_genres.id"))
                                                    )

class Folder(Base):
    __tablename__ = 'folders'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"))
    children = relationship("Folder", cascade="all, delete, delete-orphan")
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="folders")
    saved_vis = relationship("SavedVis", back_populates="folder", cascade="all, delete, delete-orphan")


class SavedVis(Base):
    __tablename__ = 'saved_vis'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey('users.id'))
    folder_id = Column(Integer, ForeignKey('folders.id'))
    project_id = Column(Integer, ForeignKey("db_projects.id"))

    vis_type = Column(String, nullable=False)
    blob = Column(String, nullable=False)

    user = relationship("User", back_populates="saved_vis")
    folder = relationship("Folder", back_populates="saved_vis")

    # project = relationship("DBProject", back_populates="saved_vis")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=False, nullable=False)
    email = Column(String, unique=True, nullable=False)
    affiliation = Column(String)
    password = Column(String, nullable=False)
    sign_up_date = Column(DateTime, nullable=False)
    activated = Column(Boolean)
    privileged = Column(Integer, unique=False, nullable=False, default=0)
    activation_hash = Column(String, nullable=False)

    uploads = relationship("Upload", back_populates="user")
    saved_vis = relationship("SavedVis", back_populates="user")
    folders = relationship("Folder", back_populates="user")
    owned_sub_corporas = relationship("DBSubCorpus", back_populates="owner")
    subscribed_sub_corporas = relationship("DBSubCorpus",
                                           secondary=Subcorpora_subscibed_user_association_table,
                                           back_populates="users")


class Upload(Base):
    __tablename__ = 'uploads'

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    storage_name = Column(String, nullable=False)
    rel_path = Column(String, nullable=False)
    abs_path = Column(String, nullable=False)
    public = Column(Boolean, nullable=False)
    upload_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=True)
    number_of_downloads = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="uploads")
    project = relationship("DBProject", uselist=False, back_populates="upload", cascade="all, delete, delete-orphan")


class DBProject(Base):
    __tablename__ = 'db_projects'

    id = Column(Integer, primary_key=True)

    # FilmColors ID
    corpus_id = Column(Integer, nullable=False)
    manifestation_id = Column(Integer, nullable=False)
    copy_id = Column(Integer, nullable=False)

    #  this is currently not constrained in VIAN, since it is not given that all movies have an iMDBID
    upload_id = Column(Integer, ForeignKey('uploads.id'))

    download_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    upload = relationship("Upload", back_populates="project", single_parent=True, cascade="all, delete, delete-orphan")
    segments = relationship("DBSegment", back_populates="project", cascade="all, delete, delete-orphan")
    annotations = relationship("DBAnnotation", back_populates="project", cascade="all, delete, delete-orphan")
    screenshots = relationship("DBScreenshot", back_populates="project", cascade="all, delete, delete-orphan")
    screenshot_analyses = relationship("DBScreenshotAnalysis", back_populates="project", cascade="all, delete, delete-orphan")
    segment_analyses = relationship("DBSegmentAnalysis", back_populates="project", cascade="all, delete, delete-orphan")
    annotation_analyses = relationship("DBAnnotationAnalysis", back_populates="project", cascade="all, delete, delete-orphan")
    movie = relationship("DBMovie", back_populates="project", uselist=False, cascade="all, delete, delete-orphan")
    # saved_vis = relationship("SavedVis", back_populates="project", cascade="all, delete, delete-orphan")
    sub_corporas = relationship("DBSubCorpus", secondary=Subcorpora_project_association_table, back_populates="projects")


    def from_project(self, project, thumbnail_path = "", download_path = "", upload_id=-1):
        if isinstance(project['movie_descriptor']['movie_id'], list):
            project['movie_descriptor']['movie_id'] = "_".join(project['movie_descriptor']['movie_id'])

        splitted_id = project['movie_descriptor']['movie_id'].split("_")
        self.corpus_id = splitted_id[0]
        self.manifestation_id = splitted_id[1]
        self.copy_id = splitted_id[2]

        self.download_path = download_path
        self.thumbnail_path = thumbnail_path
        self.upload_id = upload_id
        return self


class DBMovie(Base):
    __tablename__ = "db_movies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    source = Column(String)
    duration = Column(Integer, nullable=False)
    # fps = Column(Integer, nullable=False)
    project_id = Column(Integer, ForeignKey("db_projects.id"))

    imdb_id = Column(String, nullable=True)
    color_process = Column(String)
    director = Column(String)
    cinematography = Column(String)
    color_consultant = Column(String)
    production_design = Column(String)
    art_director = Column(String)
    costum_design = Column(String)
    production_company = Column(String)
    country = Column(String)
    year = Column(Integer)

    annotations = relationship("DBAnnotation", back_populates="movie")
    screenshots = relationship("DBScreenshot", back_populates="movie")
    project = relationship("DBProject", back_populates="movie", uselist = False)
    genres = relationship("DBGenre", secondary=Genre_association_table, back_populates="movies")

    vocabulary_images = relationship("DBConceptImage", back_populates="movie")

    def from_project(self, m, project_id):
        if m['meta_data'] is not None and "ERC_FilmColorsFilmography" in m['meta_data'].keys():
            for attr, val in m['meta_data']['ERC_FilmColorsFilmography'].items():
                if attr == "id":
                    continue
                setattr(self, attr, val)
        self.name = m['movie_name']
        self.source = m['source']
        # self.fps = m['fps']
        self.duration = m['duration']
        self.project_id = project_id
        return self


class DBGenre(Base):
    __tablename__ = "db_genres"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    movies = relationship("DBMovie", secondary=Genre_association_table, back_populates="genres")


class DBAnnotationLayer(Base):
    __tablename__ = "db_annotation_layers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    annotations = relationship("DBAnnotation", back_populates="annotation_layer")

    def from_project(self, l):
        self.name = l['name']
        return self


class DBSegmentation(Base):
    __tablename__ = "db_segmentations"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    segments = relationship("DBSegment", back_populates="segmentation")

    def from_project(self, s):
        self.name = s['name']
        return self


class DBSegment(Base):
    __tablename__ = "db_segments"
    id = Column(Integer, primary_key=True)
    movie_segm_id = Column(Integer)
    start_ms = Column(Integer)
    end_ms = Column(Integer)
    duration_ms = Column(Integer)
    body = Column(String)

    project_id = Column(Integer, ForeignKey('db_projects.id'))
    segmentation_id = Column(Integer, ForeignKey('db_segmentations.id'))

    project = relationship("DBProject", back_populates="segments")
    segmentation = relationship("DBSegmentation", back_populates="segments")
    analyses = relationship("DBSegmentAnalysis",back_populates="segment")
    screenshots = relationship("DBScreenshot", back_populates="segment")

    vocabulary_images = relationship("DBConceptImage", back_populates="segment")

    unique_keywords = relationship("DBUniqueKeyword",
                                   secondary=UKW_Segment_association_table,
                                   back_populates="segments"
                                   )

    segment_dists = relationship("DBSegmentDistanceMetric",
                            secondary=Segment_distances_association_table,
                            back_populates="segments")


    def from_project(self, s, project_id, segmentation_id):
        self.segmentation_id = segmentation_id
        self.project_id = project_id

        self.movie_segm_id = s['scene_id']
        self.start_ms = s['start']
        self.end_ms = s['end']
        self.duration_ms = s['end'] - s['start']
        self.body = s['annotation_body']
        return self


class DBAnnotation(Base):
    __tablename__ = "db_annotations"
    id = Column(Integer, primary_key=True)

    type = Column(Integer, nullable=False)

    position = Column(JSONEncodedDict)
    size = Column(JSONEncodedDict)
    text = Column(String)

    project_id = Column(Integer, ForeignKey('db_projects.id'))
    movie_id = Column(Integer, ForeignKey('db_movies.id'))
    annotation_layer_id = Column(Integer, ForeignKey('db_annotation_layers.id'))

    project = relationship("DBProject", back_populates="annotations")
    movie = relationship("DBMovie", back_populates="annotations")
    annotation_layer = relationship("DBAnnotationLayer", back_populates="annotations")
    analyses = relationship("DBAnnotationAnalysis", back_populates="annotation")

    unique_keywords = relationship(
        "DBUniqueKeyword",
        secondary=UKW_Annotation_association_table,
        back_populates="annotations"
    )

    def from_project(self, project_id, a, movie_id, annotation_layer_id):
        self.project_id = project_id

        self.movie_id = movie_id
        self.annotation_layer_id = annotation_layer_id

        self.type = a['a_type']
        self.position = Point(a['orig_position'][0], a['orig_position'][1])
        self.size = Point(a['size'][0], a['size'][1])
        self.text = a['text']
        return self


class DBScreenshotGroup(Base):
    __tablename__ = "db_screenshot_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    screenshots = relationship("DBScreenshot", back_populates="screenshot_group")

    def from_project(self, obj):
        self.name = obj['name']
        return self


class DBScreenshot(Base):
    __tablename__ = "db_screenshots"
    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    time_ms = Column(Integer, nullable=False)
    frame_width = Column(Integer, nullable=False)
    frame_height = Column(Integer, nullable=False)

    movie_id = Column(Integer, ForeignKey("db_movies.id"))
    segment_id = Column(Integer, ForeignKey("db_segments.id"))

    project_id = Column(Integer, ForeignKey("db_projects.id"))

    screenshot_group_id = Column(Integer, ForeignKey("db_screenshot_groups.id"))

    movie = relationship("DBMovie", back_populates="screenshots")
    segment = relationship("DBSegment", back_populates="screenshots")
    project = relationship("DBProject", back_populates="screenshots")
    screenshot_group = relationship("DBScreenshotGroup", back_populates="screenshots")
    analyses = relationship("DBScreenshotAnalysis", back_populates="screenshot")
    masks = relationship("DBMask", back_populates="screenshot")

    unique_keywords = relationship("DBUniqueKeyword",
                                   secondary=UKW_Screenshot_association_table,
                                   back_populates="screenshots")

    def from_project(self, s, project_id, movie_id, screenshot_group_id, filepath, segment_id, width, height):
        self.movie_id = movie_id
        self.project_id = project_id
        self.segment_id = segment_id
        self.screenshot_group_id = screenshot_group_id

        self.time_ms = s['movie_timestamp']
        self.file_path = filepath
        self.frame_height = height
        self.frame_width = width

        return self


class DBClassificationObject(Base):
    __tablename__ = "db_classification_objects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    experiment_id = Column(Integer, ForeignKey('db_experiments.id'))

    experiment = relationship("DBExperiment", back_populates="classification_objects")
    unique_keywords = relationship("DBUniqueKeyword", back_populates="classification_object")
    screenshot_analyses = relationship("DBScreenshotAnalysis", back_populates="classification_object")
    segment_analyses = relationship("DBSegmentAnalysis", back_populates="classification_object")
    annotation_analyses = relationship("DBAnnotationAnalysis", back_populates="classification_object")

    semantic_segmentation_labels = relationship("DBSemanticSegmentationLabel",
                                                secondary=SemanticSegmentationLabel_clobj_association_table,
                                                back_populates="classification_objects"
                                                )

    def from_project(self, obj, experiment_id, semantic_segmentation_labels):
        self.name = obj['name']
        self.experiment_id = experiment_id
        self.semantic_segmentation_labels = semantic_segmentation_labels
        return self


class DBVocabularyCategory(Base):
    __tablename__ = "db_vocabulary_category"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    vocabularies = relationship("DBVocabulary", back_populates="vocabulary_category")

    def from_project(self, obj):
        self.name = obj['category']
        return self


class DBVocabulary(Base):
    __tablename__ = "db_vocabularies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    vocabulary_category_id = Column(Integer, ForeignKey('db_vocabulary_category.id'))
    vocabulary_words = relationship("DBVocabularyWord", back_populates="vocabulary")
    vocabulary_category = relationship("DBVocabularyCategory", back_populates="vocabularies")

    def from_project(self, obj):
        self.name = obj['name']
        return self


class DBVocabularyWord(Base):
    __tablename__ = "db_vocabulary_words"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    vocabulary_id = Column(Integer, ForeignKey('db_vocabularies.id'))

    vocabulary_category = relationship("DBVocabulary", back_populates="vocabulary_words")
    unique_keywords = relationship("DBUniqueKeyword", back_populates="word")
    vocabulary = relationship("DBVocabulary", back_populates="vocabulary_words")

    def from_project(self, obj, vocabulary_id):
        self.vocabulary_id = vocabulary_id
        self.name = obj['name']
        return self

class DBConceptDescription(Base):
    __tablename__ = "db_concept_description"

    id = Column(Integer, primary_key=True)
    description = Column(String)

    images = relationship("DBConceptImage", back_populates="concept_description")

    keyword_id = Column(Integer, ForeignKey('db_unique_keywords.id'))
    keyword = relationship("DBUniqueKeyword", back_populates="concept_description")


class DBConceptImage(Base):
    __tablename__ = "db_concept_images"

    id = Column(Integer, primary_key=True)
    image_path = Column(String, nullable=False)
    description = Column(String)

    concept_description_id = Column(Integer, ForeignKey('db_concept_description.id'))
    concept_description = relationship("DBConceptDescription", back_populates="images")

    movie_id = Column(Integer, ForeignKey('db_movies.id'))
    movie = relationship("DBMovie", back_populates="vocabulary_images")

    segment_id = Column(Integer, ForeignKey('db_segments.id'))
    segment = relationship("DBSegment", back_populates="vocabulary_images")

class DBUniqueKeyword(Base):
    __tablename__ = "db_unique_keywords"
    id = Column(Integer, primary_key=True)

    arrangement_group = Column(Integer)
    complexity_level = Column(Integer)

    word_id = Column(Integer, ForeignKey("db_vocabulary_words.id"))
    classification_obj_id = Column(Integer, ForeignKey("db_classification_objects.id"))

    word = relationship("DBVocabularyWord", back_populates="unique_keywords")
    classification_object = relationship("DBClassificationObject", back_populates="unique_keywords")

    concept_description = relationship("DBConceptDescription", back_populates="keyword")

    annotations = relationship("DBAnnotation",
                               secondary=UKW_Annotation_association_table,
                               back_populates="unique_keywords")

    segments = relationship("DBSegment",
                                 secondary=UKW_Segment_association_table,
                                 back_populates="unique_keywords")

    screenshots = relationship("DBScreenshot",
                               secondary=UKW_Screenshot_association_table,
                               back_populates="unique_keywords")


    def from_project(self, word_id, class_obj_id):
        self.word_id = word_id
        self.classification_obj_id = class_obj_id
        return self


class DBExperiment(Base):
    __tablename__ = "db_experiments"
    id = Column(Integer, primary_key=True)
    name = Column(String,  nullable=False)
    descriptor_json = Column(String)

    classification_objects = relationship("DBClassificationObject", back_populates="experiment")

    def from_project(self, obj, descriptor_json):
        self.name = obj['name']
        self.descriptor_json = descriptor_json
        return self


class DBScreenshotAnalysis(Base):
    __tablename__ = "db_screenshot_analyses"
    id = Column(Integer, primary_key=True)
    analysis_class_name = Column(String, nullable=False)

    project_id = Column(Integer, ForeignKey("db_projects.id"))
    classification_obj_id = Column(Integer, ForeignKey("db_classification_objects.id"))
    screenshot_id = Column(Integer, ForeignKey("db_screenshots.id"))

    hdf5_dataset = Column(String, nullable=False)
    hdf5_index = Column(Integer, nullable=False)

    project = relationship("DBProject", back_populates="screenshot_analyses")
    classification_object = relationship("DBClassificationObject", back_populates="screenshot_analyses")
    screenshot = relationship("DBScreenshot", back_populates="analyses")

    def from_project(self, obj, project_id, class_obj_id,
                     screenshot_id, hdf5_dataset, hdf5_index):
        self.project_id = project_id
        self.classification_obj_id = class_obj_id
        self.screenshot_id = screenshot_id
        self.hdf5_dataset = hdf5_dataset
        self.hdf5_index = hdf5_index
        self.analysis_class_name = obj['analysis_job_class']

        return self


class DBSegmentAnalysis(Base):
    __tablename__ = "db_segment_analyses"
    id = Column(Integer, primary_key=True)
    analysis_class_name = Column(String, nullable=False)

    project_id = Column(Integer, ForeignKey("db_projects.id"))
    classification_obj_id = Column(Integer, ForeignKey("db_classification_objects.id"))
    segment_id = Column(Integer, ForeignKey("db_segments.id"))

    hdf5_dataset = Column(String, nullable=False)
    hdf5_index = Column(Integer, nullable=False)

    project = relationship("DBProject", back_populates="segment_analyses")
    classification_object = relationship("DBClassificationObject", back_populates="segment_analyses")
    segment = relationship("DBSegment", back_populates="analyses")

    def from_project(self, obj, project_id, class_obj_id,
                     segment_id, hdf5_dataset, hdf5_index):
        self.project_id = project_id
        self.classification_obj_id = class_obj_id
        self.segment_id = segment_id
        self.hdf5_dataset = hdf5_dataset
        self.hdf5_index = hdf5_index
        self.analysis_class_name = obj['analysis_job_class']

        return self


class DBAnnotationAnalysis(Base):
    __tablename__ = "db_annotation_analyses"
    id = Column(Integer, primary_key=True)
    analysis_class_name = Column(String, nullable=False)

    project_id = Column(Integer, ForeignKey("db_projects.id"))
    classification_obj_id = Column(Integer, ForeignKey("db_classification_objects.id"))
    annotation_id = Column(Integer, ForeignKey("db_annotations.id"))

    hdf5_dataset = Column(String, nullable=False)
    hdf5_index = Column(Integer, nullable=False)

    project = relationship("DBProject", back_populates="annotation_analyses")
    classification_object = relationship("DBClassificationObject", back_populates="annotation_analyses")
    annotation = relationship("DBAnnotation", back_populates="analyses")

    def from_project(self, obj, project_id, class_obj_id,
                     annotation_id, hdf5_dataset, hdf5_index):
        self.project_id = project_id
        self.classification_obj_id = class_obj_id
        self.annotation_id = annotation_id
        self.hdf5_dataset = hdf5_dataset
        self.hdf5_index = hdf5_index
        self.analysis_class_name = obj['analysis_job_class']

        return self


class DBVIANVersion(Base):
    __tablename__ = "db_vian_versions"
    id = Column(Integer, primary_key=True)
    version_a = Column(Integer, nullable=False)
    version_b = Column(Integer, nullable=False)
    version_c = Column(Integer, nullable=False)
    upload_date = Column(DateTime, nullable=False)
    download_path = Column(String, nullable=False)

    def __str__(self):
        return "_".join(list(map(str, [self.version_a,self.version_b, self.version_c])))


class DBSubCorpus(Base):
    __tablename__ = "db_sub_corpora"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    owner = relationship("User",  back_populates="owned_sub_corporas")
    owner_id = Column(Integer, ForeignKey("users.id"))
    users = relationship("User",
                         secondary=Subcorpora_subscibed_user_association_table,
                         back_populates="subscribed_sub_corporas", cascade="all, delete")
    projects = relationship("DBProject",
                            secondary=Subcorpora_project_association_table,
                            back_populates="sub_corporas", cascade="all, delete")


class DBSegmentDistanceMetric(Base):
    __tablename__ = "db_segment_distance"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    value = Column(Float, nullable=False)

    segments = relationship("DBSegment",
                            secondary=Segment_distances_association_table,
                            back_populates="segment_dists",
                            cascade="all")

#region -- SemanticSegmentation --

class DBMask(Base):
    __tablename__ = "db_masks"
    id = Column(Integer, primary_key=True)
    mask_path = Column(String, nullable=False)
    screenshot_id = Column(Integer, ForeignKey("db_screenshots.id"))
    dataset_id = Column(Integer, ForeignKey("db_semantic_segmentation_ds.id"))

    dataset = relationship("DBSemanticSegmentationDataset", back_populates="masks")
    screenshot = relationship("DBScreenshot", back_populates ="masks")

    def from_project(self, screenshot_id = -1, mask_path = "", dataset = ""):
        self.mask_path = mask_path
        self.screenshot_id = screenshot_id
        self.dataset = dataset
        return self


class DBSemanticSegmentationDataset(Base):
    __tablename__ = "db_semantic_segmentation_ds"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    labels = relationship("DBSemanticSegmentationLabel", back_populates="dataset")
    masks = relationship("DBMask", back_populates="dataset")


class DBSemanticSegmentationLabel(Base):
    __tablename__ = "db_semantic_segmentation_label"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    mask_idx = Column(Integer, nullable=False)
    dataset_id = Column(Integer, ForeignKey('db_semantic_segmentation_ds.id'))

    dataset = relationship("DBSemanticSegmentationDataset", back_populates="labels")
    classification_objects = relationship("DBClassificationObject",
                                          secondary=SemanticSegmentationLabel_clobj_association_table,
                                          back_populates="semantic_segmentation_labels")

#endregion








