from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from core.visualization.image_plots import *
from core.gui.ewidgetbase import ExpandableWidget
class PlotWidget(QDockWidget):
    def __init__(self, parent, plot, name = "no name"):
        super(PlotWidget, self).__init__(parent)
        self.plot = plot
        self.name = name
        self.widget = QWidget(self)
        self.widget.setLayout(QVBoxLayout())
        self.setWidget(self.widget)
        self.widget.layout().addWidget(plot)
        self.widget.layout().addWidget(ExpandableWidget(self, "Plot Controls", plot.get_param_widget()))
        self.show()


class PlotResultsWidget(QMainWindow):
    def __init__(self, parent):
        super(PlotResultsWidget, self).__init__(parent)
        self.plots = dict()

    def add_plot(self, p:PlotWidget):
        self.addDockWidget(Qt.RightDockWidgetArea, p, Qt.Horizontal)
        self.plots[p.name] = p

    def remove_plot(self, p):
        if p.name in self.plots:
            self.plots.pop(p)
        p.close()

