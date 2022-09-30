# -*- mode: python ; coding: utf-8 -*-
import glob
import shutil
import sys
import json
import os

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

os.environ["IMAGEIO_FFMPEG_EXE"] = "/Users/pascalforny/mambaforge/envs/vian-conda/lib/python3.8/site-packages"

mp_hidden_imports =  collect_submodules('moviepy')
flask_hidden_imports = collect_submodules('flask_server')
sklearn_hidden_imports = collect_submodules('sklearn')

# Pyinstallers looks for the dynlibs in the site-packages directory due to how
# pymediainfo loads the libraries. They are however installed in the libs folder, hence we have to copy them manually

# If the dynlibs are not locaterd in site-packages/pymediainfo,
# copy them from /Users/pascalforny/mambaforge/pkgs/libmediainfo-21.09-hb918e4c_2/lib/
CONDA_ROOT = os.path.abspath(os.environ['CONDA_EXE'] + '/../../')
to_copy = f'{CONDA_ROOT}/pkgs/libmediainfo-21.09-hb918e4c_2/lib/'
if not os.path.isdir(to_copy):
    raise ValueError(f'{to_copy} does not exist in the conda isntallation. '
                     'have you updated pymediainfo?')

for f in glob.glob(to_copy + '/*.dylib'):
    dest = f'{CONDA_ROOT}/envs/vian-conda/lib/python3.8/site-packages/pymediainfo/{os.path.basename(f)}'
    shutil.copy(f, dest)


binaries = [('/Users/pascalforny/mambaforge/pkgs/libmediainfo-21.09-hb918e4c_2/lib/', 'pymediainfo/')]

hiddenimports = mp_hidden_imports \
                + flask_hidden_imports \
                + sklearn_hidden_imports

data_paths = [
    ('data', 'data'),
    ('qt_ui', 'qt_ui'),
    ('flask_server/static', 'static'),
    ('flask_server/templates', 'templates'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/python3.8/site-packages/librosa/util/example_data', 'librosa/util/example_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libsndfile.dylib', '_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libogg.0.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libFLAC.8.3.0.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libFLAC.8.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libvorbis.0.4.9.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libvorbis.0.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libvorbisenc.2.0.12.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libopus.0.dylib','_soundfile_data'),
    ('/Users/pascalforny/mambaforge/envs/vian-conda/lib/libvorbisenc.2.dylib','_soundfile_data')

] + collect_data_files('librosa')


console = False
if sys.platform == "win32":
    console = True

    binaries += [
        ('../bin/win64/plugins', 'plugins'),
        ('../bin/win64/vcomp140.dll', '.'),
    ]
    binaries += collect_dynamic_libs('cv2')

    icon = 'qt_ui/images/main_round.ico'

elif sys.platform.startswith("linux"):
    hiddenimports += ['pkg_resources.py2_warn']

else:
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
                
#make sure that we are not in dev_mode anymore
config_path = os.path.join(os.getcwd(), 'dist', 'VIAN', 'data', 'config.json')
with open(config_path, 'r+') as f:
    data = json.load(f)
    data['dev_mode'] = "false"
    f.seek(0)
    json.dump(data, f, indent=4)
    f.truncate()
