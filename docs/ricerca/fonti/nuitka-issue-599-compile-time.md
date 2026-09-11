My end goal is to be able to use nuitka to create standalone executables from python scripts that import and use several common packages (numpy, pandas, xarray, and matplotlib.pyplot).

I am using nuitka v. 0.6.5 on Windows 10 (x86\_64) with Miniconda and python 3.6.7. I installed the C compiler using conda forge and m2w64-gcc package. I'm doing everything within a conda env, in which I have the various packages installed (numpy, pandas, xarray, matplotlib, etc) in addition to nuitka and mingw64.

I did some tests on simple hello.py type examples and the results seem to have very long compile times, very large sizes of resulting files, and long execution times for resulting files.

I'm trying to understand if there is something sub-optimal about my environment/configuration and/or the way I am calling nuitka-- as opposed to these performance concerns just being typical for nuitka, given the challenge to include and use all these large packages at once.

I set up a series progressively more demanding examples:

- hello1.py is the one in the tutorial (no imports, very simple)
- hello2.py imports numpy and executes one or two simple calls from it
- hello3.py also imports pandas and executes one or two simple calls from it too
- hello4.py also imports xarray and executes one or two simple calls from it too
- hello5.py also imports matplotlib.pyplot and executes one or two simple calls from it too

Note that hello5.py is an example of my end goal, as noted above. Maybe this end goal is simply not realistic for nuitka? Is anybody using nuitka for comparable purposes, without trouble?

An example of the compile command (for hello3.py) is as follows:

"python -m nuitka --standalone --mingw64 --follow-imports --plugin-enable=tk-inter --plugin-enable=qt-plugins --plugin-enable=pylint-warnings --plugin-enable=torch --plugin-enable=numpy hello3.py"

There are some warnings (no version of Visual Studio compiler...) during compilation, but at least for the first two examples, they are benign.

For the first test, hello1.py (no imports) the results are:

- compile time = about 10 seconds
- size of the resulting files (combined "build" and "dist" folders) = about 25 megs
- execution time of the resulting executable = trivial (as when executing uncompiled code)

For the second test, hello2.py (import and use numpy) the results are:

- compile time = several minutes
- size of the resulting files (combined "build" and "dist" folders) = about 744 megs
- execution time of the resulting executable = many seconds (far longer than when executing uncompiled code)

For the third test, the compilation failed with the error message

OSError: \[WinError 145\] The directory is not empty: 'hello3.dist\\PyQt5\\qt-plugins\\scenegraph'

but that was after 10s of minutes of compile time (!), and after the build/dist folders were already about 926 megs (!).

Unless there is something fundamentally wrong with my configuration and/or the syntax of my compilation command, I am led to believe that nuitka won't be able to help me reach my goal, because the compile times, storage size of resulting files, and executable file execution time are all so large as to be impractical. Correct?

Other ideas for how to approach my end goal are welcome, if it is indeed feasible with nuitka. If I am missing something obvious it would be great to learn what it is, and take a different tack.