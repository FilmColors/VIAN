import os
import csv
import json
from core.data.containers import EXPERIMENT, Experiment, Vocabulary, VocabularyWord, ClassificationObject, VIANProject
from core.data.plugin import GAPlugin, GAPLUGIN_WNDTYPE_MAINWINDOW
from core.gui.ewidgetbase import *

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
        self.gl_path = ""
        self.out_path = ""
        self.voc_dir = ""


    def on_ok(self):
        try:
            if os.path.isfile(self.line_gl.text()) and self.line_out.text() != "":
                out_dir = None
                if self.line_voc_dir.text() != "":
                    if os.path.isdir(self.line_voc.text()):
                        out_dir = self.line_voc.text()
                glossary_to_template(self.line_gl.text(), template_path=self.line_out.text(), out_dir)
        except:
            pass

    def on_browse_db(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.db_path = file
                self.line_db.setText(file)
        except:
            pass

    def on_browse_gl(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.gl_path = file
                self.line_gl.setText(file)
        except:
            pass

    def on_browse_out(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.out_path = file
                self.line_out.setText(file)
        except:
            pass


def create_vocabulary(name, category = ""):
    new = Vocabulary(name)
    new.category = category
    return new


def glossary_to_template(glossary_path, template_path, export_voc_dir = None):
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
                glossary_ids.append(r[idx_id])
                glossary_categories.append(r[idx_column])
                glossary_voc_names.append(r[idx_voc_name])
                glossary_mapping_strings.append(r[idx_mapping])
                if "yes" in r[idx_omit]:
                    glossary_omit.append(True)
                else:
                    glossary_omit.append(False)

                if "mind" in word:
                    print(word)
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
    fg = exp.create_class_object("Foreground", exp)
    bg = exp.create_class_object("Background", exp)
    intert = exp.create_class_object("Intertitle", exp)

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
            if glossary_voc_names[i] not in existing_voc_names:
                target_voc = create_vocabulary(glossary_voc_names[i], glossary_categories[i])
                vocabularies.append(target_voc)
                existing_voc_names.append(target_voc.name)
                voc_targets.append(glossary_mapping_strings[i])
            else:
                target_voc = vocabularies[existing_voc_names.index(glossary_voc_names[i])]
            target_voc.create_word(glossary_words[i], dispatch=False)
            keyword_ids.append(glossary_ids[i])

    # MERGE Vocabularies that are exactly the same
    voc_mapping = []
    keyword_ids_merged = []
    voc_merged = []
    for i, v in enumerate(vocabularies):
        equal_voc = None

        # Find an equal existing vocabulary in the final list
        for j, y in enumerate(voc_merged):
            # Omit Significance
            if "significance" in v.name.lower():
                break

            if set([n.name for n in v.words_plain]) == set([n.name for n in y.words_plain]):
                equal_voc = y
                break

        if equal_voc is None:
            voc_merged.append(v)
            voc_mapping.append([voc_targets[i].lower()])
            keyword_ids_merged.append([keyword_ids[i]])
        else:
            idx = voc_merged.index(equal_voc)
            if voc_targets[i].lower() not in voc_mapping[idx]:
                voc_mapping[idx].append(voc_targets[i].lower())
                keyword_ids_merged.append(keyword_ids[i])

    # Do some manual renaming
    for i, v in enumerate(voc_merged):
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
        # print(v.name.ljust(50), voc_mapping[i])#, voc_mapping[i], [n.name for n in v.words_plain])

    # Add the final list of Vocabularies to the Project and
    # Connect them to the Classification Objects
    for i, v in enumerate(voc_merged):
        proj_voc = prj.create_vocabulary(v.name)
        proj_voc.category = v.category

        for w in v.words_plain:
            proj_voc.create_word(w.name, w.parent)
        v = proj_voc

        for j, t in enumerate(voc_mapping[i]):
            if "female_protagonist" in t:
                p_fem.add_vocabulary(v)

            elif "female_support" in t:
                s_fem.add_vocabulary(v)

            elif "male_protagonist" in t:
                p_mal.add_vocabulary(v)

            elif "male_support" in t:
                s_mal.add_vocabulary(v)

            elif "intertitle" in t:
                intert.add_vocabulary(v)

            elif "character" in t or "foreground" in t:
                fg.add_vocabulary(v)

            elif "environment" in t or "objects" in t:
                bg.add_vocabulary(v)

            else:
                glob.add_vocabulary(v)

    for c in exp.get_classification_objects_plain():
        print("####", c.name, "####")
        for v in c.get_vocabularies():
            print("---", v.name)

        print("")

    # Export the Vocabularies if the path is set
    if export_voc_dir is not None:
        for v in exp.get_vocabularies():
            v.export_vocabulary(os.path.join(export_voc_dir, v.name + ".json"))

    # Set the FIWI ID to the notes in all unique keywords as hidden info
    # print(len(exp.get_unique_keywords()))
    # for ukw in exp.get_unique_keywords():
    #     print(ukw.get_name(), ukw.notes)

    template = prj.get_template(True, True, False, False, True)

    if ".viant" not in template_path:
        template_path += ".viant"

    with open(template_path, "w") as f:
        json.dump(template, f)


    prj.get_template()

if __name__ == '__main__':

    gl_path = "E:/Programming/Git/filmpalette/input/datasets/GlossaryDB_WordCount.csv"
    voc_export = "C:/Users/Gaudenz Halter/Documents/VIAN/vocabularies"
    template_path = "C:/Users/Gaudenz Halter/Documents/VIAN/templates/ERC_FilmColors.viant"
    glossary_to_template("E:/Programming/Git/filmpalette/input/datasets/GlossaryDB_WordCount.csv", template_path, voc_export)