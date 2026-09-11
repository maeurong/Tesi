# Cloud2FEM: A finite element mesh generator based on point clouds of existing/historical structures — SoftwareX 18 (2022) 101099 (PDF open access UniBo CRIS, testo estratto con pdftotext)

                                                                     SoftwareX 18 (2022) 101099



                                                           Contents lists available at ScienceDirect


                                                                            SoftwareX
                                                     journal homepage: www.elsevier.com/locate/softx


Original software publication

Cloud2FEM: A finite element mesh generator based on point clouds of
existing/historical structures
                                 ∗
Giovanni Castellazzi , Nicolò Lo Presti, Antonio Maria D’Altri, Stefano de Miranda
Department of Civil, Chemical, Environmental and Materials Engineering (DICAM), University of Bologna, Viale del Risorgimento
2, Bologna 40136, Italy



article              info                           a b s t r a c t

Article history:                                    Nowadays, the common output of surveying activities on existing/historical structures consists of dense
Received 14 February 2022                           point clouds. However, the direct and automatic exploitation of point clouds for structural purposes,
Received in revised form 20 April 2022              i.e. to generate finite element models, is still very limited. In this framework, the Cloud2FEM software
Accepted 3 May 2022
                                                    supplies an automatic finite element mesh generator based on point clouds of existing/historical
