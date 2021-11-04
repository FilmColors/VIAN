import os, sys, argparse
import requests

from vian.core.analysis.analysis_import import *
from vian.core.analysis.analysis_utils import run_analysis
from vian.core.container.project import *

EP_BASE = "http://vianweb2.westeurope.cloudapp.azure.com"
EP_UPLOAD = EP_BASE + "/api/upload/upload-project"
EP_LOGIN  = EP_BASE + "/api/user/login"
file_path = ""

gl_progress = None
progress_bar = None


def on_progress(v):
    global progress_bar
    gl_progress.update(progress_bar, completed=v)


def preprocess(file_path, progress):
    """
    Ensure all analyses which the webapp depends on are computed.
    :param file_path:
    :return:
    """
    global progress_bar
    global gl_progress

    gl_progress = progress

    with VIANProject().load_project(file_path) as vian_proj:
        segments = []
        for s in vian_proj.segmentation:
            segments.extend(s.segments)

        progress_bar1 = progress.add_task("[green]Computing ColorPaletteAnalysis...", total=1.0)
        progress_bar = progress_bar1
        run_analysis(vian_proj, ColorPaletteAnalysis(coverage=.01), segments,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)

        progress_bar2 = progress.add_task("[green]Computing ColorFeatureAnalysis...", total=1.0)
        progress_bar = progress_bar2

        run_analysis(vian_proj, ColorFeatureAnalysis(coverage=.01), segments,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)

        print("Semantic Segmentation")

        progress_bar3 = progress.add_task("[green]Computing SemanticSegmentationAnalysis...", total=1.0)
        progress_bar = progress_bar3

        run_analysis(vian_proj, SemanticSegmentationAnalysis(),
                     vian_proj.screenshots,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)
        clobjs = [
            vian_proj.get_classification_object_global("Global"),
            vian_proj.get_classification_object_global("Foreground"),
            vian_proj.get_classification_object_global("Background")
        ]

        print("Color Palettes")
        progress_bar4 = progress.add_task("[green]Computing Screenshot ColorPaletteAnalysis...", total=1.0)
        progress_bar = progress_bar4

        run_analysis(vian_proj, ColorPaletteAnalysis(), vian_proj.screenshots, clobjs, progress_callback=on_progress)

        print("Color Features")
        progress_bar5 = progress.add_task("[green]Computing Screenshot ColorFeatureAnalysis...", total=1.0)
        progress_bar = progress_bar5
        run_analysis(vian_proj, ColorFeatureAnalysis(), vian_proj.screenshots, clobjs, progress_callback=on_progress)

        progress.remove_task(progress_bar1)
        progress.remove_task(progress_bar2)
        progress.remove_task(progress_bar3)
        progress.remove_task(progress_bar4)
        progress.remove_task(progress_bar5)

        vian_proj.store_project()


def upload_project(file_path, token=None, url_override = None, email=None, password=None):
    if token is None:
        assert email is not None and password is not None
        response = requests.post(EP_LOGIN,
                                 json=dict(
                                     email=email, password=password
                                 ))
        token = response.json()['token']

    print(token)

    with VIANProject().load_project(file_path) as vian_proj:
        bake_path = vian_proj.store_project(bake=True)
        archive_path = vian_proj.zip_baked(bake_path)

        # --- Sending the File --
        try:
            if url_override is None:
                url_override = EP_UPLOAD

            fin = open(archive_path, 'rb')
            files = {'file': fin,
                     'json': json.dumps(dict(library="Aleksander", allow_new_keywords = True))}
            print(files, url_override, dict(type="upload", Authorization=token))
            r = requests.post(url_override, files=files, headers=dict(Authorization = token)).text
            print("Redceived", r)
        except Exception as e:
            raise e
            pass

        finally:
            fin.close()






