from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from core.corpus.shared.entities import *


class ProjectListWidget(QScrollArea):
    def __init__(self, parent, visualizer):
        super(ProjectListWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.entries = []
        self.end_spacer = None

        self.inner = QWidget()
        self.inner.setLayout(QVBoxLayout(self))
        self.setWidget(self.inner)
        self.setWidgetResizable(True)

    def add_entry(self, dbcontributor:DBContributor, dbproject:DBProject, filmography:DBFilmographicalData = None):
        entry = ProjectListEntry(self.inner, self.visualizer, dbcontributor, dbproject, filmography = filmography)
        self.inner.layout().addWidget(entry)
        self.entries.append(entry)
        if self.end_spacer is not None:
            self.inner.layout().removeItem(self.end_spacer)
        self.end_spacer = QSpacerItem(10,10,QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.inner.layout().addItem(self.end_spacer)
        entry.show()



class ProjectListEntry(QWidget):
    onClicked = pyqtSignal(object)

    def __init__(self, parent, visualizer, dbcontributor, dbproject, connect_slot = True, filmography:DBFilmographicalData = None):
        super(ProjectListEntry, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/ContributionEntry.ui")
        uic.loadUi(path, self)
        self.visualizer = visualizer
        self.setStyleSheet("QWidget{background:transparent;}")
        self.hovered = False
        self.lbl_ProjectName.setText(dbproject.name)

        if filmography is not None:
            self.lbl_Country.setText(filmography.country)
            self.lbl_ColorProcess.setText(filmography.color_process)
        else:
            self.lbl_Country.setText("")
            self.lbl_ColorProcess.setText("")

        self.dbproject = dbproject
        if dbcontributor is not None:
            self.contributor = dbcontributor
            self.lbl_Contributor.setText(dbcontributor.name + "\"" + dbcontributor.affiliation)
        self.lbl_Year.setText(dbproject.last_modified)

        if connect_slot:
            self.onClicked.connect(self.visualizer.on_project_selected)

        img = cv2.imread(self.dbproject.thumbnail_path)

        self.image_preview = EGraphicsView(self.widget)
        self.widget.layout().addWidget(self.image_preview)
        if img is not None:
            self.image_preview.set_image(numpy_to_pixmap(img))



    def mousePressEvent(self, a0: QtGui.QMouseEvent):
        self.onClicked.emit(self.dbproject)

    def enterEvent(self, a0: QtCore.QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QtCore.QEvent):
        self.hovered = False

    def paintEvent(self, a0: QtGui.QPaintEvent):
        if self.hovered:
            qp = QPainter()
            pen = QPen()

            qp.begin(self)
            pen.setColor(QColor(255, 160, 47, 100))
            qp.setPen(pen)
            qp.fillRect(self.rect(), QColor(255, 160, 47, 50))
            qp.drawRect(self.rect())

            qp.end()