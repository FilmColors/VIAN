from core.gui.ewidgetbase import EDockWidget
from PyQt5 import uic, QtWidgets
from core.data.interfaces import IProjectChangeNotify
import os

class HistoryView(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(HistoryView, self).__init__(main_window)
        self.setWindowTitle("History View")
        self.history_widget = HistoryWidget(self, self.project().undo_manager)
        self.setWidget(self.history_widget)
        self.show()

    def on_loaded(self, project):
        self.history_widget.undo_manager = project.undo_manager
        self.history_widget.undo_manager.on_changed.connect(self.history_widget.update_history)

    def on_changed(self, project, item):
        pass

    def on_selected(self,sender, selected):
        pass

class HistoryWidget(QtWidgets.QWidget):
    def __init__(self, parent, undo_manager):
        super(HistoryWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/HistoryView.ui")
        uic.loadUi(path, self)
        self.undo_manager = undo_manager
        self.update_history()

        self.btn_Clear.clicked.connect(self.on_clear)
        self.btn_goTo.clicked.connect(self.on_goTo)
        self.listWidget_Undo.itemClicked.connect(self.on_selection_undo)
        self.listWidget_Redo.itemClicked.connect(self.on_selection_redo)

        self.current_item = None

    def update_history(self):
        undo_list = []
        for u in self.undo_manager.undo_stack:
            undo_list.append(u[1][0].__name__)

        redo_list = []
        for u in self.undo_manager.redo_stack:
            redo_list.append(u[0][0].__name__)

        self.listWidget_Undo.clear()
        self.listWidget_Redo.clear()

        self.listWidget_Undo.addItems(undo_list)
        self.listWidget_Redo.addItems(redo_list)

    def on_selection_undo(self):
        self.listWidget_Redo.setCurrentItem(None)
        index = len(self.undo_manager.undo_stack) - self.listWidget_Undo.currentRow()
        self.current_item = ["UNDO", index]


    def on_selection_redo(self):
        self.listWidget_Undo.setCurrentItem(None)
        index = len(self.undo_manager.redo_stack)
        self.current_item = ["REDO", index]


    def on_clear(self):
        self.undo_manager.clear()
        self.update_history()

    def on_goTo(self):
        if self.current_item[0] == "UNDO":
            for i in range(self.current_item[1]):
                self.undo_manager.undo()
        else:
            for i in range(self.current_item[1]):
                self.undo_manager.redo()


