from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import os
from functools import partial
from vian.core.node_editor.operations import *
from vian.core.node_editor.datatypes import *
from vian.core.gui.ewidgetbase import EDockWidget
from vian.core.data.interfaces import *
from vian.core.data.computation import tuple2point

import json
NODETYPE_INPUT_NODE = 0
NODETYPE_OUTPUT_NODE = 1

# These are duplicates of the NODE and NODE_SCRIPT in vian.core/data/containers.py!!!
NODE = 8
NODE_SCRIPT = 9


class ExecutorSignals(QObject):
    on_finish_execution = pyqtSignal(bool)


class ScriptExecutor(QRunnable):
    def __init__(self, nodes, project, node_editor):
        super(ScriptExecutor, self).__init__()
        self.nodes = nodes
        self.project = project
        self.signals = ExecutorSignals()
        self.signals.on_finish_execution.connect(node_editor.on_script_execution_finished)

    @pyqtSlot()
    def run(self):
        try:
            for n in self.nodes:
                if n.operation.is_final_node and n.is_compiled:
                    n.perform(self.project)

            for n in self.nodes:
                n.is_running = False

            res = True
        except Exception as e:
            print("")
            print(n)
            print("Script Executor Failed")
            print(e)
            print("")

            res = False


        # finally:
        self.signals.on_finish_execution.emit(res)


class NodeEditorDock(EDockWidget):
    def __init__(self, main_window):
        super(NodeEditorDock, self).__init__(main_window, False)
        self.setWindowTitle("Node Editor")
        self.node_editor = NodeEditor(self, None)
        self.setWidget(self.node_editor)