Keywords:                                           structures. Cloud2FEM is based on open-source Python libraries with graphical interface. The point
Point cloud                                         cloud is initially sliced along with the vertical direction. Then, closed polygons are recognized on each
FE modelling                                        slice and stacked vertically thanks to the use of voxels. The voxelized volume is exported into 3D
Mesh generation                                     solid hexahedron-based finite element meshes. Suitable graphical tools are developed to help the user
Cultural heritage structures                        adjusting local potential criticalities in the slices, also when partial information is missing in the points
Voxel                                               cloud. An illustrative example is given to highlight the Cloud2FEM potentialities.
Masonry                                                   © 2022 The Author(s). Published by Elsevier B.V. This is an open access article under the CC BY-NC-ND
                                                                                                   license (http://creativecommons.org/licenses/by-nc-nd/4.0/).



Code metadata

 Current code version                                                                v1.0
 Permanent link to code/repository used for this code version                        https://github.com/ElsevierSoftwareX/SOFTX-D-22-00047
 Permanent link to reproducible capsule                                              None
 Legal code license                                                                  GNU General Public License (GPL) version 3
 Code versioning system used                                                         None
 Software code languages, tools and services used                                    Python
 Compilation requirements, operating environments and dependencies                   PyQt5, PyQtGraph, VisPy, NumPy, pyntcloud, Shapely, ezdxf.
 If available, link to developer documentation/manual                                None
 Support email for questions                                                         giovanni.castellazzi@unibo.it




1. Motivation and significance                                                        structures [3], minarets [4], and pulpits [5], have been lately
                                                                                      developed. Typically, the standard process consists in the manual
    The structural analysis of existing/historical structures is a                    creation of a CAD solid model and its discretization with solid FEs,
challenging task. One main reason consists in the geometrical                         even if this usually leads to errors in the FE meshing procedures
complexity which typically characterize these structures, that                        due to geometric imprecisions and tolerances.
lead to non-trivial tasks for the geometrical modelling in the                            In this framework, Castellazzi et al. [6,7] proposed a workflow
framework of the Finite Element Method (FEM). A promising                             to directly and semi-automatically exploit dense point clouds
support could come from modern automatic survey techniques                            to generate FE meshes. In particular, the point cloud is initially
(e.g. laser scanning and close-range photogrammetry) which pro-                       sliced along with the vertical direction. Hence, closed polygons
duce dense point clouds [1] of the building under study. However,                     are recognized on each slice and stacked vertically thanks to the
the direct exploitation of point clouds for structural purposes,                      use of voxel concept. The voxelized volume is then exported into
i.e. to generate Finite Element (FE) models, is still very limited.                   robust and conforming 3D solid hexahedron-based FE meshes.
Indeed, only few attempts concerning historic facades [2], timber                     This workflow guarantees a remarkable user-time saving with
                                                                                      respect to 3D CAD standard modelling procedures, as well as a
  ∗ Corresponding author.                                                             considerable robustness of the generated mesh. These aspects
    E-mail address: giovanni.castellazzi@unibo.it (Giovanni Castellazzi).             have been underlined in [8], where nonlinear static analysis have

https://doi.org/10.1016/j.softx.2022.101099
2352-7110/© 2022 The Author(s). Published by Elsevier B.V. This is an open access article under the CC BY-NC-ND license (http://creativecommons.org/licenses/by-
nc-nd/4.0/).
Giovanni Castellazzi, N. Lo Presti, A.M. D’Altri et al.                                                                               SoftwareX 18 (2022) 101099




Fig. 1. Cloud2FEM main graphical user interface: (I) file menu, (II) 3D Viewer panel, (III) cloud/mesh processing panel, (IV) plot area, (V) 2D Viewer panel, (VI)
editing bar.


been successfully conducted on the generated mesh of a historical                   CAD environments (i.e. .dxf slices) or FE simulations (i.e. FE solid
fortress. In particular, this workflow demonstrated to be efficient                 mesh). On the left (II), the 3D Viewer section contains buttons to
also in presence of horizontal decks and masonry vaults in the                      open a separated window where the selected quantities can be
structure, as discussed in [7].                                                     explored in 3D.
    In this paper, an easy-to-use open-source software (named                           The right panel (III) contains, starting from the top, the ex-
Cloud2FEM) which efficiently accomplishes the point cloud-to-                       treme z coordinates of the loaded point cloud, a section to specify
numerical model procedure proposed in [6,7] is released. The                        the slicing modality, buttons to perform all the steps needed
workflow proposed in [6,7], initially composed of different scripts                 to generate a FE model. Red and green indicators beside each
written in different code languages, has been herein straightfor-                   button denote if a certain step still needs to be performed or not,
wardly implemented using the Python language. In particular,                        respectively. Most of the data generated through the steps in the
the Cloud2FEM software has been developed with a user-friendly                      right panel can be visualized in the central plot area (IV), which
graphical interface. Accordingly, this allows an agile and robust                   occupies most of the space of the interface. The 2D Viewer section
seamless user experience and easy improvements of the code.                         on the left (V) can be utilized to choose the data to be shown, for
Therefore, non-skilled users are able to approach the software                      any slice. The edit button on the top bar (VI) allows to enter the
and transform a point cloud (input) into a solid FE model (output),                 edit mode for the current slice and for the selected data type. An
allowing a widespread adoption of this approach. Additionally,                      example of slice processing is shown in Fig. 2.
the graphical interface favoured the implementation of CAD-like                         On each slice, local modifications can be performed with the
tools which can be used by the user to adjust local potential                       help of various suitable ad-hoc tools (for both points and poly-
criticalities in the slices, also when partial information is missing               lines, e.g. draw, join, remove, add, move, offset, etc.), that can
in the point clouds.                                                                be activated via keyboard shortcuts. The top bar (VI) contains
                                                                                    also buttons to save or discard the changes made in the edit
2. Software description                                                             mode, as well as a copy button that opens a separated window
                                                                                    used to copy data from one slice to others. Finally, the button
    The main graphical user interface of the software Cloud2FEM                     ‘‘Generate mesh’’ positioned at the bottom of the right panel (III)
is shown in Fig. 1. On the top (I), the file menu contains buttons to               generates the matrix of nodal coordinates and the connectivity
load point clouds (the input data of this software), save a project,                matrix of the FEs, i.e. the FE mesh, which can be exported from
load a previously saved project, and export data to be used into                    the file menu (I). In this particular case, the mesh is exported into
                                                                                2
Giovanni Castellazzi, N. Lo Presti, A.M. D’Altri et al.                                                                                SoftwareX 18 (2022) 101099




Fig. 2. Example of slice processing through Cloud2FEM: (a) slice of the raw point cloud, (b) derived centroids and polylines before simplification, (c) final clean
geometry ready to be used in the mesh generation step.


                                                                                       – Loading a point cloud in .pcd or .ply formats and visu-
                                                                                         alizing it with the 3D viewer. Since the 3D visualization
                                                                                         of a large point cloud can be computationally demanding,
                                                                                         the software uses a graphical accelerated tool to support
                                                                                         real large dataset visualization. Nevertheless, the user can
                                                                                         choose between three possible predefined resolutions (10,
                                                                                         50 and 100%) to get a smoother interaction.
                                                                                       – Visualizing the extreme [Zmin , Zmax ] coordinates of the loaded
                                                                                         point cloud.
                                                                                       – Slicing of the point cloud. The user can choose between
                                                                                         two slicing rules, i.e. fixed number of slices or fixed step
                                                                                         height. The function activated by the ‘‘Generate slices’’ but-
                                                                                         ton extracts slices from the loaded point cloud, according to
                                                                                         the specified slicing parameters. Every slice, named by its Z
                                                                                         coordinate, can be selected from the drop-down list on the
        Fig. 3. Cloud2FEM software architecture and libraries involved.                  left panel and visualized in the 2D viewer. The whole set of
                                                                                         slices can be visualized in the 3D viewer by checking the
                                                                                         corresponding checkbox on the left panel.
the .inp format [9], which can be visualized also by open-source                       – Simplifying and ordering the slices. Every slice, consisting
software packages, see e.g. FreeCAD [10]. Anyway, the matrix of                          of an unordered array of points, is processed through the
nodal coordinates and the connectivity matrix of the FEs can be                          algorithm called by the ‘‘Generate Centroids’’ button to get
found unencrypted in the .inp file (text format), and so they can                        a new smaller array of ordered points that can be used
be used in any available FE software.                                                    to efficiently describe the geometry of the slice. The cen-
                                                                                         troids can be visualized in the 2D viewer by checking the
2.1. Software architecture                                                               corresponding checkbox in the left panel.
                                                                                       – Generating polylines. The centroids data generated by the
    Cloud2FEM is a Python-based software [11]. Its graphics (see                         software in a previous step is utilized to get a set of raw
e.g. Fig. 1) is realized with the help of the PyQt5 library [12],                        polylines. These are automatically simplified to get a cleaner
supplemented by the PyQtGraph library [13] for 2D plotting and                           and lightweight geometric representation. Both the raw and
editing, and by the VisPy [14] library for 3D visualization. On                          the clean polylines can be visualized in the 2D viewer by
the back-end, various open source libraries are employed. At the                         checking the corresponding checkbox in the left panel.
base, NumPy [15] is widely utilized for array computing. The                           – Generating polygons. A more descriptive data type is auto-
input point cloud data in the .pcd or .ply format is converted                           matically derived from the polylines obtained in a previous
into a Python data type by means of the pyntcloud library [16].                          step. Each slice is described by means of polygons, made of
The Shapely package [17] is adopted to manipulate 2D geometric                           inner and outer bounds. This geometric representation can
entities with ease, and ezdxf [18] is exploited to export 2D slices                      be exported in the .dxf file format.
in the .dxf format. The code consists of a main file, two .ui files                    – Generating the mesh. A FE mesh is automatically generated
where the graphic entities are stored, and four thematic modules                         from the polygons data. The X and Y dimensions of the
with the functions utilized for 3D visualization, conversion of a                        voxels are set according to the grid visible in the 2D viewer,
point cloud in a set of sorted geometric entities, conversion of                         while the Z dimension depends on the adopted slicing pa-
geometric entities in a FE mesh, manual editing of points and                            rameters. The output can be exported in a text file format
polylines. The code structure and the libraries involved are shown                       organized according to the Abaqus notation (.inp) [9].
in Fig. 3.                                                                             – Saving and opening a project. The data handled by the
                                                                                         software can be stored and retrieved to allow discontin-
2.2. Software functionalities                                                            uous work sessions. Furthermore, since the data is stored
                                                                                         using the built-in Python shelve module, advanced users can
    The main functionalities of Cloud2FEM are here listed:                               easily exploit the data in other Python-based software.
                                                                                3
Giovanni Castellazzi, N. Lo Presti, A.M. D’Altri et al.                                                                          SoftwareX 18 (2022) 101099




Fig. 4. Example of generation of a FE mesh based on a point cloud of a benchmark structure by means of the Cloud2FEM software: (a) point cloud used as input
visualized at 100% resolution, (b) slicing of the point cloud, (c) slice example with local modification, (d) FE mesh (output).


    – Editing of points and centroids. To eliminate criticalities in             points). The representation of the initial geometry of the bench-
      the slices, points and centroids can be removed individually               mark through slices composed of closed polygons is shown in
      or in bulk with graphic tools in the 2D viewer.                            Fig. 4(b). An example of slice is shown in Fig. 4(c), where a local
    – Editing of polylines. A set of tools in the 2D viewer allows for           modification through ad-hoc tools is also highlighted. Finally,
      an advanced graphic editing of the polylines. Vertices can be              Fig. 4(d) shows the FE mesh (composed of 38,882 nodes and
      added, removed or moved, polylines can be joined, removed                  31,638 8-node hexahedral FEs) generated through the Cloud2FEM
      or drawn from scratch if geometric data is missing from the                software, i.e. the main output of the software, ready to be used
      original point cloud.                                                      for structural analysis purposes. It should be noted that the visu-
    – Copy of the polylines of a slice. The polylines of a slice can             alization in Fig. 4(d) has been obtained through the open-source
      be copied to other to speed up the editing process.                        software FreeCAD [10].
                                                                                     The parameters adopted in the example in Fig. 4 are:

                                                                                    – Slicing with a fixed step height of 0.2 m, from 0.025 m to
