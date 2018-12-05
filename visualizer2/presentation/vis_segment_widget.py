from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from core.visualization.image_plots import *
from visualizer2.presentation.presentation_widget import *
from visualizer2.widgets.segment_visualization import *
from core.visualization.dot_plot import *
from random import sample

class VisSegmentLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSegmentLayout, self).__init__(parent, visualizer)#, "qt_ui/visualizer/VisSegmentsLayout.ui")
        self.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Horizontal, self)
        self.layout().addWidget(self.vsplit)
        self.left_widget = QSplitter(Qt.Vertical, self)
        self.right_widget = QSplitter(Qt.Vertical, self)

        self.plot_la_space = ImagePlotPlane(self)
        self.plot_ab_space = ImagePlotCircular(self)
        self.plot_la_dot = DotPlot(self)
        self.plot_ab_dot = DotPlot(self)
        self.vis_plot_la_space = VisualizerVisualization(self, self.visualizer, self.plot_la_space, self.plot_la_space.get_param_widget())
        self.vis_plot_ab_space = VisualizerVisualization(self, self.visualizer, self.plot_ab_space, self.plot_ab_space.get_param_widget())
        self.vis_plot_la_dot = VisualizerVisualization(self, self.visualizer, self.plot_la_dot, self.plot_la_dot.get_param_widget())
        self.vis_plot_ab_dot = VisualizerVisualization(self, self.visualizer, self.plot_ab_dot, self.plot_ab_dot.get_param_widget())

        self.segment_view = SegmentVisualization(self, self.visualizer)
        self.right_widget.addWidget(self.segment_view)

        self.classification_object_filter_cbs = [QComboBox(), QComboBox()]
        self.classification_object_filter_indices = dict()
        self.plot_ab_space.set_heads_up_widget(self.classification_object_filter_cbs[0])
        self.classification_object_filter_cbs[0].currentTextChanged.connect(self.on_classification_object_changed)

        self.segment_view.onSegmentSelected.connect(self.on_segments_selected)
        self.plot_la_space.onImageClicked.connect(self.on_images_clicked)
        self.plot_ab_space.onImageClicked.connect(self.on_images_clicked)
        self.segment_view.onSegmentSelected.connect(self.on_segments_selected)
        self.segment_view.onSegmentHovered.connect(self.on_segments_selected)

        self.la_tab = QTabWidget()
        self.ab_tab = QTabWidget()
        self.la_tab.addTab(self.vis_plot_la_dot, "Dot-Plot")
        self.la_tab.addTab(self.vis_plot_la_space, "Image-Plot")

        self.ab_tab.addTab(self.vis_plot_ab_dot, "Dot-Plot")
        self.ab_tab.addTab(self.vis_plot_ab_space, "Image-Plot")

        self.left_widget.addWidget(self.la_tab)
        self.left_widget.addWidget(self.ab_tab)

        self.vsplit.addWidget(self.left_widget)
        self.vsplit.addWidget(self.right_widget)
        self.segment_data = dict()
        self.screenshot_data = dict()
        self.color_features = dict()
        self.db_projects = dict()

        self.is_processing = False
        self.dot_plot_data = dict() #dict by classification object id
        self.processed_results = []

    @pyqtSlot(object)
    def on_screenshot_loaded(self, scr):
        if scr['screenshot_id'] not in self.screenshot_data:
            return
        try:
            self.screenshot_data[scr['screenshot_id']][1] = scr['image']
            if scr['screenshot_id'] in self.color_features and scr['screenshot_id'] in self.screenshot_data:
                l = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][0]
                x = -(self.color_features[scr['screenshot_id']].analysis_data['color_lab'][1]) + 128
                y = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][2] - 128

                # If it's currently visible by the classification object
                if self.screenshot_data[scr['screenshot_id']][2] == True:
                    if self.screenshot_data[scr['screenshot_id']][1] is not None:
                        self.plot_ab_space.add_image(x, y, self.screenshot_data[scr['screenshot_id']][1], False, mime_data=self.screenshot_data[scr['screenshot_id']][0], z = l)
                        self.plot_la_space.add_image(x, l, self.screenshot_data[scr['screenshot_id']][1], False, mime_data=self.screenshot_data[scr['screenshot_id']][0], z = y)
                        # self.segment_view.add_item_to_segment(scr['screenshot_id'], self.screenshot_data[scr['screenshot_id']][1])

                    segment_id = self.screenshot_data[scr['screenshot_id']][0].segment_id
                    if segment_id in self.segment_data:
                        segm = self.segment_data[segment_id]['segment']
                        proj = self.db_projects[segm.project_id]
                        self.segment_view.add_entry(proj, segm, self.segment_data[segment_id]['shots'], None)
                        self.segment_view.add_by_segment_id(self.segment_data[segment_id]['segment'],
                                                            self.screenshot_data[scr['screenshot_id']][0],
                                                            self.screenshot_data[scr['screenshot_id']][1])

        except Exception as e:
            pass

    def on_classification_object_changed(self, name):
        if name in self.classification_object_filter_indices:
            idx = self.classification_object_filter_indices[name]
        else:
            return

        self.plot_ab_space.clear_view()
        self.plot_la_space.clear_view()
        self.plot_la_space.add_grid()
        self.plot_ab_space.add_grid()

        for k in self.screenshot_data:
            scr = self.screenshot_data[k][0]
            if idx == scr.classification_object_id and scr.screenshot_id in self.color_features and self.screenshot_data[scr.screenshot_id][1] is not None:
                self.screenshot_data[k][2] = True
                l = self.color_features[scr.screenshot_id].analysis_data['color_lab'][0]
                x = -(self.color_features[scr.screenshot_id].analysis_data['color_lab'][1]) + 128
                y = self.color_features[scr.screenshot_id].analysis_data['color_lab'][2] - 128
                self.plot_ab_space.add_image(x, y, self.screenshot_data[scr.screenshot_id][1], False,
                                             mime_data=self.screenshot_data[scr.screenshot_id][0], z=l)
                self.plot_la_space.add_image(x, l, self.screenshot_data[scr.screenshot_id][1], False,
                                             mime_data=self.screenshot_data[scr.screenshot_id][0], z=y)
            else:
                self.screenshot_data[k][2] = False

    def clear(self):
        self.plot_ab_space.clear_view()
        self.plot_la_space.clear_view()
        self.plot_ab_dot.clear_view()
        self.plot_la_dot.clear_view()

        self.plot_la_space.add_grid()
        self.plot_ab_space.add_grid()
        self.plot_ab_dot.add_grid("AB")
        self.plot_la_dot.add_grid("LA")

        self.segment_data = dict()
        self.screenshot_data = dict()
        self.color_features = dict()

        self.segment_view.clear_view()

    def on_query_result(self, obj):
        print("Result received")
        if id(obj) in self.processed_results:
            return
        self.processed_results.append(id(obj))
        if obj['type'] == "segments":
            self.clear()
            for s in obj['data']['segments']:
                self.segment_data[s.segment_id] = dict(segment=s, shots = [], features = [])

            for scr in obj['data']['screenshots']:
                self.screenshot_data[scr.screenshot_id] = [scr, None, False]
                if self.vis_plot_ab_space.get_current_classification_object() == scr.classification_object_id:
                    self.screenshot_data[scr.screenshot_id][2] = True

            for s in self.segment_data.keys():
                for k in obj['data']['segment_mapping'][s]['shot_ids']:
                    self.segment_data[s]['shots'].append(self.screenshot_data[k][0])

            if len(obj['data']['features']) > 0:
                for o in obj['data']['features']:
                    self.color_features[o.target_container_id] = o

            to_sort = dict()
            for scr in obj['data']['screenshots']:
                if scr.classification_object_id not in to_sort:
                    to_sort[scr.classification_object_id] = []
                to_sort[scr.classification_object_id].append(scr)

            to_load = []
            for t in to_sort:
                scrs = to_sort[t]
                k = np.clip(self.visualizer.K_IMAGES, 0 , len(scrs))
                to_load.extend(sample(scrs, k))
                print("Loading:", k)
                # Create a list of Data Points for the dotplots
                self.dot_plot_data[t] = []
                for s in scrs:
                    if s.screenshot_id in self.color_features:
                        self.dot_plot_data[t].append(self.color_features[s.screenshot_id])
                        to_load.append(s)
            self.visualizer.on_load_screenshots(to_load, self.on_screenshot_loaded, False)

            for t in self.dot_plot_data[list(self.dot_plot_data.keys())[0]]:
                try:
                    l = t.analysis_data['color_lab'][0]
                    x = -(t.analysis_data['color_lab'][1]) + 128
                    y = (t.analysis_data['color_lab'][2]) - 128

                    c = QColor(t.analysis_data['color_bgr'][2],t.analysis_data['color_bgr'][1] ,t.analysis_data['color_bgr'][0], 200)
                    self.plot_ab_dot.add_point(x, y, z=l, col=c)
                    self.plot_la_dot.add_point(x, l, z=y, col=c)
                except:
                    continue

        elif obj['type'] == "keywords":
            cl_objs = []
            for k in obj['data']['cl_objs'].keys():
                cl_objs.append(obj['data']['cl_objs'][k])

            for cb in self.classification_object_filter_cbs:
                cb.clear()
                for cl in cl_objs:
                    cb.addItem(cl.name)
            for cl in cl_objs:
                self.classification_object_filter_indices[cl.name] = cl.classification_object_id

        elif obj['type'] == "projects":
            for p in obj['data']['projects'].keys():
                dbproject = obj['data']['projects'][p]
                self.db_projects[dbproject.project_id] = dbproject

    @pyqtSlot(object, object)
    def on_segments_selected(self, obj:DBSegment, scrs:List[DBScreenshot]):
        indices = []
        for idx, img in enumerate(self.plot_ab_space.images):
            if img.mime_data in scrs:
                indices.append(idx)
        print(len(indices))
        self.plot_ab_space.set_highlighted(indices)
        self.plot_la_space.set_highlighted(indices)

    @pyqtSlot(object)
    def on_images_clicked(self, mime_data):
        self.visualizer.on_screenshot_inspector(mime_data)