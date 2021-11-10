import os
import shutil

# Extract three.js Library to flask_server
shutil.unpack_archive("install/three.zip", os.path.abspath(os.path.join("vian/flask_server", "static")))