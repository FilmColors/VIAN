from tensorflow.keras.callbacks import Callback
from PyQt5.QtCore import QObject, pyqtSignal

class VIANKerasCallback(QObject, Callback):
    onCallback = pyqtSignal(object)

    def __init__(self):
        super(VIANKerasCallback, self).__init__()

    def on_epoch_end(self, epoch, logs=None):
        self.onCallback.emit(epoch)
