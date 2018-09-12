from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from core.corpus.shared.entities import *

from visualizer.presentation.presentation_widget import *
from visualizer.widgets.representation_widgets import *

class VisHomeWidget(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisHomeWidget, self).__init__(parent, visualizer, "qt_ui/visualizer/VisStartLayout.ui")
        self.contribution_list = ProjectListWidget(self, visualizer)

        lbl_Contributions = QLabel("Recent Contributions", self)
        lbl_Contributions.setStyleSheet("QLabel{font-size: 30px;}")

        self.vbox_contributions = QVBoxLayout(self)
        self.vbox_contributions.addWidget(lbl_Contributions)
        self.vbox_contributions.addWidget(self.contribution_list)
        self.hbox_Lower.addItem(self.vbox_contributions)

    @pyqtSlot(object)
    def on_query_result(self, obj):
        if obj['type'] == "projects":
            for p in obj['data']['projects'].keys():
                dbproject = obj['data']['projects'][p]
                try:
                    filmography = obj['data']['filmographies'][dbproject.project_id]
                except:
                    filmography = DBFilmographicalData()

                self.contribution_list.add_entry(None, dbproject=dbproject, filmography = filmography)
            self.visualizer.db_root = obj['data']['root']
            self.visualizer.screenshot_loader.initialize(self.visualizer.db_root)










