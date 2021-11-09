from functools import partial
from typing import Dict, List

from uuid import uuid4
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon


from vian.core.container.experiment import Vocabulary, VocabularyWord
from vian.core.gui.ewidgetbase import EDockWidget, EditableListWidget, EditableListWidgetItem
from vian.core.data.interfaces import IProjectChangeNotify
from vian.core.container.project import Segmentation, VIANProject

from vian.core.container.vocabulary_library import VocabularyLibrary, VocabularyCollection


class VocabularyManager(EDockWidget, IProjectChangeNotify):
    onUpdateProject = pyqtSignal(object)

    def __init__(self, main_window):
        super(VocabularyManager, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Vocabulary Library")
        self.main_window = main_window
        self.library = main_window.vocabulary_library
        self.tree_view = VocabularyTreeView(self, self.library)
        self.word_list = WordsList(self)

        self.tree_view.onVocabularySelected.connect(self.word_list.set_vocabulary)
        self.editor = WordEditor(self)
        self.widget = QSplitter(self)
        self.widget.addWidget(self.tree_view)
        self.widget.addWidget(self.word_list)
        self.widget.addWidget(self.editor)

        # self.action_update = self.inner.menuBar().addAction("Sync with Project")
        # self.action_update.triggered.connect(self.on_sync)
        self.editor.onWordChanged.connect(self.word_list.redraw)
        self.word_list.itemSelectionChanged.connect(self.set_word_selected)
        self.inner.setCentralWidget(self.widget)

        self.show()

    def set_word_selected(self):
        word = self.word_list.get_selected_word()
        self.editor.set_word(word)


class VocabularyTreeView(QWidget):
    onVocabularySelected = pyqtSignal(object)
    onCheckStateChanged = pyqtSignal(object)

    onFilter = pyqtSignal(str)

    MODE_EDITING = 0
    MODE_SELECTING = 1

    def __init__(self, parent, vocabulary_library: VocabularyLibrary, mode=MODE_EDITING):
        super(VocabularyTreeView, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.line_search = QLineEdit(self)
        self.line_search.setPlaceholderText("Search....")
        self.line_search.textChanged.connect(self.on_search)
        self.layout().addWidget(self.line_search)

        self.items = []

        self.vocabulary_library = vocabulary_library
        self.selected_vocabularies = []

        self.tree = CollectionTreeWidget(self)
        self.tree.itemChanged.connect(self.on_item_check_changed)
        self.tree.setSelectionMode(self.tree.ExtendedSelection)
        self.tree.onContextMenu.connect(self.context_menu)
        self.layout().addWidget(self.tree)

        if hasattr(parent, "main_window"):
            parent.main_window.onProjectOpened.connect(partial(self.recreate_tree))

        self.mode = mode
        self.recreate_tree()

        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemSelectionChanged.connect(self.on_selected)

    def on_search(self):
        def filter_name(item, s):
            if s == "":
                item.setHidden(False)
                for v in item.items.values():
                    v.setHidden(False)
                    for w in v.items.values():
                        w.setHidden(False)
            else:
                show_collection = False
                for v in item.items.values():
                    show_vocabulary = False
                    for w in v.items.values():
                        if s in w.word.name:
                            w.setHidden(False)
                            show_vocabulary = True
                        else:
                            w.setHidden(True)

                    name = v.vocabulary.name
                    name += " ".join([w.name for w in v.vocabulary.words_plain])
                    if s in name or show_vocabulary:
                        v.setHidden(False)
                        show_collection = True
                    else:
                        v.setHidden(True)
                if s in item.collection.name:
                    show_collection = True

                item.setHidden(not show_collection)

        for w in self.items:
            filter_name(w, self.line_search.text())

    def recreate_tree(self):
        self.tree.clear()
        self.items = []
        for coll in self.vocabulary_library.collections.values():
            widget = CollectionItem(self.tree, coll, self.mode)
            self.items.append(widget)
            self.tree.addTopLevelItem(widget)

    def on_selected(self):
        print(self.tree.selectedItems())

        if len(self.tree.selectedItems()) == 0:
            return
        if isinstance(self.tree.selectedItems()[0], VocabularyItem):
            self.onVocabularySelected.emit(self.tree.selectedItems()[0].vocabulary)

    def get_selected_collection(self):
        if len(self.tree.selectedItems()) == 0:
            return None
        if isinstance(self.tree.selectedItems()[0], CollectionItem):
            return self.tree.selectedItems()[0].collection

    def get_selected_vocabulary(self):
        if len(self.tree.selectedItems()) == 0:
            return None
        if isinstance(self.tree.selectedItems()[0], VocabularyItem):
            return self.tree.selectedItems()[0].collection, self.tree.selectedItems()[0].vocabulary

    def on_item_check_changed(self, itm):
        self.onCheckStateChanged.emit(self.get_check_state())

    def on_item_changed(self, itm):
        if isinstance(itm, CollectionItem) and itm.text(0) != itm.collection.name:
            itm.collection.set_name(itm.text(0))
        elif isinstance(itm, VocabularyItem) and itm.text(0) != itm.vocabulary.name:
            itm.vocabulary.set_name(itm.text(0))

    def new_collection(self, name="New Collection"):
        self.vocabulary_library.create_collection(name)
        self.recreate_tree()

    def new_vocabulary(self, col:VocabularyCollection):
        col.create_vocabulary("AA New Vocabulary")
        self.recreate_tree()

    def remove_vocabulary(self, col:VocabularyCollection, voc:Vocabulary):
        col.remove_vocabulary(voc)
        self.recreate_tree()

    def copy_collection(self, col):
        if col is not None:
            self.vocabulary_library.copy_collection(col)
        self.recreate_tree()

    def remove_collection(self, col):
        self.vocabulary_library.remove_collection(col)
        self.recreate_tree()

    @pyqtSlot(object, object)
    def context_menu(self, QMouseEvent, mappedPoint):
        if not self.mode == self.MODE_EDITING:
            return

        if QMouseEvent.buttons() == Qt.RightButton:

            menu = QMenu(self.tree)
            a_new = menu.addAction("New Collection")
            a_new.triggered.connect(partial(self.new_collection, "New Collection"))

            if self.get_selected_collection() is not None:
                a_new_vocabulary = menu.addAction("New Vocabulary")
                a_new_vocabulary.triggered.connect(partial(self.new_vocabulary,  self.get_selected_collection()))

                a_copy = menu.addAction("Copy Collection")
                a_copy.triggered.connect(partial(self.copy_collection, self.get_selected_collection()))

                a_delete = menu.addAction("Remove Collection")
                a_delete.triggered.connect(partial(self.remove_collection,  self.get_selected_collection()))
            elif self.get_selected_vocabulary() is not None:
                a_remove_vocabulary = menu.addAction("Remove Vocabulary")
                collection, vocabulary = self.get_selected_vocabulary()
                a_remove_vocabulary.triggered.connect(partial(self.remove_vocabulary, collection, vocabulary))
                menu_to = menu.addMenu("Copy to...")
                for c in self.vocabulary_library.collections.values():
                    menu_to.addAction(c.name)

            menu.popup(self.mapToGlobal(mappedPoint))

    def set_check_status(self, vocabularies:List[Vocabulary]):
        self.tree.itemChanged.disconnect()
        for itm in self.items:
            itm.set_check_status(vocabularies)
        self.tree.itemChanged.connect(self.on_item_check_changed)

    def get_check_state(self):
        result = []
        for itm in self.items:
            result = itm.get_check_state(result)
        return result


class CollectionTreeWidget(QTreeWidget):
    onContextMenu = pyqtSignal(object, object)

    def __init__(self, parent):
        super(CollectionTreeWidget, self).__init__(parent)

    def mousePressEvent(self, QMouseEvent):
        super(CollectionTreeWidget, self).mousePressEvent(QMouseEvent)
        if QMouseEvent.buttons() == Qt.RightButton:
            self.onContextMenu.emit(QMouseEvent, self.mapToParent(QMouseEvent.pos()))


class CollectionItem(QTreeWidgetItem):
    def __init__(self, parent, collection:VocabularyCollection, mode):
        super(CollectionItem, self).__init__(parent)

        self.collection = collection
        self.mode = mode

        self.setText(0, self.collection.name)
        self.setIcon(0, QIcon("qt_ui/icons/icon_vocabulary.png"))
        self.items = dict()

        if self.mode == VocabularyTreeView.MODE_EDITING:
            self.setFlags(Qt.ItemIsEditable| Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        else:
            self.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        self.recreate_vocabularies()

    def recreate_vocabularies(self):
        self.items = dict()
        for v in sorted(self.collection.vocabularies.values(), key=lambda x:x.name):
            widget = VocabularyItem(self, self.collection, v, self.mode)
            self.addChild(widget)
            self.items[v.unique_id] = widget

    def set_check_status(self, vocabularies:List[Vocabulary]):
        uuids = [v.unique_id for v in vocabularies]
        for k, itm in self.items.items():
            itm.setCheckState(0, Qt.Checked if k in uuids else Qt.Unchecked)

    def get_check_state(self, result):
        for k, itm in self.items.items():
            result.append(dict(
                vocabulary=itm.vocabulary,
                state = itm.checkState(0) == Qt.Checked
            ))
        return result


class VocabularyItem(QTreeWidgetItem):
    def __init__(self, parent, collection, vocabulary:Vocabulary, mode, show_words = False):
        super(VocabularyItem, self).__init__(parent)
        self.collection = collection
        self.vocabulary = vocabulary
        self.setText(0, vocabulary.name)
        self.items = dict()
        self.mode = mode

        if self.mode == VocabularyTreeView.MODE_EDITING:
            self.setFlags(Qt.ItemIsEditable| Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        else:
            self.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        if show_words:
            self.recreate_words()

    def recreate_words(self):
        self.items = dict()
        for v in sorted(self.vocabulary.words_plain, key=lambda x:x.name):
            widget = WordItem(self, v)
            self.addChild(widget)
            self.items[v.unique_id] = widget


class WordItem(QTreeWidgetItem):
    def __init__(self, parent, word:VocabularyWord):
        super(WordItem, self).__init__(parent)
        self.word = word
        self.setText(0, word.name)



class WordsList(QListWidget):
    def __init__(self, parent):
        super(WordsList, self).__init__(parent)
        self.vocabulary = None

    @pyqtSlot(object)
    def set_vocabulary(self, voc:Vocabulary):
        self.clear()
        self.vocabulary = voc
        for w in sorted(voc.words_plain, key=lambda x:x.name):
            self.addItem(w.name)

    def add_word(self, name="A New Word"):
        self.vocabulary.create_word(name, unique_id=str(uuid4()), rename_dups=True)
        self.redraw()

    def remove_word(self, word):
        if word is not None:
            self.vocabulary.remove_word(word)
        self.redraw()

    def redraw(self):
        self.clear()
        for w in sorted(self.vocabulary.words_plain, key=lambda x: x.name):
            self.addItem(w.name)

    def get_selected_word(self):
        if len(self.selectedItems()) > 0:
            return self.vocabulary.get_word_by_name(self.selectedItems()[0].text())
        else:
            return None

    def mousePressEvent(self, QMouseEvent):
        super(WordsList, self).mousePressEvent(QMouseEvent)
        if QMouseEvent.buttons() == Qt.RightButton:

            if self.vocabulary is None:
                return

            menu = QMenu(self)
            a_new = menu.addAction("New Word")
            a_new.triggered.connect(partial(self.add_word, "A New Word"))

            if self.get_selected_word() != None:
                a_delete = menu.addAction("Remove Word")
                a_delete.triggered.connect(partial(self.remove_word,  self.get_selected_word()))

            menu.popup(self.mapToGlobal(QMouseEvent.pos()))


class WordEditor(QWidget):
    onWordChanged = pyqtSignal(object)

    def __init__(self, parent):
        super(WordEditor, self).__init__(parent)
        self.word = None

        self.setLayout(QGridLayout())

        self.layout().addWidget(QLabel("Term"), 0, 0)
        # self.layout().addWidget(QLabel("Term DE"), 1, 0)
        self.layout().addWidget(QLabel( "Category"), 2, 0)
        self.layout().addWidget(QLabel( "Complexity Group"), 3, 0)
        self.layout().addWidget(QLabel( "Complexity Level"), 4, 0)
        self.layout().addItem(QSpacerItem(10, 10, QSizePolicy.Fixed, QSizePolicy.Expanding), 5, 0)

        self.lineEdit_TermEn = QLineEdit(self)
        # self.lineEdit_TermDE = QLineEdit(self)
        self.lineEdit_Category = QLineEdit(self)
        self.lineEdit_ComplexityGroup = QLineEdit(self)
        self.lineEdit_ComplexityLevel = QSpinBox(self)

        self.layout().addWidget(self.lineEdit_TermEn, 0, 1)
        # self.layout().addWidget(self.lineEdit_TermDE, 1, 1)
        self.layout().addWidget(self.lineEdit_Category, 2, 1)
        self.layout().addWidget(self.lineEdit_ComplexityGroup, 3, 1)
        self.layout().addWidget(self.lineEdit_ComplexityLevel, 4, 1)

        # Future
        # self.lineEdit_TermDE.setEnabled(False)

        self.lineEdit_TermEn.editingFinished.connect(self.apply_changes)
        self.lineEdit_Category.editingFinished.connect(self.apply_changes)
        self.lineEdit_ComplexityGroup.editingFinished.connect(self.apply_changes)
        self.lineEdit_ComplexityLevel.editingFinished.connect(self.apply_changes)

    def set_word(self, word:VocabularyWord):
        if word is not None:
            self.lineEdit_TermEn.setText(word.name)
            self.lineEdit_Category.setText(word.vocabulary.category)
            self.lineEdit_ComplexityGroup.setText(word.complexity_group)
            self.lineEdit_ComplexityLevel.setValue(word.complexity_lvl)

        self.word = word
        state = word is not None
        self.lineEdit_TermEn.setEnabled(state)
        self.lineEdit_Category.setEnabled(state)
        self.lineEdit_ComplexityGroup.setEnabled(state)
        self.lineEdit_ComplexityLevel.setEnabled(state)

    def apply_changes(self):
        if self.word is None:
            return

        self.word.name = self.lineEdit_TermEn.text()
        self.word.vocabulary.category = self.lineEdit_Category.text()
        self.word.complexity_group = self.lineEdit_ComplexityGroup.text()
        self.word.complexity_lvl = self.lineEdit_ComplexityLevel.value()

        self.onWordChanged.emit(self.word)






