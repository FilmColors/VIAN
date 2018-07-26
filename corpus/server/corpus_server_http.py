from glob import glob

from http.server import BaseHTTPRequestHandler, HTTPServer
from core.corpus.shared.enums import *
from core.corpus.shared.corpusdb import DatasetCorpusDB
from core.corpus.shared.entities import *

from core.data.headless import load_project_headless


class HandlerClass(BaseHTTPRequestHandler):
    local_corpus = None

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(b"<html><body><h1>hi!</h1></body></html>")

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        print(self.headers)
        msg = self.rfile.read(int(self.headers['Content-Length']))
        if self.headers['type'] == "upload":
            with open(self.local_corpus.ftp_dir +"/temp.zip", 'wb') as fh:
                fh.write(msg)
            result = json.dumps(dict(success=True, path=self.local_corpus.ftp_dir + "/temp.zip")).encode()
            self._set_headers()
            self.wfile.write(result)

        elif self.headers['type'] == "command":
            print("Received:", msg.decode())
            result = self.parse_message(msg)
        # Doesn't do anything with posted data
            self._set_headers()
            self.wfile.write(result)

        elif self.headers['type'] == "query":
            self.local_corpus.parse_query(msg.decode())

    def parse_message(self, msg):
        msg = msg.decode()
        msg = msg.split(SPLIT_ITEM)

        task = ServerCommands(int(msg[0]))
        data = json.loads(msg[1])

        response_type = ServerResponses.Failed
        response_data = dict()

        if task == ServerCommands.Connect:
            try:
                in_user = DBContributor().from_database(data['user'])

                response_data = dict(
                    success = True,
                    projects = [p.to_database(True) for p in self.local_corpus.get_projects()],
                    user = self.local_corpus.connect_user(in_user).to_database(True),
                    corpus_name=self.local_corpus.name
                )


            except Exception as e:
                print("Exception in ServerCommands.Connect" + str(e))
                response_data =  dict(
                    success = False,
                    projects = None,
                    user = None,
                    corpus_name=None
                )

        elif task == ServerCommands.Disconnect:
            try:
                in_user = DBContributor().from_database(data['user'])
                response_data = dict(path=self)
            except Exception as e:
                print("Exception in ServerCommands.Disconnect" + str(e))

        # Creates a new remote Project from a local project.
        elif task == ServerCommands.Commit_Inquiry:
            try:
                in_user = DBContributor().from_database(data['user'])
                response_data = dict(success=True, path=self.local_corpus.ftp_dir)
            except Exception as e:
                print("Exception in ServerCommands.Commit_Inquiry" + str(e))
                response_data = dict(success=False, path="")

        elif task == ServerCommands.Commit_Finished:
            try:
                archive = data['archive']
                contributor = DBContributor().from_database(data['user'])

                success, dbproject = self.local_corpus.commit_project(archive, contributor)
                response_data = dict(success=success, path=self.local_corpus.ftp_dir, dbproject=dbproject.to_database(True))

            except Exception as e:
                response_data = dict(success=False, path="")
                print("Exception in ServerCommands.Commit_Finished: " + str(e))

        # Removes a remote Project
        elif task == ServerCommands.Remove_Project:
            pass

        # Clones a remote Project to the local machine
        elif task == ServerCommands.Check_Out_Inquiry:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                success, archive = self.local_corpus.checkout_project(project.project_id, user)

                response_data = dict(
                    success=success,
                    dbprojects=[p.to_database(True) for p in self.local_corpus.get_projects()],
                )
            except Exception as e:
                print("Exception in ServerCommands.Check_Out_Inquiry: " + str(e))
                response_data = dict(
                    success=False,
                    projects=None,
                )

        # Unlocks a Remote Project for other Users
        elif task == ServerCommands.Check_In_Project:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                success = self.local_corpus.checkin_project(project.project_id, user)

                response_data = dict(
                        success = success,
                        dbprojects = [p.to_database(True) for p in self.local_corpus.get_projects()],
                    )
            except Exception as e:
                print("Exception in ServerCommands.Check_In_Project: " + str(e))
                response_data = dict(
                    success=False,
                    projects=None,
                )


        elif task == ServerCommands.Download_Project:

            try:
                project = DBProject().from_database(data['dbproject'])
                user = DBContributor().from_database(data['user'])
                archive = self.local_corpus.get_project_path(project)
                download_file = self.local_corpus.ftp_dir + os.path.split(archive)[1]
                print("Download File: ", download_file)
                shutil.copy2(archive, download_file)
                response_data = dict(
                    success=True,
                    path = os.path.split(archive)[1],
                )
            except Exception as e:
                print("Exception in ServerCommands.Download_Project: " + str(e))
                response_data = dict(
                    success=False,
                    path = ""
                )


        elif task == ServerCommands.Get_CheckOut_State:
            try:
                user = DBContributor().from_database(data['user'])
                project = DBProject().from_database(data['dbproject'])
                db_project = self.local_corpus.get_project(project.project_id)

                if db_project is None:
                    response_data = dict(
                        success=False,
                        dbproject=None,
                    )
                else:
                    response_data = dict(
                        success=True,
                        dbproject=db_project.to_database(True),
                    )
            except Exception as e:
                print("Exception in ServerCommands.Get_CheckOut_State: " + str(e))
                response_data = dict(
                    success=False,
                    dbproject=None,
                )

        result = json.dumps(response_data).encode()
        return result

class CorpusServer(QObject):
    def __init__(self, parent):
        super(CorpusServer, self).__init__(parent)
        self.active = True
        self.local_corpus = DatasetCorpusDB()
        self.local_corpus.load(
            "C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\TestCorpus_01\\TestCorpus_01.vian_corpus")

    @pyqtSlot()
    def listen(self):
        self.run()

    @pyqtSlot()
    def run(self, port=80):
        server_address = ('', port)
        HandlerClass.local_corpus = self.local_corpus
        httpd = HTTPServer(server_address, HandlerClass)
        print('Starting http server...')
        httpd.serve_forever()










