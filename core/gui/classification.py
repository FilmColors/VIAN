import os
from functools import partial
import time

import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QTabWidget, QScrollArea, QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QCheckBox, QPushButton, QHBoxLayout, QLabel

from core.data.enums import SEGMENT, ANNOTATION, SCREENSHOT
from core.data.log import log_error, log_info, log_debug, log_warning
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
            self.setWindowTitle("Classification")
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
        self.tab_sorting_mode = "class-obj"

        # can be Sequential or Selection
        self.classification_mode = "Selection"

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

        self.visibilityChanged.connect(self.on_visibility_changed)

        if self.behaviour == "query":
            self.btn_StartClassification.hide()
            self.btn_StopClassification.hide()
            self.btn_Previous.hide()
            self.btn_Next.hide()
            self.lbl_CurrentContainer.hide()
            self.comboBox_Sorting.hide()
            self.stackedWidget.setCurrentIndex(1)
            self.progressBar.hide()
            self.btn_ResetQuery = QPushButton("Reset Query")
            w = QWidget()
            w.setLayout(QHBoxLayout())
            w.layout().addWidget(self.btn_ResetQuery)

            # self.btn_PromoteToScreenshots = QPushButton("Promote to Screenshots")
            # self.btn_PromoteToScreenshots.clicked.connect(self.on_promote_query_to_screenshots)
            # w.layout().addWidget(self.btn_PromoteToScreenshots)

            self.cb_PromoteToScreenshots = QCheckBox("Promote to Screenshots", w)
            self.cb_PromoteToScreenshots.stateChanged.connect(self.on_promote_query_to_screenshots_changed)
            w.layout().addWidget(self.cb_PromoteToScreenshots)
            self.stackedWidget.widget(1).layout().addWidget(w)

            self.btn_ResetQuery.clicked.connect(self.on_reset_query)

    def on_changed(self, project, item):
        pass
        # if self.behaviour == "classification":
        #     self.comboBox_Experiment.clear()
        #     if len(project.experiments) > 0:
        #         self.setEnabled(True)
        #         for e in project.experiments:
        #             self.comboBox_Experiment.addItem(e.get_name())
        #     else:
        #         self.setEnabled(False)
        # else:
        #     self.update_widget()
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

        project.onExperimentAdded.connect(self.enable_classification)

    @pyqtSlot(object)
    def enable_classification(self, s):
        self.setEnabled(True)

    @pyqtSlot(bool)
    def on_visibility_changed(self, visibility):
        if visibility:
            if self.main_window.project is not None:
                self.on_selected(None, self.main_window.project.selected)

    def on_selected(self, sender, selected):
        if not self.isVisible():
            return
        if self.behaviour == "classification":
            if sender is self:
                return
            if len(selected) > 0 \
                    and selected[0].get_type() in [SEGMENT, SCREENSHOT, ANNOTATION] \
                    and self.current_container is not selected[0]:

                self.current_container = selected[0]
                self.update_widget()
            else:
                self.current_container = None

    def on_closed(self):
        self.current_experiment = None
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
            self.tab_sorting_mode = "class-obj"
        else:
            self.a_cat.setChecked(True)
            self.a_class.setChecked(False)
            self.tab_sorting_mode = "categories"
        self.update_widget()
        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

    def on_start_classification(self):
        self.stackedWidget.setCurrentIndex(1)
        self.current_idx = 0
        self.current_experiment = self.main_window.project.experiments[self.comboBox_Experiment.currentIndex()]
        self.sorted_containers = self.current_experiment.get_containers_to_classify()
        self.classification_mode = self.comboBox_ClassificationMode.currentText()

        if self.classification_mode == "Sequential":
            self.update_widget()
            self.progressBar.show()
            self.btn_Previous.show()
            self.btn_Next.show()
        else:
            self.progressBar.hide()
            self.btn_Previous.hide()
            self.btn_Next.hide()

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
        if self.tab_sorting_mode == "categories":
            self.update_layout_categories()

        elif self.tab_sorting_mode == "class-obj":
            self.update_layout_class_obj()

    def update_layout_class_obj(self):
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if len(self.sorted_containers) > self.current_idx:
                if self.classification_mode == "Sequential":
                    self.current_container = self.sorted_containers[self.current_idx]
                    self.main_window.project.set_selected(self, selected=[self.current_container])
                self.lbl_CurrentContainer.setText(self.current_container.__class__.__name__ +" "+ self.current_container.get_name())
                self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
            else:
                self.current_container = None
            if self.current_container is None:
                return

            # Check  if we need to rebuild the layout or if the checkboxes stay the same,
            # if so apply the classification of the current container
            if set(self.all_checkboxes.keys()) == set([itm.unique_id for itm in self.current_experiment.get_unique_keywords(self.current_container.get_parent_container())]):
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
            try:
                if self.behaviour == "query":
                    keywords = self.current_experiment.get_unique_keywords()
                else:
                    keywords = self.current_experiment.get_unique_keywords(self.current_container.get_parent_container(),
                                                                           return_all_if_none=True)

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
                    group.items.append(checkbox)
                    self.all_checkboxes[k.unique_id] = checkbox

                for g in self.checkbox_groups:
                    g.finalize()
            except Exception as e:
                log_error(e)
                raise e
        for g in self.tabs:
            for t in g:
                t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        if self.classification_mode == "Sequential":
            self.frame_container(self.current_container)

    def update_layout_categories(self):
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if len(self.sorted_containers) > self.current_idx:
                if self.classification_mode == "Sequential":
                    self.current_container = self.sorted_containers[self.current_idx]
                    self.main_window.project.set_selected(None, selected=[self.current_container])
                self.lbl_CurrentContainer.setText(self.current_container.__class__.__name__ +" "+ self.current_container.get_name())
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

            keywords = sorted(keywords, key=lambda x: (x.class_obj.name, x.voc_obj.name, x.word_obj.organization_group, x.word_obj.name))
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
                self.all_checkboxes[k.unique_id] = checkbox
                group.items.append(checkbox)
            for g in self.checkbox_groups:
                g.finalize()

        for t in self.tabs:
            t.widget().layout().addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))

        if self.classification_mode == "Sequential":
            self.frame_container(self.current_container)

    def on_query_changed(self, checkbox):
        if checkbox.isChecked():
            if checkbox.word not in self.current_query_keywords:
                self.current_query_keywords.append(checkbox.word)
        else:
            if checkbox.word in self.current_query_keywords:
                self.current_query_keywords.remove(checkbox.word)
        if self.current_experiment is not None:
            self.current_experiment.query(self.current_query_keywords, self.cb_PromoteToScreenshots.isChecked())
        pass

    def on_promote_query_to_screenshots(self):
        if self.current_experiment is not None:
            self.current_experiment.query(self.current_query_keywords, True)

    def on_promote_query_to_screenshots_changed(self):
        if self.current_experiment is not None:
            self.current_experiment.query(self.current_query_keywords, self.cb_PromoteToScreenshots.isChecked())

    def on_reset_query(self):
        self.current_query_keywords = []
        self.update_widget()
        self.current_experiment.query(self.current_query_keywords, self.cb_PromoteToScreenshots.isChecked())

    @pyqtSlot(object)
    def on_experiment_changed(self, exp):
        self.update_widget()


