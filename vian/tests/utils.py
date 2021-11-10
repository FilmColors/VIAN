import math
import os
from uuid import uuid4
from vian.core.container.project import VIANProject, Screenshot
from vian.core.container.experiment import Experiment, ClassificationObject, Vocabulary
from vian.core.container.segmentation import Segmentation, Segment

def get_test_data_dir():
    return os.path.join(os.path.dirname(__file__), "data")

def get_VIANProject1_exporter():
    project: VIANProject = VIANProject()

    # vocabulary with words
    voc = Vocabulary(name="voc1", unique_id=str(uuid4()))
    voc.create_word("word1", unique_id=str(uuid4()))
    voc.create_word("word2", unique_id=str(uuid4()))
    project.add_vocabulary(voc)

    voc2 = Vocabulary(name="voc2", unique_id=str(uuid4()))
    voc2.create_word("special:';12!@#$_)((**^characters", unique_id=str(uuid4()))
    voc2.create_word("CAPITAL_WORD", unique_id=str(uuid4()))
    project.add_vocabulary(voc2)

    # experiment with classification objects
    e = project.get_default_experiment()
    for c in range(4):
        classification_object = ClassificationObject(name="ClObj-"+str(c), experiment=e, unique_id=str(uuid4()))
        e.add_classification_object(classification_object)
        classification_object.add_vocabulary(voc)
        classification_object.add_vocabulary(voc2)
        e.add_classification_object(classification_object)

    # segmentation
    segmentation = Segmentation()
    segmentation.set_project(project)

    time_elapsed = 0
    for s in range(20):
        segment_duration = (math.sin(s) + 1.1)  * 8000  # arbitrary duration function for varying numbers.
        t = Segment(ID=s, start=time_elapsed, end=time_elapsed + segment_duration,
                    annotation_body=["test123", "test123.1", "test123.2"])
        time_elapsed += segment_duration
        t.add_tag(e.classification_objects[s % 3].unique_keywords[s % 4])
        t.add_tag(e.classification_objects[s % 3].unique_keywords[s % 3])
        segmentation.add_segment(t)

    project.add_segmentation(segmentation)

    # add screenshots
    for ss in range(1,50):
        project.add_screenshot(Screenshot(timestamp=ss * time_elapsed/50))

    return project
