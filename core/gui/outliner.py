import os
from random import randint
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QLineEdit, QMainWindow
from PyQt5.QtGui import QFont, QIcon

from core.data.computation import ms_to_string
from core.data.interfaces import IProjectChangeNotify
from core.gui.context_menu import open_context_menu, CorpusProjectContextMenu
from .ewidgetbase import EDockWidget
from core.corpus.client.corpus_client import CorpusClient
from core.corpus.shared.entities import DBProject

class Outliner(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window, corpus_client:CorpusClient):
        super(Outliner, self).__init__(main_window, width=500)
        path = os.path.abspath("qt_ui/Outliner.ui")
        uic.loadUi(path, self)

        self.tree = OutlinerTreeWidget(None,self, self.project(), main_window)
        self.dockWidgetContents.layout().addWidget(self.tree)
        self.performed_selection = False
        self.project_item = None

        self.corpus_client = corpus_client

        self.corpus_client.onCorpusConnected.connect(self.recreate_tree)
        self.corpus_client.onCorpusDisconnected.connect(self.recreate_tree)
        self.corpus_client.onCorpusChanged.connect(self.recreate_tree)
        self.item_list = []


        self.show()

    def recreate_tree(self):
        self.tree.selection_dispatch = False
        # Storing last State of the None container items
        first_time = True
        self.item_list = []


        if self.project_item is not None:
            first_time = False
            exp_p_item = self.project_item.isExpanded()
            exp_group_nodes = []
            for i in range(self.project_item.childCount()):
                exp_group_nodes.append(self.project_item.child(i).isExpanded())

        self.tree.clear()
        self.project_item = None
        p = self.project()
        if p is not None:
            self.project_item = ProjectOutlinerItem(self.tree, 0, p)

            self.descriptor_item = MovieDescriptorOutlinerItem(self.project_item, 0, p.movie_descriptor)
            self.item_list.append(self.descriptor_item)
            #self.descriptor_item.setIcon(0, QtGui.QIcon("qt_ui/icons/icon_movie.png"))

            # Segmentation
            self.segmentation_group = SegmentationOutlinerRootItem(self.project_item, 0)
            for i, st in enumerate(p.get_segmentations()):
                segmentation_item =  SegmentationOutlinerItem(self.segmentation_group, i, st)
                self.item_list.append(segmentation_item)

                if i == self.project().main_segmentation_index:
                    segmentation_item.setIcon(0, QtGui.QIcon("qt_ui/icons/icon_main_segment.png"))

                for j, s in enumerate(st.segments):
                    segment_item = SegmentOutlinerItem(segmentation_item, i, s)
                    self.item_list.append(segment_item)
            # Screenshots
            self.screenshot_group = ScreenshotRootOutlinerItem(self.project_item, 1)
            for i, scr_grp in enumerate(p.screenshot_groups):
                scr_group =  ScreenshotGroupOutlinerItem(self.screenshot_group, i, scr_grp)

                if scr_grp is self.project().active_screenshot_group:
                    scr_group.setIcon(0, QtGui.QIcon("qt_ui/icons/icon_main_segment.png"))

                for j, scr in enumerate(scr_grp.screenshots):
                    screenshot = ScreenshotOutlinerItem(scr_group, i, scr)
                    self.item_list.append(screenshot)
            # for i, scr in enumerate(p.get_screenshots()):
            #     screenshot =  ScreenshotOutlinerItem(self.screenshot_group, i, scr)
            #     self.item_list.append(screenshot)

            # Annotations
            self.annotation_group = AnnotationLayerOutlinerRootItem(self.project_item, 2)
            for i,l in enumerate(self.main_window.project.get_annotation_layers()):
                layer_item = AnnotationLayerOutlinerItem(self.annotation_group, i, l)
                self.item_list.append(layer_item)
                for j, d in enumerate(l.annotations):
                    annotation_item = AnnotationOutlinerItem(layer_item, j, d)
                    self.item_list.append(annotation_item)


            self.analyzes_group = AnalyzesOutlinerRootItem(self.project_item, 3)
            for i, a in enumerate(self.main_window.project.analysis):
                analysis_item = AnalyzesOutlinerItem(self.analyzes_group, i, a)
                self.item_list.append(analysis_item)

            self.node_scripts_group = NodeScriptsRootItem(self.project_item, 4)
            for i, s in enumerate(self.main_window.project.node_scripts):
                script_item = NodeScriptsItem(self.node_scripts_group, i, s)
                self.item_list.append(script_item)
                for j, n in enumerate(s.nodes):
                    node_item = NodeScriptsNodeItem(script_item, j, n)
                    self.item_list.append(node_item)

            self.experiment_group = ExperimentRootItem(self.project_item, 5)
            for i, exp in enumerate(self.main_window.project.experiments):
                experiment_item = ExperimentItem(self.experiment_group, i, exp)
                self.item_list.append(experiment_item)

            if not first_time:
                self.project_item.setExpanded(exp_p_item)
                for i in range(self.project_item.childCount()):
                    self.project_item.child(i).setExpanded(exp_group_nodes[i])

                complete_list = []
                self.project_item.get_children(complete_list)
                for i in complete_list:
                    if i.has_item:
                        i.setExpanded(i.get_container().outliner_expanded)

                    # self.on_selected(None, self.project().selected)
            self.tree.selection_dispatch = True

            for entry in self.item_list:
                if entry.has_item:
                    for i, a in enumerate(entry.get_container().connected_analyses):
                        analysis_item = AnalyzesOutlinerItem(entry, i, a)
                        self.item_list.append(analysis_item)


            self.on_selected(None, self.project().get_selected())

        if self.corpus_client.connected:
            to_add = []
            if self.project() is not None:
                for p in self.corpus_client.get_projects():
                    if p.name != self.project().get_name():
                        to_add.append(p)

            for p in sorted(to_add, key= lambda x:x.name):
                itm = CorpusProjectOutlinerItem(self.tree, 0, p)
                self.item_list.append(itm)

    def update_tree(self, item):
        found = False
        for itm in self.item_list:
            if itm.get_container() == item:
                itm.update_item()
                found = True
                break
        # TODO this should be item sensitive
        if not found:
            self.recreate_tree()

    def add_segmentation(self, segmentation):
        for i, st in enumerate(segmentation):
            segmentation_item = SegmentationOutlinerItem(self.segmentation_group, i, st)

            for j, s in enumerate(st.segments):
                segment_item = SegmentOutlinerItem(segmentation_item, i, s)
                segment_item.setText(0, str(s.ID))

    def remove_segmentation(self, segmentation):
        for i in range(self.segmentation_group.childCount()):
            if self.segmentation_group.child(i).segmentation is segmentation:
                self.segmentation_group.removeChild(self.segmentation_group.child(i))

    def add_annotation_layer(self, layer):

        layer_item = AnnotationLayerOutlinerItem(self.annotation_group, 0, layer)
        layer_item.setText(0, layer.name)
        layer_item.setText(1, ms_to_string(layer.t_start))
        layer_item.setText(2, ms_to_string(layer.t_end))
        for j, d in enumerate(layer.annotations):
            annotation_item = AnnotationOutlinerItem(layer_item, j, d)
            annotation_item.setText(0, d.a_type.name)

    def remove_annotation_layer(self, layer):
        for i in range(self.annotation_group.childCount()):
            if self.annotation_group.child(i).annotation_layer is layer:
                self.annotation_group.removeChild(self.annotation_group.child(i))

    def add_screenshot(self, scr):
        screenshot = ScreenshotOutlinerItem(self.screenshot_group, self.screenshot_group.childCount(), scr)
        screenshot.setText(0, scr.title)

    def remove_screenshot(self, scr):
        for i in range(self.screenshot_group.childCount()):
            if self.screenshot_group.child(i).screenshot is scr:
                self.screenshot_group.removeChild(self.screenshot_group.child(i))

    def on_changed(self, project, item):
        if item:
            self.update_tree(item)
        else:
            self.recreate_tree()

    def on_loaded(self, project):
        self.setDisabled(False)
        self.tree.project = project
        self.recreate_tree()

    def on_closed(self):
        self.setDisabled(True)

    def on_selected(self, sender, selected):
        if sender is self or selected is None:
            return

        else:
            self.tree.selection_dispatch = False
            items = []
            to_select = []
            top = self.tree.topLevelItem(0)
            top.get_children(items)

            if self.tree.selectionMode() == self.tree.SingleSelection:
                self.tree.clearSelection()

            for i in items:
                if i.has_item:
                    for s in selected:
                        if i.get_container() is s:
                            to_select.append(i)
                            i.parent().setExpanded(True)
                            try:
                                i.parent().parent().setExpanded(True)
                            except:
                                pass


            self.tree.select(to_select, False)
            self.tree.selection_dispatch = True

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Shift:
            self.tree.setSelectionMode(self.tree.MultiSelection)
        else:
            QKeyEvent.ignore()

    def keyReleaseEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Shift:
            self.tree.setSelectionMode(self.tree.SingleSelection)
        else:
            QKeyEvent.ignore()


