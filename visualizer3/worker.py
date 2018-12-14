from PyQt5.QtCore import *
from core.corpus.shared.corpus import VIANCorpus
from core.corpus.shared.sqlalchemy_entities import *
from enum import Enum
import os
from random import shuffle
from visualizer3.vis_entities import VisScreenshot
import random

class QueryType(Enum):
    Segment = 0
    Segments = 1
    Project = 2
    Projects = 4
    Keywords = 4

class QueryWorkerSignals(QObject):
    onSegmentQueryResult = pyqtSignal(object, object)
    onMovieQueryResult = pyqtSignal(object)
    onCorpusQueryResult = pyqtSignal(object, object, object, object, object)  # type: List[DBProjects], List[DBUniuqeKeywords], List[DBClassificationObject]
    onProgress = pyqtSignal(float)
CORPUS_PATH = "F:\\_corpus\\ERCFilmColors_V2\\database.db"
# CORPUS_PATH = "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\MyCorpusTesting\\MyCorpusTesting.vian_corpus"

class QueryWorker(QObject):
    def __init__(self, path, user = None):
        super(QueryWorker, self).__init__()
        self.signals = QueryWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True
        self.corpus = None
        self.user = user
        self.root = os.path.split(path)[0]
        self.path = path
        self.initialized = False

    def initialize(self):
        self.corpus.onQueryResult.connect(self.on_query_result)

    def load(self, path, root):
        self.corpus = VIANCorpus(path)
        self.root = root

    def on_query_keywords(self):
        return self.corpus.db.query(DBUniqueKeyword).all()

    def on_corpus_info(self):
        for k, v in self.generate_filmography_autofill().items():
            print(k, v)
        self.signals.onCorpusQueryResult.emit(self.generate_filmography_autofill(),
                                              self.corpus.db.query(DBProject).all(),
                                              self.corpus.db.query(DBUniqueKeyword).all(),
                                              self.corpus.db.query(DBClassificationObject).all(),
                                              self.corpus.db.query(DBSubCorpus).all())

    def on_project_query(self, project:DBProject):
        pass


    def generate_filmography_autofill(self):
        movies = self.corpus.db.query(DBMovie).all()
        result=dict(
            imdb_id = [],
            color_process = [],
            cinematography = [],
            color_consultant = [],
            production_design = [],
            art_director = [],
            costum_design = [],
            production_company = [],
            country = []
        )
        for m in movies:
            for k in result.keys():
                val = getattr(m, k)
                if val not in result[k]:
                    result[k].append(val)
        print(result)
        return result

    @pyqtSlot(object, object, object, int, object)
    def on_query_segments(self, include_kwds = None, exclude_kwds = None, subcorpora = None, n = 400, filmography:FilmographyQuery = None):
        excluded_subquery = self.corpus.db.query(DBSegment.id) \
            .filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(exclude_kwds))).subquery()

        print("Query SQL")

        q = self.corpus.db.query(DBSubCorpus, DBProject, DBMovie, DBSegment, DBScreenshot, DBScreenshotAnalysis)
        if subcorpora is not None:
            q = q.filter(DBSubCorpus.id == subcorpora.id)
        if include_kwds is not None and len(include_kwds) > 0:
            q = q.filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(include_kwds)))
        if filmography is not None:
            if filmography.color_process is not None:
                q = q.filter(DBMovie.color_process.in_(filmography.color_process))
            if filmography.imdb_id is not None:
                q = q.filter(DBMovie.imdb_id.in_(filmography.imdb_id))
            if filmography.cinematography is not None:
                q = q.filter(DBMovie.cinematography.in_(filmography.cinematography))
            if filmography.country is not None:
                q = q.filter(DBMovie.country.in_(filmography.country))
            if filmography.color_consultant is not None:
                q = q.filter(DBMovie.color_consultant.in_(filmography.color_consultant))
            if filmography.production_design is not None:
                q = q.filter(DBMovie.production_design.in_(filmography.production_design))
            if filmography.art_director is not None:
                q = q.filter(DBMovie.art_director.in_(filmography.art_director))
            if filmography.costum_design is not None:
                q = q.filter(DBMovie.costum_design.in_(filmography.costum_design))
            if filmography.production_company is not None:
                q = q.filter(DBMovie.production_company.in_(filmography.production_company))
            if filmography.corpus_id is not None:
                q = q.filter(DBProject.corpus_id == filmography.corpus_id)
            if filmography.manifestation_id is not None:
                q = q.filter(DBProject.manifestation_id == filmography.manifestation_id)
            if filmography.copy_id is not None:
                q = q.filter(DBProject.copy_id == filmography.copy_id)

        res = q.filter(DBScreenshotAnalysis.analysis_class_name == "ColorFeatures")\
                .join(DBSubCorpus.projects) \
                .join(DBMovie)\
                .join(DBSegment)\
                .join(DBScreenshot)\
                .join(DBScreenshotAnalysis)\
                .all()
        segments = []
        scrs = []

        print("Parsing SQL")
        for a, b, c, d, e, f in res:
            scrs.append([e, f])
            segments.append(d)

        segments = list(set(segments))

        screenshots = dict()
        print("Loading Analyses")

        n_attempts = int(n * 2.0)
        c = 0
        if len(scrs) > 0:
            while(len(screenshots.keys()) < n and c < n_attempts):
                idx = random.randint(0, len(scrs) - 1)
                scr_id = scrs[idx][0].id


                # Find start point
                t = idx - 1
                while(t >= 0 and scrs[t][0].id == scr_id):
                    t -= 1

                # Move forward until a new screenshot comes
                idx = t + 1
                to_add = []

                while(idx < len(scrs) and scrs[idx][0].id == scr_id):
                    to_add.append(scrs[idx])
                    idx += 1
                if len(to_add) >= 3:
                    for t in to_add:
                        scr = t[0]
                        analysis = t[1]

                        if scr.id not in screenshots:
                            screenshots[scr.id] = VisScreenshot(scr, dict())

                        screenshots[scr.id].features[analysis.classification_obj_id] = self.corpus.hdf5_manager.features()[
                            analysis.hdf5_index]
                c += 1
                self.signals.onProgress.emit(len(screenshots.keys()) / n)

        self.signals.onProgress.emit(1.0)
        return self.signals.onSegmentQueryResult.emit(segments, screenshots)


    @pyqtSlot(str, object)
    def on_query(self, query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters, shot_id):
        self.signals.onStartQuery.emit(query_type)
        # if self.user is None:

    @pyqtSlot(object)
    def on_query_result(self, result):
        self.signals.onFinishedQuery.emit("Done")
        if result is None: return
        self.signals.onQueryResult.emit(result)

