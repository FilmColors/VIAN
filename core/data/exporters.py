"""
Contains all Export Classes and Export Functions of VIAN
"""

import cv2
import numpy as np
from core.data.enums import ScreenshotNamingConventionOptions, get_enum_value, ImageType, TargetContainerType
from core.data.interfaces import IConcurrentJob
from core.data.computation import *
from core.container.project import *
import os
import csv
import shutil


DEFAULT_NAMING_SCREENSHOTS = [
    ScreenshotNamingConventionOptions.Scene_ID.name,
    ScreenshotNamingConventionOptions.Shot_ID_Segment.name,
    ScreenshotNamingConventionOptions.Movie_ID.name,
    ScreenshotNamingConventionOptions.Movie_Name.name,
    ScreenshotNamingConventionOptions.Movie_Year.name,
    ScreenshotNamingConventionOptions.Movie_Source.name,
        ]

def zip_project(output_file, project_folder):
    shutil.make_archive(output_file, 'zip', project_folder)


def get_keyword_columns(project:VIANProject, container_type = None):
    keywords = dict()
    for e in project.experiments:
        for kwd in e.get_unique_keywords(container_type):
            keywords[kwd.get_full_name()] = kwd
    return keywords


class ExportDevice:
    def export(self, project, path):
        pass


class _ScreenshotExporter(ExportDevice):
    """
    A Class that is able to export Screenshots from a Project
    """
    def __init__(self, naming, annotation_visibility = None,
                 image_type = ImageType.JPG, quality = 100, smooth = False):
        self.naming = naming
        self.smooth = smooth
        self.quality = quality
        self.image_type = image_type,
        self.annotation_visibility = annotation_visibility,

    def export(self, project, path):
        for s in project.screenshots:
            if self.naming is None:
                name = build_file_name(DEFAULT_NAMING_SCREENSHOTS, s, project.movie_descriptor)
            else:
                name = build_file_name(self.naming, s, project.movie_descriptor)
            file_name = os.path.join(path, name)

            if self.annotation_visibility is None:
                annotation_visibility = s.annotation_is_visible

            if self.annotation_visibility:
                img = s.img_blend
            else:
                img = s.get_img_movie_orig_size()

            if self.smooth:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            # Export depending on the image Type selected

            if self.image_type == ImageType.JPG:
                cv2.imwrite(file_name + ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])

            if self.image_type == ImageType.PNG:
                compression = int(np.clip(float(100 - self.quality) / 10,0,9))
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])


    def build_file_name(self, naming, screenshot, movie_descriptor):
        """
        Generates a Filename for the Screenshots by a given naming convention

        :param naming:
        :param screenshot:
        :param movie_descriptor:
        :return:
        """
        file_name = "/"

        for i, name in enumerate(naming):
            if name is not ScreenshotNamingConventionOptions.empty.name:
                value = get_enum_value(ScreenshotNamingConventionOptions, name)
                object_type = value[0]
                object_attr = value[1]

                if object_type == "Screenshot":
                    if object_attr == "screenshot_group":
                        file_name = file_name[:-1]
                    file_name += str(getattr(screenshot, object_attr))

                if object_type == "Movie":
                    file_name += str(getattr(movie_descriptor, object_attr))

                if i < len(naming) - 1:
                    if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                        break
                    else:
                        file_name += "_"

        file_name = file_name.replace("__", "")
        file_name = file_name.replace("All Shots_", "_")

        return file_name


class ScreenshotsExporter():
    """
    A Class that is able to export Screenshots from a Project
    """
    def __init__(self, settings, project, naming):
        self.settings = settings
        self.project = project
        self.naming = naming

    def export(self, screenshots, dir, annotation_visibility = None, image_type = ImageType.JPG, quality = 100, smooth = False):
        for s in screenshots:
            if self.naming is None:
                name = build_file_name(self.settings.SCREENSHOTS_EXPORT_NAMING, s, self.project.movie_descriptor)
            else:
                name = build_file_name(self.naming, s, self.project.movie_descriptor)
            file_name = dir + name

            if annotation_visibility is None:
                annotation_visibility = s.annotation_is_visible

            if annotation_visibility:
                img = s.img_blend
            else:
                img = s.get_img_movie_orig_size()

            if smooth:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            # Export depending on the image Type selected

            if image_type.value == ImageType.JPG.value:
                cv2.imwrite(file_name + ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])

            if image_type.value == ImageType.PNG.value:
                compression = int(np.clip(float(100 - quality) / 10,0,9))
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])


