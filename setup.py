from setuptools import setup, find_packages
import glob

requirements = [
    'tensorflow',
    'keras',
    'sqlalchemy',
    'opencv-contrib-python-headless',
    'requests',
    'PyQt5==5.14.2',
    'PyQtWebEngine==5.14',
    'scikit-learn',
    'flask',
    'fastcluster',
    'moviepy',
    'python-vlc',
    'librosa',
    'bokeh==2.2.1',
    'matplotlib',
    'numpy',
    'pymediainfo'
    'pandas'
]

print(glob.glob('vian/data/**', recursive=True))
setup(
    name='VIAN',
    version='0.9.5',
    packages=['vian.core',
              'vian.core.gui',
              'vian.core.gui.misc',
              'vian.core.gui.dialogs',
              'vian.core.gui.timeline',
              'vian.core.data',
              'vian.core.data.io',
              'vian.core.analysis',
              'vian.core.analysis.audio',
              'vian.core.analysis.color',
              'vian.core.analysis.colorimetry',
              'vian.core.analysis.movie_mosaic',
              'vian.core.analysis.deep_learning',
              'vian.core.analysis.pipeline_scripts',
              'vian.core.analysis.eyetracking',
              'vian.core.analysis.motion',
              'vian.core.container',
              'vian.core.concurrent',
              'vian.core.node_editor',
              'vian.core.visualization',
              'vian.extensions',
              'vian.extensions.plugins',
              'vian.extensions.plugins.fiwi_tools',
              'vian.extensions.plugins.imdb_finder',
              'vian.extensions.plugins.refactoring',
              'vian.extensions.scripts',
              'vian.extensions.analysis',
              'vian.extensions.pipelines',
              'vian.flask_server'
              ],
    url='www.vian.app',
    data_files=[('data', glob.glob('vian/data/**.*', recursive=True))],
    license='GPL',
    author='Gaudenz',
    install_requires=requirements,
    author_email='gaudenz.halter@live.com',
    description='A video annotator with a focus on the aesthetics of film material',
    include_package_data=True
)
