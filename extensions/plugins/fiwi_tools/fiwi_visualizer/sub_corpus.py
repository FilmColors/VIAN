from collections import namedtuple
from extensions.plugins.fiwi_tools.fiwi_visualizer.filmcolors_db import DBMovie
MovieTuple = namedtuple("MovieTuple", ["name", "fm_id", "year"])

class SubCorpus():
    def __init__(self, name):
        self.name = name
        self.movies = []

    def add_movie(self, movie: DBMovie):
        pass

    def remove_movie(self, movie: DBMovie):
        pass

    def get_corpus_fm_ids(self):
        item_ids = []
        for m in self.movies:
            item_ids.append(m.movie_id_db)
        return item_ids


class CorpusView():
    def __init__(self):
        pass