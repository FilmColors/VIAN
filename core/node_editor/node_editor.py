from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import os
from functools import partial
from core.node_editor.operations import *
from core.node_editor.datatypes import *
import json
NODETYPE_INPUT_NODE = 0
NODETYPE_OUTPUT_NODE = 1




class NodeEditor(QWidget):
    def __init__(self, parent):
        super(NodeEditor, self).__init__(parent)
        self.id_counter = 10000
        self.nodes = []
        self.selected_nodes = []
        self.is_connecting = False
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.lbl_compile_status = QLabel("Not Compiled", self)

        self.current_connection = None
        self.connections = []
        self.hovered_pin = None

        # self.create_node(OperationMean())
        # self.create_node(OperationShowImage())
        # self.create_node(ImageReader())

        self.is_compiled = False
        self.show()

    def create_node(self, operation, pos = QPoint(50,50)):
        node = Node(self, operation, self.id_counter)
        operation.node = node
        self.nodes.append(node)
        node.onSelection.connect(self.on_selection)
        node.move(pos)

        self.id_counter += 1
        node.show()
        return node

    def get_by_id(self, id):
        for n in self.nodes:
            if n.unique_id == id:
                return n
        for c in self.connections:
            if c.unique_id == id:
                return c

    def on_selection(self, node):
        if node is None:
            self.selected_nodes = []
        else:
            self.selected_nodes = [node]
        for n in self.nodes:
            if n not in self.selected_nodes:
                n.is_selected = False

    def remove_nodes(self, nodes):
        for n in nodes:
            for p in n.pins:
                p.break_connection()
            try:
                self.nodes.remove(n)
                n.deleteLater()
            except:
                pass

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.on_selection(None)
            if self.is_connecting and self.hovered_pin:
                self.current_connection.set_end_point(self.hovered_pin.mapTo(self, self.hovered_pin.connection_point))
                self.current_connection = None
                self.is_connecting = False
            else:
                self.abort_connection()

        if QMouseEvent.buttons() & Qt.RightButton:
            if self.is_connecting:
                self.abort_connection()
            else:
                menu = NodeEditorContextMenu(self, self.mapToGlobal(QMouseEvent.pos()), QMouseEvent.pos())

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
                self.abort_connection()

    def mouseMoveEvent(self, QMouseEvent):
        if self.is_connecting and self.current_connection:
            self.current_connection.set_end_point(self.mapToParent(QMouseEvent.pos()))
            self.update()

    def wheelEvent(self, QWheelEvent):
        for n in self.nodes:
            n.resize(n.width() - 0.1 * QWheelEvent.angleDelta().y(), n.height() - 0.1 * QWheelEvent.angleDelta().y())
            n.move(n.pos().x() - 0.1 * QWheelEvent.angleDelta().y(),  n.pos().y() - 0.1 * QWheelEvent.angleDelta().y())

    def on_pin_pressed(self, node_pin):
        if self.is_connecting:
            if isinstance(self.current_connection.start_pin.get_data_type(), node_pin.get_data_type().__class__) \
                    and self.current_connection.start_pin.pin_type != node_pin.pin_type:
                if node_pin.connection == None:
                    self.finish_connection(node_pin)
            else:
                self.abort_connection()
        else:
            self.on_begin_connection(node_pin)

    def on_begin_connection(self, start_node):
        if not self.is_connecting:
            connection = Connection(start_node.get_data_type(), self.id_counter)
            connection.set_start_point(start_node.mapTo(self, start_node.connection_point))
            connection.set_start_pin(start_node)

            self.connections.append(connection)
            self.current_connection = connection
            self.is_connecting = True
            self.update()
            self.id_counter += 1

    def finish_connection(self, end_node):
        self.current_connection.set_end_point(self.hovered_pin.mapTo(self, self.hovered_pin.connection_point))
        self.current_connection.set_end_pin(end_node)

        self.current_connection.end_pin.node.on_connect()

        self.current_connection = None
        self.is_connecting = False
        self.update()

    def abort_connection(self):
        try:
            self.connections.remove(self.current_connection)
            self.current_connection.start_pin.connection = None
            self.is_connecting = False
            self.current_connection = None
        except:
            pass
        self.update()

    def on_hover_pin(self, pin):
        self.hovered_pin = pin

    def on_leave_pin(self, pin):
        if pin is self.hovered_pin:
            self.hovered_pin = None

    def remove_connection(self, connection):
        if connection:
            connection.start_pin.connection = None
            if  connection.end_pin:
                connection.end_pin.node.update_pins()
                connection.end_pin.connection = None
            if connection in self.connections:
                self.connections.remove(connection)
            connection.deleteLater()
            self.clear_compilation()

    def compile(self):
        self.is_compiled = False
        for n in self.nodes:
            if n.operation.is_final_node:
                self.is_compiled = n.compile()

        if self.is_compiled:
            self.lbl_compile_status.setText("Compiled")
            self.lbl_compile_status.setStyleSheet("QLabel{color : green;}")
        else:
            self.lbl_compile_status.setText("NotCompiled")
            self.lbl_compile_status.setStyleSheet("QLabel{color : Red;}")

    def run_script(self):
        if self.is_compiled:
            for n in self.nodes:
                if n.operation.is_final_node and n.is_compiled:
                    n.perform()
        else:
            print "Not Compiled"

    def store_script(self, file_path="script.vis"):
        nodes = []
        print file_path
        for n in self.nodes:
            nodes.append(n.serialize())

        connections = []
        for c in self.connections:
            connections.append(c.serialize())

        data = dict(nodes = nodes, connections=connections)

        with open(file_path, "wb") as f:
            json.dump(data, f)

    def load_script(self, file_path="script.vis"):
        with open(file_path, "rb") as f:
            data = json.load(f)

        nodes = data['nodes']
        connections = data['connections']
        for n in nodes:
            node = self.create_node(Operation("Loaded", [], []), QPoint(0,0))
            node.deserialize(n)

        print self.nodes

        for c in connections:
            print c
            dt = eval(c['data_type'])()
            conn = Connection(dt, c['unique_id'])
            start_node = self.get_by_id(c['start_node'])
            end_node = self.get_by_id(c['end_node'])

            if end_node and start_node:
                for p in start_node.pins:
                    if p.pin_id == c['start_pin']:
                        conn.set_start_pin(p)
                        break
                for p in end_node.pins:
                    if p.pin_id == c['end_pin']:
                        conn.set_end_pin(p)
                        break

                self.connections.append(conn)
        self.update()

    def clear_compilation(self):
        self.is_compiled = False
        for n in self.nodes:
            n.operation.result = []
            n.is_compiled = False

    def mouseDoubleClickEvent(self, QMouseEvent):
        self.compile()

    def resizeEvent(self, QResizeEvent):
        super(NodeEditor, self).resizeEvent(QResizeEvent)
        self.lbl_compile_status.move(self.width() - 100, self.height() - 20)

    def paintEvent(self, QPaintEvent):

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setWidth(2)
        qp.setPen(pen)


        for c in self.connections:
            path = QPainterPath()
            path.moveTo(c.start_point)
            # mid1 = QPoint(((c.end_point.x()) + c.start_point.x()) / 2, c.end_point.y())
            # mid2 = QPoint(((c.end_point.x()) + c.start_point.x()) / 2, c.start_point.y())
            y_diff = ((c.end_point.x() - c.start_point.x()) * 0.2)
            mid1 = QPoint(c.start_point.x() + y_diff, c.end_point.y())
            mid2 = QPoint(c.end_point.x() - y_diff, c.start_point.y())
            path.cubicTo(mid2, mid1, c.end_point)

            pen.setColor(c.color)
            qp.setPen(pen)
            qp.drawPath(path)
            # qp.drawPoint(mid1)
            # qp.drawPoint(mid2)

        qp.end()


