import dataset as ds

from core.corpus.shared.entities import *


class CorpusDB():
    def __init__(self):
        pass

    def add_project(self, project:VIANProject):
        pass

    def commit_project(self, project:VIANProject):
        pass

    def checkout_project(self, project_id):
        pass

    def import_dataset(self, csv_dataset):
        pass

    def initialize(self, settings: DBSettings):
        pass

    def connect(self, path):
        pass

    def disconnect(self):
        pass

    def get_segments(self, filters):
        pass

    def get_screenshots(self, filters):
        pass

    def get_annotations(self, filters):
        pass

    def get_vocabularies(self):
        pass

    def get_analysis_results(self, filters):
        pass

    def get_words(self):
        pass

    def get_settings(self):
        pass

    def save(self, path):
        pass

    def load(self, path):
        pass

    def clear(self, tables = None):
        pass


class DatasetCorpusDB(CorpusDB):
    def __init__(self):
        super(DatasetCorpusDB, self).__init__()
        self.path = None
        self.db = None
        pass

    def connect(self, path):
        self.path = path
        self.db = ds.connect(path)
        pass

    def disconnect(self):
        pass

    def initialize(self, settings: DBSettings):
        pass

    def add_project(self, project: VIANProject):
        pass

    def import_dataset(self, csv_dataset):
        pass

    def get_segments(self, filters):
        pass

    def get_screenshots(self, filters):
        pass

    def get_annotations(self, filters):
        pass

    def get_vocabularies(self):
        pass

    def get_settings(self):
        pass

    def get_words(self):
        pass

    def save(self, path):
        pass

    def load(self, path):
        pass

    def clear(self, tables = None):
        pass
