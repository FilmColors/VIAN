import re
import json
import pickle
import glob
from sys import stdout as console
import os
import cv2
from core.data.importers import ELANProjectImporter
import re
import threading
import time
import shutil
from core.data.plugin import *
from core.data.interfaces import IConcurrentJob
from functools import partial
from core.gui.Dialogs.file_dialogs import MultiDirFileDialog
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QComboBox, QHBoxLayout, QMessageBox
from PyQt5 import QtWidgets
from core.gui.main_window import MainWindow

nomenclature_items = [ "FilemakerID", "None", "SGM_ID","SGM_ID_With_Sub-Segmentation", "SHOT_ID", "HR", "MIN", "SEC", "MS", "SOURCE"]

movie_formats = [".mov", ".mp4", ".mkv", ".m4v"]

#region Fetcher
class Shot():
    def __init__(self, segment_id = -1, index = -1, segment_shot_id = -1, hr = 0, min = 0, sec = 0, ms = 0, global_shot_id = -1, has_subsegment = False, subsegment = "", filemaker_ID = "", path = ""):
        self.filemaker_ID = filemaker_ID
        self.source_type = ""
        self.movie_name = ""
        self.movie_year = ""
        self.shot_id = index
        self.segment_id = segment_id
        self.segment_shot_id = segment_shot_id
        self.time = (hr, min, sec, ms)
        self.global_shot_id = global_shot_id
        self.path = path
        self.has_subsegment = has_subsegment
        self.subsegment = subsegment

    def print_shot(self, no_print = False):

        if not no_print:
            print(self.filemaker_ID, self.movie_name, self.movie_year, self.source_type, self.shot_id, [self.segment_id, self.segment_shot_id,self.global_shot_id], self.time, self.path)
        else:
            return self.filemaker_ID, self.movie_name, self.movie_year, self.source_type, self.shot_id, [self.segment_id, self.segment_shot_id,self.global_shot_id], self.time, self.path
    def deserialize(self, serialization):
        for a,v in list(serialization.items()):
            setattr(self,a,v)
        return self

    def get_path(self):
        return str(self.segment_id) + self.subsegment + "_" + str(self.segment_shot_id) + "_" + str(self.filemaker_ID[0]) + "_" + str(self.filemaker_ID[1]) + "_" + str(self.filemaker_ID[1])

class Movie():
    def __init__(self, filemaker_ID, movie_name, shots, folder_path, elan_path = None,
                 segmentation_path= None, relative_path_replace = "//130.60.131.134/studi/Filme/"):
        self.filemaker_ID = filemaker_ID
        self.movie_name = movie_name
        self.elan_path = elan_path
        self.segmentation_path = segmentation_path
        self.shots = shots
        self.folder_path = folder_path
        self.relative_path = folder_path.replace(relative_path_replace, "")


        self.needs_segmentation = False
        self.has_sub_segmentation = False

        self.errors = None
        # for s in self.shots:
        #     if s.segment_id == -1 or s.segment_shot_id == -1:
        #         self.needs_segmentation = True
        #         # print [s.segment_id, s.segment_shot_id], s.path
        #         break

    def print_movie(self):
        print(self.filemaker_ID)
        print(self.movie_name)
        print(self.elan_path)
        print(self.segmentation_path)

        print(self.folder_path)
        print(self.relative_path)

    def get_movie_path(self):
        print(self.folder_path)
        files = glob.glob(self.folder_path + "*")
        movie_file = None
        for f in movie_formats:
            for fl in files:
                if f in fl:
                    movie_file = fl
                    break
        return movie_file

    def get_elan_path(self):
        if len(self.elan_path) > 0:
            return self.elan_path[0]
        else:
            return None

    def string_ID(self):
        return str(self.filemaker_ID[0]) + "_" + str(self.filemaker_ID[1]) + "_" + str(self.filemaker_ID[2])

