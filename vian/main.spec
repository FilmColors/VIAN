# -*- mode: python ; coding: utf-8 -*-
import glob
import sys
import json
import os

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

if sys.platform.startswith("win"):
    tf_hidden_imports = collect_submodules('tensorflow')
    mp_hidden_imports = collect_submodules('moviepy')
    flask_hidden_imports = collect_submodules('flask_server')
    tf_datas = collect_data_files('tensorflow', subdir=None, include_py_files=True)
else:
    tf_hidden_imports = []
    mp_hidden_imports = []
    flask_hidden_imports = []
    tf_datas = []

librosa_data = collect_data_files('librosa')

binaries = []
binaries += collect_dynamic_libs("pymediainfo")

hiddenimports = [
    'sklearn.utils.sparsetools._graph_validation',
    'sklearn.utils.sparsetools._graph_tools',
    'sklearn.utils.lgamma',
    'sklearn.utils.weight_vector',
    'sklearn.utils.weight_vector',
    'sklearn.neighbors._typedefs'
] + tf_hidden_imports + mp_hidden_imports + flask_hidden_imports

data_paths = [
    ('data', 'data'),
    ('qt_ui', 'qt_ui'),
    ('flask_server/static', 'static'),
    ('flask_server/templates', 'templates')
] + tf_datas + librosa_data


console = False
if sys.platform == "win32":
    console = True
    vlc_dlls = [
        ('../bin/win64/libvlc.dll', '.'),
        ('../bin/win64/axvlc.dll', '.'),
        ('../bin/win64/libvlccore.dll', '.'),
        ('../bin/win64/npvlc.dll', '.')
    ]
    data_paths += vlc_dlls

    binaries += [
        ('../bin/win64/plugins', 'plugins'),
        ('../bin/win64/vcomp140.dll', '.'),
        ('../bin/win64/opencv_videoio_ffmpeg453_64.dll', '.')
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
             pathex=[],
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


# make sure that we are not in dev_mode anymore
config_path = os.path.join(os.getcwd(), 'dist', 'VIAN', 'data', 'config.json')
with open(config_path, 'r+') as f:
    data = json.load(f)
    data['dev_mode'] = 0
    f.seek(0)
    json.dump(data, f, indent=4)
    f.truncate()
