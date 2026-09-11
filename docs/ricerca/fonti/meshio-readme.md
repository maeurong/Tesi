[![meshio](https://camo.githubusercontent.com/237883bb155bc380a164742047189cc6e70afe9125b1cf5be0cb614aa4ce73aa/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f6c6f676f2d776974682d746578742e737667)](https://github.com/nschloe/meshio)

I/O for mesh files.

[![PyPi Version](https://camo.githubusercontent.com/27b96268b1632976f4fe0ec536d6518433fec17edf97fde736061610ee8d9e3d/68747470733a2f2f696d672e736869656c64732e696f2f707970692f762f6d657368696f2e7376673f7374796c653d666c61742d737175617265)](https://pypi.org/project/meshio/) [![Anaconda Cloud](https://camo.githubusercontent.com/0bd5f70b36cb907c4882b00eff5d0cd0688147706256707204071b80cb04ef2e/68747470733a2f2f616e61636f6e64612e6f72672f636f6e64612d666f7267652f6d657368696f2f6261646765732f76657273696f6e2e7376673f3d7374796c653d666c61742d737175617265)](https://anaconda.org/conda-forge/meshio/) [![Packaging status](https://camo.githubusercontent.com/a21ca890b54dd172a6e81b8c897e26f26262ff11b327bb25fea04af9bf1cfa67/68747470733a2f2f7265706f6c6f67792e6f72672f62616467652f74696e792d7265706f732f707974686f6e3a6d657368696f2e737667)](https://repology.org/project/python:meshio/versions) [![PyPI pyversions](https://camo.githubusercontent.com/00f47fb41eb00e7d500e50ca43e0e41b6cd960467ba2e7edce6307bf03a5587a/68747470733a2f2f696d672e736869656c64732e696f2f707970692f707976657273696f6e732f6d657368696f2e7376673f7374796c653d666c61742d737175617265)](https://pypi.org/project/meshio/) [![DOI](https://camo.githubusercontent.com/67c584d4597d134d89196a1655a36cc1d546447bb4318435c6ab46e63ddd06cd/68747470733a2f2f7a656e6f646f2e6f72672f62616467652f444f492f31302e353238312f7a656e6f646f2e313137333131352e7376673f7374796c653d666c61742d737175617265)](https://doi.org/10.5281/zenodo.1173115) [![GitHub stars](https://camo.githubusercontent.com/908dd65ff1819dd2790a90e1d0e9c17ca23e747ca636a79f4ddd0a74fcec1021/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f73746172732f6e7363686c6f652f6d657368696f2e7376673f7374796c653d666c61742d737175617265266c6f676f3d676974687562266c6162656c3d5374617273266c6f676f436f6c6f723d7768697465)](https://github.com/nschloe/meshio) [![Downloads](https://camo.githubusercontent.com/1b7130b56f56058609c0935a89f0bd580c3b4e0167586601dbf731b2a8ff79b1/68747470733a2f2f706570792e746563682f62616467652f6d657368696f2f6d6f6e74683f7374796c653d666c61742d737175617265)](https://pepy.tech/project/meshio)

[![Discord](https://camo.githubusercontent.com/01e8b019e4a4d8bc338002ae8baa6e8882bdf9178eef26de889c48ef641096e2/68747470733a2f2f696d672e736869656c64732e696f2f7374617469632f76313f6c6f676f3d646973636f7264266c6f676f436f6c6f723d7768697465266c6162656c3d63686174266d6573736167653d6f6e253230646973636f726426636f6c6f723d373238396461267374796c653d666c61742d737175617265)](https://discord.gg/Z6DMsJh4Hr)

[![gh-actions](https://camo.githubusercontent.com/9125d0a44a563f49120baa16b266eec3e8c3bce534935a2ca762c143e16f3d38/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f776f726b666c6f772f7374617475732f6e7363686c6f652f6d657368696f2f63693f7374796c653d666c61742d737175617265)](https://github.com/nschloe/meshio/actions?query=workflow%3Aci) [![codecov](https://camo.githubusercontent.com/0ea2db62de41f8488b548d704116c4d740036e6b1e771ef2022a49940127af14/68747470733a2f2f696d672e736869656c64732e696f2f636f6465636f762f632f6769746875622f6e7363686c6f652f6d657368696f2e7376673f7374796c653d666c61742d737175617265)](https://app.codecov.io/gh/nschloe/meshio) [![LGTM](https://camo.githubusercontent.com/3a94391777189a10206a93dc743f625e2f7fc9b0e9fff801e724a811472ee0e6/68747470733a2f2f696d672e736869656c64732e696f2f6c67746d2f67726164652f707974686f6e2f6769746875622f6e7363686c6f652f6d657368696f2e7376673f7374796c653d666c61742d737175617265)](https://lgtm.com/projects/g/nschloe/meshio) [![Code style: black](https://camo.githubusercontent.com/2609a820d198bc8e91b3d7d9f0de0546c9a97a4b331611b9e39010cfc006752d/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f636f64652532307374796c652d626c61636b2d3030303030302e7376673f7374796c653d666c61742d737175617265)](https://github.com/psf/black)

There are various mesh formats available for representing unstructured meshes. meshio can read and write all of the following and smoothly converts between them:

> [Abaqus](http://abaqus.software.polimi.it/v6.14/index.html) (`.inp`), ANSYS msh (`.msh`), [AVS-UCD](https://lanl.github.io/LaGriT/pages/docs/read_avs.html) (`.avs`), [CGNS](https://cgns.github.io/) (`.cgns`), [DOLFIN XML](https://manpages.ubuntu.com/manpages/jammy/en/man1/dolfin-convert.1.html) (`.xml`), [Exodus](https://nschloe.github.io/meshio/exodus.pdf) (`.e`, `.exo`), [FLAC3D](https://www.itascacg.com/software/flac3d) (`.f3grid`), [H5M](https://www.mcs.anl.gov/~fathom/moab-docs/h5mmain.html) (`.h5m`), [Kratos/MDPA](https://github.com/KratosMultiphysics/Kratos/wiki/Input-data) (`.mdpa`), [Medit](https://people.sc.fsu.edu/~jburkardt/data/medit/medit.html) (`.mesh`, `.meshb`), [MED/Salome](https://docs.salome-platform.org/latest/dev/MEDCoupling/developer/med-file.html) (`.med`), [Nastran](https://help.autodesk.com/view/NSTRN/2019/ENU/?guid=GUID-42B54ACB-FBE3-47CA-B8FE-475E7AD91A00) (bulk data, `.bdf`, `.fem`, `.nas`), [Netgen](https://github.com/ngsolve/netgen) (`.vol`, `.vol.gz`), [Neuroglancer precomputed format](https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#mesh-representation-of-segmented-object-surfaces), [Gmsh](https://gmsh.info/doc/texinfo/gmsh.html#File-formats) (format versions 2.2, 4.0, and 4.1, `.msh`), [OBJ](https://en.wikipedia.org/wiki/Wavefront_.obj_file) (`.obj`), [OFF](https://segeval.cs.princeton.edu/public/off_format.html) (`.off`), [PERMAS](https://www.intes.de/) (`.post`, `.post.gz`, `.dato`, `.dato.gz`), [PLY](https://en.wikipedia.org/wiki/PLY_\(file_format\)) (`.ply`), [STL](https://en.wikipedia.org/wiki/STL_\(file_format\)) (`.stl`), [Tecplot.dat](http://paulbourke.net/dataformats/tp/), [TetGen.node/.ele](https://wias-berlin.de/software/tetgen/fformats.html), [SVG](https://www.w3.org/TR/SVG/) (2D output only) (`.svg`), [SU2](https://su2code.github.io/docs_v7/Mesh-File/) (`.su2`), [UGRID](https://www.simcenter.msstate.edu/software/documentation/ug_io/3d_grid_file_type_ugrid.html) (`.ugrid`), [VTK](https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf) (`.vtk`), [VTU](https://vtk.org/Wiki/VTK_XML_Formats) (`.vtu`), [WKT](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry) ([TIN](https://en.wikipedia.org/wiki/Triangulated_irregular_network)) (`.wkt`), [XDMF](https://xdmf.org/index.php/XDMF_Model_and_Format) (`.xdmf`, `.xmf`).

([Here's a little survey](https://forms.gle/PSeNb3N3gv3wbEus8) on which formats are actually used.)

Install with one of

```
pip install meshio[all]
conda install -c conda-forge meshio
```

(`[all]` pulls in all optional dependencies. By default, meshio only uses numpy.) You can then use the command-line tool

```
meshio convert    input.msh output.vtk   # convert between two formats

meshio info       input.xdmf             # show some info about the mesh

meshio compress   input.vtu              # compress the mesh file
meshio decompress input.vtu              # decompress the mesh file

meshio binary     input.msh              # convert to binary format
meshio ascii      input.msh              # convert to ASCII format
```

with any of the supported formats.

In Python, simply do

```
import meshio

mesh = meshio.read(
    filename,  # string, os.PathLike, or a buffer/open file
    # file_format="stl",  # optional if filename is a path; inferred from extension
    # see meshio-convert -h for all possible formats
)
# mesh.points, mesh.cells, mesh.cells_dict, ...

# mesh.vtk.read() is also possible
```

to read a mesh. To write, do

```
import meshio

# two triangles and one quad
points = [
    [0.0, 0.0],
    [1.0, 0.0],
    [0.0, 1.0],
    [1.0, 1.0],
    [2.0, 0.0],
    [2.0, 1.0],
]
cells = [
    ("triangle", [[0, 1, 2], [1, 3, 2]]),
    ("quad", [[1, 4, 5, 3]]),
]

mesh = meshio.Mesh(
    points,
    cells,
    # Optionally provide extra data on points, cells, etc.
    point_data={"T": [0.3, -1.2, 0.5, 0.7, 0.0, -3.0]},
    # Each item in cell data must match the cells array
    cell_data={"a": [[0.1, 0.2], [0.4]]},
)
mesh.write(
    "foo.vtk",  # str, os.PathLike, or buffer/open file
    # file_format="vtk",  # optional if first argument is a path; inferred from extension
)

# Alternative with the same options
meshio.write_points_cells("foo.vtk", points, cells)
```

For both input and output, you can optionally specify the exact `file_format` (in case you would like to enforce ASCII over binary VTK, for example).

#### Time series

The [XDMF format](https://xdmf.org/index.php/XDMF_Model_and_Format) supports time series with a shared mesh. You can write times series data using meshio with

```
with meshio.xdmf.TimeSeriesWriter(filename) as writer:
    writer.write_points_cells(points, cells)
    for t in [0.0, 0.1, 0.21]:
        writer.write_data(t, point_data={"phi": data})
```

and read it with

```
with meshio.xdmf.TimeSeriesReader(filename) as reader:
    points, cells = reader.read_points_cells()
    for k in range(reader.num_steps):
        t, point_data, cell_data = reader.read_data(k)
```

### ParaView plugin

[![gmsh paraview](https://camo.githubusercontent.com/81cf83bc85ca60f4c0334cff8ee7da985140ca656b27b9a53917f5908928ad66/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f676d73682d70617261766965772e706e67)](https://camo.githubusercontent.com/81cf83bc85ca60f4c0334cff8ee7da985140ca656b27b9a53917f5908928ad66/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f676d73682d70617261766965772e706e67)

\*A Gmsh file opened with ParaView.\*

If you have downloaded a binary version of ParaView, you may proceed as follows.

- Install meshio for the Python major version that ParaView uses (check `pvpython --version`)
- Open ParaView
- Find the file `paraview-meshio-plugin.py` of your meshio installation (on Linux: `~/.local/share/paraview-5.9/plugins/`) and load it under *Tools / Manage Plugins / Load New*
- *Optional:* Activate *Auto Load*

You can now open all meshio-supported files in ParaView.

### Performance comparison

The comparisons here are for a triangular mesh with about 900k points and 1.8M triangles. The red lines mark the size of the mesh in memory.

#### File sizes

[![file size](https://camo.githubusercontent.com/366fce0f49bda75b1721cd69bf07992c8ce49ca6fb38f9712d056a89d8decd23/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f66696c6573697a65732e737667)](https://camo.githubusercontent.com/366fce0f49bda75b1721cd69bf07992c8ce49ca6fb38f9712d056a89d8decd23/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f66696c6573697a65732e737667)

#### I/O speed

[![performance](https://camo.githubusercontent.com/5a824638c2e9c6e7d441e5e7c517d7a0dc12b4d202fbb590cd21107ab4fe7222/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f706572666f726d616e63652e737667)](https://camo.githubusercontent.com/5a824638c2e9c6e7d441e5e7c517d7a0dc12b4d202fbb590cd21107ab4fe7222/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f706572666f726d616e63652e737667)

#### Maximum memory usage

[![memory usage](https://camo.githubusercontent.com/3058b877479386a502640ffa7b172b1fd179b13634ce25d2442e0f16cdfc1a0a/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f6d656d6f72792e737667)](https://camo.githubusercontent.com/3058b877479386a502640ffa7b172b1fd179b13634ce25d2442e0f16cdfc1a0a/68747470733a2f2f6e7363686c6f652e6769746875622e696f2f6d657368696f2f6d656d6f72792e737667)

### Installation

meshio is [available from the Python Package Index](https://pypi.org/project/meshio/), so simply run

```
pip install meshio
```

to install.

Additional dependencies (`netcdf4`, `h5py`) are required for some of the output formats and can be pulled in by

```
pip install meshio[all]
```

You can also install meshio from [Anaconda](https://anaconda.org/conda-forge/meshio):

```
conda install -c conda-forge meshio
```

### Testing

To run the meshio unit tests, check out this repository and type

```
tox
```

### License

meshio is published under the [MIT license](https://en.wikipedia.org/wiki/MIT_License).