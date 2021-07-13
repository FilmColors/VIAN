"""
Contains all Export Classes and Export Functions of VIAN
"""

import cv2
import numpy as np
import pandas as pd
from core.data.interfaces import IConcurrentJob
from core.data.computation import *
from core.container.project import *
import os
import csv
import shutil

from core.data.csv_helper import CSVFile


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


class ScreenshotExporter(ExportDevice):
    """
    A Class that is able to export Screenshots from a Project
    """
    SemSeg_None = "None"
    SemSeg_Outlines = "Outlines"
    SemSeg_Filled = "Filled"
    SemSeg_OutlinesFilled = "Both"


    def __init__(self, naming, selection = None, quality = 100, semantic_segmentation=SemSeg_None):
        self.naming = naming
        self.quality = quality
        self.selection = selection
        self.semantic_segmentation = semantic_segmentation

    def export(self, project, path):
        # If nothing is selected we export all screenshots
        if self.selection is None:
            self.selection = project.screenshots
        else:
            # Ensure only screenshots are in the selection
            self.selection = [s for s in self.selection if isinstance(s, Screenshot)]
            if len(self.selection) == 0:
                self.selection = project.screenshots

        for s in self.selection:
            name = self.build_file_name(self.naming, s, project.movie_descriptor)
            file_name = os.path.join(path, name)

            img = s.get_img_movie_orig_size()
            if self.semantic_segmentation == self.SemSeg_Filled or \
                    self.semantic_segmentation == self.SemSeg_OutlinesFilled:
                semantic_segmentations = s.get_connected_analysis("SemanticSegmentationAnalysis")
                print(semantic_segmentations)
                if len(semantic_segmentations) > 0:
                    n = 20
                    colormap = get_colormap(n)
                    data = semantic_segmentations[0].get_adata()
                    mask = np.zeros(shape=data.shape + (3,), dtype=np.float32)
                    for i in range(n):
                        mask[data == i] = colormap[i][:3]
                    mask = (mask * 255).astype(np.uint8)
                    mask = cv2.cvtColor(mask, cv2.COLOR_RGBA2BGR)
                    img = img * 0.7 + mask * 0.3

            if self.semantic_segmentation == self.SemSeg_Outlines  or \
                    self.semantic_segmentation == self.SemSeg_OutlinesFilled:
                semantic_segmentations = s.get_connected_analysis("SemanticSegmentationAnalysis")
                if len(semantic_segmentations) > 0:
                    n = 20
                    colormap = get_colormap(n)
                    data = semantic_segmentations[0].get_adata()
                    data = cv2.resize(data, img.shape[:2][::-1], interpolation=cv2.INTER_NEAREST)
                    cnts = cv2.findContours(data, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
                    print(data.shape, img.shape)
                    for i, c in enumerate(cnts):
                        # col = tuple(np.array(colormap[0][:3] * 255).astype(np.uint8))
                        # print(tuple((np.array(colormap[i][:3]) * 255).astype(np.uint8)))
                        cv2.drawContours(img, [c], -1, (232, 255, 12), thickness=3)

            if ".jpg" in file_name:
                cv2.imwrite(file_name, img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])

            elif ".png" in file_name:
                compression = int(np.clip(float(100 - self.quality) / 10,0,9))
                cv2.imwrite(file_name, img, [cv2.IMWRITE_PNG_COMPRESSION, compression])
            else:
                file_name += ".png"
                compression = int(np.clip(float(100 - self.quality) / 10,0,9))
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])

    def build_file_name(self, naming, screenshot:Screenshot, movie_descriptor:MovieDescriptor):
        """
        Generates a Filename for the Screenshots by a given naming convention

        :param naming:
        :param screenshot:
        :param movie_descriptor:
        :return:
        """
        f = naming.format(ShotID=screenshot.shot_id_segm,
                          SceneID = screenshot.scene_id,
                          TimeMS=screenshot.get_start(),
                          Timestamp=ms_to_string(screenshot.get_start()).replace(":", "_"),
                          MovieID=movie_descriptor.movie_id,
                          MovieName=movie_descriptor.movie_name,
                          MovieYear=movie_descriptor.year,
                          ShotGroup=screenshot.screenshot_group.name)
        return f.replace("All Shots", "").replace("__", "_")


class SegmentationExporter(ExportDevice):
    """
    A Class that is able to export a Segmentation into CSV
    """
    def __init__(self, file_path, export_ms, export_formated, export_formated_ms, export_formated_frame,
                 export_text, export_frame, t_start, t_end, t_duration, fps, segmentations):
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
        self.segmentations = segmentations

    def export(self, project:VIANProject, path):

        def add(d, k, v):
            if k not in d:
                d[k] = []
            d[k].append(v)

        result = dict()

        if self.segmentations is None:
            self.segmentations = project.segmentation

        # Make sure we have all bodies in the header
        bodies = set()
        for segmentation in self.segmentations:
            for s in segmentation.segments:
                for a in s.get_annotations():
                    bodies.add("annotation_{}".format(a.name))
        print("All bodies", bodies)

        for segmentation in self.segmentations:
            for s in segmentation.segments: # type:Segment
                bodies_added = set()
                add(result, "segment_id", s.ID)
                add(result, "segmentation_name", segmentation.name)
                if self.export_ms:

                    if self.t_start:
                        add(result, "start_ms", s.start)

                    if self.t_end:
                        add(result, "end_ms", s.end)

                    if self.t_duration:
                        add(result, "duration_ms", s.duration)

                if self.export_formated:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration))

                elif self.export_formated_ms:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start, include_ms=True))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end, include_ms=True))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration, include_ms=True))

                elif self.export_formated_frame:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start, include_frame=True))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end, include_frame=True))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration, include_frame=True))

                if self.export_frame:
                    if self.t_start:
                        add(result, "start_frame", ms_to_frames(s.start, self.fps))

                    if self.t_end:
                        add(result, "end_frame", ms_to_frames(s.end, self.fps))

                    if self.t_duration:
                        add(result, "duration_frame", ms_to_frames(s.duration, self.fps))

                for i, b in enumerate(s.get_annotations()):  # type: AnnotationBody
                    column = "annotation_{i}_{f}".format(i=i, f=b.name)
                    bodies_added.add(column)
                    add(result, column, b.content)

                for b in bodies.difference(bodies_added):
                    add(result, b, "")

        if ".xlsx" in path:
            pd.DataFrame(result).to_excel(path)
        else:
            pd.DataFrame(result).to_csv(path)


