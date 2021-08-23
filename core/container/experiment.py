import json
import time
import typing
from uuid import uuid4
import numpy as np

from typing import List, Tuple

from core.data.log import log_warning, log_debug, log_info, log_error
from core.container.analysis import AnalysisContainer
from core.data.enums import VOCABULARY, VOCABULARY_WORD, CLASSIFICATION_OBJECT, EXPERIMENT, SEGMENTATION, \
    ANNOTATION_LAYER, SCREENSHOT_GROUP, SEGMENT
from .container_interfaces import BaseProjectEntity, IHasName, IClassifiable, deprecation_serialization
from .hdf5_manager import get_analysis_by_name

from core.analysis.deep_learning.labels import LIPLabels

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from functools import partial


def delete_even_if_connected_msgbox(mode="word"):
    """
    Shows a Question dialog if a given keyword should be removed even if it has already been 
    used in the classification.

    :param mode: "voc" or "word" 
    :return: an QMessageBox.Answer
    """
    if mode == "word":
        text = 'This Keyword has already been connected used to classify, removing it from the vocabulary ' + \
               'also removes it from the classification. Do you want to remove it anyway?'
    else:
        text = 'This Vocabulary contains keywords which have already been used to classify, removing the vocabulary ' + \
               'also removes the classification already done. Do you want to remove it anyway?'

    answer = QMessageBox.question(None, "Warning", text)
    return answer


