import re
import json
import pickle
import glob
from sys import stdout as console
import os
import cv2
from core.data.importers import ELANProjectImporter

class ParsingError(Exception):
    def __init__(self):
        super(ParsingError, self).__init__()


class Shot():
    def __init__(self, segment_id = -1, index = -1, segment_shot_id = -1, hr = 0, min = 0, sec = 0, ms = 0, global_shot_id = -1, has_subsegment = False, subsegment = ""):
        self.filemaker_ID = ""
        self.source_type = ""
        self.movie_name = ""
        self.movie_year = ""
        self.shot_id = index
        self.segment_id = segment_id
        self.segment_shot_id = segment_shot_id
        self.time = (hr, min, sec, ms)
        self.global_shot_id = global_shot_id
        self.path = ""
        self.has_subsegment = has_subsegment
        self.subsegment = subsegment




    def print_shot(self, no_print = False):

        if not no_print:
            print self.filemaker_ID, self.movie_name, self.movie_year, self.source_type, self.shot_id, [self.segment_id, self.segment_shot_id,self.global_shot_id], self.time, self.path
        else:
            return self.filemaker_ID, self.movie_name, self.movie_year, self.source_type, self.shot_id, [self.segment_id, self.segment_shot_id,self.global_shot_id], self.time, self.path
    def deserialize(self, serialization):
        for a,v in serialization.items():
            setattr(self,a,v)
        return self


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
        for s in self.shots:
            if s.segment_id == -1 or s.segment_shot_id == -1:
                self.needs_segmentation = True
                # print [s.segment_id, s.segment_shot_id], s.path
                break




    def print_movie(self):
        print self.filemaker_ID, self.movie_name, self.elan_path, self.segmentation_path, len(self.shots)

    def get_elan_path(self):
        if len(self.elan_path) > 0:
            return self.elan_path[0]
        else:
            return None


class FiwiFetcher():
    def __init__(self, directories):
        self.directories = directories

    def fetch(self):
        movie_directories = []
        movies_without_screenshots_folder = []

        for root in self.directories:
            movie_directories.extend(glob.glob(root + "/" + "*" + "/"))

        print "######FETCHER######"
        print "Total Directories Found:", len(movie_directories)

        edited = []
        for m in movie_directories:
            files_in_dir = glob.glob(m + "\\*")
            contains_only_directories = True

            # Removing Empty Folders
            if len(files_in_dir) > 0:
                for f in files_in_dir:
                    if os.path.isfile(f):
                        contains_only_directories = False

                # If the Movie contains several Items
                if contains_only_directories:
                    for f in files_in_dir:
                        edited.append(f + "\\")

                else:
                    edited.append(m)
                    print m

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
                    print m

        movie_directories = edited


        print len(edited), len(movies_without_screenshots_folder)
        with open("results/Movies_Without_SCR.txt", "w") as f:
            for l in movies_without_screenshots_folder:
                f.write(l + "\n")

        with open("results/Movies_with_SCR.txt", "w") as f:
            for l in movie_directories:
                f.write(l + "\n")


    def fetch_shots(self):
        movie_directories = []
        with open("results/Movies_with_SCR.txt", "r") as f:
            for l in f:
                movie_directories.append(l.replace("\n", ""))

        shot_dirs = []
        shots = []
        print "ERRORS:"
        for m in movie_directories:
            try:
                files = glob.glob(m + "*\\")
                n = 0
                for f in files:
                    if not "_NOFETCH" in f:
                        if "SCR" in f or "Stills" in f:
                            shot_dirs.append(f +"\\")
                            n += 1

                if n == 0 or n > 1:
                    print m, "\t" ,n

            except TypeError as e:
                print e.message
                print e.args
                print m

        print "FETCHING SHOTS"
        for i, s in enumerate(shot_dirs):
            console.write("\r" + str(round(float(i)/len(shot_dirs)*100, 2)))
            shots.extend(glob.glob(s + "*"))

        print "GENERATING RESULT"
        with open("results/All_Shots.txt", "w") as f:
            for s in shots:
                name = s.split("\\").pop()
                path = s
                f.write(name + "\t" + path + "\n")


