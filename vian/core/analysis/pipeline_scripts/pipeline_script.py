"""
This is currently a dummy and does not work, it simply emulates the previous behaviour
when pipeline scripts where stored in the project.

"""

import os
from uuid import uuid4
from typing import List

from core.container.container_interfaces import _VIAN_ROOT


with open(os.path.join(_VIAN_ROOT, "data/default_pipeline.py"), "r") as f:
    _PIPELINE_TEMPLATE = f.read()


class PipelineScript():
    _pipeline_script_template = _PIPELINE_TEMPLATE

    def __init__(self, name = "NewScript", author = "no-author", path=None, script=None, unique_id = -1):
        super(PipelineScript, self).__init__(unique_id=unique_id)
        self.name = name
        self.author = author
        self.uuid = None
        self.experiment = None
        if script is None:
            self.script = self._init_script()
        else:
            self.script = script

        self.path = None
        if path is not None:
            self.path = path.replace(".py", "") + ".py"

        self.computation_setting = dict(segments=False, screenshots=False, annotations=False)
        self.pipeline_type = None

    def _init_script(self):
        """ Replaces all placesholders in the pipeline template with the actual values """
        script = self._pipeline_script_template.replace("%PIPELINE_NAME%", self.name.replace(" ", ""))
        script = script.replace("%AUTHOR%", self.author.replace(" ", ""))
        script = script.replace("%UUID%", str(uuid4))
        return script

    def set_project(self, project):
        super(PipelineScript, self).set_project(project)
        if self.path is None:
            if self.project.folder is not None:
                self.path = os.path.join(self.project.folder, self.name + ".py")
            else:
                self.path = self.name + ".py"

    def import_pipeline(self):
        try:
            self.save_script(self.path)
            spec = importlib.util.spec_from_file_location(self.name + "_pipeline_module", self.path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[self.name + "_pipeline_module"] = module
            r = spec.loader.exec_module(module)
            log_info("Imported OProject Pipeline:", self.name, module)
            return "Successfully imported module"
        except Exception as e:
            return traceback.format_exc()
            pass

    def save_script(self, path=None):
        """ Saves the python script at a given location, if none is given it is stored at PipelineScript.path"""
        try:
            if path is None:
                path = self.path.replace(".py", "") + ".py"
            with open(path, "w") as f:
                f.write(self.script.replace("\t", "    "))
        except OSError as e:
            log_error(traceback.format_exc())
        return path

    # def serialize(self):
    #     """ Returns a dict of json serializable values """
    #     return dict(
    #         name=self.name,
    #         unique_id = self.unique_id,
    #         script = self.script,
    #         computation_settings = self.computation_setting
    #     )
    #
    # def deserialize(self, serialization, folder):
    #     """ Applies a dict of json serializable values to this instance """
    #     self.name = serialization['name']
    #     self.unique_id = serialization['unique_id']
    #     self.script = serialization['script']
    #     self.path = os.path.join(folder, self.name.replace(".py", "") + ".py")
    #     self.computation_setting = serialization['computation_settings']
    #     return self

    def __eq__(self, other):
        print(self.name, other.name)
        return self.name == other.name and self.script == other.script



class PipelineScriptManager:
    def __init__(self, main_window):
        self.pipeline_scripts = []  # type:List[PipelineScript]
        self.project = None

    def create_pipeline_script(self, name: str, author="no_author", path=None, script=None,
                               unique_id=-1) -> PipelineScript:
        """
        Creates a new PipelineScript given a name and a script content
        :param name: The name of the script
        :param script: The actual python script text
        :return: a PipelineScript class
        """
        pipeline_script = PipelineScript(name, author, path=path, script=script, unique_id=unique_id)
        return self.add_pipeline_script(pipeline_script)

    def add_pipeline_script(self, script: PipelineScript) -> PipelineScript:
        """
        Adds a script at a given path to the project.

        :param path: Path to the pipeline python script.
        :return: None
        """
        for s in self.pipeline_scripts:
            if s.name == script.name and s.script == script.script:
                return s

        self.pipeline_scripts.append(script)
        script.set_project( self.project)
        return script

    def remove_pipeline_script(self, script: PipelineScript):
        """
        Removes a given script path from the project.

        :param path: The path to remove.
        :return: None
        """

        if script in self.pipeline_scripts:
            self.pipeline_scripts.remove(script)