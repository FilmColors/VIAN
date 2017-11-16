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
    onScale = pyqtSignal(float)

    def __init__(self, parent):
        super(NodeEditor, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.show_grid = True

        self.nodes = []
        self.connections = []
        self.selected_nodes = []
        self.id_counter = 1000000

        self.is_connecting = False
        self.is_marquee_selecting = False
        self.marquee_selection_frame = None

        self.scale = 1.0

        self.add_node(Node(self, self, OperationFrameReader()))
        n2 = self.add_node(Node(self, self, OperationNormalize()))
        n2.move(500,500)

        n2 = self.add_node(Node(self, self, OperationShowImage()))
        n2.move(800, 500)

        self.connection_drag = None

        self.is_compiled = False
        self.lbl_compile_status = QLabel("Not Compiled", self)

        self.show()

    def create_node(self, operation, pos):
        self.add_node(Node(self, self, operation), pos)

    def add_node(self, node, pos = (QPoint(200,200))):
        self.nodes.append(node)
        node.move(pos)

        self.onScale.connect(node.scale)
        node.hasMoved.connect(self.on_node_has_moved)

        node.show()
        return node

    def remove_nodes(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]

        for n in nodes:
            conns = n.get_connections()
            for c in conns:
                c.input_field.remove_connection(c)
                c.output_field.remove_connection(c)
                self.connections.remove(c)

            if n in self.nodes:
                self.nodes.remove(n)
            n.close()



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

    def on_pin_clicked(self, field):
        if not self.is_connecting:
            self.begin_connection(field)
        else:
            self.finish_connection(field)

    def on_node_has_moved(self, moveEvent):
        for n in self.selected_nodes:
            if n is not moveEvent[0]:
                n.move(n.pos() + moveEvent[1])

    def get_unique_id(self):
        self.id_counter += 1
        return self.id_counter

    def get_by_ID(self, id):
        for i in self.connections:
            if i.unique_id == id:
                return i
        for n in self.nodes:
            if n.unique_id == id:
                return n

    def clear(self):

        conns = [connection for connection in self.connections]
        nodes = [node for node in self.nodes]
        self.remove_connection(conns)
        self.remove_nodes(nodes)


    def save_script(self, file_path):
        nodes = []
        connections = []

        for n in self.nodes:
            nodes.append(n.serialize())

        for c in self.connections:
            connections.append(c.serialize())

        data = dict(
            id_counter = self.id_counter,
            nodes = nodes,
            connections = connections,
        )

        with open(file_path, "wb") as f:
            json.dump(data, f)

    def load_script(self, file_path):
        self.clear()
        with open(file_path, "rb") as f:
            data = json.load(f)

        nodes = data['nodes']
        connections = data['connections']

        for n in nodes:
            node = Node(self, self, eval(n['operation'])())
            self.add_node(node)
            pos = QPoint(n['pos'][0]* self.scale, n['pos'][1] * self.scale)
            node.scale(self.scale)
            node.node_pos = pos
            node.unique_id = n['unique_id']
            node.move(pos)

        for c in connections:
            input_node = self.get_by_ID(c['input_node'])
            output_node = self.get_by_ID(c['output_node'])
            input_field = input_node.fields[c['input_field']]
            output_field = output_node.fields[c['output_field']]

            conn = Connection(self)
            conn.set_input_pin(input_field)
            conn.set_output_pin(output_field)
            self.connections.append(conn)
            conn.input_field.add_connection(conn)
            conn.output_field.add_connection(conn)
            conn.output_field.node.update_output_types()

        self.id_counter = len(self.connections) + len(self.nodes)

    #region Connections
    def begin_connection(self, field):
        conn = Connection(self)
        if isinstance(field, InputField):
            conn.set_output_pin(field)
        else:
            conn.set_input_pin(field)
        self.connection_drag = [field.get_connection_location(), QCursor.pos(), conn]
        self.is_connecting = True

    def finish_connection(self, node):
        if self.is_connecting and self.connection_drag:
            connection = self.connection_drag[2]
            can_connect = False
            if connection.input_field is None and isinstance(node, OutputField):
                can_connect = True
                connection.input_field = node
                # self.connections.append(connection)
                # connection.input_field.add_connection(connection)
                # connection.output_field.add_connection(connection)

            elif connection.output_field is None and isinstance(node, InputField):
                can_connect = True
                connection.output_field = node
                # self.connections.append(connection)
                # connection.input_field.add_connection(connection)
                # connection.output_field.add_connection(connection)

            if can_connect:
                can_connect = connection.verify_types()


            if can_connect:
                connection.output_field = node
                self.connections.append(connection)
                connection.input_field.add_connection(connection)
                connection.output_field.add_connection(connection)

                connection.output_field.node.update_output_types()
            else:
                self.abort_connection()

            self.connection_drag = None
            self.is_connecting = False
            self.update()

    def abort_connection(self):
        self.connection_drag = None
        self.is_connecting = False
        self.update()

    def remove_connection(self, connections):
        if not isinstance(connections, list):
            connections = [connections]
        for c in connections:
            c.input_field.remove_connection(c)
            c.output_field.remove_connection(c)
            if c in self.connections:
                self.connections.remove(c)
            self.update()

    #endregion

    #region EventHandlers
    def set_selected(self, nodes):
        for n in self.selected_nodes:
            n.select(False)
            self.update()
        self.selected_nodes = nodes
        for n in nodes:
            n.select(True)
            self.update()

    def paint_grid(self, qp):
        color_a = QColor(10,10,10,100)
        color_b = QColor(50,50,50,100)
        color_c = QColor(80,80,80,100)
        for x in range(int(self.width())):
            if x % int(50 * self.scale) == 0:
                if x % int(100 * self.scale) == 0:
                    if x % int(1000 * self.scale) == 0:
                        qp.setPen(QPen(color_a))
                    else:
                        qp.setPen(QPen(color_b))
                else:
                    qp.setPen(QPen(color_c))

                qp.drawLine(QPoint(x, 0), QPoint(x, self.height()))

        for x in range(int(self.height())):
            if x % int(50 * self.scale) == 0:
                if x % int(100 * self.scale) == 0:
                    if x % int(1000 * self.scale) == 0:
                        qp.setPen(QPen(color_a))
                    else:
                        qp.setPen(QPen(color_b))
                else:
                    qp.setPen(QPen(color_c))
                qp.drawLine(QPoint(0, x), QPoint(self.width(), x))

    def draw_connection(self, painter, connection):
        pass

    def mousePressEvent(self, QMouseEvent):
        if self.is_connecting:
            self.abort_connection()
        else:
            if QMouseEvent.buttons() & Qt.LeftButton:
                self.set_selected([])
                self.marquee_selection_frame = QRect(QMouseEvent.pos().x(),QMouseEvent.pos().y(), 0 ,0)
                self.is_marquee_selecting = True

            if QMouseEvent.buttons() & Qt.RightButton:
                 menu = NodeEditorContextMenu(self, self.mapToGlobal(QMouseEvent.pos()), QMouseEvent.pos())

    def mouseMoveEvent(self, QMouseEvent):
        if self.is_connecting and self.connection_drag:
            self.connection_drag[1] = QMouseEvent.pos()
            self.update()
        elif self.is_marquee_selecting:
            x = self.marquee_selection_frame.x()
            y = self.marquee_selection_frame.y()
            w = QMouseEvent.pos().x() - self.marquee_selection_frame.x()
            h = QMouseEvent.pos().y() - self.marquee_selection_frame.y()

            self.marquee_selection_frame = QRect(x, y, w, h)
            self.update()

            # pos = (QMouseEvent.pos() - self.offset)
            # target = self.mapToParent(pos)

    def mouseReleaseEvent(self, QMouseEvent):
        if self.is_marquee_selecting:
            sel = []
            for n in self.nodes:
                n_rect = QRect(n.pos(), n.size())
                if n_rect.intersects(self.marquee_selection_frame):
                    sel.append(n)
            self.set_selected(sel)
            self.is_marquee_selecting = False
            self.marquee_selection_frame = None
            self.update()

    def wheelEvent(self, QWheelEvent):
        if QWheelEvent.angleDelta().y() > 0:
            self.scale += 0.1
        else:
            if self.scale >= 0.2:
                self.scale -= 0.1

        self.onScale.emit(self.scale)
        self.update()

    def resizeEvent(self, QResizeEvent):
        super(NodeEditor, self).resizeEvent(QResizeEvent)
        self.lbl_compile_status.move(self.width() - 100, self.height() - 20)

    def paintEvent(self, QPaintEvent):
        super(NodeEditor, self).paintEvent(QPaintEvent)
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setWidth(2)
        qp.setPen(pen)

        if self.show_grid:
            self.paint_grid(qp)

        if self.marquee_selection_frame:
            pen.setColor(QColor(255, 160, 47))
            fill = QColor(255, 160, 47, 40)
            qp.setPen(pen)
            qp.drawRect(self.marquee_selection_frame)
            qp.fillRect(self.marquee_selection_frame, fill)

        if self.connection_drag:
            start = self.connection_drag[0]
            end = self.connection_drag[1]
            y_diff = ((end.x() - start.x()) * 0.2)

            path = QPainterPath()
            path.moveTo(self.connection_drag[0])
            mid1 = QPoint(start.x() + y_diff, end.y())
            mid2 = QPoint(end.x() - y_diff, start.y())

            path.cubicTo(mid2, mid1, end)

            # pen.setColor(c.color)
            qp.setPen(pen)
            qp.drawPath(path)

        for c in self.connections:
            path = QPainterPath()

            start = c.input_field.get_connection_location()
            end = c.output_field.get_connection_location()

            path.moveTo(start)
            # mid1 = QPoint(((c.end_point.x()) + c.start_point.x()) / 2, c.end_point.y())
            # mid2 = QPoint(((c.end_point.x()) + c.start_point.x()) / 2, c.start_point.y())
            y_diff = ((end.x() - start.x()) * 0.2)
            mid1 = QPoint(start.x() + y_diff, end.y())
            mid2 = QPoint(end.x() - y_diff, start.y())
            path.cubicTo(mid2, mid1, end)
            pen.setColor(c.input_field.data_type.color)
            qp.setPen(pen)
            qp.drawPath(path)
            # qp.drawPoint(mid1)
            # qp.drawPoint(mid2)

        qp.end()
    #endregion
    pass


class Node(QWidget):
    hasMoved = pyqtSignal(list)

    def __init__(self, parent, node_editor, operation):
        super(Node, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)

        self.unique_id = node_editor.get_unique_id()

        self.node_size = QSize(200,200)
        self.node_pos = QPoint(0,0)
        self.resize(200,200)

        self.header_height = 30
        self.field_height = 25
        self.font_size = 12
        self.compiled_rect = QRect(0,0,1,1)

        self.operation = operation
        self.name = operation.name
        self.node_editor = node_editor
        self.fields = []

        self.is_dragging = False
        self.is_selected = False


        self.is_compiled = False


        self.lbl_title = None

        self.fields_counter = 0


        self.init_ui()
        self.show()

    def init_ui(self):
        self.lbl_title = QLabel(self.operation.name, self)
        self.lbl_title.move(0,0)
        self.lbl_title.resize(self.width(), self.header_height)
        self.lbl_title.setAlignment(Qt.AlignCenter| Qt.AlignVCenter)
        self.lbl_title.setAttribute(Qt.WA_TranslucentBackground)


        for i in self.operation.input_slots:
            self.add_field(InputField(self, self, i, self.fields_counter))
            self.fields_counter += 1
        for o in self.operation.output_slots:
            self.add_field(OutputField(self, self, o, self.fields_counter))
            self.fields_counter += 1
        # self.add_field(InputField(self, self, DT_Image))
        # self.add_field(InputField(self, self, DT_Image))
        # self.add_field(OutputField(self, self, DT_Image))
        # self.add_field(OutputField(self, self, DT_Image))
        # self.add_field(OutputField(self, self, DT_Image))

        # total_height = self.header_height + (self.field_height * len(self.fields)) + 20
        # self.node_size = QSize(200, total_height)

    def add_field(self, field):
        y = self.field_height * len(self.fields) + self.header_height
        field.move(0, y)
        self.fields.append(field)

    def compile(self):
        result = True
        self.operation.result = []
        for p in self.fields:
            if p.is_input:
                if p.connection is not None:
                    result = p.connection.input_field.node.compile()
                elif p.data_type_slot.default_value:
                    result = p.data_type_slot.default_value
                else:
                    result = False
                    break

        self.is_compiled = result

        return result

    def perform(self):
        if len(self.operation.result) == 0:
            args = []
            for p in self.fields:
                if p.is_input:
                    if p.connection is not None:
                        args.append(p.connection.input_field.node.perform())
                    else:
                        args.append(p.data_type_slot.default_value)

            self.operation.perform(args)
        return self.operation.result

    def select(self, selected = True):
        if selected:
            self.is_selected = True
        else:
            self.is_selected = False

    def get_connections(self):
        conns = []
        for f in self.fields:
            if isinstance(f, InputField):
                if f.connection:
                    conns.append(f.connection)
            else:
                conns.extend(f.connections)
        return conns

    def update_output_types(self):
        input_types = []
        for f in self.fields:
            if f.is_input:
                if f.connection:
                    input_types.append(f.connection.input_field.data_type)
                else:
                    input_types.append(f.data_type)

        output_types = self.operation.update_out_types(input_types)
        out_fields = []

        for f in self.fields:
            if not f.is_input:
                out_fields.append(f)

        for i, f in enumerate(out_fields):
            if not f.is_input:
                f.change_data_type(output_types[i](f))
                print f.data_type
        self.update()

    def serialize(self):
        fields = []
        for f in self.fields:
            fields.append(f.field_id)
        data = dict(
            unique_id = self.unique_id,
            pos=(self.node_pos.x(), self.node_pos.y()),
            operation=self.operation.__class__.__name__,
            fields=fields
            # size= (self.node_size.height(), self.node_size.width())

        )
        return data

    #region Events
    def scale(self, scale):
        self.resize(self.node_size.width() * scale, self.node_size.height() * scale)
        self.move(self.node_pos * scale)

        font = self.lbl_title.font()
        font.setPointSize(self.font_size * scale)
        self.lbl_title.setFont(font)
        self.lbl_title.resize(self.width(), self.header_height * scale)

        for i, field in enumerate(self.fields):
            y = self.field_height* scale * i + self.header_height * scale
            field.move(0, y)
            field.scale(scale)

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
                self.offset = QMouseEvent.pos()
                self.is_dragging = True
                if not self.is_selected:
                    self.node_editor.set_selected([self])

        else:
            QMouseEvent.ignore()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.is_dragging:
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos)
                delta = target - self.pos()
                self.move(target)
                self.node_editor.update()
                self.node_pos = target / self.node_editor.scale
                self.hasMoved.emit([self, delta])

        else:
            QMouseEvent.ignore()

    def mouseReleaseEvent(self, QMouseEvent):
        self.is_dragging = False

    def moveEvent(self, QMoveEvent):
        super(Node, self).moveEvent(QMoveEvent)
        self.node_pos = self.pos() / self.node_editor.scale

    def paintEvent(self, QPaintEvent):
        scale = self.node_editor.scale
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setWidth(3)
        pen.setColor(QColor(120,120,120,150))
        qp.setPen(pen)

        self.compiled_rect = QRect(5 * scale, self.height() - 20 * scale, self.width() -10 * scale, 10 * scale)

        if self.is_compiled:
            qp.fillRect(self.compiled_rect, QColor(51,205,95, 100))
        else:
            qp.fillRect(self.compiled_rect, QColor(244,27,27, 100))

        qp.fillRect(QRect(0,0,self.width(), self.header_height * scale), QColor(30,30,30, 100))

        if self.is_selected:
            pen.setColor(QColor(255, 160, 47, 150))
            qp.setPen(pen)

        qp.drawRect(QRect(0,0,self.width(), self.header_height * scale))

        qp.drawRect(self.rect())
        qp.end()
    #endregion
    pass


