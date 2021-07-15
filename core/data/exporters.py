"""
Contains all Export Classes and Export Functions of VIAN
"""

import csv
import cv2
import numpy as np
import os
import pandas as pd
import pypandoc
import random
import shutil
import typing
from core.container.project import *
from core.data.computation import *
from core.data.csv_helper import CSVFile
from core.data.enums import ScreenshotNamingConventionOptions, get_enum_value, ImageType, TargetContainerType
from core.data.interfaces import IConcurrentJob
from pathlib import Path
from subprocess import Popen


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
    def __init__(self, mode="csv"):
        self.data = {}
        self.ascii_doc = []
        self._to_delete_screenshots = []
        self.mode = mode

    @staticmethod
    def _write_screenshot(screenshot, path):
        """
        writes screenshots to disk

        Args:
            path: directory path (pathlib.PosixPath)
        Returns:
            None
        """
        quality = 100
        screenshot = resize_with_aspect(screenshot, width=200)
        compression = int(np.clip(float(100 - quality) / 10,0,9))

        shots = []

        cv2.imwrite(str(path), screenshot, [cv2.IMWRITE_PNG_COMPRESSION, compression])

    def _remove_screenshots(self):
        for screenshot in self._to_delete_screenshots:
            Popen(["rm", str(screenshot)])

    def _export_csv(self, project:VIANProject, path:str):
        if not len(project.segmentation) == 0:
            vocabulary_tree = dict()
            import pandas as pd

            df = pd.DataFrame()

            n_segments = 0
            for s in project.segmentation:
                n_segments += len(s.segments)

            for clobj in project.get_default_experiment().classification_objects:
                if not clobj in vocabulary_tree:
                    vocabulary_tree[clobj] = dict()
                for voc in clobj.classification_vocabularies:
                    vocabulary_tree[clobj][voc] = dict() #type: typing.Dict[Segment, typing.List[UniqueKeyword]]
                    df[clobj.name + ":" + voc.name] = [""] * n_segments

            segment_counter = 0
            segment_columns = ["ClassificationObject:Vocabulary"]
            for segmentation in project.segmentation:
                segmentation_name = segmentation.name
                segmentation_data = {}

                for segment in segmentation.segments:
                    segment_columns.append(segment.ID)
                    segment_name = segment.name
                    segment_data = {}
                    # export notes
                    segment_data["notes"] = segment.notes
                    # export free annotations
                    annos = []
                    for anno in segment._annotations:
                        annos.append((anno.name, anno.content))
                    segment_data["free annotations"] = annos

                    for kwd in segment.tag_keywords: #type:UniqueKeyword
                        if kwd.class_obj not in vocabulary_tree:
                            raise Exception("Classification Object not in Tree")
                        if kwd.voc_obj not in vocabulary_tree[kwd.class_obj]:
                            raise Exception("Vocabulary not in Tree, abort")
                        if segment not in vocabulary_tree[kwd.class_obj][kwd.voc_obj]:
                            vocabulary_tree[kwd.class_obj][kwd.voc_obj][segment] = []

                        val = df[kwd.class_obj.name + ":" + kwd.voc_obj.name].iloc[segment_counter]
                        if val != "":
                            val += ", "
                        val += kwd.word_obj.name
                        df[kwd.class_obj.name + ":" + kwd.voc_obj.name].iloc[segment_counter] = val

                    segment_counter += 1

            df.replace("", np.nan, inplace=True)
            df.dropna(how='all', axis=1, inplace=True)

            df = df.transpose()
            path = Path(path).with_suffix(".csv")
            df.to_csv(path)

    def _build_datadict(self, project):
        """
        builds the self.data dictionary
        which is used to write document

        Args:
            project: the VIAN project object
        Returns:
            None
        """
        if not len(project.segmentation) == 0:
            for ix, segmentation in enumerate(project.segmentation):
                segmentation_name = segmentation.name + str(ix)
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
                    obj_key_w = []
                    for keyw in segment.tag_keywords:
                        for uniq_k in keyw.word_obj.unique_keywords:
                            obj = uniq_k.class_obj.name
                            vocab = uniq_k.voc_obj.name
                            keyword = uniq_k.word_obj.name
                            obj_key_w.append((obj, vocab, keyword))

                    obj_key_w.sort()

                    dict_key_w = {x[0]: {} for x in obj_key_w}

                    for item in obj_key_w:
                            if item[1] in dict_key_w[item[0]]:
                                    dict_key_w[item[0]][item[1]].append(item[2])
                            else:
                                    dict_key_w[item[0]][item[1]] = [item[2]]

                    segment_data["vocabulary_keyword"] = dict_key_w
                    # screenshots
                    shots = []
                    for screenshot in project.screenshots:
                        t_screenshot =screenshot.movie_timestamp
                        if t_screenshot > segment.end:
                            break
                        elif t_screenshot < segment.start:
                            continue
                        else:
                            shots.append(screenshot)
                    try:
                        segment_data["screenshot"] = shots[random.randrange(len(shots))].get_img_movie_orig_size()
                    except:
                        segment_data["screenshot"] = None

                    segmentation_data[segment.ID] = segment_data

                self.data[segmentation_name] = segmentation_data
        else:
            self.data = None

    def export(self, project, path: str):
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

        if self.mode == "csv":
            self._export_csv(project, path)
        elif self.mode == "pdf":
            outpath = Path(path)
            outpath.parents[0].mkdir(parents=True, exist_ok=True)
            file_name = outpath.name

            markdown_path = outpath.parents[0] / (file_name.rstrip(".pdf") + ".md")

            self._build_datadict(project)

            if not self.data:
                return

            self.ascii_doc.append(f"# Sequence Protocol for '{project.name}'\n\n")

            for seg, data in self.data.items():
                self.ascii_doc.append(f"## Segmentation '{seg}'\n")
                for segment in data:
                    self.ascii_doc.append(f"### Segment '{segment}'\n")

                    screenshot = data[segment]["screenshot"]
                    if screenshot is not None:
                        width = project.movie_descriptor.display_width / 2
                        height = project.movie_descriptor.display_height / 2
                        screenshot_name = outpath.parent / (str(uuid4()) + ".png")
                        self._to_delete_screenshots.append(screenshot_name)
                        self._write_screenshot(screenshot, screenshot_name)
                        self.ascii_doc.append(f"![]( {screenshot_name})\n")

                    if data[segment]["notes"]:
                        self.ascii_doc.append("#### Notes\n")
                        self.ascii_doc.append(data[segment]["notes"] + "\n")

                    if data[segment]["free annotations"]:
                        self.ascii_doc.append("#### Free Annoations\n")
                        for anno in data[segment]["free annotations"]:
                            self.ascii_doc.append(": ".join(anno))
                            self.ascii_doc.append("\n")

                    if data[segment]["vocabulary_keyword"]:
                        self.ascii_doc.append("#### Classification Annotations\n")
                        for obj, cl in data[segment]["vocabulary_keyword"].items():
                            self.ascii_doc.append(f"* {obj}")
                            for voc, kw in cl.items():
                                self.ascii_doc.append(f"\t* {voc}")
                                for keyword in kw:
                                    self.ascii_doc.append(f"\t\t* {keyword}")

                    self.ascii_doc.append("\n'''\n\n")

            with open(markdown_path, "w") as outf:
                outf.write("\n".join(self.ascii_doc))

            try:
                latex = pypandoc.convert_file(str(markdown_path), outputfile=str(outpath), to="pdf")

                print(latex)
                # Popen(["asciidoctor-pdf", markdown_path]).wait()
                print(f"Sequence Protocol written to {str(outpath)}.")
            except Exception as e:
                self._remove_screenshots()
                # if markdown_path.exists():
                #     os.remove(str(markdown_path))
                # outpath.rmdir()

                raise e

            self._remove_screenshots()
        else:
            raise AttributeError("Mode is not supported:", self.mode)

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
