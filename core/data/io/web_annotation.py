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
        keywords = []
        selectors = dict()

        for j, s in enumerate(project.segmentation):
            items = []
            segmentation_id = id_root + s.name.replace(" ", "_") + "/"
            for i, segm in enumerate(s.segments): #type: Segment
                items.append(dict(
                    id = segmentation_id + "1/" +  str(i),
                    type="Annotation"
                    )
                )

                selectors[segm.unique_id] = dict(
                            type="FragmentSelector",
                            conformsTo="http://www.w3.org/TR/media-frags/",
                            value = os.path.split(project.movie_descriptor.movie_path)[1] +
                                    "#t=" + str(segm.get_start()/1000.0) + "," + str(segm.get_end()/1000.0)
                        )
                self._add_keyword(keywords, project, segm, selectors[segm.unique_id], creator_tag,
                                  generator_tag)
                full_annotations.append(dict(
                    context = "http://www.w3.org/ns/anno.jsonld",
                    id= segmentation_id + "1/" +  str(i),
                    motivation = "describing",
                    creator = creator_tag,
                    type = "Annotation",
                    body = dict(
                        type = "TextualBody",
                        value = segm.get_first_annotation_string(),
                        format = "text/plain",
                        language = "en",
                        purpose = "describing"
                    ),
                    generator = generator_tag,
                    target = dict(
                        id = os.path.split(project.movie_descriptor.movie_path)[1],
                        type = "Video",
                        selector = selectors[segm.unique_id]
                )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id = segmentation_id,
                creator = creator_tag,
                label = contributor.full_name,
                type = "AnnotationCollection",
                vian_type = "Segmentation",
                vian_info = "A group of temporal annotations",
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
                selectors[segm.unique_id] = dict(
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
                self._add_keyword(keywords, project, segm, selectors[segm.unique_id], creator_tag,
                                  generator_tag)
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
                        selector = selectors[segm.unique_id]
                )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id = segmentation_id,
                creator = creator_tag,
                label = contributor.full_name,
                type = "AnnotationCollection",
                vian_type="AnnotationLayer",
                vian_info="A group of svg annotations",
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
                selectors[segm.unique_id] = dict(
                            type="FragmentSelector",
                            conformsTo="http://www.w3.org/TR/media-frags/",
                            value=os.path.split(project.movie_descriptor.movie_path)[1] + "#t=" + str(
                                segm.get_start() / 1000.0) + "," + str(segm.get_end() / 1000.0)
                        )
                self._add_keyword(keywords, project, segm, selectors[segm.unique_id], creator_tag,
                                  generator_tag)
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
                        selector = selectors[segm.unique_id]
                    )))

            segmt = dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id=segmentation_id,
                creator=creator_tag,
                label=contributor.full_name,
                type="AnnotationCollection",
                vian_type="ScreenshotGroup",
                vian_info="A group of screenshots",
                total=1,
                first=dict(
                    id=segmentation_id + "/1",
                    type="AnnotationPage",
                    startIndex=0,
                    items=items
                )
            )

            result.append(segmt)

        for j, s in enumerate(project.analysis): #type:IAnalysisJobAnalysis
            if isinstance(s, ColormetryAnalysis):
                continue

            analysis_id = id_root + "Analysis" + "/"
            hdf5_location = project.hdf5_manager.get_location(s.unique_id)
            full_annotations.append(dict(
                context="http://www.w3.org/ns/anno.jsonld",
                id=analysis_id + "1/" + str(j),
                motivation="describing",
                creator=creator_tag,
                type="Annotation",
                body=dict(
                    type="VIANAnalysis",
                    value= dict(
                        hdf5_dataset=hdf5_location[0],
                        hdf5_index = hdf5_location[1]
                        ),
                    format="hdf5",
                    language="en",
                    purpose="describing"
                ),
                generator=generator_tag,
                target=dict(
                    id=os.path.split(project.movie_descriptor.movie_path)[1],
                    type="Video",
                    selector=selectors[s.target_container.unique_id]
                )))


        result.extend(full_annotations)
        result.extend(keywords)
        with open(file_path, "w") as f:
            json.dump(result, f)

    def import_(self, file_path):
        pass

    def _add_keyword(self, keywords, project, container, selector, creator_tag, generator_tag):
        for i, k in enumerate(container.tag_keywords): #type:UniqueKeyword
            url = ""
            if k.external_id is not None:
                url = "http://ercwebapp.westeurope.cloudapp.azure.com/api/vocabularies/get_concept/"  + str(k.external_id)
            keywords.append(dict(
                    context = "http://www.w3.org/ns/anno.jsonld",
                    id= "Keyword" + "/1/" + str(len(keywords)),
                    motivation = "classification",
                    creator = creator_tag,
                    type = "Annotation",
                    body = dict(
                        type = "TextualBody",
                        value = k.get_full_name(),
                        format = "text/plain",
                        language = "en",
                        purpose = "classification",
                        url = url
                    ),
                    generator = generator_tag,
                    target = dict(
                        id = os.path.split(project.movie_descriptor.movie_path)[1],
                        type = "Video",
                        selector = selector
                )))