class FiwiFetcher():
    def __init__(self, directories = None, database_dir = "\\\\130.60.131.134\\fiwi_datenbank\\"):
        self.directories = directories
        self.movies_dirs = None
        self.movie_objs = []
        self.img_quality = 90
        self.n_threads = 20
        self.database_dir = database_dir.replace("\\", "/")
        self.database_movies = None

    def set_input_dirs(self, input_dirs):
        self.directories = input_dirs.replace("\\", "/")

    def set_database_dir(self, database_dir):
        self.database_dir = database_dir.replace("\\", "/")

    def fetch(self, movie_dirs = None):
        if movie_dirs is None:
            movie_directories = []
            movies_without_screenshots_folder = []

            for root in self.directories:
                movie_directories.extend(glob.glob(root + "/" + "*" + "/"))

        print("######FETCHER######")
        print("Total Directories Found:", len(movie_directories))

        edited = []
        for m in movie_directories:
            files_in_dir = glob.glob(m + "/*")
            contains_only_directories = True

            # Removing Empty Folders
            if len(files_in_dir) > 0:
                for f in files_in_dir:
                    if os.path.isfile(f):
                        contains_only_directories = False

                # If the Movie contains several Items
                if contains_only_directories:
                    for f in files_in_dir:
                        edited.append(f + "/")

                else:
                    edited.append(m)
                    # print m

        movie_directories = edited
        edited = []
        for m in movie_directories:
            files_in_dir = glob.glob(m + "*/")
            if len(files_in_dir) == 0:
                movies_without_screenshots_folder.append(m)
            else:
                has_SCR = False
                for f in files_in_dir:
                    if "SCR" in f or "Stills" in f:
                        has_SCR = True
                        break
                if has_SCR:
                    edited.append(m)
                else:
                    pass
                    # print m

        movie_directories = edited
        self.movies_dirs = movie_directories


        print(len(edited), len(movies_without_screenshots_folder))

    def load_movie_list(self, path = "results/Movies_with_SCR.txt"):
        result = []
        with open(path) as f:
            for l in f:
                result.append(l.replace("\n", ""))
        self.movies_dirs = result

    def fetch_movies(self):
        try:
            movie_directories = self.movies_dirs
            if movie_directories is None:
                print("No Movies Loaded")
                return

            print("MOVIE DIRS", movie_directories)
            n_ok = 0
            n_noELAN = 0
            n_SEVERAL = 0

            movie_objects = []
            for i, m in enumerate(movie_directories):
                console.write("\r" + str(i) + "/" + str(len(movie_directories)))
                m = m.replace("\\", "/")
                files = glob.glob(m + "*")

                files += glob.glob(m +"*Projektdatei" + "*/*")


                elan_files = [s for s in files if ".eaf" in s]
                movie_files = ""
                segmentation_files = [s for s in files if ".txt" in s]
                segmentation_files += [s for s in files if ".csv" in s]


                if len(elan_files) > 1:
                    for e in elan_files:
                        if "eaf.00" in e:
                            elan_files.remove(e)

                elan_path = elan_files[0]
                elan_name = elan_path.replace("\\", "/")
                elan_name = elan_name.split("/").pop()
                elan_name = elan_name.split("_")
                filemaker_id = elan_name[0:3]

                movie_name = ""
                # Handling some Errors
                if filemaker_id[0] == "3186":
                    filemaker_id = [3186, 1, 1]
                    movie_name = elan_name[1]

                elif filemaker_id[0] == "217":
                    filemaker_id = [217, 1, 1]
                    movie_name = elan_name[1]

                elif filemaker_id[0] == "CosmopolitanLondon.eaf":
                    filemaker_id = [158, 1, 1]
                    movie_name = "CosmopolitanLondon"

                elif filemaker_id[2] == "1GentlemenPreferBlondes":
                    filemaker_id[2] = "1"
                    movie_name = "GentlemenPreferBlondes"

                elif "BlackHawkDown" in elan_path:
                    filemaker_id = [272, 1, 1]
                    movie_name = "BlackHawkDown"
                else:
                    movie_name = elan_name[3]

                if "392" in elan_path:
                    print(filemaker_id, "THIS")


                filemaker_id = [int(filemaker_id[0]), int(filemaker_id[1]), int(filemaker_id[2])]

                if filemaker_id[0] == 8 or filemaker_id[0] == 167 or filemaker_id[0] == 172 or filemaker_id[0] == 845 or filemaker_id[0] == 860:
                    print(filemaker_id, elan_path)

                # console.write(str(filemaker_id).ljust(20) + movie_name.ljust(30))
                movie = Movie(filemaker_id, movie_name, None, m, elan_path, segmentation_files)
                self.movie_objs.append(movie)

            with open(os.path.abspath("extensions/fiwi_tools/results/all_movies.pickle"), "wb") as f:
                pickle.dump(self.movie_objs, f)

            return True
        except Exception as e:
            print(e)
            return False

        # with open("results/all_movies.pickle", "wb") as f:
        #     pickle.dump(self.movie_objs, f)

    def fetch_databse_movies(self):
        scr_folder = glob.glob(self.database_dir + "SCR/*")
        result = []
        for s in scr_folder:
            s = s.replace("\\", "/")
            s = s.replace(self.database_dir + "SCR/","").split("_")
            result.append([int(s[0]), int(s[1]), int(s[2])])
        self.database_movies = result

    def fetch_subsegmentation(self):
        base_path = "\\\\130.60.131.134\\studi\\Filme\\FIWI\\SCR\\".replace("\\", "/")

        with open("results/fp2_movies.pickle", "rb") as f:
            self.movie_objs = pickle.load(f)

        for movie in self.movie_objs:
            movie_folder = str(movie.filemaker_ID[0]) + "_" + str(movie.filemaker_ID[1]) + "_" + str(movie.filemaker_ID[2])
            segm_folders = glob.glob(base_path + movie_folder + "/*")

            if len(segm_folders) == 0:
                print(movie.filemaker_ID, movie.folder_path)

            else:
                try:
                    for s in segm_folders:
                        segm_ID = int(s.replace("\\", "/").split("/").pop())

                except:
                    print(s.replace("\\", "/").split("/").pop())
                    movie.has_sub_segmentation = True
                    continue

        with open("results/fp2_movies_02.pickle", "wb") as f:
            pickle.dump(self.movie_objs, f)

    def remove_duplicates(self):
        with open("results/fp2_movies_02.pickle", "rb") as f:
            self.movie_objs = pickle.load(f)
        movies = sorted(self.movie_objs, key=lambda x: x.filemaker_ID[0], reverse=False)

        result = []
        removed = []
        for i in range(len(movies)-1):
            if not movies[i].filemaker_ID == movies[i+1].filemaker_ID:
                result.append(movies[i])
            else:
                removed.append(movies[i])

        result.append(movies[len(movies)-1])

        print("#####REMOVED#######")
        for r in removed:
            print(r.filemaker_ID, r.movie_name)
        print(len(movies), len(result))

        with open("results/fp2_movies_03_duplicates.pickle", "wb") as f:
            pickle.dump(result, f)

    def remove_errors(self):
        with open("results/fp2_movies_03_duplicates.pickle", "rb") as f:
            self.movie_objs = pickle.load(f)

        for m in self.movie_objs:
            if m.filemaker_ID[0] == 266:
                m.filemaker_ID = [266, 1, 1]
                print(m.print_movie())
                print(m.filemaker_ID)
            if m.filemaker_ID[0] == 182:
                m.filemaker_ID = [182,1,1]
                print(m.filemaker_ID)
            if m.filemaker_ID[0] == 392:
                print(m.filemaker_ID)

        new_movie = Movie([329,1,1], "BladeRunner",None,
                          "//130.60.131.134/studi/Filme/spaete_Filme/329_Blade_Runner_1982/",
                          "//130.60.131.134/studi/Filme/spaete_Filme/329_Blade_Runner_1982/329_1_1_BladeRunner_1982_DVD_ELAN.eaf",
                          "//130.60.131.134/studi/Filme/spaete_Filme/329_Blade_Runner_1982/329_1_1_BladeRunner_1982_DVD_ELAN_export2.txt")

        self.movie_objs.append(new_movie)

        with open("results/fp2_movies_04_errors.pickle", "wb") as f:
            pickle.dump(self.movie_objs, f)

    def fetch_shots(self, input_movies = None, input_path = "results/fp2_movies_04_errors.pickle",
                    output_done = "results/fp2_movies_05_done.pickle",
                    output_undone="results/fp2_movies_05_undone.pickle",
                    base_folder = "\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank alt Export Einzelbilder\\FIWI\\SCR\\"):

        base_path = base_folder.replace("\\", "/")
        base_path_2 = base_folder.replace("alt", "neu")
        movies_undone = []
        movies_done = []

        if input_movies is not None:
            self.movie_objs = input_movies

        if len(self.movie_objs) == 0:
            print("No Movie Entered")
            return



        for i, movie in enumerate(self.movie_objs):
            base_path = base_folder.replace("\\", "/")

            console.flush()
            console.write("\r" + str(i) + "/" + str(len(self.movie_objs)))
            console.flush()
            shots = []

            movie_folder = str(movie.filemaker_ID[0]) + "_" + str(movie.filemaker_ID[1]) + "_" + str(
                movie.filemaker_ID[2])

            print(movie_folder, "PATH", base_path)
            to_test = base_path.split("/")[len(base_path.split("/")) - 2]
            print(to_test)
            if movie_folder in to_test:
                movie_folder = ""

            print(movie_folder, "PATH", base_path)

            segm_folders = glob.glob(base_path + movie_folder + "/*")


            if len(segm_folders) == 0:
                base_path = base_path_2
                movie_folder = str(movie.filemaker_ID[0]) + "_" + str(movie.filemaker_ID[1]) + "_" + str(
                    movie.filemaker_ID[2])
                segm_folders = glob.glob(base_path + movie_folder + "/*")
                print(segm_folders, base_path + movie_folder + "/*")


            if len(segm_folders) == 0:
                print("ERROR NO FILES FOUND", movie.filemaker_ID)
                movies_undone.append(movie)

            else:
                for s in segm_folders:
                    segm_string = s.replace("\\", "/").split("/").pop()
                    segm_ID = int(re.sub("[^0-9]", "", segm_string))
                    subsegm =  "".join(re.split("[^a-zA-Z]*", segm_string))
                    shot_paths = glob.glob(s + "/*")
                    for shot_path in shot_paths:

                        shot_ID = shot_path.replace(s + "\\", "")

                        has_subsegm = False
                        if subsegm != "":
                            has_subsegm = True

                        # shot_path = glob.glob(shot_path + "/*")[0]

                        shot_path = (shot_path + "/" + os.listdir(shot_path + "/")[0]).replace("\\", "/")
                        shot = Shot(segment_id=segm_ID, segment_shot_id=shot_ID, has_subsegment=has_subsegm, subsegment=subsegm, filemaker_ID=movie.filemaker_ID, path=shot_path)
                        shots.append(shot)

                movie.shots = shots
                if len(shots) == 0:
                    print("NO Shots", movie)
                movies_done.append(movie)


    def fetch_shots_moviedirs(self, input_movies = None, test_dir = False, nomenclature = None):
        movies_undone = []
        movies_done = []

        if input_movies is not None:
            self.movie_objs = input_movies

        if len(self.movie_objs) == 0:
            return [False, "No Movies Found"]

        for i, movie in enumerate(self.movie_objs):
            base_path = ""

            shots = []

            shots_folder = None
            folders = glob.glob(movie.folder_path + "*/")
            for s in folders:
                print(s)
                if "SCR" in s or "Stills" in s:
                    shots_folder = s
                    break

            if shots_folder is None:
                return [False, "No Shots Folder Found"]

            result = []
            shots_paths = glob.glob(shots_folder + "/*")
            shots_names = []

            for s in shots_paths:
                s = s.replace("\\", "/").replace(shots_folder.replace("\\", "/"), "")
                result.append(s)

            shots_names = result

            if test_dir:
                p = shots_names[0]
                if "_SCR_" in p:
                    p = p.split("_SCR_")[1]
                elif "_Stills_" in p:
                    p = p.split("_Stills_")
                p = p.split(".")[0].split("_")
                print(len(p))
                return [True, p]

            else:
                idx_segm_id = -1
                idx_shot_id = -1
                idx_hr = -1
                idx_min = -1
                idx_sec = -1
                idx_ms = -1

                for itm in nomenclature:
                    if itm == "SGM_ID":
                        idx_segm_id = nomenclature.index("SGM_ID")
                    elif itm == "SHOT_ID":
                        idx_shot_id = nomenclature.index("SHOT_ID")
                    elif itm == "HR":
                        idx_hr = nomenclature.index("HR")
                    elif itm == "MIN":
                        idx_min = nomenclature.index("MIN")
                    elif itm == "SEC":
                        idx_sec = nomenclature.index("SEC")
                    elif itm == "MS":
                        idx_ms = nomenclature.index("MS")

                result = []
                for i,p in enumerate(shots_names):
                    path = shots_paths[i]

                    if "_SCR_" in p:
                        p = p.split("_SCR_")[1]
                    elif "_Stills_" in p:
                        p = p.split("_Stills_")
                    p = p.split(".")[0].split("_")

                    if len(p) >= 2:
                        segm_id = p[idx_segm_id]
                        shot_id = p[idx_shot_id]

                        print(idx_segm_id, idx_shot_id)

                        if idx_hr != -1:
                            shot_hr = p[idx_hr]
                        else:
                            shot_hr = -1
                        if idx_hr != -1:
                            shot_min = p[idx_min]
                        else:
                            shot_min = -1
                        if idx_hr != -1:
                            shot_sec = p[idx_sec]
                        else:
                            shot_sec = -1
                        if idx_hr != -1:
                            shot_ms = p[idx_ms]
                        else:
                            shot_ms = -1

                        print(path)
                        shot = Shot(segm_id, filemaker_ID=movie.filemaker_ID, segment_shot_id=shot_id, hr=shot_hr, min=shot_min, sec=shot_sec, ms=shot_ms, path = path)
                        result.append(shot)

                movie.shots = result
                return [True, result]


    def fiwi_database_integrity(self, path="\\\\130.60.131.134\\fiwi_datenbank\\"):
        # self.load_movie_object("results/all_movies.pickle")
        print("Path", path)
        SCR_Folder = path + "SCR/"
        SEGM_Folder = path + "SEGM/"
        MOV_Folder = path + "MOV/"

        print("SCR_FOLDER", SCR_Folder)
        print("SEGM_FOLDER", SEGM_Folder)
        print("MOV_Folder", MOV_Folder)

        scr_movies_in = glob.glob(SCR_Folder + "*")
        segm_movies_in = glob.glob(SEGM_Folder + "*")
        mov_movies_in = glob.glob(MOV_Folder + "*")

        print("\nINPUT MOVIES")
        print(scr_movies_in)
        print(segm_movies_in)
        print(mov_movies_in)

        scr_movies = []
        segm_movies = []
        mov_movies = []
        for m in scr_movies_in:
            scr_movies.append(m.replace(SCR_Folder, ""))

        for m in segm_movies_in:
            segm_movies.append(m.replace(SEGM_Folder, "").replace("_SEGM.txt", ""))
            # print m.replace(SEGM_Folder, "").replace("_SEGM.txt", "")

        for m in mov_movies_in:
            mov_movies.append(m.replace(MOV_Folder, "").split(".")[0].replace("_MOV", ""))

        print("\nOUTPUT MOVIES")
        print(scr_movies)
        print(segm_movies)
        print(mov_movies)

        # Missing in Segmentations
        print("####Missing Segmentations in /SEGM/####")
        for m in scr_movies:
            if not m in segm_movies:
                movie_object =  self.find_movies_by_id([m])
                self.copy_segmentation(movie_object[0], SEGM_Folder + m + "_SEGM.txt")

        print("\n####MISSING IN Studi/Filme/####")
        for m in scr_movies:
            if len(self.find_movies_by_id([m])) == 0:
                print(m)

        print("\n####MISSING Movies in /MOV/####")
        for i, m in enumerate(scr_movies):
            if m not in mov_movies:
                print(i, "\t", end=' ')
                movie_object = self.find_movies_by_id([m])
                print(movie_object)
                if len(movie_object) > 0:
                    movie_object = movie_object[0]
                    if movie_object is not None:
                        movie_file = movie_object.get_movie_path()
                        print(movie_file)
                        if movie_file:
                            ext = movie_file.split(".").pop()
                            print("Copy From ", movie_file, " to ",  MOV_Folder + m + "_MOV." + ext)
                            shutil.copy2(movie_file, MOV_Folder + m + "_MOV." + ext)




    def fetch_exported(self, paths):
        movies = []
        for p in paths:
            folders = glob.glob(p + "/*")
            for f in folders:
                f = f.replace(p, "").split("_")
                movies.append([int(f[0]), int(f[1]), int(f[2])])

        return movies

    def copy_movies(self, index_range=None, rm_dir = False, root_directory = "", sign_progress = None):
        debug = False

        # with open(movie_path, "rb") as f:
        #     self.movie_objs = pickle.load(f)

        root_dir = root_directory
        shots_dir = root_dir + "SCR/"
        segmentation_dir = root_dir + "SEGM/"

        if not os.path.isdir(shots_dir):
            os.mkdir(shots_dir)
        if not os.path.isdir(segmentation_dir):
            os.mkdir(segmentation_dir)

        result = []
        errors = []
        if index_range is None:
            start = 0
            stop = len(self.movie_objs)
        else:
            start = index_range[0]
            if index_range[1] > len(self.movie_objs):
                stop = len(self.movie_objs)
                print("Ajusted END: ", stop)
            else:
                stop = index_range[1]

        for i in range(start, stop):
            movie = self.movie_objs[i]
            if rm_dir is True:
                try:
                    shutil.rmtree(shots_dir + movie.string_ID())
                except Exception as e:
                    print(e)

            t1 = time.time()
            try:
                print("Copying:",str(i).ljust(5) ,str(movie.filemaker_ID).ljust(20), movie.movie_name.ljust(25), str(len(movie.shots)).ljust(25), end=' ')

                movie_path, segmentations = ELANProjectImporter().elan_project_importer(movie.elan_path)

                segmentation_path = segmentation_dir + movie.string_ID() + "_SEGM.txt"
                movie.segmentation_path = segmentation_path
                if not debug:
                    self.store_segmentation(segmentation_path, segmentations[0])

                movie_shots_dir = shots_dir + movie.string_ID()

                if not debug:
                    if not os.path.isdir(movie_shots_dir):
                        os.mkdir(movie_shots_dir)
                threads = []
                for i, shot in enumerate(movie.shots):
                    sign_progress(float(i) / len(movie.shots))
                    shot_path = movie_shots_dir + "/" +shot.get_path() + ".jpg"
                    if not debug:
                        runner = Runner(shot.path, shot_path, self.img_quality)
                        runner.start()
                        threads.append(runner)
                    if i % self.n_threads == 0:
                        for t in threads:
                            t.join()
                        shot.path = shot_path

                result.append(movie)

                t2 = time.time()
                print(["Elapsed Time (s):", t2])

            except IOError as e:
                print(e)
                errors.append(movie)

        # with open("results/movie_sets/fp2_movies_06_copy_"+str(start)+"_" +str(stop)+".pickle", "wb") as f:
        #     pickle.dump(result, f)

        if len(errors) > 0:
            with open("results/movie_sets/fp2_movies_06_copy_"+str(start)+"_" +str(stop) + "_errors"+".pickle", "wb") as f:
                pickle.dump(errors, f)

    def diff_check(self, input_path, base_folder = "\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank neu Export Einzelbilder\\FIWI\\SCR\\"):

        with open(input_path, "rb") as f:
            self.movie_objs = pickle.load(f)

            base_folder.replace("\\", "/")
            folders = glob.glob(base_folder + "/*")
            folder_names = []

            m_3103 = Movie([3103, 1, 1], "MadameDubarry", None,
                           folder_path="\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\3103_Madame_Dubarry_1919\\",
                           elan_path= "\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\3103_Madame_Dubarry_1919\\3101_1_1_MadameDubarry_1919_DVD_Elan.eaf")

            self.movie_objs.append(m_3103)

            m_172 = Movie([172, 1, 1], "LondonsFreeShows", None,
                           folder_path="\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\172_Londons_Free_Shows_1924\\",
                           elan_path="\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\172_Londons_Free_Shows_1924\\172_1_1_LondonsFreeShows_1924_DVD_Elan.eaf")
            self.movie_objs.append(m_172)

            for f in folders:
                n = f.replace(base_folder, "").split("_")
                folder_names.append([int(n[0]),int(n[1]),int(n[2])])

            movie_ids = []
            for m in self.movie_objs:
                if m.filemaker_ID == [287,1, 1]:
                    m.filemaker_ID = [287, 1, 4]
                movie_ids.append(m.filemaker_ID)

            print("Missing in Movies")
            to_change = []
            print(len(self.movie_objs))
            for n in folder_names:
                if n not in movie_ids:
                    similar = []
                    for m in movie_ids:
                        if m[0] == n [0]:
                            similar.append(m)
                    for m in self.movie_objs:
                        if m.filemaker_ID == n:
                            self.movie_objs.remove(m)

                    print(str(n).ljust(20), similar)


            print("Missing in Folders")
            print(len(self.movie_objs))
            for n in movie_ids:
                if n not in folder_names:
                    for m in self.movie_objs:
                        if m.filemaker_ID == n:
                            self.movie_objs.remove(m)
                    print(n)
            print(len(self.movie_objs))


            with open("results/movie_sets/fp2_movies_06_InputNeu.pickle", "wb") as f:
                pickle.dump(self.movie_objs, f)

    def diff_check_02(self, base_folder = "\\\\130.60.131.134\\fiwi_datenbank\\SCR\\", source_dirs = None):
        if self.database_movies is None or self.movie_objs is None:
            print("No Movies Loaded")
            return

        not_in_database = []
        not_in_movie_dir = []
        synchronized = []

        done_fIDs = []
        for m in self.movie_objs:
            if m.filemaker_ID in self.database_movies:
                synchronized.append(m)

            else:
                not_in_database.append(m)
            done_fIDs.append(m.filemaker_ID)

        for fID in self.database_movies:
            if fID not in done_fIDs:
                not_in_movie_dir.append(fID)

        not_in_database = sorted(not_in_database, key=lambda x : x.filemaker_ID[0])
        synchronized = sorted(synchronized, key=lambda x: x.filemaker_ID[0])
        not_in_movie_dir = sorted(not_in_movie_dir, key=lambda x: x[0])
        print("###############DIFF CHECK###############")
        print("########SYNCHRONIZED:############")
        print("n-Items:", len(synchronized))
        for m in synchronized:
            print(m.filemaker_ID)

        print("\n\n")
        print("######Not in Database:###########")
        print("n-Items:", len(not_in_database))
        for m in not_in_database:
            suspect = False
            for idx in not_in_movie_dir:
                if m.filemaker_ID[0] == idx[0]:
                    print(m.filemaker_ID, "\t", idx, "(Suspect wrong Item ID)")
                    suspect = True
                    break

            if not suspect:
                print(m.filemaker_ID)


        print("\n\n")
        print("######Not in Movie DIR:###########")
        print("n-Items:", len(not_in_movie_dir))
        for m in not_in_movie_dir:
            suspect = False
            for idx in not_in_database:
                if idx.filemaker_ID[0] == m[0]:
                    print(idx.filemaker_ID, "\t", m, "(Suspect wrong Item ID)")
                    suspect = True
                    break

            if not suspect:
                print(m)

    def diff_list2movies(self, idx_list = None):
        if idx_list is None:
            paths = ["\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank alt Export Einzelbilder\\FIWI\\SCR\\",
                     "\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank neu Export Einzelbilder\\FIWI\\SCR\\"]
            idx_list = self.fetch_exported(paths)

        print(idx_list)
        movie_objs_idx = []
        for m in self.movie_objs:
            movie_objs_idx.append(m.filemaker_ID)
        print(movie_objs_idx)
        print("MOVIES -> DATABASE (Missing in Database)")
        for e in movie_objs_idx:
            if e not in idx_list:
                print(e)

        print("DATABASE -> MOVIES (Missing in Exported)")
        for e in idx_list:
            if e not in movie_objs_idx:
                print(e)

    def diff_export2database(self):
        paths = ["\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank alt Export Einzelbilder\\FIWI\\SCR\\",
        "\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank neu Export Einzelbilder\\FIWI\\SCR\\"]
        self.fetch_databse_movies()
        exported = self.fetch_exported(paths)

        to_convert = []
        print("EXPORTED -> DATABASE (Missing in Database)")
        for e in exported:
            if e not in self.database_movies:
                print(e)
                to_convert.append(e)

        print("DATABASE -> EXPORTED (Missing in Exported)")
        for e in self.database_movies:
            if e not in exported:
                print(e)

        return to_convert

    def clear_database_dir(self, movie = Movie):
        root_dir = "//130.60.131.134/fiwi_datenbank/"
        shots_dir = root_dir + "SCR/"
        to_delete = shots_dir + movie.string_ID()
        try:
            shutil.rmtree(to_delete)
        except Exception as e:
            print(e)

    def load_movie_object(self, input_path):
        with open(input_path, "rb") as f:
            self.movie_objs = pickle.load(f)
            for m in self.movie_objs:
                print(m.filemaker_ID)

    def find_movies_by_id(self, id_list):
        result = []
        # print "INPUT, ", id_list,
        for idx in id_list:
            if isinstance(idx, str) or isinstance(idx, str):
                idx = idx.split("_")
                idx = [int(idx[0]),int(idx[1]),int(idx[2])]
                # print "Splitted", idx,
            found = False
            for m in self.movie_objs:
                if idx == m.filemaker_ID:
                    result.append(m)
                    found = True
                    break
            if not found:
                print(idx, " not Found")
            else:
                pass
                #print " found"
        return result

    def movie_list(self, path):
        with open(path, "rb") as f:
            self.movie_objs = pickle.load(f)
        for m in self.movie_objs:
            print(m.filemaker_ID)

    def copy_segmentation(self, movie, path):
        movie_path, segmentations = ELANProjectImporter().elan_project_importer(movie.elan_path)
        self.store_segmentation(path, segmentations[0])

    def store_segmentation(self, path, segmentation):

        try:
            with open(path, "wb") as segmentation_file:
                if len(segmentation[1]) > 0:
                    segmentation_file.write("Sequence_No\tStart\tEnd\n")
                    print("N-Segmentations:", len(segmentation[1]))

                    for s in segmentation[1]:
                        a = str(re.sub(r'[^\x00-\x7f]', r' ', str(s[0])))
                        b = str(re.sub(r'[^\x00-\x7f]', r' ', str(s[1])))
                        c = str(re.sub(r'[^\x00-\x7f]', r' ', str(s[2])))

                        segmentation_file.write(a+ "\t" + b + "\t" + c + "\n")

                else:
                    segmentation_file.write("None")
        except Exception as e:
            print("Segmentation Export Failed.", e)

    def store_shot(self, shot, shot_path):
        path = shot.path
        img = cv2.imread(path)

        shot.path = shot_path

        if img.shape[0] > 576:
            dx = 579.0 / img.shape[0]
            img = cv2.resize(img, None, None, dx, dx, cv2.INTER_CUBIC)

        cv2.imwrite(shot_path, img, [cv2.IMWRITE_JPEG_QUALITY, self.img_quality])

    def get_all_with_multiple_items(self, paths):
        movies = []

        with open("results/all_movies.pickle", "rb") as f:
            self.movie_objs = pickle.load(f)

        for p in paths:
            folders = glob.glob(p + "/*")
            for f in folders:
                f = f.replace(p, "").split("_")
                movies.append([int(f[0]), int(f[1]), int(f[2])])

        movies = sorted(movies, key=lambda x: x[0])
        print(movies)
        with_multi_items = []
        for i, m in enumerate(movies):
            if i == len(movies) - 1:
                break
            else:
                if m[0] == movies[i + 1][0]:
                    print(m, movies[i + 1])
                    print(glob.glob("//130.60.131.134/fiwi_datenbank/SCR/" + str(m[0]) + "_" + str(m[1]) + "_" + str(m[2])))
                    with_multi_items.append(m)
                    with_multi_items.append(movies[i + 1])

        print(with_multi_items)
        database_paths = glob.glob("//130.60.131.134/fiwi_datenbank/SCR/" + "*")
        database_files = []
        for p in database_paths:
            f = p.replace("//130.60.131.134/fiwi_datenbank/SCR\\", "").split("_")
            database_files.append([int(f[0]), int(f[1]), int(f[2])])

        todo = []
        for m in movies:
            if m not in database_files:
                has_found = False
                for obj in self.movie_objs:
                    if m == obj.filemaker_ID:
                        has_found = True
                        todo.append(obj)
                if has_found is False:
                    print("Not Found", m)
        for m in todo:
            print(m.filemaker_ID, m.movie_name)

        to_rename = []
        final = []
        for m in self.movie_objs:
            if m.filemaker_ID[1] != m.filemaker_ID[2]:
                # print glob.glob("//130.60.131.134/fiwi_datenbank/SCR/" + str(m.filemaker_ID[0]) + "_" + str(m.filemaker_ID[1]) + "_" + str(m.filemaker_ID[1])), glob.glob("//130.60.131.134/fiwi_datenbank/SCR/" + str(m.filemaker_ID[0]) + "_" + str(
                #     m.filemaker_ID[1]) + "_" + str(m.filemaker_ID[2]))
                final.append(m)
            elif m.filemaker_ID in with_multi_items:
                final.append(m)




        # for m in todo:
        #     print ""
        #     print m.filemaker_ID
        #     print "Current Path", glob.glob("//130.60.131.134/fiwi_datenbank/SCR/" + str(m.filemaker_ID[0]) + "_" + str(m.filemaker_ID[1]) + "_" + str(m.filemaker_ID[1]))
        for m in todo:
            found = False
            for n in final:
                if m.filemaker_ID == n.filemaker_ID:
                    found = True
            if found is False:
                print(m.filemaker_ID, "Added")
                final.append(m)

        for m in final:
            print(m.filemaker_ID, m.elan_path)
            # print "Current Path", glob.glob(
            #     "//130.60.131.134/fiwi_datenbank/SCR/" + str(m.filemaker_ID[0]) + "_" + str(m.filemaker_ID[1]) + "_" + str(
            #         m.filemaker_ID[1]))

        self.movie_objs = final
        with open("results/correction.pickle", "wb") as f:
            pickle.dump(final, f)


