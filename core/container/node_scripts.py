import numpy as np
# from PyQt5.QtCore import QPoint, QSize

from core.data.enums import NODE_SCRIPT
from core.data.interfaces import IProjectContainer, IHasName, ISelectable
from core.node_editor.node_editor import NODE
from core.node_editor.operations import *
from core.node_editor.datatypes import *

class NodeScript(IProjectContainer, IHasName, ISelectable):
    def __init__(self, name = ""):
        IProjectContainer.__init__(self)
        self.name = name
        self.notes = ""
        self.nodes = []
        self.connections = []

    def create_node(self, operation, pos, unique_id = -1):
        new = NodeDescriptor(operation, pos, unique_id)
        new.set_project(self.project)
        self.add_node(new)
        return new

    def add_node(self, node):
        self.nodes.append(node)
        node.node_script = self
        self.dispatch_on_changed(item=self)

    def remove_node(self, node, dispatch = True):
        if node in self.nodes:
            self.nodes.remove(node)
            to_remove = []
            for i, conn in enumerate(self.connections):
                if conn.input_node == node.unique_id or conn.output_node == node.unique_id:
                    to_remove.append(conn)
            for conn in to_remove:
                self.remove_connection(conn)
            self.project.remove_from_id_list(node)

            if dispatch:
                self.dispatch_on_changed(item=self)

        else:
            print("Not Found")

    def create_connection(self, connection, unique_id = -1):
        new = ConnectionDescriptor(connection.input_field, connection.output_field,
                                   connection.input_field.field_id, connection.output_field.field_id)

        new.unique_id = unique_id
        new.set_project(self.project)
        self.connections.append(new)
        return new

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)
            self.project.remove_from_id_list(connection)

    def clear(self):
        for c in self.connections:
            self.connections.remove(c)
        for n in self.nodes:
            self.nodes.remove(n)

    #region IProjectContainer
    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.project.dispatch_changed(item=self)

    def get_type(self):
        return NODE_SCRIPT

    def serialize(self):
        nodes = []
        connections = []

        for n in self.nodes:
            nodes.append(n.serialize())

        for c in self.connections:
            connections.append(c.serialize())

        data = dict(
            name = self.name,
            unique_id = self.unique_id,
            nodes=nodes,
            connections=connections,
            notes = self.notes
        )

        return data

    def deserialize(self, serialization, project):
        self.project = project
        nodes = serialization['nodes']
        connections = serialization['connections']

        # node_editor = self.project.main_window.node_editor_dock.node_editor
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        for n in nodes:
            node = NodeDescriptor().deserialize(n, self.project)
            node.set_project(self.project)
            self.add_node(node)


        for c in connections:
            conn = ConnectionDescriptor().deserialize(c, self.project)
            conn.set_project(self.project)
            self.add_connection(conn)

        return self

    def delete(self):
        self.project.remove_script(self)


class NodeDescriptor(IProjectContainer, IHasName, ISelectable):
    def __init__(self, operation = None, pos = (0, 0), unique_id = -1):
        IProjectContainer.__init__(self)
        self.unique_id = unique_id
        self.node_size = (200,200)
        self.node_script = None
        if isinstance(pos, tuple):
            self.node_pos = pos
        else:
            self.node_pos = (pos.x(), pos.y())
        self.operation = operation

        if operation is not None:
            self.name = operation.name

        self.node_widget = None

    def set_position(self, qpoint):
        self.node_pos = (qpoint.x(), qpoint.y())

    def set_size(self, qsize):
        self.node_size = (qsize.width(), qsize.height())

    def get_position(self):
        return (self.node_pos[0], self.node_pos[1])

    def get_size(self):
        return (self.node_size[0], self.node_size[1])

    #region IProjectContainer
    def get_type(self):
        return NODE

    def get_name(self):
        return self.operation.name

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes

    #endregion
    def serialize(self):
        default_values = []
        for s in self.operation.input_slots:
            value = s.default_value
            if value is None:
                value = -1
            if isinstance(value, np.ndarray):
                value = value.tolist()
            default_values.append(value)

        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            node_pos = self.node_pos,
            node_size = self.node_size,
            default_values = default_values,
            operation = self.operation.__class__.__name__,
            notes=self.notes
        )

        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.node_pos = serialization['node_pos']
        self.node_size = serialization['node_size']
        self.notes = serialization['notes']

        self.operation = eval(serialization['operation'])()
        default_values = serialization['default_values']

        for i, s in enumerate(self.operation.input_slots):
            if default_values[i] == -1:
                s.default_value = None
            else:
                s.default_value = default_values[i]

        return self

    def delete(self):
        self.node_script.remove_node(self, True)


class ConnectionDescriptor(IProjectContainer):
    def __init__(self, input_pin=None, output_pin=None, input_pin_id=None, output_pin_id=None):
        IProjectContainer.__init__(self)
        if input_pin is not None:
            self.input_node = input_pin.node.node_object.unique_id
        if output_pin is not None:
            self.output_node = output_pin.node.node_object.unique_id
        self.input_pin_id = input_pin_id
        self.output_pin_id = output_pin_id

    def get_type(self):
        return -1

    def serialize(self):
        data = dict(
            input_node = self.input_node,
            output_node=self.output_node,
            input_pin_id=self.input_pin_id,
            output_pin_id=self.output_pin_id
        )
        return data

    def deserialize(self, serialization, project):
        self.project = project
        self.input_node = serialization['input_node']
        self.output_node = serialization['output_node']
        self.input_pin_id = serialization['input_pin_id']
        self.output_pin_id = serialization['output_pin_id']

        return self

