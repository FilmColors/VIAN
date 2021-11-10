
#!/bin/bash


echo "Positional Parameters"
echo $1


MiniCondaDir=$1"/miniconda/"
echo "CondaDir:" $MiniCondaDir
conda_path=$(echo $PATH | cut -d ":" -f2);
echo $conda_path

echo "Downloading Conda"
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o $1/miniconda.sh
bash $1/miniconda.sh -b -p $MiniCondaDir
export PATH="$MiniCondaDir/bin:$PATH"
$MiniCondaDir/bin/conda env create -f $1/src/install/env/env_osx.yml 
$MiniCondaDir/bin/conda clean --all -y