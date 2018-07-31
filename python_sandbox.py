#
# """
# Very simple HTTP server in python.
# Usage::
#     ./dummy-web-server.py [<port>]
# Send a GET request::
#     curl http://localhost
# Send a HEAD request::
#     curl -I http://localhost
# Send a POST request::
#     curl -d "foo=bar&bin=baz" http://localhost
# """
# from http.server import BaseHTTPRequestHandler, HTTPServer
#
# class S(BaseHTTPRequestHandler):
#     def _set_headers(self):
#         self.send_response(200)
#         self.send_header('Content-type', 'text/html')
#         self.end_headers()
#
#     def do_GET(self):
#         self._set_headers()
#         self.wfile.write(b"<html><body><h1>hi!</h1></body></html>")
#
#     def do_HEAD(self):
#         self._set_headers()
#
#     def do_POST(self):
#         print(self.headers)
#         print(self.rfile)
#         print(self.headers)
#         print(self.headers['Content-Type'])
#         msg = self.rfile.read(int(self.headers['Content-Length']))
#         with open("test.zip", 'wb') as fh:
#             fh.write(msg)
#
#         # Doesn't do anything with posted data
#         self._set_headers()
#         self.wfile.write("OK")
#
#
# def run(server_class=HTTPServer, handler_class=S, port=80):
#     server_address = ('', port)
#     httpd = server_class(server_address, handler_class)
#     print('Starting httpd...')
#     httpd.serve_forever()
#
#
# if __name__ == "__main__":
#     from sys import argv
#
#     if len(argv) == 2:
#         run(port=int(argv[1]))
#     else:
#         run()

import dataset as ds
import pickle
db = ds.connect("sqlite:///F:\\_projects\\3381_1_1_The Wrath of the Gods_1914\\data\\database.sqlite")
r = db["TABLE_ANALYSIS_MASKS"].all()
for q in r:
    print(pickle.loads(q['json']))