class SequenceProtocolExporter:
    def __init__(self):
        self.data = {}

    def export(self, project: VIANProject, path: str):
        """
        exporting data from all Segmentations

        For a first draft, no additional arguments
        can be passed, such as specifying which
        segmentation etc.

        Args:
            project: the container class of a VIAN project
            path: a string for writing the export to
        Returns:
            None
        """
        for segmentation in project.segmentation:
            segmentation_name = segmentation.name
            segmentation_data = {}
            for segment in segmentation.segments:
                segment_name = segment.name
                segment_data = {}
                # export notes
                segment_data["notes"] = segment.notes
                # export free annotations
                annos = []
                for anno in segment._annotations:
                   annos.append((anno.name, anno.content))
                segment_data["free annotations"] = annos
                # export classifications

                segmentation_data[segment_name] = segment_data
        self.data[segmentation_name] = segmentation_data
        # import ipdb; ipdb.set_trace()


class JsonExporter():
    def segment2json(self, segment):
        pass
        # result = ""


class CSVExporter(ExportDevice):
    def __init__(self, export_segmentations = True, export_screenshots=True, export_annotations=True,
                 export_keywords = True, timestamp_format = "ms"):
        self.export_segm = export_segmentations
        self.export_ann = export_annotations
        self.export_scr = export_screenshots
        self.export_keywords = export_keywords

    def export(self, project, path):
        f = CSVFile()

        headers = ["ROW", "ID", "START_MS", "END_MS",
                   "SELECTOR_TYPE", "ANNOTATION_MIME_TYPE", "ANNOTATION_BODY_ID", "ANNOTATION_BODY",
                   "NOTES"]

        if self.export_keywords:
            keyword_mapping = get_keyword_columns(project)
            keyword_columns = keyword_mapping.keys()
            headers.extend(keyword_columns)

        f.set_header(headers)

        c = 0
        if self.export_segm:
            segments = []
            [segments.extend(s.segments) for s in project.segmentation]

            for segm in segments:  #type:Segment
                bodies = segm.get_annotations()
                if len(bodies) == 0:
                    bodies = [AnnotationBody()]
                for bd in bodies:
                    r = dict(
                        ROW = c,
                        ID = segm.unique_id,
                        START_MS = segm.get_start(),
                        END_MS = segm.get_end(),
                        SELECTOR_TYPE = "SEGMENT",
                        ANNOTATION_MIME_TYPE = bd.mime_type,
                        ANNOTATION_BODY_ID = bd.unique_id,
                        ANNOTATION_BODY = bd.content,
                        NOTES = segm.notes
                    )

                    if self.export_keywords:
                        for k in keyword_columns:
                            r[k] = 0
                        for k in segm.tag_keywords:
                            name = k.get_full_name()
                            r[name] = 1
                    f.append(r)
                    c += 1

        if self.export_scr:
            for scr in project.screenshots:  #type:Screenshot
                bodies = scr.get_annotations()
                if len(bodies) == 0:
                    bodies = [AnnotationBody()]

                for bd in bodies:
                    r = dict(
                        ROW = c,
                        ID = scr.unique_id,
                        START_MS = scr.get_start(),
                        END_MS = scr.get_end(),
                        SELECTOR_TYPE = "SCREENSHOT",
                        ANNOTATION_MIME_TYPE=bd.mime_type,
                        ANNOTATION_BODY_ID=bd.unique_id,
                        ANNOTATION_BODY=bd.content,
                        NOTES = scr.notes
                    )
                    if self.export_keywords:
                        for k in keyword_columns:
                            r[k] = 0
                        for k in scr.tag_keywords:
                            name = k.get_full_name()
                            r[name] = 1
                    f.append(r)
                    c += 1
        f.save(path)


class ColorimetryExporter(ExportDevice):
    def __init__(self):
        pass

    def export(self, project:VIANProject, path):
        if project.colormetry_analysis is None:
            raise Exception("Colorimetry has not been performed yet")

        data = np.zeros(shape=(len(project.colormetry_analysis), 6))

        timestamps = []
        for i, entry in enumerate(project.colormetry_analysis.iter_avg_color()):
            l,c,h = lch_to_human_readable([entry['l'], entry['c'],entry['h']])
            data[i] = [
              entry['time_ms'],
              entry['l'],
              entry['a'],
              entry['b'],
              c,
              h,
            ]
            timestamps.append(ms_to_string(entry['time_ms']))

        df = pd.DataFrame(dict(time_ms=data[:, 0],
                               timestamp=timestamps,
                               luminance=data[:, 1],
                               a=data[:, 2],
                               b=data[:, 3],
                               chroma=data[:, 4],
                               hue=data[:, 5]
                               ))

        df.to_csv(os.path.join(project.export_dir, path), index_label="ID")


def build_segment_nomenclature(s:Segment):
    return str(s.project.movie_descriptor.movie_id) + "_"+ s.segmentation.name +"_" + str(s.ID)
