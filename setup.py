from setuptools import setup, find_packages
import glob, os

requirements = [
    'tensorflow',
    'keras',
    'sqlalchemy',
    'opencv-contrib-python-headless',
    'requests',
    'PyQt6==5.14.2',
    'PyQtWebEngine==5.14',
    'scikit-learn',
    'flask',
    'fastcluster',
    'moviepy',
    'pandas',
    'librosa',
    'pysrt',
    'bokeh==2.2.1',
    'matplotlib',
    'pymediainfo',
    'XlsxWriter',
    'openpyxl'
]

setup(
    name='VIAN',
    version='0.9.5',
    packages=find_packages(),
    url='www.vian.app',
    license='GPL',
    author='Gaudenz',
    install_requires=requirements,
    author_email='gaudenz.halter@live.com',
    description='A video annotator with a focus on the aesthetics of film material',
    include_package_data=True
)
