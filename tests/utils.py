from uuid import uuid4
from core.container.project import VIANProject
from core.container.experiment import Experiment, ClassificationObject, Vocabulary
from core.container.segmentation import Segmentation, Segment

def get_VIANProject1_exporter():
    project: VIANProject = VIANProject()

    voc = Vocabulary(name="voc1", unique_id=str(uuid4()))
    voc.create_word("word1", unique_id=str(uuid4()))
    voc.create_word("word2", unique_id=str(uuid4()))
    project.add_vocabulary(voc)

    voc2 = Vocabulary(name="voc2", unique_id=str(uuid4()))
    voc2.create_word("special:';12!@#$_)((**^characters", unique_id=str(uuid4()))
    voc2.create_word("CAPITAL_WORD", unique_id=str(uuid4()))
    project.add_vocabulary(voc2)

    e = Experiment()

    for c in range(4):
        classification_object = ClassificationObject(name="ClObj-"+str(c), experiment=e, unique_id=str(uuid4()))
        classification_object.add_vocabulary(voc)
        classification_object.add_vocabulary(voc2)
        e.add_classification_object(classification_object)

    project.add_experiment(e)

    # segmentation
    segmentation = Segmentation()
    segmentation.set_project(project)

    for s in range(20):
        t = Segment(ID=s, start=s*1500, end=(s+1)*1500, duration=1500, annotation_body=["test123", "test123.1", "test123.2"])
        t.add_word(e.classification_objects[s%3].unique_keywords[s%4])
        t.add_word(e.classification_objects[s%3].unique_keywords[s%3])
        #print(e.classification_objects[s%3].name, e.classification_objects[s%3].unique_keywords[s%4].word_obj.name, e.classification_objects[s%3].unique_keywords[s%4].unique_id)
        #print(e.classification_objects[s % 3].name, e.classification_objects[s % 3].unique_keywords[s % 3].word_obj.name, e.classification_objects[s % 3].unique_keywords[s % 3].unique_id)
        segmentation.add_segment(t)

    project.add_segmentation(segmentation)

    return project
