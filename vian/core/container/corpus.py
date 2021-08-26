"""
A VIAN Corpus is a class which represents a collection of VIAN Projects,
all sharing a common template.


"""
import os
import json

from typing import Dict
from shutil import rmtree


from PyQt5.QtCore import QObject, pyqtSignal

from .project import VIANProject, merge_experiment
from .container_interfaces import IHasName
from core.data.log import log_error, log_warning, log_info
from core.data.enums import CORPUS


class Corpus(QObject, IHasName):
    onProjectAdded = pyqtSignal(object)
    onProjectRemoved = pyqtSignal(object)
    onTemplateChanged = pyqtSignal(object)

    CORPUS_FILE_EXTENSION = ".vian_corpus"

    # Merge Behaviour enums, define how to import projects into the corpus
    # If merge is set, two experiments with the same uuid or name get merged, else old gets removed
    # if keep is set, values (Vocabularies, ClassificationObjects and Keywords)
    # which are only present in the old experiment will be preserved
    MERGE_BEHAVIOUR_MERGE_KEEP = "merge-keep"
    MERGE_BEHAVIOUR_MERGE_DELETE = "merge-delete"
    MERGE_BEHAVIOUR_DELETE_DELETE = "delete-delete"

    def __init__(self, name="NewCorpus", directory="", file = None, template_movie_path = None):
        super(Corpus, self).__init__(None)
        self.projects_loaded = dict()     # type: Dict[VIANProject.uuid:VIANProject]
        self.project_paths = dict()       # type: Dict[VIANProject.uuid:str]
        self.name = name

        self.template = VIANProject("CorpusTemplate", movie_path=template_movie_path).__enter__()
        self.directory = directory
        self.file = file

    def add_project(self, project:VIANProject=None, file = None, merge_behaviour = MERGE_BEHAVIOUR_MERGE_KEEP):
        """
        Adds a project to the corpus, can either be given by VIANProject object or file
        :param project:
        :param file:
        :return:
        """
        if project is None and file is None:
            raise ValueError("Either project or file has to be given.")
        if project is None:
            results = None
            try:
                project = VIANProject().load_project(file)
                t_exp_names = [e.name for e in self.template.experiments]
                t_exp_unique_ids = [e.unique_id for e in self.template.experiments]

                template_dict = self.template.get_template(segm = True, voc = True,
                                                      ann = True, scripts = False,
                                                      experiment = True, pipeline=True)

                if merge_behaviour == self.MERGE_BEHAVIOUR_DELETE_DELETE:
                    to_remove = [e for e in project.experiments if e.name in t_exp_names or e.unique_id in t_exp_unique_ids]
                    for t in to_remove:
                        project.remove_experiment(t)
                    results = project.apply_template(template = template_dict)

                elif merge_behaviour == self.MERGE_BEHAVIOUR_MERGE_DELETE:
                    results = project.apply_template(template=template_dict, merge=True, merge_drop=True)

                elif merge_behaviour == self.MERGE_BEHAVIOUR_MERGE_KEEP:
                    results = project.apply_template(template=template_dict, merge=True, merge_drop=False)

            except Exception as e:
                log_error("Could not load project", e)
                return
            project.store_project()
            project.close()

            for l in results:
                log_info(l)

            self.projects_loaded[project.uuid] = project
            self.project_paths[project.uuid] = project.path
            self.onProjectAdded.emit(project)

    def remove_project(self, project:VIANProject = None, file = None, delete_from_disk = False):
        """
        Removes a project from the corpus, can either be given by VIANProject object or file.
        :param project:
        :param file:
        :param delete_from_disk:
        :return:
        """
        if project is None and file is None:
            raise ValueError("Either project or file has to be given.")
        if project is None:
            project = VIANProject().load_project(file)
        if project.uuid in self.project_paths:
            self.project_paths.pop(project.uuid)
        if project.uuid in self.projects_loaded:
            self.projects_loaded.pop(project.uuid)
        project.close()

        print(self.projects_loaded, self.project_paths)
        if delete_from_disk:
            project.close()
            pdir = project.folder
            try:
                if os.path.isdir(pdir):
                    rmtree(pdir)
            except Exception as e:
                log_error("Could not remove project", e)

        self.onProjectRemoved.emit(project)

    def import_template(self, path):
        self.template.apply_template(path, script_export=self.directory)
        self.onTemplateChanged.emit(self.template)

    def apply_template_to_all(self):
        self.reload()
        t = self.template.get_template(True, True, True, True, True, True)
        for uuid, p in self.projects_loaded.items():
            p.apply_template(template=t, merge=True)
            if p.path is not None:
                p.store_project()

    def reload(self, project=None):
        if project is None:
            for p in self.project_paths.values():
                if os.path.isfile(p):
                    project = VIANProject().load_project(p)
                    self.projects_loaded[project.uuid] = project
        else:
            project = VIANProject().load_project(project.path)
            self.projects_loaded[project.uuid] = project

        # We don't want to keep the hdf5 files locked
        for p in self.projects_loaded.values(): #type:VIANProject
            p.hdf5_manager.on_close()

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def serialize(self):
        """ Creates a json serialization of the corpus"""
        ser = dict(
            name = self.name,
            template = self.template.store_project(return_dict=True),
            projects = self.project_paths,
            directory = self.directory,
            file = self.file
        )
        return ser

    def deserialize(self, serialization):
        """ Loads a corpus from a serialization as given in serialize()"""
        self.name = serialization['name']
        self.template = VIANProject().load_project(serialization=serialization['template'])
        self.project_paths = serialization['projects']
        self.directory = serialization['directory']
        self.file = serialization['file']

        self.reload()
        return self

    def save(self, path=None):
        """ Serializes a Corpus into a json file """
        if path is None and self.file is None:
            log_warning("No path set for this corpus. First time, the path has to be given. The defaul name is used")
            self.file = os.path.join(self.directory, self.name)
            path = self.file
        elif self.file is not None:
            path = self.file

        if self.CORPUS_FILE_EXTENSION not in path:
            path += self.CORPUS_FILE_EXTENSION

        self.file = path
        with open(path, "w") as f:
            json.dump(self.serialize(), f)

    def load(self, path):
        """ Deserializes a Corpus from a json file """
        with open(path, "r") as f:
            self.deserialize(json.load(f))
        self.file = path
        return self

    def get_type(self):
        return CORPUS

