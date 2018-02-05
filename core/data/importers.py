import csv
import os
import pickle
import glob
import xml.dom.minidom
from xml.dom.minidom import parse

import numpy as np

from core.data.containers import Segment, Segmentation, ElanExtensionProject, IAnalysisJobAnalysis
from core.data.interfaces import IConcurrentJob
from core.analysis.filmcolors_pipeline.filmcolors_pipeline import *


class ELANProjectImporter():
    def __init__(self, main_window, remote_movie = False, import_screenshots = False, movie_formats = None):
        self.main_window = main_window
        self.remote_movie = remote_movie
        self.import_screenshots = import_screenshots
        if movie_formats is None:
            self.movie_formats = [".mov", ".mp4", ".mkv", ".m4v"]

    def import_project(self, path):
        movie_path, segmentations = self.elan_project_importer(path)

        path = path.replace("\\", "/")
        path = path.split("/")
        filename = path.pop().replace(".eaf", "")

        directory = ""
        for p in path:
            directory += p + "/"

        if self.remote_movie:
            files = glob.glob(directory + "*")
            id_parts = filename.split("_")
            filemaker_id = ""
            for i in range(3):
                filemaker_id += id_parts[i] + "_"
            print("FILEMAKER ID:", filemaker_id)

            for f in files:
                if filemaker_id in f and any(ext in f for ext in self.movie_formats):
                    movie_path = f

        if self.import_screenshots:
            dirs = glob.glob(directory + "*" + "/")
            screenshot_dir = None
            for d in dirs:
                if "_SCR_" in d:
                    screenshot_dir = d.replace("\\", "/")
            if screenshot_dir is not None:
                #TODO
                pass


        project_path = directory + filename
        project = ElanExtensionProject(self.main_window, project_path, filename)
        project.movie_descriptor.movie_path = movie_path

        for i in segmentations:
            segmentation_name = i[0]
            segmentation = project.create_segmentation(segmentation_name, dispatch=False)

            for j in i[1]:
                value = j[0]
                t_start = j[1]
                t_stop = j[2]
                segm = segmentation.create_segment(start = t_start, stop = t_stop, dispatch=False)# , additional_identifiers=[value])
                segm.annotation_body = value


        for s in project.segmentation:
            s.update_segment_ids()


        QMessageBox.information(self.main_window,
                                "Choose the File Path",
                                "Please Choose the Directory in which the new Project should be created.")

        dir = QFileDialog.getExistingDirectory(directory=self.main_window.settings.DIR_PROJECT)
        try:
            # If this project does already exist, we want to test for an increasing number at the end
            if os.path.isdir(dir + "/" + filename):
                counter = 0
                while(os.path.isdir(dir + "/" + filename + "_" + str(counter).zfill(2))):
                    counter += 1
                filename = filename + "_" + str(counter).zfill(2)

            os.mkdir(dir + "/" + filename)
        except:
            self.main_window.print_message("IMPORT FAILED: Could not Create Directory: " + str(dir + filename), "Red")
            return False

        project.folder = dir + "/" + filename + "/"
        project.path = dir + "/" + filename + "/" + filename
        print("Imported ELAN Project:")
        print("      Name: ", project.name)
        print(" Directory: ", project.folder)
        print("      Path: ", project.movie_descriptor.movie_path)
        print("Movie Path: ", project.movie_descriptor.movie_path)
        print("######################")

        project.create_file_structure()

        return project

    def find_time_slot(self, slots, slot_name):
        for s in slots:
            if s[0] == slot_name:
                return s[1]

    def find_absolute_annotation(self, annotations, annotation_name):
        for a in annotations:
            if a[0] == "ABS":
                if a[1] == annotation_name:
                    return a

    def elan_project_importer(self, path):
        DOMTree = xml.dom.minidom.parse(path)
        collection = DOMTree.documentElement

        movie_path = collection.getElementsByTagName("MEDIA_DESCRIPTOR")[0].getAttribute("MEDIA_URL")

        time_slots = []
        time_order_nodes = collection.getElementsByTagName("TIME_ORDER")[0]
        for to in time_order_nodes.getElementsByTagName("TIME_SLOT"):
            slot_id = to.getAttribute("TIME_SLOT_ID")
            slot_time = int(to.getAttribute("TIME_VALUE"))
            time_slots.append([slot_id, slot_time])

        tiers = []
        tier_nodes = collection.getElementsByTagName("TIER")
        for t in tier_nodes:
            tier_name = t.getAttribute("TIER_ID")
            annotations = []
            annotation_nodes = t.getElementsByTagName("ANNOTATION")
            for a in annotation_nodes:
                anotation_object = a.getElementsByTagName('ALIGNABLE_ANNOTATION')
                if len(anotation_object) > 0:
                    a = anotation_object[0]
                    annotation_id = a.getAttribute("ANNOTATION_ID")
                    if a.getElementsByTagName("ANNOTATION_VALUE")[0].firstChild is not None:
                        value = a.getElementsByTagName("ANNOTATION_VALUE")[0].firstChild.nodeValue
                    else:
                        value = "No Value"

                    time_slot_start = a.getAttribute("TIME_SLOT_REF1")
                    time_slot_end = a.getAttribute("TIME_SLOT_REF2")
                    annotations.append(["ABS", annotation_id, value, time_slot_start, time_slot_end])
                else:
                    a = a.getElementsByTagName('REF_ANNOTATION')[0]
                    annotation_id = a.getAttribute("ANNOTATION_ID")
                    value = a.getElementsByTagName("ANNOTATION_VALUE")[0].firstChild
                    annotation_ref = a.getAttribute("ANNOTATION_REF")
                    if value is None:
                        value = annotation_id
                    else:
                        value = value.nodeValue

                    time_slot_end = None
                    annotations.append(["REF", annotation_id, value, annotation_ref, time_slot_end])

            tiers.append([tier_name, annotations])
        abs_annotations = []
        for t in tiers:
            for a in t[1]:
                if a[0] == "ABS":
                    abs_annotations.append(a)

        segmentations = []
        for t in tiers:
            segmentation_name = t[0]
            segments = []
            for a in t[1]:
                value = a[2]
                if a[0] == "ABS":
                    absolute_annotation = a
                    # print a[1]
                else:
                    absolute_annotation = self.find_absolute_annotation(abs_annotations, a[3])

                # if absolute_annotation is None:
                #     print "ERROR", a[3]
                # else:
                #     print "OK", a[3]
                t_start = self.find_time_slot(time_slots, absolute_annotation[3])
                t_stop = self.find_time_slot(time_slots, absolute_annotation[4])
                segment = [value, t_start, t_stop]
                segments.append(segment)

            segmentation = [segmentation_name, segments]
            segmentations.append(segmentation)

        return movie_path, segmentations


