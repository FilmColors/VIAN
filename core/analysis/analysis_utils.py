from threading import Lock
from core.data.interfaces import IAnalysisJob
from core.container.container_interfaces import IProjectContainer
from typing import List, Dict
from core.container.project import ClassificationObject, VIANProject

from multiprocessing import Pool

PROJECT_LOCK = Lock()


def progress_dummy(args, **kwargs):
    pass


def run_analysis(project:VIANProject, analysis: IAnalysisJob, targets: List[IProjectContainer],
                 class_objs: List[ClassificationObject]=None):
    fps = project.movie_descriptor.fps

    if class_objs is None:
        class_objs = project.get_classification_object_global("Global")

    if not isinstance(class_objs, list):
        class_objs = [class_objs]

    for clobj in class_objs:
        args = analysis.prepare(project, targets, fps, clobj)

        res = []
        if analysis.multiple_result:
            for i, arg in enumerate(args):
                res.append(analysis.process(arg, progress_dummy))
        else:
            res = analysis.process(args, progress_dummy)

        if isinstance(res, list):
            for r in res:
                with PROJECT_LOCK:
                    analysis.modify_project(project, r)
                    project.add_analysis(r)
        else:
            with PROJECT_LOCK:
                analysis.modify_project(project, res)
                project.add_analysis(res)

