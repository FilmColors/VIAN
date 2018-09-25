from PyQt5.QtCore import *
from core.corpus.shared.entities import *
from core.corpus.client.corpus_interfaces import *

class ScreenshotWorkerSignals(QObject):
    onScreenshotLoaded = pyqtSignal(object)


CORPUS_PATH = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"
class ScreenshotWorker(QObject):
    def __init__(self, visualizer):
        super(ScreenshotWorker, self).__init__()
        self.signals = ScreenshotWorkerSignals()
        self.project = None
        self.visualizer = visualizer

        self.active = True
        self.wait = True
        self.db_root = None
        self.aborted = False

    def initialize(self, db_root):
        self.db_root = db_root

    @pyqtSlot(object)
    def on_load_screenshots(self, dbscreenshots:List[DBScreenshot]):
        dbscreenshots = sample(dbscreenshots, self.visualizer.K_IMAGES)
        for s in dbscreenshots:
            if self.aborted:
                break
            if os.path.isfile(self.db_root + s.file_path):
                img = cv2.imread(self.db_root + s.file_path, cv2.IMREAD_UNCHANGED).astype(np.uint8)
                if img.shape[1] > self.visualizer.MAX_WIDTH:
                    d = self.visualizer.MAX_WIDTH / img.shape[1]
                    img = cv2.resize(img, None, None, d, d, cv2.INTER_CUBIC)
                self.signals.onScreenshotLoaded.emit(dict(screenshot_id = s.screenshot_id, image=img))
        try:
            self.signals.onScreenshotLoaded.disconnect()
        except:
            pass
        self.aborted = False

    @pyqtSlot()
    def abort(self):
        self.aborted = True