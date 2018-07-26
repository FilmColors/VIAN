from PyQt5.QtCore import *
from core.corpus.shared.entities import *

class QueryWorkerSignals(QObject):
    onQueryResult = pyqtSignal(object)
    onMessage = pyqtSignal(str)

class QueryWorker(QObject):
    def __init__(self):
        super(QueryWorker, self).__init__()
        self.signals = QueryWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True

    @pyqtSlot(str, object, object, object)
    def on_query(self, query_type, filter_filmography, filter_keywords, filter_classification_objects):
        try:
            QueryRequestData(query_type, filter_filmography, filter_keywords, filter_classification_objects)
        except Exception as e:
            raise e