class Vocabulary(BaseProjectEntity, IHasName):
    """
    :var str name: The Name of the Vocabulary
    :var str comment: This is a generic field to put a description into about the Voc.
    :var str info_url: A URL to a description of this vocabulary
    :var List[VocabularyWord] words: The words in a hierarchical form.
    :var List[VocabularyWord] words_plain: A List of All VocabularyWords that are in the Vocabulary
    :var string category: The Category it belongs to
    """
    onVocabularyChanged = pyqtSignal(object)
    onVocabularyWordAdded = pyqtSignal(object)
    onVocabularyWordRemoved = pyqtSignal(object)

    def __init__(self, name="", unique_id=-1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        self.name = name
        self.comment = ""
        self.info_url = ""
        self.words = []
        self.words_plain = [] # type: List[VocabularyWord]

        self.image_urls = []
        self.category = "default"

        self.is_visible = True
        self.is_builtin = False

        self._path = ""

    def create_word(self, name, parent_word = None, unique_id = -1, dispatch = True, rename_dups = False):
        """
        Creates a new word in the vocabulary.

        :param str name: the name of word
        :param Vocabulary|VocabularyWord parent_word:
        :param str unique_id:
        :param bool dispatch: Trigger an update event in the VIAN editor.
        :param bool rename_dups: If True, the words are renamed if a duplicate exists, if False the duplicate is not added
        :return VocabularyWord|None: the created word
        """

        tname = name
        i = 0
        if rename_dups:
            while tname in [w.name for w in self.words_plain]:
                tname = name + f"_{i}"
                i += 1
            name = tname
        elif name in [w.name for w in self.words_plain]:
            log_warning("Duplicate Word", name)
            return

        word = VocabularyWord(name, vocabulary=self, unique_id=unique_id)
        self.add_word(word, parent_word, dispatch)
        return word

    def add_word(self, word, parent_word = None, dispatch = True):
        """
        Adds a word to the vocabulary.

        :param VocabularyWord word: the Word object to add
        :param Vocabulary|VocabularyWord parent_word: the parent Word, either as String or Word Object
        :param bool dispatch: Trigger an update event in the VIAN editor.
        :return: None
        """
        if parent_word is None or isinstance(parent_word, Vocabulary):
            word.parent = self
            self.words.append(word)
            self.words_plain.append(word)
            word.set_project(self.project)
        else:
            if isinstance(parent_word, str):
                parent = self.get_word_by_name(parent_word)
            else:
                parent = parent_word

            if parent is not None:
                word.parent = parent
                parent.add_children(word)
                self.words_plain.append(word)
                word.set_project(self.project)

        if dispatch:
            self.dispatch_on_changed(item=self)

        self.onVocabularyWordAdded.emit(word)
        self.onVocabularyChanged.emit(self)

    def remove_word(self, word, dispatch = True):
        """
        Removes a word from the vocabulary, cleans up all references to this word.

        :param VocabularyWord word:
        :param bool dispatch:
        :return:
        """
        children = []
        word.get_children_plain(children)

        # Remove all unique keywords attached to this VocabularyWord
        word.cleanup_referenced_keywords()

        # Remove all children if necessary
        for w in children:
            self.words_plain.remove(w)

        # If the word is directly attached to the Vocabulary we can simply remove it
        if word in self.words:
            self.words.remove(word)
        else:
            # If the word is a child somewhere deeper in the tree, we have to remove it there.
            if word in word.parent.children:
                word.parent.children.remove(word)

        # Remove it from the words_plain list
        if word in self.words_plain:
            self.words_plain.remove(word)

        # Remove it from the project
        if self.project is not None:
            self.project.remove_from_id_list(word)

        if dispatch:
            self.dispatch_on_changed(item=self)

        self.onVocabularyWordRemoved.emit(word)
        self.onVocabularyChanged.emit(self)

    def get_word_by_name(self, name):
        """
        Searches a word in the vocabulary by name.

        :param str name:
        :return VocabularyWord|None: A vocabulary if existent else None
        """
        for w in self.words_plain:
            if w.name == name:
                return w
        return None

    def get_vocabulary_as_list(self):
        """
        Recursively traverses the complete Vocabulary tree and returns a list words.

        :return List[VocabularyWord]: A list of words.
        """
        result = []
        for w in self.words:
            w.get_children_plain(result)
        return result

    def get_complexity_groups(self):
        return [w.complexity_group for w in self.words]

    def serialize(self) -> dict:
        """
        Returns the entity as json compliant values.

        :return: the entity as json compliant values.
        """

        words = self.words_plain

        voc_data = dict(
            name = self.name,
            category = self.category,
            unique_id = self.unique_id,
            words = [ w.serialize() for w in words ],
            image_urls = self.image_urls,
            comment = self.comment,
            visible = self.is_visible
        )

        return voc_data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.category = serialization['category']

        self.comment = deprecation_serialization(serialization, 'comment', "")

        # Probably we will not need the hierarchy anymore but for the sake of functionality
        # we do a local unique_id to object resolving
        # TODO whe should get rid of the old therausus data structures where words are hierachical trees.
        # todo replace words_plain with words

        hierarchy_mapper = dict()
        hierarchy_mapper[self.unique_id] = self

        for w in serialization['words']:

            # Due to a previous bug, there exist vocabularies with the same unique id.
            # We have already imported one with this unique id, we have to generate new ids for the next.
            # This will be done during the keyword serialization, now, we just collect them and keep it on the project
            # level
            if project is not None and project.get_by_id(w['unique_id']) is not None:
                if "_contains_voc_dups" not in project.meta_data:
                    project.meta_data["_contains_voc_dups"] = dict(has=True, all_vocs = [])
                project.meta_data["_contains_voc_dups"]['all_vocs'].append(self)
                log_warning("ERROR, duplicate UID", self.name, w['name'])

            parent = hierarchy_mapper[w['parent']]
            word = VocabularyWord.deserialize(w, self)
            self.add_word(word, parent_word=parent, dispatch=False)
            hierarchy_mapper[word.unique_id] = word

        self.is_visible = deprecation_serialization(serialization, 'visible', default=True)
        return self

    def export_vocabulary(self, path):
        data = self.serialize()
        with open(path, "w") as f:
            json.dump(data, f)

    def import_vocabulary(self, path = None, project = None, serialization = None):
        if serialization is None:
            with open(path, "r") as f:
                serialization = json.load(f)

        id_replacing_table = dict()

        self.project = project
        self.name = serialization['name']
        self.category = serialization['category']

        old_id = serialization['unique_id']
        new_id = project.create_unique_id()
        self.unique_id = new_id

        id_replacing_table[old_id] = new_id
        try:
            self.comment = serialization['comment']
        except:
            log_warning("No UUID found in this vocabulary", self.name)
            pass

        # Replace all IDs with new one:
        for w in serialization['words']:
            old = w['unique_id']
            new = self.project.create_unique_id()
            id_replacing_table[old] = new

        for w in serialization['words']:
            new_parent = id_replacing_table[w['parent']]
            w['unique_id'] = id_replacing_table[w['unique_id']]

            parent = self.project.get_by_id(new_parent)

            word = VocabularyWord.deserialize(w, self)
            self.add_word(word, parent_word=parent, dispatch=False)

        return self, id_replacing_table

    def update_vocabulary(self, new_voc, compare_by_name = False):
        for attr in VOC_COMPARE_ATTRS:
            if hasattr(self, attr):
                setattr(self, attr, getattr(new_voc, attr))

        words = dict()
        to_remove = []

        if compare_by_name:
            self.project.add_to_id_list(new_voc, self.unique_id)
            self.unique_id = new_voc.unique_id

            for w in new_voc.words_plain:
                words[w.name] = w

            for w in self.words_plain:
                if w.name in words:
                    for attr in WORD_COMPARE_ATTRS:
                        setattr(w, attr, getattr(words[w.name], attr))
                    self.project.add_to_id_list(words[w.name], w.unique_id)

                    w.unique_id = words[w.name].unique_id

                    words.pop(w.name)
                    w.parent = self
                else:
                    to_remove.append(w)

        else:
            words_by_name = dict()
            for w in new_voc.words_plain:
                words[w.unique_id] = w
                words_by_name[w.name] = w

            for w in self.words_plain:
                if w.unique_id in words:
                    for attr in WORD_COMPARE_ATTRS:
                        setattr(w, attr, getattr(words[w.unique_id], attr))
                    words.pop(w.unique_id)
                    w.parent = self
                elif w.name in words_by_name:
                    rpl = words_by_name[w.name]
                    for attr in WORD_COMPARE_ATTRS:
                        setattr(w, attr, getattr(rpl, attr))
                    w.unique_id = rpl.unique_id
                    words.pop(w.unique_id)
                    w.parent = self
                else:
                    to_remove.append(w)

        # TODO
        if "Surface" in self.name or "Texture" in self.name:
            print(self.name)
            print([w.name for w in self.words_plain])
            print("to_remove", [n.name for n in to_remove])
            print("to_add", [n.name for n in words.values()])
            print("\n")

        for w in to_remove:
            self.remove_word(w)
        for w in words.values():
            self.add_word(w)

    def get_type(self):
        return VOCABULARY

    def get_name(self):
        return self.name

    def set_name(self, name):
        base = name
        if self.project is not None:
            counter = 0
            while name in [v.name for v in self.project.vocabularies]:
                counter += 1
                name = base + "_" + str(counter).zfill(2)
        self.name = name
        print("set name", self.sender())
        self.onVocabularyChanged.emit(self)

    def delete(self):
        for w in self.words_plain:
            self.remove_word(w, dispatch=False)
        self.project.remove_vocabulary(self)

    def save_delete(self):
        has_been_used = False
        for w in self.words_plain:
            for k in w.unique_keywords:
                if len(k.tagged_containers) > 0:
                    has_been_used = True
                    break
        if has_been_used:
            answer = delete_even_if_connected_msgbox("voc")
            if answer == QMessageBox.Yes:
                self.delete()
            else:
                return
        else:
            self.delete()


class VocabularyWord(BaseProjectEntity, IHasName):
    """

    :var name: The Name of the Word
    :var comment: An additional field to add some info about it. In the ERC_FILM_COLORS this refers to the glossary ID
    :var info_url: A Url to the description of this Vocabulary
    :var vocabulary: It's parent Vocabulary
    :var parent: The Parent Word
    :var children: The Children Words
    :var connected_items: BaseProjectEntity objects that are connected with it # Obsolete

    """
    onVocabularyWordChanged = pyqtSignal(object)

    def __init__(self, name, vocabulary, parent = None, unique_id=-1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        self.name = name
        self.comment = ""
        self.info_url = ""
        self.vocabulary = vocabulary
        self.parent = parent
        self.children = []
        self.image_urls = []
        self.connected_items = []
        self.unique_keywords = []
        self.organization_group = 0
        self.complexity_lvl = 0
        self.complexity_group = ""

    def _add_referenced_unique_keyword(self, kwd):
        self.unique_keywords.append(kwd)
        kwd.class_obj.onUniqueKeywordsChanged.emit(kwd)

    def _remove_referenced_unique_keyword(self, kwd):
        if kwd in self.unique_keywords:
            self.unique_keywords.remove(kwd)
            kwd.class_obj.onUniqueKeywordsChanged.emit(kwd)

    def set_name(self, name):
        self.name = name
        self.onVocabularyWordChanged.emit(self)

    def add_children(self, children):
        """
        Adds a VocabularyWord or list of as Child.

        :param List[VocabularyWord]|VocabularyWord children:
        :return:
        """
        if isinstance(children, list):
            for c in children:
                self.children.append(c)
                c.parent = self
        else:
            self.children.append(children)

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def get_type(self):
        return VOCABULARY_WORD

    def get_name(self):
        return self.name

    def cleanup_referenced_keywords(self):
        """
        Removes all UniqueKeyword from unique_keywords, which do no longer exist.

        :return:
        """
        to_remove = []
        for ukw in self.unique_keywords:
            ukw.class_obj.unique_keywords = [x for x in ukw.class_obj.unique_keywords if not x.word_obj == self]
            to_remove.append(ukw)
        self.unique_keywords = [x for x in self.unique_keywords if x not in to_remove]

    def delete(self):
        self.project.remove_from_id_list(self)
        self.vocabulary.remove_word(self)

    def save_delete(self):
        has_been_used = False
        for k in self.unique_keywords:
            if len(k.tagged_containers) > 0:
                has_been_used = True
                break
        if has_been_used:
            answer = delete_even_if_connected_msgbox("word")
            if answer == QMessageBox.Yes:
                self.delete()
            else:
                return
        else:
            self.delete()

    def serialize(self) -> dict:
        return dict(
            name = self.name,
            unique_id = self.unique_id,
            parent = self.parent.unique_id,
            children = [a.unique_id for a in self.children],
            organization_group = self.organization_group,
            complexity_lvl = self.complexity_lvl,
            complexity_group = self.complexity_group,
            image_urls = self.image_urls,
            comment=self.comment
        )

    @staticmethod
    def deserialize(ser, voc):
        self = VocabularyWord(ser['name'], voc, unique_id=ser['unique_id'])
        self.complexity_lvl = deprecation_serialization(ser, 'complexity_lvl', 0, int)
        self.organization_group = deprecation_serialization(ser, 'organization_group', 0, int)
        self.complexity_group = deprecation_serialization(ser, 'complexity_group', "")
        self.image_urls = deprecation_serialization(ser, 'image_urls', [])
        self.comment = deprecation_serialization(ser, "comment")
        return self


class ClassificationObject(BaseProjectEntity, IHasName):
    """
    A ClassificationObject is an Object that one wants to classify by a set of Vocabularies.
    Several ClassificationObjects may form a Tree.

    Example: Say one wants to analyse the Foreground and Background Color of a given Film using his homemade 
    Vocabulary called "ColorVocabulary". 
    
    The ClassificationObjects would therefore be "Foreground" and "Background", both will have "ColorVocabulary".

    :var str name: The Name of this ClassificationObject
    :var Experiment experiment: A reference to the Experiment it belongs to
    :var ClassificationObject|Experiment parent: A Parent Classification Object or an Experiment if it's at the root
    :var List[ClassificationObject] children: A List of Children ClassificationObjects if any
    :var List[Vocabulary] classification_vocabularies: A List of Vocabularies attached to this ClassificationObject
    :var List[UniqueKeyword] unique_keywords: A List of Unique Keywords generated from this ClassificationObjects and its Vocabularies
    :var List[BaseProjectEntity] target_container: A List of Target Containers to classify with this Classification Object
    :var Tuple[str, List[int]] semantic_segmentation_labels: The Semantic Segmentation assigned to it Tuple ("<Name of Dataset>", [Indices of assigned Mask layers])

    """
    # TODO Semantic Segmentation Refactor

    onClassificationObjectChanged = pyqtSignal(object)
    onUniqueKeywordsChanged = pyqtSignal(object)
    onSemanticLabelsChanged = pyqtSignal(object)

    def __init__(self, name, experiment, parent = None, unique_id = -1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        self.name = name
        self.experiment = experiment
        self.parent = parent
        self.children = []
        self.classification_vocabularies = []
        self.unique_keywords = [] # type:List[UniqueKeyword]
        self.target_container = []
        self.semantic_segmentation_labels = ("", [])

    def add_vocabulary(self, voc: Vocabulary, dispatch = True, external_ids = None, keyword_override = None):
        """
        Adds a vocabulary to this classification object and generates the keywords.

        :param Vocabulary voc:
        :param bool dispatch:
        :param list external_ids:
        :param dict[str, UniqueKeyword] keyword_override:
        :return List[UniqueKeyword]::
        """
        if voc not in self.classification_vocabularies:
            self.classification_vocabularies.append(voc)

            keywords = []
            for i, w in enumerate(voc.words_plain):
                keyword = None
                if keyword_override is not None and w.unique_id in keyword_override:
                    keyword = keyword_override[w.unique_id]
                if keyword is None:
                    keyword = UniqueKeyword(self.experiment, voc, w, self, emit_change=False, unique_id=str(uuid4()))
                if external_ids is not None:
                    keyword.external_id = external_ids[i]
                keyword.set_project(self.project)
                self.unique_keywords.append(keyword)
                keywords.append(keyword)
            self.onUniqueKeywordsChanged.emit(self)

            voc.onVocabularyWordAdded.connect(self.on_vocabulary_word_added)
            voc.onVocabularyWordRemoved.connect(self.on_vocabulary_word_removed)
            print("Vocabulary added", voc.name)
            return keywords
        else:
            #Check if really there are new words in the vocabulary which are not yet added to the keywords.
            keywords = []
            all_words = [w.word_obj for w in self.unique_keywords]
            all_word_uids = [kwd.word_obj.unique_id for kwd in self.unique_keywords]

            for i, w in enumerate(voc.words_plain):
                if w not in all_words and w.unique_id not in all_word_uids:
                    keyword = None
                    if keyword_override is not None and w.unique_id in keyword_override:
                        keyword = keyword_override[w.unique_id]
                    if keyword is None:
                        keyword = UniqueKeyword(self.experiment, voc, w, self)
                    if external_ids is not None:
                        keyword.external_id = external_ids[i]
                    keyword.set_project(self.project)
                    self.unique_keywords.append(keyword)
            for r in self.unique_keywords:
                if r.voc_obj == voc:
                    keywords.append(r)
            self.onUniqueKeywordsChanged.emit(self)
            return keywords

    def on_vocabulary_word_added(self, w:VocabularyWord):
        if w.unique_id not in [kwd.word_obj.unique_id for kwd in self.unique_keywords]:
            keyword = UniqueKeyword(self.experiment, w.vocabulary, w, self)
            self.unique_keywords.append(keyword)
            self.onUniqueKeywordsChanged.emit(self)

    def on_vocabulary_word_removed(self, w:VocabularyWord):
        to_remove = None
        for kwd in self.unique_keywords:
            if kwd.word_obj == w:
                to_remove = kwd
        if to_remove is not None:
            self.unique_keywords.remove(to_remove)
        self.onUniqueKeywordsChanged.emit(self)

    def remove_vocabulary(self, voc):
        if voc not in self.classification_vocabularies:
            return

        self.classification_vocabularies.remove(voc)

        to_delete = [x for x in self.unique_keywords if x.voc_obj == voc]
        self.unique_keywords = [x for x in self.unique_keywords if not x.voc_obj == voc]

        for d in to_delete:
            self.project.remove_from_id_list(d)

        voc.onVocabularyWordAdded.disconnect(self.on_vocabulary_word_added)
        voc.onVocabularyWordRemoved.disconnect(self.on_vocabulary_word_removed)
        print("Vocabulary removed", voc.name)
        self.onUniqueKeywordsChanged.emit(self)

    def get_vocabularies(self):
        return self.classification_vocabularies

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.onClassificationObjectChanged.emit(self)

    def add_child(self, classification_object):
        classification_object.parent = self
        classification_object.set_project(self.project)
        self.children.append(classification_object)

    def remove_child(self, classification_object):
        if classification_object in self.children:
            self.children.remove(classification_object)
            self.project.remove_from_id_list(classification_object)
        else:
            log_warning("Classification Object not found.")

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def set_dataset(self, dataset_name):
        if dataset_name == None:
            self.semantic_segmentation_labels = ("", [])
        else:
            self.semantic_segmentation_labels = (dataset_name, [])
        self.onClassificationObjectChanged.emit(self)

    def add_dataset_label(self, value):
        if value not in self.semantic_segmentation_labels[1]:
            self.semantic_segmentation_labels[1].append(value)
        self.onClassificationObjectChanged.emit(self)

    def remove_dataset_label(self, value):
        if value in self.semantic_segmentation_labels[1]:
            self.semantic_segmentation_labels[1].remove(value)

    def get_type(self):
        return CLASSIFICATION_OBJECT

    def serialize(self):
        if self.semantic_segmentation_labels[0] != "":
            semseg_serialization = dict(model=self.semantic_segmentation_labels[0],
                                        labels=[dict(name=LIPLabels(t).name, label=t) for t in self.semantic_segmentation_labels[1]])
        else:
            semseg_serialization = None

        serialization = dict(
            name=self.name,
            unique_id = self.unique_id,
            parent = self.parent.unique_id,
            classification_vocabularies = [v.unique_id for v in self.classification_vocabularies],
            unique_keywords =  [k.serialize() for k in self.unique_keywords],
            target_container = [k.unique_id for k in self.target_container],
            children = [c.unique_id for c in self.children],
            semantic_segmentation_labels = semseg_serialization
        )

        return serialization

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']

        t = dict()
        for clobj in self.experiment.get_classification_objects_plain():
            t[clobj.unique_id] = clobj
        t[self.experiment.unique_id] = self.experiment
        p = t[serialization['parent']]

        if isinstance(p, ClassificationObject):
            p.add_child(self)
        else:
            p.classification_objects.append(self)
            self.parent = p
            self.set_project(project)

        self.classification_vocabularies = []
        for uid in serialization['classification_vocabularies']:
            voc = project.get_by_id(uid)
            if voc is not None:
                self.classification_vocabularies.append(voc)
                voc.onVocabularyWordAdded.connect(self.on_vocabulary_word_added)
                voc.onVocabularyWordRemoved.connect(self.on_vocabulary_word_removed)
            else:
                # raise Exception("Could not Resolve Vocabulary", uid)
                log_warning("Could not Resolve Vocabulary:", uid)

        self.unique_keywords = []
        # All words which are attached to the Classification Object
        # This is used to remove dangling Keywords, which belong to a vocabulary which is
        # no longer attached to the ClassificationObject
        all_words = dict()

        # Due to an bug in the copying of vocabularies, it can be durin 0.9.3, that
        # copied vocabulary words share the same unique_ids, we thus have to tried to resolve this
        cl_vocs_words = dict()
        for voc in self.classification_vocabularies:
            cl_vocs_words[voc.unique_id] = dict()
            for w in voc.words_plain:
                cl_vocs_words[voc.unique_id][w.unique_id] = w

        for ser in serialization['unique_keywords']:
            try:
                if ser['word_obj'] not in all_words:
                    vocc = cl_vocs_words.get(ser['voc_obj'])
                    if vocc is not None:
                        word_obj = vocc.get(ser["word_obj"])
                    else:
                        # This UniqueKeyword is dangling and should be removed!
                        continue
                    if ser['unique_id'] == "38a326f0-1260-4b66-9aec-df6805cec7ce":
                        print("Hello")
                    ukw = UniqueKeyword(self.experiment).deserialize(ser, project, word_obj)
                    project.add_to_id_list(ukw, ukw.unique_id)
                    self.unique_keywords.append(ukw)
                    all_words[(ser['voc_obj'], ser['word_obj'])] = ukw
                else:
                    ukw = all_words[(ser['voc_obj'], ser['word_obj'])]
                    project.add_to_id_list(ukw, ser['unique_id'])
                    print("Imported Duplicate", ukw.word_obj.name, ukw.voc_obj.name)
            except Exception as e:
                log_error(e, ser['word_obj'], ser)

        # Ensure that all keywords are created,
        # also the ones which have not been in the serialization but the library!
        for v in self.classification_vocabularies:
            self.add_vocabulary(v)

        ts = [project.get_by_id(uid) for uid in serialization['target_container']]

        for t in ts:
            if t is not None:
                self.target_container.append(t)
        try:
            try:
                self.semantic_segmentation_labels = (serialization['semantic_segmentation_labels']['model'],
                                                     [t['label'] for t in serialization['semantic_segmentation_labels']['labels']])
            except Exception as e:
                log_debug("Importing old style SemanticSegmentation Labels", e)
                self.semantic_segmentation_labels = serialization['semantic_segmentation_labels']

        except Exception as e:
            log_error("Exception in deserialize", e)
        if self.semantic_segmentation_labels is None:
            self.semantic_segmentation_labels = ("", [])
        return self


class UniqueKeyword(BaseProjectEntity):
    """
    Unique Keywords are generated when a Vocabulary is added to a Classification Object. 
    For each word in the Vocabulary a Unique Keyword is created to the Classification Object.

    :var experiment: The Experiment this Keyword belongs to
    :var voc_obj: The Vocabulary this keyword origins
    :var word_obj: The VocabularyWord this keyword origins
    :var class_obj: The ClassObj this keyword origins
    :var external_id: An External Key for the ERC-FilmColors Project
    """
    def __init__(self, experiment,  voc_obj:Vocabulary = None, word_obj:VocabularyWord = None, class_obj:ClassificationObject = None, unique_id=-1, emit_change=True):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        self.experiment = experiment
        self.voc_obj = voc_obj
        self.word_obj = word_obj
        self.class_obj = class_obj
        self.external_id = -1
        self.tagged_containers = []

        if word_obj is not None and emit_change:
            self.word_obj._add_referenced_unique_keyword(self)

    def get_name(self):
        return self.word_obj.get_name()

    def get_full_name(self):
        return ":".join([self.class_obj.name, self.voc_obj.name, self.word_obj.name]).replace(" ", "-")

    def get_root_name(self):
        return ":".join([self.class_obj.name, self.voc_obj.name]).replace(" ", "-")

    def serialize(self):
        data = dict(
            unique_id = self.unique_id,
            voc_obj = self.voc_obj.unique_id,
            word_obj = self.word_obj.unique_id,
            class_obj = self.class_obj.unique_id,
            vian_webapp_external_id = self.external_id
        )
        return data

    def deserialize(self, serialization, project, word_obj = None):
        self.unique_id = serialization['unique_id']
        self.word_obj = word_obj
        self.voc_obj = self.word_obj.vocabulary
        self.class_obj = project.get_by_id(serialization['class_obj'])

        try:
            self.external_id = deprecation_serialization(serialization,['vian_webapp_external_id', 'external_id'])
        except Exception as e:
            log_error("Could not deserialize vian_webapp_external_id")
            pass

        if self.voc_obj is None or self.word_obj is None or self.class_obj is None:
            raise ValueError("UniqueKeyword could not be resolved.")

        self.set_project(project)
        self.word_obj._add_referenced_unique_keyword(self)

        return self


class Experiment(BaseProjectEntity, IHasName):
    """
    An Experiment holds all information connected to Classification of Objects.
    As such it defines rules for an experiment and tracks the Progress.

    :var name: The Name of this Experiment
    :var classification_objects: The Classification Objects Attached to it
    :var analyses: The Names of Analyses that have to be performed in this experiment
    :var analyses_parameters: The List of Analyses parameters connected to the analyses above
    :var classification_results: The Classification Mapping a list of [IClassifiable, UniqueKeywords]

    """
    onExperimentChanged = pyqtSignal(object)
    onClassificationObjectAdded = pyqtSignal(object)
    onClassificationObjectRemoved = pyqtSignal(object)

    def __init__(self, name="New Experiment", unique_id=-1):
        BaseProjectEntity.__init__(self, unique_id=unique_id)
        self.name = name
        self.classification_objects = []    #type:List[ClassificationObject]
        self.analyses = []

        # This is a list of [IClassifiable, UniqueKeyword]
        self.classification_results = [] #type: List[Tuple[IClassifiable, UniqueKeyword]]
        self.correlation_matrix = None

        self.onClassificationObjectRemoved.connect(partial(self.emit_change))
        self.onClassificationObjectAdded.connect(partial(self.emit_change))

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.onExperimentChanged.emit(self)

    def get_type(self):
        return EXPERIMENT
    
    def query(self, keywords:List[UniqueKeyword], promote_to_screenshots = False):
        """
        Query the project for all IClassifiable which are tagged with any of list of keywords.

        :param keywords:
        :param promote_to_screenshots:
        :return:
        """
        result = []
        containers = self.project.get_all_containers()

        for c in containers:
            if isinstance(c, IClassifiable):
                c.set_classification_highlight(False)

        for k in self.classification_results:
            if k[1] in keywords:
                result.append(k[0])
        result = list(set(result))

        if not promote_to_screenshots:
            for r in result:
                r.set_classification_highlight(True)
        else:
            screenshots = []
            for r in result:
                r.set_classification_highlight(True)

                if r.get_type() == SEGMENT and r in self.project.segment_screenshot_mapping:
                    screenshots.extend(self.project.segment_screenshot_mapping[r])
            self.project.onScreenshotsHighlighted.emit(screenshots)

    def get_correlation_matrix(self):
        if self.correlation_matrix is not None:
            return self.get_unique_keywords(), self.correlation_matrix
        else:
            keywords = self.get_unique_keywords()
            idx = dict()
            for i, k in enumerate(keywords):
                idx[k] = i
            matrix = np.zeros(shape=(len(keywords), len(keywords)))
            curr_classifyable = None
            curr_correlations = []
            for res in sorted(self.classification_results, key=lambda x:id(x[0])):
                if res[0] != curr_classifyable:
                    if curr_classifyable is not None:
                        for x, k in enumerate(curr_correlations):
                            for y, l in enumerate(curr_correlations):
                                matrix[idx[k[1]], idx[l[1]]] += 1
                                matrix[idx[l[1]], idx[k[1]]] += 1
                    curr_correlations = []
                    curr_classifyable = res[0]
                curr_correlations.append(res)
            matrix /= np.amax(matrix)
            return keywords, matrix

    def get_vocabularies(self) -> List[Vocabulary]:
        result = []
        for clobj in self.classification_objects:
            result.extend(clobj.get_vocabularies())
        return result

    def get_vocabularies_for_target(self, target):
        """
        Returns all classification objects which are connected to a certain Segmentation or Screenshot Group.
        Classification Objects with no target container defined, are assumed to be connected to all Segmentations and
        Screenshot Groups.

        :param target:
        :return:
        """
        result = []
        for clobj in self.get_classification_objects_plain():
            if target in clobj.target_container or len(clobj.target_container) == 0:
                result.append(target)
        return result

    def get_complexity_groups(self):
        """
        Returns a list of all complexity groups used in the vocabularies attached to this Experiment
        :return:
        """
        complexity_groups = []
        for k in self.get_unique_keywords():
            t = k.word_obj.complexity_group
            if t not in complexity_groups:
                complexity_groups.append(t)
        return complexity_groups

    def create_class_object(self, name, parent=None, unique_id=-1):
        t = self.get_classification_object_by_name(name)
        if t is not None:
            return t

        if parent is None:
            parent = self
        obj = ClassificationObject(name, self, parent, unique_id=unique_id)
        if parent is self:
            obj.set_project(self.project)
            self.classification_objects.append(obj)
        else:
            parent.add_child(obj)
        return obj

    def get_unique_keywords(self, container_type = None, return_all_if_none = False) -> List[UniqueKeyword]:
        """
        :return: Returns a List of UniqueKeywords used in this Experiment's Classification Objects
        """
        keywords = []
        objects = self.get_classification_objects_plain()
        if container_type is None:
            for k in objects:
                keywords.extend(k.unique_keywords)
        else:
            for k in objects:
                if len(k.target_container) == 0 and return_all_if_none:
                    keywords.extend(k.unique_keywords)
                elif container_type in k.target_container:
                    keywords.extend(k.unique_keywords)
        return keywords

    def add_classification_object(self, obj: ClassificationObject):
        if obj not in self.classification_objects:
            self.classification_objects.append(obj)
            self.onClassificationObjectAdded.emit(self)

        obj.onClassificationObjectChanged.connect(partial(self.emit_change))
        obj.onUniqueKeywordsChanged.connect(partial(self.emit_change))

    def remove_classification_object(self, obj: ClassificationObject):
        if obj in self.classification_objects:
            self.classification_objects.remove(obj)
            self.onClassificationObjectRemoved.emit(self)
            self.project.remove_from_id_list(obj)

    def get_containers_to_classify(self):
        """
        Returns a list of all containers to classify in this experiment. 
        :return: 
        """
        result = []
        for c in self.get_classification_objects_plain():
            if len(c.target_container) > 0:
                for tgt in c.target_container:
                    if tgt.get_type() == SEGMENTATION:
                        for child in tgt.segments:
                            if child not in result:
                                result.append(child)
                    if tgt.get_type() == ANNOTATION_LAYER:
                        for child in tgt.annotations:
                            if child not in result:
                                result.append(child)
                    if tgt.get_type() == SCREENSHOT_GROUP:
                        for child in tgt.screenshots:
                            if child not in result:
                                result.append(child)
            else:
                for s in self.project.segmentation:
                    result.extend(s.segments)
                for s in self.project.annotation_layers:
                    result.extend(s.annotations)
                result.extend(self.project.screenshots)
        return result

    def get_classification_objects_plain(self) -> List[ClassificationObject]:
        result = []
        for root in self.classification_objects:
            root.get_children_plain(result)
        return result

    def get_classification_object_by_name(self, name) -> ClassificationObject:
        for obj in self.get_classification_objects_plain():
            if obj.name == name:
                return obj
        return None

    def add_analysis_to_pipeline(self, name, analysis:AnalysisContainer, parameters = None, classification_object = None):
        if analysis not in self.analyses:
            self.analyses.append(
                dict(
                    name = name,
                    class_name = analysis,
                    params = parameters,
                    class_obj = classification_object
                )
            )

    def remove_analysis_from_pipeline(self, obj):
        if obj in self.analyses:
            self.analyses.remove(obj)

    def toggle_tag(self, container: IClassifiable, keyword: UniqueKeyword):
        tag = [container, keyword]
        if tag not in self.classification_results:
            self.tag_container(container, keyword)
            return True
        else:
            self.remove_tag(container, keyword)
            return False

    def has_tag(self, container: IClassifiable, keyword: UniqueKeyword):
        tag = [container, keyword]
        if tag in self.classification_results:
            return True
        else:
            return False

    def tag_container(self, container: IClassifiable, keyword: UniqueKeyword):
        tag = [container, keyword]
        if tag not in self.classification_results:
            self.classification_results.append(tag)
            if container not in keyword.tagged_containers:
                keyword.tagged_containers.append(container)
                container.add_word(keyword)

    def remove_tag(self, container: IClassifiable, keyword: UniqueKeyword):
        try:
            self.classification_results.remove([container, keyword])
            if container in keyword.tagged_containers:
                keyword.tagged_containers.remove(container)
                container.remove_word(keyword)
        except Exception as e:
            log_error("Exception in remove_tag", e)

    def remove_all_tags_with_container(self, container):
        self.classification_results[:] = [tup for tup in self.classification_results if not tup[0] is container]

    def emit_change(self):
        self.onExperimentChanged.emit(self)

    def serialize(self):
        analyses = []
        for a in self.analyses:
            if a['class_obj'] is not None:
                analyses.append(dict(
                    name = a['name'],
                    class_name=str(a['class_name'].__name__),
                    params=a['params'],
                    class_obj=a['class_obj'].unique_id
                ))
            else:
                analyses.append(dict(
                    name=a['name'],
                    class_name=str(a['class_name'].__name__),
                    params=a['params'],
                    class_obj=None
                ))

        data = dict(
            name=self.name,
            unique_id = self.unique_id,
            classification_objects=[c.serialize() for c in self.get_classification_objects_plain()],
            analyses=analyses,
            classification_results = [dict(target=c[0].unique_id, keyword=c[1].unique_id) for c in self.classification_results],
        )
        return data

    def to_template(self):
        analyses = []
        for a in self.analyses:
            if a['class_obj'] is not None:
                analyses.append(dict(
                    name=a['name'],
                    class_name=str(a['class_name'].__name__),
                    params=a['params'],
                    class_obj=a['class_obj'].unique_id
                ))
            else:
                analyses.append(dict(
                    name=a['name'],
                    class_name=str(a['class_name'].__name__),
                    params=a['params'],
                    class_obj=None
                ))

        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            classification_objects=[c.serialize() for c in self.get_classification_objects_plain()],
            analyses=analyses,
            classification_results=[],
        )
        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']

        for ser in serialization['classification_objects']:
            obj = ClassificationObject("", self).deserialize(ser, project)
            obj.onClassificationObjectChanged.connect(partial(self.emit_change))
            obj.onUniqueKeywordsChanged.connect(partial(self.emit_change))

        analyses = serialization['analyses']
        if len(analyses) > 0:
            if "class_name" not in analyses[0]:
                self.analyses = []
            else:
                self.analyses = []
                try:
                    for a in analyses:
                        if a['class_obj'] != None:
                            self.analyses.append(dict(
                                name=a['name'],
                                class_name = get_analysis_by_name(a['class_name']),
                                params = a['params'],
                                class_obj = project.get_by_id(a['class_obj'])
                            ))
                        else:
                            self.analyses.append(dict(
                                name=a['name'],
                                class_name=get_analysis_by_name(a['class_name']),
                                params=a['params'],
                                class_obj=None
                            ))
                except Exception as e:
                    log_error("Exeption during loading ExperimentAnalysis:", e)
                    self.analyses = []

        try:
            keywords = dict()
            for k in self.get_unique_keywords():
                keywords[k.unique_id] = k

            for ser in serialization['classification_results']:
                try:
                    target_uuid = ser['target']
                    keyword_uuid = ser['keyword']
                except:
                    target_uuid = ser[0]
                    keyword_uuid = ser[1]

                c = project.get_by_id(target_uuid)
                try:
                    k = project.get_by_id(keyword_uuid)
                except:
                    k = None
                if c is not None and k is not None:
                    self.tag_container(c, k)
                else:
                    log_error("Loading Classification mapping failed: ", c, k)
        except Exception as e:
            log_error("Exeption during Experiment.deserialize:", e)
            pass
        return self

    def delete(self):
        self.project.remove_experiment(self)


def merge_experiment(self:Experiment, other: Experiment, drop=False):
    """
    Merges another experiment into this experiment
    :param self:
    :param other:
    :param drop:
    :return:
    """
    changes = []

    # Creating all missing Classification Objects
    cl_objs_index = dict()
    for entry in other.get_classification_objects_plain():
        clobj = self.project.get_by_id(entry.unique_id)
        if clobj is None:
            clobj = ClassificationObject(entry.name, experiment=self, parent=self)
            clobj.unique_id = entry.unique_id
            clobj.set_project(self.project)
            self.add_classification_object(clobj)
            clobj.semantic_segmentation_labels = entry.semantic_segmentation_labels
            changes.append(("Added Classification Object", clobj))
        cl_objs_index[entry.unique_id] = clobj
    words_index = dict()

    # Creating all missing Vocabularies
    for entry in other.get_vocabularies():
        voc = self.project.get_by_id(entry.unique_id)

        if voc is None:
            voc = self.project.get_by_id(entry.unique_id)
            if voc is not None:
                entry.unique_id = voc.unique_id

        if voc is None:
            voc = Vocabulary(name=entry.name)
            voc.unique_id = entry.unique_id
            self.project.add_vocabulary(voc)
            changes.append(("Added Vocabulary Object", voc))

        voc.category = entry.category

        for w in entry.words_plain:
            word = self.project.get_by_id(w.unique_id)
            if word is None:
                word = VocabularyWord(name=w.name, vocabulary=voc)
                word.unique_id = w.unique_id
                voc.add_word(word)
                changes.append(("Added Vocabulary Word", voc))

            # Updating Values
            word.complexity_group = w.complexity_group
            word.complexity_lvl = w.complexity_lvl
            word.organization_group = w.organization_group
            words_index[word.unique_id] = word

            # if entry.name == "Narratology":
            #     print("Word", word.name, word.unique_id, voc.unique_id)

    vocs_to_add = []
    unique_keywords = dict()

    # Creating all missing Unique Keywords
    for entry in other.get_unique_keywords():
        clobj = cl_objs_index[entry.class_obj.unique_id]
        word = words_index[entry.word_obj.unique_id]

        # We build a lookup hashtable
        if clobj.unique_id not in unique_keywords:
            unique_keywords[clobj.unique_id] = dict()

        # Check if the keyword already exists in this experiment by id:
        keyword = self.project.get_by_id(entry.unique_id) #type:UniqueKeyword

        # Check if the keyword exists by hierarchy (VocabularyWord - Classification Object)
        if keyword is None:
            ts = [(kwd, kwd.word_obj) for kwd in clobj.unique_keywords]
            for k, w in ts:
                if w == word:
                    keyword = k
                    break

        # if the keyword doesn't exist, create it
        if keyword is None:
            keyword = UniqueKeyword(self, word.vocabulary, word, clobj)

        keyword.unique_id = entry.unique_id

        if (word.vocabulary, clobj) not in vocs_to_add:
            vocs_to_add.append((word.vocabulary, clobj))
            unique_keywords[clobj.unique_id][word.vocabulary.unique_id] = dict()

        unique_keywords[clobj.unique_id][word.vocabulary.unique_id][word.unique_id] = keyword

        if word.vocabulary.name == "Narratology":
            print(clobj.unique_id, word.vocabulary.unique_id, unique_keywords[clobj.unique_id][word.vocabulary.unique_id])


    # Creating adding the vocabularies to the classification object, inject the UniqueKeywords
    for vocabulary, clobj in vocs_to_add:
        print(clobj.unique_id, vocabulary.unique_id)
        clobj.add_vocabulary(vocabulary, keyword_override=unique_keywords[clobj.unique_id][vocabulary.unique_id])

    if drop:
        diff = set([t.unique_id for t in self.get_classification_objects_plain()])\
            .difference([t.unique_id for t in other.get_classification_objects_plain()])

        for d in diff:
            self.remove_classification_object(self.project.get_by_id(d))

        for c_self in self.get_classification_objects_plain():
            c_other = other.project.get_by_id(c_self.unique_id)
            diff = set([t.unique_id for t in c_self.get_vocabularies()])\
                .difference([t.unique_id for t in c_other.get_vocabularies()])
            for d in diff:
                c_self.remove_vocabulary(self.project.get_by_id(d))

        for v_self in self.get_vocabularies():
            v_other = other.project.get_by_id(v_self.unique_id)
            diff = set([t.unique_id for t in v_self.words_plain]) \
                .difference([t.unique_id for t in v_other.words_plain])
            for d in diff:
                v_self.remove_word(self.project.get_by_id(d))
    return changes


def merge_experiment_inspect(self:Experiment, other: Experiment):
    changes = []
    cl_objs_index = dict()
    for entry in other.get_classification_objects_plain():
        clobj = self.project.get_by_id(entry.unique_id)
        if clobj is None:
            changes.append(("Added Classification Object", entry.name))
        cl_objs_index[entry.unique_id] = entry

    words_index = dict()
    for entry in other.get_vocabularies():
        voc = self.project.get_by_id(entry.unique_id)
        if voc is None:
            changes.append(("Added Vocabulary Object", entry))

        for w in entry.words_plain:
            word = self.project.get_by_id(w.unique_id)
            if word is None:
                changes.append(("Added Vocabulary Word", w))
            words_index[w.unique_id] = w

    # Creating all missing Unique Keywords
    t1 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in other.get_unique_keywords()]
    t2 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in self.get_unique_keywords()]

    #To Add
    diff = set(t1).difference(set(t2))

    def format_keyword(t, r):
        return t.project.get_by_id(r[0]).name, \
               t.project.get_by_id(r[1]).name, \
               t.project.get_by_id(r[2]).name

    for d in diff:
        changes.append(("Added UniqueKeyword", format_keyword(other, d)))
        # To Add
    diff = set(t2).difference(set(t1))
    for d in diff:
        changes.append(("Removed UniqueKeyword", format_keyword(self, d)))

    return changes


