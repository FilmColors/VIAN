from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu
from functools import partial
from typing import List
from core.container.media_objects import AbstractMediaObject
from core.container.project import MOVIE_DESCRIPTOR, SEGMENTATION, ANNOTATION, SEGMENT, ANNOTATION_LAYER, \
    SCREENSHOT, SCREENSHOT_GROUP, NODE_SCRIPT,MEDIA_OBJECT,EXPERIMENT, CLASSIFICATION_OBJECT, VIANProject, Screenshot,\
    Experiment
from core.corpus.client.corpus_client import CorpusClient
from core.corpus.legacy.sqlalchemy_entities import DBProject
from core.data.log import log_error, log_info, log_debug, log_warning


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

        if container_type == MEDIA_OBJECT:
            media_objects = containers
            cm = MediaObjectContextMenu(main_window, pos, project, media_objects)
            return cm

        if container_type == EXPERIMENT:
            return ExperimentContextMenu(main_window, pos, project, containers)

        if container_type == CLASSIFICATION_OBJECT:
            return ClassificationObjectContextMenu(main_window, pos, project, containers)

        else:
            cm = ContextMenu(main_window, pos)
            return cm

    return cm

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
                log_error("ContextMenu Error", e)
                continue

    def toggle_timeline_visiblity(self):
        self.hide()
        visibility = not self.segmentation[0].timeline_visibility
        for s in self.segmentation:
            try:
                s.set_timeline_visibility(visibility)
            except Exception as e:
                log_error("ContextMenu Error", e)
                continue

    def on_delete(self):
        self.hide()
        for s in self.segmentation:
            try:
                s.project.remove_segmentation(s)
            except Exception as e:
                log_error("ContextMenu Error", e)
                continue
        self.close()

    def on_set_main(self):
        self.hide()
        try:
            self.segmentation[0].project.set_main_segmentation(self.segmentation[0])
        except Exception as e:
                log_error("ContextMenu Error", e)
        self.close()


class LayerContextMenu(ContextMenu):
    def __init__(self, parent, pos, layer):
        super(LayerContextMenu, self).__init__(parent, pos)
        self.layer = layer
        self.action_delete = self.addAction("Remove Layer")
        self.action_delete.triggered.connect(self.on_delete)

        if self.layer[0].is_visible is False:
            self.action_visibility = self.addAction("Show Layer")
        else:
            self.action_visibility = self.addAction("Hide Layer")
        self.action_visibility.triggered.connect(self.toggle_visibility)
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
                log_error("ContextMenu Error", e)
                continue
        self.close()

    def toggle_visibility(self):
        for l in self.layer:
            l.set_visibility(not l.is_visible)


    def toggle_timeline_visiblity(self):
        self.hide()
        visibility = not self.layer[0].timeline_visibility
        for s in self.layer:
            try:
                s.set_timeline_visibility(visibility)
            except Exception as e:
                log_error("ContextMenu Error", e)
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
                    log_error("ContextMenu Error", e)
                    continue
        except Exception as e:
            log_error("ContextMenu Error", e)


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
                log_error("ContextMenu Error", e)
                continue

        self.close()

    def on_delete(self):
        self.hide()
        for a in self.annotation:
            try:
                a.project.remove_annotation(a)
            except Exception as e:
                log_error("ContextMenu Error", e)
                continue
        self.close()


class ScreenshotContextMenu(ContextMenu):
    def __init__(self, parent, pos, screenshots, project: VIANProject):
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
                log_error("ContextMenu Error", e)
                continue
        self.close()

    def go_to(self):
        try:
            self.hide()
            last = self.screenshots[len(self.screenshots) - 1]
            self.main_window.player.pause()
            self.main_window.player.set_media_time(last.movie_timestamp)
        except Exception as e:
            log_error("ContextMenu Error", e)

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
                log_error("ContextMenu Error", e)
                continue
        self.close()


