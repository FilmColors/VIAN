#!/usr/bin/env bash

# Activate the Environment
source activate vian_dev

conda install -c anaconda pyqt
conda install -c conda-forge opencv pyqtgraph pyftpdlib
conda install -c anaconda requests, networkx, scikit-learn
pip install dataset
pip install fastcluster

conda install h5py
conda install -c anaconda cudnn
pip3 install tensorflow
pip install keras