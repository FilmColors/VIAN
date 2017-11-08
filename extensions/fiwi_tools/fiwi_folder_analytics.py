import os
import json
import glob
import sys

class FiwiDirectoryAnalyser():
    def __init__(self, root):
        self.root_directory = root
        self.n_dir = 0
        self.results = []
        self.file_extensions = []
        self.file_information = []
        self.total = []
        self.movie_formats = [".mov", ".mp4", ".mkv", ".m4v"]
        self.other_nomenclatures_lengths = []
        self.other_nomenclatures = []
        self.all_shots = []
        self.all_shots_path = []
        
        self.header = ""
        self.details = ""

    def add_to_others(self, length, nomenclature):
        if length in self.other_nomenclatures_lengths:
            self.other_nomenclatures[self.other_nomenclatures_lengths.index(length)].append(nomenclature)
        else:
            self.other_nomenclatures.append([nomenclature])
            self.other_nomenclatures_lengths.append(length)


    def print_result(self):
        spacing = 15
        self.header = ""
        self.header += ( "\n")
        self.header += ( "************************Result***************************\n")
        self.header += ( "Directory:".ljust(spacing)+ str(self.root_directory) + "\n")
        self.header += ( "Total Folders:".ljust(spacing)+ str(self.n_dir)+ "\n\n\n")

        self.header += ( "*******************File Information**********************"+ "\n")
        self.header += ("n-Correct".ljust(spacing) +
                        "n-Multiple".ljust(spacing) +
                        "n-Incorrect".ljust(spacing)+
                        "n-Not-Started".ljust(spacing) +
                        "n-Total".ljust(spacing) +
                        "\n")
        self.header += (str(self.total[9]).ljust(spacing) +
                        str(self.total[10]).ljust(spacing) +
                        str(self.total[11]).ljust(spacing) +
                        str(self.total[13]).ljust(spacing) +
                        str(self.total[0]).ljust(spacing) +
                        "\n\n\n")

        self.header += ("************************Details***************************" + "\n")
        self.header += ("Legend" + "\n" +
                        "PR: Pre-Naming Nomeclature\n" +
                        "MS: Missing Segmentation\n" +
                        "AL: Everything OK" + "\n\n\n"
                        )
        self.header += ("Status".rjust(spacing) +
                        "n-Movies".rjust(spacing) +
                        "n-ELAN".rjust(spacing) +
                        "n-Filemaker".rjust(spacing) +
                        "n-Segment.".rjust(spacing) +
                        "n-Folders".rjust(spacing) +
                        "n-Indexing".rjust(spacing) +
                        "n-Timestamp".rjust(spacing) +
                        "n-PreNaming".rjust(spacing) +
                        "n-Others".rjust(spacing) +
                        "".rjust(spacing) +
                        "Path".ljust(5) + "\n")

        for info in self.file_information:
            self.header += (str(info[10]).rjust(spacing) +
                            str(info[9]).rjust(spacing) +
                            str(info[1]).rjust(spacing) +
                            str(info[2]).rjust(spacing) +
                            str(info[8]).rjust(spacing) +
                            str(info[7]).rjust(spacing) +
                            str(info[3]).rjust(spacing) +
                            str(info[4]).rjust(spacing) +
                            str(info[11]).rjust(spacing) +
                            str(info[5]).rjust(spacing) +
                            "".rjust(spacing) +
                            str(info[0]).ljust(5)+ "\n")

        # [n_total, n_elan_total, n_filemaker_total, n_indexing_total, n_timestamp_total,
        #  n_other_total, n_folders_total, n_textfiles_total, n_movies_total, n_correct,
        #  n_multiple, n_incorrect]
        self.header += ("\n\n\n" + "*************************Total***************************" + "\n")
        self.header += ("".rjust(spacing) +
                        "n-Movies".rjust(spacing) +
                        "n-ELAN".rjust(spacing) +
                        "n-Filemaker".rjust(spacing) +
                        "n-Segment.".rjust(spacing) +
                        "n-Folders".rjust(spacing) +
                        "n-Indexing".rjust(spacing) +
                        "n-Timestamp".rjust(spacing) +
                        "n-PreNaming".rjust(spacing) +
                        "n-Others".rjust(spacing) +
                        "".rjust(spacing) +
                        "".ljust(5) + "\n")
        self.header += (
            "Total:" + "".rjust(spacing - len("Total:")) +
            str(self.total[8]).rjust(spacing) +
            str(self.total[1]).rjust(spacing) +
            str(self.total[2]).rjust(spacing) +
            str(self.total[6]).rjust(spacing) +
            str(self.total[7]).rjust(spacing) +
            str(self.total[3]).rjust(spacing) +
            str(self.total[4]).rjust(spacing) +
            str(self.total[12]).rjust(spacing) +
            str(self.total[5]).rjust(spacing) +
            "\n\n\n"
        )


        self.header += ( "**********************File Formats***********************"+ "\n")
        for ext in self.file_extensions:
            self.header += (ext+ "\n")

        self.header += "\n\n\n"

        self.header += ("*************Suspicious Shots Nomenclature****************" + "\n")
        self.header += ("*************************Overview*************************" + "\n")
        self.header += (
            str("Length").rjust(spacing) +
            str("n-Files").rjust(spacing) + "\n"
        )

        for i, length in enumerate(self.other_nomenclatures_lengths):
            self.header += (
                str(length).rjust(spacing) +
                str(len(self.other_nomenclatures[i])).rjust(spacing) + "\n"
            )
        self.header += ("**************************Details*************************\n\n")
        for info in self.file_information:
            if info[5] > 0:
                for f in info[6]:
                    if f[0] == "Other":
                        self.header += (info[6][1][1] + "\n")
                        break
                # self.header += (info[6][1][0].rjust(spacing) +"\t"+ info[6][1][1] + "\n")
        self.header += ("**********************************************************" + "\n")
        self.header += ("**********************************************************" + "\n")
        self.header += ("\n" + "\n")

        self.details += ("*********Suspicious Shots Nomenclature Details************" + "\n")
        for i, length in enumerate(self.other_nomenclatures_lengths):
            self.details += ("*********Length = "+str(length)+"************" + "\n")
            for j in self.other_nomenclatures[i]:
                self.details += j + "\n"

        return self.header, self.details, self.all_shots, self.all_shots_path


    def analyse(self):
        n_total = 0
        n_elan_total = 0
        n_filemaker_total = 0
        n_textfiles_total = 0
        n_movies_total = 0
        n_indexing_total = 0
        n_timestamp_total = 0
        n_pre_naming_total = 0
        n_other_total = 0
        n_folders_total = 0
        
        n_correct = 0
        n_multiple = 0
        n_incorrect = 0
        n_not_started = 0


        counter = 0
        for root in self.root_directory:
            sub_directories = glob.glob(root + "/" + "*" + "/")
            self.n_dir += len(sub_directories)


            for i, d in enumerate(sub_directories):
                counter += 1
                sys.stdout.write ("\r" + str(counter) + "/" + str(self.n_dir))
                curr_dir = os.path.abspath(d)
                n_total += 1

                n_elan =  len(glob.glob(d + "/*.eaf"))
                n_filemaker = len(glob.glob(d + "/*.fmp*"))
                n_folders = len(glob.glob(d + "*/"))
                n_textfiles = len(glob.glob(d + "/*.txt"))
                n_textfiles += len(glob.glob(d + "/*.csv"))
                n_movies = 0
                


                files = glob.glob(d + "/*")
                for f in files:
                    if not os.path.isdir(f):
                        splitted = f.split(".")
                        extension = "." + splitted.pop()
                        if extension in self.movie_formats:
                            n_movies += 1
                        if extension not in self.file_extensions:
                            self.file_extensions.append(extension)


                screenshot_formats = [["Format", "Name", False]]
                consistend_nomenclature = True
                n_indexing = 0
                n_timestamp = 0
                n_pre_naming = 0
                n_other = 0
                dirs = glob.glob(d + "/*/",)
                for s in dirs:
                    if "SCR" in s or "Stills" in s:
                        for scr in glob.glob(s + "*"):
                            file_name = scr.replace("\\", "/").split("/").pop()
                            format_length = len(file_name.split("_"))
                            if format_length >= 2:
                                self.all_shots.append(file_name)
                                path = (s + file_name).replace("\\", "/")
                                self.all_shots_path.append(path)
                                if format_length == 8:
                                    screenshot_formats.append(["Indexing", file_name, False])
                                    n_indexing += 1

                                elif format_length == 12:
                                        screenshot_formats.append(["Timestamp", file_name, False])
                                        n_timestamp += 1
                                elif format_length == 2:
                                        n_pre_naming += 1
                                        screenshot_formats.append(["PreNaming", file_name, False])
                                else:
                                    screenshot_formats.append(["Other", file_name, True])
                                    self.add_to_others(format_length, file_name)
                                    n_other += 1
                                    consistend_nomenclature = False

                n_elan_total += n_elan
                n_filemaker_total += n_filemaker
                n_textfiles_total += n_textfiles
                n_indexing_total += n_indexing
                n_timestamp_total += n_timestamp
                n_other_total += n_other
                n_folders_total += n_folders
                n_movies_total += n_movies
                n_pre_naming_total += n_pre_naming



                # Status Check
                if consistend_nomenclature and n_folders > 0 and n_elan > 0 and n_filemaker > 0 and n_movies > 0:
                    if n_folders > 1 or n_elan > 1 or n_filemaker > 1 or n_textfiles > 1 or n_movies > 1:
                        status = "*Multiple"
                        n_multiple += 1
                    else:
                        status = "OK"
                        if n_textfiles == 0:
                            status += "-MS"
                        if n_pre_naming > 0:
                            status += "-PN"
                        if status == "OK":
                            status += "-AL"
                        n_correct += 1
                else:
                    if n_elan == 0:
                        status = "*Not Started"
                        n_not_started += 1
                    else:
                        status = "***Incorrect"
                        n_incorrect += 1
                
                
                self.file_information.append([curr_dir,n_elan,n_filemaker, n_indexing, n_timestamp, 
                                              n_other, screenshot_formats, n_folders, n_textfiles, n_movies,
                                              status, n_pre_naming])

                
        self.total = [n_total, n_elan_total, n_filemaker_total, n_indexing_total, n_timestamp_total, 
                      n_other_total, n_folders_total, n_textfiles_total, n_movies_total, n_correct, 
                      n_multiple, n_incorrect, n_pre_naming_total, n_not_started]

        return self.print_result()


