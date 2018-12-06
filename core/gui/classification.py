import os
from functools import partial

import numpy as np
from PyQt5 import uic
from PyQt5.QtWidgets import QTabWidget, QScrollArea, QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QCheckBox

from core.data.enums import SEGMENT, ANNOTATION, SCREENSHOT
from core.data.interfaces import IProjectChangeNotify
from core.gui.ewidgetbase import EDockWidget

MATRIX_ORDER_PER_SEGMENT = 0
MATRIX_ORDER_PER_TYPE = 1
MATRIX_ORDER_RANDOM = 2
MATRIX_ORDERS = ["By Time", "By Type", "Random"]

class ClassificationWindow(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window, behaviour = "classification"):
        super(ClassificationWindow, self).__init__(main_window, limit_size=False)
        path = os.path.abspath("qt_ui/ClassificationWidget.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.n_per_row = 20
        self.behaviour = behaviour
        if self.behaviour == "classification":
            self.setWindowTitle("Classification Window")
        else:
            self.setWindowTitle("Query Window")

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

        self.current_query_keywords = []

        # GUI
        self.tab_widget = QTabWidget(self.contentWidget)
        self.contentWidget.layout().addWidget(self.tab_widget)

        self.tab_categories = []
        self.tabs = [] # The Category Tabs
        self.checkbox_groups = []
        self.checkbox_names =[]
        self.all_checkboxes = dict() # All Checkboxes by their corresponding UniqueKeyword.unique_id

        m_layout = self.inner.menuBar().addMenu("Layout")
        self.a_cat = m_layout.addAction("Category")
        self.a_cat.setCheckable(True)
        self.a_cat.setChecked(False)

        self.a_class = m_layout.addAction("Class-Obj / Category")
        self.a_class.setCheckable(True)
        self.a_class.setChecked(True)

        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

        if self.behaviour == "query":
            self.btn_StartClassification.hide()
            self.btn_StopClassification.hide()
            self.btn_Previous.hide()
            self.btn_Next.hide()
            self.lbl_CurrentContainer.hide()
            self.comboBox_Sorting.hide()
            self.stackedWidget.setCurrentIndex(1)
            self.progressBar.hide()


    def on_changed(self, project, item):
        if self.behaviour == "classification":
            self.comboBox_Experiment.clear()
            if len(project.experiments) > 0:
                self.setEnabled(True)
                for e in project.experiments:
                    self.comboBox_Experiment.addItem(e.get_name())
            else:
                self.setEnabled(False)
        else:
            self.update_widget()
        return

    def on_loaded(self, project):
        if self.behaviour == "classification":
            self.comboBox_Experiment.clear()
            if len(project.experiments) > 0:
                self.setEnabled(True)
                for e in project.experiments:
                    self.comboBox_Experiment.addItem(e.get_name())
            else:
                self.setEnabled(False)

            self.stackedWidget.setCurrentIndex(0)
        else:
            if len(project.experiments) > 0:
                self.current_query_keywords = []
                self.setEnabled(True)
                self.current_experiment = project.experiments[0]
            self.stackedWidget.setCurrentIndex(1)
            self.update_widget()

    def on_selected(self, sender, selected):
        # if isinstance(selected, )
        # if self.behaviour == "query":
        #     self.current_experiment =
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
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if len(self.sorted_containers) > self.current_idx:
                self.current_container = self.sorted_containers[self.current_idx]
                self.main_window.project.set_selected(None, selected=[self.current_container])
                self.lbl_CurrentContainer.setText(self.current_container.get_name())
                self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
            else:
                self.current_container = None
            if self.current_container is None:
                return

            # Check if we need to rebuild the layout or if the checkboxes stay the same,
            # if so apply the classification of the current container
            if set(self.all_checkboxes.keys()) == set(itm.unique_id for itm in self.current_experiment.get_unique_keywords(self.current_container.get_parent_container())):
                for checkbox in self.all_checkboxes.values():
                    checkbox.stateChanged.disconnect()
                    checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                    checkbox.stateChanged.connect(partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                return

        self.tab_widget.clear()
        self.tabs = []
        self.all_checkboxes = dict()
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

        # Draw Fields
        if self.current_container is not None or self.behaviour == "query":
            if self.behaviour == "query":
                keywords = self.current_experiment.get_unique_keywords()
            else:
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
                if self.behaviour == "classification":
                    checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                    checkbox.stateChanged.connect(partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                else:
                    checkbox.setChecked(k in self.current_query_keywords)
                    checkbox.stateChanged.connect(partial(self.on_query_changed, checkbox))
                group.add_checkbox(checkbox)
                self.all_checkboxes[k.unique_id] = checkbox

        for g in self.tabs:
            for t in g:
                t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.frame_container(self.current_container)

    def update_layout_categories(self):
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if len(self.sorted_containers) > self.current_idx:
                self.current_container = self.sorted_containers[self.current_idx]
                self.main_window.project.set_selected(None, selected=[self.current_container])
                self.lbl_CurrentContainer.setText(self.current_container.get_name())
                self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
            else:
                self.current_container = None
            if self.current_container is None:
                return

            # Check if we need to rebuild the layout or if the checkboxes stay the same,
            # if so apply the classification of the current container
            if set(self.all_checkboxes.keys()) == set(itm.unique_id for itm in
                                                      self.current_experiment.get_unique_keywords(
                                                              self.current_container.get_parent_container())):
                for checkbox in self.all_checkboxes.values():
                    checkbox.stateChanged.disconnect()
                    checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                    checkbox.stateChanged.connect(
                        partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                return

        self.tab_widget.clear()
        self.tabs = []
        self.tab_categories = []
        self.checkbox_groups = []
        self.all_checkboxes = dict()
        self.checkbox_names = []

        if self.current_container is not None or self.behaviour == "query":
            if self.behaviour == "query":
                keywords = self.current_experiment.get_unique_keywords()
            else:
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
                if self.behaviour == "classification":
                    checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                    checkbox.stateChanged.connect(partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                else:
                    checkbox.setChecked(k in self.current_query_keywords)
                    checkbox.stateChanged.connect(partial(self.on_query_changed, checkbox))
                self.all_checkboxes[k.k.unique_id] = checkbox
                group.add_checkbox(checkbox)

        for t in self.tabs:
            t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.frame_container(self.current_container)

    def on_query_changed(self, checkbox):
        if checkbox.isChecked():
            if checkbox.word not in self.current_query_keywords:
                self.current_query_keywords.append(checkbox.word)
        else:
            if checkbox.word in self.current_query_keywords:
                self.current_query_keywords.remove(checkbox.word)
        if self.current_experiment is not None:
            self.current_experiment.query(self.current_query_keywords)
        pass

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