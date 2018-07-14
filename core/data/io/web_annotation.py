"""
:author Gaudenz Halter

This IODevice is mainly targeting the export
"""

import os
import sys
import json
from core.container.project import *
from core.container.segmentation import *
from core.corpus.shared.entities import DBContributor

class WebAnnotationDevice():
    def export(self, file_path, project:VIANProject, contributor:DBContributor):
        results = []
        for s in project.segmentation:
            for i, segm in enumerate(s.segments):
                results.append(dict(
                    context="http://www.w3.org/ns/anno.jsonld",
                    id = i,
                    type="Annotation",
                    motivation="describing",
                    creator = dict(
                        type = "Person",
                        name = contributor.name,
                        email = "" # TODO
                    ),
                    body = dict(
                        type = "TextualBody",
                        value = segm.annotation_body,
                        format = "text/plain",
                        language = "en", # TODO
                        purpose = "describing"
                    ),
                    target = dict(
                        type="FragmentSelector",
                        conformsTo="http://www.w3.org/TR/media-frags/",
                        value = project.movie_descriptor.movie_path + "#t=" + str(segm.get_start()/1000.0) + "," + str(segm.get_end()/1000.0)
                    )
                ))

        for e in project.experiments:
            e = Experiment()
            for (container, keyword) in e.classification_results:
                pass

        with open(file_path, "w") as f:
            json.dump(results, f)

    def import_(self, file_path):
        pass



