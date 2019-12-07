import os
import glob
import json
from random import randint
from functools import partial

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeyEvent, QColor, QDropEvent, QDragEnterEvent
from PyQt5 import uic
from core.data.computation import create_icon
from core.data.log import log_error, log_info, log_warning, log_debug
from core.container.project import VIANProject
from core.gui.drop_image_container import DropImageContainer
from core.container.experiment import Vocabulary, VocabularyWord, compare_vocabularies
from core.gui.ewidgetbase import EDockWidget, EDialogWidget
from core.data.interfaces import IProjectChangeNotify
from core.data.enums import *

#region --DEFINITIONS--
#endregion


class VocabularyManagerToolbar(QToolBar):
    def __init__(self, parent):
        super(VocabularyManagerToolbar, self).__init__(parent)
        self.a_new_vocabulary = self.addAction((create_icon("qt_ui/icons/icon_create_vocabulary.png")),
                                               "Create new Vocabulary")
        self.a_save = self.addAction(create_icon("qt_ui/icons/icon_save.png"), "Save")
        self.a_load = self.addAction(create_icon("qt_ui/icons/icon_load.png"), "Load")

        self.a_toproject = self.addAction(create_icon("qt_ui/icons/icon_toproject.png"), "Compare from Library to Project")
        self.a_fromproject = self.addAction(create_icon("qt_ui/icons/icon_fromproject.png"), "Compare from Project to Library")
        # self.a_switch_library = self.addAction(create_icon("qt_ui/icons/icon_switch_voc_project_library.png"),
        #                                     "Switch between Project and Library Vocabularies")


class VocabularySaveDialog(QDialog):
    def __init__(self, parent, vocabularies, default_dir):
        super(VocabularySaveDialog, self).__init__(parent)
        self.setWindowTitle("Save Vocabularies")
        self.setLayout(QVBoxLayout())
        self.default_dir = default_dir
        # lbl = QLabel("Select all vocabularies you want to save. The ones changed are highlighted in green")
        # lbl.setWordWrap(True)
        # self.layout().addWidget(lbl)
        self.modified_list = QListWidget()
        self.layout().addWidget(self.modified_list)
        self.vocabularies = vocabularies
        self.itms = []
        for v in self.vocabularies.values():
            voc = v['voc']
            itm = QListWidgetItem(voc.name)
            if not v['edited']:
                itm.setCheckState(Qt.Checked)
                itm.setForeground(QColor(0,255,0))
            else:
                itm.setCheckState(Qt.Unchecked)
                itm.setForeground(QColor(255, 255, 255))
            self.modified_list.addItem(itm)
            self.itms.append(dict(voc=v, list_item=itm))
        hlt = QHBoxLayout(self)
        self.layout().addItem(hlt)
        self.btn_save = QPushButton("Save", self)
        self.btn_save_as = QPushButton("Save As...", self)
        hlt.addWidget(self.btn_save)
        hlt.addWidget(self.btn_save_as)
        self.btn_save.clicked.connect(partial(self.on_save, False))
        self.btn_save_as.clicked.connect(partial(self.on_save, True))

    def on_save(self, save_as = False):
        if save_as:
            folder = QFileDialog.getExistingDirectory(caption="Select Directory to Vocabularies into")
        else:
            folder = None
        for itm in self.itms:
            if itm['list_item'].checkState() == Qt.Checked:
                voc = itm['voc']['voc']
                if folder is None:
                    if itm['voc']['path'] == "":
                        path = os.path.join(self.default_dir, voc.name + ".json")
                    else:
                        path = itm['voc']['path']
                else:
                    path = os.path.join(folder, voc.name + ".json")
                voc.export_vocabulary(path)

                log_info("Saving", itm['voc'])
            else:
                log_info("Not Saving", itm['voc'])
        self.close()