class FiwiParser():
    def __init__(self,file_path):
        self.store_paths = True
        self.lines = []
        self.indices = []
        self.errors = []
        self.error_indices = []
        self.results = []
        self.total_lines = 0
        self.paths = []
        self.debug = False
        with open(file_path, "r") as f:
            lines = []
            indices1 = []
            indices2 = []
            paths = []
            for i, line in enumerate(f):
                line = line.replace("\\", "/")
                line = line.split("\t")

                lines.append(line[0])
                paths.append(line[1].replace("\n", ""))
                indices1.append(i)
                indices2.append(i)
                if self.debug:
                    if i > 1000:
                        break

            self.lines = [lines, indices1]
            self.paths = [paths, indices2]


        self.total_lines = len(self.lines[0])


    def parse(self):
        result = []
        errors = []
        time_pattern = re.compile("\d\d")

        # Cleanup
        cleaned = []
        to_remove = []
        duplicates = []

        custom_first_two = []
        custom_last_two = []
        seconds_scr = []
        no_scr_counter = []
        print "CLEANUP"
        last = "-1"
        last_year_error = "-1"

        for idx, l in enumerate(self.lines[0]):
            if idx % 1000 == 0:
                console.write("\r" + str(round(float(idx) / float(self.total_lines) * 100,2)))
                console.flush()

            do_remove = False
            error = ""
            line_index = self.lines[1][idx]
            l = l.replace("\n", "")
            l = l.replace("-", "_")
            l = l.replace("_BL", "")
            l = l.replace("_s", "_")
            l = l.replace(".", "_")
            l = l.replace("__", "_")
            l = l.replace("SCR00", "SCR_00")
            items = l.split("_")
            l = self.recombine(items)


            if l[0] == "s":
                l = l[1:]

            if "3380_1_1_BalletDesSylphides_1902_DVD_SCR_3380_1_1_BalletDesSylphides_1902_DVD_SCR_" in l:
                l = l.replace("SCR_3380_1_1_BalletDesSylphides_1902_DVD_SCR_", "SCR_")


            if "LassieComeHome" in l and "BeckySharp" in l:
                l = l.replace("63_1_2_BeckySharp_1935_DVD_SCR_", "")


            if "HallucinationsPerceptionetlImaginaire_1964_" in l:
                l = l.replace("1964_", "1964_DVD_SCR_")
                l = l.replace("128", "128_1_1")

            if "Der_Golem" in l:
                l = l.replace("Der_Golem", "DerGolem")

            if "_Imitation" in l:
                l = l.replace("_Imitation", "")

            if "_imitation" in l:
                l = l.replace("_imitation", "")

            if "FeuMathiasPascal" in l:
                l = self.swap_first_two_to_last(l)

            if "UnaGiornataParticolare" in l:
                l = self.swap_first_two_to_last(l)

            if "Wojna_Swjatow" in l:
                l = l.replace("Wojna_Swjatow", "WojnaSwjatow")

            if "1880_1_1_SilenceLambs" in l:
                l = l.replace("1880_1_1_SilenceLambs", "_1880_1_1_SilenceLambs")
                l = l.replace("__1880_1_1_SilenceLambs_1980_SCR", "")
                l = self.swap_first_two_to_last(l)

            if "350_1_1_Nerven_1919_SCR" in l:
                l = l.replace("350_1_1_Nerven_1919_SCR", "_350_1_1_Nerven_1919_SCR")
                l = l.split("_350_1_1_Nerven_1919_SCR")
                l = "350_1_1_Nerven_1919_SCR_" + l[0]

            if "291_1_1_Spartacus_1960_SCR" in l:
                l = l.replace("_291_1_1_Spartacus_1960_SCR", "_291_1_1_Spartacus_1960_SCR")
                l = l.split("_291_1_1_Spartacus_1960_SCR")
                l = "291_1_1_Spartacus_1960_SCR_" + l[0]

            if "212_SoloSunny" in l:
                l = l.replace("212_SoloSunny", "212_1_1_SoloSunny")

            if "315_PlayTime" in l:
                l = l.replace("315_PlayTime", "315_1_1_PlayTime")

            if "3382_The_Dragon_Painter" in l:
                l = l.replace("3382_The_Dragon_Painter", "3382_1_1_TheDragonPainter")

            if "3399_AmourDesclave" in l:
                l = l.replace("3399_AmourDesclave", "3399_1_1_AmourDesclave")

            if "Gribiche_1926" in l:
                l = self.swap_first_two_to_last(l)

            if "TheBlueLangoon" in l:
                l = self.swap_first_two_to_last(l)

            if "_crop" in l:
                do_remove = True
                error = "Unknown Identifier"

            if "_org" in l:
                do_remove = True
                error = "Unknown Identifier"

            if "_jpg" in l:
                do_remove = True
                error = "Unknown Identifier"

            if "_bmp" in l:
                do_remove = True
                error = "Unknown Identifier"

            if "_JohnnyGuitar_1954" in l:
                do_remove = False
                error = "Weird Nomenclature"
                seconds_scr.append([l, line_index])

            if "TheThiefOfBagdad1924" in l:
                l = l.replace("TheThiefOfBagdad1924", "TheThiefOfBagdad_1924")

            if "SCR" not in l:
                path = ""

                if "DVD" in l or "Bluray" in l:
                    if "DVD" in l:
                        idx = l.index("DVD")
                        l = self.insert_string(l, idx + 4, "SCR_")

                    elif "Bluray" in l:
                        idx = l.index("Bluray")
                        l = self.insert_string(l, idx + 4, "SCR_")

                    else:
                        do_remove = True
                        error = "NO SCR, DVD or BLURAY"
                        no_scr_counter.append((l, path))

                else:

                    path = self.get_path(line_index)
                    path = path.split("/")
                    path = path[len(path) - 2]
                    path = path.replace("_SCR_", "_")
                    path = path.replace("DIASTOR_Restoration", "DIASTOR")
                    path = path.replace("DIASTORRestoration", "DIASTOR")
                    path = path.replace("BD", "Bluray")
                    path = path.replace("_SCR", "")
                    path = path.replace("_DVD Stills", "_DVD_Stills")
                    path = path.replace("_STILLS_", "_")
                    path = path.replace("_STILLS_", "_")
                    path = path.replace("_STILLS", "")
                    path = path.replace("_Stills_", "_")
                    path = path.replace("_Stills", "")
                    path = path.replace("_BF", "")
                    path = path.replace("The Lodger", "TheLodger")
                    path = path.replace("_uncropped_", "")



                    test_seq = path.split("_")
                    if "DVD" in test_seq:
                        if test_seq.index("DVD") != len(test_seq)-1:
                            pass
                            #print test_seq.index("DVD"), len(test_seq) - 1, path

                    elif "Bluray" in test_seq:
                        if test_seq.index("Bluray") != len(test_seq)-1:
                            pass
                            # print test_seq.index("Bluray"), len(test_seq) - 1, path

                    else:
                        if "LesPapillonsJaponais" in path:
                            path += "_DVD"
                        elif "ImitationOfLife" in path:
                            path += "_DVD"
                        else:
                            pass

                # Connecting the Information gathered from the Folder with the ones from the File
                if path is not "":
                    l = path + "_SCR_" + l


            else:
                n_scr = 0
                for itm in l.split("_"):
                    if "SCR" in itm:
                        n_scr += 1
                if n_scr > 1:
                    do_remove = True
                    error = "Duplicated Name"


            if do_remove:
                to_remove.append([l, line_index, error])


            try:
                year = int(l.split("_")[4])

            except ValueError as e:
                if l.split("_")[0] != last_year_error:

                    path = self.get_path(line_index)


                    path = path.split("/")[len(path.split("/"))-2]
                    path = path.replace("_SCR_", "_")
                    path = path.replace("DIASTOR_Restoration", "DIASTOR")
                    path = path.replace("BD", "Bluray")
                    path = path.replace("_SCR", "")

                    path = path.replace("_DVD Stills", "_DVD_Stills")
                    path = path.replace("_STILLS_", "_")
                    path = path.replace("_STILLS_", "_")
                    path = path.replace("_STILLS", "")
                    path = path.replace("_Stills_", "_")
                    path = path.replace("_Stills", "")
                    path = path.replace("_BF", "")
                    path = path.replace("The Lodger", "TheLodger")
                    path = path.replace("_uncropped_", "")
                    path = path.replace("_DVD_", "")
                    path = path.replace("_SCR_", "")
                    path = path.replace("_DVD", "")
                    path = path.replace("_SCR", "")
                    path = path.replace("ITreVoltiDellaPaura", "ITreVoltiDellaPaura_1963")


                    to_insert_year = path.split("_").pop()
                    splitted = l.split("_")
                    splitted.insert(4, to_insert_year)
                    l = splitted[0]

                    for split in splitted[1:]:
                        l += "_" + split
                    last_year_error = l.split("_")[0]

            if last not in l:
                result.append(l)
            last = l.split("_")[0]

            cleaned.append(l)

        # result.sort(key=lambda x: int(x.split("_")[0]))
        # for r in result:
        #     dtr = r.split("_")
        #     string = dtr[0].rjust(5) + dtr[1].rjust(3) + dtr[2].rjust(3) + dtr[3].rjust(50)
        #     for dt in range(4, len(dtr), 1):
        #         string += dtr[dt].rjust(10) + "\t"
        #     print string


        print "Missing SCR", len(no_scr_counter)
        for sqr in no_scr_counter:
            print sqr

        self.lines = [cleaned, self.lines[1]]
        lst = []
        lst_e = []
        print "Length before Cleaning:", len(self.lines[0])

        for l in to_remove:
            lst.append(l[1])
            lst_e.append(l[2])

        self.to_error_index(lst, lst_e)
        print "Length after Cleaning:", len(self.lines[0])


        # Parsing
        if not self.debug:
            print "Parsing Seconds Symbols", len(seconds_scr[0])
            self.print_remaining()
            for i, l in enumerate(seconds_scr):

                res = self.parse_seconds(l[0], l[1])

                if res is not None:
                    self.to_results(res)

        n0 = self.get_all_with_n_after(self.lines, "_SCR", 0)
        self.to_error_index(n0[1])


        n1 = self.get_all_with_n_after(self.lines, "_SCR_", 1)
        self.to_error_index(n1[1])

        n2 = self.get_all_with_n_after(self.lines,"_SCR_", 2)

        n3 = self.get_all_with_n_after(self.lines, "_SCR_", 3)

        n4 = self.get_all_with_n_after(self.lines, "_SCR_", 4)
        n5 = self.get_all_with_n_after(self.lines, "_SCR_", 5)
        n6 = self.get_all_with_n_after(self.lines, "_SCR_", 6)

        # self.print_all(n4)

        n7 = self.get_all_with_n_after(self.lines, "_SCR_", 7)
        self.to_error_index(n7[1])

        n_not = self.get_containing(self.lines, "SCR",inverse=True)

        lists = [n0, n2, n3, n4, n5, n6, n_not]
        test_list_a=[]
        test_list_b=[]
        for itm in lists:
            test_list_a.extend(itm[0])
            test_list_b.extend(itm[0])

        self.get_result_ratio([test_list_a, test_list_b], self.lines)

        self.print_remaining()

        print "Parsing Two Symbols", len(n2[0])
        self.print_remaining()
        for i, l in enumerate(n2[0]):
            res = self.parse_two_fields(l, n2[1][i])
            if res is not None:
                self.to_results(res)

        print "Parsing Three Symbols", len(n3[0])
        self.print_remaining()
        for i, l in enumerate(n3[0]):
            res = self.parse_three_fields(l, n3[1][i])
            if res is not None:
                self.to_results(res)

        print "Parsing Four Symbols", len(n4[0])
        self.print_remaining()
        for i, l in enumerate(n4[0]):
            res = self.parse_four_fields(l, n4[1][i])
            if res is not None:
                self.to_results(res)

        print "Parsing Five Symbols", len(n5[0])
        self.print_remaining()
        for i, l in enumerate(n5[0]):
            res = self.parse_five_fields(l, n5[1][i])
            if res is not None:
                self.to_results(res)

        print "Parsing Six Symbols", len(n6[0])
        self.print_remaining()
        for i, l in enumerate(n6[0]):
            res = self.parse_six_fields(l, n6[1][i])
            if res is not None:
                self.to_results(res)

        self.print_remaining()

        print "Parsing No SCR Symbol", len(n6[0])
        self.print_remaining()
        counter = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        for i, l in enumerate(n_not[0]):
            item_length = len(l.split("_"))
            line_index = n_not[1][i]
            shot = None
            if item_length == 1:
                counter[0] += 1
                self.to_error_index(line_index)
            elif item_length == 2:
                counter[1] += 1
                shot = self.parse_two_fields(l, line_index, False)
            elif item_length == 3:
                counter[2] += 1
                self.to_error_index(line_index)
            elif item_length == 4:
                counter[3] += 1
                shot = self.parse_four_fields(l, line_index, False)
            elif item_length == 5:
                counter[4] += 1
                shot = self.parse_five_fields(l, line_index, False)
            elif item_length == 6:
                counter[5] += 1
                self.to_error_index(line_index)
            else:
                self.to_error_index(line_index)
                counter[6] += 1

            if shot is not None:
                self.to_results(shot)
        print "RESULT: No SCR Symbol", counter


        self.print_remaining()
        self.print_all(self.lines)
        self.to_error_index(self.lines[1])
        self.save_error_list()
        self.store_shots(self.results)

        #
        #
        # self.get_result_ratio(result, self.lines[0])
        #self.print_errors()



    #region HELPERS
    def store_shots(self, shot_list):
        to_save = []
        for s in shot_list:
            to_save.append(s.__dict__)
        try:
            with open("results/SHOTS_OBJ_PICKLE.pkl", 'wb') as f:
                pickle.dump(shot_list, f, pickle.HIGHEST_PROTOCOL)

            with open("results/SHOTS_OBJECTS.json", 'w') as f:
                json.dump(to_save, f)
        except Exception as e:
            raise e



    def sec_to_string(self, sec):
        sec = int(sec)
        seconds = sec % 60
        minutes = (sec / 60) % 60
        hours = (sec / (60 * 60)) % 24

        return [hours, minutes, seconds]

    def swap_first_two_to_last(self, l):
        split_ext = l.split(".")
        splitted = split_ext[0].split("_")
        res = ""
        for i in range(2, len(splitted)):
            res += splitted[i] + "_"
        res += splitted[0] + "_"
        res += splitted[1] + "." + split_ext[1]
        l = res
        return l

    def get_path(self, index):
        idx = self.paths[1].index(index)
        return self.paths[0][idx]

    def insert_string(self, string, index, to_insert):
        return string[:index] + to_insert + string[index:]

    def recombine(self, items):
        l = ""
        for idx, i in enumerate(items):
            if idx == 0:
                l = i
            elif idx < len(items) - 1:
                l += "_" + i
            else:
                l += "." + i
        return l

    def print_containing(self, line, containing):
            if containing in line:
                print line

    def print_remaining(self):
        print "REMAINING:", len(self.lines[0])

    def get_containing(self, lines, containing, inverse = False):
        result = []
        indices = []
        for i, l in enumerate(lines[0]):
            if not inverse:
                if containing in l:
                    result.append(l)
                    indices.append(lines[1][i])
            else:
                if not containing in l:
                    result.append(l)
                    indices.append(lines[1][i])
        return [result, indices]

    def get_result_ratio(self, input, lines):
        print len(input[0]), "/", len(lines[0])
        print float(len(input[0])) / len(lines[0]) * 100, "%"

    def print_all(self, to_print):
        for i, l in enumerate(to_print[0]):
            print l, to_print[1][i]
        print "LENGTH: ", len(to_print)

    def get_all_with_n_after(self,lines, split_str, n):
        result = []
        result_indices = []
        for i, l in enumerate(lines[0]):
            if split_str in l:
                if n == 0:
                    ld = l.split(".")
                    if split_str in ld[0][len(ld[0])-len(split_str):]:
                        result.append(l)
                        result_indices.append(lines[1][i])
                else:
                    ld = l.split(split_str)[1]
                    if len(ld.split("_")) == n:
                        result.append(l)
                        result_indices.append(lines[1][i])

        return [result,result_indices]

    def get_with_n_items(self, lines, n, s = "_"):
        result = []
        for l in lines:
            if len(l.split(s)) == n:
                result.append(l)
        return result

    def to_error_index(self, indices, Error = "Unknown Nomenclature"):

        if not isinstance(indices, list):
            indices = [indices]

        if not isinstance(Error, list):
            Error = [Error]

            if len(Error) != len(indices):
                Error = [Error][0] * len(indices)


        for err_index, i in enumerate(indices):
            try:

                idx = self.lines[1].index(i)
                name = self.lines[0].pop(idx)
                index = self.lines[1].pop(idx)

                path = self.get_path(i)
                self.errors.append([name, index, path, Error[err_index]])
                self.error_indices.append(index)

            except ValueError as e:
               if i in self.error_indices:
                   print "Already Removed"
               else :
                   raise e

    def to_error(self, items):
        for idx, itm in enumerate(self.lines[0]):
            if itm in items:
                name = self.lines[0].pop(idx)
                index = self.lines[1].pop(idx)
                self.errors.append([name, index])
                self.error_indices.append(index)

    def print_errors(self):
        print "********ERRORS*********"
        for e in self.errors:
            print e

    def save_error_list(self):

        summary_names = []
        summary_errors = []
        for e in self.errors:
            path = e[2].split("/")
            path.pop()
            r_path = ""
            for p in path:
                r_path += p + "/"
            if r_path not in summary_names:
                summary_names.append(r_path)
                summary_errors.append(e[3])




        with open("error_list.txt", "w") as file:
            file.write("********************HEADER*****************\n")
            file.write("*******************Summary*****************\n")
            file.write(" Total Files:\t" + str(self.total_lines ) + "\n")
            file.write("Total Errors:\t" + str(len(self.errors)) + "\n")
            file.write("Success Rate:\t" + str(round((1.0 - float(len(self.errors)) / self.total_lines) * 100,2))+ "%\n")
            file.write("****************Error Files****************\n")
            file.write("********************UNIX*******************\n")
            for i, s in enumerate(summary_names):
                file.write(summary_errors[i].ljust(25) + s + "\n")
            file.write("\n\n")

            file.write("*******************Windows*****************\n")
            for i, s in enumerate(summary_names):
                file.write(summary_errors[i].ljust(25) + s.replace("/", "\\") + "\n")
            file.write("\n\n")

        with open("error_list_details.txt", "w") as file:
            file.write("****************Details****************\n")
            for e in self.errors:
                file.write(e[3] + "\t" + e[0]+ "\t in \t" +e[2]+ "\n")

    def to_results(self, result):
        res_id = result.shot_id
        idx = self.lines[1].index(res_id)
        name = self.lines[0].pop(idx)
        index = self.lines[1].pop(idx)

        if self.store_paths:
            result.path = self.get_path(res_id)
        self.results.append(result)
    # endregion

    #region Parsers

    def parse_movie_info(self, line, shot):
        info = line.split("_")
        shot.filemaker_ID = (int(info[0]), int(info[1]), int(info[2]))
        shot.movie_name = info[3]
        shot.movie_year = info[4]
        shot.source_type = info[5]

    def parse_seconds(self, line, index):
        try:
            l = line
            segment_info = l.split("_")
            segment_id = segment_info[7].split(".")[0]
            seconds = segment_info[6]
            timestamp = self.sec_to_string(seconds)


            shot = Shot(segment_id, index, hr=timestamp[0], min=timestamp[1],sec=timestamp[2])
            self.parse_movie_info(line, shot)
            return shot

        except:
            self.to_error_index(index, "Parsing Failed")
            return None

    def parse_custom_segmid(self, line, index, sgmid_index, segm_id_shot_index):
        try:
            l = line
            segment_info = l.split("_")

            segment_id = int(re.sub("[^0-9]", "", segment_info[sgmid_index]))
            segment_shot_id = int(re.sub("[^0-9]", "",segment_info[segm_id_shot_index].split(".")[0]))
            shot = Shot(segment_id, index, segment_shot_id)
            self.parse_movie_info(line, shot)
            return shot

        except:
            self.to_error_index(index, "Parsing Failed")
            return None

    def parse_two_fields(self, line, index, do_split = True):
        try:
            if do_split:
                l = line.split("_SCR_")
                segment_info = l[1].split("_")
            else:
                l = line
                segment_info = l.split("_")

            segment_id = int(re.sub("[^0-9]", "", segment_info[0]))
            segment_shot_id = int(re.sub("[^0-9]", "",segment_info[1].split(".")[0]))
            shot = Shot(segment_id, index, segment_shot_id)
            self.parse_movie_info(line, shot)
            return shot

        except:
            self.to_error_index(index, "Parsing Failed")
            return None

    def parse_three_fields(self, line, index, do_split = True):
        try:
            if do_split:
                l = line.split("_SCR_")
                segment_info = l[1].split("_")
            else:
                l = line
                segment_info = l.split("_")

            time_hour = int(re.sub("[^0-9]", "", segment_info[0]))
            time_minutes = int(re.sub("[^0-9]", "", segment_info[1]))
            time_seconds = int(re.sub("[^0-9]", "", segment_info[2].split(".")[0]))
            shot = Shot(-1, index, hr=time_hour,min=time_minutes, sec=time_seconds)
            self.parse_movie_info(line, shot)
            error = self.error_check(shot, line)

            if not error:
                return shot
            else:
                raise RuntimeError("Error in Timestamp")
        except Exception as e:
            print e.message
            self.to_error_index(index, "Parsing Failed")
            if not (isinstance(e, RuntimeError) or isinstance(e, ValueError)):
                raise e

    def parse_four_fields(self, line, index, do_split = True):
        try:
            first_is_segment_id = False

            if do_split:
                l = line.split("_SCR_")
                segment_info = l[1].split("_")
            else:
                l = line
                segment_info = l.split("_")
            segment_id = segment_info[0]

            if "S" in segment_id:
                segment_id = segment_id.replace("S", "")
                first_is_segment_id = True

            if len(segment_id) == 3:
                first_is_segment_id = True

            if len(segment_id) == 4:
                first_is_segment_id = True

            if first_is_segment_id:
                segment_id = int(re.sub("[^0-9]", "", segment_info[0]))
                time_hour = int(re.sub("[^0-9]", "", segment_info[1]))
                time_minutes = int(re.sub("[^0-9]", "", segment_info[2]))
                time_seconds = int(re.sub("[^0-9]", "", segment_info[3].split(".")[0]))

                shot = Shot(segment_id, index, hr=time_hour, min=time_minutes, sec=time_seconds)

            else:
                time_hour = int(re.sub("[^0-9]", "", segment_info[0]))
                time_minutes = int(re.sub("[^0-9]", "", segment_info[1]))
                time_seconds = int(re.sub("[^0-9]", "", segment_info[2]))
                time_ms = int(re.sub("[^0-9]", "", segment_info[3].split(".")[0]))

                shot = Shot(-1, index, hr=time_hour,min=time_minutes, sec=time_seconds, ms=time_ms)

            error = self.error_check(shot, line)

            if not error:
                self.parse_movie_info(line, shot)
                return shot
            else:
                raise RuntimeError("Error in Timestamp")
        except Exception as e:
            print e.message
            self.to_error_index(index, "Parsing Failed")
            if not (isinstance(e, RuntimeError) or isinstance(e, ValueError)):
                print l
                raise e

    def parse_five_fields(self, line, index, do_split = True):
        try:
            if do_split:
                l = line.split("_SCR_")
                segment_info = l[1].split("_")
            else:
                l = line
                segment_info = l.split("_")

            segment_id = int(re.sub("[^0-9]", "", segment_info[0]))
            time_hour = int(re.sub("[^0-9]", "", segment_info[1]))
            time_minutes = int(re.sub("[^0-9]", "", segment_info[2]))
            time_seconds = int(re.sub("[^0-9]", "", segment_info[3]))
            time_ms = int(re.sub("[^0-9]", "", segment_info[4].split(".")[0]))
            #TODO contains comma error
            # print line, segment_id,  time_hour, time_minutes, time_seconds, time_ms

            shot = Shot(segment_id, index, hr=time_hour,min=time_minutes, sec=time_seconds, ms=time_ms)
            error = self.error_check(shot, line)

            if not error:
                self.parse_movie_info(line, shot)
                return shot
            else:
                raise RuntimeError("Error in Timestamp")
        except Exception as e:
            print e.message
            self.to_error_index(index, "Parsing Failed")
            if not (isinstance(e, RuntimeError) or isinstance(e, ValueError)):
                raise e

    def parse_six_fields(self, line, index, do_split = True):
        try:
            if do_split:
                l = line.split("_SCR_")
                segment_info = l[1].split("_")
            else:
                l = line
                segment_info = l.split("_")

            segment_id = int(re.sub("[^0-9]", "", segment_info[0]))
            time_hour = int(re.sub("[^0-9]", "", segment_info[1]))
            time_minutes = int(re.sub("[^0-9]", "", segment_info[2]))
            time_seconds = int(re.sub("[^0-9]", "", segment_info[3]))
            time_ms = int(re.sub("[^0-9]", "", segment_info[4]))
            global_shot_id = int(re.sub("[^0-9]", "", segment_info[5].split(".")[0]))
            #TODO contains comma error
            # print line, segment_id,  time_hour, time_minutes, time_seconds, time_ms
            shot = Shot(segment_id, index, hr=time_hour,min=time_minutes, sec=time_seconds, ms=time_ms, global_shot_id=global_shot_id)
            error = self.error_check(shot, line)
            if not error:
                self.parse_movie_info(line, shot)
                return shot
            else:
                raise RuntimeError("Error in Timestamp")
        except Exception as e:
            print e.message
            if not (isinstance(e, RuntimeError) or isinstance(e, ValueError)):
                raise e
            self.to_error_index(index, "Parsing Failed")

    def error_check(self, shot, line = None):
        error = False

        if shot.time[0] > 10:
            error = True
        if shot.time[1] > 60:
            error = True
        if shot.time[2] > 60:
            error = True
        if shot.time[3] > 1000:
            error = True

        return error
    pass
    #endregion


