from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pickle
import typing
import sys

from functools import partial
import numpy as np
import networkx as nx

from core.gui.ewidgetbase import EGraphicsView, line_separator


DATA_SET = "../../results/result_fm_db_parser.pickle"

COL_NODE_DES = QColor(30, 30, 30, 150)
COL_NODE_SEL = QColor(230, 230, 230, 200)

COL_NODE_UNH = QColor(30, 30, 30, 5)

BRUSH_NODE_DES = QColor(133, 42, 42, 150)
BRUSH_NODE_SEL = QColor(150, 42, 42, 200)
BRUSH_NODE_UNH = QColor(133, 42, 42, 5)

COL_EDGE_DES = QColor(200, 200, 140, 150)
COL_EDEG_SEL = QColor(200, 200, 140, 250)
COL_EDGE_UNH = QColor(200, 200, 140, 5)

PEN_UNH = 2
PEN_DES = 3
PEN_SEL = 6
#enregion


class GraphNode(QGraphicsEllipseItem):
    def __init__(self, context_obj, view, pen, brush, is_selectable = True):
        super(GraphNode, self).__init__()
        self.context_obj = context_obj
        self.view = view
        self.setPen(pen)
        self.setBrush(brush)
        self.is_selectable = is_selectable
        self.edges = []
        self.label = None
        self.current_order = 1 # How far am i from the currently selected Node?

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def get_graph(self, result_edges, result_nodes, depth = 2):
        self.current_order = self.view.selection_graph_depth - depth
        result_nodes.append(self)

        if depth == 0:
            return
        else:
            for e in self.edges:
                if e not in result_edges:
                    e.set_order(self.current_order)

            result_edges.extend(self.edges)
            for e in self.edges:
                other = e.get_other_node(self)
                if other not in result_nodes:
                    other.get_graph(result_edges, result_nodes, depth - 1)
            return

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(GraphNode, self).mousePressEvent(event)
        if self.is_selectable:
            self.view.on_selection(self)


    def set_selected(self, state):
        self.current_order = 1
        if state:
            self.setBrush(BRUSH_NODE_SEL)
            self.setPen(QPen(COL_NODE_SEL, PEN_SEL))
        else:
            self.setBrush(BRUSH_NODE_DES)
            self.setPen(QPen(COL_NODE_DES, PEN_DES))

        if self.label is not None:
            self.label.show()

    def set_highlighted(self, state):
        if state:
            c = BRUSH_NODE_SEL
            b_col = QColor(c.red(), c.green(), c.blue(), int(np.clip(c.alpha() - (self.current_order * (250 / self.view.selection_graph_depth)),20, 255)))
            c = COL_NODE_SEL
            p_col = QColor(c.red(), c.green(), c.blue(), int(np.clip(c.alpha() - (self.current_order * (250 / self.view.selection_graph_depth)),20, 255)))
            self.setBrush(b_col)
            self.setPen(QPen(p_col, PEN_SEL))
            if self.label is not None:
                self.label.show()
        else:
            self.setBrush(BRUSH_NODE_UNH)
            self.setPen(QPen(COL_NODE_UNH, PEN_UNH))
            if self.label is not None:
                self.label.hide()


class GraphEdge(QGraphicsLineItem):

    def __init__(self, context_obj, view, pen, n1, n2, is_selectable = False, n_occurence = 1.0):
        super(GraphEdge, self).__init__()
        self.context_obj = context_obj
        self.view = view
        self.setPen(pen)
        self.is_selectable = is_selectable
        self.n1 = n1
        self.n2 = n2
        self.current_order = 1.0
        self.n_occurence = n_occurence
        self.label = None

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(GraphEdge, self).mousePressEvent(event)
        if self.is_selectable:
            self.view.on_selection(self)

    def set_selected(self, state):
        if state:
            self.setPen(QPen(COL_EDEG_SEL, PEN_SEL))
        else:
            self.setPen(QPen(COL_EDGE_DES, PEN_DES))

    def set_order(self, order):
        self.current_order = order

    def set_highlighted(self, state):
        if state:
            c = COL_EDEG_SEL
            p_col = QColor(c.red(), c.green(), c.blue(), int(np.clip(c.alpha() - self.current_order * (250 / self.view.selection_graph_depth), 20, 255)))
            self.setPen(QPen(p_col, PEN_SEL))
            if self.label is not None:
                self.label.show()
        else:
            self.setPen(QPen(COL_EDGE_UNH, PEN_UNH))
            if self.label is not None:
                self.label.hide()

    def get_other_node(self, node):
        if self.n1 == node:
            return self.n2
        else:
            return self.n1