class VocabularyCompareDialog(QDialog):
    def __init__(self, parent, comparisons, to_add, vocabularies_project, callback):
        super(VocabularyCompareDialog, self).__init__(parent)
        self.setWindowTitle("Compared Vocabularies")
        self.setLayout(QVBoxLayout())
        self.vocabulary_manager = parent
        self.to_add = to_add
        self.vocabularies_project = vocabularies_project

        self.modified_list = QListWidget()
        self.layout().addWidget(self.modified_list)
        self.comparisons = comparisons
        self.itms = []
        self.callback = callback
        for v in comparisons:
            voc = v['voc']
            changes = v['changes']
            itm = QListWidgetItem(str(voc.name) + "\t" + str(changes))
            itm.setCheckState(Qt.Checked)
            self.modified_list.addItem(itm)
            self.itms.append(dict(voc=voc, list_item=itm))

        hlt = QHBoxLayout(self)
        self.layout().addItem(hlt)
        self.btn_apply = QPushButton("Apply", self)
        hlt.addWidget(self.btn_apply)
        self.btn_apply.clicked.connect(self.on_apply)

    def on_apply(self):
        to_update = []
        for v in self.itms:
            if v['list_item'].checkState() == Qt.Checked:
                to_update.append(v['voc'])

        self.callback(self.to_add,to_update,self.vocabularies_project)
        self.close()
        pass