#
# if __name__ == '__main__':
#     root_directory_1 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\")
#     root_directory_2 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\mittlere_Filme\\")
#     root_directory_3 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\spaete_Filme\\")
#     source_dir = [root_directory_1, root_directory_2, root_directory_3]
#
#     fetcher = FiwiFetcher(source_dir)
#     # difference = fetcher.diff_export2database()
#     # fetcher.load_movie_object("results/all_movies.pickle")
#     # result = fetcher.find_movies_by_id(difference)
#     # fetcher.fetch_shots(input_movies=result, output_done="results/correction2_done.pickle", output_undone="results/correction2_undone.pickle")
#     # fetcher.copy_movies("results/correction2_done.pickle", rm_dir=True)
#
#     fetcher.fetch()
#     fetcher.fetch_movies()
#     fetcher.diff_list2movies()
#     #
#     print "############################"
#     print "############################"
#     fetcher.fetch_databse_movies()
#     fetcher.diff_export2database()
#
#     # fetcher.get_all_with_multiple_items(["\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank alt Export Einzelbilder\\FIWI\\SCR\\",
#     #    "\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank neu Export Einzelbilder\\FIWI\\SCR\\"])
#     # fetcher.fetch_shots(output_done="results/correction_done.pickle", output_undone="results/correction_undone.pickle")
#     # fetcher.fetch_shots(input_path="results/correction_undone.pickle", output_done="results/correction_done2.pickle", output_undone="results/correction_undone2.pickle")
#
#     #fetcher.copy_movies("results/correction_done.pickle", [26, 27])
#     # fetcher.diff_check_02()
# #region PARSING FIRST
#     # fetcher = FiwiFetcher(source_dir)
#     #fetcher.load_movie_list()
#     #fetcher.fetch_movies()
#     # fetcher.fetch_subsegmentation()
#
#     # fetcher.fetch_shots(input_path="results/movie_sets/fp2_movies_06_InputNeu.pickle",
#     #                     output_done="results/fp2_movies_07_done.pickle",
#     #                     output_undone="results/fp2_movies_07_undone.pickle",
#     #                     base_folder="\\\\130.60.131.134\\fiwi_datenbank\\SCR_SOURCE\\Masterdatenbank neu Export Einzelbilder\\FIWI\\SCR\\")
#     # fetcher.copy_movies("results/fp2_movies_07_done.pickle")
#
#     # fetcher.diff_check(input_path="results/fp2_movies_05_undone.pickle")
#     # fetcher.remove_duplicates()
#     # fetcher.remove_errors()
#     # fetcher.open_sort()
#
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle")
#     # ranges = [[0, 20], [20,40],[40,60],[60,80],[80,100],[100,120],[120,140],[140,160],[160,180],[180,200],[200,240],[240,260]]
#
#
#
#     # print "Copying:", [7, 20]
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle", [7, 20])
#     #
#     # print "Copying:", [100, 200]
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle", [100, 200])
#     #
#     # print "Copying:", [40, 60]
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle", [40, 60])
#     #
#     # print "Copying:", [60, 80]
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle", [60, 80])
#     #
#     # print "Copying:", [80, 100]
#     # fetcher.copy_movies("results/fp2_movies_05_done.pickle", [80, 100])
#     # fetcher.fetch_shots()
#     # parser = FiwiParser("results/All_Shots.txt")
#     # parser.parse()
#
#     # copier = FiwiCopy()
#     # copier.create_movies()
#     # copier.check_segmentation()
#     # copier.store_movies()
#     # copier.copy_screenshots(load_movies=Tr
#
# #endregion
#endregion