class Node(QWidget):
    onSelection = pyqtSignal(object)

    def __init__(self, parent, operation, unique_id, name = "Base Class Node"):
        super(Node, self).__init__(parent)
        self.curr_loc = self.pos
        self.unique_id = unique_id
        self.node_editor = parent
        self.name = operation.name
        self.lbl_Title = QLabel(operation.name, self)
        self.lbl_Title.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)

        self.setAttribute(Qt.WA_MouseTracking, True)
        self.operation = operation
        # self.setLayout(QVBoxLayout(self))
        # self.layout().addWidget(self.lbl_Title)
        self.resize(200,150)
        self.lbl_Title.move(1, 1)
        self.lbl_Title.resize(198,18)
        self.color = QColor(150,150,150)
        self.offset = QPoint(0,0)
        self.compile_rect = QRect(1, self.height() - 5, self.width() - 1, self.height() - 1)
        self.is_dragging = False
        self.is_hovered = False
        self.is_selected = False


        self.is_compiled = False

        self.pins = []
        self.counter = 0

        self.create_pins()

        if isinstance(self.operation, OperationValue):
            self.widget = self.operation.get_input_widget(self)
            self.widget.move(5, self.height() - 100)

    def create_pins(self):
        for i in self.operation.input_types:
            self.add_pin(NODETYPE_INPUT_NODE, i)
        for o in self.operation.output_types:
            self.add_pin(NODETYPE_OUTPUT_NODE, o)

    def on_connect(self):
        inputs = []
        for p in self.pins:
            if isinstance(p, InputNodePin):
                if p.connection:
                    p.data_type = p.connection.data_type
                inputs.append(p.data_type)
        outputs = self.operation.update_out_types(inputs)
        self.update_pins(outputs)

    def update_pins(self, data_type = None):
        if data_type:
            counter = 0
            for p in self.pins:
                if isinstance(p, OutputNodePin):
                    p.data_type = data_type[counter]
                    p.color = p.data_type.color
                    counter += 1
        else:
            for p in self.pins:
                if isinstance(p, OutputNodePin):
                    p.reset_datatype()

    def compile(self):
        result = True
        self.operation.result = []
        for p in self.pins:
            if p.pin_type == "input":
                if p.connection is not None:
                    result = p.connection.start_pin.node.compile()
                else:
                    result = False

        self.is_compiled = result

        return result

    def perform(self):
        if len(self.operation.result) == 0:
            args = []
            for p in self.pins:
                if p.pin_type == "input":
                   args.append(p.connection.start_pin.node.perform())
            self.operation.perform(args)
        return self.operation.result

    def get_other_pins(self, exclude, type):
        result = []
        for p in self.pins:
            if isinstance(p, type) and p is not exclude:
                result.append(p.data_type)
        return result

    def add_pin(self, type, data_type, name = "A Pin"):
        if type == NODETYPE_INPUT_NODE:
            pin = InputNodePin(self, data_type,self.counter, name)
        else:
            pin = OutputNodePin(self, data_type,self.counter, name)

        pin.onDragConnection.connect(self.node_editor.on_pin_pressed)
        pin.onEnter.connect(self.node_editor.on_hover_pin)
        pin.onLeave.connect(self.node_editor.on_leave_pin)

        self.pins.append(pin)
        pin.move(0, len(self.pins) * 20)
        pin.resize(self.size().width(), pin.height())
        pin.show()
        self.counter += 1

    def serialize(self):
        data = dict(
            unique_id = self.unique_id,
            position = (self.pos().x(), self.pos().y()),
            operation = self.operation.__class__.__name__
        )
        return data
    def deserialize(self, serialization):
        operation = serialization['operation']
        self.operation = eval(operation)()
        self.unique_id = serialization['unique_id']
        self.move(QPoint(serialization['position'][0], serialization['position'][1]))
        self.lbl_Title.setText(self.operation.name)

        self.create_pins()
        if isinstance(self.operation, OperationValue):
            self.widget = self.operation.get_input_widget(self)
            self.widget.move(5, self.height() - 100)
            self.widget.show()

        return self

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
                self.curr_loc = self.pos()
                self.offset = QMouseEvent.pos()
                self.is_dragging = True
                self.onSelection.emit(self)
                self.is_selected = True
        # else:
        #     super(Node, self).mousePressEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.is_dragging:
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos)
                self.move(target)
        else:

            QMouseEvent.ignore()

    def mouseReleaseEvent(self, QMouseEvent):
        self.is_dragging = False

    def paintEvent(self, QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)

        qp.fillRect(self.rect(), QColor(67,67,67,150))

        if self.is_hovered:
            pen.setColor(QColor(200,200,200))
        else:
            pen.setColor( self.color)

        if self.is_selected:
            pen.setWidth(8)
            pen.setColor(QColor(255,160,47))
        else:
            pen.setWidth(2)
        qp.setPen(pen)
        qp.drawRect(self.rect())

        if self.is_compiled:
            qp.fillRect(self.compile_rect, QColor(50,100,30))
        else:
            qp.fillRect(self.compile_rect, QColor(100,50,30))
        qp.setPen(pen)

        qp.end()

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False

    def moveEvent(self, QMoveEvent):
        super(Node, self).moveEvent(QMoveEvent)
        for p in self.pins:
            p.onMoved.emit(p)
        self.node_editor.update()

    def resizeEvent(self, QResizeEvent):
        ratio = QResizeEvent.size().height() / self.height()
        super(Node, self).resizeEvent(QResizeEvent)
        for p in self.pins:
            p.resize(self.width(), p.height() * ratio)


