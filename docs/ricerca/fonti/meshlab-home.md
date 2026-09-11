**MeshLab** the open source system for processing and editing 3D triangular meshes.  
It provides a set of tools for editing, cleaning, healing, inspecting, rendering, texturing and converting meshes. It offers features for processing raw data produced by 3D digitization tools/devices and for preparing models for 3D printing.

## News

### MeshLab 2025.07 and PyMeshLab 2025.7 released! 09/09/2025

MeshLab and PyMeshLab 2025.07 have been released!  
This release brings the support for ARM64 architecture on Linux and MacOS.

Moreover, it includes support for 3mf, several bugfixes and improvements.

### MeshLab 2023.12 and PyMeshLab 2023.12 have been released! 28/02/2022

A new version of MeshLab and PyMeshLab has been released: 2023.12!  
Moreover, MeshLab is now available for download on the Microsoft Store! Check it out [here](https://apps.microsoft.com/detail/9N4TL5DXC6C0?hl=en-US&gl=US)!

  
Additional details about this release can be found [here](https://github.com/cnr-isti-vclab/meshlab/discussions/1449) and [here](https://github.com/cnr-isti-vclab/PyMeshLab/discussions/349).

### New MeshLab and PyMeshLab version: 2022.02 28/02/2022

We released MeshLab and PyMeshLab 2022.02, with new features, bugfixes and improvements! You can check for more details [here](https://github.com/cnr-isti-vclab/meshlab/discussions/1218) and [here](https://github.com/cnr-isti-vclab/PyMeshLab/discussions/187).

### MeshLab and PyMeshLab 2021.10 released 29/10/2021

MeshLab and PyMeshLab 2021.10 have been released, with lot of bugfixes and new features! You can check for more details [here](https://github.com/cnr-isti-vclab/meshlab/discussions/1135) and [here](https://github.com/cnr-isti-vclab/PyMeshLab/discussions/160).

### MeshLab 2021.07 has been released 23/07/2021

MeshLab 2021.07 is out! In this version we introduce support to several file formats (\*.gltf, \*.glb, \*.nxs, \*.nxz, \*.e57) and a brand new plugin for exact mesh booleans. You can download in the [download](#download) section, or in the [github release page](https://github.com/cnr-isti-vclab/meshlab/releases).

You can check all the details regarding the new release [here](https://github.com/cnr-isti-vclab/meshlab/discussions/1041).

### MeshLab 2021.05 released 27/05/2021

MeshLab 2021.05 has been released! You can download in the [download](#download) section, or in the [github release page](https://github.com/cnr-isti-vclab/meshlab/releases).

You can check all the details regarding the new release [here](https://github.com/cnr-isti-vclab/meshlab/discussions/992).  

### New version 2020.12 is out!! 01/12/2020

MeshLab 2020.12 has been released. With this version, we dismiss meshlabserver in favour of [PyMeshLab](https://github.com/cnr-isti-vclab/PyMeshLab), our new Python library for mesh batch processing using MeshLab filters.  
We release also a new version that stores data with double precision. For further details, you can read the [discussion](https://github.com/cnr-isti-vclab/meshlab/discussions/843) in our GitHub page.

**Changelog:**

- lot of bug fixes
- GUI improvements
- new version 2020.12d that stores data with double precision (beta!!)

### MeshLab 2020.07 released 06/07/2020

MeshLab 2020.07 is out! You can download in the [download](#download) section, or in the [github release page](https://github.com/cnr-isti-vclab/meshlab/releases).

**Changelog:**

- new plugin "Global Registration" based on OpenGR library;
- option to reverse wheel direction;
- snap package allows to associate file extensions and to open files on external disks;
- u3d exporter is now more stable and works on every platform;
- removed support for XML plugins and QtScript dependecy;
- VisualSFM (and some other formats) output \*.nvm, \*.rd.out projects supported by meshlabserver
- various bugfixes

### MeshLab 2020.06 released 01/06/2020

MeshLab 2020.06 is out! You can download in the [download](#download) section, or in the [github release page](https://github.com/cnr-isti-vclab/meshlab/releases).

**Changelog:**  
Due to the deprecation of QtScript and all the issues related to it, we are dropping from MeshLab the support to XML plugins, and therefore all the XML plugins have been transformed to classic plugins in this MeshLab version. The involved plugins are:

- Screened Poisson;
- Measure;
- Voronoi;
- Mutualinfo;
- Sketchfab;
Due to this porting, all old.mlx MeshLab scripts that involve one of these plugins may not work on MeshLab and MeshLabServer 2020.06. Starting from MeshLab 2020.07, XML plugins won't compile anymore and they cannot be loaded anymore.  

### New MeshLab 2020.03 and automatic deployment 26/3/2020

We are happy to annouce that MeshLab 2020.03 is out! We set up an automatic system on our [Github repository](https://github.com/cnr-isti-vclab/meshlab) to automatically release a MeshLab version every first day of the month. Ultimate release can be found in the [release page](https://github.com/cnr-isti-vclab/meshlab/releases).

Note for Windows version: before installing MeshLab 2020.03, please uninstall manually any old MeshLab version. This is a known bug of the installer and will be fixed as soon as possible in future versions.

### SGP Software Award 6/6/2017

[![](img/SGP_SW_Award.jpg)](img/SGP_SW_Award.jpg)

We are proud to announce that on July the 6th, at the Eurographics Symposium on Geometry Processing (SGP), MeshLab has been endowed with the prestigious **Eurographics Software Award**!

The award has been given for " *having contributed to the scientific progress in Geometry Processing by making the software available to the public such that others can reproduce the results and further build on them in their own research work* ".

### MeshLab 2016 Released 23/12/2016

After a very long time, a huge rewriting process, and a strongly renewed effort the new MeshLab version is finally out!

- Total rewriting of the internal rendering system. Huge rendering speed ahead!
- Screened Poisson Surface Reconstruction updated to the very latest version.
- New Transformation filters.
- New ways of getting metric information out of your models.
- Transformation matrices are now used more uniformly among filters.
- Alpha value is now used properly by all color-related filters.
- Improvement and typos removal on various help/description texts.
- Direct upload of models on SketchFab
- Raster registration on 3D model based also on 2D/3D correspondences
- Bug-fixing on almost all filters.

## Download

### MeshLab 2025.07

09/09/2025

## Features

- ### {{feature.name}}
	{{feature.description}}

- ### {{feature2.name}}
	{{feature2.description}}

## References

The simplest way to show your appreciation of the MeshLab system is to remember citing it whenever you have used some of its functionalities.  
There are many publications related with MeshLab, in case of doubt use the first one, but, please, look through the list and cite also all the proper ones.  
  
As general info, MeshLab is an open-source system whose development has been led by the [Visual Computing Lab](http://vcg.isti.cnr.it/) of ISTI-CNR since 2005. It has been downloaded more than 3 million times, and, according to updating stats, it is currently used by more than 100,000 users.  
  

| *{{pi.description}}* | *{{pi.paperAuthors}}*   **{{pi.paperTitle}}**   {{pi.paperVenue}}, {{pi.paperYear}} | bibTeX  `{{pi.bibtex}}` |  |
| --- | --- | --- | --- |