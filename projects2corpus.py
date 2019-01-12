# TODO DEPRECATED
#
# from core.corpus.shared.entities import *
# from core.data.headless import *
# from core.corpus.client.corpus_interfaces import LocalCorpusInterface
# from core.corpus.shared.corpusdb import *
# import glob
# import hashlib, uuid
# from threading import Thread
#
# salt = uuid.uuid4().hex
#
# import csv
#
# def parse_users(file):
#     users = []
#     with open(file, "r") as f:
#         reader = csv.reader(f, delimiter=";")
#         for i, r in enumerate(reader):
#             if i == 0:
#                 continue
#             else:
#                 users.append(dict(
#                     name = r[0],
#                     affiliation = r[1],
#                     password =  hashlib.sha512((r[2] + salt).encode()).hexdigest(),
#                     email = hashlib.sha512((r[3] + salt).encode()).hexdigest(),
#                     short = r[4]
#                 )
#             )
#     return users
#
#
# def create_corpus(path, name = "ERC_FilmColorsCorpus"):
#     database = DatasetCorpusDB()
#     database.allow_movie_upload = False
#     database.allow_project_download = True
#     database.initialize(name, path)
#     return database
#
# def prepare_project(vian_project_path, a):
#     try:
#         local_corpus = LocalCorpusInterface()
#         project, mw = load_project_headless(vian_project_path)
#         if project is None or mw is None:
#             return
#         mw.load_screenshots()
#         local_corpus.prepare_project(project, True)
#     except Exception as e:
#         print("ERROR", vian_project_path)
#
#
#
# def commit_project(vian_project_path, corpus_path = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"):
#     user = DBContributor(name = "Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg", affiliation="Nahh")
#     project, mw = load_project_headless(vian_project_path)
#     mw.load_screenshots()
#     local_corpus = LocalCorpusInterface()
#     local_corpus.connect_user(user, corpus_path)
#     local_corpus.commit_project(user, project)
#
#
# def commit_no_prepare( file, corpus_path = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"):
#     user = DBContributor(name="Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg",
#                          affiliation="Nahh")
#     local_corpus = DatasetCorpusDB()
#     local_corpus.load(corpus_path)
#     local_corpus.commit_project(file, user, omit_existing=True)
#
#
# CORPUS_ROOT = "F:\\_corpus\\"
# USER_CSV = "F:\\_input\\Accounts.csv"
# N_PROJECT = 500
#
#
# if __name__ == '__main__':
#     ##TEst Corpus
#     # if not os.path.isdir(CORPUS_ROOT + "\\DemoCorpus\\"):
#     #     db = create_corpus(CORPUS_ROOT, name="DemoCorpus")
#     #     # Create Users
#     #     users = parse_users(USER_CSV)
#     #     for u in users:
#     #         db.add_user(DBContributor(u['name'], "", u['affiliation'], u['password'], u['email']))
#     # # Commit all Projects to the Corpus
#     # zipped = glob.glob("F:/_projects/*.zip")
#     # to_add = ["329", "272", "200", "217", "415", "3100", "207"]
#     # for i, f in enumerate(zipped):
#     #     for a in to_add:
#     #         if a in f:
#     #             print(i, "/", len(zipped))
#     #             commit_no_prepare(f, corpus_path="F:\\_corpus\\DemoCorpus\\DemoCorpus.vian_corpus")
#
#     # True SCRIPT begins Here, upper is for Pajarola
#     # Create a Corpus if it does not already exist
#     if not os.path.isdir(CORPUS_ROOT + "\\ERC_FilmColorsCorpus\\"):
#         db = create_corpus(CORPUS_ROOT)
#         # Create Users
#         users = parse_users(USER_CSV)
#         for u in users:
#             db.add_user(DBContributor(u['name'], "", u['affiliation'], u['password'], u['email']))
#
#     # Prepare All Projects (Export it's masks and screenshots, create a Zip file)
#     c = 0
#     zipped = glob.glob("F:/_projects/*.zip")
#
#     project_files = glob.glob("F:/_projects/*/*.eext")
#     to_prepare = []
#     for f in project_files:
#         prepare = True
#         for q in zipped:
#             if f.replace("\\", "/").split("/").pop().replace(".eext", "") in q:
#                 prepare = False
#                 break
#         if prepare:
#             to_prepare.append(f)
#
#     print("To Prepare:", len(to_prepare), "of", len(project_files))
#     threads = []
#     c = 0
#     n_threads = 8
#     for i, file in enumerate(to_prepare):
#         c += 1
#         if i > N_PROJECT:
#             break
#
#         if c % n_threads == 0:
#             for t in threads:
#                 t.join()
#             threads = []
#             print(c, "/", len(to_prepare))
#         print("\n#### ---", (str(c) + "/" + str(len(project_files))).rjust(6), f, "---####")
#
#         thread = Thread(target=prepare_project, args=(file, None))
#         thread.start()
#         threads.append(thread)
#
#     for t in threads:
#         t.join()
#     zipped = glob.glob("F:/_projects/*.zip")
#     errors = []
#     for i, f in enumerate(zipped):
#         print(i, "/", len(zipped))
#         try:
#             commit_no_prepare(f)
#         except:
#             print("Error", f)
#             print("\n")
#             errors.append(f)
#
#     for f in errors:
#         print(f)
#


