from setuptools import setup, find_packages

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
    'numpy'
]

setup(
    name='VIAN',
    version='0.9.3',
    packages=['core', 'core.gui', 'core.gui.misc', 'core.gui.dialogs', 'core.gui.timeline', 'core.data', 'core.data.io',
              'core.analysis', 'core.analysis.audio', 'core.analysis.color', 'core.analysis.colorimetry',
              'core.analysis.movie_mosaic', 'core.analysis.deep_learning', 'core.analysis.pipeline_scripts',
              'core.container', 'core.concurrent', 'core.node_editor', 'core.visualization', 'extensions',
              'extensions.plugins', 'extensions.plugins.fiwi_tools', 'extensions.plugins.imdb_finder',
              'extensions.plugins.refactoring', 'extensions.scripts', 'extensions.analysis', 'extensions.pipelines',
              'flask_server'],
    url='www.vian.app',
    license='GPL',
    author='Gaudenz',
    install_requires=requirements,
    author_email='gaudenz.halter@live.com',
    description='A video annotator with a focus on the aesthetics of film material',
    include_package_data=True
)
