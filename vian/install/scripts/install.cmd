miniconda\Scripts\conda create --prefix miniconda/envs/vian-win
miniconda\Scripts\activate vian-win

conda install -c anaconda tensorflow keras requests networkx scikit-learn sqlalchemy h5py pyqt
conda install -c conda-forge fastcluster librosa
conda install -c defaults opencv

pip install moviepy
