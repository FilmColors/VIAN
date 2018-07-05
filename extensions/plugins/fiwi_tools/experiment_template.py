import os
import csv
import json
from core.container.project import EXPERIMENT, VIANProject
from core.container.experiment import Vocabulary, VocabularyWord, ClassificationObject, Experiment
from core.data.plugin import GAPlugin, GAPLUGIN_WNDTYPE_MAINWINDOW
from core.gui.ewidgetbase import *
from core.analysis.analysis_import import *
from core.analysis.deep_learning.labels import *
# TODO Implement the Plugin
class FiwiGlossary2Template(GAPlugin):
    def __init__(self, main_window):
        super(FiwiGlossary2Template, self).__init__(main_window)
        self.plugin_name = "GlossaryDB to VIANTemplate"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = FiwiGlossary2TemplateDialog(self.main_window)
        wnd.show()


class FiwiGlossary2TemplateDialog(EDialogWidget):
    def __init__(self, main_window):
        super(FiwiGlossary2TemplateDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("extensions/plugins/fiwi_tools/gui/fiwi_glossary_evaluation.ui")
        uic.loadUi(path, self)
        self.btn_Glossary.clicked.connect(self.on_browse_gl)
        self.btn_Template.clicked.connect(self.on_browse_template)
        self.btn_Vocabulary.clicked.connect(self.on_browse_out)

        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.close)

    def on_ok(self):
        try:
            if os.path.isfile(self.lineEdit_Template.text()) and os.path.isfile(self.lineEdit_Glossary.text()) and os.path.isfile(self.lineEdit_Result.text()):
                exp_dir = None
                if self.lineEdit_Vocabulary.text() != "":
                    glossary_to_template(self.lineEdit_Glossary.text(),self.lineEdit_Template.text(), exp_dir)
        except Exception as e:
            print(e)

    def on_browse_template(self):
        try:
            file = QFileDialog.getSaveFileName(filter="*.viant")[0]
            self.lineEdit_Template.setText(file)
        except:
            pass

    def on_browse_gl(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.lineEdit_Glossary.setText(file)
        except:
            pass

    def on_browse_out(self):
        try:
            file = QFileDialog.getExistingDirectory()
            self.lineEdit_Vocabulary.setText(file)
        except:
            pass


def create_vocabulary(name, category = ""):
    new = Vocabulary(name)
    new.category = category
    return new


def glossary_to_template(glossary_path, template_path, export_voc_dir = None):
    """
    Parses the GlossaryDB CSV and creates a custom experiment and VIANTemplate from the given data. 
    :param glossary_path: 
    :param template_path: 
    :param export_voc_dir: 
    :return: 
    """
    # Parse the Glossary
    glossary_words = []
    glossary_ids = []
    glossary_categories = []
    glossary_voc_names = []
    glossary_mapping_strings = []
    glossary_omit = []

    # Read all lines of the CSV File and get the glossary values
    with open(glossary_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter = 0
        for r in reader:
            if counter == 0:
                idx_word = r.index("Term_EN")
                idx_id = r.index("Glossar ID")
                idx_column = r.index("Register")
                idx_voc_name = r.index("Field")
                idx_mapping = r.index("exp Field")
                idx_omit = r.index("Disregard")
            else:
                word = r[idx_word]
                word = word.strip()
                word = word.replace("’", "")
                word = word.replace("/", "")
                word = word.replace(" ", "_")
                word = word.replace("-", "_")
                glossary_words.append(word)
                glossary_ids.append(int(r[idx_id]))
                glossary_categories.append(r[idx_column])
                glossary_voc_names.append(r[idx_voc_name])
                glossary_mapping_strings.append(r[idx_mapping])
                if "yes" in r[idx_omit]:
                    glossary_omit.append(True)
                else:
                    glossary_omit.append(False)

            counter += 1

    # We create a dummy object to create our container objects subsequently
    prj = VIANProject("Dummy")
    prj.inhibit_dispatch = True
    exp = prj.create_experiment()
    exp.name = "ERC Advanced Grant FilmColors"

    # Adding the Main Segmentation
    segm = prj.create_segmentation("Main Segmentation")

    # Create the Classification Object Tree
    glob = exp.create_class_object("Global", exp)
    glob.set_dataset(DATASET_NAME_ADE20K)
    for lbl in ADE20K: glob.add_dataset_label(lbl.value)

    fg = exp.create_class_object("Foreground", exp)
    fg.set_dataset(DATASET_NAME_ADE20K)
    fg.add_dataset_label(ADE20K.person_lbl.value)

    bg = exp.create_class_object("Background", exp)
    bg.set_dataset(DATASET_NAME_ADE20K)
    for lbl in ADE20K:
        if lbl != ADE20K.person_lbl:
            bg.add_dataset_label(lbl.value)

    intert = exp.create_class_object("Intertitle", exp)
    env = exp.create_class_object("Environment", exp)
    light = exp.create_class_object("Lighting", exp)

    p_fem = exp.create_class_object("Female Protagonist", fg)
    p_mal = exp.create_class_object("Male Protagonist", fg)
    s_fem = exp.create_class_object("Female Support", fg)
    s_mal = exp.create_class_object("Male Support", fg)

    # Connect the Main Segmentation as Target container for all Created Classification Objects
    for cobj in exp.get_classification_objects_plain():
        cobj.target_container.append(segm)

    # Create all vocabularies
    existing_voc_names = []
    vocabularies = []
    voc_targets = []
    keyword_ids = []
    for i in range(len(glossary_words)):
        if not glossary_omit[i] == True:
            # if i > 1250:
            #     print(glossary_voc_names[i])
            if glossary_voc_names[i] not in existing_voc_names:
                target_voc = create_vocabulary(glossary_voc_names[i], glossary_categories[i])
                vocabularies.append(target_voc)
                existing_voc_names.append(target_voc.name)
                voc_targets.append(glossary_mapping_strings[i])
                keyword_ids.append([glossary_ids[i]])
            else:
                idx = existing_voc_names.index(glossary_voc_names[i])
                target_voc = vocabularies[idx]
                keyword_ids[idx].append(glossary_ids[i])
            target_voc.create_word(glossary_words[i], dispatch=False)

    # MERGE Vocabularies that are exactly the same
    voc_mapping = []
    keyword_ids_merged = []
    voc_merged = []
    print("--- ALL VOCABULARIES --")
    for i, v in enumerate(vocabularies):
        equal_voc = None
        # print(v.name)
        # Find an equal existing vocabulary in the final list
        for j, y in enumerate(voc_merged):
            # Omit Significance
            if "significance" in v.name.lower():
                break

            if set([n.name for n in v.words_plain]) == set([q.name for q in y.words_plain]):
                equal_voc = y
                if len(v.words_plain) != len(y.words_plain):
                    print([n.name for n in v.words_plain])
                    print([q.name for q in y.words_plain])
                break

        if equal_voc is None:
            voc_merged.append(v)
            voc_mapping.append([voc_targets[i].lower()])
            keyword_ids_merged.append([[x for _,x in sorted(zip([w.name for w in v.words_plain], keyword_ids[i]))]])
        else:
            idx = voc_merged.index(equal_voc)
            if voc_targets[i].lower() not in voc_mapping[idx]:
                voc_mapping[idx].append(voc_targets[i].lower())
                keyword_ids_merged[idx].append([x for _,x in sorted(zip([w.name for w in v.words_plain], keyword_ids[i]))])

        # print("#################")
        # for i, v in enumerate(voc_merged):
        #     for j, t in enumerate(voc_mapping[i]):
        #         print(len(v.words_plain) == len(keyword_ids_merged[i][j]), t, v.name)

    print("#####################")
    # Do some manual renaming
    for i, v in enumerate(voc_merged):
        if "Significance" in v.name:
            continue
        if "Hue" in v.name:
            v.name = "Hues"
        elif "Textures" in v.name:
            v.name = "Textures"
        elif "Visual Complexity" in v.name:
            v.name = "Significance"
        elif "Character Movement" in v.name:
            v.name = "Movement"
        elif "Surfaces" in v.name:
            v.name = "Surfaces"

    for i, v in enumerate(voc_merged):
        for j, t in enumerate(voc_mapping[i]):
            print(len(v.words_plain) == len(keyword_ids_merged[i][j]), t, v.name)
    # Add the final list of Vocabularies to the Project and
    # Connect them to the Classification Objects
    for i, v in enumerate(voc_merged):
        print(v.name)

        proj_voc = prj.create_vocabulary(v.name)
        proj_voc.category = v.category

        for w in sorted(v.words_plain, key=lambda x:x.name):
            proj_voc.create_word(w.name, w.parent)
        v = proj_voc

        # Fint the correct classification Object
        for j, t in enumerate(voc_mapping[i]):
            if "female_protagonist" in t:
                p_fem.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "female_support" in t:
                s_fem.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "male_protagonist" in t:
                p_mal.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "male_support" in t:
                s_mal.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "intertitle" in t:
                intert.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "character" in t or "foreground" in t:
                fg.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "objects" in t or "background" in t:
                bg.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "environment" in t:
                env.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            elif "lighting" in t:
                light.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

            else:
                glob.add_vocabulary(v, external_ids=keyword_ids_merged[i][j])

    for c in exp.get_classification_objects_plain():
        print("####", c.name, "####")
        for v in c.get_vocabularies():
            print("---", v.name)

        print("")
    to_count = []
    for x in glossary_omit:
        if x == False:
            to_count.append(x)
    print(len(to_count))
    print(len(exp.get_unique_keywords()))

    # Add Analyses
    sem_seg_params = dict(model="ADE20K", resolution=50)
    palette_params = dict(resolution=50)
    feature_params = dict(resolution=50)
    exp.add_analysis_to_pipeline("Fg/Bg Segmentation", SemanticSegmentationAnalysis, sem_seg_params)

    exp.add_analysis_to_pipeline("ColorPalette FG", ColorPaletteAnalysis, palette_params, fg)
    exp.add_analysis_to_pipeline("ColorPalette BG", ColorPaletteAnalysis, palette_params, bg)
    exp.add_analysis_to_pipeline("ColorPalette GLOB", ColorPaletteAnalysis, palette_params, glob)

    exp.add_analysis_to_pipeline("ColorPalette FG", ColorFeatureAnalysis, feature_params, fg)
    exp.add_analysis_to_pipeline("ColorPalette BG", ColorFeatureAnalysis, feature_params, bg)
    exp.add_analysis_to_pipeline("ColorPalette GLOB", ColorFeatureAnalysis, feature_params, glob)

    # Export the Vocabularies if the path is set
    if export_voc_dir is not None:
        for v in exp.get_vocabularies():
            v.export_vocabulary(os.path.join(export_voc_dir, v.name + ".json"))

    template = prj.get_template(True, True, False, False, True)

    if ".viant" not in template_path:
        template_path += ".viant"

    with open(template_path, "w") as f:
        json.dump(template, f)

    prj.get_template()


if __name__ == '__main__':
    gl_path = "E:\Programming\Datasets\FilmColors\PIPELINE\_input/GlossaryDB_WordCount.csv"
    voc_export = "C:/Users/Gaudenz Halter/Documents/VIAN/vocabularies"
    template_path = "C:/Users/Gaudenz Halter/Documents/VIAN/templates/ERC_FilmColors.viant"
    glossary_to_template("E:/Programming/Git/filmpalette/input/datasets/GlossaryDB_WordCount.csv", template_path, voc_export)
