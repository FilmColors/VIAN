from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from random import sample

from core.visualization.image_plots import ImagePlotTime
from visualizer.presentation.presentation_widget import *
from core.visualization.graph_plots import VocabularyGraph
from core.visualization.feature_plot import *
from core.corpus.shared.entities import *

class VisMovieLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisMovieLayout, self).__init__(parent, visualizer)#, "qt_ui/visualizer/VisMovieLayout.ui")

        self.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Vertical, self)
        self.layout().addWidget(self.vsplit)
        self.upper_widget = QSplitter(self)
        self.lower_widget = QSplitter(self)
        self.lower_right = QSplitter(Qt.Vertical, self.lower_widget)
        self.lower_left = QSplitter(Qt.Vertical, self.lower_widget)
        self.lower_widget.addWidget(self.lower_left)
        self.lower_widget.addWidget(self.lower_right)

        self.vsplit.addWidget(self.upper_widget)
        self.vsplit.addWidget(self.lower_widget)

        self.plot_color_dt = ImagePlotTime(self)
        self.plot_network = VocabularyGraph(self)
        self.plot_features = GenericFeaturePlot(self)

        self.vis_plot_color_dt = VisualizerVisualization(None, self.plot_color_dt, self.plot_color_dt.get_param_widget())
        self.vis_plot_network = VisualizerVisualization(None, self.plot_network, self.plot_network.get_controls())
        self.vis_plot_features = VisualizerVisualization(None, self.plot_features)

        self.upper_widget.addWidget(self.vis_plot_color_dt)
        self.lower_right.addWidget(self.vis_plot_network)
        self.lower_left.addWidget(self.vis_plot_features)

        self.screenshots = dict() # TUPLE (DBScreenshot, Image)
        self.color_features = dict()

    @pyqtSlot(object)
    def on_screenshot_loaded(self, scr):
        self.screenshots[scr['screenshot_id']][1] = scr['image']
        if scr['screenshot_id'] in self.color_features and scr['screenshot_id'] in self.screenshots:
            x = self.screenshots[scr['screenshot_id']][0].time_ms
            # This is an Error in the Database, in the Globa Analyses the Features are switched.... DAMN
            if len(self.color_features[scr['screenshot_id']].analysis_data['saturation_p']) > 1:
                y = self.color_features[scr['screenshot_id']].analysis_data['color_bgr']
            else:
                y = self.color_features[scr['screenshot_id']].analysis_data['saturation_p']

            self.plot_color_dt.add_image(x, y, self.screenshots[scr['screenshot_id']][1])
            # x = scr[]
            # self.plot_color_dt.add_image()

    def clear(self):
        self.plot_color_dt.clear_view()

    def on_query_result(self, obj):
        if obj['type'] == "movie_info":
            # COLOR FEATURES
            segments = []
            segment_index = dict()
            self.clear()

            dbsegments = obj['data']['segments']
            for s in dbsegments:
                segments.append(SegmentTuple(s.movie_segm_id, s.segm_start, s.segm_end))
                segment_index[s.segment_id] = s.movie_segm_id

            feature_index = dict()
            self.compute_node_matrix(obj['data']['keywords'], self.visualizer.all_keywords)
            for f in obj['data']['keywords']:
                if f.keyword_id not in feature_index:
                    feature_index[f.keyword_id] = FeatureTuple(self.visualizer.all_keywords[f.keyword_id]['word'].name, [])
                if f.entry_id in segment_index:
                    feature_index[f.keyword_id].segment_ids.append(segment_index[f.entry_id])

            self.plot_features.clear_view()
            self.plot_features.create_timeline(segments)
            for f in feature_index.keys():

                self.plot_features.create_feature(feature_index[f])

            # COLOR-D
            if len(obj['data']['screenshots']) > 0:
                if len(obj['data']['screenshots']) < 50:
                    k = len(obj['data']['screenshots'])
                else:
                    k = 50

                self.visualizer.on_load_screenshots(sample(obj['data']['screenshots'], k), self.on_screenshot_loaded)
            for scr in obj['data']['screenshots']:
                self.screenshots[scr.screenshot_id] = [scr, None]

            if len(obj['data']['features']) > 0:
                for o in obj['data']['features']:
                    self.color_features[o.target_container_id] = o

            print("OK")

    def compute_node_matrix(self, key_mapping, keywords):
        labels = []

        # Generate a list of labes from the received keyword result of the Query
        for k in keywords.keys():
            k = keywords[k]
            labels.append(k['word'].name + ":" + k['voc'].name + ":" + k['cl_obj'].name)

        # Iterate over all Segments, and create a segment wise correlation matrix
        segment_sorted = dict()
        for k in key_mapping:
            if k.target_id not in segment_sorted:
                segment_sorted[k.target_id] = []
            segment_sorted[k.target_id].append(k)

        node_matrix = np.zeros(shape=(len(keywords), len(keywords)), dtype=np.float32)
        for k in segment_sorted.keys():
            k = segment_sorted[k]
            all_keyws_in_segment = [kwd.keyword_id for kwd in k]
            for x in all_keyws_in_segment:
                for y in all_keyws_in_segment:
                    node_matrix[x][y] += 1

        self.plot_network.create_graph(node_matrix, labels)




