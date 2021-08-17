from core.container.project import VIANProject
from core.container.experiment import Experiment, ClassificationObject, Vocabulary
from core.container.segmentation import Segmentation, Segment

def get_VIANProject1_exporter():
    project: VIANProject = VIANProject()

    vocabularies = []
    voc = Vocabulary(name="voc1")
    voc.create_word("asdfas")
    voc.create_word("lala")

    vocabularies.append(voc)
    project.vocabularies = vocabularies

    experiments = []
    e = Experiment()
    experiments.append(e)
    project.experiments = experiments

    classification_objects = []

    for c in range(4):
        classification_object = ClassificationObject(name="CO:"+str(c), experiment=e)
        classification_object.add_vocabulary(voc)
        classification_objects.append(classification_object)

    e.classification_objects = classification_objects

    # segmentation
    segments = []
    t = Segment(ID=1, start=1000, end=2300, duration=1300, annotation_body="test123")
    t.add_word(classification_objects[0].unique_keywords[0])
    segments.append(t)
    project.segmentation = [Segmentation(segments=segments)]

    return project
