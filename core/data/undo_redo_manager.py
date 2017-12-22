from PyQt5.QtCore import QObject, pyqtSignal

class UndoRedoManager(QObject):
    on_changed = pyqtSignal()

    def __init__(self):
        super(UndoRedoManager, self).__init__()
        self.undo_stack = []
        self.redo_stack = []
        self.is_undoing = False
        self.is_redoing = False

    def has_modifications(self):
        return not (len(self.undo_stack) == 0 and len(self.redo_stack) == 0)

    def to_undo(self, redo, undo):
        if self.is_undoing:
            self.is_undoing = False
        elif self.is_redoing:
            self.is_redoing = False
            self.undo_stack.append((redo, undo))
        else:
            self.clear_redo()
            self.undo_stack.append((redo, undo))
        self.on_changed.emit()

    def to_redo(self, redo, undo):
        self.redo_stack.append((redo, undo))
        self.on_changed.emit()

    def undo(self):
        self.is_undoing = True
        if len(self.undo_stack) == 0:
            return
        
        tpl = self.undo_stack.pop()
        func = tpl[1][0]
        attr = tpl[1][1]
        func(*attr)
        self.redo_stack.append(tpl)

        self.on_changed.emit()

    def redo(self):
        self.is_redoing = True
        if len(self.redo_stack) == 0:
            return
        tpl = self.redo_stack.pop()
        func = tpl[0][0]
        attr = tpl[0][1]
        func(*attr)

        self.on_changed.emit()

    def clear(self):
        self.undo_stack = []
        self.redo_stack = []

        self.on_changed.emit()

    def clear_redo(self):
        self.redo_stack = []


