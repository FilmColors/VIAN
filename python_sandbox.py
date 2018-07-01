import xml.etree.cElementTree as et
import xml.dom.minidom as md
from core.container.segmentation import *
from core.container.analysis import *
from core.container.project import *
from core.container.experiment import *
from core.container.screenshot import *
from core.container.annotation import *
from core.container.media_objects import *
from core.data.headless import *

from core.data.computation import images_to_movie

def build_document(author = "author", format = "2.8", version = "2.8"):
    root = et.Element("ANNOTATION_DOCUMENT")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:noNamespaceSchemaLocation", "http://www.mpi.nl/tools/elan/EAFv2.8.xsd")
    root.set("AUTHOR", author)
    root.set("FORMAT", format)
    root.set("VERSION", version)

    return root


def build_header(root, project:VIANProject, media: MovieDescriptor, time_units = "milliseconds"):
    d = dict(MEDIA_FILE = media.movie_path,
             TIME_UNITS = time_units,
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


def add_time_slots(root, ts):
    grp = et.Element("TIMER_ORDER")
    for i, t in enumerate(ts[0]):
        d = dict(TIME_SLOT_ID = str(ts[1][i]), TIME_VALUE = str(ts[0][i]))
        et.SubElement(grp, "TIME_SLOT", d)
    root.insert(1, grp)
    return grp


def to_time_mapping(mapping, container:ITimeRange):
    a = container.get_start()
    b = container.get_end()
    if a not in mapping[0]:
        mapping[0].append(a)
        mapping[1].append("ts" + str(len(mapping[1])))
    if b not in mapping[0]:
        mapping[0].append(b)
        mapping[1].append("ts" + str(len(mapping[1])))
    return (mapping[1][mapping[0].index(a)], mapping[1][mapping[0].index(b)])


def add_segmentation(root, seg:Segmentation, time_mapping, external_media):
    grp = et.SubElement(root, "SEGMENTATION", NAME=seg.name, ID = str(seg.unique_id))
    for s in seg.segments:
        # s = Segment()
        (ref_start, ref_end) = to_time_mapping(time_mapping, s)
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


def add_annotation(root, lay:AnnotationLayer, time_mapping, external_media):
    grp = et.SubElement(root, "ANNOTATION_LAYER", NAME=lay.name, ID = str(lay.unique_id))
    for a in lay.annotations:
        # a = Annotation()
        (ref_start, ref_end) = to_time_mapping(time_mapping, a)
        d = dict(
            ID = str(a.unique_id),
            T_START = ref_start,
            T_END = ref_end,
            A_TYPE = str(a.a_type),
            POS = str(a.orig_position),
            SIZE = str(a.size),
            TEXT = str(a.text),
            RESSOURCE_PATH = str(a.resource_path),
            COLOR = str(a.color)
        )
        et.SubElement(grp, "VISUAL_ANNOTATION", d)

        for ext in a.media_objects:
            external_media.append([ext.unique_id, ext.file_path, s.unique_id])
    return grp


def add_screenshots(root, screenshots: Screenshot, screenshot_groups: List[ScreenshotGroup], time_mapping):
    grp = et.SubElement(root, "SCREENSHOTS")
    for a in screenshots:
        # a = Screenshot()
        (ref_start, ref_end) = to_time_mapping(time_mapping, a)
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
            et.SubElement(elem, "SCREENSHOT", d)


def add_experiment(root, experiment: Experiment):
    grp = et.SubElement(root, "EXPERIMENTS")
    for t in experiment.classification_objects:
        # t = ClassificationObject()
        d = dict(
            NAME = t.name,
            ID = str(t.unique_id),
        )
        elem = et.SubElement(grp, "CLASSIFICATION_OBJECT", d)
        for tgt in t.target_container:
            et.SubElement(elem, "TARGET", ID = str(tgt.unique_id))

    for v in experiment.get_vocabularies():
        d = dict(
            NAME=v.name,
            ID=str(v.unique_id),
            CATEGORY = v.category,
            INFO_URL = v.info_url
        )
        elem = et.SubElement(grp, "VOCABULARY", d)
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


def add_external_media(root, media_objects, in_path, out_path):
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


def add_analysis(root, analyses, out_path, in_path):
    grp = et.SubElement(root, "ANALYSES")
    for a in analyses:
        # a = ColormetryAnalysis()
        path = str(a.unique_id) + ".npz"
        if isinstance(a, ColormetryAnalysis):
            d = dict(
                ID=str(a.unique_id),
                NAME = a.name,
                PATH = path
            )
            et.SubElement(grp, "COLORIMETRY_ANALSIS", d)
            copy2(in_path +"/" + path, out_path + path)
        elif isinstance(a, IAnalysisJobAnalysis):
            d = dict(
                ID=str(a.unique_id),
                NAME=a.analysis_job_class,
                PATH=path
            )
            et.SubElement(grp, "JOB_ANALYSIS", d)
            copy2(in_path + "/" + path, out_path + path)


def xsd_element(p, name):
    return et.SubElement(p, "xsd:element", name=name)


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = et.tostring(elem, 'utf-8')
    reparsed = md.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")


def export(project: VIANProject, out_path):

    root = build_document()
    build_header(root, project, project.movie_descriptor)
    external_media = []

    if not os.path.isdir(out_path):
        os.mkdir(os.path.abspath(out_path))

    time_mapping = [[],[]] # list of IDS and TIME
    for s in project.segmentation:
        add_segmentation(root, s, time_mapping, external_media)

    for a in project.annotation_layers:
        add_annotation(root, a, time_mapping, external_media)

    add_screenshots(root, project.screenshots, project.screenshot_groups, time_mapping)

    for e in project.experiments:
        add_experiment(root, e)

    add_external_media(root, external_media, project.data_dir, out_path)

    add_analysis(root, project.analysis, out_path, project.data_dir)

    add_time_slots(root, time_mapping)
    tree = et.ElementTree(root)

    with open(out_path + "out.xml", "w") as f:
        f.write(prettify(root))
#
#
# project = load_project_headless("C:/Users/Gaudenz Halter/Documents/VIAN/3774_1_1_Blade_Runner_1900_DVD/3774_1_1_Blade_Runner_1900_DVD.eext")
# export(project, "test/")

root = "E:\\Programming\\Datasets\\LIP2\\train_images\\"
paths = [
    root + "77_471474.jpg",
    root + "113_1207747.jpg",
    root + "136_500146.jpg",
    root + "165_443487.jpg",
]
imgs = []
for p in paths:
    img = cv2.imread(p)
    imgs.append(img)
    cv2.imshow("wind", img)
    cv2.waitKey(100)
images_to_movie(imgs, "test.avi",fps=20.0)