class FiwiCopy():
    def __init__(self, path = "results/SHOTS_OBJ_PICKLE.pkl"):

        # with open(path, 'r') as f:
        #     dicts = json.load(f)
        with open(path, "rb") as f:
            self.shots = pickle.load(f)

        self.movies = []
        self.shots.sort(key=lambda x: x.filemaker_ID[0], reverse=False)

        print "Number of Shots", len(self.shots)


    def create_movies(self):
        last_movie_id = [0,0,0]
        last_shot = None
        movies = []
        curr_shots = []
        total_SCR = 0
        for s in self.shots:
            curr_movie_id = s.filemaker_ID

            if curr_movie_id != last_movie_id:
                if last_shot is not None:

                    movie_id = last_movie_id
                    movie_name = last_shot.movie_name
                    movie_path = last_shot.path.replace(last_shot.path.split("/").pop(), "")
                    movie_path = movie_path.replace(last_shot.path.split("/")[len(last_shot.path.split("/")) -2] + "/", "")


                    dir_files = glob.glob(movie_path + "*")
                    elan_path = []
                    segmentation_path = []
                    for d in dir_files:
                        if ".eaf" in d and not ".eaf.001" in d:
                            elan_path.append(d)
                        elif ".txt" in d:
                            segmentation_path.append(d)

                    if len(elan_path) == 0:
                        dir_files = glob.glob(movie_path + "/*Projektdatei/*.eaf")
                        if len(dir_files) > 0:
                            elan_path = [dir_files[0]]

                        else:
                            elan_path = []
                            print "NO ELAN", movie_path

                    if len(segmentation_path) == 0:
                        segmentation_path = []

                    # curr_shots = []
                    total_SCR += len(curr_shots)
                    movie = Movie(movie_id, movie_name, curr_shots, movie_path, elan_path, segmentation_path)
                    # print movie.movie_name, len(movie.shots), movie.needs_segmentation
                    movies.append(movie)
                    curr_shots = []
            else:
                curr_shots.append(s)
                last_shot = s

            last_movie_id = curr_movie_id

        print "Unclear ELAN PATH"
        for m in movies:
            if m.elan_path is None:
                files = glob.glob(m.folder_path + "*")
                has_elan = False
                for f in files:
                    if "Projektdatei" in f:
                        # print m.movie_name, True, f
                        has_elan = True
                if has_elan is False:
                    m.print_movie()
                    print m.folder_path



                # m.print_movie()

        to_segment = 0
        for m in movies:
            if m.needs_segmentation:
                to_segment += 1

        print "TOTAL MOVIES:", len(movies)
        print "TOTAL SHOTS: ", total_SCR
        print "MISSING SEGM:", to_segment

        self.movies = movies


    def check_segmentation(self):
        errors = []
        for m in self.movies:

            if m.needs_segmentation:
                print m.movie_name, m.filemaker_ID
                movie_path, segmentations = ELANProjectImporter().elan_project_importer(m.get_elan_path())
                for s in m.shots:
                    if s.segment_id == -1:
                        ms_pos = s.time[0] * long(60*60*1000) + s.time[1] * long(60 * 1000) + s.time[2] * 1000 + s.time[3]

                        segm_id = -1
                        last_ms = -1000
                        for i, segm in enumerate(segmentations[0][1]):
                            last_ms = segm[2]
                            if segm[1] <= ms_pos <= segm[2]:
                                segm_id = i +1
                                break

                        if segm_id != -1:
                            s.segment_id = segm_id
                        else:
                            errors.append(s)
                            m.shots.remove(s)
                            print "ERROR", s.time, [ms_pos, last_ms], s.segment_id, s.segment_shot_id, s.path


                m.shots.sort(key=lambda s:s.time[0] * long(60*60*1000) + s.time[1] * long(60 * 1000) + s.time[2] * 1000 + s.time[3])
                curr_segm = 0
                curr_shot_id = 0
                for s in m.shots:
                    if s.segment_id != curr_segm:
                        curr_segm = s.segment_id
                        curr_shot_id = 1

                    s.segment_shot_id = curr_shot_id

                    curr_shot_id += 1

        with open("ErrorFile_Copier.txt", "w") as f:
            for e in errors:
                string = str(e.filemaker_ID) + "\t" + str(e.path)
                f.write(string)

    def store_movies(self):
        with open("results/Movies_OBJ_PICKLE.pkl", 'wb') as f:
            pickle.dump(self.movies, f, pickle.HIGHEST_PROTOCOL)

    def copy_screenshots(self, root_directory = "//130.60.131.134/studi/Filme/FIWI/", load_movies = False, quality = 100):

        if load_movies:
            with open("results/Movies_OBJ_PICKLE.pkl", "rb") as f:
                movies = pickle.load(f)
        else:
            movies = self.movies

        for i,m in enumerate(movies):
            if i == 1:
                return


            filemaker_ID_string = str(m.filemaker_ID[0]) +"_" +str(m.filemaker_ID[1]) +"_" +str(m.filemaker_ID[2])
            movie_directory = root_directory + filemaker_ID_string
            if not os.path.isdir(movie_directory):
                os.mkdir(movie_directory)

            for j, s in enumerate(m.shots):
                console.write("\r" + str(round(float(j) / len(m.shots) * 100, 2)))
                path = s.path
                img = cv2.imread(path)

                if img.shape[0] > 576:
                    dx = 579.0 / img.shape[0]
                    img = cv2.resize(img, None, None,dx,dx,cv2.INTER_CUBIC)

                filename = str(s.segment_id) +"_" + str(s.segment_shot_id) +"_" + filemaker_ID_string + ".jpg"
                cv2.imwrite(movie_directory + "/" + filename, img, [cv2.IMWRITE_JPEG_QUALITY, quality])



            # print "MOVIE: ", m.movie_name, m.filemaker_ID



if __name__ == '__main__':
    root_directory_1 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\")
    root_directory_2 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\mittlere_Filme\\")
    root_directory_3 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\spaete_Filme\\")
    source_dir = [root_directory_1, root_directory_2, root_directory_3]

    # fetcher = FiwiFetcher(source_dir)
    # fetcher.fetch()
    # fetcher.fetch_shots()
    # parser = FiwiParser("results/All_Shots.txt")
    # parser.parse()

    copier = FiwiCopy()
    # copier.create_movies()
    # copier.check_segmentation()
    # copier.store_movies()
    copier.copy_screenshots(load_movies=True)
