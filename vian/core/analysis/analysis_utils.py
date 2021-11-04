from threading import Lock
from vian.core.data.interfaces import IAnalysisJob
from vian.core.container.container_interfaces import BaseProjectEntity
from typing import List, Dict
from vian.core.container.project import ClassificationObject, VIANProject

PROJECT_LOCK = Lock()


def progress_dummy(args, **kwargs):
    pass


def run_analysis(project:VIANProject,
                 analysis: IAnalysisJob,
                 targets: List[BaseProjectEntity],
                 class_objs: List[ClassificationObject]=None,
                 progress_callback=None,
                 override = True):

    if progress_callback is None:
        progress_callback = progress_dummy

    fps = project.movie_descriptor.fps

    if not isinstance(class_objs, list):
        class_objs = [class_objs]

    n, n_total = 0, len(class_objs) * len(targets)

    for clobj in class_objs:

        if override is False:
            tgts = []
            for t in targets:
                ret = t.get_connected_analysis(analysis.__class__, as_clobj_dict=True)
                if clobj in ret:
                    continue
                tgts.append(t)
        else:
            tgts = targets
        args = analysis.prepare(project, tgts, fps, clobj)
        res = []
        if analysis.multiple_result:
            for i, arg in enumerate(args):
                progress_callback(n / n_total)
                res.append(analysis.process(arg, progress_dummy))
                n += 1
        else:
            res = analysis.process(args, progress_callback)

        if isinstance(res, list):
            for r in res:
                if r is not None:
                    with PROJECT_LOCK:
                        analysis.modify_project(project, r)
                        project.add_analysis(r)
        else:
            if res is not None:
                with PROJECT_LOCK:
                    analysis.modify_project(project, res)
                    project.add_analysis(res)

    progress_callback(1.0)