class NodeField(QWidget):
    def __init__(self, parent, node, data_slot, field_id, is_input = False):
        super(NodeField, self).__init__(parent)

        self.field_id = field_id
        self.font_size = 10

        self.setAttribute(Qt.WA_MouseTracking, True)

        self.node = node
        self.data_type_slot = data_slot
        self.data_type = data_slot.data_type(self)

        # self.info_widget = self.data_type
        self.info_widget = QRect(0,0,1,1)
        self.pin_widget = NodePin(self)

        self.is_hovered = False
        self.is_input = is_input

        self.resize(self.node.width(), self.node.field_height)
        self.init_ui()
        self.show()

    def init_ui(self):
        pass

    def add_connection(self, connection):
        pass

    def remove_connection(self, connection):
        pass

    def change_data_type(self, new):
        # self.info_widget.deleteLater()
        # self.info_widget = new
        self.data_type = new

    def get_connection_location(self):
        pass

    def scale(self, scale):
        self.resize(self.node.width(), self.node.field_height * scale)
        # self.info_widget.scale(scale)
        self.pin_widget.scale(scale)

    def mouseMoveEvent(self, QMouseEvent):
        QMouseEvent.ignore()

    def enterEvent(self, QEvent):
        self.is_hovered = True

    def leaveEvent(self, QEvent):
        self.is_hovered = False

    def paintEvent(self, QPaintEvent):
        # self.resize(self.node.width(), self.node.field_height)
        # self.inner_rect = QRect(self.x() + 2, self.y() + 2, self.width() - 2, self.height() - 2)

        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setWidth(2)
        if self.is_hovered:
            pen.setColor(QColor(255,160,47))
            fill = QColor(255,160,47, 40)
        else:
            pen.setColor(QColor(50,50,50))
            fill = QColor(120, 120, 120, 30)
        qp.setPen(pen)


        qp.fillRect(self.rect(), fill)
        qp.drawRect(self.rect())

        #INFO WIDGET BAckground
        # fill = QColor(30, 30, 30, 100)
        # qp.fillRect(self.info_widget, fill)

        pen.setColor(self.data_type.color)
        font = qp.font()
        font.setPointSize(self.font_size * self.node.node_editor.scale)
        qp.setFont(font)
        qp.setPen(pen)
        qp.drawText(self.info_widget,Qt.AlignCenter|Qt.AlignVCenter, self.data_type_slot.name)



        qp.end()