class ScreenshotImporter(IConcurrentJob):
    def __init__(self, args):
        super(ScreenshotImporter, self).__init__(args=args)

    def run_concurrent(self, args, sign_progress):
        pass


class FilmColorsPipelineImporter():
    def import_pipeline(self, path, project: ElanExtensionProject):

        try:
            with open(path, "rb") as file:
                data = pickle.load(file)
            #region #--- Import Analysis ---
            analysis = IAnalysisJobAnalysis("FilmColors Pipeline",
                                            results=data,
                                            analysis_job_class=FilmColorsPipelineAnalysis().__class__,
                                            parameters= FilmColorsPipelinePreferences().get_parameters())

            print(np.mean(data['frame_lab_fg'], axis = 0))
            print(np.mean(data['frame_lab_bg'], axis=0))
            print(np.mean(np.divide(np.add(data['frame_lab_bg'].astype(np.float32),data['frame_lab_fg']), 2), axis=0))

            # thumb_fg = []
            # for img in data["thumbnails_fg"]:
            #     thumb_fg.append(cv2.cvtColor(img, cv2.COLOR_BGR2RGBA))
            # thumb_bg = []
            # for img in data["thumbnails_bg"]:
            #     thumb_bg.append(cv2.cvtColor(img, cv2.COLOR_BGR2RGBA))

            # data['thumbnails_fg'] = thumb_fg
            # data['thumbnails_bg'] = thumb_bg

            project.add_analysis(analysis)
            analysis.unload_container()
            #endregion

            return analysis
        except Exception as e:
            print(e)


