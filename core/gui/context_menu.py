import os

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QMainWindow, QMenu, QFileDialog
from core.data.enums import *
from core.data.computation import parse_file_path
from core.data.containers import *

def open_context_menu(main_window, pos, containers, project, screenshot_root = False, scripts_root=False):


    if len(containers) == 0 and (screenshot_root == False and scripts_root == False):
        return None

    elif len(containers) == 0 and screenshot_root == True:
        cm = ScreenshotRootContexMenu(main_window, pos, project)

    elif len(containers) == 0 and scripts_root == True:
        cm = ScriptsRootContexMenu(main_window, pos, project)

    else:
        container_type = containers[0].get_type()

        if container_type == MOVIE_DESCRIPTOR:
            movie_descriptor = containers
            cm = MovieDescriptorContextMenu(main_window, pos, movie_descriptor)
            return cm

        if container_type == SEGMENTATION:
            segmentations = containers
            cm = SegmentationContextMenu(main_window, pos, segmentations)
            return cm

        if container_type == SEGMENT:
            segments = containers
            cm = SegmentContexMenu(main_window, pos, segments)
            return cm

        if container_type == ANNOTATION_LAYER:
            layers = containers
            cm = LayerContextMenu(main_window, pos, layers)
            return cm

        if container_type == ANNOTATION:
            annotation = containers
            cm = AnnotationContextMenu(main_window, pos, annotation)
            return

        if container_type == SCREENSHOT:
            screenshots = containers
            cm = ScreenshotContextMenu(main_window, pos, screenshots, project)
            return cm

        if container_type == SCREENSHOT_GROUP:
            screenshots_grp = containers
            cm = ScreenshotGroupContexMenu(main_window, pos, screenshots_grp, project)
            return cm

        if container_type == NODE_SCRIPT:
            scripts = containers
            cm = NodeScriptContextMenu(main_window, pos, scripts, project)
            return cm
        else:
            cm = ContextMenu(main_window, pos)
            return cm

    return cm
#
# class ContextMenu(QMainWindow):
#     def __init__(self, parent, position, project):
#         super(ContextMenu, self).__init__(parent)
#         path = os.path.abspath("qt_ui/ContextWidget.ui")
#         self.setStyleSheet(
#             "QPushButton{border-radius: 1; padding-left: 1px; padding-right: 1px;} "
#             "QWidget{border-radius: 1; padding-left: 1px; padding-right: 1px; "
#             "color: #b1b1b1; background-color: #323232;} ")
#         uic.loadUi(path, self)
#         self.project = project
#         self.setWindowFlags(Qt.FramelessWindowHint|Qt.Popup)
#
#         # self.vlayout = QVBoxLayout(self)
#         # self.button_container.setLayout(self.vlayout)
#         self.move(position)
#
#         self.btn_delete = QPushButton(self)
#         self.btn_delete.setText("Delete")
#         self.btn_delete.clicked.connect(self.on_delete)
#
#         self.buttons = [self.btn_delete]
#         self.create_ui()
#
#
#
#     def create_ui(self):
#
#         for btn in self.buttons:
#             self.centralWidget().layout().addWidget(btn)
#
#         self.centralWidget().layout().addWidget(self.btn_delete)
#         self.resize(200, self.button_container.size().height())
#         self.show()
#
#     def on_delete(self):
#         print "Deleted"
#         self.close()
#
# class SegmentationContextMenu(ContextMenu):
#     def __init__(self, parent, position, project, segmentation):
#         super(SegmentationContextMenu, self).__init__(parent, position, project)
#         self.segmentation = segmentation
#         self.btn_hide_in_timeline = QPushButton(self)
#         self.btn_hide_in_timeline.setText("Hide in Timeline")
#         self.btn_hide_in_timeline.clicked.connect(self.on_hide_in_timeline)
#
#         self.btn_show_in_timeline = QPushButton(self)
#         self.btn_show_in_timeline.setText("Show in Timeline")
#         self.btn_show_in_timeline.clicked.connect(self.on_show_in_timeline)
#
#
#         self.buttons.extend([self.btn_hide_in_timeline,
#                              self.btn_show_in_timeline])
#
#         self.create_ui()
#
#     def on_hide_in_timeline(self):
#         for i in self.segmentation:
#             i.set_timeline_visibility(False)
#         self.close()
#
#     def on_show_in_timeline(self):
#         for i in self.segmentation:
#             i.set_timeline_visibility(True)
#         self.close()
#
#
# class LayerContextMenu(ContextMenu):
#     def __init__(self, parent, position, project, annotation_layers):
#         super(LayerContextMenu, self).__init__(parent, position, project)
#         self.annotation_layers = annotation_layers
#
#     def on_delete(self):
#         for l in self.annotation_layers:
#             print "OK", l.get_type() == con.ANNOTATION_LAYER, l.get_type()
#             if l.get_type() == con.ANNOTATION_LAYER:
#                 self.project.remove_annotation_layer(l)
#         self.close()
#
# class AnnotationContextMenu(ContextMenu):
#     def __init__(self, parent, position, project, annotations):
#         super(AnnotationContextMenu, self).__init__(parent, position, project)
#         self.annotations = annotations
#
#
#     def on_delete(self):
#         for a in self.annotations:
#             self.project.remove_annotation(a)
#         self.close()