class SegmentationExporter(IConcurrentJob):
    """
    A Class that is able to export a Segmentation into CSV
    """
    def __init__(self, file_path, export_ms, export_formated, export_formated_ms, export_formated_frame,
                 export_text, export_frame, t_start, t_end, t_duration, fps):
        self.file_path = file_path
        self.fps = fps
        self.export_formated = export_formated
        self.export_formated_ms = export_formated_ms
        self.export_formated_frame = export_formated_frame
        self.export_text = export_text
        self.export_frame = export_frame
        self.t_start = t_start
        self.t_end = t_end
        self.t_duration = t_duration
        self.export_ms = export_ms

    def export(self, segmentations):
        # tab = "\t"
        result = ""
        for segmentation in segmentations:
            name = segmentation['name']

            for s in segmentation['segments']:
                id = s['scene_id']
                line = name + "\t" + str(id) + "\t"

                start = int(s['start'])
                end = int(s['end'])
                duration = int(s["end"] - s['start'])

                if self.export_ms:
                    if self.t_start:
                        line += str(start) + "\t"

                    if self.t_end:
                        line += str(end) + "\t"

                    if self.t_duration:
                        line += str(duration) + "\t"

                if self.export_formated:
                    if self.t_start:
                        line += ms_to_string(start) + "\t"

                    if self.t_end:
                        line += ms_to_string(end) + "\t"

                    if self.t_duration:
                        line += ms_to_string(duration) + "\t"

                if self.export_formated_ms:
                    if self.t_start:
                        line += ms_to_string(start, include_ms=True) + "\t"

                    if self.t_end:
                        line += ms_to_string(end, include_ms=True) + "\t"

                    if self.t_duration:
                        line += ms_to_string(duration, include_ms=True) + "\t"

                if self.export_formated_frame:
                    if self.t_start:
                        line += ms_to_string(start, include_frame=True, fps = self.fps) + "\t"

                    if self.t_end:
                        line += ms_to_string(end, include_frame=True, fps = self.fps) + "\t"

                    if self.t_duration:
                        line += ms_to_string(duration, include_frame=True, fps = self.fps) + "\t"

                if self.export_frame:
                    if self.t_start:
                        line += str(ms_to_frames(start, self.fps)) + "\t"

                    if self.t_end:
                        line += str(ms_to_frames(end, self.fps)) + "\t"

                    if self.t_duration:
                        line += str(ms_to_frames(duration, self.fps)) + "\t"

                if self.export_text:
                    line += s['annotation_body'].replace("\n", "")
                result += line +"\n"

        try:
            with open(self.file_path , "w") as output:
                output.write(result)
            return True, None
        except Exception as e:
            return False, e


class JsonExporter():
    def segment2json(self, segment):
        pass
        # result = ""


class XMLExchangeExporter():
    def __init__(self):
        pass

    def export(self, project:VIANProject):
        pass


class CSVExporter(ExportDevice):
    def __init__(self, export_segmentations = True, export_screenshots=True, export_annotations=True,
                 export_keywords = True, timestamp_format = "ms"):
        self.export_segm = export_segmentations
        self.export_ann = export_annotations
        self.export_scr = export_screenshots
        self.export_keywords = export_keywords

    def export(self, project, path):
        if self.export_segm:
            segm_outfile = path + "_segm.csv"

            headers = ["UID", "Time Start", "Time End", "Body"]
            if self.export_keywords:
                keyword_mapping = get_keyword_columns(project)
                keyword_columns = keyword_mapping.keys()
                headers.extend(keyword_columns)
            segments = []
            [segments.extend(s.segments) for s in project.segmentation]
            with open(segm_outfile, "w", newline="") as out_file:
                writer = csv.writer(out_file, delimiter=";")
                writer.writerow(headers)
                for s in segments: #type:Segment
                    row = [s.unique_id, s.start, s.end, s.annotation_body]
                    if self.export_keywords:
                        row.extend([False] * (len(headers) - 4))
                        for k in s.tag_keywords:
                            name = k.get_full_name()
                            row[headers.index(name)] = True
                    writer.writerow(row)
        if self.export_scr:
            segm_outfile = path + "_scr.csv"

            headers = ["UID", "Time Start"]
            if self.export_keywords:
                keyword_mapping = get_keyword_columns(project)
                keyword_columns = keyword_mapping.keys()
                headers.extend(keyword_columns)
            with open(segm_outfile, "w", newline="") as out_file:
                writer = csv.writer(out_file, delimiter=";")
                writer.writerow(headers)

                for s in project.screenshots: # type: Screenshot
                    row = [s.unique_id, s.movie_timestamp]
                    if self.export_keywords:
                        row.extend([False] * (len(headers) - 4))
                        for k in s.tag_keywords:
                            name = k.get_full_name()
                            row[headers.index(name)] = True
                    writer.writerow(row)


def build_file_name(naming, screenshot, movie_descriptor):
    """
    Generates a Filename for the Screenshots by a given naming convention
    
    :param naming: 
    :param screenshot: 
    :param movie_descriptor: 
    :return: 
    """
    file_name = "/"

    for i, name in enumerate(naming):
        if name is not ScreenshotNamingConventionOptions.empty.name:
            value = get_enum_value(ScreenshotNamingConventionOptions, name)
            object_type = value[0]
            object_attr = value[1]

            if object_type == "Screenshot":

                # This removed the underline for the ERC Screenshot Groups, but is unpredictable for other users.
                # if object_attr == "screenshot_group":
                #     file_name = file_name[:-1]

                attr = getattr(screenshot, object_attr)
                if isinstance(attr, ScreenshotGroup):
                    attr = attr.get_name()
                file_name += str(attr)

            if object_type == "Movie":
                file_name += str(getattr(movie_descriptor, object_attr))

            if i < len(naming) - 1:
                if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                    break
                else:
                    file_name += "_"

    file_name = file_name.replace("__", "")
    file_name = file_name.replace("All Shots_", "_")

    return file_name