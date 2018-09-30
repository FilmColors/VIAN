"""
:author Gaudenz Halter

This IODevice is realises the import and export of WebAnnotations 
https://www.w3.org/TR/annotation-model/diff.html#web-annotation-framework

Currently only an export is included
"""

import os
import sys
import json
import hashlib
from core.container.project import *
from core.container.segmentation import *
from core.data.settings import Contributor

class WebAnnotationDevice():
    def export(self, file_path, project:VIANProject, contributor:Contributor, version):
        result = []
        full_annotations = []
        creator_tag = dict(
                    type = "Person",
                    name = contributor.full_name,
                    email_sha1 = hashlib.sha1(contributor.email.encode()).hexdigest()
                )
        generator_tag = dict(
            id = "VIAN",
            type = "Software",
            name = "VIAN_" + version,
            homepage = "https://github.com/ghalter/VIAN/"
        )
        id_root = contributor.full_name.replace(" ", "_") + ":" + project.name.replace(" ", "_") + "/"
        for j, s in enumerate(project.segmentation):
            items = []
            segmentation_id = id_root + s.name.replace(" ", "_") + "/"
            for i, segm in enumerate(s.segments):
                items.append(dict(
                    id = segmentation_id + "1/" +  str(i),
                    type="Annotation"
                    )
                )
                full_annotations.append(dict(
                    context = "http://www.w3.org/ns/anno.jsonld",
                    id= segmentation_id + "1/" +  str(i),
                    motivation = "describing",
                    creator = creator_tag,
                    type = "Annotation",
                    body = dict(
                        type = "TextualBody",
                        value = segm.annotation_body,
                        format = "text/plain",
                        language = "en",
                        purpose = "describing"
                    ),
                    generator = generator_tag,
                    target = dict(
                        id = os.path.split(project.movie_descriptor.movie_path)[1],
                        type = "Video",
                        selector = dict(
                            type="FragmentSelector",
                            conformsTo="http://www.w3.org/TR/media-frags/",
                            value = os.path.split(project.movie_descriptor.movie_path)[1] + "#t=" + str(segm.get_start()/1000.0) + "," + str(segm.get_end()/1000.0)
                        )
                )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id = segmentation_id,
                creator = creator_tag,
                label = contributor.full_name,
                type = "AnnotationCollection",
                total = 1,
                first = dict(
                    id = segmentation_id + "1",
                    type = "AnnotationPage",
                    startIndex = 0,
                    items = items
                )
            )
            result.append(segmt)

        for j, s in enumerate(project.annotation_layers):
            items = []
            segmentation_id = id_root + s.name.replace(" ", "_") + "/"
            for i, segm in enumerate(s.annotations):
                items.append(dict(
                    id = segmentation_id + "1/" +  str(i),
                    type="Annotation"
                    )
                )
                full_annotations.append(dict(
                    context = "http://www.w3.org/ns/anno.jsonld",
                    id= segmentation_id + "1/" +  str(i),
                    motivation = "describing",
                    creator = creator_tag,
                    type = "Annotation",
                    body = dict(
                        type = "TextualBody",
                        value = segm.a_type.name,
                        format = "text/plain",
                        language = "en",
                        purpose = "describing"
                    ),
                    generator = generator_tag,
                    target = dict(
                        id = os.path.split(project.movie_descriptor.movie_path)[1],
                        type = "Video",
                        selector = dict(
                            type="FragmentSelector",
                            conformsTo="http://www.w3.org/TR/media-frags/",
                            value = os.path.split(project.movie_descriptor.movie_path)[1] + "#t=" + str(segm.get_start()/1000.0) + "," + str(segm.get_end()/1000.0),
                            refinedBy= dict(
                                type= "SvgSelector",
                                value= "<rect x='" + str(segm.orig_position[0]) + "' y=' " +str(segm.orig_position[1]) + "' "
                                       "width='" + str(segm.size[0]) + "' height='" +str(segm.size[1])+ "' "
                                       "style='stroke: #ff00ff; fill: none;' > "
                            )
                        )
                )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id = segmentation_id,
                creator = creator_tag,
                label = contributor.full_name,
                type = "AnnotationCollection",
                total = 1,
                first = dict(
                    id = segmentation_id + "/1",
                    type = "AnnotationPage",
                    startIndex = 0,
                    items = items
                )
            )
            result.append(segmt)

        for j, s in enumerate(project.screenshot_groups):
            items = []
            segmentation_id = id_root + s.name.replace(" ", "_") + "/"
            for i, segm in enumerate(s.screenshots):
                items.append(dict(
                    id=segmentation_id + "1/" + str(i),
                    type="Annotation"
                )
                )
                full_annotations.append(dict(
                    context="http://www.w3.org/ns/anno.jsonld",
                    id=segmentation_id + "1/" + str(i),
                    motivation="highlighting",
                    creator=creator_tag,
                    type="Annotation",
                    body=dict(
                        type="TextualBody",
                        value="Screenshot",
                        format="text/plain",
                        language="en",
                        purpose="describing"
                    ),
                    generator=generator_tag,
                    target=dict(
                        id=os.path.split(project.movie_descriptor.movie_path)[1],
                        type="Video",
                        selector=dict(
                            type="FragmentSelector",
                            conformsTo="http://www.w3.org/TR/media-frags/",
                            value=os.path.split(project.movie_descriptor.movie_path)[1] + "#t=" + str(
                                segm.get_start() / 1000.0) + "," + str(segm.get_end() / 1000.0)
                        )
                    )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id=segmentation_id,
                creator=creator_tag,
                label=contributor.full_name,
                type="AnnotationCollection",
                total=1,
                first=dict(
                    id=segmentation_id + "/1",
                    type="AnnotationPage",
                    startIndex=0,
                    items=items
                )
            )
            result.append(segmt)

        result.extend(full_annotations)
        with open(file_path, "w") as f:
            json.dump(result, f)

    def import_(self, file_path):
        pass