class GraphText(QGraphicsTextItem):
    def __init__(self, text, conn_obj):
        super(GraphText, self).__init__(text)
        self.conn_obj = conn_obj


#region -- Classes --

class VocabularyGraph(QWidget):
    onSelectionChanged = pyqtSignal(object)

    def __init__(self, parent):
        super(VocabularyGraph, self).__init__(parent)
        self.view = EGraphicsView(self)
        self.view.setScene(QGraphicsScene(self))

        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.view)
        self.node_matrix = None
        self.node_labels = None
        self.context_objects = None

        self.text_size = 15
        self.node_threshold = 1000
        self.edge_threshold = 800
        self.selection_graph_depth = 2

        self.nodes = []
        self.edges = []
        self.labels = []

        self.node_words_model = QStandardItemModel()
        self.current_labels = []
        self.controls = None
        self.current_selection = None


    def on_selection(self, obj):
        for n in self.nodes:
            n.set_selected(False)

        for n in self.edges:
            n.set_selected(False)

        self.current_selection = obj

        if obj is not None:
            self.view.setRenderHint(QPainter.Antialiasing, True)
            obj.set_selected(True)
            self.onSelectionChanged.emit(obj)

            h_nodes = []
            h_edges = []
            obj.get_graph(h_edges, h_nodes, depth=self.selection_graph_depth)

            self.highlight(h_nodes, h_edges)
        else:
            self.view.setRenderHint(QPainter.Antialiasing, False)

    def highlight(self, nodes, edges):
        for n in self.nodes:
            if n not in nodes:
                n.set_highlighted(False)
            else:
                n.set_highlighted(True)

        for e in self.edges:
            if e not in edges:
                e.set_highlighted(False)
            else:
                e.set_highlighted(True)

    def on_filter(self, indices):
        matrix = self.node_matrix[:, indices]
        matrix = matrix[indices, :]
        self.create_graph(matrix, np.array(self.node_labels)[indices].tolist())

    def clear_view(self):
        for n in self.nodes:
            self.view.scene().removeItem(n)
        for e in self.edges:
            self.view.scene().removeItem(e)

        for lbl in self.labels:
            self.view.scene().removeItem(lbl)

        self.nodes = []
        self.edges = []
        self.labels = []

    def create_graph(self, node_matrix, labels = None, context_objects = None, dot_size = 20, edge_threshold = 1):
        self.clear_view()

        self.node_matrix = node_matrix
        self.node_labels = labels
        self.context_objects = context_objects

        if labels is None:
            labels = [""] * node_matrix.shape[0]
        if context_objects is None:
            context_objects = [None] * node_matrix.shape[0]

        g = nx.Graph()
        m = node_matrix

        edges = []
        edges_n_occurences = []
        m_max = np.amax(m)

        node_sums = np.sum(m, axis=1).astype(np.float32)
        node_sums = np.divide(node_sums, np.amax(node_sums))
        node_sums = np.multiply(node_sums, dot_size)

        # Filter the Input by the Node Threshold
        print("Filtering Nodes")
        node_names = labels
        node_infos = []
        valid_node_indices = []
        valid_node_mapping = []
        for x in range(m.shape[0]):
            if np.sum(m[x]) >= self.node_threshold:
                valid_node_indices.append(x)
                valid_node_mapping.append(len(node_infos))
                node_info = [len(node_infos) - 1, labels[x], context_objects[x], [], x, node_sums[x]]
                node_infos.append(node_info)

        for info in node_infos:
            mx = info[4] # the index of this node in the node-matrix
            ndx = info[0] # the index of this node in the final filtered list
            for my in range(m.shape[1]):
                if m[mx, my] >= self.edge_threshold:
                    if my in valid_node_indices:
                        ny = valid_node_mapping[valid_node_indices.index(my)]
                        info[3].append([ndx, ny, m[mx, my]])

        print("Creating Graph Layout")
        for x in range(len(node_infos)):
            g.add_node(x)

        for info in node_infos:
            for eg in info[3]:
                edges_n_occurences.append([eg[2]])
                g.add_edge(eg[0], eg[1], attr_dict=dict(weight = eg[2] / m_max))
                edges.append([eg[0], eg[1]])

        print("N-Edges:", len(edges), "N-Nodes:", len(g.nodes))
        lt = nx.spring_layout(g)

        scale = 100000

        pen = QPen(QColor(201, 29, 32, 250))
        pen.setWidth(5)
        pen.setColor(COL_EDGE_DES)
        dot_center = dot_size / 2

        print("Drawing Edges")
        for i, e in enumerate(edges):
            if i % 100 == 0:
                a = lt[e[0]]
                b = lt[e[1]]
                # s1 = node_sums[e[0]]
                # s2 = node_sums[e[1]]
                s1 = node_infos[e[0]][5]
                s2 = node_infos[e[1]][5]

                item = GraphEdge(None, self, pen, e[0], e[1], n_occurence=edges_n_occurences[i])
                self.edges.append(item)
                self.view.scene().addItem(item)
                item.setLine(a[0] * scale + (dot_center * s1), a[1] * scale + (dot_center * s1),
                                           b[0] * scale + (dot_center * s2), b[1] * scale + (dot_center * s2))

        pen = QPen(COL_NODE_DES)
        font = QFont("Consolas", self.text_size)
        brush = QBrush(BRUSH_NODE_DES, Qt.SolidPattern)

        counter = 0
        print("Drawing Nodes")
        for key, itm in lt.items():
            # s = node_sums[counter]
            if counter >= len(node_infos):
                print("1 OUPS")
                continue
            s = node_infos[counter][5]
            n_itm = GraphNode(None, self, pen, brush)
            self.nodes.append(n_itm)
            self.view.scene().addItem(n_itm)
            n_itm.setRect(itm[0] * scale, itm[1] * scale, dot_size * s, dot_size * s)
            counter += 1

        counter = 0
        self.current_labels = []
        if labels is not None:
            for key, itm in lt.items():
                if counter >= len(node_infos):
                    print("2 OUPS")
                    continue
                s = node_infos[counter][5]
                name = node_infos[counter][1] #node_names[counter]
                self.current_labels.append(name)

                lbl = self.view.scene().addText(name,font)
                lbl.setPos(itm[0] * scale + (dot_size * s / 2) - lbl.textWidth(),
                           itm[1] * scale + (dot_size * s / 2))
                lbl.setDefaultTextColor(QColor(200,200,200))
                self.labels.append(lbl)
                self.nodes[counter].label = lbl
                counter += 1

        ok = 0
        errors = 0

        print("Connecting Nodes and Edges")
        for e in self.edges:
            p_center = (e.line().p1() + e.line().p2()) / 2

            lbl = self.view.scene().addText(str(e.n_occurence), font)
            lbl.setPos(p_center)
            lbl.setDefaultTextColor(QColor(200, 200, 200))
            self.labels.append(lbl)
            e.label = lbl

            try:
                n1 = self.nodes[e.n1]
                n2 = self.nodes[e.n2]

                n1.add_edge(e)
                n2.add_edge(e)

                e.n1 = n1
                e.n2 = n2
                ok += 1
            except:
                errors += 1
                continue

        self.node_words_model.clear()
        if self.controls is not None:
            for lbl in self.current_labels:
                self.node_words_model.appendRow(QStandardItem(lbl))

            completer = QCompleter()
            completer.setModel(self.node_words_model)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            self.controls.node_query_line.setCompleter(completer)

        # print("Errors:", errors, " OK:", ok)

    def get_node_by_context(self, context_obj):
        for n in self.nodes:
            if n.context_obj is context_obj:
                return n

    def mousePressEvent(self, a0: QMouseEvent):
        if a0.button() == Qt.RightButton:
            self.on_selection(None)

    def get_controls(self):
        self.controls = GraphControls(self)
        return self.controls

    def set_edge_threshold(self, value):
        self.edge_threshold = value

    def set_node_threshold(self, value):
        self.node_threshold = value

    def set_selection_graph_depth(self, value):
        self.selection_graph_depth = value

    def on_query_by_label(self, label):
        for n in self.nodes:
            if n.label.toPlainText() == label:
                self.on_selection(n)
                break



