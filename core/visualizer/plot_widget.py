from typing import List
from PyQt5.QtGui import *
from core.corpus.legacy.sqlalchemy_entities import DBSegment
from core.visualization.image_plots import *
from core.visualization.dot_plot import DotPlot
from core.gui.ewidgetbase import ExpandableWidget, EMultiGraphicsView
from core.visualizer.vis_entities import VisScreenshot

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
        print("Exception in Feature Changed", e)
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
        # self.widget.layout().addWidget(ExpandableWidget(self, "Plot Controls", plot.get_param_widget()))
        self.show()
        self.plot.frame_plot()


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

    def add_plots(self, p:List[PlotWidget], classification_objects, scrs, summary_dict, segments):
        name = "_".join([str(summary_dict['filmography']['corpus_id']),
               "_".join(summary_dict['include_kwds_str']),
               "_".join(summary_dict['exclude_kwds_str']),
               str(summary_dict['filmography']['year_start']),
               str(summary_dict['filmography']['year_end']),
               str(summary_dict['n'])])\
            .replace("None", "")\
            .replace("2100", "")\
            .replace("1800", "")\
            .replace("__", "_")\
            .replace("__", "_")

        t = PlotResultsGroupWidget(self, classification_objects, name, scrs, segments)
        self.result_counter += 1

        t.scrs = scrs
        for q in p:
            t.add_plot(q)

        # t.setWindowTitle("Results_" + str(self.result_counter).zfill(2))
        # self.addDockWidget(Qt.RightDockWidgetArea, t, Qt.Vertical)
        self.tab.addTab(t, name)

        self.group_widgets.append(t)
        t.set_summary(summary_dict)
        t.show()

    @pyqtSlot(str, str)
    def on_group_name_changed(self, old, new):
        for i in range(self.tab.count()):
            if self.tab.tabText(i) == old:
                self.tab.setTabText(i, new)
                break


class PlotResultsGroupWidget(QDockWidget):
    def __init__(self, parent, classification_objects, name, screenshots, segments):
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
        self.summary = QuerySummary(self, self.classification_object_selector, name, screenshots, segments)
        self.central.addDockWidget(Qt.TopDockWidgetArea, self.summary)
        self.summary.onGroupNameChanged.connect(parent.on_group_name_changed)

        self.segment_view = SegmentsList(self)

        i = 0
        curr_segment = None
        screenshots = sorted(screenshots.values(), key=lambda x:x.dbscreenshot.segment.id)
        vis_scrs = []
        for s in screenshots: #type:DBSegment
            if s.dbscreenshot.segment != curr_segment:
                if len(vis_scrs) > 0:
                    self.segment_view.add_segment(curr_segment, vis_scrs)
                vis_scrs = []
                curr_segment = s.dbscreenshot.segment
            vis_scrs.append(s)
        self.central.tabifyDockWidget(self.summary, self.segment_view)

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
            for p in self.plots.values():
                p.plot.naming_fields['classification_obj'] = name
                print(p.plot, name)


import json
class QuerySummary(QDockWidget):
    onGroupNameChanged = pyqtSignal(str, str)

    def __init__(self, parent, clobj_widget, name, screenshots, segments):
        super(QuerySummary, self).__init__(parent)
        self.clobj_widget = clobj_widget
        self.setWindowTitle("Summary")
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.setWidget(self.scroll)
        self.inner = QWidget(self.scroll)
        self.scroll.setWidget(self.inner)
        self.inner.setLayout(QVBoxLayout())
        self.name_edit = QLineEdit(name, self)
        self.inner.layout().addWidget(self.name_edit)
        self.old_name = name
        self.text_field_desc = QTextEdit(self)
        self.text_field_raw = QTextEdit(self)
        self.text_field_desc.setReadOnly(True)
        self.text_field_raw.setReadOnly(True)
        self.name_edit.editingFinished.connect(self.on_name_changed)

        self.screenshots = screenshots
        self.segments = segments

        self.inner.layout().addWidget(self.text_field_desc)
        self.inner.layout().addWidget(ExpandableWidget(self, "Classification Objects", self.clobj_widget, True))
        self.inner.layout().addWidget(ExpandableWidget(self, "Raw Query", self.text_field_raw, False))

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


    def on_name_changed(self):
        self.onGroupNameChanged.emit(self.old_name, self.name_edit.text())
        self.old_name = self.name_edit.text()