class FileMakerVocImporter():
    def import_filemaker(self, path, project: ElanExtensionProject):
        with open(path, "r") as file:
            film_id = project.movie_descriptor.movie_id
            reader = csv.reader(file, delimiter=';')
            table = None
            for row in reader:
                if table is None:
                    table = self.parse_header(row)

                elif row[0] == film_id:
                    for i, w in enumerate(row):
                        w = w.replace("\n", "")
                        w = w.rstrip()
                        w = w.lstrip()
                        w = w.split("°")
                        keywords = []
                        for k in w:
                            k = k.rstrip()
                            k = k.lstrip()
                            keywords.append(k)
                        table[i].append(keywords)

            self.apply_vocabulary(table, project)

    def parse_header(self, header):
        header_words = []
        for w in header:
            w = w.replace("_sortiert", "")
            w = w.replace("_Checkboxes_", "")
            w = w.replace("_Checkboxes", "")
            w = w.replace("Checkboxes", "")
            w = w.replace("sortiert", "")
            w = w.replace("Keywords_", "")
            w = w.replace("KeyWords_", "")
            w = w.replace("Merger", "")
            w = w.replace("_", " ")
            w = w.rstrip()
            w = w.lstrip()
            header_words.append([w])
        return header_words


    def apply_vocabulary(self, table, project: ElanExtensionProject, print_failed = False):
        if table is None:
            return

        voc_names = [v.name for v in project.vocabularies]
        voc_obj = [v for v in project.vocabularies]

        segments = []
        skipped = 0
        added  = 0
        for i, row in enumerate(table):
            category = row[0]
            if category in voc_names:
                voc = voc_obj[voc_names.index(category)]
                for j in range(1, len(row)):
                    segm = [j - 1, []]
                    word_group = row[j]
                    for word in word_group:
                        if word != "":
                            word_obj = voc.get_word_by_name(word)
                            if word_obj is None:
                                skipped += 1
                            else:
                                added += 1
                                segm[1].append(word_obj)

                    segments.append(segm)
            else:
                print("No Such Category:", category.replace(" ", "_"))

        main_seg = project.get_main_segmentation()
        print("Main Segmentation Length: ",len(main_seg.segments))
        for s in segments:
            idx = s[0]
            objs = s[1]
            if idx < len(main_seg.segments):
                for word in objs:
                    main_seg.segments[idx].add_word(word)
            else:
                print("Sub-Segmentation Ignored")

        print("Filemaker Data Loaded")
        print("Skipped: ", skipped)
        print("  Added: ", added)


# OLD CODE
# def import_elan_segmentation(path, name, id_identifier, prevent_overlapping = False): #, additional_identifiers):
#     """
#     This Function is deprecated.
#
#     :param path:
#     :param name:
#     :param id_identifier:
#     :param prevent_overlapping:
#     :return:
#     """
#     path = os.path.abspath(path)
#     if not os.path.isfile(path):
#         return False, "Path not found\n" + path
#
#     lines = []
#     segments_data = []
#
#     try:
#         with open(path, 'rb') as csvfile:
#             spamreader = csv.reader(csvfile, delimiter='\t', quotechar='|')
#             for row in spamreader:
#                 lines.append(row)
#
#         curr_id = 0
#         last_end = 0
#         segments = []
#         for row in lines:
#             if row[0] in id_identifier:
#                 id_sequence = curr_id
#                 start_time = int(row[2])
#                 end_time = int(row[3])
#                 duration = int(row[4])
#                 identifier = str(row[5])
#
#                 if prevent_overlapping:
#                     start_time = np.clip(start_time, last_end, None)
#                     last_end = end_time
#
#                 segments.append(Segment(id_sequence, start_time, end_time, duration, [identifier]))
#                 curr_id += 1
#
#
#
#
#
#         segmentation = Segmentation(name, segments)
#         return True, segmentation
#
#     except Exception as e:
#         return False, str(e)
#
# def get_elan_segmentation_identifiers(path):
#     path = os.path.abspath(path)
#     if not os.path.isfile(path):
#         return False, "No such File Exists"
#
#     identifiers = []
#
#     # Finding all identifiers exported
#     try:
#         with open(path, 'rb') as csvfile:
#             spamreader = csv.reader(csvfile, delimiter='\t', quotechar='|')
#
#             for row in spamreader:
#                 if row[0] not in identifiers:
#                     identifiers.append(row[0])
#         return True, identifiers
#     except Exception as e:
#         print(e)
#         return False, e
