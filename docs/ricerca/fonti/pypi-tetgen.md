[![https://img.shields.io/pypi/v/tetgen.svg?logo=python&logoColor=white](https://pypi-camo.freetls.fastly.net/57a37b27e1c1cf886df81eff2656676fac7e6359/68747470733a2f2f696d672e736869656c64732e696f2f707970692f762f74657467656e2e7376673f6c6f676f3d707974686f6e266c6f676f436f6c6f723d7768697465)](https://pypi.org/project/tetgen/)

This Python library is an interface to Hang Si’s [TetGen](https://github.com/ufz/tetgen) C++ software. This module combines speed of C++ with the portability and ease of installation of Python along with integration to [PyVista](https://docs.pyvista.org/) for 3D visualization and analysis. See the [TetGen](https://github.com/ufz/tetgen) GitHub page for more details on the underlying software.

This Python library uses the C++ source from TetGen (version 1.6.0, released on August 31, 2020) hosted at [libigl/tetgen](https://github.com/libigl/tetgen). Some modifications have been made correct minor bugs.

Brief description from [Weierstrass Institute Software](http://wias-berlin.de/software/index.jsp?id=TetGen&lang=1):

> TetGen is a program to generate tetrahedral meshes of any 3D polyhedral domains. TetGen generates exact constrained Delaunay tetrahedralization, boundary conforming Delaunay meshes, and Voronoi partitions.
> 
> TetGen provides various features to generate good quality and adaptive tetrahedral meshes suitable for numerical methods, such as finite element or finite volume methods. For more information of TetGen, please take a look at a list of [features](http://wias-berlin.de/software/tetgen/features.html).

## Installation

From [PyPI](https://pypi.python.org/pypi/tetgen)

```bash
pip install tetgen
```

From source at [GitHub](https://github.com/pyvista/tetgen)

```bash
git clone https://github.com/pyvista/tetgen
cd tetgen
pip install .
```

## Basic Example

The features of the C++ TetGen software implemented in this module are primarily focused on the tetrahedralization a manifold triangular surface. This basic example demonstrates how to tetrahedralize a manifold surface and plot part of the mesh.

```python
import pyvista as pv
import tetgen
import numpy as np
pv.set_plot_theme('document')

sphere = pv.Sphere()
tet = tetgen.TetGen(sphere)
tet.tetrahedralize(order=1, mindihedral=20, minratio=1.5)
grid = tet.grid
grid.plot(show_edges=True)
```
![https://github.com/pyvista/tetgen/raw/main/doc/images/sphere.png](https://pypi-camo.freetls.fastly.net/1affde1057d62413d36907d3d5d629cf59a7ec06/68747470733a2f2f6769746875622e636f6d2f707976697374612f74657467656e2f7261772f6d61696e2f646f632f696d616765732f7370686572652e706e67)

Tetrahedralized Sphere

Extract a portion of the sphere’s tetrahedral mesh below the xy plane and plot the mesh quality.

```python
# get cell centroids
cells = grid.cells.reshape(-1, 5)[:, 1:]
cell_center = grid.points[cells].mean(1)

# extract cells below the 0 xy plane
mask = cell_center[:, 2] < 0
cell_ind = mask.nonzero()[0]
subgrid = grid.extract_cells(cell_ind)

# advanced plotting
plotter = pv.Plotter()
plotter.add_mesh(subgrid, 'lightgrey', lighting=True, show_edges=True)
plotter.add_mesh(sphere, 'r', 'wireframe')
plotter.add_legend([[' Input Mesh ', 'r'],
                    [' Tessellated Mesh ', 'black']])
plotter.show()
```
![https://github.com/pyvista/tetgen/raw/main/doc/images/sphere_subgrid.png](https://pypi-camo.freetls.fastly.net/1c1198efc20b6761acf9b8d028cce9e2873db8e2/68747470733a2f2f6769746875622e636f6d2f707976697374612f74657467656e2f7261772f6d61696e2f646f632f696d616765732f7370686572655f737562677269642e706e67)

Here is the cell quality as computed according to the minimum scaled jacobian.

```
Compute cell quality

>>> cell_qual = subgrid.cell_quality()['scaled_jacobian']

Plot quality

>>> subgrid.plot(scalars=cell_qual, stitle='Quality', cmap='bwr', clim=[0, 1],
...              flip_scalars=True, show_edges=True)
```
![https://github.com/pyvista/tetgen/raw/main/doc/images/sphere_qual.png](https://pypi-camo.freetls.fastly.net/e68d3ad778df65ccc02183b22554ff1dcfccf423/68747470733a2f2f6769746875622e636f6d2f707976697374612f74657467656e2f7261772f6d61696e2f646f632f696d616765732f7370686572655f7175616c2e706e67)

## Using a Background Mesh

A background mesh in TetGen is used to define a mesh sizing function for adaptive mesh refinement. This function informs TetGen of the desired element size throughout the domain, allowing for detailed refinement in specific areas without unnecessary densification of the entire mesh. Here’s how to utilize a background mesh in your TetGen workflow:

1. **Generate the Background Mesh**: Create a tetrahedral mesh that spans the entirety of your input piecewise linear complex (PLC) domain. This mesh will serve as the basis for your sizing function.
2. **Define the Sizing Function**: At the nodes of your background mesh, define the desired mesh sizes. This can be based on geometric features, proximity to areas of interest, or any criterion relevant to your simulation needs.
3. **Optional: Export the Background Mesh and Sizing Function**: Save your background mesh in the TetGen-readable .node and .ele formats, and the sizing function values in a .mtr file. These files will be used by TetGen to guide the mesh generation process.
4. **Run TetGen with the Background Mesh**: Invoke TetGen, specifying the background mesh. TetGen will adjust the mesh according to the provided sizing function, refining the mesh where smaller elements are desired.

**Full Example**

To illustrate, consider a scenario where you want to refine a mesh around a specific region with increased detail. The following steps and code snippets demonstrate how to accomplish this with TetGen and PyVista:

1. **Prepare Your PLC and Background Mesh**:
	```python
	import pyvista as pv
	import tetgen
	import numpy as np
	# Load or create your PLC
	sphere = pv.Sphere(theta_resolution=10, phi_resolution=10)
	# Generate a background mesh with desired resolution
	def generate_background_mesh(bounds, resolution=20, eps=1e-6):
	    x_min, x_max, y_min, y_max, z_min, z_max = bounds
	    grid_x, grid_y, grid_z = np.meshgrid(
	        np.linspace(xmin - eps, xmax + eps, resolution),
	        np.linspace(ymin - eps, ymax + eps, resolution),
	        np.linspace(zmin - eps, zmax + eps, resolution),
	        indexing="ij",
	    )
	    return pv.StructuredGrid(grid_x, grid_y, grid_z).triangulate()
	bg_mesh = generate_background_mesh(sphere.bounds)
	```
2. **Define the Sizing Function and Write to Disk**:
	```python
	# Define sizing function based on proximity to a point of interest
	def sizing_function(
	    points, focus_point=np.array([0, 0, 0]), max_size=1.0, min_size=0.1
	):
	    distances = np.linalg.norm(points - focus_point, axis=1)
	    return np.clip(max_size - distances, min_size, max_size)
	bg_mesh.point_data["target_size"] = sizing_function(bg_mesh.points)
	# Optionally write out the background mesh
	def write_background_mesh(background_mesh, out_stem):
	    """Write a background mesh to a file.
	    This writes the mesh in tetgen format (X.b.node, X.b.ele) and a X.b.mtr file
	    containing the target size for each node in the background mesh.
	    """
	    mtr_content = [f"{background_mesh.n_points} 1"]
	    target_size = background_mesh.point_data["target_size"]
	    for i in range(background_mesh.n_points):
	        mtr_content.append(f"{target_size[i]:.8f}")
	    pv.save_meshio(f"{out_stem}.node", background_mesh)
	    mtr_file = f"{out_stem}.mtr"
	    with open(mtr_file, "w") as f:
	        f.write("\n".join(mtr_content))
	write_background_mesh(bg_mesh, "bgmesh.b")
	```
3. **Use TetGen with the Background Mesh**:
	Directly pass the background mesh from PyVista to tetgen:
	```python
	tet_kwargs = dict(order=1, mindihedral=20, minratio=1.5)
	tet = tetgen.TetGen(mesh)
	tet.tetrahedralize(bgmesh=bgmesh, **tet_kwargs)
	refined_mesh = tet.grid
	```
	Alternatively, use the background mesh files.
	```python
	tet = tetgen.TetGen(sphere)
	tet.tetrahedralize(bgmeshfilename="bgmesh.b", **tet_kwargs)
	refined_mesh = tet.grid
	```

This example demonstrates generating a background mesh, defining a spatially varying sizing function, and using this background mesh to guide TetGen in refining a PLC. By following these steps, you can achieve adaptive mesh refinement tailored to your specific simulation requirements.

## Acknowledgments

Software was originally created by Hang Si based on work published in [TetGen, a Delaunay-Based Quality Tetrahedral Mesh Generator](https://dl.acm.org/citation.cfm?doid=2629697).

## Project links

Data verified by PyPI on May 4, 2026

Data provided by the project maintainers, verified at the time the release was uploaded to PyPI.

- [Documentation](https://tetgen.pyvista.org/)

## Key dates

PyPI data

## 1 maintainer

PyPI data

 [![Avatar for pyvista from gravatar.com](https://pypi-camo.freetls.fastly.net/627296d012853606f0d74a6a64f2013f4106e898/68747470733a2f2f7365637572652e67726176617461722e636f6d2f6176617461722f35313830393537646132363663653139326530326236356165323365653735333f73697a653d3335 "Avatar for pyvista from gravatar.com") pyvista](https://pypi.org/user/pyvista/)

## GitHub Statistics

Data verified by PyPI on May 4, 2026

The GitHub source repository was provided by the project maintainers and verified by PyPI at the time of upload. Stars, forks, and open issues/PRs are derived from that repository and have not been independently verified.

Download the file for your platform. If you're not sure which to choose, learn more about [installing packages](https://packaging.python.org/tutorials/installing-packages/ "External link").

### Source Distribution

[tetgen-0.8.4.tar.gz](https://files.pythonhosted.org/packages/af/b6/bd320925cc4127c6f838c9127fdb0b2292147286500489d5ba6aac5d34e1/tetgen-0.8.4.tar.gz) (827.1 kB [view details](#tetgen-0.8.4.tar.gz))

### Built Distributions

If you're not sure about the file name format, learn more about [wheel file names](https://packaging.python.org/en/latest/specifications/binary-distribution-format/ "External link").

[tetgen-0.8.4-cp312-abi3-win\_amd64.whl](https://files.pythonhosted.org/packages/bf/2e/348cdeb63c0a04cee46fae2d92019123cd6d6ba0f4c3895b7ca0cd33d091/tetgen-0.8.4-cp312-abi3-win_amd64.whl) (307.2 kB [view details](#tetgen-0.8.4-cp312-abi3-win_amd64.whl))

Uploaded May 4, 2026 `CPython 3.12+` `Windows x86-64`

[tetgen-0.8.4-cp312-abi3-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/f2/6b/b2568feb06fa57f8010f18bf27fd456546e921edf8d71c1147614e54234f/tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl) (411.1 kB [view details](#tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.12+` `manylinux: glibc 2.27+ x86-64` `manylinux: glibc 2.28+ x86-64`

[tetgen-0.8.4-cp312-abi3-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/89/d3/7cb2c03fa45c51d4b32caa34423acebfb4f78e3ebdd6fca0a12b3a42931f/tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl) (407.5 kB [view details](#tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl))

Uploaded May 4, 2026 `CPython 3.12+` `manylinux: glibc 2.26+ ARM64` `manylinux: glibc 2.28+ ARM64`

[tetgen-0.8.4-cp312-abi3-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/aa/60/fa9f368d759ef425f90f3b5d6b2e934fcc30e2b2bcdd63e5bcc7fbca802d/tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl) (362.5 kB [view details](#tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl))

Uploaded May 4, 2026 `CPython 3.12+` `macOS 11.0+ ARM64`

[tetgen-0.8.4-cp312-abi3-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/29/4a/4c38923509ae6ef5e194623bde5ffa6b16b8e9fa2d674136558b10a7dfeb/tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl) (399.1 kB [view details](#tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.12+` `macOS 10.14+ x86-64`

[tetgen-0.8.4-cp311-cp311-win\_amd64.whl](https://files.pythonhosted.org/packages/71/c0/fdf1694eca85ea9cee6f015049dc6e21fce8e5b6f9a53a81352fb1c92c45/tetgen-0.8.4-cp311-cp311-win_amd64.whl) (309.1 kB [view details](#tetgen-0.8.4-cp311-cp311-win_amd64.whl))

Uploaded May 4, 2026 `CPython 3.11` `Windows x86-64`

[tetgen-0.8.4-cp311-cp311-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/8f/af/14d737a3c571d15c4adfd42b4f845a39886158ad15d99aff3e1f3f365d54/tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl) (415.9 kB [view details](#tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.11` `manylinux: glibc 2.27+ x86-64` `manylinux: glibc 2.28+ x86-64`

[tetgen-0.8.4-cp311-cp311-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/29/00/1186139e2c53aaed4776610c81129e72c6095b20f059b5a955c60f28e175/tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl) (411.0 kB [view details](#tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl))

Uploaded May 4, 2026 `CPython 3.11` `manylinux: glibc 2.26+ ARM64` `manylinux: glibc 2.28+ ARM64`

[tetgen-0.8.4-cp311-cp311-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/79/ed/da003fedf6161ed3a20be0514c27d5e8e91311a7121d2c43e017ff565c4b/tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl) (364.8 kB [view details](#tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl))

Uploaded May 4, 2026 `CPython 3.11` `macOS 11.0+ ARM64`

[tetgen-0.8.4-cp311-cp311-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/47/e9/1c47a16684133ab5597c9e62b5987031972fec03834d05bd95b33fc2135d/tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl) (400.8 kB [view details](#tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.11` `macOS 10.14+ x86-64`

[tetgen-0.8.4-cp310-cp310-win\_amd64.whl](https://files.pythonhosted.org/packages/b9/2f/bd90b674c2bd40020dcd595927edd14d66587370eea551c5557d4bcbcf23/tetgen-0.8.4-cp310-cp310-win_amd64.whl) (309.2 kB [view details](#tetgen-0.8.4-cp310-cp310-win_amd64.whl))

Uploaded May 4, 2026 `CPython 3.10` `Windows x86-64`

[tetgen-0.8.4-cp310-cp310-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/8f/4a/69c4bbc79f499fa12585ccd8e2f35cff428e3a58423e5d04a5c47ca2ea56/tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl) (416.1 kB [view details](#tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.10` `manylinux: glibc 2.27+ x86-64` `manylinux: glibc 2.28+ x86-64`

[tetgen-0.8.4-cp310-cp310-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/de/73/49a100715f96a7536c6f00fd22454e36ac6f43aaf2680b55c3dd0cc275cf/tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl) (411.3 kB [view details](#tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl))

Uploaded May 4, 2026 `CPython 3.10` `manylinux: glibc 2.26+ ARM64` `manylinux: glibc 2.28+ ARM64`

[tetgen-0.8.4-cp310-cp310-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/d3/2c/62ebb483fda3c6db1af385fec0e4fcb3e318d64b847a9142832ba767dc84/tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl) (364.9 kB [view details](#tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl))

Uploaded May 4, 2026 `CPython 3.10` `macOS 11.0+ ARM64`

[tetgen-0.8.4-cp310-cp310-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/55/53/ac9a72f257926362e1005d81ba158ae5c2c893639db765d85d0719fd7801/tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl) (401.0 kB [view details](#tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl))

Uploaded May 4, 2026 `CPython 3.10` `macOS 10.14+ x86-64`

Details for the file `tetgen-0.8.4.tar.gz`.

### File metadata

- Download URL: [tetgen-0.8.4.tar.gz](https://files.pythonhosted.org/packages/af/b6/bd320925cc4127c6f838c9127fdb0b2292147286500489d5ba6aac5d34e1/tetgen-0.8.4.tar.gz)
- Upload date: May 4, 2026
- Size: 827.1 kB
- Tags: Source
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `b6ca979ccecf43ddc0d31fa4f5a05da3cfeb4ab0705b8128530745bbab38bb86` | Copy |
| MD5 | `54bb190e6e68f0d2f670416d5681bb99` | Copy |
| BLAKE2b-256 | `afb6bd320925cc4127c6f838c9127fdb0b2292147286500489d5ba6aac5d34e1` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4.tar.gz`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4.tar.gz`
		- Subject digest: `b6ca979ccecf43ddc0d31fa4f5a05da3cfeb4ab0705b8128530745bbab38bb86`
		- Sigstore transparency entry: [1437806947](https://search.sigstore.dev/?logIndex=1437806947)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp312-abi3-win_amd64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp312-abi3-win\_amd64.whl](https://files.pythonhosted.org/packages/bf/2e/348cdeb63c0a04cee46fae2d92019123cd6d6ba0f4c3895b7ca0cd33d091/tetgen-0.8.4-cp312-abi3-win_amd64.whl)
- Upload date: May 4, 2026
- Size: 307.2 kB
- Tags: CPython 3.12+, Windows x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `de38fc1e9e684546862f0795f3e91c19450c6d11961542a6035bab249c65b51f` | Copy |
| MD5 | `6deeb7a795cdbca88dba94d7a5b53753` | Copy |
| BLAKE2b-256 | `bf2e348cdeb63c0a04cee46fae2d92019123cd6d6ba0f4c3895b7ca0cd33d091` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp312-abi3-win_amd64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp312-abi3-win_amd64.whl`
		- Subject digest: `de38fc1e9e684546862f0795f3e91c19450c6d11961542a6035bab249c65b51f`
		- Sigstore transparency entry: [1437807093](https://search.sigstore.dev/?logIndex=1437807093)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp312-abi3-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/f2/6b/b2568feb06fa57f8010f18bf27fd456546e921edf8d71c1147614e54234f/tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl)
- Upload date: May 4, 2026
- Size: 411.1 kB
- Tags: CPython 3.12+, manylinux: glibc 2.27+ x86-64, manylinux: glibc 2.28+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `e24f383fdd5d12660fd85cea937506ca2d81cca20fb92945a61f658e3719bc76` | Copy |
| MD5 | `861fc4dfc417241db559e2e74602c26d` | Copy |
| BLAKE2b-256 | `f26bb2568feb06fa57f8010f18bf27fd456546e921edf8d71c1147614e54234f` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
		- Subject digest: `e24f383fdd5d12660fd85cea937506ca2d81cca20fb92945a61f658e3719bc76`
		- Sigstore transparency entry: [1437807390](https://search.sigstore.dev/?logIndex=1437807390)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp312-abi3-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/89/d3/7cb2c03fa45c51d4b32caa34423acebfb4f78e3ebdd6fca0a12b3a42931f/tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl)
- Upload date: May 4, 2026
- Size: 407.5 kB
- Tags: CPython 3.12+, manylinux: glibc 2.26+ ARM64, manylinux: glibc 2.28+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `58125b8c81b56869d26ba69d5404bacb0ae320ce9b8b45116aee0753dc89edc8` | Copy |
| MD5 | `dc02449029a25bfd418c29c526e319a7` | Copy |
| BLAKE2b-256 | `89d37cb2c03fa45c51d4b32caa34423acebfb4f78e3ebdd6fca0a12b3a42931f` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp312-abi3-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`
		- Subject digest: `58125b8c81b56869d26ba69d5404bacb0ae320ce9b8b45116aee0753dc89edc8`
		- Sigstore transparency entry: [1437807332](https://search.sigstore.dev/?logIndex=1437807332)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp312-abi3-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/aa/60/fa9f368d759ef425f90f3b5d6b2e934fcc30e2b2bcdd63e5bcc7fbca802d/tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl)
- Upload date: May 4, 2026
- Size: 362.5 kB
- Tags: CPython 3.12+, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `eb74efee0950fdc4cdd65e3eac2b8ae8f37d9a08a8d5e366e52ed052b86e44a4` | Copy |
| MD5 | `a84bdba209d00779a727c544f9c6d18b` | Copy |
| BLAKE2b-256 | `aa60fa9f368d759ef425f90f3b5d6b2e934fcc30e2b2bcdd63e5bcc7fbca802d` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp312-abi3-macosx_11_0_arm64.whl`
		- Subject digest: `eb74efee0950fdc4cdd65e3eac2b8ae8f37d9a08a8d5e366e52ed052b86e44a4`
		- Sigstore transparency entry: [1437807435](https://search.sigstore.dev/?logIndex=1437807435)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp312-abi3-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/29/4a/4c38923509ae6ef5e194623bde5ffa6b16b8e9fa2d674136558b10a7dfeb/tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl)
- Upload date: May 4, 2026
- Size: 399.1 kB
- Tags: CPython 3.12+, macOS 10.14+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `2ceff7d99c4c4777ba605b7726a021d51c7e76fce35b524551a160379fa45981` | Copy |
| MD5 | `95b74f39f9bce60732e057df8b3e9a0a` | Copy |
| BLAKE2b-256 | `294a4c38923509ae6ef5e194623bde5ffa6b16b8e9fa2d674136558b10a7dfeb` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp312-abi3-macosx_10_14_x86_64.whl`
		- Subject digest: `2ceff7d99c4c4777ba605b7726a021d51c7e76fce35b524551a160379fa45981`
		- Sigstore transparency entry: [1437807292](https://search.sigstore.dev/?logIndex=1437807292)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp311-cp311-win_amd64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp311-cp311-win\_amd64.whl](https://files.pythonhosted.org/packages/71/c0/fdf1694eca85ea9cee6f015049dc6e21fce8e5b6f9a53a81352fb1c92c45/tetgen-0.8.4-cp311-cp311-win_amd64.whl)
- Upload date: May 4, 2026
- Size: 309.1 kB
- Tags: CPython 3.11, Windows x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `22993175186927ad4be8c73b678b2c4fa3654a5bff5ec31c0410c78494a58644` | Copy |
| MD5 | `157bbd575aa1f1e52aedeb4a89ac13fe` | Copy |
| BLAKE2b-256 | `71c0fdf1694eca85ea9cee6f015049dc6e21fce8e5b6f9a53a81352fb1c92c45` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp311-cp311-win_amd64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp311-cp311-win_amd64.whl`
		- Subject digest: `22993175186927ad4be8c73b678b2c4fa3654a5bff5ec31c0410c78494a58644`
		- Sigstore transparency entry: [1437807195](https://search.sigstore.dev/?logIndex=1437807195)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp311-cp311-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/8f/af/14d737a3c571d15c4adfd42b4f845a39886158ad15d99aff3e1f3f365d54/tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl)
- Upload date: May 4, 2026
- Size: 415.9 kB
- Tags: CPython 3.11, manylinux: glibc 2.27+ x86-64, manylinux: glibc 2.28+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `b3a6e7bad3ef934c8780531fb1b063901472bfde3fca3d4426fc85e9e79ee1bf` | Copy |
| MD5 | `e602555977b9c61a0c38c813106380f8` | Copy |
| BLAKE2b-256 | `8faf14d737a3c571d15c4adfd42b4f845a39886158ad15d99aff3e1f3f365d54` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
		- Subject digest: `b3a6e7bad3ef934c8780531fb1b063901472bfde3fca3d4426fc85e9e79ee1bf`
		- Sigstore transparency entry: [1437807014](https://search.sigstore.dev/?logIndex=1437807014)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp311-cp311-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/29/00/1186139e2c53aaed4776610c81129e72c6095b20f059b5a955c60f28e175/tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl)
- Upload date: May 4, 2026
- Size: 411.0 kB
- Tags: CPython 3.11, manylinux: glibc 2.26+ ARM64, manylinux: glibc 2.28+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `adc6cf4af5e90250e9619a4a160468e408edb4307e55c4688c9a0a8ed1394cba` | Copy |
| MD5 | `187beddc3581c0cbeec3c2ac10cfb699` | Copy |
| BLAKE2b-256 | `29001186139e2c53aaed4776610c81129e72c6095b20f059b5a955c60f28e175` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp311-cp311-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`
		- Subject digest: `adc6cf4af5e90250e9619a4a160468e408edb4307e55c4688c9a0a8ed1394cba`
		- Sigstore transparency entry: [1437807483](https://search.sigstore.dev/?logIndex=1437807483)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp311-cp311-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/79/ed/da003fedf6161ed3a20be0514c27d5e8e91311a7121d2c43e017ff565c4b/tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl)
- Upload date: May 4, 2026
- Size: 364.8 kB
- Tags: CPython 3.11, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `1bc405ee5dbfd944a9cee3e62da072e724851562fa0d279933caa91afae0eb8c` | Copy |
| MD5 | `efedd025a2a822efd99ffea0dcfdefc4` | Copy |
| BLAKE2b-256 | `79edda003fedf6161ed3a20be0514c27d5e8e91311a7121d2c43e017ff565c4b` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp311-cp311-macosx_11_0_arm64.whl`
		- Subject digest: `1bc405ee5dbfd944a9cee3e62da072e724851562fa0d279933caa91afae0eb8c`
		- Sigstore transparency entry: [1437807546](https://search.sigstore.dev/?logIndex=1437807546)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp311-cp311-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/47/e9/1c47a16684133ab5597c9e62b5987031972fec03834d05bd95b33fc2135d/tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl)
- Upload date: May 4, 2026
- Size: 400.8 kB
- Tags: CPython 3.11, macOS 10.14+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `2d20488f92709cb4db4e5e83bb2440067c762b14419727a15fb91ec1d8870084` | Copy |
| MD5 | `9e0c65902a13351f36a7c37641b3c839` | Copy |
| BLAKE2b-256 | `47e91c47a16684133ab5597c9e62b5987031972fec03834d05bd95b33fc2135d` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp311-cp311-macosx_10_14_x86_64.whl`
		- Subject digest: `2d20488f92709cb4db4e5e83bb2440067c762b14419727a15fb91ec1d8870084`
		- Sigstore transparency entry: [1437807598](https://search.sigstore.dev/?logIndex=1437807598)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp310-cp310-win_amd64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp310-cp310-win\_amd64.whl](https://files.pythonhosted.org/packages/b9/2f/bd90b674c2bd40020dcd595927edd14d66587370eea551c5557d4bcbcf23/tetgen-0.8.4-cp310-cp310-win_amd64.whl)
- Upload date: May 4, 2026
- Size: 309.2 kB
- Tags: CPython 3.10, Windows x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `ef9a8a950baa9caddb6a4de34ff402426f652e43fead71dfa5b4fdee862bbef4` | Copy |
| MD5 | `3909c6b124c5bfa874901d489078b683` | Copy |
| BLAKE2b-256 | `b92fbd90b674c2bd40020dcd595927edd14d66587370eea551c5557d4bcbcf23` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp310-cp310-win_amd64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp310-cp310-win_amd64.whl`
		- Subject digest: `ef9a8a950baa9caddb6a4de34ff402426f652e43fead71dfa5b4fdee862bbef4`
		- Sigstore transparency entry: [1437807363](https://search.sigstore.dev/?logIndex=1437807363)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp310-cp310-manylinux\_2\_27\_x86\_64.manylinux\_2\_28\_x86\_64.whl](https://files.pythonhosted.org/packages/8f/4a/69c4bbc79f499fa12585ccd8e2f35cff428e3a58423e5d04a5c47ca2ea56/tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl)
- Upload date: May 4, 2026
- Size: 416.1 kB
- Tags: CPython 3.10, manylinux: glibc 2.27+ x86-64, manylinux: glibc 2.28+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `bc605762e5d3b8dea44c81de508118a5c4420fb911c5aebe69000c1e9deb738f` | Copy |
| MD5 | `5c3eb67e579353578c954329f6a91958` | Copy |
| BLAKE2b-256 | `8f4a69c4bbc79f499fa12585ccd8e2f35cff428e3a58423e5d04a5c47ca2ea56` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp310-cp310-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
		- Subject digest: `bc605762e5d3b8dea44c81de508118a5c4420fb911c5aebe69000c1e9deb738f`
		- Sigstore transparency entry: [1437806974](https://search.sigstore.dev/?logIndex=1437806974)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp310-cp310-manylinux\_2\_26\_aarch64.manylinux\_2\_28\_aarch64.whl](https://files.pythonhosted.org/packages/de/73/49a100715f96a7536c6f00fd22454e36ac6f43aaf2680b55c3dd0cc275cf/tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl)
- Upload date: May 4, 2026
- Size: 411.3 kB
- Tags: CPython 3.10, manylinux: glibc 2.26+ ARM64, manylinux: glibc 2.28+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `95b2df04a868ce9ac800b051f4641471af576997ee8519614f0b55eb134eae9a` | Copy |
| MD5 | `ca1331366395a6bb5925adc7ed7bd0b4` | Copy |
| BLAKE2b-256 | `de7349a100715f96a7536c6f00fd22454e36ac6f43aaf2680b55c3dd0cc275cf` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp310-cp310-manylinux_2_26_aarch64.manylinux_2_28_aarch64.whl`
		- Subject digest: `95b2df04a868ce9ac800b051f4641471af576997ee8519614f0b55eb134eae9a`
		- Sigstore transparency entry: [1437807047](https://search.sigstore.dev/?logIndex=1437807047)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp310-cp310-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/d3/2c/62ebb483fda3c6db1af385fec0e4fcb3e318d64b847a9142832ba767dc84/tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl)
- Upload date: May 4, 2026
- Size: 364.9 kB
- Tags: CPython 3.10, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `e0d98fb56a6e782e9490dfda3f99f2902d4f3733c1eb4bdd9876d13bf22574f1` | Copy |
| MD5 | `0234d52c9faff00e5fb25951e9f69b1b` | Copy |
| BLAKE2b-256 | `d32c62ebb483fda3c6db1af385fec0e4fcb3e318d64b847a9142832ba767dc84` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp310-cp310-macosx_11_0_arm64.whl`
		- Subject digest: `e0d98fb56a6e782e9490dfda3f99f2902d4f3733c1eb4bdd9876d13bf22574f1`
		- Sigstore transparency entry: [1437807520](https://search.sigstore.dev/?logIndex=1437807520)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`

Details for the file `tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl`.

### File metadata

- Download URL: [tetgen-0.8.4-cp310-cp310-macosx\_10\_14\_x86\_64.whl](https://files.pythonhosted.org/packages/55/53/ac9a72f257926362e1005d81ba158ae5c2c893639db765d85d0719fd7801/tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl)
- Upload date: May 4, 2026
- Size: 401.0 kB
- Tags: CPython 3.10, macOS 10.14+ x86-64
- Uploaded using Trusted Publishing? Yes
- Uploaded via: `twine/6.1.0 CPython/3.13.12`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `19d17b859cebfae974d613fd7a3afbf6817538047b5a9541349fc2c0bf245d66` | Copy |
| MD5 | `bde251dd6b102b7b21bbe5b9d9dd99fd` | Copy |
| BLAKE2b-256 | `5553ac9a72f257926362e1005d81ba158ae5c2c893639db765d85d0719fd7801` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

### Provenance

The following attestation bundles were made for `tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl`:

Publisher: [`build-and-deploy.yml` on pyvista/tetgen](https://github.com/pyvista/tetgen/blob/HEAD/.github/workflows/build-and-deploy.yml)

Attestations: *Values shown here reflect the state when the release was signed and may no longer be current.*
- Statement:
	- Statement type: [`https://in-toto.io/Statement/v1`](https://in-toto.io/Statement/v1)
		- Predicate type: [`https://docs.pypi.org/attestations/publish/v1`](https://docs.pypi.org/attestations/publish/v1)
		- Subject name: `tetgen-0.8.4-cp310-cp310-macosx_10_14_x86_64.whl`
		- Subject digest: `19d17b859cebfae974d613fd7a3afbf6817538047b5a9541349fc2c0bf245d66`
		- Sigstore transparency entry: [1437807144](https://search.sigstore.dev/?logIndex=1437807144)
		- Sigstore integration time: May 4, 2026
	Source repository:
	- Permalink: [`pyvista/tetgen@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/tree/c039698cf4cce5c671b281c003dbc6cd8e58acc3)
		- Branch / Tag: [`refs/tags/v0.8.4`](https://github.com/pyvista/tetgen/tree/refs/tags/v0.8.4)
		- Owner: [https://github.com/pyvista](https://github.com/pyvista)
		- Access: `public`
	Publication detail:
	- Token Issuer: `https://token.actions.githubusercontent.com`
		- Runner Environment: `github-hosted`
		- Publication workflow: [`build-and-deploy.yml@c039698cf4cce5c671b281c003dbc6cd8e58acc3`](https://github.com/pyvista/tetgen/blob/c039698cf4cce5c671b281c003dbc6cd8e58acc3/.github/workflows/build-and-deploy.yml)
		- Trigger Event: `push`