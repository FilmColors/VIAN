from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt5 import uic
from core.gui.ewidgetbase import EDockWidget, EDialogWidget
from core.data.interfaces import IProjectChangeNotify, IClassifiable, ITimeRange
from core.data.enums import get_type_as_string
import os
from functools import partial
from core.data.enums import *
import numpy as np
from random import shuffle
#region --DEFINITIONS--
MATRIX_ORDER_PER_SEGMENT = 0
MATRIX_ORDER_PER_TYPE = 1
MATRIX_ORDER_RANDOM = 2
MATRIX_ORDERS = ["By Time", "By Type", "Random"]
#endregion


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

        self.treeView = VocabularyTreeView(self, self)
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
                print("FAILED TO CREAE WORD")
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
    def __init__(self, parent, vocabulary_manager: VocabularyManager):
        super(VocabularyTreeView, self).__init__(parent)
        self.is_editing = False
        self.vocabulary_manager = vocabulary_manager

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            self.open_context_menu(QMouseEvent)
        else:
            super(VocabularyTreeView, self).mousePressEvent(QMouseEvent)

    def currentChanged(self, QModelIndex, QModelIndex_1):
        if self.vocabulary_manager.main_window.project is None:
            return

        super(VocabularyTreeView, self).currentChanged(QModelIndex, QModelIndex_1)
        if self.vocabulary_manager.vocabulary_model is not None:
            current_item = self.vocabulary_manager.vocabulary_model.itemFromIndex(self.currentIndex())
            if current_item is not None:
                obj = current_item.voc_object
                if obj is not None:
                    self.vocabulary_manager.main_window.project.set_selected(sender=None, selected=[obj])

    def open_context_menu(self, QMouseEvent):
        pos = self.mapToGlobal(QMouseEvent.pos())
        try:
            obj = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        except:
            obj = None
        cm = VocabularyContextMenu(self.vocabulary_manager.main_window, pos, obj)

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


class VocabularyContextMenu(QMenu):
    def __init__(self, parent, pos, item):
        super(VocabularyContextMenu, self).__init__(parent)
        self.item = item
        self.main_window = parent

        if item is not None:
            self.a_remove = self.addAction("Remove Word")
            self.a_remove.triggered.connect(self.on_remove)
            self.a_add_word = self.addAction("Add Word")
            if self.item.get_type() == VOCABULARY and self.main_window.project is not None:
                self.a_copy = self.addAction("Copy Vocabulary")
                self.a_copy.triggered.connect(partial(self.main_window.project.copy_vocabulary, self.item))

        self.a_new_voc = self.addAction("New Vocabulary")
        self.a_new_voc.triggered.connect(self.on_new_voc)

        self.popup(pos)

    def on_new_voc(self):
        self.main_window.project.create_vocabulary("New Vocabulary")

    def on_remove(self):
        if self.item.get_type() == VOCABULARY:
            self.main_window.project.remove_vocabulary(self.item)
        else:
            self.item.vocabulary.remove_word(self.item)


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