class InputField(NodeField):
    def __init__(self, parent, node, data_slot, field_id):
        super(InputField, self).__init__(parent, node, data_slot, field_id, is_input=True)
        self.connection = None


    def init_ui(self):
        self.pin_widget.move(5,5)
        #self.info_widget.move(25,5)
        #self.info_widget = QRect(25,0,self.width() - 25, self.height())
        self.info_widget = self.rect()

    def add_connection(self, connection):
        if self.connection:
            self.node.node_editor.remove_connection(self.connection)
        self.connection = connection

    def remove_connection(self, connection):
        self.connection = None

    def get_connection_location(self):
        return self.mapTo(self.node.node_editor, (QPoint(12, 12) * self.node.node_editor.scale))

    def scale(self, scale):
        super(InputField, self).scale(scale)
        self.pin_widget.move(5 * scale, 5 * scale)
        #self.info_widget = QRect(25 * scale, 5, self.width() - 25 * scale - 10 * scale - 15 * scale, self.height() - 10 * scale)
        self.info_widget = self.rect()
        # self.info_widget.move(25 * scale, 5 * scale)
        # self.info_widget.resize(self.width() - 25 * scale, self.height())

    def paintEvent(self, QPaintEvent):
        super(InputField, self).paintEvent(QPaintEvent)


