import requests
from core.corpus.shared.enums import *
import json

def send_message(command: ServerCommands, message=None):
    try:
        if message is None:
            message = dict()

        msg = (str(command.value) + SPLIT_ITEM + json.dumps(message)).encode()
        msg = requests.post('http://localhost', data=msg, headers=headers).text
        return msg
    except Exception as e:
        raise e

# r = requests.post('http://localhost', data=dict(msg="Hello World"))
# print(r.text)
print(send_message(ServerCommands.Connect))
# archive_file = "F:\\test-zip.zip"
# fin = open(archive_file, 'rb')
# files = {'file': fin}
# try:
#     r = requests.post('http://localhost', files=files)
#     print(r.text)
# finally:
#     fin.close()