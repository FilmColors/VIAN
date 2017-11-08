from random import randint

class MasterClientData():
    def __init__(self, user_name, client_id, project_data):
        self.ID = client_id
        self.user_name = user_name
        self.project_data = project_data

class ProjectData():
    def __init__(self, project_ID ="", project_name="", project_path="", movie_path="",movie_descriptor="", performed_analysis = None):
        self.project_ID = project_ID
        self.project_name = project_name
        self.project_path = project_path
        self.movie_path = movie_path
        self.movie_descriptor = movie_descriptor
        self.performed_analysis = performed_analysis

    def from_EEXTProject(self, p):
        self.project_ID = randint(10000, 90000)
        self.project_name = p.name
        self.project_path = p.path
        self.movie_descriptor = CorpusMovie().from_movie_descriptor(p.movie_descriptor)
        self.movie_path = self.movie_descriptor.movie_path
        return self



class CorpusMovie():
    def __init__(self, movie_name = "", movie_path = "", movie_id = -0001, year = 1800, source = "", duration = 100):
        self.movie_name = movie_name
        self.movie_path = movie_path
        self.movie_id = movie_id
        self.year = year
        self.source = source
        self.duration = duration
        self.projects = []

    def add_project(self, project_data):
        self.projects.append(project_data)

    def update_project(self, project_data):
        project = self.find_project(project_data)
        if project is None:
            self.add_project(project_data)
        else:
            self.projects[self.projects.index(project)] = project_data


    def from_movie_descriptor(self, desc):
        self.movie_name = desc.movie_name
        self.movie_path = desc.movie_path
        self.movie_id = desc.movie_id
        self.year = desc.year
        self.source = desc.source
        self.duration = desc.duration
        self.projects = []
        return self

    def find_project(self, project_data):
        for p in self.projects:
            if p.project_ID == project_data.project_ID:
                return p
        return None


class Corpus():
    def __init__(self, corpus_name = ""):

        self.corpus_name = corpus_name
        self.corpus_movies = []

    def find_movie(self, path):
        for m in self.corpus_movies:
            if m.movie_path == path:
                return m
        else:
            return None

    def update_project(self, project_data):
        movie = self.find_movie(project_data.movie_descriptor.movie_path)
        if movie is None:
            movie = CorpusMovie()
            movie.from_movie_descriptor(project_data.movie_descriptor)
            self.corpus_movies.append(movie)

        movie.update_project(project_data)






