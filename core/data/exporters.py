import cv2
import numpy as np
from core.data.enums import ScreenshotNamingConventionOptions, get_enum_value, ImageType
from core.data.interfaces import IConcurrentJob
from core.data.computation import *
import os
import shutil

def zip_project(output_file, project_folder):
    shutil.make_archive(output_file, 'zip', project_folder)


class ScreenshotsExporter():
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
                img = s.img_movie

            if smooth:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            # Export depending on the image Type selected

            if image_type.value == ImageType.JPG.value:
                cv2.imwrite(file_name + ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])

            if image_type.value == ImageType.PNG.value:
                compression = np.clip(int(float(100 - quality) / 10),0,9)
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])

            print(file_name)


class SegmentationExporter(IConcurrentJob):
    def __init__(self, file_path, export_ms, export_formated, export_text, export_frame, t_start, t_end, t_duration, fps):
        self.file_path = file_path
        self.fps = fps
        self.export_formated = export_formated
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
                # value = s['additional_identifiers'][0]
                # start = ms_to_string(s['start'])
                # end = ms_to_string(s["end"])
                # duration = ms_to_string(s["end"] - s['start'])

                # result += name + tab + tab + start + tab + end + tab + duration + tab + value + "\n"
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


def build_file_name(naming, screenshot, movie_descriptor):
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
                print(file_name)

            if i < len(naming) - 1:
                if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                    break
                else:
                    file_name += "_"


    file_name = file_name.replace("__", "")
    file_name = file_name.replace("All Shots_", "_")

    return file_name