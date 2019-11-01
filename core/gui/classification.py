import os
from functools import partial
import time

import numpy as np
from PyQt5 import uic
from PyQt5.QtGui import QShowEvent, QHideEvent
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QTabWidget, QScrollArea, QWidget, QVBoxLayout, QGridLayout, \
    QSpacerItem, QSizePolicy, QCheckBox, QPushButton, QHBoxLayout, QLabel, QAction, QDialog, QSlider, \
    QComboBox, QFrame


from core.data.enums import SEGMENT, ANNOTATION, SCREENSHOT
from core.data.log import log_error, log_info, log_debug, log_warning
from core.data.interfaces import IProjectChangeNotify
from core.gui.ewidgetbase import EDockWidget
from core.container.experiment import Experiment
from core.container.project import Segment, Annotation, Screenshot, ClassificationObject, UniqueKeyword

MATRIX_ORDER_PER_SEGMENT = 0
MATRIX_ORDER_PER_TYPE = 1
MATRIX_ORDER_RANDOM = 2
MATRIX_ORDERS = ["By Time", "By Type", "Random"]

CLASS_OBJ_SORTING_ERC = {
    "Global" : 0,
    "Foreground" : 1,
    "Female Protagonist" : 2,
    "Male Protagonist" : 3,
    "Female Support" : 4,
    "Male Support": 5,
    "Background": 6,
    "Objects":7,
    "Environment":8,
    "Lighting": 9,
    "Intertitle":10,
}
CATEGORY_SORTING_ERC = {
    "Location / Time": 0, "Key Words": 1, "Color": 2, "Color Contrasts": 3, "Composition": 4,
    "Depth of Field": 5, "Lighting": 6, "Textures": 7, "Materials": 8, "Faktura": 9, "Movement": 10
}


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
        self.tab_widgets_class_objs = dict()
        self.tab_widget_tree = dict()

        self.cl_obj_arrangement = dict()
        self.category_arrangement = dict()

        m_layout = self.inner.menuBar().addMenu("Layout")
        self.a_cat = m_layout.addAction("Category")
        self.a_cat.setCheckable(True)
        self.a_cat.setChecked(False)

        self.a_class = m_layout.addAction("Class-Obj / Category")
        self.a_class.setCheckable(True)
        self.a_class.setChecked(True)

        self.a_hidden = m_layout.addAction("Show Hidden Vocabularies")
        self.a_hidden.setCheckable(True)
        self.a_hidden.setChecked(False)
        self.a_hidden.triggered.connect(partial(self.update_widget, True))

        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

        self.a_complexity = QAction("Change Complexity")
        self.inner.menuBar().addAction(self.a_complexity)

        self.a_complexity.triggered.connect(self.on_change_complexity)

        self.visibilityChanged.connect(self.on_visibility_changed)
        self.complexity_settings = None

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
        project.onExperimentAdded.connect(self.update_classification_list)
        project.onExperimentRemoved.connect(self.update_classification_list)

    @pyqtSlot(object)
    def enable_classification(self, s):
        self.setEnabled(True)

    @pyqtSlot(object)
    def update_classification_list(self, experiment):
        self.comboBox_Experiment.clear()
        if self.project() is None:
            return

        for e in self.project().experiments:
            self.comboBox_Experiment.addItem(e.get_name())
        if len(self.project().experiments) > 0:
            self.setEnabled(True)
        else:
            self.setEnabled(False)

    @pyqtSlot(bool)
    def on_visibility_changed(self, visibility):
        if visibility:
            if self.main_window.project is not None:
                self.on_selected(None, self.main_window.project.selected)

    def on_change_complexity(self):
        if self.current_experiment is not None:
            dialog = ComplexityDialog(self, self, self.current_experiment, complexity_settings=self.complexity_settings)
            dialog.show()
        pass

    def apply_complexities(self, d):
        self.complexity_settings = d
        self.update_widget(force = True)

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
        self.clear_view()
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
        self.update_widget(force=True)
        self.a_cat.triggered.connect(self.on_layout_changed)
        self.a_class.triggered.connect(self.on_layout_changed)

    def on_start_classification(self):
        self.stackedWidget.setCurrentIndex(1)
        self.current_idx = 0
        self.current_experiment = self.main_window.project.experiments[self.comboBox_Experiment.currentIndex()]
        self.sorted_containers = self.current_experiment.get_containers_to_classify()
        self.classification_mode = self.comboBox_ClassificationMode.currentText()

        if self.classification_mode == "Sequential":
            self.progressBar.show()
            self.btn_Previous.show()
            self.btn_Next.show()
            self.update_widget()
        else:
            self.progressBar.hide()
            self.btn_Previous.hide()
            self.btn_Next.hide()
            if len(self.project().selected) > 0:
                self.current_container = self.project().selected[0]
                self.update_widget()

    def on_stop_classification(self):
        self.stackedWidget.setCurrentIndex(0)

    def on_next(self):
        if len(self.sorted_containers) > self.current_idx + 1:
            self.current_idx += 1
            self.update_widget()
            if self.current_container is not None:
                self.frame_container(self.current_container)

    def on_previous(self):
        if 0 <= self.current_idx - 1:
            self.current_idx -= 1
            self.update_widget()
            if self.current_container is not None:
                self.frame_container(self.current_container)

    def on_order_changed(self):
        self.order_method = self.cb_ordering.currentIndex()

    def frame_container(self, container):
        if container is None:
            return

        if container.get_type() == (SEGMENT or ANNOTATION):
            self.main_window.player.set_media_time(container.get_start() + ((container.get_end() - container.get_start()) / 2))
            self.main_window.timeline.timeline.frame_time_range(container.get_start(), container.get_end())
        elif container.get_type() == SCREENSHOT:
            segm = self.main_window.project.get_main_segmentation().get_segment_of_time(container.get_start())
            self.main_window.player.set_media_time(container.get_start())
            self.main_window.timeline.timeline.frame_time_range(segm.get_start(), segm.get_end())
            self.main_window.screenshots_manager.frame_screenshot(container)

    def update_widget(self, force=False):
        if self.current_experiment is None:
            return
        if self.tab_sorting_mode == "categories":
            self.update_layout_categories(force)

        elif self.tab_sorting_mode == "class-obj":
            self.update_layout_class_obj(force)

    def clear_view(self):
        self.tab_widget.clear()
        self.tab_widget.setMovable(True)
        self.tabs = []
        self.all_checkboxes = dict()
        self.tab_categories = []
        self.checkbox_groups = []
        self.checkbox_names = []
        self.tab_widget_tree = dict()

    def update_layout_class_obj(self, force=False):
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if self.classification_mode == "Sequential":
                if len(self.sorted_containers) > self.current_idx:
                    self.current_container = self.sorted_containers[self.current_idx]
                    self.main_window.project.set_selected(self, selected=[self.current_container])
                    self.progressBar.setValue((self.current_idx + 1) / len(self.sorted_containers) * 100)
                else:
                    self.current_container = None

            if self.current_container is None :
                return
            if not (isinstance(self.current_container, Segment)
                    or isinstance(self.current_container, Annotation)
                    or isinstance(self.current_container, Screenshot)):
                return

            # print("Current Container", self.current_container)
            self.lbl_CurrentContainer.setText(self.current_container.__class__.__name__
                                              + " " + self.current_container.get_name())
            # Check  if we need to rebuild the layout or if the checkboxes stay the same,
            # if so apply the classification of the current container
            if not force:
                s1 = set(self.all_checkboxes.keys())
                s2 = []
                for k in self.current_experiment.get_unique_keywords(self.current_container.get_parent_container(),
                                                           return_all_if_none=True):
                    if not k.voc_obj.is_visible and not self.a_hidden.isChecked():
                        continue
                    s2.append(k.unique_id)

                s2 = set(s2)
                if s1 == s2:
                    for checkbox in self.all_checkboxes.values():
                        checkbox.stateChanged.disconnect()
                        checkbox.setChecked(self.current_experiment.has_tag(self.current_container, checkbox.word))
                        checkbox.stateChanged.connect(partial(self.current_experiment.toggle_tag, self.current_container, checkbox.word))
                    return

        # last_sorting_arrangement = dict()
        # for k, v in self.tab_widgets_class_objs.items():
        #     last_sorting_arrangement[k] = v.index()
        #
        # last_cl_obj_arrangement = dict()
        # for class_name, v in self.tab_widget_tree.items():
        #     last_cl_obj_arrangement[class_name] = dict()
        #     for category_name, w in self.tab_widget_tree[class_name]:
        #         if class_name in self.tab_widgets_class_objs and category_name in self.tab_widget_tree[class_name]:
        #             last_cl_obj_arrangement[class_name][category_name] = \
        #                 self.tab_widgets_class_objs[class_name].indexOf(self.tab_widget_tree[class_name][category_name])

        self.tab_widget.clear()
        self.tab_widget.setMovable(True)
        self.tabs = []
        self.all_checkboxes = dict()
        self.tab_categories = []
        self.checkbox_groups = []
        self.checkbox_names = []

        self.tab_widget_tree = dict()

        tab_widgets_class_objs_index = []
        tab_widgets_class_objs = dict()

        # Create outer tabs for Classification Objects
        ctabs = self.current_experiment.get_classification_objects_plain()
        try:
            ctabs = sorted(ctabs, key=lambda x: CLASS_OBJ_SORTING_ERC[x.name])
        except Exception as e:
            ctabs = sorted(ctabs, key=lambda x: x.name)
        for c in ctabs: #type:ClassificationObject
            visible_keywords = 0
            for kwd in c.unique_keywords: #type:UniqueKeyword
                if kwd.voc_obj.is_visible or self.a_hidden.isChecked():
                    visible_keywords += 1
            if visible_keywords == 0:
                continue
            tab = QTabWidget(self.tab_widget)
            tab.setMovable(True)
            try:
                self.tab_widget.insertTab(CLASS_OBJ_SORTING_ERC[c.name], tab, c.name)
            except Exception as e:
                self.tab_widget.addTab(tab, c.get_name())

            tab_widgets_class_objs[str(c.unique_id)] = tab
            tab_widgets_class_objs_index.append(c.unique_id)
            self.tab_widget_tree[c.name] = dict()

            self.tab_categories.append([])
            self.tabs.append([])
        self.tab_widgets_class_objs = tab_widgets_class_objs

        # Draw Fields
        if self.current_container is not None or self.behaviour == "query":
            try:
                if self.behaviour == "query":
                    keywords = self.current_experiment.get_unique_keywords()
                else:
                    keywords = self.current_experiment.get_unique_keywords(self.current_container.get_parent_container(),
                                                                           return_all_if_none=True)

                try:
                    keywords = sorted(keywords, key=lambda x: (CATEGORY_SORTING_ERC[x.voc_obj.category], not "Significance" in x.voc_obj.name, x.word_obj.name))
                except Exception as e:
                    print("Exception in Classification Redraw", e)
                    keywords = sorted(keywords, key=lambda x: (x.class_obj.name, x.voc_obj.name, x.word_obj.name))
                for k in keywords:
                    if not k.voc_obj.is_visible and not self.a_hidden.isChecked():
                        continue

                    if self.complexity_settings is not None:
                        try:
                            if self.complexity_settings[k.word_obj.complexity_group] < k.word_obj.complexity_lvl:
                                continue
                        except Exception as e:
                            print("Exception in Classification Complexity Redrwa", e)

                    idx = tab_widgets_class_objs_index.index(k.class_obj.unique_id)
                    if  k.voc_obj.category not in self.tab_categories[idx]:
                        tab = QScrollArea()
                        tab.setWidget(QWidget())
                        tab.widget().setLayout(QVBoxLayout())
                        tab.setWidgetResizable(True)

                        self.tabs[idx].append(tab)
                        self.tab_categories[idx].append(k.voc_obj.category)
                        self.tab_widget_tree[k.class_obj.name][k.voc_obj.category] = tab
                        try:
                            tab_widgets_class_objs[str(k.class_obj.unique_id)].insertTab(CATEGORY_SORTING_ERC[k.voc_obj.category], tab, k.voc_obj.category)
                        except Exception as e:
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

    def update_layout_categories(self, force=False):
        # if we are classifying, Select current Container
        if self.behaviour == "classification":
            if self.current_container is None :
                return
            if not (isinstance(self.current_container, Segment)
                    or isinstance(self.current_container, Annotation)
                    or isinstance(self.current_container, Screenshot)):
                return

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
            if not force and set(self.all_checkboxes.keys()) == set(itm.unique_id for itm in
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
                keywords = self.current_experiment.get_unique_keywords(self.current_container.get_parent_container(), return_all_if_none=True)

            keywords = sorted(keywords, key=lambda x: (x.class_obj.name, x.voc_obj.name, x.word_obj.organization_group, x.word_obj.name))
            for k in keywords:
                if not k.voc_obj.is_visible and not self.a_hidden.isChecked():
                    continue

                if self.complexity_settings is not None:
                    try:
                        if self.complexity_settings[k.word_obj.complexity_group] < k.word_obj.complexity_lvl:
                            continue
                    except Exception as e:
                        print("Exception in Classification Complexity Redraw", e)

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

    def get_settings(self):
        return self.complexity_settings

    def apply_settings(self, settings):
        self.complexity_settings = settings

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

        self.group_widgets = dict()

        self.btn_Class.setText(name.ljust(50))
        self.btn_Class.setStyleSheet("Text-align:left")
        self.btn_Class.clicked.connect(self.toggle_expand)
        self.lineEditSearchBar.textChanged.connect(self.on_search)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.toggle_expand()

    def on_search(self):
        if self.lineEditSearchBar.text() == "":
            for k in self.items:
                k.show()
        else:
            for k in self.items:
                if self.lineEditSearchBar.text().lower() in k.word.get_name().lower():
                    k.show()
                else:
                    k.hide()
        for w in self.group_widgets.values():
            w[0].check_visibility()

    def finalize(self):
        is_visualizer = False
        try:
            # In VIAN
            self.items = sorted(self.items, key=lambda x: (x.word.word_obj.organization_group, x.word.word_obj.name))
        except:
            # In Visualizer
            self.items = sorted(self.items, key=lambda x: x.word.word.name)

        self.group_widgets = dict()
        for w in self.items:
            if w.word.word_obj.organization_group not in self.group_widgets:
                group_w = ArrangementGroupBox(None)
                self.group_widgets[w.word.word_obj.organization_group] = [group_w, 0]
            self.group_widgets[w.word.word_obj.organization_group][0].add_item(w)
            self.group_widgets[w.word.word_obj.organization_group][1] += 1

        c, r  = 0, 0
        n_per_c = len(self.items) / 3
        t = None
        for k in sorted(self.group_widgets.keys()):
            w, n_words = self.group_widgets[k]
            if c == 0:
                t = self.vl_01
            elif c == 1:
                t = self.vl_02
            else:
                t = self.vl_03

            t.addWidget(w)
            r += n_words

            if r >= n_per_c:
                r = 0
                c += 1
                lbl = QLabel("")
                lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
                t.addWidget(lbl)
            elif r != 0:
                lbl = QLabel("")
                lbl.setFixedHeight(10)
                t.addWidget(lbl)

        if t is not None:
            lbl = QLabel("")
            lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            t.addWidget(lbl)

    # def finalize_old(self):
    #     is_visualizer = False
    #     try:
    #         # In VIAN
    #         self.items = sorted(self.items, key=lambda x: (x.word.word_obj.organization_group, x.word.word_obj.name))
    #     except:
    #         # In Visualizer
    #         self.items = sorted(self.items, key=lambda x: x.word.word.name)
    #         is_visualizer = True
    #
    #     size = len(self.items)
    #     n_rows = np.ceil(size / self.n_columns)
    #
    #     r = 0
    #     c = 0
    #     items_last_group = 0
    #     last_org_group = 0
    #     for w in self.items:
    #         # if a new organization group we insert an empty label
    #         items_last_group += 1
    #         if not is_visualizer:
    #             if last_org_group != w.word.word_obj.organization_group:
    #                 last_org_group = w.word.word_obj.organization_group
    #                 if items_last_group > 1:
    #                     lbl = QLabel("")
    #                     lbl.setFixedHeight(10)
    #                     if c == 0:
    #                         self.vl_01.addWidget(lbl)
    #                     elif c == 1:
    #                         self.vl_02.addWidget(lbl)
    #                     else:
    #                         self.vl_03.addWidget(lbl)
    #                     r += 1
    #                     if r == n_rows:
    #                         r = 0
    #                         c += 1
    #                 items_last_group = 0
    #
    #         if c == 0:
    #             self.vl_01.addWidget(w)
    #         elif c == 1:
    #             self.vl_02.addWidget(w)
    #         else:
    #             self.vl_03.addWidget(w)
    #         r += 1
    #         if r == n_rows:
    #             lbl = QLabel()
    #             lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    #             if c == 0:
    #                 self.vl_01.addWidget(lbl)
    #             elif c == 1:
    #                 self.vl_02.addWidget(lbl)
    #             else:
    #                 self.vl_03.addWidget(lbl)
    #             r = 0
    #             c += 1

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
        self.lineEditSearchBar.hide()
        self.widgetContent.hide()
        # for itm in self.items:
        #     itm.hide()

    def show_all(self):
        self.lineEditSearchBar.show()
        self.widgetContent.show()
        # for itm in self.items:
        #     itm.show()


class ArrangementGroupBox(QFrame):
    def __init__(self, parent):
        super(ArrangementGroupBox, self).__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.setStyleSheet("QWidget { background-color: transparent; }"
                           "QFrame  { background-color: #202020; border: 1px solid #101010; }  ")
        self.items = []

    def add_item(self, itm):
        self.items.append(itm)
        self.layout().addWidget(itm)

    def check_visibility(self):
        visible = False
        for i in self.items:
            if i.visible:
                self.show()
                visible = True
        if visible:
            self.show()
        else:
            self.hide()


class WordCheckBox(QCheckBox):
    def __init__(self, parent, word):
        super(WordCheckBox, self).__init__(parent)
        self.word = word
        self.setText(word.get_name().replace("_", " "))
        self.visible = True

    def show(self) -> None:
        super(WordCheckBox, self).show()
        self.visible = True

    def hide(self) -> None:
        super(WordCheckBox, self).hide()
        self.visible = False


class ComplexityDialog(QDialog):
    onComplete = pyqtSignal(object)

    def __init__(self, parent, classification_widget, experiment:Experiment, complexity_settings = None):
        super(ComplexityDialog, self).__init__(parent)
        self.experiment = experiment
        self.classification_widget = classification_widget
        self.setLayout(QGridLayout())

        self.complexities = {
            "0 (Undefined)": 5,
            "1 (Beginner)": 1,
            "2": 2,
            "3 (Intermediate)": 3,
            "4": 4,
            "5 (Expert)": 5
        }

        self.cboxes = dict()
        self.cb_global = QComboBox(self)
        for k, v in self.complexities.items():
            self.cb_global.addItem(k)
        self.cb_global.currentTextChanged.connect(self.on_global)
        self.layout().addWidget(QLabel("Global", self), 0, 0)
        self.layout().addWidget(self.cb_global, 0, 1)

        row = 1
        for t in experiment.get_complexity_groups():
            self.layout().addWidget(QLabel(t, self), row, 0)
            cbox = QComboBox(self)
            for k, v in self.complexities.items():
                cbox.addItem(k)

            if complexity_settings is not None and t in complexity_settings:
                cbox.setCurrentIndex(complexity_settings[t])
            self.cboxes[t] = cbox
            self.layout().addWidget(cbox, row, 1)
            row += 1

        self.btn_complete = QPushButton("Apply", self)
        self.btn_complete.clicked.connect(self.on_complete)
        self.layout().addWidget(self.btn_complete)

    def on_global(self):
        t = self.cb_global.currentText()
        for k, cb in self.cboxes.items():
            cb.setCurrentText(t)

    def on_complete(self):
        result = dict()
        for key, cbox in self.cboxes.items():
            result[key] = self.complexities[cbox.currentText()]
        self.classification_widget.apply_complexities(result)
        self.classification_widget.main_window.query_widget.apply_complexities(result)
        self.close()



