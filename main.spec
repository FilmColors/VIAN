# -*- mode: python ; coding: utf-8 -*-
import glob
import sys

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

BUILD_PYTHON_DIR = os.environ['vian_build_dir']
print(BUILD_PYTHON_DIR)

if sys.platform.startswith("win"):
    tf_hidden_imports = collect_submodules('tensorflow_core')
    tf_datas = collect_data_files('tensorflow_core', subdir=None, include_py_files=True)
else:
    tf_hidden_imports = []
    tf_datas = []


librosa_data = collect_data_files('librosa')
binaries = []
binaries += collect_dynamic_libs("pymediainfo")
hiddenimports = [
    'sklearn.utils.sparsetools._graph_validation',
    'sklearn.utils.sparsetools._graph_tools',
    'sklearn.utils.lgamma',
    'sklearn.utils.weight_vector'
    'sklearn.utils.weight_vector'
    'sklearn.neighbors._typedefs'
] + tf_hidden_imports


data_paths = [
    ('data', 'data'),
    ('qt_ui', 'qt_ui'),
    ('flask_server/static', 'flask_server/static'),
    ('flask_server/templates', 'flask_server/templates')
] + tf_datas + librosa_data


console = False
if sys.platform == "win32":
    console = True
    VLC_ROOT = 'C:/Program Files/VideoLAN/VLC/'
    vlc_dlls = [
        (VLC_ROOT + '/libvlc.dll', '.'),
        (VLC_ROOT + '/axvlc.dll', '.'),
        (VLC_ROOT + '/libvlccore.dll', '.'),
        (VLC_ROOT + '/npvlc.dll', '.')
    ]
    data_paths += vlc_dlls
    data_paths += [(os.path.join(BUILD_PYTHON_DIR, "Lib/site-packages/astor/"), "astor/")]
    binaries += [
        (VLC_ROOT + "\plugins", "plugins"),
        (os.path.join(BUILD_PYTHON_DIR, "Lib/site-packages/sklearn/.libs/vcomp140.dll"), "."),
        (os.path.join(BUILD_PYTHON_DIR, "Lib/site-packages/cv2/opencv_videoio_ffmpeg440_64.dll"), ".")
    ]
    icon='qt_ui/images/main_round.ico'

elif sys.platform.startswith("linux"):
    hiddenimports += ['pkg_resources.py2_warn']

else:
    binaries = [
        ('/System/Library/Frameworks/Tk.framework/Tk', 'tk'),
        ('/System/Library/Frameworks/Tcl.framework/Tcl','tcl')
        ]
     #for g in glob.glob("/Applications/VLC.app/Contents/MacOS/lib/*"):
     #   print(g)
     #   binaries.append((g, '.'))
    icon='qt_ui/images/main_round.icns'
    
a = Analysis(['main.py'],
             pathex=['E:\\Programming\\Git\\visual-movie-annotator'],
             binaries=binaries,
             datas=data_paths,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)



print(sys.platform)
if sys.platform.startswith('linux'):
    exe = EXE(pyz,
              a.scripts,
              [],
              exclude_binaries=True,
              name='VIAN',
              debug=True,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              console=False)

    coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='VIAN')
else:
    exe = EXE(pyz,
              a.scripts,
              [],
              exclude_binaries=True,
              name='VIAN',
              debug=True,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              console=console,
              icon=icon)

    coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='VIAN',
               icon=icon)

if sys.platform == "darwin":
    app = BUNDLE(coll,
             name='VIAN.app',
             icon=icon,
             bundle_identifier=None,
             info_plist={
                'NSPrincipalClass': 'NSApplication',
                'NSAppleScriptEnabled': False,
                'CFBundleDocumentTypes': [
                    {
                        'CFBundleTypeName': '.eext',
                        'CFBundleTypeRole':'Editor',
                        'CFBundleTypeIconFile': icon,
                        'LSItemContentTypes': ['com.example.eext'],
                        'LSHandlerRank': 'Owner'
                        }
                    ]
                },)