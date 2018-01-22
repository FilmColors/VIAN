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
        self.current_analysis = None

        self.analysis_widget.setLayout(QHBoxLayout(self))


    def activate_analysis(self, analysis: IAnalysisJobAnalysis):
        self.clear_analysis_widget()
        self.current_analysis = analysis
        self.current_analysis.load_container(self.apply_analysis, sync=True)

    def apply_analysis(self):
        print("TEST, Applying Analysis")
        visualization = self.current_analysis.get_visualization()

        self.current_analysis.unload_container()
        if visualization is not None:
            self.analysis_widget.layout().addWidget(visualization)
            self.current_visualization = visualization
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






