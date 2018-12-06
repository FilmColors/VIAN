from PyQt5.QtCore import *
from visualizer2.data.vis_container import VisScreenshot
from core.corpus.client.corpus_interfaces import *
from core.data.computation import apply_mask

class ScreenshotWorkerSignals(QObject):
    onScreenshotLoaded = pyqtSignal(object)


CORPUS_PATH = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"
class ScreenshotWorker(QObject):
    def __init__(self, visualizer, root = None):
        super(ScreenshotWorker, self).__init__()
        self.signals = ScreenshotWorkerSignals()
        self.project = None
        self.visualizer = visualizer

        self.active = True
        self.wait = True
        self.db_root = root
        self.aborted = False

    def initialize(self, db_root):
        self.db_root = db_root
        print(self.db_root)

    @pyqtSlot(object, object, int)
    def on_load_screenshots(self, scrs:List[VisScreenshot], clobj_labels, current_cl_obj_id):
        print("Loading Shots...")
        for i, s in enumerate(scrs):
            if self.aborted:
                break
            if os.path.isfile(self.db_root + "/shots/" + s.dbscreenshot.file_path):
                img = cv2.imread(self.db_root + "/shots/" + s.dbscreenshot.file_path, cv2.IMREAD_UNCHANGED).astype(np.uint8)
                if img.shape[1] > self.visualizer.MAX_WIDTH:
                    d = self.visualizer.MAX_WIDTH / img.shape[1]
                    img = cv2.resize(img, None, None, d, d, cv2.INTER_CUBIC)

                if s.mask is not None:
                    mask = cv2.imread(self.db_root + "/masks/" + s.mask.mask_path, cv2.IMREAD_GRAYSCALE)
                    for clobj in clobj_labels:
                        s.image_cache[clobj[0]] = numpy_to_pixmap(apply_mask(img, mask, clobj[1]))

                    s.current_image = s.image_cache[current_cl_obj_id]
                else:
                    s.current_image = numpy_to_pixmap(img)

                s.onImageChanged.emit(s.current_image)
        self.aborted = False

    @pyqtSlot()
    def abort(self):
        self.aborted = True