class ContextMenu(QMenu):
    def __init__(self, parent, pos):
        super(ContextMenu, self).__init__(parent)
        self.main_window = parent
        self.setAttribute(Qt.WA_MacNoClickThrough, True)


class SegmentationContextMenu(ContextMenu):
    def __init__(self, parent, pos, segmentation):
        super(SegmentationContextMenu, self).__init__(parent, pos)
        self.segmentation = segmentation

        self.action_delete = self.addAction("Remove Segmentation")
        self.action_set_as_main = self.addAction("Set as main segmentation")

        if self.segmentation[0].timeline_visibility is True:
            self.action_set_timeline_visibility = self.addAction("Hide in Timeline")
        else:
            self.action_set_timeline_visibility = self.addAction("Show in Timeline")

        if self.segmentation[0].is_locked():
            self.action_set_locked = self.addAction("Unlock Segmentation")
        else:
            self.action_set_locked = self.addAction("Lock Segmentation")
        self.action_set_locked.triggered.connect(self.toggle_lock)

        self.action_cleanup_borders = self.addAction("Cleanup Borders")
        self.action_cleanup_borders.triggered.connect(self.cleanup_borders)
        self.action_set_timeline_visibility.triggered.connect(self.toggle_timeline_visiblity)

        self.action_copy_segmentation = self.addAction("Copy Segmentation")
        self.action_copy_segmentation.triggered.connect(self.copy_segmentation)

        self.action_delete.triggered.connect(self.on_delete)
        self.action_set_as_main.triggered.connect(self.on_set_main)



        self.popup(pos)

    def cleanup_borders(self):
        for s in self.segmentation:
            s.cleanup_borders()

    def copy_segmentation(self):
        self.segmentation[0].project.copy_segmentation(self.segmentation[0])

    def toggle_lock(self):
        self.hide()
        new_status = not self.segmentation[0].is_locked()
        for s in self.segmentation:
            try:
                if new_status:
                    s.lock()
                else:
                    s.unlock()
            except Exception as e:
                print("ContextMenu Error", e)
                continue

    def toggle_timeline_visiblity(self):
        self.hide()
        visibility = not self.segmentation[0].timeline_visibility
        for s in self.segmentation:
            try:
                s.set_timeline_visibility(visibility)
            except Exception as e:
                print("ContextMenu Error", e)
                continue

    def on_delete(self):
        self.hide()
        for s in self.segmentation:
            try:
                s.project.remove_segmentation(s)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.close()

    def on_set_main(self):
        self.hide()
        try:
            self.segmentation[0].project.set_main_segmentation(self.segmentation[0])
        except Exception as e:
                print("ContextMenu Error", e)
        self.close()


