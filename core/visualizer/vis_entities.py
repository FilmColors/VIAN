import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject


class VisScreenshot(QObject):
    onImageChanged = pyqtSignal(object)
    onFeatureChanged = pyqtSignal(object)
    onPaletteChanged = pyqtSignal(object)

    def __init__(self, dbscreenshot, features):
        super(VisScreenshot, self).__init__()
        self.dbscreenshot = dbscreenshot
        self.path = dbscreenshot.file_path
        self.image_cache = dict()
        if len(dbscreenshot.masks) > 0:
            self.mask = dbscreenshot.masks[0]
        else:
            self.mask = None
        self.current_image = np.zeros(shape=(50,35,3), dtype=np.uint8)
        self.features = features
        self.current_feature = None
        self.palettes = dict()
        self.current_palette = None
        self.year_x = 0

    def set_current_clobj_index(self, idx):
        if idx in self.image_cache and idx in self.features:
            self.current_image = self.image_cache[idx]
            self.current_feature = self.features[idx]
            self.onImageChanged.emit(self.current_image)
            self.onFeatureChanged.emit(self.features[idx])

        if idx in self.palettes:
            self.current_palette = self.palettes[idx]
            self.onPaletteChanged.emit(self.current_palette)
        else:
            self.current_palette = None



