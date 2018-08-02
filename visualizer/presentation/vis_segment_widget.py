from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from core.visualization.image_plots import *
from visualizer.presentation.presentation_widget import *
from visualizer.widgets.segment_visualization import *
from random import sample

class VisSegmentLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSegmentLayout, self).__init__(parent, visualizer)#, "qt_ui/visualizer/VisSegmentsLayout.ui")
        self.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Vertical, self)
        self.layout().addWidget(self.vsplit)
        self.upper_widget = QSplitter(self)
        self.lower_widget = QSplitter(self)

        self.plot_la_space = ImagePlotPlane(self)
        self.plot_ab_space = ImagePlotCircular(self)
        self.vis_plot_la_space = VisualizerVisualization(self, self.plot_la_space, self.plot_ab_space.get_param_widget())
        self.vis_plot_ab_space = VisualizerVisualization(self, self.plot_ab_space, self.plot_ab_space.get_param_widget())
        self.segment_view = SegmentVisualization(self, self.visualizer)
        self.lower_widget.addWidget(self.segment_view)


        self.classification_object_filter_cbs = [QComboBox(), QComboBox()]
        self.classification_object_filter_indices = dict()
        self.plot_ab_space.set_heads_up_widget(self.classification_object_filter_cbs[0])
        self.classification_object_filter_cbs[0].currentTextChanged.connect(self.on_classification_object_changed)

        self.upper_widget.addWidget(self.vis_plot_la_space)
        self.upper_widget.addWidget(self.vis_plot_ab_space)

        self.vsplit.addWidget(self.upper_widget)
        self.vsplit.addWidget(self.lower_widget)
        self.segment_data = dict()
        self.screenshot_data = dict()
        self.color_features = dict()
        self.db_projects = dict()

    @pyqtSlot(object)
    def on_screenshot_loaded(self, scr):
        if scr['screenshot_id'] not in self.screenshot_data:
            return

        self.screenshot_data[scr['screenshot_id']][1] = scr['image']
        if scr['screenshot_id'] in self.color_features and scr['screenshot_id'] in self.screenshot_data:
            l = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][0]
            x = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][1] - 128
            y = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][2] - 128
            if self.screenshot_data[scr['screenshot_id']][2] == True:
                if self.screenshot_data[scr['screenshot_id']][1] is not None:
                    self.plot_ab_space.add_image(x, y, self.screenshot_data[scr['screenshot_id']][1], False)
                    self.plot_la_space.add_image(x, l, self.screenshot_data[scr['screenshot_id']][1], False)
                    self.segment_view.add_item_to_segment(scr['screenshot_id'], self.screenshot_data[scr['screenshot_id']][1])

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
                x = self.color_features[scr.screenshot_id].analysis_data['color_lab'][1] - 128
                y = self.color_features[scr.screenshot_id].analysis_data['color_lab'][2] - 128
                self.plot_ab_space.add_image(x, y, self.screenshot_data[scr.screenshot_id][1], False)
                self.plot_la_space.add_image(x, l, self.screenshot_data[scr.screenshot_id][1], False)
            else:
                self.screenshot_data[k][2] = False

    def clear(self):
        self.plot_ab_space.clear_view()
        self.plot_la_space.clear_view()

        self.plot_la_space.add_grid()
        self.plot_ab_space.add_grid()

        self.segment_data = dict()
        self.screenshot_data = dict()
        self.color_features = dict()

        self.segment_view.clear_view()

    def on_query_result(self, obj):
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
            k = 150
            for t in to_sort:
                scrs = to_sort[t]

                if len(scrs) > 0:
                    if len(scrs) < self.visualizer.K:
                        k = len(scrs)
                    else:
                        k = self.visualizer.K
                step = int(np.floor(len(scrs) / k))
                for i in range(k):
                    to_load.append(scrs[i * step])
                #     to_load.extend(sample(scrs, k))
            self.visualizer.on_load_screenshots(to_load, self.on_screenshot_loaded)

            for k in self.segment_data.keys():
                segm = self.segment_data[k]['segment']
                if segm.project_id in self.db_projects:
                    proj = self.db_projects[segm.project_id]
                else:
                    continue
                self.segment_view.add_entry(proj, segm, self.segment_data[k]['shots'], None)

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
