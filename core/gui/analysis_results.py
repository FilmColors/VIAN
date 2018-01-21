from core.gui.ewidgetbase import EDockWidget
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from core.data.containers import IAnalysisJobAnalysis
from core.data.interfaces import IProjectChangeNotify


class AnalysisResultsDock(EDockWidget):
    def __init__(self, main_window):
        super(AnalysisResultsDock, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Analysis Results")


class AnalysisResultsWidget(QWidget, IProjectChangeNotify):
    def __init__(self, parent, main_window):
        super(AnalysisResultsWidget, self).__init__(parent)
        self.main_window = main_window
        self.analysis_widget = QWidget(self)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.analysis_widget)
        self.current_visualization = None

        self.analysis_widget.setLayout(QHBoxLayout(self))


    def activate_analysis(self, analysis):
        self.clear_analysis_widget()
        self.current_visualization = analysis.get_visualization()

    def apply_analysis(self, visualization):
        if self.current_visualization is not None:
            self.analysis_widget.layout().addWidget(self.current_visualization)
            self.current_visualization.show()
        else:
            self.main_window.print_message("Visualization returned None", "Red")

    def clear_analysis_widget(self):
        for c in self.analysis_widget.children():
            if isinstance(c, QWidget):
                c.close()
                c.deleteLater()

    def toggle_fullscreen(self, active):
        pass

    def on_changed(self, project, item):
        pass

    def on_loaded(self, project):
        self.clear_analysis_widget()
        pass

    def on_selected(self, sender, selected):
        if len(selected) > 0:
            if isinstance(selected[0], IAnalysisJobAnalysis):
                self.activate_analysis(selected[0])