3. Illustrative example
                                                                                      11.97 m.
                                                                                    – Slice thickness St equal to 0.005 m.
   An illustrative example of the automated generation of a con-
                                                                                    – Minimum wall thickness Mwt equal to 0.3 m.
forming FE mesh based on a point cloud of a pseudo-actual
                                                                                    – X and Y grid dimensions set equal to 0.2 m.
benchmark structure by means of the Cloud2FEM software is
shown in Fig. 4. The structure has a height equal to 12 m, a                     It should be highlighted that these parameters are here listed
square base with a length of 6 m and its walls are roughly 1 m                   to guarantee the reproducibility of the model in Fig. 4. For the
thick. Fig. 4(a) shows the point cloud used as input (5,977,514                  sake of example, the influence of the voxel size on the structural
                                                                             4
Giovanni Castellazzi, N. Lo Presti, A.M. D’Altri et al.                                                                             SoftwareX 18 (2022) 101099


performance of voxel-based numerical models has been assessed                    Ad-hoc graphical tools have been developed to help the user
in [19]. Accordingly, the choice of the voxel dimensions can be               adjusting local potential criticalities in the slices, also when
conducted in agreement with the suggestions given in [6,7,19].                partial information is missing in the point cloud. Accordingly,
   Moreover, St refers to the tolerance in the Z direction, i.e. a            Cloud2FEM allows the generation of solid FE models of exist-
point P belongs to the slice Zi if its Z coordinate ZP is included            ing/historical buildings starting from point clouds of any level of
between the limits Zi − S2t ≤ ZP ≤ Zi + S2t . At first, the value of St       completeness, i.e. also in the case of non-comprehensive point
can be typically set equal to 5 mm and then, if needed, adjusted              clouds, which is the most common case encountered in practice.
depending on the density of the actual point cloud. Furthermore,
Mwt refers to a tolerance used by the software to correctly identify          Declaration of competing interest
distinct portions in a slice, and it can be set depending on the
                                                                                  The authors declare that they have no known competing finan-
actual minimum wall thickness or, if smaller, on dimension of the
                                                                              cial interests or personal relationships that could have appeared
smaller opening measurable in the structure.
                                                                              to influence the work reported in this paper.
   Finally, it should be highlighted that point clouds made of
up to 150 million points have been easily manipulated with                    Acknowledgements
Cloud2FEM (on a commercial laptop equipped with 16 GB of RAM
and a dedicated GPU).                                                            This project has received funding from the European Union’s
                                                                              Horizon 2020 research and innovation programme under the
4. Impact                                                                     Marie Sklodowska-Curie grant agreement No. 101029792 (HOLA-
                                                                              HERIS project, "A holistic structural analysis method for cultural
    The impact of the Cloud2FEM software on common practices                  heritage structures conservation").
in structural analysis of cultural heritage buildings appears signif-
                                                                              Appendix A. Supplementary data
icant. First of all, Cloud2FEM allows non-skilled users to generate
solid and robust FE models of existing/historical buildings starting
                                                                                 Supplementary material related to this article can be found
from raw dense point clouds of any complexity and any level of                online at https://doi.org/10.1016/j.softx.2022.101099.
completeness. Indeed, the software herein discussed guarantees
its usability also in case of non-comprehensive point clouds,                 References
e.g. point clouds surveyed only on the external building surfaces,
which are the most common case encountered in practice. This                   [1] Riveiro B, DeJong MJ, Conde B. Automated processing of large point clouds
allows the direct and automatic exploitation of point clouds for                   for structural health monitoring of masonry arch bridges. Autom Constr
                                                                                   2016;72:258–68. http://dx.doi.org/10.1016/j.autcon.2016.02.009.
structural purposes, i.e. for the generation of voxel-based FE                 [2] Truong-Hong L, Laefer DF. Validating computational models from laser
models which demonstrated to be particularly appealing for both                    scanning data for historic facades. J Test Eval 2013;41(3):481–96. http:
model updating [20] and seismic assessments,8. Therefore, this                     //dx.doi.org/10.1520/jte20120243.
software represents a generalization of the procedures used in [6–             [3] Armesto J, Lubowiecka I, Ordóñez C, Rial FI. FEM modeling of struc-
                                                                                   tures based on close range digital photogrammetry. Autom Constr
8], characterized by the possibility to deal with a larger range of                2009;18(5):559–69. http://dx.doi.org/10.1016/j.autcon.2008.11.006.
cases and by a smoother user experience.                                       [4] Korumaz M, Betti M, Conti A, Tucci G, Bartoli G, Bonora V, et al. An
    Cloud2FEM usage appears preferable with respect to standard                    integrated terrestrial laser scanner (TLS), deviation analysis (DA) and
                                                                                   finite element (FE) approach for health assessment of historical structures,
3D CAD-based procedures, given its speediness and robustness.
                                                                                   a minaret case study. Eng Struct 2017;153:224–38. http://dx.doi.org/10.
Indeed, it always guarantees the generation of robust conforming                   1016/j.engstruct.2017.10.026.
solid FE meshes, and it allows to save user-time with respect                  [5] Bartoli G, Betti M, Bonora V, Conti A, Fiorini L, Kovacevic VC, et al. From
3D CAD approaches [6]. In particular, it requires no CAD skills                    TLS data to FE model: A workflow for studying the dynamic behavior
                                                                                   of the pulpit by Giovanni Pisano in Pistoia (Italy). Proc Struct Integ
from the user, who needs basically no training to be able to use
                                                                                   2020;29:55–62.
Cloud2FEM.                                                                     [6] Castellazzi G, D’Altri AM, Bitelli G, Selvaggi I, Lambertini A. From laser
    Therefore, Cloud2FEM could become the starting point for ad-                   scanning to finite element analysis of complex buildings by using a semi-
vanced structural assessments of cultural heritage structures [4,                  automatic procedure. Sensors 2015;15(8):18360–80. http://dx.doi.org/10.
                                                                                   3390/s150818360.
8,21–24], used by both research groups and consultancy pro-                    [7] Castellazzi G, D’Altri AM, de Miranda S, Ubertini F. An innovative numerical
fessional teams. For example, it will be thoroughly used in the                    modeling strategy for the structural analysis of historical monumen-
H2020-funded HOLAHERIS project [25]. The simplicity of the                         tal buildings. Eng Struct 2017;132:229–48. http://dx.doi.org/10.1016/j.
Cloud2FEM usage also encourages its adoption in student and                        engstruct.2016.11.032.
                                                                               [8] Degli Abbati S, D’Altri AM, Ottonelli D, Castellazzi G, Cattari S, de Mi-
teaching activities (e.g. theses, homework, etc.).                                 randa S, et al. Seismic assessment of interacting structural units in complex
                                                                                   historic masonry constructions by nonlinear static analyses. Comput Struct
                                                                                   2019;213:51–71.
5. Conclusions                                                                             ®
                                                                               [9] Abaqus . Theory manual, version 6.20. 2020.
                                                                              [10] Riegel J, Mayer W, van Havre Y. FreeCAD. 2016.
    The Cloud2FEM software supplies a FE mesh generator which                 [11] Python language reference, version 3.8.5. Python Software Foundation;
                                                                                   2020, [Online]. Availablewww.python.org [Accessed 23 July 2020].
receives as input the point cloud of an existing/historical struc-            [12] PyQt5 - Python bindings for Qt v5. 2021, [Online]. Available: https://pypi.
ture, and gives as output the solid FE model of the structure.                     org/project/PyQt5/ [Accessed 20 October 2021].
Cloud2FEM is based on open-source Python libraries with graphi-               [13] PyQtGraph. Scientific graphics and GUI library for Python, v0.11.1.
cal interface, which demonstrated to be particularly user-friendly.                2021, [Online]. Available: https://pypi.org/project/pyqtgraph/ [Accessed 21
                                                                                   January 2021].
The data processing follows the initial slicing of the point cloud            [14] VisPy. Interactive visualization in Python, v0.6.6. 2021, [Online]. Available:
along with the vertical direction, the automatic recognition of                    https://pypi.org/project/vispy/ [Accessed 21 January 2021].
closed polygons on each slice, and the slice stacking using the               [15] NumPy. Package for array computing with python, v1.21.2. 2021, [Online].
                                                                                   Available: https://pypi.org/project/numpy/ [Accessed 13 October 2021].
concept of voxel. Finally, the voxelized volume is exported into
                                                                              [16] Pyntcloud. Python library for working with 3D point clouds, v0.1.5.
3D solid hexahedron-based FE meshes ready to be used for struc-                    2021, [Online]. Available: https://pypi.org/project/pyntcloud/ [Accessed 20
tural purposes.                                                                    October 2021].

                                                                          5
