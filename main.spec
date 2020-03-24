# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


hiddenimports_SKLEARN = [
    'sklearn.utils.sparsetools._graph_validation',
    'sklearn.utils.sparsetools._graph_tools',
    'sklearn.utils.lgamma',
    'sklearn.utils.weight_vector'
    'sklearn.neighbors._typedefs'
]

data_paths = [
    ('data', 'data'),
    ('qt_ui', 'qt_ui')
]


import sys
if sys.platform == "win32":
    VLC_ROOT = 'C:/Program Files/VideoLAN/VLC/'
    vlc_dlls = [
        (VLC_ROOT + '/libvlc.dll', '.'),
        (VLC_ROOT + '/axvlc.dll', '.'),
        (VLC_ROOT + '/libvlccore.dll', '.'),
        (VLC_ROOT + '/npvlc.dll', '.')
    ]
    data_paths += vlc_dlls
    binaries = [
        (VLC_ROOT + "\plugins", "plugins")
    ]

a = Analysis(['main.py'],
             pathex=['E:\\Programming\\Git\\visual-movie-annotator'],
             binaries=binaries,
             datas=data_paths,
             hiddenimports=hiddenimports_SKLEARN,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)


exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='VIAN - A visual movie annotator',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True)


coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='main')
