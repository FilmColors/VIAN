# VIAN - Visual Film Annotation

![alt text](qt_ui/images/github-title.png)

Welcome to the repo of VIAN, software package for annotating, analysing and 
visualizing color in film. 

## VIAN for Film Scholars
This page hosts the source code of VIAN and is therefore directed towards developers who are interested in VIAN. 
If you are interested in the desktop application, please visit 
[this page](http://ercwebapp.westeurope.cloudapp.azure.com/vian) 
to download VIAN for users. 

## VIAN for Developers
If you are interested in the source code or want to contribute to VIAN, you are correct here. 

### Prerequisites
- Download and install [Anaconda](https://www.anaconda.com/distribution/)
- Download and install [VLC 64-bit](https://www.videolan.org/vlc/index.html)

---

***Note***

    You can also install VIAN with a another python 3 distribution than anaconda, however
    this is not tested yet, so no guarantees. 
    
---

### Setting up the development environment
1. Clone this repository on your computer
2. cd to the root of the VIAN directory

```cd path/to/my/VIAN/```
3. Install the corresponding environment:

<b>OSX:</b>
```conda env create -f install/env/env_osx_dl.yml``` 

<b>Windows:</b>
```conda env create -f install/env/env_win64_dl.yml``` 

After the installation is complete, you can start VIAN by activating the new environment
and run main.py

<b>OSX:</b>
````
conda activate vian-osx
python main.py
````

<b>Windows:</b>
````
conda activate vian-win
python main.py
````

