- Nuitka version, full Python version, flavor, OS, etc. as output by *this exact* command.
	> python -m nuitka --version

```
1.9.7
Commercial: None
Python: 3.11.7 (main, Dec 15 2023, 10:49:17) [GCC]
Flavor: Unknown
Executable: /home/user/myvenv/bin/python
OS: Linux
Arch: x86_64
Distribution: Opensuse-Tumbleweed (based on opensuse suse) None
Version C compiler: /usr/lib64/ccache/gcc (gcc 13).
```

- How did you install Nuitka and Python

virtualenv myvenv  
then `pip install -U nuitka`

- The specific PyPI names and versions
	> python -m pip freeze

```
certifi==2023.11.17
gmsh==4.12.0
Nuitka==1.9.7
numpy==1.26.2
numpy-stl==3.1.1
ordered-set==4.1.0
python-utils==3.8.1
trimesh==4.0.8
typing_extensions==4.9.0
zstandard==0.22.0
```

- Many times when you get an error from Nuitka, your setup may be special

gmsh module has a standalone .so/.dll that should be included, I've tried different command line options to include it with no success

- Also supply a Short, Self Contained, Correct, Example  
	Here is a python code, when I run it with python after activating the venv it should not warnings  
	call it testgmsh.py example

```
import gmsh
print(gmsh.__version__)
```

- Provide in your issue the Nuitka options used  
	after activating the venv build with:  
	`python -m nuitka --standalone --remove-output testgmsh.py`

When I run `./testgmsh.dist/testgmsh.bin` I get

```
Warning: could not find Gmsh shared library libgmsh.so.4.12
Searched at these locations: [ LIST OF MANY LOCATIONS ]
```

Simply copying the .so solves the problem, same issue in Windows with same copy workaround working  
`cp -a ~/myvenv/lib/libgmsh.so.4.12 testgmsh.dist/`