class LayerContextMenu(ContextMenu):
    def __init__(self, parent, pos, layer):
        super(LayerContextMenu, self).__init__(parent, pos)
        self.layer = layer

        self.action_delete = self.addAction("Remove Layer")
        self.action_delete.triggered.connect(self.on_delete)

        if self.layer[0].timeline_visibility is True:
            self.action_set_timeline_visibility = self.addAction("Hide in Timeline")
        else:
            self.action_set_timeline_visibility = self.addAction("Show in Timeline")
        self.action_set_timeline_visibility.triggered.connect(self.toggle_timeline_visiblity)

        if self.layer[0].is_locked():
            self.action_set_locked = self.addAction("Unlock Layer")
        else:
            self.action_set_locked = self.addAction("Lock Layer")
        self.action_set_locked.triggered.connect(self.toggle_lock)

        self.popup(pos)

    def on_delete(self):
        self.hide()
        for l in self.layer:
            try:
                l.project.remove_annotation_layer(l)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.close()

    def toggle_timeline_visiblity(self):
        self.hide()
        visibility = not self.layer[0].timeline_visibility
        for s in self.layer:
            try:
                s.set_timeline_visibility(visibility)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.hide()

    def toggle_lock(self):
        self.hide()
        try:
            new_status = not self.layer[0].is_locked()
            for s in self.layer:
                try:
                    if new_status:
                        s.lock()
                    else:
                        s.unlock()
                except Exception as e:
                    print("ContextMenu Error", e)
                    continue
        except Exception as e:
            print("ContextMenu Error", e)


class AnnotationContextMenu(ContextMenu):
    def __init__(self, parent, pos, annotation):
        super(AnnotationContextMenu, self).__init__(parent, pos)
        self.annotation = annotation


        self.action_key = self.addAction("Key Annotation")
        self.action_remove_all_key = self.addAction("Remove all Keys")
        self.action_delete = self.addAction("Remove Annotation")

        self.action_key.triggered.connect(self.on_key)
        self.action_remove_all_key.triggered.connect(self.remove_keys)
        self.action_delete.triggered.connect(self.on_delete)
        self.popup(pos)

    def on_key(self):
        self.hide()
        self.main_window.on_key_annotation()
        self.close()

    def remove_keys(self):
        self.hide()
        for a in self.annotation:
            try:
                a.remove_keys()
            except Exception as e:
                print("ContextMenu Error", e)
                continue

        self.close()

    def on_delete(self):
        self.hide()
        for a in self.annotation:
            try:
                a.project.remove_annotation(a)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.close()


class ScreenshotContextMenu(ContextMenu):
    def __init__(self, parent, pos, screenshots, project: ElanExtensionProject):
        super(ScreenshotContextMenu, self).__init__(parent, pos)
        self.screenshots = screenshots
        self.project = project


        self.action_goto = self.addAction("Go To Time")
        self.action_delete = self.addAction("Remove Screenshot")
        self.action_goto.triggered.connect(self.go_to)
        self.action_delete.triggered.connect(self.on_delete)

        self.group_menu = self.addMenu("Assign to Group ...")
        self.a_new_grp = self.group_menu.addAction("Create new Group")
        self.a_new_grp.triggered.connect(self.on_assign_to_new)
        self.group_menu.addSeparator()

        for grp in self.project.screenshot_groups:
            action = self.group_menu.addAction(grp.get_name())
            action.triggered.connect(partial(self.on_assign_grp, grp))


        self.popup(pos)

    def on_delete(self):
        self.hide()
        for s in self.screenshots:
            try:
                s.project.remove_screenshot(s)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.close()

    def go_to(self):
        try:
            self.hide()
            last = self.screenshots[len(self.screenshots) - 1]
            self.main_window.player.pause()
            self.main_window.player.set_media_time(last.movie_timestamp)
        except Exception as e:
            print("ContextMenu Error", e)

        self.close()

    def on_assign_to_new(self):
        grp = self.project.add_screenshot_group()
        self.on_assign_grp(grp)


    def on_assign_grp(self, grp):
        to_assign = []
        for s in self.screenshots:
            if isinstance(s, Screenshot):
                to_assign.append(s)

        grp.add_screenshots(to_assign)


class SegmentContexMenu(ContextMenu):
    def __init__(self, parent, pos, segments):
        super(SegmentContexMenu, self).__init__(parent, pos)
        self.segments = segments

        self.action_delete = self.addAction("Remove Segment")
        self.action_delete.triggered.connect(self.on_delete)
        self.popup(pos)


    def on_delete(self):
        self.hide()
        for s in self.segments:
            try:
                s.project.remove_segment(s)
            except Exception as e:
                print("ContextMenu Error", e)
                continue
        self.close()


