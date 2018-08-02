from PyQt5.QtCore import *
from core.corpus.shared.entities import *
from core.corpus.client.corpus_interfaces import *

class ScreenshotWorkerSignals(QObject):
    onScreenshotLoaded = pyqtSignal(object)


CORPUS_PATH = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"
class ScreenshotWorker(QObject):
    def __init__(self):
        super(ScreenshotWorker, self).__init__()
        self.signals = ScreenshotWorkerSignals()
        self.project = None

        self.active = True
        self.wait = True
        self.db_root = None
        self.aborted = False

    def initialize(self, db_root):
        self.db_root = db_root

    @pyqtSlot(object)
    def on_load_screenshots(self, dbscreenshots:List[DBScreenshot]):
        for s in dbscreenshots:
            if self.aborted:
                break
            if os.path.isfile(self.db_root + s.file_path):
                img = cv2.imread(self.db_root + s.file_path, cv2.IMREAD_UNCHANGED)
                self.signals.onScreenshotLoaded.emit(dict(screenshot_id = s.screenshot_id, image=img))
        self.signals.onScreenshotLoaded.disconnect()
        self.aborted = False

    @pyqtSlot()
    def abort(self):
        self.aborted = True