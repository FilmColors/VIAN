import csv
import os
import glob
import xml.dom.minidom
from xml.dom.minidom import parse

import numpy as np

from core.data.containers import Segment, Segmentation, ElanExtensionProject
from core.data.interfaces import IConcurrentJob


def import_elan_segmentation(path, name, id_identifier, prevent_overlapping = False): #, additional_identifiers):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return False, "Path not found\n" + path

    lines = []
    segments_data = []

    try:
        with open(path, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter='\t', quotechar='|')
            for row in spamreader:
                lines.append(row)

        curr_id = 0
        last_end = 0
        segments = []
        for row in lines:
            if row[0] in id_identifier:
                id_sequence = curr_id
                start_time = long(row[2])
                end_time = long(row[3])
                duration = long(row[4])
                identifier = str(row[5])

                if prevent_overlapping:
                    start_time = np.clip(start_time, last_end, None)
                    last_end = end_time

                segments.append(Segment(id_sequence, start_time, end_time, duration, [identifier]))
                curr_id += 1





        segmentation = Segmentation(name, segments)
        return True, segmentation

    except Exception as e:
        return False, str(e)

def get_elan_segmentation_identifiers(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return False, "No such File Exists"

    identifiers = []

    # Finding all identifiers exported
    try:
        with open(path, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter='\t', quotechar='|')

            for row in spamreader:
                if row[0] not in identifiers:
                    identifiers.append(row[0])
        return True, identifiers
    except Exception as e:
        print e.message
        return False, e.message

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
            print "FILEMAKER ID:", filemaker_id

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
            segmentation = Segmentation(segmentation_name)
            project.add_segmentation(segmentation)

            for j in i[1]:
                value = j[0]
                t_start = j[1]
                t_stop = j[2]
                segm = Segment(start = t_start, end = t_stop, additional_identifiers=[value])

                # segmentation.segments.append(segm)
                segmentation.add_segment(segm)
            # project.segmentation.append(segmentation)

        for s in project.segmentation:
            s.update_segment_ids()

        print project.name
        print project.path
        print project.movie_descriptor.movie_path

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
            slot_time = long(to.getAttribute("TIME_VALUE"))
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
    
