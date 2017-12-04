import cv2
import numpy as np
from core.data.enums import ScreenshotNamingConventionOptions, get_enum_value, ImageType
from core.data.interfaces import IConcurrentJob
from core.data.computation import *
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

            print file_name

class SegmentationExporter(IConcurrentJob):
    def __init__(self, file_path, export_ms = False, ):
        self.file_path = file_path
        self.export_ms = export_ms


    def export(self, segmentations):
        tab = "\t"
        result = ""
        for segmentation in segmentations:
            name = segmentation['name']
            for s in segmentation['segments']:
                value = s['additional_identifiers'][0]
                start = ms_to_string(s['start'])
                end = ms_to_string(s["end"])
                duration = ms_to_string(s["end"] - s['start'])

                result += name + tab + tab + start + tab + end + tab + duration + tab + value + "\n"

        with open("result.txt", "w") as output:
            output.write(result)


def build_file_name(naming, screenshot, movie_descriptor):
    file_name = "/"
    print screenshot.scene_id

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
                print file_name

            if i < len(naming) - 1:
                if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                    break
                else:
                    file_name += "_"


    file_name = file_name.replace("__", "")
    file_name = file_name.replace("All Shots_", "_")

    return file_name