class MovieDescriptorContextMenu(ContextMenu):
    def __init__(self, parent, pos, movie_descriptor):
        super(MovieDescriptorContextMenu, self).__init__(parent, pos)
        self.movie_descriptor = movie_descriptor[0]

        self.action_set_movie_path = self.addAction("Set Movie Path")
        self.action_set_movie_path.triggered.connect(self.on_set_movie_path)
        self.action_update_movie_desc = self.addAction("Update Duration")
        self.action_update_movie_desc.triggered.connect(self.on_update_duration)
        self.popup(pos)

    def on_set_movie_path(self):
        path = parse_file_path(QFileDialog.getOpenFileName(self)[0])
        self.movie_descriptor.movie_path = path
        self.main_window.player.open_movie(path)
        self.main_window.dispatch_on_changed()

    def on_update_duration(self):
        self.main_window.project.movie_descriptor.set_duration(self.main_window.player.get_media_duration())


class ScreenshotGroupContexMenu(ContextMenu):
    def __init__(self, parent, pos, screenshot_group, project):
        super(ScreenshotGroupContexMenu, self).__init__(parent, pos)
        self.screenshot_group = screenshot_group[0]
        self.project = project

        self.action_set_active = self.addAction("Set as Active Screenshot Group")
        self.action_set_active.triggered.connect(self.on_set_active)

        self.action_delete = self.addAction("Remove Screenshot Group")
        self.action_delete.triggered.connect(self.on_remove)
        self.popup(pos)

    def on_remove(self):
        self.hide()
        try:
            self.project.remove_screenshot_group(self.screenshot_group)
        except Exception as e:
            print("ContextMenu Error", e)

    def on_set_active(self):
        self.project.set_current_screenshot_group(self.screenshot_group)


class ScreenshotRootContexMenu(ContextMenu):
    def __init__(self, parent, pos, project):
        super(ScreenshotRootContexMenu, self).__init__(parent, pos)
        self.project = project

        self.action_new = self.addAction("New Screenshot Group")
        self.action_new.triggered.connect(self.on_new_screenshot_group)
        self.popup(pos)

    def on_new_screenshot_group(self):
        self.project.add_screenshot_group()


class NodeScriptContextMenu(ContextMenu):
    def __init__(self, parent, pos, scripts, project):
        super(NodeScriptContextMenu, self).__init__(parent, pos)
        self.project = project
        self.scripts = scripts

        self.action_new_script = self.addAction("New Script")
        self.action_new_script.triggered.connect(self.on_new_script)

        self.action_remove_script = self.addAction("Remove Script")
        self.action_remove_script.triggered.connect(self.on_remove_script)

        self.action_open_script = self.addAction("Open Script")
        self.action_open_script.triggered.connect(self.on_open_script)
        self.popup(pos)

    def on_new_script(self):
        self.project.create_script()

    def on_remove_script(self):
        for script in self.scripts:
            try:
                self.project.remove_script(script)
            except Exception as e:
                print("ContextMenu Error", e)
                continue

    def on_open_script(self):
        try:
            self.project.set_current_script(self.scripts[0])
        except Exception as e:
            print("ContextMenu Error", e)


class NodeScriptRootContextMenu(ContextMenu):
    def __init__(self, parent, pos, project):
        super(NodeScriptRootContextMenu, self).__init__(parent, pos)
        self.project = project

        self.action_new_script = self.addAction("New Script")
        self.action_new_script.triggered.connect(self.on_new_script)

        self.popup(pos)

    def on_new_script(self):
        self.project.create_script()


class ScriptsRootContexMenu(ContextMenu):
    def __init__(self, parent, pos, project):
        super(ScriptsRootContexMenu, self).__init__(parent, pos)
        self.project = project

        self.action_new_script = self.addAction("New Script")
        self.action_new_script.triggered.connect(self.on_new_script)

        self.popup(pos)

    def on_new_script(self):
        self.project.create_script()