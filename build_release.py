import sys
import os
import shutil

BUILD_PYTHON_WIN = "C:/Users/gaude/AppData/Local/Programs/Python/Python36/python.exe"

SPEC_FILE = "main.spec"

arguments = ["-y"]
if sys.platform.startswith("win"):
    build_python = BUILD_PYTHON_WIN
    build_archive = "VIAN-Windows-64bit"

build_dir = os.path.split(build_python)[0]
os.environ['vian_build_dir'] = build_dir

cmd = [os.path.join(build_dir, "Scripts/pyinstaller"), SPEC_FILE]
cmd += arguments

cmd = " ".join(cmd)
print("Building: ", cmd)
os.system(cmd)

print("Zipping")
build_archive = "dist/" + build_archive
if os.path.isfile(build_archive):
    os.remove(build_archive)
shutil.make_archive(build_archive, "zip", "dist/VIAN")
print("Done")