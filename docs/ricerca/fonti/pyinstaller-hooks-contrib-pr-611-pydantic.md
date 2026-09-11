The v2.0.0 of pydantic seems to have removed the `pydantic.compiled` attribute, and cython-compiled version of PyPI wheels do not seem to be available anymore.

Fixes [#610](https://github.com/pyinstaller/pyinstaller-hooks-contrib/issues/610).

---

## Comments

> **bwoodsend** · 2023-07-04
> 
> Glad one library has finally realised that blindly cythonizing everything is more trouble than it's worth.

> **Wyko** · 2023-07-04
> 
> Nice fast response to this issue!

> **alekssamos** · 2024-02-04
> 
> Hi. Everything has been updated to the latest versions, but it still doesn't work.

> **rokm** · 2024-02-04
> 
> > Hi. Everything has been updated to the latest versions, but it still doesn't work.
> 
> What is the pydantic version you are using, and what is the error traceback?

> **alekssamos** · 2024-02-04
> 
> Strange. What's it? It's working. Somehow it worked by itself. And it didn't work 10 minutes ago. I'm sorry, it's okay.  
> I think I've run the command `pip install -U pyinstaller-hooks-contrib`  
> And it was written that everything has already been installed and so the newest and no changes have been made.  
> And after that, I thought that nothing had changed.  
> And I wrote here, because there was an error before executing this command.  
> I am surprised by the instant response! Thank you very much! All the best!