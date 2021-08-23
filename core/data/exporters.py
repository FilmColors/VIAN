"""
Contains all Export Classes and Export Functions of VIAN
"""
import io
import pandas as pd
from core.container.project import *
import os
import shutil
from PIL import Image

from core.data.computation import ms_to_string
from core.data.csv_helper import CSVFile


def zip_project(output_file, project_folder):
    shutil.make_archive(output_file, 'zip', project_folder)


def get_keyword_columns(project:VIANProject, container_type = None):
    keywords = dict()
    for e in project.experiments:
        for kwd in e.get_unique_keywords(container_type):
            keywords[kwd.get_full_name()] = kwd
    return keywords


class IExportDevice:
    def export(self, project, path):
        pass


class ScreenshotExporter(IExportDevice):
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


class SegmentationExporter(IExportDevice):
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


class SequenceProtocolExporter(IExportDevice):
    FORMAT_CSV = "csv"
    FORMAT_PDF = "pdf"
    FORMAT_EXCEL = "excel"

    def __init__(self, export_format=FORMAT_CSV):
        self.export_format = export_format

    def export(self, project: VIANProject, path: str):
        """
        Export the project into Sequence protocols.

        :param project: the VIANProject which the data is exported for
        :param path: the destination path for the exported csv file
        """
        f = CSVFile()
        headers = {"NO": "NO", "START": "START", "END": "END", "DURATION": "DURATION", "ANNOTATIONS": "ANNOTATIONS",
                   "SCREENSHOTS": "SCREENSHOTS"}

        # collect all unique_id of used keywords and collect additional headers
        additional_headers = []
        for segmentation in project.segmentation:
            for segment in segmentation.segments:
                for unique_keyword in segment.tag_keywords:

                    # search for correct classification object
                    for classification_object in project.experiments[0].classification_objects:
                        found = False
                        for keyword in classification_object.unique_keywords:
                            if keyword.unique_id == unique_keyword.unique_id:
                                additional_headers.append((classification_object, unique_keyword.voc_obj))
                                found = True
                                break
                        if found:
                            break

        # set the additional header columns which were found above
        unique_classification_objects = set([ah[0] for ah in additional_headers])
        for additional_header in additional_headers: # if only one object is tagged, its name is not exported
            if len(unique_classification_objects) > 1:
                headers[additional_header] = additional_header[0].name + ":" + additional_header[1].name
            else:
                headers[additional_header] = additional_header[1].name

        f.set_header(headers.values())

        for segmentation in project.segmentation:
            for segment in segmentation.segments:
                entry = dict.fromkeys(headers.values())
                entry["NO"] = segment.ID
                entry["START"] = ms_to_string(segment.get_start())
                entry["END"] = ms_to_string(segment.get_end())

                entry["DURATION"] = segment.duration // 1000  # convert ms to seconds (floor)

                annotation = "\n".join([a.content for a in segment.get_annotations()])
                entry["ANNOTATIONS"] = annotation

                if self.export_format == SequenceProtocolExporter.FORMAT_CSV \
                        and bool(project.segment_screenshot_mapping):
                    screenshots = "\n".join(
                        ["{}_{}_{}_{}".format(ss.scene_id, ss.shot_id_segm,
                                              ss.screenshot_group.name, project.movie_descriptor.movie_id)
                         for ss in project.segment_screenshot_mapping[segment]])
                    entry["SCREENSHOTS"] = screenshots

                for key_word in segment.tag_keywords:
                    if (key_word.class_obj, key_word.voc_obj) in headers.keys():
                        if entry[headers[(key_word.class_obj, key_word.voc_obj)]] is None:
                            entry[headers[(key_word.class_obj, key_word.voc_obj)]] = key_word.word_obj.name
                        else:
                            entry[headers[(key_word.class_obj, key_word.voc_obj)]] = \
                                entry[headers[(key_word.class_obj, key_word.voc_obj)]] + ", " + key_word.word_obj.name

                f.append(entry)

        if self.export_format == SequenceProtocolExporter.FORMAT_CSV:
            f.save(path, index=False)
        elif self.export_format == SequenceProtocolExporter.FORMAT_EXCEL:
            df = f.get_data()
            writer = pd.ExcelWriter(path, engine='xlsxwriter')

            df.to_excel(writer, sheet_name='Sheet1', index=False)
            workbook = writer.book
            workbook.formats[0].set_text_wrap()
            worksheet = writer.sheets['Sheet1']
            
            for idx, col in enumerate(df):  # column width is set according to longest string
                series = df[col]
                single_items = [word for word_collection in series.array for word in str(word_collection).split("\n")]
                max_len = max((
                    pd.Series(single_items).astype(str).map(len).max(),  # length of largest item
                    len(str(series.name))  # length of column header
                )) + 1  # adding a bit of extra space
                worksheet.set_column(idx, idx, max_len)  # set column width

            df_counter = 1  # the excel file starts with the header at index 0
            margin = 15
            screenshots_exist = False
            screenshots_index = df.columns.get_loc("SCREENSHOTS")
            screenshot_width = 200
            for segmentation in project.segmentation:
                for segment in segmentation.segments:
                    offset_y = 0
                    for screenshot in project.segment_screenshot_mapping[segment]:
                        screenshots_exist = True
                        f = screenshot.get_img_movie_orig_size()
                        imgByteArr = io.BytesIO()
                        Image.fromarray(f[:,:,::-1], 'RGB').save(imgByteArr, format="png")
                        scaling_factor = screenshot_width/f.shape[1]
                        worksheet.insert_image(df_counter, screenshots_index, "", {'image_data': imgByteArr,
                                                          'x_scale': scaling_factor, 'y_scale': scaling_factor,
                                                          'y_offset' : offset_y * scaling_factor})
                        offset_y += f.shape[0] + margin
                    worksheet.set_row_pixels(df_counter, offset_y * scaling_factor) # set row height
                    df_counter += 1
            if screenshots_exist:
                worksheet.set_column_pixels(screenshots_index, screenshots_index, screenshot_width)  # set column width
            writer.close() # saves the file and closes all handles


class JsonExporter():
    def segment2json(self, segment):
        pass
        # result = ""


class ColorimetryExporter(IExportDevice):
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
