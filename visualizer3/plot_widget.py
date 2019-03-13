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
        ty = data[7]
        x = data[1]
        y = data[2]
        color = QColor(data[5], data[4], data[3], 200)

        if isinstance(plot, ImagePlotCircular):
            plot.update_item(scr.dbscreenshot.id, (-x, -y, l))
        elif isinstance(plot, ImagePlotPlane):
            plot.update_item(scr.dbscreenshot.id, (-x, l, -y))
        elif isinstance(plot, ImagePlotTime):
            plot.update_item(scr.dbscreenshot.id, (tx, ty))
        elif isinstance(plot, DotPlot):
            if plot.curr_grid == "AB":
                plot.update_item(scr.dbscreenshot.id, x, -y, z=l, col=color)
            else:
                plot.update_item(scr.dbscreenshot.id, x, l, z=-y, col=color)
        elif isinstance(plot, ImagePlotYear):
            plot.update_item(scr.dbscreenshot.id, (scr.year_x, ty))

    except Exception as e:
        print(e)
        pass


class PlotWidget(QDockWidget):
    def __init__(self, parent, plot, name = "no name"):
        super(PlotWidget, self).__init__(parent)
        self.plot = plot
        self.name = name
        self.widget = QWidget(self)
        self.setWindowTitle(self.name)
        self.widget.setLayout(QVBoxLayout())
        self.setWidget(self.widget)
        self.widget.layout().addWidget(plot)
        self.widget.layout().addWidget(ExpandableWidget(self, "Plot Controls", plot.get_param_widget()))
        self.show()


class ClassificationObjectSelector(QWidget):
    onClassificationObjectChanged = pyqtSignal(str)

    def __init__(self, parent, clobjs = None):
        super(ClassificationObjectSelector, self).__init__(parent)
        self.list = QListWidget()
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.list)
        self.cl_objs = dict()
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
        self.tab = QTabWidget(self)
        self.setCentralWidget(self.tab)

    def add_plots(self, p:List[PlotWidget], classification_objects, scrs, summary_dict):
        t = PlotResultsGroupWidget(self, classification_objects)
        self.result_counter += 1

        t.scrs = scrs
        for q in p:
            t.add_plot(q)

        # t.setWindowTitle("Results_" + str(self.result_counter).zfill(2))
        # self.addDockWidget(Qt.RightDockWidgetArea, t, Qt.Vertical)
        self.tab.addTab(t, "Results_" + str(self.result_counter).zfill(2))

        self.group_widgets.append(t)
        t.set_summary(summary_dict)
        t.show()


class PlotResultsGroupWidget(QDockWidget):
    def __init__(self, parent, classification_objects):
        super(PlotResultsGroupWidget, self).__init__(parent)
        self.plots = dict()
        self.classification_objects = classification_objects
        self.classification_object_selector = ClassificationObjectSelector(self, classification_objects)
        self.classification_object_selector.onClassificationObjectChanged.connect(self.on_classification_object_changed)
        self.central = QMainWindow()
        t = QWidget()
        t.setFixedSize(1,1)
        self.last_up_plot = None
        self.last_low_plot = None
        self.setWidget(self.central)
        self.central.setCentralWidget(t)
        self.scrs = dict()
        self.summary = QuerySummary(self, self.classification_object_selector)
        self.central.addDockWidget(Qt.TopDockWidgetArea, self.summary)


    def set_summary(self, summary_dict):
        self.summary.set_summary(summary_dict)

    def add_plot(self, p: PlotWidget):
        alignment = Qt.Horizontal
        if isinstance(p.plot, ImagePlotTime) or isinstance(p.plot, ImagePlotYear):
            if self.last_low_plot is not None:
                self.central.tabifyDockWidget(self.last_low_plot, p)
            else:
                self.central.addDockWidget(Qt.BottomDockWidgetArea, p, Qt.Horizontal)
                self.last_low_plot = p
        else:
            if self.last_up_plot is not None:
                self.central.tabifyDockWidget(self.last_up_plot, p)
                self.last_up_plot = None
            else:
                self.central.addDockWidget(Qt.TopDockWidgetArea, p, Qt.Horizontal)
                self.last_up_plot = p

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

            if "Palette-Dot" in self.plots:
                palettes = []
                for scr in self.scrs.values():
                    if id_cl in scr.palettes:
                        if scr.palettes[id_cl] is not None:
                            palettes.append(scr.palettes[id_cl])
                if len(palettes) == 0:
                    return

                self.plots["Palette-Dot"].plot.set_palettes(palettes)

import json
class QuerySummary(QDockWidget):
    def __init__(self, parent, clobj_widget):
        super(QuerySummary, self).__init__(parent)
        self.clobj_widget = clobj_widget
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.setWidget(self.scroll)
        self.inner = QWidget(self.scroll)
        self.scroll.setWidget(self.inner)
        self.inner.setLayout(QVBoxLayout())
        self.inner.layout().addWidget(QLineEdit("Result_01"))
        self.text_field_desc = QTextEdit(self)
        self.text_field_raw = QTextEdit(self)
        self.text_field_desc.setReadOnly(True)
        self.text_field_raw.setReadOnly(True)

        self.inner.layout().addWidget(self.text_field_desc)

        self.inner.layout().addWidget(ExpandableWidget(self, "Classification Objects", self.clobj_widget, True))
        self.inner.layout().addWidget(ExpandableWidget(self, "Raw", self.text_field_raw, True))

        self.inner.layout().addItem(QSpacerItem(0,0, QSizePolicy.Fixed, QSizePolicy.Expanding))


    def set_summary(self, summary):
        description = "Include Keywords:\n"
        for s in summary['include_kwds_str']:
            description += "\t" + s + "\n"

        description += "\nExclude Keywords:\n"
        for s in summary['exclude_kwds_str']:
            description += "\t" + s + "\n"

        description += "\nFilmography:\n"
        for key, attr in summary['filmography'].items():
            if attr is not None:
                description += "\t" + key + "\t" + str(attr) + "\n"

        self.text_field_desc.setText(description)
        self.text_field_raw.setText(json.dumps(summary))