class CheckBoxGroupWidget(QWidget):
    def __init__(self, parent, name, n_columns = 3):
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

    def finalize(self):
        is_visualizer = False
        try:
            # In VIAN
            self.items = sorted(self.items, key=lambda x: (x.word.word_obj.organization_group, x.word.word_obj.name))
        except:
            # In Visualizer
            self.items = sorted(self.items, key=lambda x: x.word.word.name)
            is_visualizer = True

        size = len(self.items)
        n_rows = np.ceil(size / self.n_columns)

        r = 0
        c = 0
        items_last_group = 0
        last_org_group = 0
        for w in self.items:
            # if a new organization group we insert an empty label
            items_last_group += 1

            if not is_visualizer:
                if last_org_group != w.word.word_obj.organization_group:
                    if items_last_group > 1:
                        last_org_group = w.word.word_obj.organization_group
                        lbl = QLabel("")
                        if c == 0:
                            self.vl_01.addWidget(lbl)
                        elif c == 1:
                            self.vl_02.addWidget(lbl)
                        else:
                            self.vl_03.addWidget(lbl)
                        r += 1
                        if r == n_rows:
                            r = 0
                            c += 1
                    items_last_group = 0

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

    def add_checkbox(self, checkbox):
        self.items.append(checkbox)
        self.finalize()

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
        self.setText(word.get_name().replace("_", " "))