class MovieDescriptorContextMenu(ContextMenu):
    def __init__(self, parent, pos, movie_descriptor):
        super(MovieDescriptorContextMenu, self).__init__(parent, pos)
        self.movie_descriptor = movie_descriptor[0]
        self.main_window = parent
        self.action_set_movie_path = self.addAction("Set Movie Path")
        self.action_set_movie_path.triggered.connect(self.on_set_movie_path)
        self.action_reload = self.addAction("Reload Movie")
        self.action_reload.triggered.connect(self.on_reload_movie)
        self.action_update_movie_desc = self.addAction("Update Duration")
        self.action_update_movie_desc.triggered.connect(self.on_update_duration)
        self.popup(pos)

    def on_reload_movie(self):
        self.main_window.on_reload_movie()

    def on_set_movie_path(self):
        self.main_window.on_set_movie_path()

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
            log_error("ContextMenu Error", e)

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
                log_error("ContextMenu Error", e)
                continue

    def on_open_script(self):
        try:
            self.project.set_current_script(self.scripts[0])
        except Exception as e:
            log_error("ContextMenu Error", e)


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


class MediaObjectContextMenu(ContextMenu):
    def __init__(self, parent, pos, project:VIANProject, media_object: AbstractMediaObject):
        super(MediaObjectContextMenu, self).__init__(parent, pos)
        self.project = project
        self.media_object = media_object
        self.a_preview = self.addAction("Preview")
        self.a_delete = self.addAction("Delete Object")
        self.a_preview.triggered.connect(self.on_preview)
        self.a_delete.triggered.connect(self.on_delete)
        self.popup(pos)

    def on_preview(self):
        pass

    def on_delete(self):
        try:
            for obj in self.media_object:
                obj.container.remove_media_object(obj)
        except Exception as e:
            log_error(e)
            pass


class ExperimentContextMenu(ContextMenu):
    def __init__(self, parent, pos, project:VIANProject, experiments: List[Experiment]):
        super(ExperimentContextMenu, self).__init__(parent, pos)
        self.project = project
        self.experiments = experiments
        self.a_delete = self.addAction("Delete Experiments")
        self.a_delete.triggered.connect(self.on_delete)
        self.popup(pos)


    def on_delete(self):
        try:
            for obj in self.experiments:
                self.project.remove_experiment(obj)
        except:
            pass


class CorpusProjectContextMenu(ContextMenu):
    def __init__(self, parent, pos, project:VIANProject, corpus_project:VIANProject, corpus):
        super(CorpusProjectContextMenu, self).__init__(parent, pos)
        self.project = project
        self.corpus_project = corpus_project
        self.corpus = corpus

        self.a_open = self.addAction("Open Project")
        # self.a_check_in = self.addAction("Check In")
        # self.a_check_out = self.addAction("Check Out")
        # self.a_commit = self.addAction("Commit")
        self.a_remove = self.addAction("Remove from Corpus")

        self.a_open.triggered.connect(self.on_open)
        # self.a_check_in.triggered.connect(self.on_check_in)
        # self.a_check_out.triggered.connect(self.on_check_out)
        # self.a_commit.triggered.connect(self.on_commit)
        self.a_remove.triggered.connect(self.on_remove)
        self.popup(pos)

    def on_open(self):
        self.main_window.close_project()
        self.main_window.load_project(self.corpus_project.path)

    def on_check_in(self):
        self.corpus_client.checkin_project(self.dbproject)

    def on_check_out(self):
        self.corpus_client.checkout_project(self.dbproject)

    def on_commit(self):
        pass

    def on_remove(self):
        self.corpus.remove_project(self.corpus_project)


class ClassificationObjectContextMenu(ContextMenu):
    def __init__(self, parent, pos, project, cl_obj):
        super(ClassificationObjectContextMenu, self).__init__(parent, pos)
        self.cl_obj = cl_obj[0]
        self.project = project

        self.action_set_active = self.addAction("Set as Active Classification Object")
        self.action_set_active.triggered.connect(self.on_set_active)

        self.action_delete = self.addAction("Remove Classification Object")
        self.action_delete.triggered.connect(self.on_remove)
        self.popup(pos)

    def on_set_active(self):
        self.main_window.on_classification_object_changed(self.cl_obj)
        # self.main_window.currentClassificationObjectChanged.emit(self.cl_obj)

    def on_remove(self):
        self.cl_obj.experiment.remove_classification_object(self.cl_obj)