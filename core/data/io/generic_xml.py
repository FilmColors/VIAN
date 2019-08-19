import xml.etree.cElementTree as et
import xml.dom.minidom as md

from core.analysis.analysis_import import *
class GenericXMLDevice():
    def __init__(self):
        pass

    #region EXPORT
    def build_document(self, author = "author", format = "2.8", version = "2.8"):
        root = et.Element("ANNOTATION_DOCUMENT")
        root.set("AUTHOR", author)
        root.set("FORMAT", format)
        root.set("VERSION", version)

        return root

    def build_header(self, root, project:VIANProject, media: MovieDescriptor, time_units = "milliseconds"):
        d = dict(
                PROJECT_NAME = project.name
                 )

        header = et.SubElement(root, "HEADER",  d)

        movied = dict(MEDIA_URL=media.movie_path,
                 TIME_UNITS=time_units,
                 DURATION=str(media.duration),
                 FPS=str(media.fps),
                 YEAR=str(media.year),
                 IS_RELATIVE=str(media.is_relative),
                 )

        et.SubElement(header, "MEDIA_DESCRIPTOR", movied)

        return header

    def add_time_slots(self, root, ts):
        grp = et.Element("TIMER_ORDER")
        for i, t in enumerate(ts[0]):
            d = dict(TIME_SLOT_ID = str(ts[1][i]), TIME_VALUE = str(ts[0][i]))
            et.SubElement(grp, "TIME_SLOT", d)
        root.insert(1, grp)
        return grp

    def to_time_mapping(self, mapping, container:ITimeRange):
        a = container.get_start()
        b = container.get_end()
        if a not in mapping[0]:
            mapping[0].append(a)
            mapping[1].append("ts" + str(len(mapping[1])))
        if b not in mapping[0]:
            mapping[0].append(b)
            mapping[1].append("ts" + str(len(mapping[1])))
        return (mapping[1][mapping[0].index(a)], mapping[1][mapping[0].index(b)])

    def add_segmentation(self, root, seg:Segmentation, time_mapping, external_media):
        grp = et.SubElement(root, "SEGMENTATION", NAME=seg.name, ID = str(seg.unique_id))
        for s in seg.segments:
            # s = Segment()
            (ref_start, ref_end) = self.to_time_mapping(time_mapping, s)
            d = dict(
                ID = str(s.unique_id),
                T_START = ref_start,
                T_END = ref_end,
                BODY = s.annotation_body
            )
            et.SubElement(grp, "SEGMENT", d)
            for ext in s.media_objects:
                external_media.append([ext, s.unique_id])
        return grp

    def add_annotation(self, root, lay:AnnotationLayer, time_mapping, external_media):
        grp = et.SubElement(root, "ANNOTATION_LAYER", NAME=lay.name, ID = str(lay.unique_id))
        for a in lay.annotations:
            # a = Annotation()
            (ref_start, ref_end) = self.to_time_mapping(time_mapping, a)
            pos = str(a.orig_position[0]) +", "+ str(a.orig_position[1])
            size = str(a.size[0]) + ", " + str(a.size[1])
            color = str(a.color[0]) + ", " + str(a.color[1])+ ", " + str(a.color[1])
            d = dict(
                ID = str(a.unique_id),
                T_START = ref_start,
                T_END = ref_end,
                A_TYPE = str(a.a_type),
                POS = pos,
                SIZE = size,
                TEXT = str(a.text),
                RESSOURCE_PATH = str(a.resource_path),
                COLOR = color
            )
            et.SubElement(grp, "VISUAL_ANNOTATION", d)

            for ext in a.media_objects:
                external_media.append([ext.unique_id, ext.file_path, ext.unique_id])
        return grp

    def add_screenshots(self, root, screenshots: Screenshot, screenshot_groups: List[ScreenshotGroup], time_mapping):
        grp = et.SubElement(root, "SCREENSHOTS")
        for a in screenshots:
            a = Screenshot()
            (ref_start, ref_end) = self.to_time_mapping(time_mapping, a)
            d = dict(
                ID = str(a.unique_id),
                T_START = ref_start,
            )
            et.SubElement(grp, "SCREENSHOT", d)

        grp2 = et.SubElement(root, "SCREENSHOT_GROUPS")
        for g in screenshot_groups:
            d = dict(
                ID=str(a.unique_id),
                NAME = str(g.name)
            )
            elem = et.SubElement(grp2, "SCREENSHOT_GROUP", d)
            for s in g.screenshots:
                d = dict(
                    ID = str(s.unique_id)
                )
                et.SubElement(elem, "SCREENSHOT_REF", d)

    def add_experiment(self, root, experiment: Experiment):
        d = dict(
            NAME = experiment.name,
            ID = str(experiment.unique_id)
        )
        grp = et.SubElement(root, "EXPERIMENT", d)
        grp_c = et.SubElement(grp, "CLASSIFICATION_OBJECTS")
        for t in experiment.get_classification_objects_plain():
            # t = ClassificationObject()
            # If this is a root object we set the ID to -1
            parent_id = -1

            if t.parent.unique_id != experiment.unique_id:
                parent_id = t.parent.unique_id

            d = dict(
                NAME = t.name,
                ID = str(t.unique_id),
                PARENT = str(parent_id),

            )
            elem = et.SubElement(grp_c, "CLASSIFICATION_OBJECT", d)
            for tgt in t.target_container:
                et.SubElement(elem, "TARGET", ID = str(tgt.unique_id))

        grp_v = et.SubElement(grp, "VOCABULARIES")
        for v in experiment.get_vocabularies():
            d = dict(
                NAME=v.name,
                ID=str(v.unique_id),
                CATEGORY = v.category,
                INFO_URL = v.info_url
            )
            elem = et.SubElement(grp_v, "VOCABULARY", d)
            for word in v.words_plain:
                et.SubElement(elem, "VOCABULARY_WORD", ID=str(word.unique_id), NAME = word.name, INFO_URL = word.info_url)

        kwgrp = et.SubElement(grp, "KEYWORDS")
        for t in experiment.get_unique_keywords():
            d = dict(
                WORD_ID = str(t.word_obj.unique_id),
                CLASSIFICATION_OBJECT_ID = str(t.class_obj.unique_id),
                ID=str(t.unique_id)
            )
            et.SubElement(kwgrp, "KEYWORD", d)

        results = et.SubElement(grp, "CLASSIFICATION")
        for r in experiment.classification_results:
            d = dict(
                TARGET_ID=str(r[0].unique_id),
                KEYWORD_ID=str(r[1].unique_id),
            )
            et.SubElement(results, "KEYWORD", d)

    def add_external_media(self, root, media_objects, in_path, out_path):
        grp = et.SubElement(root, "EXTERNAL_MEDIA_OBJECTS")
        for a in media_objects:
            path = os.path.split(a[0].file_path)[1]
            d = dict(
                ID=str(a[0].unique_id),
                PATH = str(a[0].file_path),
                TARGET_ID = str(a[1])
            )
            et.SubElement(grp, "EXTERNAL_MEDIA", d)
            copy2(a[0].file_path, out_path + path)

    def add_analysis(self, root, analyses, out_path, in_path, export_analysis_objects = True):
        grp = et.SubElement(root, "ANALYSES")
        for a in analyses:
            # a = ColormetryAnalysis()
            path = str(a.unique_id)
            if isinstance(a, ColormetryAnalysis):
                if not export_analysis_objects:
                    path = "No Export"
                else:
                    path += ".npz"
                d = dict(
                    ID=str(a.unique_id),
                    NAME = a.name,
                    PATH = path,
                )
                et.SubElement(grp, "COLORIMETRY_ANALSIS", d)
                if path != "No Export":
                    copy2(in_path +"/" + path, out_path + path)
            elif isinstance(a, IAnalysisJobAnalysis):
                ser_type = eval(a.analysis_job_class)().serialization_type()
                if ser_type == DataSerialization.JSON:
                    if not export_analysis_objects:
                        path = "No Export"
                    else:
                        path += ".json"
                        # data_string = eval(a.analysis_job_class)().to_json(a.get_adata())
                        data_string = str(a.analysis_job_class)
                        with open(out_path + path, "w") as f:
                            f.write(data_string)

                elif ser_type == DataSerialization.MASKS:
                    if not export_analysis_objects:
                        path = "No Export"
                    else:
                        path += ".png"
                        cv2.imwrite(out_path + path, a.get_adata()['mask'])
                target_c_obj = a.target_classification_object
                if target_c_obj is None:
                    target_c_obj = str(-1)
                else:
                    target_c_obj = target_c_obj.unique_id
                d = dict(
                    ID=str(a.unique_id),
                    NAME=a.analysis_job_class,
                    PATH=path,
                    TYPE=ser_type.name,
                    CLASSIFICATION_OBJECT_REF=target_c_obj
                )
                et.SubElement(grp, "JOB_ANALYSIS", d)

    def xsd_element(self, p, name):
        return et.SubElement(p, "xsd:element", name=name)

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = et.tostring(elem, 'utf-8')
        reparsed = md.parseString(rough_string)
        return reparsed.toprettyxml(indent="/t")

    def export(self, project: VIANProject, out_path, export_analysis_objects = True):

        root = self.build_document()
        self.build_header(root, project, project.movie_descriptor)
        external_media = []

        if not os.path.isdir(out_path):
            os.mkdir(os.path.abspath(out_path))

        time_mapping = [[],[]] # list of IDS and TIME
        for s in project.segmentation:
            self.add_segmentation(root, s, time_mapping, external_media)

        for a in project.annotation_layers:
            self.add_annotation(root, a, time_mapping, external_media)

        self.add_screenshots(root, project.screenshots, project.screenshot_groups, time_mapping)

        for e in project.experiments:
            self.add_experiment(root, e)

        self.add_external_media(root, external_media, project.data_dir, out_path)

        self.add_analysis(root, project.analysis, out_path, project.data_dir, export_analysis_objects)

        self.add_time_slots(root, time_mapping)
        tree = et.ElementTree(root)

        with open(out_path + "out.xml", "w") as f:
            rough_string = et.tostring(root, 'utf-8')
            reparsed = md.parseString(rough_string)
            f.write(reparsed.toprettyxml())

    #endregion

    #region IMPORT
    def parse_header(self, project:VIANProject, elem:et.Element):
        project.name = elem.get('PROJECT_NAME')
        md_elem = elem.find("MEDIA_DESCRIPTOR")
        project.movie_descriptor.set_movie_path(md_elem.get("MEDIA_URL"))

    def parse_time_mapping(self, elem:et.Element):
        times = []
        names = []
        for c in elem.iter("TIME_SLOT"):
            times.append(int(c.get("TIME_VALUE")))
            names.append(str(c.get("TIME_SLOT_ID")))
        return (times, names)

    def get_time_ms(self, mapping, id_):
        if id_ in mapping[1]:
            return mapping[0][mapping[1].index(id_)]
        else:
            raise Exception("Timestamp not in List")

    def parse_segmentation(self, project:VIANProject, elem:et.Element, time_mapping):
        segm = Segmentation(elem.get("NAME"))
        segm.unique_id = int(elem.get("ID"))
        project.add_segmentation(segm)
        for c in elem.iter("SEGMENT"):
            segment = Segment(start = self.get_time_ms(time_mapping, c.get("T_START")),
                              end=self.get_time_ms(time_mapping, c.get("T_END")),
                              annotation_body= c.get("BODY"))
            segm.unique_id = int(c.get("ID"))
            segm.add_segment(segment)

    def parse_annotation(self, project:VIANProject, elem:et.Element, time_mapping):
        lay = AnnotationLayer(elem.get("NAME"))
        lay.unique_id = int(elem.get("ID"))
        project.add_annotation_layer(lay)
        for c in elem.iter("VISUAL_ANNOTATION"):
            size = c.get("SIZE").replace("[", "").replace("]", "").split(",")
            size = (float(size[0]), float(size[1]))

            pos = c.get("POS").replace("[", "").replace("]", "").split(",")
            pos = (float(pos[0]), float(pos[1]))
            ann = Annotation(t_start = self.get_time_ms(time_mapping, c.get("T_START")),
                             t_end=self.get_time_ms(time_mapping, c.get("T_END")),
                             text = c.get("TEXT"),
                             a_type = eval(c.get("A_TYPE")),
                             size = size, orig_position = pos, resource_path=c.get("RESSOURCE_PATH"))

            ann.unique_id = int(c.get("ID"))
            lay.add_annotation(ann)

    def import_(self, path, project = None):
        with open(path, "r") as f:
            text = f.read()
        if text is None:
            return

        tree = et.fromstring(text)
        for c in tree:
            print(c.tag, c.attrib)

        mapping = self.parse_time_mapping(tree.find("TIMER_ORDER"))

        # self.parse_header(project, tree.find("HEADER"))
        for s in tree.findall("SEGMENTATION"):
            self.parse_segmentation(project, s, mapping)
        for a in tree.findall("ANNOTATION_LAYER"):
            self.parse_annotation(project, a, mapping)
        pass

if __name__ == '__main__':
    from core.data.headless import *
    project, mw = load_project_headless("C:/Users/Gaudenz/Desktop/vian_demo/project/107_1_1_Leave Her to Heaven_1945/107_1_1_Leave Her to Heaven_1945.eext")
    GenericXMLDevice().export(project, "C:/Users/Gaudenz/Desktop/vian_demo/export/", False)
    # project = VIANProject(HeadlessMainWindow())
    # GenericXMLDevice().import_("../../../test/out.xml", project)
