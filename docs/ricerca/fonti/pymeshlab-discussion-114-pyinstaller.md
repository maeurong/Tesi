*Premise*: I deeply apologize if this is not the right place to ask this question. But maybe you can help me to understand which PyMeshLab modules are ignored by PyInstaller or maybe you have already tried to freeze PyMeshLab.

---

I am trying to create an executable from the following script (named test\_2.py):

```
import pymeshlab

def main():
    ms = pymeshlab.MeshSet()
    mesh_non_isotropic = ms.load_new_mesh('bunny10k.ply')
    mesh_isotropic = ms.remeshing_isotropic_explicit_remeshing()
    ms.save_current_mesh('bunny_isotropic_pymeshlab.ply')

if __name__ == '__main__':
    main()
```

The file bunny10k.ply can be downloaded [here](https://github.com/cnr-isti-vclab/meshlab/tree/master/sample).

I am using PyMeshLab 0.2.1, [PyInstaller](https://www.pyinstaller.org/), on Windows 10, in a python 3.8.10 virtual environment. The script works fine.

The PyInstaller command can be found below. The executable is created successfully.

```
pyinstaller test_2.py --hidden-import=numpy
```

When I run the executable I get the following error:

```
Traceback (most recent call last):
  File "test_2.py", line 20, in <module>
    main()
  File "test_2.py", line 15, in main
    mesh_non_isotropic = ms.load_new_mesh('bunny10k.ply')
pymeshlab.pmeshlab.PyMeshLabException: Unknown format for load: ply
[12648] Failed to execute script test_2
```

So it is not able to recognize the file format. Clearly, PyInstaller is not properly freezing the application. So can you just share any hint about which modules PyInstaller is ignoring, please?

Thanks!

Answered by [alemuntoni](https://github.com/alemuntoni)

Note:  
`load_new_mesh()` method of MeshSet does not return an object, and `remeshing_isotropic_explicit_remeshing()` does not return a mesh.

\--  
I don't know how it works pyinstaller, but it seems that it is not exporting the meshlab plugins.  
You can check the number of exporter plugins by calling `pymeshlab.number_plugins()`, result should be 49 in pymeshlab 0.2.1.

## 1 comment 1 reply