class VocabularyManager(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(VocabularyManager, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Vocabulary Manager: Library")
        self.vocabulary_view = VocabularyView(self, self.main_window)
        self.setWidget(self.vocabulary_view)

        self.mode = "library"
        self.toolbar = VocabularyManagerToolbar(self.inner)
        self.toolbar.a_save.triggered.connect(self.save_vocabularies)
        self.toolbar.a_load.triggered.connect(self.import_vocabularies)
        # self.toolbar.a_toproject.triggered.connect(self.vocabulary_view.compare_library_to_project)
        self.toolbar.a_new_vocabulary.triggered.connect(self.on_new_vocabulary)
        # self.toolbar.a_switch_library.triggered.connect(self.on_switch_current_library)
        self.inner.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.a_toproject.triggered.connect(self.synchronize_from_library_to_project)
        self.toolbar.a_fromproject.triggered.connect(self.synchronize_from_project_to_library)

        self.show()

    def on_new_vocabulary(self):
        voc = self.vocabulary_view.vocabulary_collection.create_vocabulary("New Vocabulary")
        self.vocabulary_view.treeViewLibrary.scroll_to_item(voc)

    @pyqtSlot()
    def save_vocabularies(self):
        if len(self.vocabulary_view.treeViewLibrary.selected_vocabularies) == 0:
            vocabularies = self.vocabulary_view.vocabulary_index
        else:
            vocabularies = dict()
            for v in self.vocabulary_view.treeViewLibrary.selected_vocabularies:
                vocabularies[v.uuid] = self.vocabulary_view.vocabulary_index[v.uuid]

        dialog = VocabularySaveDialog(self, vocabularies, self.main_window.settings.DIR_VOCABULARIES)
        dialog.show()

    def import_vocabularies(self):
        files = QFileDialog.getOpenFileNames(filter="*.json")[0]
        for f in files:
            self.vocabulary_view.vocabulary_collection.import_vocabulary(f)

    def synchronize_from_library_to_project(self):
        if len(self.vocabulary_view.treeViewLibrary.selected_vocabularies) == 0:
            return
        if self.main_window.project is None:
            msg = QMessageBox.warning(self, "No Project Loaded",
                                      "You first need to load a project before attaching vocabularies.")
            return

        vocabularies_project = dict()
        for v in self.main_window.project.vocabularies:
            vocabularies_project[v.uuid] = v

        to_compare = dict()
        for v in self.vocabulary_view.treeViewLibrary.selected_vocabularies:
            to_compare[v.uuid] = v
        to_apply = []
        to_check = []
        for k, v in to_compare.items():
            if k in vocabularies_project:
                changes = compare_vocabularies(v, vocabularies_project[k])
                if len(changes) > 0:
                    to_check.append(dict(voc=v, changes=changes))
            else:
                to_apply.append(v)
        if len(to_check) > 0:
            dialog = VocabularyCompareDialog(self, to_check, to_apply, vocabularies_project, self.finish_synchronize_from_library_to_project)
            dialog.show()
        else:
            self.finish_synchronize_from_library_to_project(to_apply, [], vocabularies_project)

    def finish_synchronize_from_library_to_project(self, to_add, to_update, vocabularies_project):
        for v in to_add:
            copy = self.vocabulary_view.vocabulary_collection.copy_vocabulary(v, add_to_global=False)
            self.main_window.project.add_vocabulary(copy)
        for v in to_update:
            vocabularies_project[v.uuid].update_vocabulary(v)
        self.vocabulary_view.recreate_tree()

    def synchronize_from_project_to_library(self):
        if self.main_window.project is None:
            return

        if len(self.vocabulary_view.treeViewProject.selected_vocabularies) == 0:
            return

        vocabularies_collection = dict()
        for v in self.vocabulary_view.vocabulary_collection.vocabularies:
            vocabularies_collection[v.uuid] = v

        to_compare = dict()
        for v in self.vocabulary_view.treeViewProject.selected_vocabularies:
            to_compare[v.uuid] = v
        to_apply = []
        to_check = []
        for k, v in to_compare.items():
            if k in vocabularies_collection:
                changes = compare_vocabularies(v, vocabularies_collection[k])
                if len(changes) > 0:
                    to_check.append(dict(voc=v, changes=changes))
            else:
                to_apply.append(v)
        if len(to_check) > 0:
            dialog = VocabularyCompareDialog(self, to_check, to_apply, vocabularies_collection, self.finish_synchronize_from_project_to_library)
            dialog.show()
        else:
            self.finish_synchronize_from_library_to_project(to_apply, [], vocabularies_collection)

    def finish_synchronize_from_project_to_library(self, to_add, to_update, vocabularies_project):
        for v in to_add:
            copy = self.main_window.project.vocabulary_collection.copy_vocabulary(v, add_to_global=False)
            self.vocabulary_view.vocabulary_collection.add_vocabulary(copy)
        for v in to_update:
            vocabularies_project[v.uuid].update_vocabulary(v)
        self.vocabulary_view.recreate_tree()

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
        self.project = None
        self.current_item = None

        self.vocabulary_collection = VIANProject(name="VocabularyCollection")

        self.vocabulary_index = dict()  # A dict of vocabularies found on the file system
        self.fetch_vocabularies()

        self.complexities = {
            "0 (Undefined)": 1,
            "1 (Beginner)": 1,
            "2" : 2,
            "3 (Intermediate)" : 3,
            "4" : 4,
            "5 (Expert)" : 5
        }
        for k, v in self.complexities.items():
            self.comboBoxComplexity.addItem(k)

        self.treeViewLibrary = VocabularyTreeView(self, self, self.vocabulary_collection, allow_create=True)
        self.vocabulary_model_library = VocabularyTreeItemModel(self.treeViewLibrary, self.parent().synchronize_from_project_to_library, "library")
        self.innerLibrary.layout().addWidget(self.treeViewLibrary)

        self.treeViewProject = VocabularyTreeView(self, self, self.project, allow_create=False)
        self.vocabulary_model_project = VocabularyTreeItemModel(self.treeViewProject, self.parent().synchronize_from_library_to_project, "project")
        self.innerProject.layout().addWidget(self.treeViewProject)

        self.image_drop = DropImageContainer(self)
        self.widgetImageContainer.setLayout(QVBoxLayout())
        self.widgetImageContainer.layout().addWidget(self.image_drop)

        self.btn_addItem.clicked.connect(self.add_word)
        self.lineEdit_Item.returnPressed.connect(self.add_word)

        self.lineEditName.textChanged.connect(self.on_name_changed)
        self.textEditDescription.textChanged.connect(self.on_description_changed)
        self.lineEditComplexityGroup.textChanged.connect(self.on_complexity_group_changed)
        self.comboBoxComplexity.currentTextChanged.connect(self.on_complexity_level_changed)

        self.vocabulary_collection.onVocabularyAdded.connect(partial(self.recreate_tree))
        self.vocabulary_collection.onVocabularyRemoved.connect(partial(self.recreate_tree))
        self.recreate_tree()

        self.show()

    def fetch_vocabularies(self):
        for p in glob.glob("data/vocabularies/*.json"):
            v = self.vocabulary_collection.import_vocabulary(p)
            v._path = p
            v.is_builtin = True
            self.vocabulary_index[v.uuid] = dict(voc=v, path=p, edited=False)

        for p in glob.glob(self.main_window.settings.DIR_VOCABULARIES + "/*.json"):
            v = self.vocabulary_collection.import_vocabulary(p)
            self.vocabulary_index[v.uuid] = dict(voc=v, path=p, edited=False)
            v._path = p

    def add_vocabulary(self, model, view, voc):
        model.appendRow(self.get_vocabulary_item_model(voc))
        view.setModel(model)
        if voc.uuid in self.vocabulary_index:
            edited =  self.vocabulary_index[voc.uuid]['edited']
        else:
            edited = False
        self.vocabulary_index[voc.uuid] = dict(voc=voc, path=voc._path, edited=edited)

        # self.treeView = QTreeView()

    def get_vocabulary_item_model(self, voc):
        root = VocabularyItem(voc.name, voc)
        for w in voc.words:
            self.get_children(root, w)
        return root

    def get_children(self, parent_item, word):
        item = VocabularyItem(word.name, word)
        parent_item.appendRow(item)
        if len(word.children) > 0:
            for c in word.children:
                self.get_children(item, c)

    def set_current(self, current):
        """
        Sets the current item to be edited in the right widget.

        :param current: The item to be edited
        """
        self.current_item = None
        if current is None:
            return
        self.lineEditName.setText(current.name)
        self.textEditDescription.setPlainText(current.comment)

        voc = None
        if isinstance(current, VocabularyWord):
            voc = current.vocabulary
            self.lineEditCategory.setEnabled(False)
            self.comboBoxComplexity.setEnabled(True)
            print("Complexity Group", current.complexity_group)
            self.lineEditComplexityGroup.setText(current.complexity_group)
            for k, v in self.complexities.items():
                if v == current.complexity_lvl:
                    self.comboBoxComplexity.setCurrentText(k)
                    break

        elif isinstance(current, Vocabulary):
            voc = current
            self.lineEditCategory.setText(current.category)
            self.lineEditCategory.setEnabled(True)
            complexity_groups = []
            for w in current.words: #type: VocabularyWord
                if w.complexity_group not in complexity_groups:
                    complexity_groups.append(w.complexity_group)
            if len(complexity_groups) > 1:
                self.lineEditComplexityGroup.setText("Multiple")
            elif len(complexity_groups) == 1:
                self.lineEditComplexityGroup.setText(complexity_groups[0])
        self.current_item = current

        if voc is not None and voc.is_builtin:
            self.lineEditName.setEnabled(False)
            self.textEditDescription.setEnabled(False)
            self.lineEditCategory.setEnabled(False)
            self.comboBoxComplexity.setEnabled(False)
            self.lineEditComplexityGroup.setEnabled(False)
        else:
            self.lineEditName.setEnabled(True)
            self.textEditDescription.setEnabled(True)
            self.lineEditCategory.setEnabled(True)
            self.comboBoxComplexity.setEnabled(True)
            self.lineEditComplexityGroup.setEnabled(True)

    def add_word(self):
        name = self.lineEdit_Item.text()
        if name != "" and len(self.treeViewLibrary.selectedIndexes()) > 0:
            selected = self.vocabulary_model_library.itemFromIndex(self.treeViewLibrary.selectedIndexes()[0])
            selected_item = selected.voc_object

            item = None
            if selected_item.get_type() == VOCABULARY_WORD:
                word = selected_item.vocabulary.create_word(name, selected_item.name)

                if word is not None:
                    item = VocabularyItem(word.name, word)
                else:
                    msg = QMessageBox.warning(self, "Duplicate Word",
                                              "Adding two words with the same name is not allowed.")
            elif selected_item.get_type() == VOCABULARY:
                word = selected_item.create_word(name)

                if word is not None:
                    item = VocabularyItem(word.name, word)
                else:
                    msg = QMessageBox.warning(self, "Duplicate Word",
                                              "Adding two words with the same name is not allowed.")
            else:
                log_error("Failed to create word")
                item = None

            if item is not None:
                index = self.add_to_tree(selected, item)
                self.treeViewLibrary.scrollTo(index)
        self.lineEdit_Item.setText("")

    def recreate_tree(self):
        # AutoCompleter for Complexity Groups

        complexity_groups = []
        for v in self.vocabulary_collection.vocabularies:
            complexity_groups.extend(v.get_complexity_groups())
        complexity_groups = list(set(complexity_groups))
        completer = QCompleter(complexity_groups)
        self.lineEditComplexityGroup.setCompleter(completer)

        self.vocabulary_model_library.clear()
        for v in sorted(self.vocabulary_collection.vocabularies, key=lambda x:x.name):
            self.add_vocabulary(self.vocabulary_model_library, self.treeViewLibrary, v)

        self.vocabulary_model_project.clear()
        if self.project is not None:
            for v in sorted(self.project.vocabularies, key=lambda x:x.name):
                self.add_vocabulary(self.vocabulary_model_project, self.treeViewProject, v)
        self.treeViewProject.setModel(self.vocabulary_model_project)

    def add_to_tree(self, selected, item):
        selected.appendRow(item)
        return item.index()

    def on_name_changed(self):
        name = self.lineEditName.text()
        if self.current_item is not None:
            self.current_item.name = name

    def on_complexity_group_changed(self):
        if self.current_item is None:
            return
        if isinstance(self.current_item, Vocabulary):
            for w in self.current_item.words:
                w.complexity_group = self.lineEditComplexityGroup.text()
        elif isinstance(self.current_item, VocabularyWord):
            self.current_item.complexity_group = self.lineEditComplexityGroup.text()

    def on_complexity_level_changed(self):
        if self.current_item is None:
            return
        if isinstance(self.current_item, Vocabulary):
            for w in self.current_item.words:
                w.complexity_lvl = self.complexities[self.comboBoxComplexity.currentText()]
        elif isinstance(self.current_item, VocabularyWord):
            self.current_item.complexity_lvl = self.complexities[self.comboBoxComplexity.currentText()]

    def on_description_changed(self):
        description = self.textEditDescription.toPlainText()
        if self.current_item is not None:
            self.current_item.comment = description

    def on_loaded(self, project):
        self.project = project
        self.treeViewProject.collection = project
        self.recreate_tree()

    def on_closed(self):
        self.current_item = None
        self.lineEditName.setText("")
        self.textEditDescription.setPlainText("")

    def on_changed(self, project, item):
        if item is None:
            self.recreate_tree()

    def on_selected(self, sender, selected):
        pass


class VocabularyTreeView(QTreeView):
    def __init__(self, parent, vocabulary_manager: VocabularyView, collection:VIANProject, allow_create=True):
        super(VocabularyTreeView, self).__init__(parent)
        self.is_editing = False
        self.vocabulary_manager = vocabulary_manager
        self.selected_vocabularies = []
        self.setSelectionMode(self.ExtendedSelection)
        self.collection = collection
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropOverwriteMode(True)
        self.setDropIndicatorShown(True)

        self.allow_create = allow_create
        self.header().close()

    def scroll_to_item(self, itm):
        for r in range(self.model().rowCount()):
            index = self.model().index(r, 0)
            if self.model().data(index) == itm.get_name():
                self.scrollTo(index)
                return
            for r in range(self.model().rowCount(index)):
                if self.model().data(index) == itm.get_name():
                    self.scrollTo(index)
                    return

    def mousePressEvent(self, QMouseEvent):
        super(VocabularyTreeView, self).mousePressEvent(QMouseEvent)
        if QMouseEvent.buttons() == Qt.RightButton:
            if self.collection is not None:
                self.open_context_menu(QMouseEvent)

    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        try:
            self.selected_vocabularies = []
            for t in self.selectedIndexes():
                obj = t.model().itemFromIndex(t).voc_object
                if isinstance(obj, Vocabulary):
                    self.selected_vocabularies.append(t.model().itemFromIndex(t).voc_object)
        except:
            pass

    def currentChanged(self, QModelIndex, QModelIndex_1):
        # if self.vocabulary_manager.main_window.project is None:
        #     return

        super(VocabularyTreeView, self).currentChanged(QModelIndex, QModelIndex_1)
        if self.vocabulary_manager.vocabulary_model_library is not None:
            current_item = self.vocabulary_manager.vocabulary_model_library.itemFromIndex(self.currentIndex())
            if current_item is not None:
                obj = current_item.voc_object
                if obj is not None:
                    # self.vocabulary_manager.main_window.project.set_selected(sender=None, selected=[obj])
                    self.vocabulary_manager.set_current(obj)

    def open_context_menu(self, QMouseEvent):
        pos = self.mapToGlobal(QMouseEvent.pos())
        try:
            model_obj = self.model().itemFromIndex(self.selectedIndexes()[0])
            obj = model_obj.voc_object
        except:
            obj = None
            model_obj = None

        cm = VocabularyContextMenu(self.vocabulary_manager.main_window, pos, model_obj,
                                   obj, self.collection, self.model(), self.vocabulary_manager, self, self.allow_create)

    def apply_name_changed(self):
        current_word = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        if isinstance(current_word, Vocabulary):
            if current_word.is_builtin:
                QMessageBox.warning(self, "Vocabulary is built-in", "You can not edit a built in vocabulary.")
                name = "(FilmColors) " + self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object.name
                self.model().itemFromIndex(self.selectedIndexes()[0]).setText(name)
                return
        new_name = self.model().itemFromIndex(self.selectedIndexes()[0]).text()
        current_word.set_name(new_name)
        self.model().itemFromIndex(self.selectedIndexes()[0]).setText(current_word.get_name())

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

    #
    # def keyReleaseEvent(self, QKeyEvent):
    #     if QKeyEvent.key() == Qt.Key_Shift:
    #         self.setSelectionMode(self.SingleSelection)
    #     else:
    #         QKeyEvent.ignore()


class VocabularyContextMenu(QMenu):
    def __init__(self, parent, pos, model_item, item, voc_collection, item_model, manager, view, allow_create=True):
        super(VocabularyContextMenu, self).__init__(parent)
        self.model_item = model_item
        self.item = item
        self.main_window = parent
        self.voc_collection = voc_collection
        self.item_model = item_model
        self.manager = manager
        self.view = view
        if item is not None:
            self.a_remove = self.addAction("Remove " + str(item.__class__.__name__))
            self.a_remove.triggered.connect(self.on_remove)
            if isinstance(item, Vocabulary):
                self.a_copy = self.addAction("Copy Vocabulary")
                self.a_copy.triggered.connect(self.on_copy)

        if allow_create:
            self.a_new_voc = self.addAction("New Vocabulary")
            self.a_new_voc.triggered.connect(self.on_new_voc)

        self.popup(pos)

    def on_create_word(self):
        if isinstance(self.item, Vocabulary):
            self.item.create_word("New Word")
        elif isinstance(self.item, VocabularyWord):
            self.item.vocabulary.create_word("New Word")
        self.manager.recreate_tree()

    def on_copy(self):
        v = self.item.project.copy_vocabulary(self.item, replace_uuid=True)
        self.manager.recreate_tree()

    def on_new_voc(self):
        voc = self.voc_collection.create_vocabulary("New Vocabulary")
        self.view.scroll_to_item(voc)

    def on_remove(self):
        if self.model_item.parent() is not None:
            self.item_model.removeRow(self.model_item.row(), self.model_item.parent().index())
        else:
            self.item_model.removeRow(self.model_item.row())
        self.item.save_delete()


class VocabularyTreeItemModel(QStandardItemModel):
    def __init__(self, parent, migration_function, type):
        super(VocabularyTreeItemModel, self).__init__(parent=parent)
        self.migration_function = migration_function
        self.type = type


    def mimeTypes(self):
        return ["vocabularies"]

    def mimeData(self, indexes) -> QtCore.QMimeData:
        # vocs = [str(self.itemFromIndex(idx).voc_object.unique_id) for idx in indexes]
        # vocs = ";".join(vocs)
        d  = QtCore.QMimeData()
        d.setData("vocabularies", bytes(self.type, encoding="UTF-8"))
        return d

    def dropMimeData(self, data: QtCore.QMimeData, action: QtCore.Qt.DropAction, row: int, column: int, parent: QtCore.QModelIndex) -> bool:
        q = str(data.data("vocabularies"), encoding='utf-8')
        if q == self.type:
            return False

        self.migration_function()
        return False


class VocabularyItem(QStandardItem):
    def __init__(self, text, object):
        if isinstance(object, Vocabulary):
            if object.is_builtin:
                text = "(FilmColors) " + text
        super(VocabularyItem, self).__init__(text)
        self.voc_object = object
        self.setDragEnabled(True)


class VocabularyExportDialog(EDialogWidget):
    def __init__(self, main_window):
        super(VocabularyExportDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogExportVocabulary.ui")
        uic.loadUi(path, self)
        self.project = main_window.project
        self.lineEdit_Path.setText(self.project.export_dir)

        self.entries = []
        for voc in self.project.vocabularies:
            item = QWidget(self.vocList)
            item.setLayout(QHBoxLayout(item))
            item.layout().addWidget(QLabel(voc.name, item))
            cb = QCheckBox(item)
            item.layout().addWidget(cb)
            self.entries.append([cb, voc])
            self.vocList.layout().addWidget(item)

        self.btn_Export.clicked.connect(self.export)
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_Browse.clicked.connect(self.on_browse)

    def on_browse(self):
        path = QFileDialog.getExistingDirectory(caption="Select Directory to export Vocabulary into", directory=self.project.export_dir)
        self.lineEdit_Path.setText(path)

    def export(self):
        if not os.path.isdir(self.lineEdit_Path.text()):
            QMessageBox.warning(self, "No valid Directory", "Please select a valid Directory first")
        else:
            dir = self.lineEdit_Path.text()
            for itm in self.entries:
                if itm[0].isChecked():
                    itm[1].export_vocabulary(dir + "/" +itm[1].name + ".json")
            self.close()


#endregion