class NodeEditor(QWidget, IProjectChangeNotify):
    onScale = pyqtSignal(float)

    def __init__(self, parent, result_visualizer):
        super(NodeEditor, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.show_grid = True

        # self.project = parent.project()

        self.result_visualizer = result_visualizer

        # self.current_script = self.project.current_script
        self.nodes = []
        self.connections = []
        self.selected_nodes = []
        self.id_counter = 1000000

        self.is_connecting = False
        self.is_marquee_selecting = False
        self.marquee_selection_frame = None

        self.scale = 1.0
        self.relative_corner = QPoint(0, 0)
        self.is_dragging = False

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(8)
        self.thread_pool.maxThreadCount()

        self.connection_drag = None

        self.is_compiled = False
        self.lbl_compile_status = QLabel("Not Compiled", self)

        self.show()

    def create_node(self, operation, pos):
        node = self.current_script.create_node(operation, pos / self.scale)
        # self.add_node(node, pos)
        # node.scale(self.scale)

    def add_node(self, node, pos = (QPoint(200,200))):
        self.nodes.append(node)
        node.move(pos + self.relative_corner)

        self.onScale.connect(node.scale)
        node.hasMoved.connect(self.on_node_has_moved)

        self.onScale.emit(self.scale)
        node.show()
        return node

    def remove_nodes(self, nodes, remove_from_project = False):
        if not isinstance(nodes, list):
            nodes = [nodes]

        for n in nodes:
            conns = n.get_connections()
            for c in conns:
                c.input_field.remove_connection(c)
                c.output_field.remove_connection(c)
                if c in self.connections:
                    self.connections.remove(c)

                if remove_from_project:
                    self.current_script.remove_connection(c.connection_object)

            if n in self.nodes:
                self.nodes.remove(n)

            n.node_object.node_widget = None

            if remove_from_project:
                self.current_script.remove_node(n.node_object, dispatch=False)

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
        self.compile()

        if self.is_compiled:
            executor = ScriptExecutor(self.nodes, self.project, self)
            self.thread_pool.start(executor)
            # for n in self.nodes:
            #     if n.operation.is_final_node and n.is_compiled:
            #         n.perform()
        else:
            print("Not Compiled")

    def on_script_execution_finished(self, success):
        if success:
            name = self.project.current_script.get_name() + "_result"
            script_id = self.project.current_script.unique_id
            final_node_ids = []
            node_results = []
            for n in self.nodes:
                if n.operation.is_final_node and n.operation.result is not None:
                    self.result_visualizer.visualize(n.operation)

                    node_results.append( n.operation.result)
                    final_node_ids.append(n.node_object.get_id())

            self.project.create_node_analysis(name, node_results, script_id, final_node_ids)

    @pyqtSlot(list)
    def on_modify_project(self, l):
        l[0](self.project, l[1])

    def on_pin_clicked(self, field):
        if not self.is_connecting:
            self.begin_connection(field)
        else:
            self.finish_connection(field)

    def on_node_has_moved(self, moveEvent):
        for n in self.selected_nodes:
            if n is not moveEvent[0]:
                n.node_object.set_position(n.pos() / self.scale + moveEvent[1] - (self.relative_corner / self.scale))
                n.move(n.pos() + moveEvent[1])

    def get_unique_id(self):
        self.id_counter += 1
        return self.id_counter

    def get_by_ID(self, id):
        return self.project.get_by_id(id)

    def clear(self):
        conns = [connection for connection in self.connections]
        nodes = [node for node in self.nodes]

        self.remove_connection(conns, remove_in_project = False)
        self.remove_nodes(nodes, remove_from_project=False)

    def set_current_script(self, script):
        self.clear()
        self.current_script = script
        self.update_node_editor()

    def update_node_editor(self):
        for node in self.current_script.nodes:
            if isinstance(node.operation, OperationIterate):
                new = LoopNode(self, self, node)
            else:
                new = Node(self, self, node)
            node.node_widget = new
            self.add_node(new, tuple2point(node.get_position()))

        for conn in self.current_script.connections:
            new = Connection(self)
            new.connection_object = conn
            self.connections.append(new)

            input_node = self.find_node_by_id(conn.input_node)
            output_node = self.find_node_by_id(conn.output_node)

            new.set_input_field(input_node.fields[conn.input_pin_id])
            new.set_output_field(output_node.fields[conn.output_pin_id])

            new.input_field.add_connection(new)
            new.output_field.add_connection(new)
            new.output_field.node.update_output_types()

    def find_node_by_id(self, node_id):
        for node in self.nodes:
            if node.node_object.unique_id == node_id:
                return node
        return None


    #region IProjectNotify
    def on_loaded(self, project):
        self.project = project
        self.set_current_script(project.current_script)

        for n in self.nodes:
            if n.operation.is_final_node and n.operation.result is not None:
                self.result_visualizer.visualize(n.operation)

    def on_changed(self, project, item):
        self.clear()
        self.current_script = project.current_script
        self.update_node_editor()

    def on_selected(self, sender, selected):
        pass
    #endregion

    #region Connections
    def begin_connection(self, field):
        conn = Connection(self)
        if isinstance(field, InputField):
            conn.set_output_field(field)
        else:
            conn.set_input_field(field)

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

                conn = self.current_script.create_connection(connection)
                connection.set_connection_object(conn)

            else:
                self.abort_connection()

            self.connection_drag = None
            self.is_connecting = False
            self.update()

    def abort_connection(self):
        self.connection_drag = None
        self.is_connecting = False
        self.update()

    def remove_connection(self, connections,remove_in_project=True):
        if not isinstance(connections, list):
            connections = [connections]
        for c in connections:
            c.input_field.remove_connection(c)
            c.output_field.remove_connection(c)
            if c in self.connections:
                self.connections.remove(c)

            if remove_in_project:
                self.current_script.remove_connection(c.connection_object)
            self.update()

    #endregion

    #region EventHandlers
    def set_selected(self, nodes, dispatch = False):
        to_select = []
        for n in nodes:
            if isinstance(n, Node):
                to_select.append(n)

        for n in self.selected_nodes:
            n.select(False)
            self.update()
        self.selected_nodes = nodes
        project_containers = []
        for n in to_select:
            n.select(True)
            project_containers.append(n.node_object)
            self.update()

        if dispatch:
            self.project.set_selected(self, project_containers)

    def paint_grid(self, qp):
        color_a = QColor(10,10,10,100)
        color_b = QColor(50,50,50,100)
        color_c = QColor(80,80,80,100)
        for x in range(int(self.width() - self.relative_corner.x())):
            if x % int(50 * self.scale) == 0:
                if x % int(100 * self.scale) == 0:
                    if x % int(1000 * self.scale) == 0:
                        qp.setPen(QPen(color_a))
                    else:
                        qp.setPen(QPen(color_b))
                else:
                    qp.setPen(QPen(color_c))

                qp.drawLine(QPoint(x + self.relative_corner.x(), 0), QPoint(x + self.relative_corner.x(), self.height()))

        for x in range(int(self.height() - self.relative_corner.y())):
            if x % int(50 * self.scale) == 0:
                if x % int(100 * self.scale) == 0:
                    if x % int(1000 * self.scale) == 0:
                        qp.setPen(QPen(color_a))
                    else:
                        qp.setPen(QPen(color_b))
                else:
                    qp.setPen(QPen(color_c))
                qp.drawLine(QPoint(0, x + self.relative_corner.y()), QPoint(self.width(), x + self.relative_corner.y()))

    def draw_connection(self, painter, connection):
        pass

    def mousePressEvent(self, QMouseEvent):
        if self.is_connecting:
            self.abort_connection()
        else:
            if QMouseEvent.buttons() & Qt.LeftButton:
                self.set_selected([], True)
                self.marquee_selection_frame = QRect(QMouseEvent.pos().x(),QMouseEvent.pos().y(), 0 ,0)
                self.is_marquee_selecting = True

            if QMouseEvent.buttons() & Qt.RightButton:
                 menu = NodeEditorContextMenu(self, self.mapToGlobal(QMouseEvent.pos()), QMouseEvent.pos())

            if QMouseEvent.buttons() & Qt.MiddleButton:
                self.offset = QMouseEvent.pos()
                self.is_dragging = True

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

        elif self.is_dragging:
            # Dragging the GRID

            pos = (QMouseEvent.pos() - self.offset)
            if (self.relative_corner + pos).x() > 0:
                pos = QPoint(0, pos.y())
            if (self.relative_corner + pos).y() > 0:
                pos = QPoint(pos.x(), 0)
            self.offset = QMouseEvent.pos()
            self.relative_corner = pos + self.relative_corner


            for n in self.nodes:
                n.move(n.pos() + pos)


            self.update()

    def mouseReleaseEvent(self, QMouseEvent):
        if self.is_marquee_selecting:
            sel = []
            for n in self.nodes:
                n_rect = QRect(n.pos(), n.size())
                if n_rect.intersects(self.marquee_selection_frame):
                    sel.append(n)
            self.set_selected(sel, True)
            self.is_marquee_selecting = False
            self.marquee_selection_frame = None
            self.update()

        elif self.is_dragging:
            self.is_dragging = False

    def wheelEvent(self, QWheelEvent):

        old = QWheelEvent.pos() * self.scale - self.relative_corner * self.scale
        offset_old = QPoint((self.size() / 2).width(), (self.size() / 2).height()) * self.scale
        old_c = self.relative_corner

        if QWheelEvent.angleDelta().y() > 0:
            self.scale += 0.1
        else:
            if self.scale >= 0.2:
                self.scale -= 0.1

        center_point = (QWheelEvent.pos()  - self.relative_corner) * self.scale

        if QWheelEvent.angleDelta().y() > 0:
            new = old_c - (center_point - old) / self.scale  # - ((center_point-old)/ self.scale
        else:
            new = old_c - (center_point - old) / self.scale  # - ((center_point-old)/ self.scale


        self.relative_corner = QPoint(np.clip(new.x(), None, 0), np.clip(new.y(), None, 0))
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
            y_diff = ((end.x() - start.x()) * 0.2)
            mid1 = QPoint(start.x() + y_diff, end.y())
            mid2 = QPoint(end.x() - y_diff, start.y())
            path.cubicTo(mid2, mid1, end)
            pen.setColor(c.input_field.data_type.color)
            qp.setPen(pen)
            qp.drawPath(path)
        qp.end()
    #endregion
    pass


class Node(QWidget, IHasName):
    hasMoved = pyqtSignal(list)
    def __init__(self, parent, node_editor, node_object):
        super(Node, self).__init__(parent)
        self.setAttribute(Qt.WA_MouseTracking, True)
        self.node_object = node_object

        # self.unique_id = node_editor.get_unique_id()
        self.unique_id = node_object.unique_id
        self.node_size = QSize(200,200)
        self.node_pos = QPoint(0,0)
        self.resize(200,200)

        self.header_height = 30
        self.field_height = 25
        self.font_size = 12
        self.compiled_rect = QRect(0,0,1,1)
        self.progress_rect = QRect(0,0,1,1)

        self.operation = node_object.operation
        self.name = node_object.operation.name
        self.node_editor = node_editor
        self.fields = []

        self.operation.onProgress.connect(self.onProgress)

        self.is_dragging = False
        self.is_selected = False

        self.is_compiled = False

        self.is_running = False
        self.current_progress = 0.0

        self.lbl_title = None

        self.fields_counter = 0
        self.n_input_fields = 0
        self.n_output_fields = 0

        self.display_cache_size = True
        self.cache_size = 0


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
            self.n_input_fields += 1

        for o in self.operation.output_slots:
            self.add_field(OutputField(self, self, o, self.fields_counter))
            self.fields_counter += 1
            self.n_output_fields += 1
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

    def compile(self, loop_compile = False):
        result = True
        self.operation.reset_result()

        for p in self.fields:
            if p.is_input:
                if p.connection is not None:
                    result = p.connection.input_field.node.compile(loop_compile)
                elif p.data_type_slot.default_value is not None:
                    result = p.data_type_slot.default_value is not None
                else:
                    result = False
                    break

        self.is_compiled = result

        return result

    def perform(self, project, perform_loop_nodes = False):
        # If there is no Result in cache, or this node allows multiple execution, execute.
        # Else return the existing cache
        if len(self.operation.result) == 0 or self.operation.multi_execute:
            args = []

            # Executing all Nodes before this one
            for p in self.fields:
                if p.is_input:
                    # IF has Connected Nodes, execute those
                    if p.connection is not None:
                        pin_id = p.connection.connection_object.input_pin_id - p.connection.input_field.node.n_input_fields
                        print(pin_id)
                        args.append(p.connection.input_field.node.perform(project, perform_loop_nodes)[pin_id])
                    # ELSE return default value
                    else:
                        args.append(p.data_type_slot.default_value)

            self.is_running = True

            # EXECUTE THIS NODE
            # If this is a loop node, and we are currently executing a loop,
            # resp, vice-versa execute the node. This makes sure, that the loop nodes are not executed,
            # after the loop finished and the executor is moving down the graph
            if self.operation.is_in_loop_node == perform_loop_nodes:
                if isinstance(self.operation, ProjectOperation):
                    self.operation.perform_modify(args, self.onProgress, project, self.node_editor.on_modify_project)
                else:
                    self.operation.perform(args, self.onProgress, project)

            if len(self.operation.result)>0:
                # This may fail, when the array is not shaped in like numpy wants us to.
                # The cache size is cosmetic anyway
                try:
                    self.cache_size = np.array(self.operation.result[0]).nbytes
                except Exception as e:
                    self.cache_size = 0
            self.update()

        return self.operation.result


    # OLDCODE
    # def on_perform_finished(self):
    #     """
    #     Informing all proceeding input fields, that the result is ready
    #     :return:
    #     """
    #
    #     for f in self.fields:
    #         if isinstance(f, OutputField):
    #             for c in f.connections:
    #                 c.output_field.on_recieved_result()
    #
    #
    # def check_result_availability(self):
    #     """
    #     Loop over all input nodes and check if this node can start it's oepration
    #     :return:
    #     """
    #     has_all = True
    #     for f in self.fields:
    #         if isinstance(f, InputField):
    #             if not f.has_result:
    #                 has_all = False
    #                 break
    #     if has_all:
    #         self.perform()
    @pyqtSlot(float)
    def onProgress(self, float):
        self.current_progress = float
        self.update()

    def select(self, selected = True):
        if selected:
            self.is_selected = True
        else:
            self.is_selected = False

    def get_connections(self):
        conns = []
        for f in self.fields:
            # if it is an Input field it can only have one input
            if isinstance(f, InputField):
                if f.connection:
                    conns.append(f.connection)
            # Else it may have several
            else:
                conns.extend(f.connections)
        return conns

    def update_output_types(self):
        input_types = []
        for f in self.fields:
            if f.is_input:
                if f.connection:
                    input_types.append(f.connection.input_field.data_type_slot)

                    # input_types.append(f.connection.input_field.data_type)
                    f.change_data_type(f.connection.input_field.data_type_slot.data_type())
                else:
                    input_types.append(f.data_type_slot)
                    f.reset_data_type()


        output_types = self.operation.update_out_types(input_types)
        out_fields = []

        for f in self.fields:
            if not f.is_input:
                out_fields.append(f)

        for i, f in enumerate(out_fields):
            if not f.is_input:
                f.change_data_type(output_types[i](f))
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

    def get_type(self):
        return NODE

    def get_name(self):
        return self.name

    def get_leaf_nodes(self, result, stop_on_loop = False):
        out = self.get_out_connections()
        if len(out) > 0 and not (not self.operation.execute_output_fields_in_loop and stop_on_loop):
            for o in out:
                o.output_field.node.get_leaf_nodes(result, stop_on_loop)
        else:
            if self not in result:
                result.append(self)

    def node_walk_down(self, result, stop_on_loop=True):
        out = self.get_out_connections()
        if len(out)>0 and not (not self.operation.execute_output_fields_in_loop and stop_on_loop):
            for o in out:
                o.output_field.node.node_walk_down(result)
        result.append(self)

    def get_output_fields(self):
        output_fields = []
        for f in self.fields:
            if isinstance(f, OutputField):
                output_fields.append(f)
        return output_fields

    def get_input_fields(self):
        input_fields = []
        for f in self.fields:
            if isinstance(f, InputField):
                input_fields.append(f)
        return input_fields

    def get_out_connections(self):
        fields = self.get_output_fields()
        conns = []
        for f in fields:
            conns.extend(f.connections)
        return conns


    #region Events
    def scale(self, scale):
        self.resize(self.node_object.get_size()[0]* scale, self.node_object.get_size()[1] * scale)
        self.move(tuple2point(self.node_object.get_position()) * scale + self.node_editor.relative_corner)

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
                    self.node_editor.set_selected([self], True)

        else:
            if not self.is_selected:
                self.node_editor.set_selected([self], True)
            QMouseEvent.ignore()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.is_dragging:
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos)
                delta = target - self.pos()
                self.move(target)
                self.node_editor.update()
                self.node_pos = target / self.node_editor.scale - self.node_editor.relative_corner / self.node_editor.scale
                self.hasMoved.emit([self, delta])

                self.node_object.set_position(self.node_pos)

        else:
            QMouseEvent.ignore()

    def mouseReleaseEvent(self, QMouseEvent):
        self.is_dragging = False
        super(Node, self).mouseReleaseEvent(QMouseEvent)

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
        self.progress_rect = QRectF(self.width() - (30 * scale), self.height() - 45 * scale, 20 * scale, 20 * scale)

        if self.is_compiled:
            qp.fillRect(self.compiled_rect, QColor(51,205,95, 100))
        else:
            qp.fillRect(self.compiled_rect, QColor(244,27,27, 100))

        qp.fillRect(QRect(0,0,self.width(), self.header_height * scale), QColor(30,30,30, 100))

        if self.is_selected:
            pen.setColor(QColor(255, 160, 47, 150))
            qp.setPen(pen)

        qp.drawRect(QRect(0,0,self.width(), self.header_height * scale))
        if self.operation.is_in_loop_node:
            qp.fillRect(QRect(0, 0, self.width(), self.header_height * scale), QColor(165,186,42, 150))

        qp.drawRect(self.rect())
        if self.display_cache_size + self.cache_size > 0.0:
            pen.setColor(QColor(200,200,200,150))
            font = qp.font()
            font.setPointSize(8 * scale)
            qp.setFont(font)
            qp.setPen(pen)

            cache_widget = QRect(10 * scale, self.height() - 45 * scale, self.width(), 20 * scale)
            qp.drawText(cache_widget, Qt.AlignLeft | Qt.AlignVCenter, str(round(float(self.cache_size) / 1000000,2)) + " MB")

        # if self.operation.is_in_loop_node:
        #     loop_widget = QRect(40 * scale, self.height() - 45 * scale, self.width(), 20 * scale)
        #     qp.drawText(loop_widget, Qt.AlignLeft | Qt.AlignVCenter, "Loop Node")

        if self.is_running:
            path = QPainterPath()
            path.moveTo(QPoint(self.progress_rect.x() + self.progress_rect.width()/2,self.progress_rect.y() + self.progress_rect.height()/2))
            path.arcTo(self.progress_rect, -90, - self.current_progress * 360 + 0)
            if self.current_progress == 1.0:
                qp.fillPath(path, QColor(51,205,95, 100))
            else:
                qp.fillPath(path, QColor(255, 160, 47, 100))

            pen.setColor(QColor(37, 37, 37, 255))
            pen.setWidth(1)
            qp.setPen(pen)
            qp.drawPath(path)
        qp.end()
    #endregion
    pass


