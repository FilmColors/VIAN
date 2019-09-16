import os
import glob
import json
from random import randint
from functools import partial

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeyEvent, QColor
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
        self.a_save = self.addAction(create_icon("qt_ui/icons/icon_save.png"), "Save")
        self.a_load = self.addAction(create_icon("qt_ui/icons/icon_load.png"), "Load")
        self.a_toproject = self.addAction(create_icon("qt_ui/icons/icon_toproject.png"), "Compare from Library to Project")
        self.a_fromproject = self.addAction(create_icon("qt_ui/icons/icon_fromproject.png"), "Compare from Project to Library")
        self.a_switch_library = self.addAction(create_icon("qt_ui/icons/icon_switch_voc_project_library.png"),
                                            "Switch between Project and Library Vocabularies")


class VocabularySaveDialog(QDialog):
    def __init__(self, parent, vocabularies):
        super(VocabularySaveDialog, self).__init__(parent)
        self.setWindowTitle("Save Vocabularies")
        self.setLayout(QVBoxLayout())
        lbl = QLabel("Select all vocabularies you want to save. The ones changed are highlighted in green")
        lbl.setWordWrap(True)
        self.layout().addWidget(lbl)
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
            folder = QFileDialog.getExistingDirectory()
        else:
            folder = None
        for itm in self.itms:
            if itm['list_item'].checkState() == Qt.Checked:
                voc = itm['voc']['voc']
                if folder is None:
                    path = itm['voc']['path']
                else:
                    path = os.path.join(folder, voc.name + ".json")
                voc.export_vocabulary(path)

                log_info("Saving", itm['voc'])
            else:
                log_info("Not Saving", itm['voc'])


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
        self.toolbar.a_toproject.triggered.connect(self.vocabulary_view.compare_library_to_project)
        self.toolbar.a_switch_library.triggered.connect(self.on_switch_current_library)
        self.inner.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.a_toproject.triggered.connect(self.synchronize_from_library_to_project)
        self.toolbar.a_fromproject.triggered.connect(self.synchronize_from_project_to_library)

        self.show()

    @pyqtSlot()
    def on_switch_current_library(self):
        """
        Switching between the VocabularyManager showing the Projects vocabularies or the libraries vocabularies.
        :return:
        """
        if self.mode == "library":
            if self.main_window.project is None:
                msg = QMessageBox.warning(self, "No Project Loaded", "You first have to load a Project to do this.")
            else:
                self.vocabulary_view.current_displayed_collection = self.main_window.project
                self.mode = "project"
                self.setWindowTitle("Vocabulary Manager: Project")
                self.vocabulary_view.recreate_tree()
                self.vocabulary_view.labelLibrary.hide()
                self.vocabulary_view.labelProject.show()
        else:
            self.vocabulary_view.current_displayed_collection = self.vocabulary_view.vocabulary_collection
            self.mode = "library"
            self.setWindowTitle("Vocabulary Manager: Library")
            self.vocabulary_view.recreate_tree()
            self.vocabulary_view.labelLibrary.show()
            self.vocabulary_view.labelProject.hide()

    @pyqtSlot()
    def save_vocabularies(self):
        if len(self.vocabulary_view.treeView.selected_vocabularies) == 0:
            vocabularies = self.vocabulary_view.vocabulary_index
        else:
            vocabularies = dict()
            for v in self.vocabulary_view.treeView.selected_vocabularies:
                vocabularies[v.uuid] = self.vocabulary_view.vocabulary_index[v.uuid]

        dialog = VocabularySaveDialog(self, vocabularies)
        dialog.show()

    def import_vocabularies(self):
        files = QFileDialog.getOpenFileNames(filter="*.json")[0]
        for f in files:
            self.vocabulary_view.vocabulary_collection.import_vocabulary(f)

    def synchronize_from_library_to_project(self):
        if len(self.vocabulary_view.treeView.selected_vocabularies) == 0:
            return
        if self.main_window.project is None:
            return

        vocabularies_project = dict()
        for v in self.main_window.project.vocabularies:
            vocabularies_project[v.uuid] = v

        to_compare = dict()
        for v in self.vocabulary_view.treeView.selected_vocabularies:
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
            copy = self.vocabulary_view.vocabulary_collection.copy_vocabulary(v)
            self.main_window.project.add_vocabulary(copy)
        for v in to_update:
            vocabularies_project[v.uuid].update_vocabulary(v)

    def synchronize_from_project_to_library(self):
        if self.main_window.project is None:
            return

        if len(self.vocabulary_view.treeView.selected_vocabularies) == 0:
            return

        vocabularies_collection = dict()
        for v in self.vocabulary_view.vocabulary_collection.vocabularies:
            vocabularies_collection[v.uuid] = v

        to_compare = dict()
        for v in self.vocabulary_view.treeView.selected_vocabularies:
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
            copy = self.main_window.project.vocabulary_collection.copy_vocabulary(v)
            self.vocabulary_view.vocabulary_collection.add_vocabulary(copy)
        for v in to_update:
            vocabularies_project[v.uuid].update_vocabulary(v)

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
        self.current_item = None

        self.vocabulary_collection = VIANProject(name="VocabularyCollection")
        self.vocabulary_index = dict()
        self.fetch_vocabularies()

        self.current_displayed_collection = self.vocabulary_collection

        self.treeView = VocabularyTreeView(self, self)
        self.inner.layout().addWidget(self.treeView)

        self.image_drop = DropImageContainer(self)
        self.widgetImageContainer.setLayout(QVBoxLayout())
        self.widgetImageContainer.layout().addWidget(self.image_drop)
        self.vocabulary_model = QStandardItemModel(self.treeView)

        self.btn_addItem.clicked.connect(self.add_word)
        self.lineEdit_Item.returnPressed.connect(self.add_word)

        self.lineEditName.textChanged.connect(self.on_name_changed)
        self.textEditDescription.textChanged.connect(self.on_description_changed)

        self.recreate_tree()

        self.labelLibrary.show()
        self.labelProject.hide()

        self.show()

    def fetch_vocabularies(self):
        for p in glob.glob("data/vocabularies/*.json"):
            v = self.vocabulary_collection.import_vocabulary(p)
            self.vocabulary_index[v.uuid] = dict(voc=v, path=p, edited=False)
        for p in glob.glob(self.main_window.settings.DIR_VOCABULARIES + "/*.json"):
            v = self.vocabulary_collection.import_vocabulary(p)
            self.vocabulary_index[v.uuid] = dict(voc=v, path=p, edited=False)
        pass

    @pyqtSlot()
    def compare_library_to_project(self):
        if self.main_window.project is None:
            msg = QMessageBox.warning(self, "No Project Loaded", "You first have to open a Project to compare.")
            return
        vocabularies_in_project = dict()
        for v in self.main_window.project.vocabularies:
            vocabularies_in_project[v.uuid] = v

        to_add = []
        compared = []
        for v in self.vocabulary_collection.vocabularies:
            if v.uuid not in vocabularies_in_project:
                to_add.append(v)
            else:
                compared.append(compare_vocabularies(v, vocabularies_in_project[v.uuid]))

    def add_vocabulary(self, voc):
        self.vocabulary_model.appendRow(self.get_vocabulary_item_model(voc))
        self.treeView.setModel(self.vocabulary_model)
        self.vocabulary_index[voc.uuid] = dict(voc=voc, path="", edited=False)
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
        if isinstance(current, VocabularyWord):
            pass
        elif isinstance(current, Vocabulary):
            pass
        self.current_item = current

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
                log_error("Failed to create word")
            self.add_to_tree(selected, item)
        self.lineEdit_Item.setText("")

    def recreate_tree(self):
        self.vocabulary_model.clear()
        for v in self.current_displayed_collection.vocabularies:
            self.add_vocabulary(v)

    def add_to_tree(self, selected, item):
        selected.appendRow(item)

    def on_name_changed(self):
        name = self.lineEditName.text()
        if self.current_item is not None:
            self.current_item.name = name

    def on_description_changed(self):
        description = self.textEditDescription.toPlainText()
        if self.current_item is not None:
            self.current_item.comment = description

    def on_loaded(self, project):
        self.project = project
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
    def __init__(self, parent, vocabulary_manager: VocabularyView):
        super(VocabularyTreeView, self).__init__(parent)
        self.is_editing = False
        self.vocabulary_manager = vocabulary_manager
        self.selected_vocabularies = []

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            self.open_context_menu(QMouseEvent)
        else:
            super(VocabularyTreeView, self).mousePressEvent(QMouseEvent)

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
        if self.vocabulary_manager.vocabulary_model is not None:
            current_item = self.vocabulary_manager.vocabulary_model.itemFromIndex(self.currentIndex())
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
                                   obj, self.vocabulary_manager.current_displayed_collection, self.model())

    def apply_name_changed(self):
        current_word = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        new_name = self.model().itemFromIndex(self.selectedIndexes()[0]).text()
        current_word.name = new_name

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

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Shift:
            self.setSelectionMode(self.MultiSelection)
        else:
            QKeyEvent.ignore()

    def keyReleaseEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Shift:
            self.setSelectionMode(self.SingleSelection)
        else:
            QKeyEvent.ignore()


