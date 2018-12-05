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

    @pyqtSlot(object, bool)
    def on_load_screenshots(self, dbscreenshots:List[DBScreenshot], by_segment = True):
        # dbscreenshots = self.create_subsample(dbscreenshots, by_segment)
        print("Loading Shots...")
        for i, s in enumerate(dbscreenshots):
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
        except Exception as e:
            print(e)
            pass
        print("Done")
        self.aborted = False

    def create_subsample(self, scrs:List[DBScreenshot], by_segment = True):
        print("N-Shots:", len(scrs))
        samples = dict()
        if by_segment:
            # sort them by segment
            for scr in scrs:
                if scr.segment_id not in samples:
                    samples[scr.segment_id] = []
                samples[scr.segment_id].append(scr)

            samples = [samples[s] for s in samples.keys()]
            n_segments = len(samples)
            if n_segments > 0:
                n_per_segment = int(self.visualizer.K_IMAGES / n_segments)
                result = []
                for smpl in samples:

                    if len(smpl) < n_per_segment:
                        result.extend(smpl)
                    else:
                        n = n_per_segment
                        result.extend(sample(smpl, n))

                print("Shots to load:", len(result))
                return result
            else:
                return scrs
        else:
            k = np.clip(self.visualizer.K_IMAGES, 0, len(scrs))
            result = sample(scrs, k)
            print("Shots to load:", len(result))
            return result


    @pyqtSlot()
    def abort(self):
        self.aborted = True