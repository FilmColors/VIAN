import datetime
import json
import os


class MasterFile():
    def __init__(self, settings):
        self.file_extension = settings.PROJECT_FILE_EXTENSION
        self.store_path = settings.MASTERFILE_PATH
        self.projects = []


    def add_project(self, project):
        name = project.name
        if name in [p['name'] for p in self.projects]:
            return

        data = dict(
            name = project.name,
            path = project.path,
            movie_path = project.movie_descriptor.movie_path,
            date = str(datetime.datetime.now().isoformat(":"))
        )
        self.projects.append(data)

        self.store()

    def check_existing(self):
        non_existing = []
        for p in self.projects:
            if not os.path.isfile(p['path']):
                non_existing.append(p)
        for p in non_existing:
            print("Removed from Masterfile:", p['path'])
            self.projects.remove(p)

        self.store()

    def remove_project(self, path):
        p_remove = None
        for p in self.projects:
            if p['path'] == path:
                p_remove = p
                break
        self.projects.remove(p_remove)
        self.store()



    def store(self):
        dict = vars(self)
        print(self.store_path)

        with open(self.store_path, 'w') as f:
            json.dump(dict, f)

    def load(self):
        if not os.path.isfile(self.store_path):
            print("No Masterfile existing")
            self.store()
            return
        try:
            with open(self.store_path) as f:
                dict = json.load(f)
                for attr, value in dict.items():
                    setattr(self, attr, value)
        except ValueError as e:
            print(e)

        self.check_existing()