import os
import json

from typing import Dict
from shutil import rmtree


from PyQt5.QtCore import QObject

from .project import VIANProject
from .container_interfaces import IHasName
from core.data.log import log_error

CORPUS_FILE_EXTENSION = ".vian_corpus"

class Corpus(QObject, IHasName):
    def __init__(self, name, directory):
        super(Corpus, self).__init__(None)
        self.projects_loaded = dict()     # type: Dict[VIANProject.uuid:VIANProject]
        self.project_paths = dict()       # type: Dict[VIANProject.uuid:str]
        self.name = name

        self.template = VIANProject("CorpusTemplate").__enter__()
        self.directory = directory

    def add_project(self, project:VIANProject=None, file = None):
        """
        Adds a project to the corpus, can either be given by VIANProject object or file
        :param project:
        :param file:
        :return:
        """
        if project is None and file is None:
            raise ValueError("Either project or file has to be given.")
        if project is None:
            try:
                project = VIANProject().load_project(file)
            except Exception as e:
                log_error("Could not load project", e)
                return

        project.close()

        self.projects_loaded[project.uuid] = project
        self.project_paths[project.uuid] = project.path

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

        if delete_from_disk:
            project.close()
            pdir = project.folder
            try:
                if os.path.isdir(pdir):
                    rmtree(pdir)
            except Exception as e:
                log_error("Could not remove project", e)

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
            directory = self.directory
        )
        return ser

    def deserialize(self, serialization):
        """ Loads a corpus from a serialization as given in serialize()"""
        self.name = serialization['name']
        self.template = VIANProject().load_project(serialization=serialization['template'])
        self.name = serialization['name']
        self.directory = serialization['directory']

        return self

    def save(self, path):
        """ Serializes a Corpus into a json file """
        if CORPUS_FILE_EXTENSION not in path:
            path += CORPUS_FILE_EXTENSION
        with open(path, "w") as f:
            json.dump(self.serialize(), f)

    def load(self, path):
        """ Deserializes a Corpus from a json file """
        with open(path, "r") as f:
            self.deserialize(json.load(f))
        return self