class LoopNode(Node):
    def __init__(self, parent, node_editor, node_object):
        super(LoopNode, self).__init__(parent, node_editor, node_object)

        # self.execution_Field = InputField(self, self, node_object.operation. self.fields_counter)
        # self.add_field(self.execution_Field)

        # This is the Field which should be performed first
        self.execution_field = self.fields[1]
        self.loop_nodes = []
        self.execution_tails = []

    def perform(self, project, perform_loop_nodes = False):
        if len(self.operation.result) == 0:
            args = []
            for p in self.fields:
                if p.is_input:
                    if p.connection is not None:
                        pin_id = p.connection.connection_object.input_pin_id - p.connection.input_field.node.n_input_fields
                        args.append(p.connection.input_field.node.perform(project, perform_loop_nodes)[pin_id])
                    else:
                        args.append(p.data_type_slot.default_value)

            # print "Performing", self.name, args
            self.is_running = True
            has_more = True
            while(has_more):
                # print "Iteration", self.operation.current_index
                self.operation.perform(args, self.onProgress, project)
                self.execute_loop(project)
                has_more = self.operation.result[1]
                if has_more:
                    self.clear_loop_nodes()
        return self.operation.result

    def compile(self, loop_compile = False):
        if loop_compile:
            return True
        else:
            super(LoopNode, self).compile(loop_compile)

            self.execution_tails = []
            self.get_leaf_nodes(self.execution_tails, stop_on_loop=True)

            self.loop_nodes = []
            self.node_walk_down(self.loop_nodes, stop_on_loop=True)
            self.loop_nodes.remove(self)

            for n in self.loop_nodes:
                if n.operation.execute_output_fields_in_loop:
                    n.operation.is_in_loop_node = True

                # Include all Nodes which are not directly connected to the Loop Node
                for f in n.get_input_fields():
                    if f.connection:
                        node = f.connection.input_field.node
                        if node not in self.loop_nodes and node is not self:
                            self.loop_nodes.append(node)
                            if node.operation.execute_output_fields_in_loop:
                                f.connection.input_field.node.operation.is_in_loop_node = True

            result = True
            for e in self.execution_tails:
                result = e.compile(loop_compile=True)
                e.operation.is_in_loop_node = True

            return result

    def execute_loop(self, project):
        # Execute all leaf nodes of the Loop
        for i, e in enumerate(self.execution_tails):
            e.perform(project, perform_loop_nodes = True)


    def clear_loop_nodes(self):
        # Clear all Cached Results within the Loop Nodes,
        # make sure that the main execution graph skips the nodes within the loop after the loops has been executed
        for e in self.loop_nodes:
            if e.operation.execute_output_fields_in_loop:
                e.operation.reset_result()


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
        self.data_type_slot.data_type = new.__class__
        self.data_type = new

    def reset_data_type(self):
        self.data_type_slot.data_type = self.data_type_slot.default_data_type
        self.data_type = self.data_type_slot.default_data_type()

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
    # receivedResult = pyqtSignal()

    def __init__(self, parent, node, data_slot, field_id):
        super(InputField, self).__init__(parent, node, data_slot, field_id, is_input=True)
        self.connection = None

        self.has_result = False

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
        self.connection_object = None
        self.input_field = None
        self.output_field = None

    def set_connection_object(self, conn):
        self.connection_object = conn

    def verify_types(self):
        if isinstance(self.input_field.data_type, self.output_field.data_type_slot.default_data_type):
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

    def set_input_field(self, field):
        self.input_field = field

    def set_output_field(self, field):
        self.output_field = field


