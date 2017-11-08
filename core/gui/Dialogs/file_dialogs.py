from PyQt5 import QtCore, QtGui, uic, QtWidgets, QtSvg
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal


class EFileDialog(QtWidgets.QFileDialog):
    def __init__(self):
        super(EFileDialog, self).__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.show()



class MultiDirFileDialog(QtWidgets.QFileDialog):
    OnSelectionFinished = pyqtSignal(list)

    def __init__(self, parent):
        super(MultiDirFileDialog, self).__init__(parent)
        self.setOption(self.DontUseNativeDialog, True)
        self.setOption(self.ReadOnly, False)
        self.setFileMode(self.DirectoryOnly)



        for view in self.findChildren((QtWidgets.QListView, QtWidgets.QTreeView)):
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)


    def accept(self):
        self.OnSelectionFinished.emit(self.selectedFiles())
        super(MultiDirFileDialog, self).accept()

