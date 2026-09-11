## pymeshlab 2025.7.post1

pip install pymeshlab

## PyMeshLab

[![DOI](https://pypi-camo.freetls.fastly.net/141ad1c48055f2360617edc55dfbeb86ef04eb41/68747470733a2f2f7a656e6f646f2e6f72672f62616467652f444f492f31302e353238312f7a656e6f646f2e343433383735302e737667)](https://doi.org/10.5281/zenodo.4438750)

[![BuildAndTest](https://pypi-camo.freetls.fastly.net/b976715a268438d903ea893e32f91e103ef3ab0f/68747470733a2f2f6769746875622e636f6d2f636e722d697374692d76636c61622f50794d6573684c61622f616374696f6e732f776f726b666c6f77732f4275696c64416e64546573742e796d6c2f62616467652e737667)](https://github.com/cnr-isti-vclab/PyMeshLab/actions/workflows/BuildAndTest.yml)

[![Documentation Status](https://pypi-camo.freetls.fastly.net/0fb12d7056bb6d5763d9041638523322948f4859/68747470733a2f2f72656164746865646f63732e6f72672f70726f6a656374732f70796d6573686c61622f62616467652f3f76657273696f6e3d6c6174657374)](https://pymeshlab.readthedocs.io/en/latest/?badge=latest)

PyMeshLab is a Python library that interfaces to [MeshLab](https://github.com/cnr-isti-vclab/meshlab), the popular open source application for editing and processing large 3D triangle meshes. Python bindings are generated using [pybind11](https://github.com/pybind/pybind11).

## Documentation

You can find the official documentation [here](https://pymeshlab.readthedocs.io/).

## Install PyMeshLab

You can easily install PyMeshLab using pip:

```
pip3 install pymeshlab
```

### Note about Conda

PyMeshLab is now available on [Conda-Forge](https://anaconda.org/conda-forge/pymeshlab).

If you are in a Conda environment, we recommend installing PyMeshLab from Conda-Forge:

```
conda install -c conda-forge pymeshlab
```

See [this discussion](https://github.com/cnr-isti-vclab/PyMeshLab/discussions/434) for more information.

## Run PyMeshLab

After installing PyMeshLab through pip:

```
python
>>> import pymeshlab
>>> ms = pymeshlab.MeshSet()
```

You can load, save meshes and apply MeshLab filters:

```
ms.load_new_mesh('airplane.obj')
ms.generate_convex_hull()
ms.save_current_mesh('convex_hull.ply')
```

And apply filters with your parameters:

```
ms.create_noisy_isosurface(resolution=128)
```

You can find all the names and parameters of the filters in the [List of Filters](https://pymeshlab.readthedocs.io/en/latest/filter_list.html) page of the documentation.

To run the tests:

```
pip3 install pytest
pytest --pyargs pymeshlab
```

## Build PyMeshLab

See the [`src`](https://pypi.org/project/pymeshlab/src/README.md) folder that contains the instructions to build PyMeshLab.

## License

The PyMeshlab source is released under the [GPL License](https://pypi.org/project/pymeshlab/LICENSE).

## Copyright

```
PyMeshLab
All rights reserved.

VCGLib  http://www.vcglib.net                                     o o
Visual and Computer Graphics Library                            o     o
                                                               _   O  _
Paolo Cignoni                                                    \/)\/
Visual Computing Lab  http://vcg.isti.cnr.it                    /\/|
ISTI - Italian National Research Council                           |
Copyright(C) 2020                                                  \
```

## References

[![DOI](https://pypi-camo.freetls.fastly.net/141ad1c48055f2360617edc55dfbeb86ef04eb41/68747470733a2f2f7a656e6f646f2e6f72672f62616467652f444f492f31302e353238312f7a656e6f646f2e343433383735302e737667)](https://doi.org/10.5281/zenodo.4438750)

Please, when using this tool, cite:

```
@software{pymeshlab,
  author       = {Muntoni, Alessandro and Cignoni, Paolo},
  title        = {{PyMeshLab}},
  month        = jan,
  year         = 2021,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.4438750}
}
```

## Contacts

- Paolo Cignoni (paolo.cignoni (at) isti.cnr.it)
- Alessandro Muntoni (alessandro.muntoni (at) isti.cnr.it)

## Feedback

For documented and repeatable bugs, feature requests, etc., please use the [GitHub issues](https://github.com/cnr-isti-vclab/PyMeshLab/issues).

Download the file for your platform. If you're not sure which to choose, learn more about [installing packages](https://packaging.python.org/tutorials/installing-packages/ "External link").

### Source Distributions

No source distribution files available for this release.See tutorial on [generating distribution archives](https://packaging.python.org/tutorials/packaging-projects/#generating-distribution-archives "External link").

### Built Distributions

If you're not sure about the file name format, learn more about [wheel file names](https://packaging.python.org/en/latest/specifications/binary-distribution-format/ "External link").

[pymeshlab-2025.7.post1-cp314-cp314-win\_amd64.whl](https://files.pythonhosted.org/packages/3e/f0/65e3b96a14e9c80e05c085f8b32b923ccd5a70acf63eb66528e3fa94cf54/pymeshlab-2025.7.post1-cp314-cp314-win_amd64.whl) (56.6 MB [view details](#pymeshlab-2025.7.post1-cp314-cp314-win_amd64.whl))

Uploaded Jan 30, 2026 `CPython 3.14` `Windows x86-64`

[pymeshlab-2025.7.post1-cp314-cp314-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/79/c0/9b769a1acd7ce4405059820793c2f14129d9faba99b595ea35c8c9d8c57d/pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_x86_64.whl) (106.6 MB [view details](#pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.14` `manylinux: glibc 2.35+ x86-64`

[pymeshlab-2025.7.post1-cp314-cp314-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/ac/01/b26a8c0d70a76fc333a620ce1ee7b11f8ab4b3791306350e28a578dcb47f/pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_aarch64.whl) (65.4 MB [view details](#pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_aarch64.whl))

Uploaded Jan 30, 2026 `CPython 3.14` `manylinux: glibc 2.35+ ARM64`

[pymeshlab-2025.7.post1-cp314-cp314-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/65/0d/58258e56400f3a5ff9df565b4ff48616568af25aa5d8a70eb2afee467709/pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_x86_64.whl) (54.5 MB [view details](#pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.14` `macOS 11.0+ x86-64`

[pymeshlab-2025.7.post1-cp314-cp314-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/29/e6/68bb19ec11de2f60bc3319e0ce93aba4082ec82a6bbc03dd142f0d319585/pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_arm64.whl) (65.0 MB [view details](#pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_arm64.whl))

Uploaded Jan 30, 2026 `CPython 3.14` `macOS 11.0+ ARM64`

[pymeshlab-2025.7.post1-cp313-cp313-win\_amd64.whl](https://files.pythonhosted.org/packages/a2/69/1732c3222ce63758c32746841099ac82059907cc3ff6bd77499da78abcbc/pymeshlab-2025.7.post1-cp313-cp313-win_amd64.whl) (55.2 MB [view details](#pymeshlab-2025.7.post1-cp313-cp313-win_amd64.whl))

Uploaded Jan 30, 2026 `CPython 3.13` `Windows x86-64`

[pymeshlab-2025.7.post1-cp313-cp313-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/7f/af/3f7597d43813e8918bc2798aeed9b3be123a62e8a5be7de032cce03db8ed/pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_x86_64.whl) (106.4 MB [view details](#pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.13` `manylinux: glibc 2.35+ x86-64`

[pymeshlab-2025.7.post1-cp313-cp313-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/0a/4e/31b08dddba8c77676c9cf7ed90810b7dfcbd99cba845bb9b20b7bbaa4d7c/pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_aarch64.whl) (65.2 MB [view details](#pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_aarch64.whl))

Uploaded Jan 30, 2026 `CPython 3.13` `manylinux: glibc 2.35+ ARM64`

[pymeshlab-2025.7.post1-cp313-cp313-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/27/52/a11aa52eb3b250f78a891b9e4ffcdf4af4da13a462d079cc6cf3d17d34ac/pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_x86_64.whl) (54.5 MB [view details](#pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.13` `macOS 11.0+ x86-64`

[pymeshlab-2025.7.post1-cp313-cp313-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/a7/06/ef68bf08d23f44118ab846b93dd30eaf87ad85cc44b4f3e5ac8764e9bc9f/pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_arm64.whl) (65.0 MB [view details](#pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_arm64.whl))

Uploaded Jan 30, 2026 `CPython 3.13` `macOS 11.0+ ARM64`

[pymeshlab-2025.7.post1-cp312-cp312-win\_amd64.whl](https://files.pythonhosted.org/packages/4f/06/66b91d2d77fbb2bf729dfe58692957bad3cea706ecb3fe51fca4b07c0c95/pymeshlab-2025.7.post1-cp312-cp312-win_amd64.whl) (55.2 MB [view details](#pymeshlab-2025.7.post1-cp312-cp312-win_amd64.whl))

Uploaded Jan 30, 2026 `CPython 3.12` `Windows x86-64`

[pymeshlab-2025.7.post1-cp312-cp312-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/a3/4c/b0b1b5ad425acd80abcff4632f0241ca490c52ef9c48013d71f573680a2a/pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_x86_64.whl) (106.5 MB [view details](#pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.12` `manylinux: glibc 2.35+ x86-64`

[pymeshlab-2025.7.post1-cp312-cp312-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/6b/8d/6082aa85f8c918901221d1a7e1e810cb5b56eecbed59a5e688feea92c148/pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_aarch64.whl) (65.3 MB [view details](#pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_aarch64.whl))

Uploaded Jan 30, 2026 `CPython 3.12` `manylinux: glibc 2.35+ ARM64`

[pymeshlab-2025.7.post1-cp312-cp312-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/f8/0d/6692ef6d96fa27763899665562c11ee6411eba55b2bddcda6799213dadac/pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_x86_64.whl) (54.5 MB [view details](#pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.12` `macOS 11.0+ x86-64`

[pymeshlab-2025.7.post1-cp312-cp312-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/ae/c1/a8db8ba66b5c51e700ba0eccea2c81f68a3223b775b0afe7b30a3da9a2ec/pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_arm64.whl) (65.0 MB [view details](#pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_arm64.whl))

Uploaded Jan 30, 2026 `CPython 3.12` `macOS 11.0+ ARM64`

[pymeshlab-2025.7.post1-cp311-cp311-win\_amd64.whl](https://files.pythonhosted.org/packages/e6/56/c4383522d9603cca76ad0c1c886014bf6ac4e79df96018e13025c669b068/pymeshlab-2025.7.post1-cp311-cp311-win_amd64.whl) (55.2 MB [view details](#pymeshlab-2025.7.post1-cp311-cp311-win_amd64.whl))

Uploaded Jan 30, 2026 `CPython 3.11` `Windows x86-64`

[pymeshlab-2025.7.post1-cp311-cp311-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/c0/20/5b18072334280015899fce0a514a8455619421dfb122d37c1fd7166507db/pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_x86_64.whl) (106.2 MB [view details](#pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.11` `manylinux: glibc 2.35+ x86-64`

[pymeshlab-2025.7.post1-cp311-cp311-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/49/7b/caba5fba3e0cc57230b5600b4a4965e797d39aa59b3ef87e405f4fb9b5bc/pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_aarch64.whl) (65.1 MB [view details](#pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_aarch64.whl))

Uploaded Jan 30, 2026 `CPython 3.11` `manylinux: glibc 2.35+ ARM64`

[pymeshlab-2025.7.post1-cp311-cp311-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/d1/d1/d6a0a4fc5f4858f3ddbdaf72a28709aa05fc46efb052f1b14d5ab54c6a61/pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_x86_64.whl) (54.5 MB [view details](#pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.11` `macOS 11.0+ x86-64`

[pymeshlab-2025.7.post1-cp311-cp311-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/4e/c4/0651d56e6af7680e76460f80ce2812e29b1bc5aefba3988423ea43095074/pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_arm64.whl) (65.0 MB [view details](#pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_arm64.whl))

Uploaded Jan 30, 2026 `CPython 3.11` `macOS 11.0+ ARM64`

[pymeshlab-2025.7.post1-cp310-cp310-win\_amd64.whl](https://files.pythonhosted.org/packages/63/b5/eb7c2a986084175d2eb7351ea34de08fe9ca78bc9a0164fc7555a8f6bae8/pymeshlab-2025.7.post1-cp310-cp310-win_amd64.whl) (55.2 MB [view details](#pymeshlab-2025.7.post1-cp310-cp310-win_amd64.whl))

Uploaded Jan 30, 2026 `CPython 3.10` `Windows x86-64`

[pymeshlab-2025.7.post1-cp310-cp310-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/07/a5/b0df05e63303dea51fc5026d00d5c4788c7ddbd7136175b1296b494c9161/pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_x86_64.whl) (105.9 MB [view details](#pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.10` `manylinux: glibc 2.35+ x86-64`

[pymeshlab-2025.7.post1-cp310-cp310-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/1e/d3/80ad31b6ce43d2e134a72038b932b59758fe5b4ed7c856d309ae4752061a/pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_aarch64.whl) (64.7 MB [view details](#pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_aarch64.whl))

Uploaded Jan 30, 2026 `CPython 3.10` `manylinux: glibc 2.35+ ARM64`

[pymeshlab-2025.7.post1-cp310-cp310-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/1f/b6/34e2e7791298210472af8c70d284b30fe88b5350024ba274d06f1ef363d3/pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_x86_64.whl) (54.5 MB [view details](#pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_x86_64.whl))

Uploaded Jan 30, 2026 `CPython 3.10` `macOS 11.0+ x86-64`

[pymeshlab-2025.7.post1-cp310-cp310-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/73/7e/d44a74e360163ffc37f380c1be421c1594bd67e4ef9a4805691fdb662449/pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_arm64.whl) (65.0 MB [view details](#pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_arm64.whl))

Uploaded Jan 30, 2026 `CPython 3.10` `macOS 11.0+ ARM64`

Details for the file `pymeshlab-2025.7.post1-cp314-cp314-win_amd64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp314-cp314-win\_amd64.whl](https://files.pythonhosted.org/packages/3e/f0/65e3b96a14e9c80e05c085f8b32b923ccd5a70acf63eb66528e3fa94cf54/pymeshlab-2025.7.post1-cp314-cp314-win_amd64.whl)
- Upload date: Jan 30, 2026
- Size: 56.6 MB
- Tags: CPython 3.14, Windows x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `881389fb62ac832c81555fe22a3990a81624deb78e78ca3862836075d5c62c2b` | Copy |
| MD5 | `6ac3f1eac00db1192745234f3b6380d2` | Copy |
| BLAKE2b-256 | `3ef065e3b96a14e9c80e05c085f8b32b923ccd5a70acf63eb66528e3fa94cf54` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp314-cp314-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/79/c0/9b769a1acd7ce4405059820793c2f14129d9faba99b595ea35c8c9d8c57d/pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 106.6 MB
- Tags: CPython 3.14, manylinux: glibc 2.35+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `951fe5aeb3e92632f3db3a1a6525279b41e5d7191c6b9011429dbb0b67f2f0d3` | Copy |
| MD5 | `cff52f103532eab7ea28a640d5544aed` | Copy |
| BLAKE2b-256 | `79c09b769a1acd7ce4405059820793c2f14129d9faba99b595ea35c8c9d8c57d` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_aarch64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp314-cp314-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/ac/01/b26a8c0d70a76fc333a620ce1ee7b11f8ab4b3791306350e28a578dcb47f/pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_aarch64.whl)
- Upload date: Jan 30, 2026
- Size: 65.4 MB
- Tags: CPython 3.14, manylinux: glibc 2.35+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `de6468bf43d5eeb23cdac78fe30286694ff5ad6d349a9bfa44584ac7e434e054` | Copy |
| MD5 | `678e40a5732dc0c39393e1b608731b45` | Copy |
| BLAKE2b-256 | `ac01b26a8c0d70a76fc333a620ce1ee7b11f8ab4b3791306350e28a578dcb47f` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp314-cp314-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/65/0d/58258e56400f3a5ff9df565b4ff48616568af25aa5d8a70eb2afee467709/pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 54.5 MB
- Tags: CPython 3.14, macOS 11.0+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `472b7247e4ae9b9937d9a13bfb78b9e6e777b805ae20a114101f9dcc15bea8fc` | Copy |
| MD5 | `92c98be813af486d1d306cb37805645c` | Copy |
| BLAKE2b-256 | `650d58258e56400f3a5ff9df565b4ff48616568af25aa5d8a70eb2afee467709` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp314-cp314-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/29/e6/68bb19ec11de2f60bc3319e0ce93aba4082ec82a6bbc03dd142f0d319585/pymeshlab-2025.7.post1-cp314-cp314-macosx_11_0_arm64.whl)
- Upload date: Jan 30, 2026
- Size: 65.0 MB
- Tags: CPython 3.14, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `c9990cd5e4620fc598795baf91f1b7b37ebb65a7b87eb01beb54d37339207d46` | Copy |
| MD5 | `ce438522893b5f005e2c48ff345612bd` | Copy |
| BLAKE2b-256 | `29e668bb19ec11de2f60bc3319e0ce93aba4082ec82a6bbc03dd142f0d319585` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp313-cp313-win_amd64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp313-cp313-win\_amd64.whl](https://files.pythonhosted.org/packages/a2/69/1732c3222ce63758c32746841099ac82059907cc3ff6bd77499da78abcbc/pymeshlab-2025.7.post1-cp313-cp313-win_amd64.whl)
- Upload date: Jan 30, 2026
- Size: 55.2 MB
- Tags: CPython 3.13, Windows x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `25eb2578dd6c4d1b2e0253fb3b4f8f7895e8bb4f3f1236832db0ab58e6a44998` | Copy |
| MD5 | `9e7a570b48ddbe92664a29a4e8577e13` | Copy |
| BLAKE2b-256 | `a2691732c3222ce63758c32746841099ac82059907cc3ff6bd77499da78abcbc` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp313-cp313-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/7f/af/3f7597d43813e8918bc2798aeed9b3be123a62e8a5be7de032cce03db8ed/pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 106.4 MB
- Tags: CPython 3.13, manylinux: glibc 2.35+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `99bb0f83ad20c61bdc63beb8d7f0c9ed3af6912a4770da170ce8d4bd02a7ecb0` | Copy |
| MD5 | `c7d157a51d513054a8570caaf67197d5` | Copy |
| BLAKE2b-256 | `7faf3f7597d43813e8918bc2798aeed9b3be123a62e8a5be7de032cce03db8ed` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_aarch64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp313-cp313-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/0a/4e/31b08dddba8c77676c9cf7ed90810b7dfcbd99cba845bb9b20b7bbaa4d7c/pymeshlab-2025.7.post1-cp313-cp313-manylinux_2_35_aarch64.whl)
- Upload date: Jan 30, 2026
- Size: 65.2 MB
- Tags: CPython 3.13, manylinux: glibc 2.35+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `2432dffe99e58e1b5e77dbfeb7690502b6d0ebccb1ed75356fca4676ec56c9a2` | Copy |
| MD5 | `20c01537d3f654494b5376eb69ad72c3` | Copy |
| BLAKE2b-256 | `0a4e31b08dddba8c77676c9cf7ed90810b7dfcbd99cba845bb9b20b7bbaa4d7c` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp313-cp313-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/27/52/a11aa52eb3b250f78a891b9e4ffcdf4af4da13a462d079cc6cf3d17d34ac/pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 54.5 MB
- Tags: CPython 3.13, macOS 11.0+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `06c7171f70ff86753535d1c0d952ead34854923061af37197e9cc22dea515e9d` | Copy |
| MD5 | `9bc0eb28d1c47a72f92b681696f07934` | Copy |
| BLAKE2b-256 | `2752a11aa52eb3b250f78a891b9e4ffcdf4af4da13a462d079cc6cf3d17d34ac` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp313-cp313-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/a7/06/ef68bf08d23f44118ab846b93dd30eaf87ad85cc44b4f3e5ac8764e9bc9f/pymeshlab-2025.7.post1-cp313-cp313-macosx_11_0_arm64.whl)
- Upload date: Jan 30, 2026
- Size: 65.0 MB
- Tags: CPython 3.13, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `841b1fa15fc76ab73e594f4bbfcbe339782b36be67d9387ff5aa5f4ca422e180` | Copy |
| MD5 | `21db3a77e9f3bdc64c8fda80713d1c3f` | Copy |
| BLAKE2b-256 | `a706ef68bf08d23f44118ab846b93dd30eaf87ad85cc44b4f3e5ac8764e9bc9f` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp312-cp312-win_amd64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp312-cp312-win\_amd64.whl](https://files.pythonhosted.org/packages/4f/06/66b91d2d77fbb2bf729dfe58692957bad3cea706ecb3fe51fca4b07c0c95/pymeshlab-2025.7.post1-cp312-cp312-win_amd64.whl)
- Upload date: Jan 30, 2026
- Size: 55.2 MB
- Tags: CPython 3.12, Windows x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `fc04cb2206e8d0194b2c8f61ea6ef54505bbe3d217e7f1960ee9608464f9bfad` | Copy |
| MD5 | `b4c0ad8b44a11f12a804bd651da27e1c` | Copy |
| BLAKE2b-256 | `4f0666b91d2d77fbb2bf729dfe58692957bad3cea706ecb3fe51fca4b07c0c95` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp312-cp312-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/a3/4c/b0b1b5ad425acd80abcff4632f0241ca490c52ef9c48013d71f573680a2a/pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 106.5 MB
- Tags: CPython 3.12, manylinux: glibc 2.35+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `bc453d89b114671affc747991a939b257d2320b71885b31213190c64081f5c35` | Copy |
| MD5 | `46873801f9f558175425e3e58cf3ae3e` | Copy |
| BLAKE2b-256 | `a34cb0b1b5ad425acd80abcff4632f0241ca490c52ef9c48013d71f573680a2a` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_aarch64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp312-cp312-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/6b/8d/6082aa85f8c918901221d1a7e1e810cb5b56eecbed59a5e688feea92c148/pymeshlab-2025.7.post1-cp312-cp312-manylinux_2_35_aarch64.whl)
- Upload date: Jan 30, 2026
- Size: 65.3 MB
- Tags: CPython 3.12, manylinux: glibc 2.35+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `d39fbaac1274adbbdf75cd999710d2ba48bd4d9087f34815afbdedb99dd3ded6` | Copy |
| MD5 | `79de917c3f040152e24385ddc1238f1c` | Copy |
| BLAKE2b-256 | `6b8d6082aa85f8c918901221d1a7e1e810cb5b56eecbed59a5e688feea92c148` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp312-cp312-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/f8/0d/6692ef6d96fa27763899665562c11ee6411eba55b2bddcda6799213dadac/pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 54.5 MB
- Tags: CPython 3.12, macOS 11.0+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `265503a06968420c8eb6934e3db78ff0767518000d8afd46ef3c976a506cfcf7` | Copy |
| MD5 | `3850b50d9187341123a42e3d12b6ba0f` | Copy |
| BLAKE2b-256 | `f80d6692ef6d96fa27763899665562c11ee6411eba55b2bddcda6799213dadac` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp312-cp312-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/ae/c1/a8db8ba66b5c51e700ba0eccea2c81f68a3223b775b0afe7b30a3da9a2ec/pymeshlab-2025.7.post1-cp312-cp312-macosx_11_0_arm64.whl)
- Upload date: Jan 30, 2026
- Size: 65.0 MB
- Tags: CPython 3.12, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `693101c1ade7aadbad114878626307bf434fe607de873449fbe6b6b95a30cd01` | Copy |
| MD5 | `d45f5ecfc856db7ca221e5592744f88d` | Copy |
| BLAKE2b-256 | `aec1a8db8ba66b5c51e700ba0eccea2c81f68a3223b775b0afe7b30a3da9a2ec` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp311-cp311-win_amd64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp311-cp311-win\_amd64.whl](https://files.pythonhosted.org/packages/e6/56/c4383522d9603cca76ad0c1c886014bf6ac4e79df96018e13025c669b068/pymeshlab-2025.7.post1-cp311-cp311-win_amd64.whl)
- Upload date: Jan 30, 2026
- Size: 55.2 MB
- Tags: CPython 3.11, Windows x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `3c1b87f3d6e6c8b129311b44f5c75a22df23c969b9d4300843286220a0d2a49c` | Copy |
| MD5 | `8ca809baf259c04c2738b5578f12cd44` | Copy |
| BLAKE2b-256 | `e656c4383522d9603cca76ad0c1c886014bf6ac4e79df96018e13025c669b068` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp311-cp311-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/c0/20/5b18072334280015899fce0a514a8455619421dfb122d37c1fd7166507db/pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 106.2 MB
- Tags: CPython 3.11, manylinux: glibc 2.35+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `c3c1b01f101334b14469ace3b004382cd313b80a128f551a1da77e3053f09c30` | Copy |
| MD5 | `98de389f50dab37a0ce6ec4ea0a6b29e` | Copy |
| BLAKE2b-256 | `c0205b18072334280015899fce0a514a8455619421dfb122d37c1fd7166507db` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_aarch64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp311-cp311-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/49/7b/caba5fba3e0cc57230b5600b4a4965e797d39aa59b3ef87e405f4fb9b5bc/pymeshlab-2025.7.post1-cp311-cp311-manylinux_2_35_aarch64.whl)
- Upload date: Jan 30, 2026
- Size: 65.1 MB
- Tags: CPython 3.11, manylinux: glibc 2.35+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `244324df41dc168a0adb0818b0585a91d31d10d73b4415d59b15eaaba0eec900` | Copy |
| MD5 | `8b4dd6760e15c260f49f3ba59732df02` | Copy |
| BLAKE2b-256 | `497bcaba5fba3e0cc57230b5600b4a4965e797d39aa59b3ef87e405f4fb9b5bc` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp311-cp311-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/d1/d1/d6a0a4fc5f4858f3ddbdaf72a28709aa05fc46efb052f1b14d5ab54c6a61/pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 54.5 MB
- Tags: CPython 3.11, macOS 11.0+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `56628cf8603195f057884ffafd006391a6baca9ef90aa7f7032c50a276c77bfb` | Copy |
| MD5 | `2f2eb4eec162752e1dc95eeca15d035a` | Copy |
| BLAKE2b-256 | `d1d1d6a0a4fc5f4858f3ddbdaf72a28709aa05fc46efb052f1b14d5ab54c6a61` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp311-cp311-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/4e/c4/0651d56e6af7680e76460f80ce2812e29b1bc5aefba3988423ea43095074/pymeshlab-2025.7.post1-cp311-cp311-macosx_11_0_arm64.whl)
- Upload date: Jan 30, 2026
- Size: 65.0 MB
- Tags: CPython 3.11, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `d4d2e9b9ef05b4205bb61b83326287a140ef87220bb0485c1caf42c446f41d37` | Copy |
| MD5 | `fe842700d85dc97b7efc9d6e831068a1` | Copy |
| BLAKE2b-256 | `4ec40651d56e6af7680e76460f80ce2812e29b1bc5aefba3988423ea43095074` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp310-cp310-win_amd64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp310-cp310-win\_amd64.whl](https://files.pythonhosted.org/packages/63/b5/eb7c2a986084175d2eb7351ea34de08fe9ca78bc9a0164fc7555a8f6bae8/pymeshlab-2025.7.post1-cp310-cp310-win_amd64.whl)
- Upload date: Jan 30, 2026
- Size: 55.2 MB
- Tags: CPython 3.10, Windows x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `c3761b15e9bcdff14c78b9dc291164b9752bef9f1e1b3fc5f83f1cdbefcd3c85` | Copy |
| MD5 | `dba9623a2279ff810b239ae9f29985ea` | Copy |
| BLAKE2b-256 | `63b5eb7c2a986084175d2eb7351ea34de08fe9ca78bc9a0164fc7555a8f6bae8` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp310-cp310-manylinux\_2\_35\_x86\_64.whl](https://files.pythonhosted.org/packages/07/a5/b0df05e63303dea51fc5026d00d5c4788c7ddbd7136175b1296b494c9161/pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 105.9 MB
- Tags: CPython 3.10, manylinux: glibc 2.35+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `a2559887a1b8d38390d05f69e7519f95bed3a24c75afba1023e2a98e82f546da` | Copy |
| MD5 | `b9bd8eeb568e8dcb3717e4cb1067bd54` | Copy |
| BLAKE2b-256 | `07a5b0df05e63303dea51fc5026d00d5c4788c7ddbd7136175b1296b494c9161` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_aarch64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp310-cp310-manylinux\_2\_35\_aarch64.whl](https://files.pythonhosted.org/packages/1e/d3/80ad31b6ce43d2e134a72038b932b59758fe5b4ed7c856d309ae4752061a/pymeshlab-2025.7.post1-cp310-cp310-manylinux_2_35_aarch64.whl)
- Upload date: Jan 30, 2026
- Size: 64.7 MB
- Tags: CPython 3.10, manylinux: glibc 2.35+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `f366cccb6ad74673a62cbfa77b38021eb67217c2e02bd0616b4d33214a8a6674` | Copy |
| MD5 | `6503574ebb2333452698097b69dad76e` | Copy |
| BLAKE2b-256 | `1ed380ad31b6ce43d2e134a72038b932b59758fe5b4ed7c856d309ae4752061a` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_x86_64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp310-cp310-macosx\_11\_0\_x86\_64.whl](https://files.pythonhosted.org/packages/1f/b6/34e2e7791298210472af8c70d284b30fe88b5350024ba274d06f1ef363d3/pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_x86_64.whl)
- Upload date: Jan 30, 2026
- Size: 54.5 MB
- Tags: CPython 3.10, macOS 11.0+ x86-64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `7a5ce54e8724259b6dd25bdaa35640a94327e6a5451c440ab80e36817a053cc1` | Copy |
| MD5 | `a31602568c0eb1c5b9b1951143e3ee39` | Copy |
| BLAKE2b-256 | `1fb634e2e7791298210472af8c70d284b30fe88b5350024ba274d06f1ef363d3` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")

Details for the file `pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_arm64.whl`.

### File metadata

- Download URL: [pymeshlab-2025.7.post1-cp310-cp310-macosx\_11\_0\_arm64.whl](https://files.pythonhosted.org/packages/73/7e/d44a74e360163ffc37f380c1be421c1594bd67e4ef9a4805691fdb662449/pymeshlab-2025.7.post1-cp310-cp310-macosx_11_0_arm64.whl)
- Upload date: Jan 30, 2026
- Size: 65.0 MB
- Tags: CPython 3.10, macOS 11.0+ ARM64
- Uploaded using Trusted Publishing? No
- Uploaded via: `twine/6.2.0 CPython/3.12.3`

### File hashes

| Algorithm | Hash digest |  |
| --- | --- | --- |
| SHA256 | `a5692a0a50cca49178ad9a3ceb02f60f200c7572b72f89964c7dbf915ef9e65a` | Copy |
| MD5 | `457cae71792110f0dead7633b37cdae9` | Copy |
| BLAKE2b-256 | `737ed44a74e360163ffc37f380c1be421c1594bd67e4ef9a4805691fdb662449` | Copy |

[See more details on using hashes here.](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode "External link")