class GraphControls(QWidget):
    def __init__(self, graph_widget:VocabularyGraph):
        super(GraphControls, self).__init__(None)
        self.setLayout(QVBoxLayout(self))

        self.graph_widget = graph_widget

        self.node_query_ctrl = QWidget(self)
        self.node_query_ctrl.setLayout(QHBoxLayout(self.node_query_ctrl))
        self.node_query_ctrl.layout().addWidget(QLabel("Search Name:"))
        self.node_query_line = QLineEdit(self.node_query_ctrl)
        self.node_query_line.returnPressed.connect(self.on_query)
        self.node_query_ctrl.layout().addWidget(self.node_query_line)

        self.n_depth_ctrl = QWidget(self)
        self.n_depth_ctrl.setLayout(QHBoxLayout(self.n_depth_ctrl))
        self.n_depth_ctrl.layout().addWidget(QLabel("Graph Depth:"))
        self.sB_depth = QSpinBox(self.n_depth_ctrl)
        self.sB_depth.setRange(1, 10)
        self.sB_depth.setValue(self.graph_widget.selection_graph_depth)
        self.n_depth_ctrl.layout().addWidget(self.sB_depth)
        self.sB_depth.valueChanged.connect(self.on_depth_changed)

        self.thresholds_nodes_ctrl = QWidget(self)
        self.thresholds_nodes_ctrl.setLayout(QHBoxLayout(self.thresholds_nodes_ctrl))
        self.thresholds_nodes_ctrl.layout().addWidget(QLabel("Node Threshold:"))
        self.sl_threshold_nodes = QSpinBox(self.thresholds_nodes_ctrl)
        self.sl_threshold_nodes.setRange(0, 100000)
        self.sl_threshold_nodes.setValue(self.graph_widget.node_threshold)
        self.thresholds_nodes_ctrl.layout().addWidget(self.sl_threshold_nodes)
        self.sl_threshold_nodes.valueChanged.connect(self.on_node_threshold_changed)

        self.thresholds_edges_ctrl = QWidget(self)
        self.thresholds_edges_ctrl.setLayout(QHBoxLayout(self.thresholds_edges_ctrl))
        self.thresholds_edges_ctrl.layout().addWidget(QLabel("Edge Threshold:"))
        self.sB_threshold_edge = QSpinBox(self.thresholds_edges_ctrl)
        self.sB_threshold_edge.setRange(0, 100000)
        self.sB_threshold_edge.setValue(self.graph_widget.edge_threshold)
        self.thresholds_edges_ctrl.layout().addWidget(self.sB_threshold_edge)
        self.sB_threshold_edge.valueChanged.connect(self.on_edge_threshold_changed)

        self.btn_reload = QPushButton("Reload Graph")
        self.layout().addWidget(self.btn_reload)
        self.btn_reload.clicked.connect(self.on_reload_graph)

        self.layout().addWidget(self.node_query_ctrl)
        self.layout().addWidget(self.n_depth_ctrl)
        self.layout().addWidget(line_separator(Qt.Horizontal))
        self.layout().addWidget(self.thresholds_nodes_ctrl)
        self.layout().addWidget(self.thresholds_edges_ctrl)
        self.layout().addWidget(self.btn_reload)
        self.layout().addItem(QSpacerItem(1,1,QSizePolicy.Fixed, QSizePolicy.Expanding))

    def on_query(self):
        self.node_query_line.completer().complete()
        text = self.node_query_line.text()
        self.graph_widget.on_query_by_label(text)

    def on_depth_changed(self):
        self.graph_widget.selection_graph_depth = self.sB_depth.value()
        self.graph_widget.on_selection(self.graph_widget.current_selection)

    def on_edge_threshold_changed(self):
        self.graph_widget.edge_threshold = self.sl_threshold_nodes.value()

    def on_node_threshold_changed(self):
        self.graph_widget.node_threshold = self.sB_threshold_edge.value()

    def on_reload_graph(self):
        self.graph_widget.create_graph(self.graph_widget.node_matrix,
                                       self.graph_widget.node_labels,
                                       self.graph_widget.context_objects)

#endregion