class NodePin(QWidget):
    onDragConnection = pyqtSignal(object)
    onEnter = pyqtSignal(object)
    onLeave = pyqtSignal(object)
    onMoved = pyqtSignal(object)

    def __init__(self, parent, node, data_type,pin_id, name = "A Pin"):
        super(NodePin, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.pin_id = pin_id
        self.node = node
        self.is_hovered = False
        self.pin_height = 20
        self.pin_width = 100
        self.resize(self.pin_width, self.pin_height)
        self.label = QLabel(name, self)
        self.label.move(20,5)
        self.label.setAttribute(Qt.WA_MouseTracking, True)
        self.pin_rect = QRect(5,5,10,10)
        self.connection_point = QPoint(10,10)
        self.connection = None

        self.default_data_type = data_type
        self.data_type = data_type
        self.color = data_type.color

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.onDragConnection.emit(self)
        elif QMouseEvent.button() == Qt.RightButton:
            menu = PinContextMenu(self.node.node_editor, self.mapToGlobal(QMouseEvent.pos()), self)

    def paintEvent(self, QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        if self.is_hovered:
            pen.setColor(QColor(200,200,200))
        else:
            pen.setColor(QColor(100, 100, 100))

        pen.setWidth(2)
        qp.setPen(pen)
        qp.drawRect(self.rect())
        pen.setColor(self.color)
        qp.setPen(pen)
        qp.drawEllipse(self.pin_rect)
        qp.end()

    def enterEvent(self, QEvent):
        self.is_hovered = True
        self.onEnter.emit(self)

    def leaveEvent(self, QEvent):
        self.is_hovered = False
        self.onLeave.emit(self)

    def get_connection_location(self):
        return self.mapTo(self.node.node_editor, self.connection_point)

    def get_data_type(self):
        return self.data_type

    def break_connection(self):
        if self.connection is not None:
            self.node.node_editor.remove_connection(self.connection)

    def reset_datatype(self):
        self.data_type = self.default_data_type
        self.color = self.data_type.color


class InputNodePin(NodePin):
    def __init__(self, parent, data_type, pin_id, name = "Output Pin"):
        super(InputNodePin, self).__init__(parent, parent, data_type, pin_id, name)
        self.pin_rect = QRect(5,5,10,10)
        self.connection_point = QPoint(10, 10)
        self.pin_type = "input"
        self.label.hide()
        self.setToolTip("This is an Input Node")


        # if data_type.has_widget:
        #     self.default = data_type.widget(self)
        #     self.default.move(QPoint(20,0))


class OutputNodePin(NodePin):
    def __init__(self, parent, data_type, pin_id, name = "Output Pin"):
        super(OutputNodePin, self).__init__(parent, parent, data_type, pin_id, name)
        self.pin_rect = QRect(85, 5, 10, 10)
        self.connection_point = QPoint(90, 10)
        self.label.move(5, 5)
        self.label.setAlignment(Qt.AlignRight| Qt.AlignVCenter)
        self.pin_type = "output"

    def resizeEvent(self, QResizeEvent):
        super(NodePin, self).resizeEvent(QResizeEvent)
        a = self.width() - 15
        self.pin_rect = QRect(a, 5, 10, 10)
        self.connection_point = QPoint(a + 5, 10)


class Connection(QObject):
    def __init__(self, data_type, unique_id):
        super(Connection, self).__init__()
        self.unique_id = unique_id
        self.start_point = QPoint(0,0)
        self.end_point = QPoint(0,0)
        self.color = QColor(203,212,194)

        self.start_pin = None
        self.end_pin = None

        self.data_type = data_type
        self.color = data_type.color

    def set_start_point(self, qpoint):
        self.start_point = qpoint

    def set_end_point(self, qpoint):
        self.end_point = qpoint

    def update_start(self, object):
        self.start_point = object.get_connection_location()

    def update_end(self, object):
        self.end_point = object.get_connection_location()

    def set_end_pin(self, pin):
        self.end_pin = pin
        self.end_pin.connection = self
        self.end_point = pin.get_connection_location()
        self.end_pin.onMoved.connect(self.update_end)

        if pin.pin_type == "output":
            self.swap_pins()
            print "Swapped"

    def set_start_pin(self, pin):
        self.start_pin = pin
        self.start_pin.connection = self
        self.start_point = pin.get_connection_location()
        self.start_pin.onMoved.connect(self.update_start)

    def swap_pins(self):
        temp = self.start_pin
        self.start_pin.onMoved.disconnect()
        self.end_pin.onMoved.disconnect()

        self.set_start_pin(self.end_pin)
        self.set_end_pin(temp)

    def serialize(self):
        data = dict(
            start_node = self.start_pin.node.unique_id,
            end_node=self.end_pin.node.unique_id,
            start_pin = self.start_pin.pin_id,
            end_pin=self.end_pin.pin_id,
            data_type=self.data_type.__class__.__name__,
            unique_id = self.unique_id
        )
        return data


class NodeEditorContextMenu(QMenu):
    def __init__(self, node_editor, pos, node_pos):
        super(NodeEditorContextMenu, self).__init__(node_editor)
        self.node_editor = node_editor
        self.node_menu = self.addMenu("New Node")
        self.input_menu = self.node_menu.addMenu("Input")
        self.a_read_frame = self.input_menu.addAction("Read Frames")
        self.a_movie_colormetrics = self.input_menu.addAction("Movie Colorimetric")

        self.input_menu.addAction("TimeRange Colorimetric")

        self.a_scalar = self.input_menu.addAction("Scalar")
        self.a_vector2 = self.input_menu.addAction("Vector2D")
        self.computation_menu = self.node_menu.addMenu("Computation")
        self.node_pos = node_pos

        self.a_sum = self.computation_menu.addAction("Sum")
        self.a_subtraction = self.computation_menu.addAction("Subtraction")
        self.a_multiply = self.computation_menu.addAction("Multiplication")
        self.a_division = self.computation_menu.addAction("Division")
        self.computation_menu.addSeparator()

        self.a_resize = self.computation_menu.addAction("Resize")
        self.a_mean = self.computation_menu.addAction("Mean")
        self.a_normalization = self.computation_menu.addAction("Normalization")

        self.a_color2img = self.computation_menu.addAction("Color2Image")


        self.vis_menu = self.node_menu.addMenu("Visualization")
        self.a_show_img = self.vis_menu.addAction("Show Image")

        self.a_bar = self.vis_menu.addAction("Bar Plot")
        self.vis_menu.addAction("Color Histogram")
        self.vis_menu.addAction("Image Cluster")

        self.misc_menu = self.node_menu.addMenu("Miscellaneous")
        self.misc_menu.addAction("To Analysis")

        self.action_compile = self.addAction("Compile")
        self.action_run = self.addAction("Run")
        self.node_editor = node_editor
        self.action_save = self.addAction("Save Script")
        self.action_load = self.addAction("Load Script")

        if len(node_editor.selected_nodes) > 0:
            self.a_delete = self.addAction("Delete Nodes")
            self.a_delete.triggered.connect(partial(self.node_editor.remove_nodes, self.node_editor.selected_nodes))
        self.action_compile.triggered.connect(self.node_editor.compile)
        self.action_run.triggered.connect(self.node_editor.run_script)
        self.action_save.triggered.connect(partial(self.node_editor.store_script, "script.vis"))
        self.action_load.triggered.connect(partial(self.node_editor.load_script, "script.vis"))
        self.a_read_frame.triggered.connect(partial(self.node_editor.create_node, ImageReader(), self.node_pos ))

        self.a_scalar.triggered.connect(partial(self.node_editor.create_node, OperationScalar(), self.node_pos ))
        self.a_vector2.triggered.connect(partial(self.node_editor.create_node, OperationVector2(), self.node_pos ))
        # Action Binding
        # Computation
        self.a_color2img.triggered.connect(partial(self.node_editor.create_node, OperationColor2Image(), self.node_pos ))
        self.a_sum.triggered.connect(partial(self.node_editor.create_node, OperationAdd(), self.node_pos ))
        self.a_subtraction.triggered.connect(partial(self.node_editor.create_node, OperationSubtract(), self.node_pos ))
        self.a_multiply.triggered.connect(partial(self.node_editor.create_node, OperationMultiply(), self.node_pos ))
        self.a_division.triggered.connect(partial(self.node_editor.create_node, OperationDivision(), self.node_pos ))
        self.a_mean.triggered.connect(partial(self.node_editor.create_node, OperationMean(), self.node_pos ))
        self.a_normalization.triggered.connect(partial(self.node_editor.create_node, OperationNormalize(), self.node_pos))
        # Visualization
        self.a_show_img.triggered.connect(partial(self.node_editor.create_node, OperationShowImage(), self.node_pos ))
        self.a_bar.triggered.connect(partial(self.node_editor.create_node, OperationBarPlot(), self.node_pos ))



        self.popup(pos)


class PinContextMenu(QMenu):
    def __init__(self, node_editor, pos, pin):
        super(PinContextMenu, self).__init__(node_editor)
        self.action_break = self.addAction("Break Connection")
        self.node_editor = node_editor
        self.pin = pin

        self.action_break.triggered.connect(self.pin.break_connection)

        self.popup(pos)

