from core.corpus.shared.entities import *
from core.data.headless import *
from core.corpus.client.corpus_interfaces import LocalCorpusInterface
from core.corpus.shared.corpusdb import *
import glob
import hashlib, uuid
salt = uuid.uuid4().hex

import csv

def parse_users(file):
    users = []
    with open(file, "r") as f:
        reader = csv.reader(f, delimiter=";")
        for i, r in enumerate(reader):
            if i == 0:
                continue
            else:
                users.append(dict(
                    name = r[0],
                    affiliation = r[1],
                    password =  hashlib.sha512((r[2] + salt).encode()).hexdigest(),
                    email = hashlib.sha512((r[3] + salt).encode()).hexdigest(),
                    short = r[4]
                )
            )
    return users

def create_corpus(path):
    database = DatasetCorpusDB()
    database.allow_movie_upload = False
    database.allow_project_download = True
    database.initialize("ERC_FilmColorsCorpus", path)
    return database


def commit_project(vian_project_path, corpus_path = "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\TestCorpus_01\\TestCorpus_01.vian_corpus"):
    user = DBContributor(name = "Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg", affiliation="Nahh")
    project, mw = load_project_headless(vian_project_path)
    local_corpus = LocalCorpusInterface()
    local_corpus.connect_user(user, corpus_path)
    local_corpus.commit_project(user, project)


CORPUS_ROOT = "F:\\_corpus\\"
USER_CSV = "F:\\_input\\Accounts.csv"
if __name__ == '__main__':

    db = create_corpus(CORPUS_ROOT)
    # Create Users
    users = parse_users(USER_CSV)
    for u in users:
        db.add_user(DBContributor(u['name'], "", u['affiliation'], u['password'], u['email']))

    # print(glob.glob("F:/_projects/*"))
    # for f in glob.glob("F:/_projects/*/*.eext"):
    #     print(f)
    #     commit_project(f)