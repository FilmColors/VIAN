from PyQt5.QtCore import QObject
from core.data.corpus_client import check_erc_template



class ERCUpdateJob(QObject):
    def __init__(self):
        super(ERCUpdateJob, self).__init__()

    def run_concurrent(self, project, callback):
        check_erc_template(project)
