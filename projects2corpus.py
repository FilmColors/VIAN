from core.corpus.shared.entities import *
from core.data.headless import *
from core.corpus.client.corpus_interfaces import LocalCorpusInterface
from core.corpus.shared.corpusdb import *
import glob
import hashlib, uuid
from threading import Thread

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

def prepare_project(vian_project_path):
    local_corpus = LocalCorpusInterface()
    project, mw = load_project_headless(vian_project_path)
    local_corpus.prepare_project(project, True)


def commit_project(vian_project_path, corpus_path = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"):
    user = DBContributor(name = "Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg", affiliation="Nahh")
    project, mw = load_project_headless(vian_project_path)
    mw.load_screenshots()
    local_corpus = LocalCorpusInterface()
    local_corpus.connect_user(user, corpus_path)
    local_corpus.commit_project(user, project)


def commit_no_prepare( file, corpus_path = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"):
    user = DBContributor(name="Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg",
                         affiliation="Nahh")
    local_corpus = DatasetCorpusDB()
    local_corpus.load(corpus_path)
    local_corpus.commit_project(file, user)


CORPUS_ROOT = "F:\\_corpus\\"
USER_CSV = "F:\\_input\\Accounts.csv"


if __name__ == '__main__':
    # Create a Corpus if it does not already exist
    if not os.path.isdir(CORPUS_ROOT):
        db = create_corpus(CORPUS_ROOT)
        # Create Users
        users = parse_users(USER_CSV)
        for u in users:
            db.add_user(DBContributor(u['name'], "", u['affiliation'], u['password'], u['email']))

    # Prepare All Projects (Export it's masks and screenshots, create a Zip file)
    c = 0
    zipped = glob.glob("F:/_projects/*.zip")

    project_files = glob.glob("F:/_projects/*/*.eext")
    to_prepare = []

    for f in project_files:
        print("\n#### ---", (str(c) + "/" + str(len(project_files))).rjust(6), f, "---####")
        prepare = True
        for q in zipped:
            if f.replace("\\", "/").split("/").pop().replace(".eext", "") in q:
                prepare = False
                break
        if prepare:
            to_prepare.append(f)

    n_threads  = 5
    threads = []
    for i, file in enumerate(to_prepare):
        if c % n_threads == 0:
            for t in threads:
                t.join()
            threads = []
            print(c, "/", len(to_prepare))
        else:
            thread = Thread(target=prepare_project, args=file)
            thread.start()
            threads.append(thread)

    # Commit all Projects to the Corpus
    zipped = glob.glob("F:/_projects/*.zip")
    for f in zipped:
        commit_no_prepare(f)
