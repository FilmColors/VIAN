from PyQt5.QtWidgets import QWidget, QSplitter, QVBoxLayout, QTabWidget
from PyQt5.QtCore import Qt


from core.gui.ewidgetbase import EDockWidget, EditableListWidget
from core.gui.filmography_widget import FilmographyWidget2

class CorpusDockWidget(EDockWidget):
    def __init__(self, main_window):
        super(CorpusDockWidget, self).__init__(main_window, False)
        self.setWindowTitle("Corpus")
        self.w = QSplitter(Qt.Horizontal, self)
        # self.w = QWidget(self)
        # self.w.setLayout(QVBoxLayout(self.w))
        self.list = CorpusList(self.w)

        self.info_widget = QTabWidget(self.w)

        self.general_widget = QWidget()
        self.filmography = FilmographyWidget2(self.w)
        self.w.addWidget(self.list)
        self.w.addWidget(self.info_widget)

        self.info_widget.addTab(self.general_widget, "General")
        self.info_widget.addTab(self.filmography, "Filmography")
        self.setWidget(self.w)



class CorpusList(EditableListWidget):
    def __init__(self, parent):
        super(CorpusList, self).__init__(parent)

