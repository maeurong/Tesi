## 🐛 Bug Description

Compiling the latest SciPy 1.17.0 version in standalone mode results in a ModuleNotFoundError.

## 🖥️ Environment

### 1\. Nuitka Version, Python Version, OS, and Platform

```shell
4.0.1
Commercial: None
Python: 3.12.8 (tags/v3.12.8:2dc476b, Dec  3 2024, 19:30:04) [MSC v.1942 64 bit (AMD64)]
Flavor: CPython Official
Executable: ~\Desktop\New folder (9)\venv-3.12\Scripts\python.exe
OS: Windows
Arch: x86_64
WindowsRelease: 11
Version C compiler: cl (cl 14.3).
```

### 2\. How Nuitka and Python were Installed

via pip in a venv

### 3\. Relevant PyPI Packages and Versions

```shell
scipy                    1.17.0      C:\Users\Tim\Desktop\New folder (9)\venv-3.12\Lib\site-packages pip
```
```shell
scipy 1.17.0 pip
```

## 🛠️ To Reproduce

```python
# Compilation instructions
# nuitka-project: --standalone

import scipy
print(scipy.__version__)
```

## 📉 Expected Behavior

Compile without any errors

## 📄 Actual Behavior & Output

```
(venv-3.12) PS C:\Users\Tim\Desktop\New folder (9)\test2.dist> .\test2.exe
Traceback (most recent call last):
  File "C:\Users\Tim\Desktop\NEDD60~1\TEST2~1.DIS\scipy\__init__.py", line 95, in <module scipy>
  File "C:\Users\Tim\Desktop\NEDD60~1\TEST2~1.DIS\scipy\_lib\_ccallback.py", line 1, in <module scipy._lib._ccallback>
  File "scipy/_lib/_ccallback_c.pyx", line 1, in init scipy._lib._ccallback_c
ModuleNotFoundError: No module named 'scipy._cyutility'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\Tim\Desktop\NEDD60~1\TEST2~1.DIS\test2.py", line 4, in <module>
  File "C:\Users\Tim\Desktop\NEDD60~1\TEST2~1.DIS\scipy\__init__.py", line 100, in <module scipy>
ImportError: The \`scipy\` install you are using seems to be broken, (extension modules cannot be imported), please try reinstalling.
```