if __name__ == '__main__':

    root_directory_1 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\frueher_Film\\")
    root_directory_2 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\mittlere_Filme\\")
    root_directory_3 = os.path.abspath("\\\\130.60.131.134\\studi\\Filme\\spaete_Filme\\")
    source_dir = [root_directory_1, root_directory_2, root_directory_3]

    headers = ""
    details = ""
    analyzer = FiwiDirectoryAnalyser(source_dir)
    h, d, a, a_paths = analyzer.analyse()
    headers += h
    details += d

    text_file = open("Analysis_Result.txt", "w")

    text_file.write( "************************Header***************************\n")
    text_file.write(headers)
    text_file.write( "************************Details**************************\n")
    text_file.write(details)

    text_file.close()

    text_file_all_shots = open("Analysis_all_shots.txt", "w")
    for i, p in enumerate(a):
        text_file_all_shots.write(p +"\t"+a_paths[i] + "\n")
    text_file_all_shots.close()


    #
    # text_file = open("Analysis_Result.txt","r")
    # output = open("Analysis_Result2.txt", "w")
    # for l in text_file.readlines():
    #     l.replace("\n", "")
    #     output.write(l.replace("\n", "") + "\n")
    # text_file.close()
    # output.close()
    #
    #
    # res = glob.glob("//130.60.131.134\studi\Filme\spaete_Filme/241_All_That_Heaven_Allows_1955/241_1_1_AllThatHeavenAllows_DVD_Stills/*")

