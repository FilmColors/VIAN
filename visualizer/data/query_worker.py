from PyQt5.QtCore import *
from core.corpus.shared.entities import *
from core.corpus.client.corpus_interfaces import *

class QueryWorkerSignals(QObject):
    onQueryResult = pyqtSignal(object)
    onMessage = pyqtSignal(str)
    onStartQuery = pyqtSignal(str)
    onFinishedQuery = pyqtSignal(str)


CORPUS_PATH = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"
# CORPUS_PATH = "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\MyCorpusTesting\\MyCorpusTesting.vian_corpus"
class QueryWorker(QObject):
    def __init__(self, path, user = None):
        super(QueryWorker, self).__init__()
        self.signals = QueryWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True
        self.corpus = LocalCorpusInterface()
        self.root = os.path.split(path)[0]
        self.user = user
        self.path = path
        self.initialized = False

    def initialize(self):
        if self.user is None:
            contributor = DBContributor(name="Dummy",
                                  image_path="qt_ui/images/Blank_woman_placeholder.png",
                                  affiliation="ToyotaCrashTest")
            self.user = contributor

        self.corpus.connect_user(self.user, self.path)
        self.corpus.onQueryResult.connect(self.on_query_result)

    @pyqtSlot(str, object, object, object, object, object, object)
    def on_query(self, query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters, shot_id):
        self.signals.onStartQuery.emit(query_type)
        # if self.user is None:
        if not self.initialized:
            self.initialize()
        try:
            query = QueryRequestData(query_type, filter_filmography, filter_keywords, filter_classification_objects, project_filters, segment_filters, shot_id)
            self.corpus.submit_query(query)
        except Exception as e:
            raise e

    @pyqtSlot(object)
    def on_query_result(self, result):
        self.signals.onFinishedQuery.emit("Done")
        if result is None: return
        self.signals.onQueryResult.emit(result)