class OutlinerTreeWidget(QTreeWidget):
    def __init__(self, parent, outliner, project, main_window):
        super(OutlinerTreeWidget, self).__init__(parent)
        # self.clicked.connect(self.on_clicked)
        self.doubleClicked.connect(self.on_doubleClicked)
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.editor = None
        self.click_counter = 0
        self.project = project
        self.outliner = outliner
        self.has_performed_selection = False
        self.context_menu = None
        self.selection_dispatch = True

        self.pint = 0

        font, color = main_window.settings.main_font()
        self.setFont(font)

        self.header().close()

    # def on_clicked(self, QModelIndex):
    #     self.itemFromIndex(QModelIndex).setSelected(True)
    # #     self.select([self.itemFromIndex(QModelIndex)], dispatch=True)
    #     # if self.currentItem().has_item:
    #     #     self.project.set_selected(self.outliner, self.currentItem().get_container())
    #     #     self.has_performed_selection = True

    def on_doubleClicked(self, QModelIndex):
        if not self.currentItem().is_editable:
            return
        self.click_counter = 0
        rect = self.visualItemRect(self.currentItem())
        pos = QtCore.QPoint(rect.x(), rect.y())
        pos = self.mapToParent(pos)

        self.editor = QOutlinerLineEdit(self, self.currentItem())
        self.editor.move(self.mapToParent(pos))
        self.editor.resize(QtCore.QSize(rect.width(), rect.height()))
        self.editor.setFocus(Qt.OtherFocusReason)

    def on_selection_changed(self):
        if self.selection_dispatch:
            if self.editor is not None:
                self.editor.close()

            selected_items = self.selectedItems()
            self.select(selected_items, True)

    def select(self, selected_items, dispatch = True):
        selected_objs = []

        for s in selected_items:
            if s.get_container() is not None and not isinstance(s.get_container(), DBProject):
                selected_objs.append(s.get_container())
                s.setSelected(True)

        self.update()

        if dispatch:
            self.project.set_selected(self.outliner, selected_objs)

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            if len(self.selectedIndexes()) <= 1:
                super(OutlinerTreeWidget, self).mousePressEvent(QMouseEvent)

            self.open_context_menu(QMouseEvent)
            self.setSelectionMode(self.SingleSelection)
        else:
            super(OutlinerTreeWidget, self).mousePressEvent(QMouseEvent)

    def itemExpanded(self, QTreeWidgetItem):
        container = QTreeWidgetItem.get_container()
        if container is not None:
            container.set_expanded(True)

    def itemCollapsed(self, QTreeWidgetItem):
        container = QTreeWidgetItem.get_container()
        if container is not None:
            container.set_expanded(False)

    def open_context_menu(self, QMouseEvent):
        if self.context_menu is not None:
            self.context_menu.close()

        if self.currentItem() is None:
            return

        if len(self.selectedIndexes()) == 0:
            return

        if isinstance(self.selectedItems()[0], ScreenshotRootOutlinerItem):
            context_menu = open_context_menu(self.outliner.main_window, self.mapToGlobal(QMouseEvent.pos()), [],
                                           self.project, screenshot_root=True)

        elif isinstance(self.selectedItems()[0], NodeScriptsRootItem):
            context_menu = open_context_menu(self.outliner.main_window, self.mapToGlobal(QMouseEvent.pos()), [],
                                           self.project, scripts_root=True)

        elif isinstance(self.selectedItems()[0], CorpusProjectOutlinerItem):
            context_menu = CorpusProjectContextMenu(self.outliner.main_window, self.mapToGlobal(QMouseEvent.pos()),
                                                    self.project, self.selectedItems()[0].get_container(), self.outliner.corpus_client)
        else:
            containers = []
            for item in self.selectedItems():
                if item.has_item is True:
                    containers.append(item.get_container())
            context_menu = open_context_menu(self.outliner.main_window, self.mapToGlobal(QMouseEvent.pos()), containers, self.project)


