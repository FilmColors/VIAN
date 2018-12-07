from PyQt5.QtCore import *
from core.corpus.shared.corpus import VIANCorpus
from core.corpus.shared.sqlalchemy_entities import *
from enum import Enum
import os
from random import shuffle
from visualizer3.vis_entities import VisScreenshot

class QueryType(Enum):
    Segment = 0
    Segments = 1
    Project = 2
    Projects = 4
    Keywords = 4

class QueryWorkerSignals(QObject):
    onSegmentQueryResult = pyqtSignal(object, object)
    onMovieQueryResult = pyqtSignal(object)
    onCorpusQueryResult = pyqtSignal(object, object, object, object)  # type: List[DBProjects], List[DBUniuqeKeywords], List[DBClassificationObject]
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
        self.signals.onCorpusQueryResult.emit(self.corpus.db.query(DBProject).all(),
                                              self.corpus.db.query(DBUniqueKeyword).all(),
                                              self.corpus.db.query(DBClassificationObject).all(),
                                              self.corpus.db.query(DBSubCorpus).all())

    def on_project_query(self, project:DBProject):
        pass


    def on_query_segments(self, include_kwds = None, exclude_kwds = None, subcorpora = None):
        excluded_subquery = self.corpus.db.query(DBSegment.id) \
            .filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(exclude_kwds))).subquery()

        res = self.corpus.db.query(DBSegment, DBScreenshot, DBScreenshotAnalysis) \
            .filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(include_kwds)))\
            .filter(DBSegment.id.notin_(excluded_subquery))\
            .filter(DBScreenshotAnalysis.analysis_class_name == "ColorFeatures")\
            .join(DBScreenshot)\
            .join(DBScreenshotAnalysis)\
            .all()

        segments = []
        for r in res:
            segments.append(r[0])

        segments = list(set(segments))

        screenshots = dict()
        print("Loading Analyses")
        # shuffle(res)
        n = 1000
        step = int(len(res) / n)
        indices = []
        for i in range(len(n)):
            if i % step == 0:
                indices.extend([i * step, i*step + 1, i+step + 2])

        # for i, (segm, scr, analysis)  in enumerate(res): #type: DBScreenshot
        for i, idx in enumerate(indices):
            self.signals.onProgress.emit(i / 1000 * 3)
            segm, scr, analysis = res[idx]
            if scr.id not in screenshots:
                screenshots[scr.id] = VisScreenshot(scr, dict())
            screenshots[scr.id].features[analysis.classification_obj_id]=self.corpus.hdf5_manager.features()[analysis.hdf5_index]
            if i == 1000:
                break
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

