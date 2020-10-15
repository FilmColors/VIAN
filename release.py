import sys
import os
import shutil

BUILD_PYTHON_WIN = "C:/Users/gaude/AppData/Local/Programs/Python/Python36/python.exe"
BUILD_PYTHON_OSX = "/Users/Kris/Documents/Gaudenz/vian_env/bin/python"
BUILD_PYTHON_OSX = "venv37/bin/python"

SPEC_FILE = "main.spec"

arguments = ["-y", "--debug=all", "--additional-hooks-dir=hooks"]
if sys.platform.startswith("win"):
    build_python = BUILD_PYTHON_WIN
    build_dir = os.path.split(build_python)[0]
    build_archive = "VIAN-Windows-64bit"
    pyinstaller = os.path.join(build_dir, "Scripts/pyinstaller")

elif sys.platform.startswith("darwin"):
    arguments += ["--windowed"]
    build_python = BUILD_PYTHON_OSX
    build_archive = "VIAN-OSX"

    build_dir = os.path.split(build_python)[0]
    pyinstaller = os.path.join(build_dir, "pyinstaller")

os.environ['vian_build_dir'] = build_dir

cmd = [pyinstaller, SPEC_FILE]
cmd += arguments

cmd = " ".join(cmd)
print("Building: ", cmd)
os.system(cmd)

print("Zipping")
build_archive = "dist/" + build_archive
if os.path.isfile(build_archive):
    os.remove(build_archive)

if sys.platform == "darwin":
    shutil.make_archive(build_archive, "zip", "dist/VIAN.app")
else:
    shutil.make_archive(build_archive, "zip", "dist/VIAN")
print("Done")