VOC_COMPARE_ATTRS = [
    "name",
    "comment",
    "info_url",
    "image_urls",
    "category"
]

WORD_COMPARE_ATTRS = [
    "name",
    "comment",
    "info_url",
    "image_urls",
    "organization_group",
    "complexity_lvl",
    "complexity_group"
]


def compare_vocabularies(voc1: Vocabulary, voc2: Vocabulary):
    changes = []
    for attr in VOC_COMPARE_ATTRS:
        if getattr(voc1, attr) != getattr(voc2, attr):
            changes.append(dict(modification="Modified Vocabulary",
                                name=attr,
                                text=str(getattr(voc1, attr)) + " to " + str(getattr(voc2, attr))))

    uuid_map_voc1 = dict()
    for w in voc1.words_plain: #type:VocabularyWord
        uuid_map_voc1[w.unique_id] = w

    uuid_map_voc2 = dict()
    for w in voc2.words_plain:  # type:VocabularyWord
        uuid_map_voc2[w.unique_id] = w

    words_to_add = []
    for uuid in uuid_map_voc1:
        if uuid not in uuid_map_voc2:
            words_to_add.append(uuid_map_voc1[uuid])

    words_to_remove = []
    for uuid in uuid_map_voc2:
        if uuid not in uuid_map_voc1:
            words_to_remove.append(uuid_map_voc2[uuid])

    for uuid in uuid_map_voc1:
        if uuid not in uuid_map_voc2:
            continue
        w1 = uuid_map_voc1[uuid]
        w2 = uuid_map_voc2[uuid]
        for attr in WORD_COMPARE_ATTRS:
            if getattr(w1, attr) != getattr(w2, attr):
                changes.append(dict(modification="Modified Word",
                                    name=attr,
                                    text=str(getattr(w1, attr)) + " to " + str(getattr(w2, attr))))

    for w in words_to_add:
        changes.append(dict(modification="Added Word",
                            name=w,
                            text="Added new word " + w.name))
    for w in words_to_remove:
        changes.append(dict(modification="Removed Word",
                            name=w,
                            text="Removed new word " + w.name))

    return changes