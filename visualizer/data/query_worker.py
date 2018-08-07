from PyQt5.QtCore import *
from core.corpus.shared.entities import *
from core.corpus.client.corpus_interfaces import *

class QueryWorkerSignals(QObject):
    onQueryResult = pyqtSignal(object)
    onMessage = pyqtSignal(str)


CORPUS_PATH = "F:\\_corpus\\Backup\\ERC_FilmColorsCorpus_03\\ERC_FilmColorsCorpus.vian_corpus"
CORPUS_PATH = "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\MyCorpusTesting\\MyCorpusTesting.vian_corpus"
class QueryWorker(QObject):
    def __init__(self, path):
        super(QueryWorker, self).__init__()
        self.signals = QueryWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True
        self.corpus = LocalCorpusInterface()
        self.user = None
        self.path = path

    def initialize(self):
        self.user = DBContributor(name="Gaudenz",
                                  image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg",
                                  affiliation="Nahh")
        self.corpus.connect_user(self.user, self.path)
        self.corpus.onQueryResult.connect(self.on_query_result)


    @pyqtSlot(str, object, object, object, object, object)
    def on_query(self, query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters):
        if self.user is None:
            self.initialize()
        try:
            query = QueryRequestData(query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters)
            self.corpus.submit_query(query)
        except Exception as e:
            raise e

    @pyqtSlot(object)
    def on_query_result(self, result):
        if result is None: return
        self.signals.onQueryResult.emit(result)