class ClassificationWindow(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ClassificationWindow, self).__init__(main_window, limit_size=False)
        path = os.path.abspath("qt_ui/ClassificationWidget.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.n_per_row = 20
        self.setWindowTitle("Classification Window")

        self.order_method = MATRIX_ORDER_PER_SEGMENT

        self.btn_StartClassification.clicked.connect(self.on_start_classification)
        self.btn_StopClassification.clicked.connect(self.on_stop_classification)
        self.btn_Previous.clicked.connect(self.on_previous)
        self.btn_Next.clicked.connect(self.on_next)

        for itm in MATRIX_ORDERS:
            self.comboBox_Sorting.addItem(itm)

        self.current_idx = 0
        self.current_experiment = None
        self.current_container = None
        self.sorted_containers = []

        # Can be one of "categories", "class-obj", "class-cat"
        self.mode = "class-obj"

        # GUI
        self.tab_widget = QTabWidget(self.contentWidget)
        self.contentWidget.layout().addWidget(self.tab_widget)

        self.tab_categories = []
        self.tabs = [] # The Category Tabs
        self.checkbox_groups = []
        self.checkbox_names =[]
        self.all_checkboxes = []

        m_layout = self.inner.menuBar().addMenu("Layout")
        self.a_cat = m_layout.addAction("Category")
        self.a_cat.setCheckable(True)
        self.a_cat.setChecked(False)

        self.a_class = m_layout.addAction("Class-Obj / Category")
        self.a_class.setCheckable(True)
        self.a_class.setChecked(True)

        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

    def on_changed(self, project, item):
        self.comboBox_Experiment.clear()
        if len(project.experiments) > 0:
            self.setEnabled(True)
            for e in project.experiments:
                self.comboBox_Experiment.addItem(e.get_name())
        else:
            self.setEnabled(False)

        return

    def on_loaded(self, project):
        self.comboBox_Experiment.clear()
        if len(project.experiments) > 0:
            self.setEnabled(True)
            for e in project.experiments:
                self.comboBox_Experiment.addItem(e.get_name())
        else:
            self.setEnabled(False)

        self.stackedWidget.setCurrentIndex(0)

    def on_selected(self, sender, selected):
        # if sender is not self:
        #     if len(selected) > 0:
        #         self.current_container = selected[0]
        #     else:
        #         self.current_container = None
        #     self.update_widget()
        pass

    def on_closed(self):
        self.stackedWidget.setCurrentIndex(0)
        self.setEnabled(False)
        return

    def on_layout_changed(self):
        sender = self.sender()
        self.a_cat.triggered.disconnect()
        self.a_class.triggered.disconnect()
        if sender == self.a_class:
            self.a_cat.setChecked(False)
            self.a_class.setChecked(True)
            self.mode = "class-obj"
        else:
            self.a_cat.setChecked(True)
            self.a_class.setChecked(False)
            self.mode = "categories"
        self.update_widget()
        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

    def on_start_classification(self):
        self.stackedWidget.setCurrentIndex(1)
        self.current_idx = 0
        self.current_experiment = self.main_window.project.experiments[self.comboBox_Experiment.currentIndex()]
        self.sorted_containers = self.current_experiment.get_containers_to_classify()

        #TODO Sort Containers
        self.update_widget()

    def on_stop_classification(self):
        self.stackedWidget.setCurrentIndex(0)

    def on_next(self):
        if len(self.sorted_containers) > self.current_idx + 1:
            self.current_idx += 1
            self.update_widget()

    def on_previous(self):
        if 0 <= self.current_idx - 1:
            self.current_idx -= 1
            self.update_widget()

    def on_order_changed(self):
        self.order_method = self.cb_ordering.currentIndex()

    def frame_container(self, container):
        if container is None:
            return

        if container.get_type() == (SEGMENT or ANNOTATION):
            self.main_window.player.set_media_time(container.get_start())
            self.main_window.timeline.timeline.frame_time_range(container.get_start(), container.get_end())
        elif container.get_type() == SCREENSHOT:
            segm = self.main_window.project.get_main_segmentation().get_segment_of_time(container.get_start())
            self.main_window.player.set_media_time(container.get_start())
            self.main_window.timeline.timeline.frame_time_range(segm.get_start(), segm.get_end())
            self.main_window.screenshots_manager.frame_screenshot(container)

    def update_widget(self):
        if self.current_experiment is None:
            return
        if self.mode == "categories":
            self.update_layout_categories()
        elif self.mode == "class-obj":
            self.update_layout_class_obj()

    def update_layout_class_obj(self):
        self.tab_widget.clear()
        self.tabs = []

        self.tab_categories = []
        self.checkbox_groups = []
        self.checkbox_names = []

        tab_widgets_class_objs_index = []
        tab_widgets_class_objs = dict()

        # Create outer tabs for Classification Objects
        for c in self.current_experiment.get_classification_objects_plain():
            tab = QTabWidget(self.tab_widget)
            self.tab_widget.addTab(tab, c.get_name())
            tab_widgets_class_objs[str(c.unique_id)] = tab
            tab_widgets_class_objs_index.append(c.unique_id)
            self.tab_categories.append([])
            self.tabs.append([])

        # Select current Container
        if len(self.sorted_containers) > self.current_idx:
            self.current_container = self.sorted_containers[self.current_idx]
            self.main_window.project.set_selected(None, selected=[self.current_container])
            self.lbl_CurrentContainer.setText(self.current_container.get_name())
            self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
        else:
            self.current_container = None

        # Draw Fields
        if self.current_container is not None:
            keywords = self.current_experiment.get_unique_keywords(self.current_container.get_parent_container())
            keywords = sorted(keywords, key=lambda x: (x.class_obj.name, x.voc_obj.name, x.word_obj.name))

            for k in keywords:
                idx = tab_widgets_class_objs_index.index(k.class_obj.unique_id)
                if  k.voc_obj.category not in self.tab_categories[idx]:
                    tab = QScrollArea()
                    tab.setWidget(QWidget())
                    tab.widget().setLayout(QVBoxLayout())
                    tab.setWidgetResizable(True)

                    self.tabs[idx].append(tab)
                    self.tab_categories[idx].append(k.voc_obj.category)
                    tab_widgets_class_objs[str(k.class_obj.unique_id)].addTab(tab, k.voc_obj.category)
                else:
                    tab = self.tabs[idx][self.tab_categories[idx].index(k.voc_obj.category)]

                if k.voc_obj.name + ":" + k.class_obj.name not in self.checkbox_names:
                    self.checkbox_names.append(k.voc_obj.name + ":" + k.class_obj.name)
                    group = CheckBoxGroupWidget(tab, k.voc_obj.name)
                    tab.widget().layout().addWidget(group)
                    self.checkbox_groups.append(group)
                else:
                    group = self.checkbox_groups[self.checkbox_names.index(k.voc_obj.name + ":" + k.class_obj.name)]

                checkbox = WordCheckBox(group, k)
                checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                checkbox.stateChanged.connect(
                    partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                group.add_checkbox(checkbox)

        for g in self.tabs:
            for t in g:
                t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.frame_container(self.current_container)

    def update_layout_categories(self):
        self.tab_widget.clear()
        self.tabs = []
        self.tab_categories = []
        self.checkbox_groups = []
        self.checkbox_names = []

        if len(self.sorted_containers) > self.current_idx:
            self.current_container = self.sorted_containers[self.current_idx]
            self.main_window.project.set_selected(None, selected=[self.current_container])
            self.lbl_CurrentContainer.setText(self.current_container.get_name())
            self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
        else:
            self.current_container = None

        if self.current_container is not None:
            keywords = self.current_experiment.get_unique_keywords(self.current_container.get_parent_container())
            keywords = sorted(keywords, key=lambda x: (x.class_obj.name, x.voc_obj.name, x.word_obj.name))
            for k in keywords:
                if k.voc_obj.category not in self.tab_categories:
                    tab = QScrollArea()
                    tab.setWidget(QWidget())
                    tab.widget().setLayout(QVBoxLayout())
                    tab.setWidgetResizable(True)

                    self.tabs.append(tab)
                    self.tab_categories.append(k.voc_obj.category)
                    self.tab_widget.addTab(tab, k.voc_obj.category)
                else:
                    tab = self.tabs[self.tab_categories.index(k.voc_obj.category)]

                if k.voc_obj.name + ":" + k.class_obj.name not in self.checkbox_names:
                    self.checkbox_names.append(k.voc_obj.name + ":" + k.class_obj.name)
                    group = CheckBoxGroupWidget(tab, k.class_obj.name + ":" + k.voc_obj.name)
                    tab.widget().layout().addWidget(group)
                    self.checkbox_groups.append(group)
                else:
                    group = self.checkbox_groups[self.checkbox_names.index(k.voc_obj.name + ":" + k.class_obj.name)]

                checkbox = WordCheckBox(group, k)
                checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                checkbox.stateChanged.connect(
                    partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                group.add_checkbox(checkbox)

        for t in self.tabs:
            t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.frame_container(self.current_container)


class CheckBoxGroupWidget(QWidget):
    def __init__(self, parent, name ,n_columns = 3):
        super(CheckBoxGroupWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/ClassificationCategory.ui")
        uic.loadUi(path, self)
        self.cx = 0
        self.cy = 0
        self.items = []
        self.expanded = True
        self.n_columns = n_columns
        self.btn_Class.setText(name.ljust(50))
        self.btn_Class.clicked.connect(self.toggle_expand)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.toggle_expand()

    def add_checkbox(self, checkbox):
        self.items.append(checkbox)
        self.items = sorted(self.items, key = lambda x: x.word.get_name())
        size = len(self.items)
        n_rows = np.ceil(size/self.n_columns)

        r = 0
        c = 0
        for w in self.items:
            if c == 0:
                self.vl_01.addWidget(w)
            elif c == 1:
                self.vl_02.addWidget(w)
            else:
                self.vl_03.addWidget(w)
            r += 1
            if r == n_rows:
                r = 0
                c += 1

    def toggle_expand(self):
        if self.expanded:
            self.hide_all()
        else:
            self.show_all()
        self.expanded = not self.expanded

    def hide_all(self):
        self.widgetContent.hide()
        # for itm in self.items:
        #     itm.hide()

    def show_all(self):
        self.widgetContent.show()
        # for itm in self.items:
        #     itm.show()


class WordCheckBox(QCheckBox):
    def __init__(self, parent, word):
        super(WordCheckBox, self).__init__(parent)
        self.word = word
        self.setText(word.get_name())
#endregion
