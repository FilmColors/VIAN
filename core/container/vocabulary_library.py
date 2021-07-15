import json
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSignal
from core.container.experiment import Vocabulary, VocabularyWord
from typing import Dict, List
from functools import partial
from core.container.project import VIANProject

# TODO Implement Copy Collection Behaviour
# TODO Storing Behaviour
# TODO Implement Trash

from threading import Lock


class VocabularyCollection(QObject):
    onCollectionChanged = pyqtSignal(object)

    def __init__(self, name="New Collection"):
        super(VocabularyCollection, self).__init__()
        self.name = name
        self.unique_id = str(uuid4())
        self.vocabularies = dict()  # type: Dict[str, Vocabulary]
        self.is_editable = True

    def set_name(self, name):
        self.name = name
        self.onCollectionChanged.emit(self)

    def create_vocabulary(self, name="New Vocabulary"):
        voc = Vocabulary(name, unique_id=str(uuid4()))
        self.add_vocabulary(voc)

    def add_vocabulary(self, voc:Vocabulary, force = False):
        if voc.unique_id in self.vocabularies and not force:
            raise Exception("Vocabulary already in Collection")
        else:
            self.vocabularies[voc.unique_id] = voc
            voc.onVocabularyChanged.connect(self.on_changed)

        self.onCollectionChanged.emit(self)
        return voc

    def on_changed(self):
        self.onCollectionChanged.emit(self)

    def remove_vocabulary(self, voc:Vocabulary):
        voc.onVocabularyChanged.disconnect(self.on_changed)
        if voc.unique_id in self.vocabularies:
            self.vocabularies.pop(voc.unique_id)
        self.onCollectionChanged.emit(self)
        return voc

    def __str__(self):
        s = "Vocabulary Collection {f}".format(f=self.name)
        for uid, voc in self.vocabularies.items():
            s += "\n\t-{voc_name}".format(voc_name = voc.name)
        return s

    def serialize(self):
        return dict(
            name = self.name,
            unique_id = self.unique_id,
            vocabularies = [v.serialize() for v in self.vocabularies.values()],
            is_editable = self.is_editable
        )

    @staticmethod
    def deserialize(data:Dict):
        new_instance = VocabularyCollection()
        new_instance.is_editable = data['is_editable']
        new_instance.name = data['name']
        new_instance.unique_id = data['unique_id']

        for v in data['vocabularies']:
            voc = Vocabulary().deserialize(v, None)
            new_instance.add_vocabulary(voc)

        return new_instance


class VocabularyLibrary(QObject):

    """
    The VocabularyLibrary is the central place where all vocabularies of a user are stored and shared between different
    project. Whenever a user loads a Project, the current versions of the vocabularies are fetched.
    """
    onLibraryChanged = pyqtSignal(object)

    def __init__(self):
        super(VocabularyLibrary, self).__init__()

        self.file_path = None
        self.collections = dict()
        self.voc_index = dict()
        self.voc_name = dict()

        self._write_lock = Lock()

    def reindex(self):
        self.voc_index = dict()
        for c in self.collections.values():
            for v in c.vocabularies.values():
                self.voc_index[str(v.unique_id)] = v
                self.voc_name[v.name] = v

    def on_change(self):
        self.reindex()
        if self.file_path is not None:
            self.save()
        self.onLibraryChanged.emit(self)

    def get_vocabulary_by_id(self, unique_id:str) -> Vocabulary :
        """
        Returns a vocabulary by a given unique_id.

        :param unique_id: uuid
        :return:
        """
        return self.voc_index.get(str(unique_id))

    def get_vocabulary_by_name(self, name:str) -> Vocabulary :
        """
        Returns a vocabulary by a given unique_id.

        :param unique_id: uuid
        :return:
        """
        return self.voc_name.get(str(name))

    def create_collection(self, name) -> VocabularyCollection:
        """
        Creates a new, empty collection
        :param name:
        :return: type:VocabularyCollection
        """
        col = VocabularyCollection(name)
        self.add_collection(col)
        self.on_change()

        return col

    def add_collection(self, col:VocabularyCollection) -> VocabularyCollection:
        """
        Adds a collection object to the library
        :param col:
        :return:
        """
        self.collections[col.unique_id] = col
        col.onCollectionChanged.connect(self.on_change)
        self.on_change()
        return col

    def remove_collection(self, col:VocabularyCollection):
        """
        Removes a collection from the library and puts it in the trash (todo)
        :param col:
        :return:
        """
        if col.unique_id in self.collections:
            self.collections.pop(col.unique_id)
        self.on_change()

    def copy_collection(self, col):
        # TODO needs implementation
        self.on_change()
        pass

    def save(self, filepath=None):
        """
        Serializes a collection into a JSON File
        :param filepath:
        :return:
        """
        if filepath is None and self.file_path is not None:
            filepath = self.file_path

        if filepath is None:
            raise Exception("VocabularyLibrary: Attempting to store without a given filename")

        with self._write_lock:
            data = dict(
                name="vian-vocabulary-library",
                collections=[]
            )
            for i, t in self.collections.items():
                data['collections'].append(t.serialize())

            with open(filepath, "w") as f:
                json.dump(data, f)

        return data

    def load(self, filepath):
        """
        Loads a collection from a filepath into the library.
        :param filepath:
        :return:
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        self.file_path = filepath

        for json_data in data['collections']:
            col = self.add_collection(VocabularyCollection.deserialize(json_data))

        self.on_change()
        return self


# global_library = None
if __name__ == '__main__':
    p = VIANProject().load_project("C:/Users/gaude/Documents/VIAN/projects/project_name_netflix/project_name_netflix.eext")

    library = VocabularyLibrary()
    col = library.create_collection("My Collection Number 1")

    for voc in p.vocabularies:
        col.add_vocabulary(voc)

    library.save("../../data/library.json")









