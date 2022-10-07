# VIAN - Visual Film Annotation (Beta)

![alt text](vian/qt_ui/images/github-title.png)

Welcome to the repo of VIAN, software package for annotating, analysing and 
visualizing color in film. 

## VIAN for Film Scholars
This page hosts the source code of VIAN and is therefore directed towards developers who are interested in VIAN. 
If you are interested in the desktop application, download VIAN from 
[the github releases page](https://github.com/FilmColors/VIAN/releases). 

## VIAN for Developers
If you are interested in the source code or want to contribute to VIAN, you are correct here. 


```conda env create -f requirements.yml```


### Setting up the development environment
1. Clone this repository on your computer
2. Download the models from [OneDrive](https://1drv.ms/f/s!Avol1nnS24kLldQ6sI0KucWUrWWF6g) and copy it into the VIAN/data directory
3. cd to the root of the VIAN directory ```cd path/to/my/VIAN/```
4. Install the corresponding environment (see [below](#step4) for details)
5. Run VIAN ```python vian/main.py```


-----
### <a name="step4"></a>Details for step 4

First, we run the build.py file to setup the directory (in vian directory): ```python build.py```

Then, we create an environment. It needs to be activated and the dependencies installed:

<b>macOS (Intel):</b>
````
python -m venv venv
source venv/bin/activate
python -m pip install requirements.txt
````

<b>macOS (M1):</b>

As not all packages are available via pip, we use a conda environment (e.g. [mambaforge](https://github.com/mamba-org/mamba)). 
````
conda env create -f environment-macos.yml
conda activate vian-osx
````

<b>Windows:</b>
````
python -m venv venv
venv/Scripts/activate
python -m pip install requirements.txt
````