class NodeEditorContextMenu(QMenu):
    def __init__(self, node_editor, pos, node_pos):
        super(NodeEditorContextMenu, self).__init__(node_editor)
        self.node_pos = node_pos

        self.node_editor = node_editor
        self.node_menu = self.addMenu("New Node")
        self.input_menu = self.node_menu.addMenu("Input")
        self.a_read_frame = self.input_menu.addAction("Read Frames")
        self.a_range_reader = self.input_menu.addAction("Range Reader")
        self.input_menu.addSeparator()
        self.a_project_node = self.input_menu.addAction("Project Node")
        self.input_menu.addSeparator()
        self.a_range=self.input_menu.addAction("Range")
        self.a_movie_colormetrics = self.input_menu.addAction("Movie Colorimetric")

        self.input_menu.addAction("TimeRange Colorimetric")

        self.a_scalar = self.input_menu.addAction("Scalar")
        self.a_vector2 = self.input_menu.addAction("Vector2D")

        self.computation_menu = self.node_menu.addMenu("Computation")
        self.a_add = self.computation_menu.addAction("Addition")
        self.a_subtraction = self.computation_menu.addAction("Subtraction")
        self.a_multiply = self.computation_menu.addAction("Multiplication")
        self.a_division = self.computation_menu.addAction("Division")
        self.computation_menu.addSeparator()

        self.a_resize = self.computation_menu.addAction("Resize")
        self.a_mean = self.computation_menu.addAction("Mean")
        self.a_normalization = self.computation_menu.addAction("Normalization")
        self.a_color_histogram = self.computation_menu.addAction("Color Histogram")
        self.computation_menu.addSeparator()

        self.a_random = self.computation_menu.addAction("Random Number")
        self.a_color2img = self.computation_menu.addAction("Color2Image")

        self.vis_menu = self.node_menu.addMenu("Visualization")
        self.a_show_img = self.vis_menu.addAction("Show Image")

        self.a_bar = self.vis_menu.addAction("Bar Plot")
        self.vis_menu.addAction("Color Histogram")
        self.vis_menu.addAction("Image Cluster")

        #MISC
        self.misc_menu = self.node_menu.addMenu("Miscellaneous")
        self.a_loop = self.misc_menu.addAction("For-Each-Loop")
        self.a_aggregate = self.misc_menu.addAction("Aggregation")
        self.misc_menu.addSeparator()
        self.a_print = self.misc_menu.addAction("Print to Console")
        self.misc_menu.addAction("To Analysis")

        self.action_compile = self.addAction("Compile")
        self.action_run = self.addAction("Run")
        self.node_editor = node_editor
        self.action_save = self.addAction("Save Script")
        self.action_load = self.addAction("Load Script")

        # PROJECT
        self.project_menu = self.node_menu.addMenu("Project")
        self.a_create_segment = self.project_menu.addAction("Create Segment")
        self.a_add_segmentation = self.project_menu.addAction("Add Segmentation")
        self.a_create_annotation = self.project_menu.addAction("Create SVGAnnotation")
        self.a_add_annotation_layer = self.project_menu.addAction("Add SVGAnnotation Layer")
        self.a_create_screenshot = self.project_menu.addAction("Create Screenshot")



        if len(node_editor.selected_nodes) > 0:
            self.a_delete = self.addAction("Delete Nodes")
            self.a_delete.triggered.connect(self.on_remove)

        self.action_compile.triggered.connect(self.node_editor.compile)
        self.action_run.triggered.connect(self.node_editor.run_script)
        # self.action_save.triggered.connect(partial(self.node_editor.save_script, "script.vis"))
        # self.action_load.triggered.connect(partial(self.node_editor.load_script, "script.vis"))
        self.a_read_frame.triggered.connect(partial(self.node_editor.create_node, OperationFrameReader(), self.node_pos))
        self.a_range_reader.triggered.connect(partial(self.node_editor.create_node, OperationRangeReader(), self.node_pos))

        self.a_project_node.triggered.connect(partial(self.node_editor.create_node, ProjectNode(), self.node_pos))
        self.a_range.triggered.connect(partial(self.node_editor.create_node, OperationRange(), self.node_pos))

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
        self.a_resize.triggered.connect(partial(self.node_editor.create_node, OperationResize(), self.node_pos))
        self.a_random.triggered.connect(partial(self.node_editor.create_node, OperationRandomInt(), self.node_pos))

        # Visualization
        self.a_show_img.triggered.connect(partial(self.node_editor.create_node, OperationShowImage(), self.node_pos ))
        self.a_bar.triggered.connect(partial(self.node_editor.create_node, OperationBarPlot(), self.node_pos ))

        self.a_loop.triggered.connect(partial(self.node_editor.create_node, OperationIterate(), self.node_pos))
        self.a_aggregate.triggered.connect(partial(self.node_editor.create_node, OperationAggregate(), self.node_pos))

        self.a_print.triggered.connect(partial(self.node_editor.create_node, OperationPrintToConsole(), self.node_pos))

        self.a_create_segment.triggered.connect(partial(self.node_editor.create_node, OperationCreateSegment(), self.node_pos))
        self.a_add_segmentation.triggered.connect(
            partial(self.node_editor.create_node, OperationAddSegmentation(), self.node_pos))

        self.a_create_annotation.triggered.connect(partial(self.node_editor.create_node, OperationCreateAnnotation(), self.node_pos))
        self.a_add_annotation_layer.triggered.connect(partial(self.node_editor.create_node, OperationAddAnnotationLayer(), self.node_pos))
        self.a_create_screenshot.triggered.connect(partial(self.node_editor.create_node, OperationCreateScreenshot(), self.node_pos))
        self.popup(pos)

    def on_remove(self):
        self.node_editor.remove_nodes(self.node_editor.selected_nodes, remove_from_project=True)