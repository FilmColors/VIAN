from PyQt5.QtCore import *
from typing import List
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from core.visualization.image_plots import *
from core.visualization.dot_plot import DotPlot
from core.gui.ewidgetbase import ExpandableWidget

def feature_changed(scr, plot):
    try:
        data = scr.current_feature
        img = scr.current_image
        # img = cv2.imread(self.worker.root + "/shots/" + scr.dbscreenshot.file_path)
        l = data[0]
        tx = scr.dbscreenshot.time_ms
        ty = data[6]
        x = data[1]
        y = data[2]
        c = QColor(data[5], data[4], data[3], 200)

        if isinstance(plot, ImagePlotCircular):
            plot.update_item(scr.dbscreenshot.id, (-x, -y, l))
        elif isinstance(plot, ImagePlotPlane):
            plot.update_item(scr.dbscreenshot.id, (-x, l, y))
        elif isinstance(plot, ImagePlotTime):
            plot.update_item(scr.dbscreenshot.id, (tx, ty))
        elif isinstance(plot, DotPlot):
            if plot.curr_grid == "AB":
                plot.update_item(scr.dbscreenshot.id, x, -y, z=l, col=c)
            else:
                plot.update_item(scr.dbscreenshot.id, -x, l, z=-y, col=c)

    except Exception as e:
        print(e)
        pass


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

class ClassificationObjectSelector(QDockWidget):
    onClassificationObjectChanged = pyqtSignal(str)

    def __init__(self, parent, clobjs = None):
        super(ClassificationObjectSelector, self).__init__(parent)
        self.list = QListWidget()
        self.setWidget(self.list)
        self.cl_objs = dict()
        self.setMaximumWidth(200)
        if clobjs is not None:
            self.set_classification_objects(clobjs)
        self.list.currentItemChanged.connect(self.on_clobject_changed)


    def set_classification_objects(self, objects):
        self.list.clear()
        self.cl_objs = dict()
        for c in sorted(objects.values(), key=lambda x: x.name):
            self.list.addItem(c.name)
            self.cl_objs[c.name] = c.name

    def on_clobject_changed(self):
        self.onClassificationObjectChanged.emit(self.list.currentItem().text())


class PlotResultsWidget(QMainWindow):
    def __init__(self, parent):
        super(PlotResultsWidget, self).__init__(parent)
        self.group_widgets = []
        self.result_counter = 0

    def add_plots(self, p:List[PlotWidget], classification_objects, scrs):
        t = PlotResultsGroupWidget(self, classification_objects)
        self.result_counter += 1
        t.setWindowTitle("Results_" + str(self.result_counter).zfill(2))
        t.scrs = scrs
        for q in p:
            t.add_plot(q)
        self.addDockWidget(Qt.RightDockWidgetArea, t, Qt.Vertical)
        self.group_widgets.append(t)
        t.show()


class PlotResultsGroupWidget(QDockWidget):
    def __init__(self, parent, classification_objects):
        super(PlotResultsGroupWidget, self).__init__(parent)
        self.plots = dict()
        self.classification_objects = classification_objects
        self.classification_object_selector = ClassificationObjectSelector(self, classification_objects)
        self.classification_object_selector.onClassificationObjectChanged.connect(self.on_classification_object_changed)
        self.central = QMainWindow()
        self.setWidget(self.central)
        self.central.addDockWidget(Qt.LeftDockWidgetArea, self.classification_object_selector)
        self.scrs = dict()

    def add_plot(self, p: PlotWidget):
        self.central.addDockWidget(Qt.RightDockWidgetArea, p, Qt.Horizontal)
        self.plots[p.name] = p

    def remove_plot(self, p):
        if p.name in self.plots:
            self.plots.pop(p)
        p.close()

    def on_classification_object_changed(self, name):
        if name in self.classification_objects:
            id_cl = self.classification_objects[name].id
            for s in self.scrs.values():
                s.set_current_clobj_index(id_cl)
