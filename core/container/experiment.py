import json
from typing import List
from core.container.analysis import AnalysisContainer, AnalysisParameters
from core.data.enums import VOCABULARY, VOCABULARY_WORD, CLASSIFICATION_OBJECT, EXPERIMENT, SEGMENTATION, \
    ANNOTATION_LAYER, SCREENSHOT_GROUP
from core.data.interfaces import IProjectContainer, IHasName, IClassifiable
from core.gui.vocabulary import VocabularyItem

class Vocabulary(IProjectContainer, IHasName):
    """
    :var name: The Name of the Vocabulary
    :var comment: This is a generic field to put a description into about the Voc.
    :var info_url: A URL to a description of this vocabulary
    :var words: A List of VocabularyWords that sit in the root
    :var words_plain: A List of All VocabularyWords that are in the Vocabulary
    :var was_expanded: If it is expandend in the VocabularyManager
    :var category: The Category it belongs to
    :var derived_vocabulary: OBSOLETE
    :var base_vocabulary: OBSOLETE
    """
    def __init__(self, name):
        IProjectContainer.__init__(self)
        self.name = name
        self.comment = ""
        self.info_url = ""
        self.words = []
        self.words_plain = []
        self.was_expanded = False
        self.category = "default"

        self.derived_vocabulary = False  # TODO OBSOLETE
        self.base_vocabulary = None # TODO OBSOLETE

    def create_word(self, name, parent_word = None, unique_id = -1, dispatch = True):
        if name in [w.name for w in self.words_plain]:
            print("Duplicate Word")
            return
        word = VocabularyWord(name, vocabulary=self)
        word.unique_id = unique_id
        self.add_word(word, parent_word, dispatch)
        return word

    def add_word(self, word, parent_word = None, dispatch = True):
        """
        
        :param word: the Word object to add
        :param parent_word: the parent Word, either as String or Word Object
        :return: 
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

    def remove_word(self, word, dispatch = True):
        children = []
        word.get_children_plain(children)

        for w in children:
            self.words_plain.remove(w)

        if word in self.words:
            self.words.remove(word)
        else:
            if word in word.parent.children:
                word.parent.children.remove(word)

        if word in self.words_plain:
            self.words_plain.remove(word)

        self.project.remove_from_id_list(word)

        if dispatch:
            self.dispatch_on_changed()

    def get_word_by_name(self, name):
        for w in self.words_plain:
            if w.name == name:
                return w
        return None

    def get_vocabulary_item_model(self):
        root = VocabularyItem(self.name, self)
        for w in self.words:
            w.get_children(root)
        return root

    def get_vocabulary_as_list(self):
        result = []
        for w in self.words:
            w.get_children_plain(result)
        return result

    def serialize(self):
        words = []
        for w in self.words:
            w.get_children_plain(words)

        words_data = []
        for w in words:
            data = dict(
                name = w.name,
                unique_id = w.unique_id,
                parent = w.parent.unique_id,
                children = [a.unique_id for a in w.children]
            )
            words_data.append(data)

        if self.base_vocabulary is not None:
            base = self.base_vocabulary.unique_id
        else:
            base = -1

        voc_data = dict(
            name = self.name,
            category = self.category,
            unique_id = self.unique_id,
            words = words_data,
            derived = self.derived_vocabulary,
            base = base
        )

        return voc_data

    def deserialize(self, serialization, project):
        self.project = project
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.category = serialization['category']
        for w in serialization['words']:
            parent = self.project.get_by_id(w['parent'])
            # If this is a root node in the Vocabulary
            if isinstance(parent, Vocabulary):
                self.create_word(w['name'], unique_id=w['unique_id'], dispatch=False)

            else:
                self.create_word(w['name'], parent, unique_id=w['unique_id'], dispatch=False)

        try:
            self.derived_vocabulary = serialization['derived']
            self.base_vocabulary = project.get_by_id(serialization['base'])
        except:
            self.derived_vocabulary = False
            self.base_vocabulary = None
        return self

    def export_vocabulary(self, path):
        try:
            data = self.serialize()
            with open(path, "w") as f:
                json.dump(data, f)
        except:
            print("Export_Vocabulary() failed with:", path)

    def import_vocabulary(self, path = None, project = None, serialization = None):
        if serialization is None:
            with open(path, "r") as f:
                serialization = json.load(f)

        id_replacing_table = []

        self.project = project
        self.name = serialization['name']
        self.category = serialization['category']

        old_id = serialization['unique_id']
        new_id = project.create_unique_id()
        self.unique_id = new_id

        id_replacing_table.append([old_id, new_id])


        # Replace all IDs with new one:
        for w in serialization['words']:
            old = w['unique_id']
            new = self.project.create_unique_id()
            id_replacing_table.append([old, new])

        for w in serialization['words']:
            old_parent = w['parent']

            new_parent = -1
            for tpl in id_replacing_table:
                if tpl[0] == old_parent:
                    new_parent = tpl[1]
                    break

            old_id = w['unique_id']
            new_id = -1
            for tpl in id_replacing_table:
                if tpl[0] == old_id:
                    new_id = tpl[1]
                    break


            parent = self.project.get_by_id(new_parent)
            # If this is a root node in the Vocabulary
            if isinstance(parent, Vocabulary):
                self.create_word(w['name'], unique_id=new_id)

            else:
                self.create_word(w['name'], parent, unique_id=new_id)

        return self, id_replacing_table

    def get_vocabulary_id(self):
        vid = self.name
        for w in self.get_vocabulary_as_list():
            try:
                vid += w.name[0]
            except:
                continue
        print("Vocabulary ID: ", vid)
        return vid

    def get_type(self):
        return VOCABULARY

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def delete(self):
        for w in self.words_plain:
            self.remove_word(w, dispatch=False)
        self.project.remove_vocabulary(self)


class VocabularyWord(IProjectContainer, IHasName):
    """
    :var name: The Name of the Word
    :var comment: An additional field to add some info about it. In the ERC_FILM_COLORS this refers to the glossary ID
    :var info_url: A Url to the description of this Vocabulary
    :var vocabulary: It's parent Vocabulary
    :var is_checkable: If this word is checkeable or not
    :var was_expanded: If this word is expanded in the Vocabulary Manager
    :var parent: The Parent Word
    :var children: The Children Words
    :var connected_items: IProjectContainer objects that are connected with it # Obsolete

    """
    def __init__(self, name, vocabulary, parent = None, is_checkable = False):
        IProjectContainer.__init__(self)
        self.name = name
        self.comment = ""
        self.info_url = ""
        self.vocabulary = vocabulary
        self.is_checkable = is_checkable
        self.was_expanded = False
        self.parent = parent
        self.children = []
        self.connected_items = []

    # OBSOLETE
    def add_connected_item(self, item):
        self.connected_items.append(item)

    # OBSOLETE
    def remove_connected_item(self, item):
        if item in self.connected_items:
            self.connected_items.remove(item)

    def add_children(self, children):
        if isinstance(children, list):
            for c in children:
                self.children.append(c)
                c.parent = self
        else:
            self.children.append(children)

    def get_children(self, parent_item):
        item = VocabularyItem(self.name, self)
        parent_item.appendRow(item)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children(item)

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def get_type(self):
        return VOCABULARY_WORD

    def get_name(self):
        return self.name

    def delete(self):
        self.project.remove_from_id_list(self)
        self.vocabulary.remove_word(self)


class ClassificationObject(IProjectContainer, IHasName):
    """
    A ClassificationTarget is an Object that one wants to classify by a set of Vocabularies.
    Several ClassificationTargets may form a Tree. 
    
    Example: Say one wants to analyse the Foreground and Background Color of a given Film using his homemade 
    Vocabulary called "ColorVocabulary". 
    
    The ClassificationTargets would therefore be "Foreground" and "Background", both will have "ColorVocabulary".

    :var name: The Name of this ClassificationObject
    :var experiment: A reference to the Experiment it belongs to
    :var parent: A Parent Classification Object or an Experiment if it's at the root
    :var children: A List of Chilren ClassificationObjects if any
    :var classification_vocabularies: A List of Vocabularies attached to thsi ClassificationObject
    :var unique_keywords: A List of Unique Keywords generated from this ClassificationObjects and its Vocabularies
    :var target_container: A List of Target Containers to classify with this Classification Object

    """
    def __init__(self, name, experiment, parent = None):
        IProjectContainer.__init__(self)
        self.name = name
        self.experiment = experiment
        self.parent = parent
        self.children = []
        self.classification_vocabularies = []
        self.unique_keywords = []
        self.target_container = []

    def add_vocabulary(self, voc: Vocabulary, dispatch = True, external_ids = None):
        if voc not in self.classification_vocabularies:
            self.classification_vocabularies.append(voc)
            keywords = []
            for i, w in enumerate(voc.words_plain):
                keyword = UniqueKeyword(self.experiment, voc, w, self)
                if external_ids is not None:
                    keyword.external_id = external_ids[i]
                keyword.set_project(self.project)
                self.unique_keywords.append(keyword)
                keywords.append(keyword)
            return keywords
        else:
            keywords = []
            for r in self.unique_keywords:
                if r.voc_obj == voc:
                    keywords.append(r)
            return keywords


    def remove_vocabulary(self, voc):
        self.classification_vocabularies.remove(voc)
        to_delete = [x for x in self.unique_keywords if x.voc_obj == voc]
        self.unique_keywords = [x for x in self.unique_keywords if not x.voc_obj == voc]

        for d in to_delete:
            self.project.remove_from_id_list(d)

    def get_vocabularies(self):
        return self.classification_vocabularies

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def add_child(self, classification_object):
        classification_object.parent = self
        classification_object.set_project(self.project)
        self.children.append(classification_object)

    def remove_child(self, classification_object):
        if classification_object in self.children:
            self.children.remove(classification_object)
            self.project.remove_from_id_list(classification_object)
        else:
            print("NOT FOUND")

    def get_children_plain(self, list):
        list.append(self)
        if len(self.children) > 0:
            for c in self.children:
                c.get_children_plain(list)

    def get_type(self):
        return CLASSIFICATION_OBJECT

    def serialize(self):

        serialization = dict(
            name=self.name,
            unique_id = self.unique_id,
            parent = self.parent.unique_id,
            classification_vocabularies = [v.unique_id for v in self.classification_vocabularies],
            unique_keywords =  [k.serialize() for k in self.unique_keywords],
            target_container = [k.unique_id for k in self.target_container],
            children = [c.unique_id for c in self.children],
        )

        return serialization

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        p = project.get_by_id(serialization['parent'])

        if isinstance(p, ClassificationObject):
            p.add_child(self)
        else:
            p.classification_objects.append(self)
            self.parent = p
            self.set_project(project)

        self.classification_vocabularies = [project.get_by_id(uid) for uid in serialization['classification_vocabularies']]
        self.unique_keywords = [UniqueKeyword(self.experiment).deserialize(ser, project) for ser in serialization['unique_keywords']]
        self.target_container = [project.get_by_id(uid) for uid in serialization['target_container']]

        return self


class UniqueKeyword(IProjectContainer):
    """
    Unique Keywords are generated when a Vocabulary is added to a Classification Object. 
    For each word in the Vocabulary a Unique Keyword is created to the Classification Object.

    :var experiment: The Experiment this Keyword belongs to
    :var voc_obj: The Vocabulary this keyword origins
    :var word_obj: The VocabularyWord this keyword origins
    :var class_obj: The ClassObj this keyword origins
    :var external_id: An External Key for the ERC-FilmColors Project
    """
    def __init__(self, experiment,  voc_obj:Vocabulary = None, word_obj:VocabularyWord = None, class_obj:ClassificationObject = None):
        IProjectContainer.__init__(self)
        self.experiment = experiment
        self.voc_obj = voc_obj
        self.word_obj = word_obj
        self.class_obj = class_obj
        self.external_id = -1

    def get_name(self):
        return self.word_obj.get_name()

    def serialize(self):
        data = dict(
            unique_id = self.unique_id,
            voc_obj = self.voc_obj.unique_id,
            word_obj = self.word_obj.unique_id,
            class_obj = self.class_obj.unique_id,
            external_id = self.external_id
        )

        return data

    def deserialize(self, serialization, project):
        self.unique_id = serialization['unique_id']
        self.voc_obj = project.get_by_id(serialization['voc_obj'])
        self.word_obj = project.get_by_id(serialization['word_obj'])
        self.class_obj = project.get_by_id(serialization['class_obj'])
        try:
            self.external_id = serialization['external_id']
        except:
            pass

        self.set_project(project)

        return self


class Experiment(IProjectContainer, IHasName):
    """
    An Experiment holds all information connected to Classification of Objects.
    As such it defines rules for an experiment and tracks the Progress.

    :var name: The Name of this Experiment
    :var classification_objects: The Classification Objects Attached to it
    :var analyses: The Names of Analyses that have to be performed in this experiment
    :var analyses_parameters: The List of Analyses parameters connected to the analyses above
    :var classification_results: The Classification Mapping a list of [IClassifiable, UniqueKeywords]

    """

    def __init__(self, name="New Experiment"):
        IProjectContainer.__init__(self)
        self.name = name
        self.classification_objects = []
        self.analyses = []
        self.analyses_parameters = []

        # This is a list of [IClassifiable, UniqueKeyword]
        self.classification_results = []

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_type(self):
        return EXPERIMENT

    def get_vocabularies(self):
        result = []
        for clobj in self.classification_objects:
            result.extend(clobj.get_vocabularies())
        return result

    def create_class_object(self, name, parent):
        obj = ClassificationObject(name, self, parent)
        if parent is self:
            obj.set_project(self.project)
            self.classification_objects.append(obj)
        else:
            parent.add_child(obj)
        return obj

    def get_unique_keywords(self, container_type = None):
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
                if container_type in k.target_container:
                    keywords.extend(k.unique_keywords)
        return keywords

    def add_classification_object(self, obj: ClassificationObject):
        if obj not in self.classification_objects:
            self.classification_objects.append(obj)

    def remove_classification_object(self, obj: ClassificationObject):
        if obj in self.classification_objects:
            self.classification_objects.remove(obj)

    def get_containers_to_classify(self):
        """
        Returns a list of all containers to classify in this experiment. 
        :return: 
        """
        result = []
        for c in self.get_classification_objects_plain():
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
        return result

    def get_classification_objects_plain(self) -> List[ClassificationObject]:
        result = []
        for root in self.classification_objects:
            root.get_children_plain(result)
        return result

    def add_analysis(self, analysis:AnalysisContainer, parameters:AnalysisParameters = None):
        if analysis not in self.analyses:
            self.analyses.append(analysis)

            if parameters is None:
                parameters = AnalysisParameters()
            self.analyses_parameters.append(parameters)

    def remove_analysis(self, analysis):
        if analysis in self.analyses:
            idx = self.analyses.index(analysis)
            self.analyses.remove(analysis)
            self.analyses_parameters.pop(idx)

    def toggle_tag(self, container: IClassifiable, keyword: UniqueKeyword):
        tag = [container, keyword]
        # print("Toggled", tag)
        if tag not in self.classification_results:
            self.classification_results.append(tag)
        else:
            self.classification_results.remove([container, keyword])

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

    def remove_tag(self, container: IClassifiable, keyword: UniqueKeyword):
        try:
            self.classification_results.remove([container, keyword])
        except Exception as e:
            print(e)

    def remove_all_tags_with_container(self, container):
        self.classification_results[:] = [tup for tup in self.classification_results if not tup[0] is container]

    def serialize(self):
        data = dict(
            name=self.name,
            unique_id = self.unique_id,
            classification_objects=[c.serialize() for c in self.get_classification_objects_plain()],
            analyses=self.analyses,
            classification_results = [(c[0].unique_id, c[1].unique_id) for c in self.classification_results]
        )
        return data

    def to_template(self):
        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            classification_objects=[c.serialize() for c in self.get_classification_objects_plain()],
            analyses=self.analyses,
            classification_results=[]
        )
        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        project.add_experiment(self)

        for ser in serialization['classification_objects']:
            obj = ClassificationObject("", self).deserialize(ser, project)

        self.analyses = serialization['analyses']

        try:
            for ser in serialization['classification_results']:
                c = project.get_by_id(ser[0])
                k = project.get_by_id(ser[1])
                if c is not None and k is not None:
                    self.classification_results.append([c, k])
                else:
                    print("Loading Classification mapping failed: ", c, k)

        except Exception as e:
            print(e)
            pass

        return self

    def delete(self):
        self.project.remove_experiment(self)