Giovanni Castellazzi, N. Lo Presti, A.M. D’Altri et al.                                                                                         SoftwareX 18 (2022) 101099


[17] Shapely. Python package for manipulation and analysis of planar geometric           [21] Kassotakis N, Sarhosis V, Riveiro B, Conde B, D’Altri AM, Mills J, et al. Three-
     objects, v1.7.1. 2021, [Online]. Available: https://pypi.org/project/Shapely/            dimensional discrete element modelling of rubble masonry structures from
     [Accessed 21 January 2021].                                                              dense point clouds. Autom Constr 2020;119:103365.
[18] Ezdxf. A Python package to create/manipulate DXF drawings, v0.15.2. 2021,           [22] Almac U, Pekmezci I, Ahunbay M. Numerical analysis of historic struc-
     [Online]. Available: https://pypi.org/project/ezdxf/ [Accessed 23 February               tural elements using 3D point cloud data. Open Const Build Technol J
     2021].                                                                                   2016;10(1).
[19] Castellazzi G, D’Altri AM, de Miranda S, Ubertini F, Bitelli G, Lambertini A,       [23] Pepi C, Cavalagli N, Gusella V, Gioffrè M. An integrated approach for the
     et al. A mesh generation method for historical monumental buildings:                     numerical modeling of severely damaged historic structures: Application
     An innovative approach. In: Proceedings of the VII european congress on                  to a masonry bridge. Adv Eng Softw 2021;151:102935.
     computational methods in applied sciences and engineering. Crete Island;            [24] Funari MF, Hajjat AE, Masciotta MG, Oliveira DV, Lourenço B. A parametric
     2016, http://dx.doi.org/10.7712/100016.1823.11948.                                       scan-to-FEM framework for the digital twin generation of historic masonry
[20] Bassoli E, Vincenzi L, D’Altri AM, de Miranda S, Forghieri M, Castellazzi G.             structures. Sustainability 2021;13(19):11088.
     Ambient vibration-based finite element model updating of an earthquake-             [25] HOLAHERIS website. 2022, [Online]. Available: https://site.unibo.it/
     damaged masonry tower. Structural Control and Health Monitoring                          holaheris/en [Accessed 17 May 2022].
     2018;25(5):e2150.




                                                                                     6