class OutputField(NodeField):
    def __init__(self, parent, node, data_slot, field_id):
        super(OutputField, self).__init__(parent, node, data_slot, field_id)
        self.connections = []

    def init_ui(self):
        self.pin_widget.move(self.width() - 25, 5)
        #self.info_widget = QRect(5, 5, self.width() - 25, self.height() - 10)
        # self.info_widget.move(5, 5)
        self.info_widget = self.rect()

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)

    def get_connection_location(self):
        offset = 12 * self.node.node_editor.scale
        return self.mapTo(self.node.node_editor, QPoint(self.width() - offset, offset))

    def scale(self, scale):
        super(OutputField, self).scale(scale)
        self.pin_widget.move(self.width() - 25 * scale, 5 * scale)
        # self.info_widget = QRect(0 + 15, 5 * scale, self.width() - 25 * scale - 10 * scale, self.height() - 10 * scale)
        self.info_widget = self.rect()
        # self.info_widget.move(5 * scale, 5 * scale)
        # self.info_widget.resize(self.width() - 25 * scale, self.height())

    def paintEvent(self, QPaintEvent):
        super(OutputField, self).paintEvent(QPaintEvent)


class NodePin(QWidget):
    def __init__(self, parent):
        super(NodePin, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.pin_size = QSize(15,15)
        self.resize(self.pin_size)
        self.field = parent

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            self.field.node.node_editor.on_pin_clicked(self.field)


        elif QMouseEvent.buttons() & Qt.RightButton:
            pass

    def scale(self, scale):
        self.resize(self.pin_size * scale)

    def paintEvent(self, QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setWidth(2)
        pen.setColor(self.field.data_type.color)
        qp.setPen(pen)
        qp.drawEllipse(QRect(self.rect().x() + 1, self.rect().y() + 1, self.rect().width() - 2, self.rect().height() - 2))
        qp.end()


class Connection(QObject):
    def __init__(self, node_editor):
        super(Connection, self).__init__()

        self.unique_id = node_editor.get_unique_id()

        self.input_field = None
        self.output_field = None

    def verify_types(self):
        if isinstance(self.input_field.data_type, self.output_field.data_type.__class__):
            return True
        else:
            return False

    def serialize(self):
        data = dict(
            unique_id = self.unique_id,
            input_node = self.input_field.node.unique_id,
            input_field = self.input_field.field_id,
            output_node=self.output_field.node.unique_id,
            output_field = self.output_field.field_id
        )
        return data
    def set_input_pin(self, pin):
        self.input_field = pin

    def set_output_pin(self, pin):
        self.output_field = pin


class NodeEditorContextMenu(QMenu):
    def __init__(self, node_editor, pos, node_pos):
        super(NodeEditorContextMenu, self).__init__(node_editor)
        self.node_editor = node_editor
        self.node_menu = self.addMenu("New Node")
        self.input_menu = self.node_menu.addMenu("Input")
        self.a_read_frame = self.input_menu.addAction("Read Frames")
        self.a_movie_colormetrics = self.input_menu.addAction("Movie Colorimetric")
        self.a_range_reader = self.input_menu.addAction("Range Reader")

        self.input_menu.addAction("TimeRange Colorimetric")

        self.a_scalar = self.input_menu.addAction("Scalar")
        self.a_vector2 = self.input_menu.addAction("Vector2D")
        self.computation_menu = self.node_menu.addMenu("Computation")
        self.node_pos = node_pos

        self.a_add = self.computation_menu.addAction("Addition")
        self.a_subtraction = self.computation_menu.addAction("Subtraction")
        self.a_multiply = self.computation_menu.addAction("Multiplication")
        self.a_division = self.computation_menu.addAction("Division")
        self.computation_menu.addSeparator()

        self.a_resize = self.computation_menu.addAction("Resize")
        self.a_mean = self.computation_menu.addAction("Mean")
        self.a_normalization = self.computation_menu.addAction("Normalization")
        self.a_color_histogram = self.computation_menu.addAction("Color Histogram")

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
        self.action_save.triggered.connect(partial(self.node_editor.save_script, "script.vis"))
        self.action_load.triggered.connect(partial(self.node_editor.load_script, "script.vis"))
        self.a_read_frame.triggered.connect(partial(self.node_editor.create_node, OperationFrameReader(), self.node_pos))
        self.a_range_reader.triggered.connect(partial(self.node_editor.create_node, OperationRangeReader(), self.node_pos))

        self.a_scalar.triggered.connect(partial(self.node_editor.create_node, OperationScalar(), self.node_pos ))
        self.a_vector2.triggered.connect(partial(self.node_editor.create_node, OperationVector2(), self.node_pos ))
        # Action Binding
        # Computation
        self.a_color2img.triggered.connect(partial(self.node_editor.create_node, OperationColor2Image(), self.node_pos ))
        self.a_add.triggered.connect(partial(self.node_editor.create_node, OperationAdd(), self.node_pos ))
        self.a_subtraction.triggered.connect(partial(self.node_editor.create_node, OperationSubtract(), self.node_pos ))
        self.a_multiply.triggered.connect(partial(self.node_editor.create_node, OperationMultiply(), self.node_pos ))
        self.a_division.triggered.connect(partial(self.node_editor.create_node, OperationDivision(), self.node_pos ))
        self.a_mean.triggered.connect(partial(self.node_editor.create_node, OperationMean(), self.node_pos ))
        self.a_normalization.triggered.connect(partial(self.node_editor.create_node, OperationNormalize(), self.node_pos))
        self.a_color_histogram.triggered.connect(partial(self.node_editor.create_node, OperationColorHistogram(), self.node_pos))
        # Visualization
        self.a_show_img.triggered.connect(partial(self.node_editor.create_node, OperationShowImage(), self.node_pos ))
        self.a_bar.triggered.connect(partial(self.node_editor.create_node, OperationBarPlot(), self.node_pos ))



        self.popup(pos)