class SegmentsList(QDockWidget):
    def __init__(self, parent):
        super(SegmentsList, self).__init__(parent)
        self.setWindowTitle("Segment List")
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(QWidget())
        self.setWidget(self.scroll_area)
        self.scroll_area.widget().setLayout(QVBoxLayout(self))
        self.segment_items = dict()

    def add_segment(self, segment, screenshots):
        item = SegmentItem(self, segment, screenshots)
        self.segment_items[segment.id] = item
        self.scroll_area.widget().layout().addWidget(item)


class SegmentItem(QWidget):
    def __init__(self, parent, segment:DBSegment, screenshots:List[VisScreenshot]):
        super(SegmentItem, self).__init__(parent)
        self.setLayout(QHBoxLayout(self))
        self.left = QWidget(self)
        self.left.setMaximumWidth(200)
        self.left.setLayout(QVBoxLayout())
        self.left.layout().addWidget(QLabel("Project ID: " + "_".join([str(segment.project.corpus_id),
                                                                       str(segment.project.manifestation_id),
                                                                       str(segment.project.copy_id)])))
        self.left.layout().addWidget(QLabel("Segment ID: " + str(segment.movie_segm_id)))
        self.left.layout().addWidget(QLabel("MovieName : " + str(segment.project.movie.name)))
        lbl = QLabel("Annotation: " + str(segment.body))
        lbl.setWordWrap(True)
        self.left.layout().addWidget(lbl)
        self.image_view = EMultiGraphicsView(self)
        self.layout().addWidget(self.left)
        self.layout().addWidget(self.image_view)
        self.screenshots = screenshots
        for scr in screenshots:
            self.image_view.add_image(numpy_to_pixmap(scr.current_image), item_id=scr.dbscreenshot.id)
            scr.onImageChanged.connect(self.on_image_changed)

    @pyqtSlot(object)
    def on_image_changed(self, pixmap):
        self.image_view.replace_image(self.sender().dbscreenshot.id, pixmap)


class ControlsWidget(QDockWidget):
    def __init__(self, parent):
        super(ControlsWidget, self).__init__(parent)
        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner.setLayout(QVBoxLayout(self))
        self.scroll_area.setWidget(self.inner)
        self.ctrl_container = QWidget(self.inner)
        self.ctrl_container.setLayout(QVBoxLayout(self.ctrl_container))
        self.placeholder = QWidget()
        self.placeholder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.inner.layout().addWidget(self.ctrl_container)
        self.inner.layout().addWidget(self.placeholder)

        self.setWidget(self.scroll_area)

        self.controls = dict()

    def add_plot(self, p):
        if p.naming_fields['plot_name'] not in self.controls:
            ctrls = p.get_param_widget()
            self.controls[p.naming_fields['plot_name']] = ctrls
            self.ctrl_container.layout().addWidget(ExpandableWidget(self.inner, p.naming_fields['plot_name'], ctrls))
        else:
            p.get_param_widget(w=self.controls[p.naming_fields['plot_name']])

# class PlotSettings:
#     def __init__(self):
#         self.image_ab_plot = dict(
#             range_scale = None,
#             image_scale = None,
#         )
#         self.image_lc_plot = dict(
#             image_scale = None,
#             range_scale = None
#         )
#         self.image_color_dt = dict(
#             image_scale = None,
#             x_scale = None,
#             y_scale = None
#         )
#         self.image_color_dy = dict(
#             image_scale = None,
#             x_scale = None,
#             y_scale = None
#         )
#         self.palette_ab_plot = dict(
#             depth = None
#         )
#         self.dot_plot = dict(
#             range_scale = None,
#             dot_alpha = None,
#             dot_size = None
#         )