class QOutlinerLineEdit(QLineEdit):
    def __init__(self, parent, item):
        super(QOutlinerLineEdit, self).__init__(parent)
        self.item = item
        self.setText(self.item.get_name())
        self.selectAll()
        self.returnPressed.connect(self.on_return)

        self.show()


    def on_return(self):
        self.item.set_name(self.text())
        self.close()

    def arrow_forward(self):
        self.deselect()
        self.cursorForward(False, 1)

    def arrow_backward(self):
        self.deselect()
        self.cursorBackward(False, 1)

    def focusOutEvent(self, QFocusEvent):
        self.close()


#region Outliner Items #


class AbstractOutlinerItem(QTreeWidgetItem):
    def __init__(self, parent, index):
        super(AbstractOutlinerItem, self).__init__(parent)
        self.index = index
        self.is_editable = False
        self.has_item = False
        self.item = None

    def get_container(self):
        return None

    def get_name(self):
        return "Not Implemented"

    def set_name(self, name):
        "Not implemented"


    def update_item(self):
        if self.has_item:
            if self.get_container() is not None and self.get_container().outliner_highlighted:
                self.setForeground(0, QtGui.QColor(0,200,0))





    def get_children(self, list):
        if self.childCount() > 0:
            for i in range(self.childCount()):
                self.child(i).get_children(list)
        else:
            list.append(self)


class CorpusProjectOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, dbproject: DBProject):
        super(CorpusProjectOutlinerItem, self).__init__(parent, index)
        self.dbproject = dbproject
        self.update_item()

    def set_name(self, name):
        "Not implemented"

    def update_item(self):
        super(CorpusProjectOutlinerItem, self).update_item()
        self.setText(0, self.dbproject.name)
        if self.dbproject.is_checked_out:
            self.setForeground(0, QtGui.QColor(216, 51, 36, 150)) #0, 113, 122
        else:
            self.setForeground(0, QtGui.QColor(255, 255, 255, 200))

    def get_container(self):
        return self.dbproject


class SegmentationOutlinerRootItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(SegmentationOutlinerRootItem, self).__init__(parent, index)
        self.update_item()

    def set_name(self, name):
        "Not implemented"

    def update_item(self):
        super(SegmentationOutlinerRootItem, self).update_item()
        self.setText(0, "Segmentations")
        self.setForeground(0, QtGui.QColor(0, 167, 179)) #0, 113, 122


class SegmentationOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, segmentation):
        super(SegmentationOutlinerItem, self).__init__(parent, index)
        self.segmentation = segmentation
        self.is_editable = True
        self.has_item = True
        self.update_item()

    def get_container(self):
        return self.segmentation

    def set_name(self, name):
        self.segmentation.set_name(name)

    def get_name(self):
        return self.segmentation.name

    def update_item(self):
        super(SegmentationOutlinerItem, self).update_item()
        self.setText(0, self.segmentation.get_name())
        self.setIcon(0, QIcon())

        if self.segmentation.project.segmentation[self.segmentation.project.main_segmentation_index] is self.segmentation:
            self.setIcon(0, QtGui.QIcon("qt_ui/icons/icon_main_segment.png"))

        elif self.segmentation.timeline_visibility is False:
            self.setIcon(1 ,QtGui.QIcon("qt_ui/icons/icon_hidden.png"))

        else:
            self.setIcon(0, QIcon())


class SegmentOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, segment):
        super(SegmentOutlinerItem, self).__init__(parent, index)
        self.segment = segment
        self.has_item = True
        self.update_item()

    def get_container(self):
        return self.segment

    def set_name(self, name):
        self.segment.set_id()

    def update_item(self):
        super(SegmentOutlinerItem, self).update_item()
        self.setText(0, str(str(self.segment.ID)))


class AnnotationLayerOutlinerRootItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(AnnotationLayerOutlinerRootItem, self).__init__(parent, index)
        self.setText(0, "Annotation Layers")
        self.setForeground(0, QtGui.QColor(174, 55, 55)) #133,42,42


class AnnotationLayerOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, annotation_layer):
        super(AnnotationLayerOutlinerItem, self).__init__(parent, index)
        self.annotation_layer = annotation_layer
        self.is_editable = True
        self.has_item = True
        self.update_item()

    def get_container(self):
        return self.annotation_layer

    def set_name(self, name):
        self.annotation_layer.set_name(name)

    def get_name(self):
        return self.annotation_layer.name

    def update_item(self):
        super(AnnotationLayerOutlinerItem, self).update_item()

        self.setText(0,  self.annotation_layer.get_name())
        self.setText(1, ms_to_string(self.annotation_layer.get_start()))
        self.setText(2, ms_to_string(self.annotation_layer.get_end()))

        if self.annotation_layer.timeline_visibility is False:
            self.setIcon(0, QtGui.QIcon("qt_ui/icons/icon_hidden.png"))
        else:
            self.setIcon(0, QIcon())


class AnnotationOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, annotation):
        super(AnnotationOutlinerItem, self).__init__(parent, index)
        self.annotation = annotation
        self.is_editable = True
        self.has_item = True
        self.update_item()

    def get_container(self):
        return self.annotation

    def set_name(self, name):
       self.annotation.set_name(name)

    def get_name(self):
        return self.annotation.get_name()

    def update_item(self):
        super(AnnotationOutlinerItem, self).update_item()
        self.setText(0, self.annotation.get_name())
        self.setText(1, self.annotation.a_type.name)


class ScreenshotRootOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(ScreenshotRootOutlinerItem, self).__init__(parent, index)
        self.setText(0, "Screenshots")
        self.setForeground(0, QtGui.QColor(135, 85, 170)) #116,73,146


class ScreenshotGroupOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, screenshot_group):
        super(ScreenshotGroupOutlinerItem, self).__init__(parent, index)
        self.item = screenshot_group
        self.setText(0, screenshot_group.get_name())
        self.has_item = True
        self.is_editable = True

    def get_container(self):
        return self.item

    def set_name(self, name):
        self.item.set_name(name)

    def get_name(self):
        return self.item.get_name()


class ScreenshotOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, screenshot):
        super(ScreenshotOutlinerItem, self).__init__(parent, index)
        self.screenshot = screenshot
        self.is_editable = True
        self.has_item = True

        self.update_item()
    def get_container(self):
        return self.screenshot

    def set_name(self, name):
        self.screenshot.set_title(name)

    def get_name(self):
        return self.screenshot.title

    def update_item(self):
        super(ScreenshotOutlinerItem, self).update_item()
        self.setText(0, self.screenshot.get_name())


class ProjectOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, project):
        super(ProjectOutlinerItem, self).__init__(parent, index)
        self.project = project
        self.setText(0, project.name)
        self.is_editable = True
        self.has_item = True

        self.update_item()

    def get_container(self):
        return self.project

    def set_name(self, name):
        self.project.set_name(name)

    def get_name(self):
        return self.project.name

    def update_item(self):
        self.setText(0, self.project.name)
        self.setForeground(0, QtGui.QColor(22, 142, 42, 200))


class MovieDescriptorOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, movie_descriptor):
        super(MovieDescriptorOutlinerItem, self).__init__(parent, index)
        self.setText(0,"Movie: " + movie_descriptor.movie_name)
        self.movie_descriptor = movie_descriptor
        self.is_editable = False
        self.has_item = True
        self.update_item()

    def get_container(self):
        return self.movie_descriptor

    def set_name(self, name):
        self.movie_descriptor.set_name(name)

    def update_item(self):
        super(MovieDescriptorOutlinerItem, self).update_item()
        self.setText(0, self.movie_descriptor.movie_name)
        self.setForeground(0, QtGui.QColor(242, 170, 13)) #182,128,10


class AnalyzesOutlinerRootItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(AnalyzesOutlinerRootItem, self).__init__(parent, index)
        self.update_item()

    def set_name(self, name):
        "Not implemented"

    def update_item(self):
        self.setText(0, "Analyses")
        self.setForeground(0, QtGui.QColor(9, 170, 60)) #7,133,47


class AnalyzesOutlinerItem(AbstractOutlinerItem):
    def __init__(self, parent, index, analysis):
        super(AnalyzesOutlinerItem, self).__init__(parent, index)
        self.item = analysis
        self.update_item()
        self.has_item = True

    def get_container(self):
        return self.item

    def set_name(self, name):
        self.item.set_name(name)

    def update_item(self):
        self.setText(0, self.item.name)


class NodeScriptsRootItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(NodeScriptsRootItem, self).__init__(parent, index)
        self.update_item()

    def set_name(self, name):
        "Not implemented"

    def update_item(self):
        self.setText(0, "Node Scripts")

        self.setForeground(0, QtGui.QColor(108, 147, 120)) #81,109,90


class NodeScriptsItem(AbstractOutlinerItem):
    def __init__(self, parent, index, script):
        super(NodeScriptsItem, self).__init__(parent, index)
        self.has_item = True
        self.is_editable = True
        self.item = script
        self.update_item()

    def get_container(self):
        return self.item

    def set_name(self, name):
        self.item.set_name(name)

    def get_name(self):
        return self.item.get_name()

    def update_item(self):
        self.setText(0, self.item.get_name())


class NodeScriptsNodeItem(AbstractOutlinerItem):
    def __init__(self, parent, index, script):
        super(NodeScriptsNodeItem, self).__init__(parent, index)
        self.has_item = True
        self.is_editable = True
        self.item = script
        self.update_item()

    def get_container(self):
        return self.item

    def set_name(self, name):
        self.item.set_name(name)

    def get_name(self):
        return self.item.get_name()

    def update_item(self):
        self.setText(0, self.item.get_name())


class ExperimentRootItem(AbstractOutlinerItem):
    def __init__(self, parent, index):
        super(ExperimentRootItem, self).__init__(parent, index)
        self.update_item()

    def set_name(self, name):
        pass
        "Not implemented"

    def update_item(self):
        self.setText(0, "Experiments")
        self.setForeground(0, QtGui.QColor(106,165,255))


class ExperimentItem(AbstractOutlinerItem):
    def __init__(self, parent, index, script):
        super(ExperimentItem, self).__init__(parent, index)
        self.has_item = True
        self.is_editable = True
        self.item = script
        self.update_item()

    def get_container(self):
        return self.item

    def set_name(self, name):
        self.item.set_name(name)

    def get_name(self):
        return self.item.get_name()

    def update_item(self):
        self.setText(0, self.item.get_name())


pass
#endregion