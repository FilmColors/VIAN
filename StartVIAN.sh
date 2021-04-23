#!/bin/bash


MiniCondaDir="miniconda/"

if ! [ -d "$MiniCondaDir" ]; then
    echo $MiniCondaDir
    curl https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o miniconda.sh
    bash miniconda.sh -b -p $MiniCondaDir
    $MiniCondaDir/bin/conda create --name vian python==3.6
    $MiniCondaDir/bin/conda activate vian
    $MiniCondaDir/bin/pip install -r requirements.txt

fi


$MiniCondaDir/bin/python main.py
