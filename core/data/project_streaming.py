import os
import shelve

from core.data.interfaces import IConcurrentJob


class ProjectStreamer():
    def __init__(self, main_window):
        self.stream_path = ""
        self.stream = None
        self.main_window = main_window
        pass

    def set_project(self, project):
        p = str(project.path)
        p = p.replace("\\", "/").split("/")
        p.pop()
        p = "/".join(p)
        path = p
        name = project.name

        self.stream_path = path + "/." + name
        self.stream = shelve.open(self.stream_path, writeback=True)

    def release_project(self):
        self.stream.close()
        self.stream = None
        self.stream_path = ""

        # Removing the temporary File
        try:
            os.remove(self.stream_path)
        except:
            self.main_window.print_message("No Streaming File Found", "Orange")

    def to_stream(self, unique_id, object):
        job = ProjectToStreamJob([self.stream, unique_id, object])
        self.main_window.run_job_concurrent(job)

        # if self.stream is not None:
        #     self.stream[str(unique_id)] = object



    def from_stream(self, unique_id):
        if self.stream is not None:
            return self.stream[str(unique_id)]


class ProjectToStreamJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        stream = args[0]
        unique_id = args[1]
        obj = args[2]

        if stream is not None:
            stream[str(unique_id)] = obj

