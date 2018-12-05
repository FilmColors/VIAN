from PyQt5.QtCore import *
from core.corpus.shared.corpus import VIANCorpus
from core.corpus.shared.sqlalchemy_entities import *
from enum import Enum
import os

class QueryType(Enum):
    Segment = 0
    Segments = 1
    Project = 2
    Projects = 4
    Keywords = 4

class QueryWorkerSignals(QObject):
    onQueryResult = pyqtSignal(object)
    onMessage = pyqtSignal(str)
    onStartQuery = pyqtSignal(str)
    onSegmentsQueryResult = pyqtSignal(object)
    onKeywordsQueryResult = pyqtSignal(object)
    onProjectsQueryResult = pyqtSignal(object)
    onCorpusQueryResult = pyqtSignal(object, object) #type: List[DBProjects], List[DBUniuqeKeywords]
    onProjectQueryResult = pyqtSignal(object)
    onFinishedQuery = pyqtSignal(str)


CORPUS_PATH = "F:\\_corpus\\ERCFilmColors_V2\\database2_after_g.db"
# CORPUS_PATH = "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\MyCorpusTesting\\MyCorpusTesting.vian_corpus"
class QueryWorker(QObject):
    def __init__(self, path, user = None):
        super(QueryWorker, self).__init__()
        self.signals = QueryWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True
        self.corpus = VIANCorpus(path)
        self.user = user
        self.root = os.path.split(path)[0]
        self.path = path
        self.initialized = False

    def initialize(self):
        self.corpus.onQueryResult.connect(self.on_query_result)

    def on_query_keywords(self):
        return self.corpus.db.query(DBUniqueKeyword).all()

    def on_corpus_info(self):
        self.signals.onCorpusQueryResult.emit(self.corpus.db.query(DBProject).all(), self.corpus.db.query(DBUniqueKeyword).all())

    def on_project_query(self, project:DBProject):
        pass


    def on_query_segments(self, include_kwds = None, exclude_kwds = None):
        excluded_subquery = self.corpus.db.query(DBSegment.id) \
            .filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(exclude_kwds))).subquery()

        segments = self.corpus.db.query(DBSegment) \
            .filter(DBSegment.unique_keywords.any(DBUniqueKeyword.id.in_(include_kwds))) \
            .filter(DBSegment.id.notin_(excluded_subquery)) \
            .all()
        return segments

    @pyqtSlot(str, object)
    def on_query(self, query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters, shot_id):
        self.signals.onStartQuery.emit(query_type)
        # if self.user is None:

    @pyqtSlot(object)
    def on_query_result(self, result):
        self.signals.onFinishedQuery.emit("Done")
        if result is None: return
        self.signals.onQueryResult.emit(result)


if __name__ == '__main__':
    worker = QueryWorker("F:/_corpus/ERCFilmColors_V2/database2_after_g.db")
    print(worker.on_query_keywords())
    print(len(worker.on_query_segments(list(range(1000)), include_kwds=list(range(100)), exclude_kwds=list(range(100, 120)))))