class FiwiParserExtension(GAPlugin):
    def __init__(self, main_window):
        super(FiwiParserExtension, self).__init__(main_window)
        self.plugin_name = "FIWI Parser"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = FIWIParserWindow(self.main_window)
        wnd.show()


class FIWIParserWindow(QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__(parent)
        path = os.path.abspath("extensions/plugins/fiwi_tools/gui/fiwi_filetool.ui")
        uic.loadUi(path, self)
        self.main_window = parent
        self.setWindowTitle("Fiwi Parser")

        self.input_folder = None
        self.output_folder = None
        self.movie_root = None
        self.from_fm_export = False

        self.fetcher = FiwiFetcher()

        self.input_nomenclature_selectors = []
        self.output_nomenclature_selectors = []


        self.btn_BrowseInput.clicked.connect(self.on_browse_input)
        self.btn_BrowseMovieBase.clicked.connect(self.on_browse_movie_root)
        self.btn_BrowseOutput.clicked.connect(self.on_browse_output)

        self.output_nomenclature_selectors.append(self.create_item_selector("SGM_ID"))
        self.output_nomenclature_selectors.append(self.create_item_selector("SHOT_ID"))
        self.output_nomenclature_selectors.append(self.create_item_selector("FilemakerID"))

        self.update_out_pattern()

        self.btn_AddOutItem.clicked.connect(self.on_add_item)
        self.btn_RemoveOutItem.clicked.connect(self.on_remove_item)
        self.btn_Update.clicked.connect(self.on_update)
        self.btn_Run.clicked.connect(self.on_run)
        self.btn_UpdateMovieList.clicked.connect(self.on_update_movie_list)

        self.actionCopy_Movies_to_Database.triggered.connect(self.copy_movies2database)
        self.rB_FromFMExport.toggled.connect(self.on_input_type_changed)
        self.rB_FromMovieFolder.toggled.connect(self.on_input_type_changed)

    def on_input_type_changed(self):
        self.from_fm_export = self.rB_FromFMExport.isChecked()

        if self.from_fm_export:
            self.edit_InputFolders.setText("The Root Folder of the Exported Movie (../216_1_1)")
            self.btn_BrowseMovieBase.setEnabled(True)
            self.lineEdit_MovieBase.setEnabled(True)
            self.btn_UpdateMovieList.setEnabled(True)
        else:
            self.edit_InputFolders.setText("The Root Folder of the Movie (SpaeteFilme/216_****)")
            self.btn_BrowseMovieBase.setEnabled(False)
            self.lineEdit_MovieBase.setEnabled(False)
            self.btn_UpdateMovieList.setEnabled(False)

    def copy_movies2database(self):
        try:
            if self.output_folder is not None:
                self.fetcher.load_movie_object(os.path.abspath("extensions/fiwi_tools/results/all_movies.pickle"))
                self.fetcher.fiwi_database_integrity(path=self.output_folder)
        except:
            print("Error")

    def on_run(self):
        if self.fetcher.movie_objs is not None and self.output_folder is not None:
            job = CopyConcurrentJob([self.fetcher.movie_objs, self.output_folder])
            self.main_window.run_job_concurrent(job)
        else:
            QMessageBox.warning(self, "Error", "Please make sure, that input and output folders are set")
        #self.fetcher.copy_movies(root_directory=self.output_folder)

    def on_update(self):
        try:
            if self.input_folder is not None and self.output_folder is not None:
                if self.from_fm_export is False:
                    nomenclature = []
                    for s in self.input_nomenclature_selectors:
                        nomenclature.append(s.currentText())
                    result = self.fetcher.fetch_shots_moviedirs(self.fetcher.movie_objs, nomenclature=nomenclature)
                    self.list_SCR.clear()
                    for r in result[1]:
                        self.list_SCR.addItem(str([r.segment_id, r.segment_shot_id]).ljust(25) + str(r.time).ljust(15))
                else:
                    nomenclature = []
                    for s in self.input_nomenclature_selectors:
                        nomenclature.append(s.currentText())
                    for shot in self.fetcher.movie_objs[0].shots:
                        self.list_SCR.addItem(str([shot.segment_id, shot.segment_shot_id]).ljust(25) + str(shot.time).ljust(15))
        except Exception as e:
            print(e)


        else:
            QMessageBox.warning(self, "Error", "Please make sure, that input and output folders are set")

    def on_remove_item(self):
        to_rm = self.output_nomenclature_selectors.pop()
        to_rm.deleteLater()
        self.update_out_pattern()

    def on_add_item(self):
        to_add = self.create_item_selector("None")
        self.output_nomenclature_selectors.append(to_add)
        self.update_out_pattern()

    def update_out_pattern(self):
        for i in self.output_nomenclature_selectors:
            self.hbox_OutputPattern.addWidget(i)

    def create_item_selector(self, current):
        cb = QComboBox(self)
        cb.setMinimumContentsLength(10)
        cb.setSizeAdjustPolicy(cb.AdjustToMinimumContentsLength)
        cb.addItems(nomenclature_items)
        cb.setCurrentText(current)
        return cb

    def on_browse_input(self):
        selected = QFileDialog.getExistingDirectory()
        self.input_folder = selected + "/"
        if self.from_fm_export:
                self.update_input_filemaker_export()
        else:
            self.update_input_movie_dir()

    def on_browse_movie_root(self):
        selected = QFileDialog.getExistingDirectory()
        self.movie_root = selected + "/"
        self.lineEdit_MovieBase.setText(self.movie_root)
        # if self.input_folder is not None:
        #     self.update_input_filemaker_export()

    def on_browse_output(self):
        selected = QFileDialog.getExistingDirectory()
        self.output_folder = selected + "/"
        self.edit_OutputFolder.setText(self.output_folder)

    def on_update_movie_list(self):
        root = self.movie_root
        if root:
            root_directories = [root + "frueher_Film/",root + "mittlere_Filme/", root + "spaete_Filme/",]
            self.fetcher.directories = root_directories
            self.fetcher.fetch()
            self.fetcher.fetch_movies()
        else:
            QMessageBox.warning(self, "Parsing Failed",
                                "Please select the root folder of the movie_directories. (.../Studi/Filme)")

    def update_input_movie_dir(self):
        self.edit_InputFolders.setText(self.input_folder)
        self.fetcher.movies_dirs = [self.input_folder]

        result = self.fetcher.fetch_movies()

        if result is True:
            self.edit_ELAN.setStyleSheet("color: green;")
            self.edit_ELAN.setText(self.fetcher.movie_objs[0].elan_path)

            if len(self.fetcher.movie_objs[0].segmentation_path) > 0:
                self.edit_Segm.setText(self.fetcher.movie_objs[0].segmentation_path[0])
                self.edit_Segm.setStyleSheet("color: green;")
            else:
                self.edit_Segm.setText("NOT FOUND, will be Exported from ELAN")
            self.edit_FMID.setStyleSheet("color: green;")
            self.edit_FMID.setText(str(self.fetcher.movie_objs[0].filemaker_ID))
        else:
            QMessageBox.warning(self, "Parsing Failed",
                                "Please Make sure, that the folder contains an .eaf, and a Folder that contains either '_SCR_' or '_Stills_'")
            self.edit_ELAN.setStyleSheet("color: red;")
            self.edit_FMID.setStyleSheet("color: red;")
            self.edit_Segm.setStyleSheet("color: red;")
            self.edit_ELAN.setText("PARSING FAILED")

        result = self.fetcher.fetch_shots_moviedirs(self.fetcher.movie_objs, test_dir=True)
        if result[0] is False:
            print(result)
            return

        parsing_items = []
        if len(result[1]) == 2:
            parsing_items = ["SGM_ID", "SHOT_ID"]

        elif len(result[1]) == 3:
            parsing_items = ["HR", "MIN", "SEC"]

        elif len(result[1]) == 4:
            parsing_items = ["HR", "MIN", "SEC", "MS"]

        elif len(result[1]) == 5:
            parsing_items = ["SGM_ID", "HR", "MIN", "SEC", "MS"]

        elif len(result[1]) == 6:
            parsing_items = ["SGM_ID", "HR", "MIN", "SEC", "MS", "None"]

        for i in self.input_nomenclature_selectors:
            i.deleteLater()
        self.input_nomenclature_selectors = []

        for i in range(len(result[1])):
            cb = self.create_item_selector(parsing_items[i])
            self.input_nomenclature_selectors.append(cb)
            self.hbox_InputPattern.addWidget(cb)

    def update_input_filemaker_export(self):
        try:
            self.fetcher.load_movie_object(os.path.abspath("extensions/fiwi_tools/results/all_movies.pickle"))
            print("Loaded Movies", len(self.fetcher.movie_objs))
            stringID = self.input_folder.replace("\\","/").split("/")
            stringID.pop() # get rid of the EMPTY
            stringID = stringID.pop().split("_")
            filmaker_ID = [int(stringID[0]), int(stringID[1]), int(stringID[2])]
            result = self.fetcher.find_movies_by_id([filmaker_ID])
        except Exception as e:
            QMessageBox.warning(self, "Error", e)
            return
        if self.fetcher.movie_objs[0] is None:
            return

        if len(result) == 0:
            print(len(self.fetcher.movie_objs))
            QMessageBox.warning(self, "Error", "NO Such Movie Found in the Movie Database")
            return
        else:
            self.edit_ELAN.setStyleSheet("color: green;")
            self.edit_ELAN.setText(self.fetcher.movie_objs[0].elan_path)

            if len(result[0].segmentation_path) > 0:
                self.edit_Segm.setText(result[0].segmentation_path[0])
                self.edit_Segm.setStyleSheet("color: green;")
                self.edit_Segm.setText("NOT FOUND, will be Exported from ELAN")
            self.edit_FMID.setStyleSheet("color: green;")
            self.edit_FMID.setText(str(result[0].filemaker_ID))

            self.fetcher.fetch_shots(input_movies=result, base_folder=self.input_folder)
            if self.fetcher.movie_objs[0].shots is None:
                return

            for shot in self.fetcher.movie_objs[0].shots:
                print(shot.segment_id, shot.segment_shot_id)


        # self.fetcher.fetch_shots(input_movies=result, output_done="results/correction2_done.pickle", output_undone="results/correction2_undone.pickle")
        # self.fetcher.copy_movies("results/correction2_done.pickle", rm_dir=Tru


class CopyConcurrentJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        fetcher = FiwiFetcher()
        fetcher.movie_objs = args[0]
        fetcher.copy_movies(root_directory=args[1], sign_progress=sign_progress)


class Runner(threading.Thread):
    def __init__(self, input_path, output_path, quality = 90):
        super(Runner, self).__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.img_quality = quality

    def run(self):
        path = self.input_path
        img = cv2.imread(path)

        if img.shape[0] > 576:
            dx = 579.0 / img.shape[0]
            img = cv2.resize(img, None, None, dx, dx, cv2.INTER_CUBIC)

        cv2.imwrite(self.output_path, img, [cv2.IMWRITE_JPEG_QUALITY, self.img_quality])
