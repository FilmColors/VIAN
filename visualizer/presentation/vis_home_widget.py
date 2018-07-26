from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from core.corpus.shared.entities import *

from visualizer.presentation.presentation_widget import *

class VisHomeWidget(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisHomeWidget, self).__init__(parent, visualizer, "qt_ui/visualizer/VisStartLayout.ui")
        self.contribution_list = ContributionListWidget(self, visualizer)
        self.hbox_Lower.addWidget(self.contribution_list)

    @pyqtSlot(object)
    def on_query_result(self, obj):
        if obj['type'] == "projects":
            for p in obj['data']['projects'].keys():
                dbproject = obj['data']['projects'][p]
                self.contribution_list.add_entry(None, dbproject=dbproject)


class ContributionListWidget(QScrollArea):
    def __init__(self, parent, visualizer):
        super(ContributionListWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.entries = []
        self.end_spacer = None

        self.inner = QWidget()
        self.inner.setLayout(QVBoxLayout(self))
        self.setWidget(self.inner)
        self.setWidgetResizable(True)

    def add_entry(self, dbcontributor:DBContributor, dbproject:DBProject):
        entry = ContributionListEntry(self.inner, self.visualizer, dbcontributor, dbproject)
        self.inner.layout().addWidget(entry)
        self.entries.append(entry)
        if self.end_spacer is not None:
            self.inner.layout().removeItem(self.end_spacer)
        self.end_spacer = QSpacerItem(10,10,QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.inner.layout().addItem(self.end_spacer)
        entry.show()


class ContributionListEntry(QWidget):
    def __init__(self, parent, visualizer, dbcontributor, dbproject):
        super(ContributionListEntry, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/ContributionEntry.ui")
        uic.loadUi(path, self)
        self.visualizer = visualizer
        self.setStyleSheet("QWidget{background:transparent;}")
        self.hovered = False
        self.lbl_ProjectName.setText(dbproject.name)

        self.dbproject = dbproject
        if dbcontributor is not None:
            self.contributor = dbcontributor
            self.lbl_Contributor.setText(dbcontributor.name + "\"" + dbcontributor.affiliation)
        self.lbl_Year.setText(dbproject.last_modified)

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




