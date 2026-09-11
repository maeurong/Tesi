### Checklist

- [ ] I have searched for [similar issues](https://github.com/isl-org/Open3D/issues).
- [ ] For Python issues, I have tested with the [latest development wheel](https://www.open3d.org/docs/latest/getting_started.html#development-version-pip).
- [ ] I have checked the [release documentation](https://www.open3d.org/docs/release/) and the [latest documentation](https://www.open3d.org/docs/latest/) (for `main` branch).

### My Question

I have a desktop application in PyQt6 that uses Open3D for point cloud visualisation. I tried to bundle it to the standalone executable using PyInstaller, but it crashes when I'm trying to run it with the DLL load failed error(traceback below). It happens only when I try to run it on the Windows device that do not have C++ Build tools. So, the question is how can I create standalone executable without the additional step with the build tools installation?

As I understand, pybind requires some DLLs on the target system:

```
Traceback (most recent call last):
   File "src\__main__.py", line 5, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\__init__.py", line 1, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\__main__.py", line 5, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\ui\__init__.py", line 1, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\ui\main.py", line 13, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\ui\views\presenter.py", line 25, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "src\ui\views\components\video\open3d_.py", line 1, in <module>
   File "PyInstaller\loader\pyimod02_importers.py", line 385, in exec_module
   File "open3d\__init__.py", line 97, in <module>
ImportError: DLL load failed while importing pybind: A dynamic link library (DLL) initialization routine failed.
[3924] Failed to execute script '__main__' due to unhandled exception!
```

Otherwise, can I know which DLLs are required for the Open3D? In this case I will try to include them to the bundle manually.