class VocabularyContextMenu(QMenu):
    def __init__(self, parent, pos, model_item, item, voc_collection, item_model):
        super(VocabularyContextMenu, self).__init__(parent)
        self.model_item = model_item
        self.item = item
        self.main_window = parent
        self.voc_collection = voc_collection
        self.item_model = item_model

        if item is not None:
            self.a_remove = self.addAction("Remove " + str(item.__class__.__name__))
            self.a_remove.triggered.connect(self.on_remove)
            self.a_add_word = self.addAction("Add Word")
            # if self.item.get_type() == VOCABULARY and self.voc_collection is not None:
            #     self.a_copy = self.addAction("Copy Vocabulary")
            #     self.a_copy.triggered.connect(partial(self.voc_collection.copy_vocabulary, self.item))

        self.a_new_voc = self.addAction("New Vocabulary")
        self.a_new_voc.triggered.connect(self.on_new_voc)

        self.popup(pos)

    def on_new_voc(self):
        self.voc_collection.create_vocabulary("New Vocabulary")

    def on_remove(self):
        if self.model_item.parent() is not None:
            self.item_model.removeRow(self.model_item.row(), self.model_item.parent().index())
        else:
            self.item_model.removeRow(self.model_item.row())
        self.item.save_delete()


class VocabularyItem(QStandardItem):
    def __init__(self, text, object):
        super(VocabularyItem, self).__init__(text)
        self.voc_object = object


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
        path = QFileDialog.getExistingDirectory(directory=self.project.export_dir)
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
