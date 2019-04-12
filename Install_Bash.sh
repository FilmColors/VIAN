#!/usr/bin/env bash

# Activate the Environment
source activate vian-env

conda install -c anaconda requests networkx scikit-learn h5py sqlalchemy
conda install -c conda-forge opencv fastcluster pyqt
conda install -c menpo dlib

conda install -c anaconda cudnn
conda install -c conda-forge tensorflow

pip install keras
pip install python-vlc