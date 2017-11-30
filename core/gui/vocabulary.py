from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QTreeView, QMenu, QHBoxLayout
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5 import uic
from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import IProjectChangeNotify
import os
from core.data.enums import *

class VocabularyManager(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(VocabularyManager, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Vocabulary Manager")
        self.vocabulary_view = VocabularyView(self, self.main_window)
        self.setWidget(self.vocabulary_view)

        self.show()

    def on_changed(self, project, item):
        self.vocabulary_view.on_changed(project, item)

    def on_selected(self, sender, selected):
        self.vocabulary_view.on_selected( sender, selected)

    def on_loaded(self, project):
        self.vocabulary_view.on_loaded(project)


class VocabularyView(QWidget, IProjectChangeNotify):
    def __init__(self, parent, main_window):
        super(VocabularyView, self).__init__(parent)
        path = os.path.abspath("qt_ui/VocabularyManager.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.project = main_window.project


        self.treeView = VocabularyTreeView(self)
        self.inner.layout().addWidget(self.treeView)

        self.vocabulary_model = QStandardItemModel(self.treeView)

        self.btn_addItem.clicked.connect(self.add_word)
        self.lineEdit_Item.returnPressed.connect(self.add_word)
        self.show()

    def add_vocabulary(self, voc):
        self.vocabulary_model.appendRow(voc.get_vocabulary_item_model())
        self.treeView.setModel(self.vocabulary_model)
        # self.treeView = QTreeView()

    def add_word(self):
        name = self.lineEdit_Item.text()
        if name != "" and len(self.treeView.selectedIndexes()) > 0:
            selected = self.vocabulary_model.itemFromIndex(self.treeView.selectedIndexes()[0])
            selected_item = selected.voc_object

            if selected_item.get_type() == VOCABULARY_WORD:
                word = selected_item.vocabulary.create_word(name, selected_item.name)
                item = VocabularyItem(word.name, word)
            elif selected_item.get_type() == VOCABULARY:
                word = selected_item.create_word(name)
                item = VocabularyItem(word.name, word)

            else:
                print "FAILED TO CREAE WORD"
            # if isinstance(selected_item, Vocabulary):
            #     selected_item.add_word(VocabularyWord(name))
            # elif isinstance(selected_item, VocabularyWord):
            #     selected_item.add_children(VocabularyWord(name))

            self.add_to_tree(selected, item)
        self.lineEdit_Item.setText("")

    def recreate_tree(self):
        self.vocabulary_model.clear()
        for v in self.project.vocabularies:
            self.add_vocabulary(v)

    def add_to_tree(self, selected, item):
        selected.appendRow(item)

    def on_loaded(self, project):
        self.project = project
        self.recreate_tree()

    def on_changed(self, project, item):
        if item is None:
            self.recreate_tree()

    def on_selected(self, sender, selected):
        pass


class VocabularyTreeView(QTreeView):
    def __init__(self, parent):
        super(VocabularyTreeView, self).__init__(parent)
        self.is_editing = False


    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            self.open_context_menu(QMouseEvent)
        else:
            super(VocabularyTreeView, self).mousePressEvent(QMouseEvent)

    def open_context_menu(self, QMouseEvent):
        pos = self.mapToGlobal(QMouseEvent.pos())
        try:
            obj = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        except:
            obj = None
        cm = VocabularyContextMenu(self.parent().parent().main_window, pos, obj)

    def apply_name_changed(self):
        current_word = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        new_name = self.model().itemFromIndex(self.selectedIndexes()[0]).text()
        current_word.name = new_name
        print new_name

    def edit(self, *args, **kwargs):
        self.is_editing = True
        return super(VocabularyTreeView, self).edit(*args, **kwargs)

    def closeEditor(self, *args, **kwargs):
        super(VocabularyTreeView, self).closeEditor(*args, **kwargs)
        self.is_editing = False
        self.apply_name_changed()

    def editorDestroyed(self, *args, **kwargs):
        self.is_editing = False
        self.apply_name_changed()
        super(VocabularyTreeView, self).editorDestroyed(*args, **kwargs)


class VocabularyContextMenu(QMenu):
    def __init__(self, parent, pos, item):
        super(VocabularyContextMenu, self).__init__(parent)
        self.item = item
        self.main_window = parent

        if item is not None:
            self.a_remove = self.addAction("Remove Word")
            self.a_remove.triggered.connect(self.on_remove)
            self.a_add_word = self.addAction("Add Word")
        self.a_new_voc = self.addAction("New Vocabulary")

        self.a_new_voc.triggered.connect(self.on_new_voc)


        self.popup(pos)

    def on_new_voc(self):
        self.main_window.project.create_vocabulary("New Vocabulary")

    def on_remove(self):

        self.item.vocabulary.remove_word(self.item)


class VocabularyItem(QStandardItem):
    def __init__(self, text, object):
        super(VocabularyItem, self).__init__(text)
        self.voc_object = object


#endregion











""