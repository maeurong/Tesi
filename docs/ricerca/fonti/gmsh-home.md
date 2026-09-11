## Gmsh

## A three-dimensional finite element mesh generator with built-in pre- and post-processing facilities

#### Christophe Geuzaine and Jean-François Remacle

Gmsh is an open source 3D finite element mesh generator with a built-in CAD engine and post-processor. Its design goal is to provide a fast, light and user-friendly meshing tool with parametric input and flexible visualization capabilities. Gmsh is built around [four modules](doc/texinfo/gmsh.html#Overview-of-Gmsh) (geometry, mesh, solver and post-processing), which can be controlled with the [graphical user interface](doc/texinfo/gmsh.html#Gmsh-graphical-user-interface), from the [command line](doc/texinfo/gmsh.html#Gmsh-command_002dline-interface), using text files written in Gmsh's own [scripting language](doc/texinfo/gmsh.html#Gmsh-scripting-language) (`.geo` files), or through the C++, C, Python, Julia and Fortran [application programming interface](doc/texinfo/gmsh.html#Gmsh-application-programming-interface).

See this [general presentation](doc/course/general_overview.pdf) for a high-level overview of Gmsh and the [reference manual](doc/texinfo/gmsh.html) for the complete documentation, which includes the [Gmsh tutorial](doc/texinfo/gmsh.html#Gmsh-tutorial). The [source code repository](https://gitlab.onelab.info/gmsh/gmsh/) contains the [tutorial source files](https://gitlab.onelab.info/gmsh/gmsh/tree/master/tutorials) as well as many [other](https://gitlab.onelab.info/gmsh/gmsh/tree/master/benchmarks) [examples](https://gitlab.onelab.info/gmsh/gmsh/tree/master/examples).

## Download

Gmsh is distributed under the terms of the [GNU General Public License (GPL)](LICENSE.txt):

- ```
	Current stable release (version 4.15.2, 24 March 2026):
	  Download Gmsh for
	    Windows,
	    Linux,
	    macOS (x86) or
	    macOS (ARM)
	    *
	  Download the source code
	  Download the Software Development Kit (SDK) for
	    Windows,
	    Linux,
	    macOS (x86) or
	    macOS (ARM)
	     *
	  Download both Gmsh and the SDK with pip: 'pip install
	      --upgrade gmsh'
	```
	*Make sure to read the [tutorial](doc/texinfo/gmsh.html#Gmsh-tutorial) and the [FAQ](doc/texinfo/gmsh.html#Frequently-asked-questions) before sending questions or bug reports.*
- Development version:
	- Download the latest automatic Gmsh snapshot for [Windows](bin/Windows/gmsh-git-Windows64.zip), [Linux](bin/Linux/gmsh-git-Linux64.tgz), [macOS (x86)](bin/macOS/gmsh-git-MacOSX.dmg) or [macOS (ARM)](bin/macOS/gmsh-git-MacOSARM.dmg) [<sup>*</sup>](#1)
		- Download the latest automatic [source code](src/gmsh-git-source.tgz) snapshot
		- Download the latest automatic SDK snapshot for [Windows](bin/Windows/gmsh-git-Windows64-sdk.zip), [Linux](bin/Linux/gmsh-git-Linux64-sdk.tgz), [macOS (x86)](bin/macOS/gmsh-git-MacOSX-sdk.tgz) or [macOS (ARM)](bin/macOS/gmsh-git-MacOSARM-sdk.tgz) [<sup>*</sup>](#1)
		- Access the Git repository: ' `git clone           https://gitlab.onelab.info/gmsh/gmsh.git` '
		- Download the latest automatic snapshot of both Gmsh and the SDK with pip: ' `pip install -i https://gmsh.info/python-packages-dev         --force-reinstall --no-cache-dir gmsh` ' (on Linux systems without X windows, use `python-packages-dev-nox` instead of `python-packages-dev`)
- All versions: [binaries](bin/) and [sources](src/)

If you use Gmsh please cite the following reference in your work (books, articles, reports, etc.): [C. Geuzaine and J.-F. Remacle. *Gmsh: a three-dimensional finite element mesh generator with built-in pre- and post-processing facilities*. International Journal for Numerical Methods in Engineering 79(11), pp. 1309-1331, 2009](doc/preprints/gmsh_paper_preprint.pdf). You can also cite additional references for [specific features and algorithms](#References).

<sup>*</sup> Binary releases require Windows ≥ 10, Linux with glibc ≥ 2.28, macOS ≥ 10.15 (x86 - Intel processors) or ≥ 12 (ARM - Apple M-series processors)

## Documentation

- [General presentation](doc/course/general_overview.pdf) with high-level overview of Gmsh and recent developments
- **[Gmsh reference manual (stable release)](doc/texinfo/gmsh.html) (also available in [PDF](doc/texinfo/gmsh.pdf) and in [plain text](doc/texinfo/gmsh.txt))**
- [Gmsh reference manual (development version)](dev/doc/texinfo/gmsh.html) (also available in [PDF](dev/doc/texinfo/gmsh.pdf) and in [plain text](dev/doc/texinfo/gmsh.txt))
- [Screencasts](screencasts/) showing how to use the graphical user interface
- [Gitlab development site](https://gitlab.onelab.info/gmsh/gmsh) with a [wiki](https://gitlab.onelab.info/gmsh/gmsh/wikis/home), [time line](https://gitlab.onelab.info/gmsh/gmsh/commits/master) of changes and the [bug tracking](https://gitlab.onelab.info/gmsh/gmsh/issues) database
- [Changelog](https://gitlab.onelab.info/gmsh/gmsh/blob/master/CHANGELOG.txt)

Please report all issues on [`https://gitlab.onelab.info/gmsh/gmsh/issues`](https://gitlab.onelab.info/gmsh/gmsh/issues).

## Licensing

Gmsh is copyright (C) 1997-2026 by [C. Geuzaine](http://people.montefiore.ulg.ac.be/geuzaine) and [J.-F. Remacle](http://perso.uclouvain.be/jean-francois.remacle/) (see the [CREDITS](CREDITS.txt) file for more information) and is distributed under the terms of the [GNU General Public License (GPL)](LICENSE.txt) (version 2 or later, with an exception to allow for easier linking with external libraries).

In short, this means that everyone is free to use Gmsh and to redistribute it on a free basis. Gmsh is not in the public domain; it is copyrighted and there are restrictions on its distribution (see the license and the related [frequently asked questions](https://www.gnu.org/copyleft/gpl-faq.html)). For example, you cannot integrate this version of Gmsh (in full or in parts) in any *closed-source* software you plan to distribute (commercially or not). If you want to integrate parts of Gmsh into a closed-source software, or want to sell a modified closed-source version of Gmsh, you will need to obtain a commercial license: please [contact us](http://www.montefiore.ulg.ac.be/~geuzaine) for details.

## Screenshots

These are two screenshots of the Gmsh user interface, with either the light or dark user interface theme. See the [ONELAB](http://onelab.info/) web site for more.

[![screenshot](gallery/thumbnail.png)](gallery/screenshot.png)## Links

- Gmsh uses [OpenCASCADE](http://www.opencascade.org/) for constructive geometry features, and interfaces the optional external mesh and mesh adaptation librairies [Netgen](http://ngsolve.org/) and [Mmg3d](https://www.mmgtools.org/).
- Gmsh's cross-platform graphical user interface is based on [FLTK](http://www.fltk.org/) and [OpenGL](http://www.opengl.org/).
- Gmsh's high quality vector PostScript, PDF and SVG output is produced by [GL2PS](http://geuz.org/gl2ps/).
- Gmsh implements a [ONELAB](http://onelab.info/) server to drive external solvers such as the open source finite element solver [GetDP](https://getdp.info/). Gmsh and GetDP are bundled in the ONELAB app for [iPhone, iPad](https://itunes.apple.com/us/app/onelab/id845930897) and [Android](https://play.google.com/store/apps/details?id=org.geuz.onelab) devices.

## References

Gmsh
- C. Geuzaine and J.-F. Remacle. *[Gmsh: a three-dimensional finite element mesh generator with built-in pre- and post-processing facilities](doc/preprints/gmsh_paper_preprint.pdf)*. International Journal for Numerical Methods in Engineering 79(11), pp. 1309-1331, 2009.
Cross-patch and STL meshing (Compounds)
- J.-F. Remacle, C. Geuzaine, G. Compère and E. Marchandise. *[High-quality surface remeshing using harmonic maps](doc/preprints/gmsh_stl_preprint.pdf)*. International Journal for Numerical Methods in Engineering 83(4), pp. 403-425, 2010.
- E. Marchandise, C. Carton de Wiart, W. G. Vos, C. Geuzaine and J.-F. Remacle. *[High quality surface remeshing using harmonic maps. Part II: surfaces with high genus and of large aspect ratio](doc/preprints/gmsh_stl2_preprint.pdf)*. International Journal for Numerical Methods in Engineering 86(11), pp. 1303-1321, 2011.
- E. Marchandise, J.-F. Remacle and C. Geuzaine. *[Optimal parametrizations for surface remeshing](doc/preprints/gmsh_stl3_preprint.pdf)*. Engineering with Computers, December 2012, pp. 1-20.
Quad meshing
- J.-F. Remacle, J. Lambrechts, B. Seny, E. Marchandise, A. Johnen and C. Geuzaine. *[Blossom-Quad: a non-uniform quadrilateral mesh generator using a minimum cost perfect matching algorithm](doc/preprints/gmsh_quad_preprint.pdf)*. International Journal for Numerical Methods in Engineering 89, pp. 1102-1119, 2012.
- J.-F. Remacle, F. Henrotte, T. Carrier-Baudouin, E. Béchet, E. Marchandise, C. Geuzaine and T. Mouton. *[A frontal Delaunay quad mesh generator using the L∞ norm](doc/preprints/gmsh_quad2_preprint.pdf)*. International Journal for Numerical Methods in Engineering, 94(5), pp. 494-512, 2013.
High-order meshing
- A. Johnen, J.-F. Remacle and C. Geuzaine. *[Geometric validity of curvilinear finite elements](doc/preprints/gmsh_curved_preprint.pdf)*. Journal of Computational Physics 233, pp. 359-372, 2013.
- A. Johnen, J.-F. Remacle and C. Geuzaine. *[Geometric validity of high-Order triangular finite elements](doc/preprints/gmsh_curved2_preprint.pdf)*. Engineering with Computers 30 (3), pp. 375-382, 2014.
- T. Toulorge, C. Geuzaine, J.-F. Remacle, J. Lambrechts. *[Robust untangling of curvilinear meshes](doc/preprints/gmsh_untangling_preprint.pdf)*. Journal of Computational Physics 254, pp. 8-26, 2013.
High-order visualization
- J.-F. Remacle, N. Chevaugeon, E. Marchandise and C. Geuzaine. *[Efficient visualization of high-order finite elements](doc/preprints/gmsh_visu_preprint.pdf)*. International Journal for Numerical Methods in Engineering 69(4), pp. 750-771, 2007.
Homology solver
- M. Pellikka, S. Suuriniemi, L. Kettunen and C. Geuzaine. *[Homology and cohomology computation in finite element modeling](doc/preprints/gmsh_homology_preprint.pdf)*. SIAM Journal on Scientific Computing 35(5), pp. 1195-1214, 2013.