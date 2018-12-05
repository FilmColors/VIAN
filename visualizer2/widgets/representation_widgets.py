from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
import cv2
from core.gui.ewidgetbase import EGraphicsView
from core.data.computation import *
from core.corpus.shared.sqlalchemy_entities import *


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

    def add_entry(self, dbproject:DBProject):
        entry = ProjectListEntry(self.inner, self.visualizer, dbproject)
        self.inner.layout().addWidget(entry)
        self.entries.append(entry)
        if self.end_spacer is not None:
            self.inner.layout().removeItem(self.end_spacer)
        self.end_spacer = QSpacerItem(10,10,QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.inner.layout().addItem(self.end_spacer)
        entry.show()



class ProjectListEntry(QWidget):
    onClicked = pyqtSignal(object)

    def __init__(self, parent, visualizer, dbproject:DBProject, connect_slot = True, filmography = None):
        super(ProjectListEntry, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/ContributionEntry.ui")
        uic.loadUi(path, self)
        self.visualizer = visualizer
        self.setStyleSheet("QWidget{background:transparent;}")
        self.hovered = False
        self.lbl_ProjectName.setText(dbproject.movie.name)

        if filmography is not None:
            self.lbl_Country.setText(dbproject.movie.country)
            self.lbl_ColorProcess.setText(dbproject.movie.color_process)
        else:
            self.lbl_Country.setText("")
            self.lbl_ColorProcess.setText("")

        self.dbproject = dbproject
        self.lbl_Year.setText(str(dbproject.upload.upload_date))

        if connect_slot:
            self.onClicked.connect(self.visualizer.on_project_selected)

        img = cv2.imread(self.dbproject.thumbnail_path)

        self.image_preview = EGraphicsView(self.widget)
        self.widget.layout().addWidget(self.image_preview)
        if img is not None:
            self.image_preview.set_image(numpy_to_pixmap(img))



    def mousePressEvent(self, a0: QMouseEvent):
        self.onClicked.emit(self.dbproject)

    def enterEvent(self, a0: QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QEvent):
        self.hovered = False

    def paintEvent(self, a0: QPaintEvent):
        if self.hovered:
            qp = QPainter()
            pen = QPen()

            qp.begin(self)
            pen.setColor(QColor(255, 160, 47, 100))
            qp.setPen(pen)
            qp.fillRect(self.rect(), QColor(255, 160, 47, 50))
            qp.drawRect(self.rect())

            qp.end()