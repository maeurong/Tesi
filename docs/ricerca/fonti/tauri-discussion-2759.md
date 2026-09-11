Discussion options

I have a command-line based Python app. It uses some PyPI packages. I'd like to make a Tauri app which will call this Python app to do some operations and calculations. I read the documentation on the Sidecar feature of Tauri. I am still not sure how to use this. I am thinking about embedding the whole Python interpreter and packages somehow. Which folder in the Tauri project should I place the Python interpreter? What would be the best practice to embed a Python app inside a Tauri app? Would it work if I create a conda environment and install packages and my Python app in the conda environment, and then copy the entire conda environment folder to a subfolder of my Tauri project? I'd appreciate any help.

You must be logged in to vote

The most straight forward way is probably the same as for nodejs apps (using [pkg](https://www.npmjs.com/package/pkg)). So you'd sidecar a packaged python app created with [pyinstaller](http://www.pyinstaller.org/index.html) or something.

Or, if you're absolutely crazy and proficient in rust there's also this one: [https://github.com/RustPython/RustPython](https://github.com/RustPython/RustPython). But i don't know how easy it would be to use it for a whole py project with dependencies (if it's even possible).

[View full answer](#discussioncomment-1489324)

Comment options

The most straight forward way is probably the same as for nodejs apps (using [pkg](https://www.npmjs.com/package/pkg)). So you'd sidecar a packaged python app created with [pyinstaller](http://www.pyinstaller.org/index.html) or something.

Or, if you're absolutely crazy and proficient in rust there's also this one: [https://github.com/RustPython/RustPython](https://github.com/RustPython/RustPython). But i don't know how easy it would be to use it for a whole py project with dependencies (if it's even possible).

You must be logged in to vote

9 replies

Comment options

Never mind, found it [https://tauri.app/v1/api/config#bundleconfig](https://tauri.app/v1/api/config#bundleconfig)

Comment options

There is no guide-like documentation, only the config and api themselves. Then there is this repo example: [https://github.com/tauri-apps/tauri/tree/dev/examples/resources](https://github.com/tauri-apps/tauri/tree/dev/examples/resources)

Comment options

> [@ThatXliner](https://github.com/ThatXliner) In theory yes, but it is more of a hassle. You'd have to bundle it as `resources` and then figure out how to run the executable inside it.

Is there a way to specify something in the resources folder as an `externalBin`? Been trying to make them interplay nicely but the binary then can't seem to find any of the other dynamic libraries in the resources folder.

Comment options

Not as externalBin (that's the config to include sidecar binaries), but in theory the shell scope config accepts `$RESOURCE` dirs: [https://tauri.app/v1/api/config/#shellallowlistscope](https://tauri.app/v1/api/config/#shellallowlistscope) - tbh no idea how reliable that really is.

An imo easier way to do it, until we implement resource mapping, would be to move all the resource files next to the tauri.conf.json (*not* inside a separate folder) - at least on windows all files should end up in the same folder this way.

Or maybe setting the cwd (current working dir) on the sidecar is enough?

Comment options

edited

Going a level deeper on this...

Is there a way to add firewall exceptions via WiX for a one-folder build. On a separate [github issue](https://github.com/tauri-apps/tauri/issues/4546) this fragment was provided:

```
<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi" xmlns:fire="http://schemas.microsoft.com/wix/FirewallExtension">
  <Fragment>
    <DirectoryRef Id="TARGETDIR">
      <Component Id="FirewallExceptions" Guid="de95bf40-7d9c-4ee6-8c47-1a06f3b7ebe3">
        <fire:FirewallException Id="ArbitraryId1" Name="App Name (TCP)" Program="[!Path]" Profile="all" Protocol="tcp" Scope="any" />
      </Component>
    </DirectoryRef>
  </Fragment>
</Wix>
```

with matching config:

```
"wix": {
  "fragmentPaths": ["./windows-installer/firewall-exception.wxs"],
  "componentRefs": ["FirewallExceptions"]
}
```

but that targets the main application. Is it possible to add a fragment that targets the built binary in `resources`? I'm mostly unsure about what the appropriate path would be during the install, as it looks like `[!Path]` is the main tauri app?

Answer selected by [rkimoakbioinformatics](https://github.com/rkimoakbioinformatics)

Comment options

I created an Example Repo: [https://github.com/cherob/tauri-rust-py](https://github.com/cherob/tauri-rust-py)

You must be logged in to vote

2 replies

Comment options

Thanks. I'll check it out.

Comment options

edited

[@drumnicorn](https://github.com/drumnicorn), I just tried running your template with npm (replaced yarn with npm) and it fails to run, throwing the following error:  
\`tauri-rust-py@0.0.0 build\_py

> pyinstaller -F py/test.py --distpath src-tauri/bin/python --clean -n test-x86\_64-pc-windows-msvc\`  
> ^^  
> EDIT: Nvm, I guess you do require pyinstaller in order to bundle the app, got it working after installing pyinstaller - thank you!

Comment options

I did a little experiment that involved creating a client-side Flask server for various distributable WebView solutions (electron, tauri, FlaskWebGui). You can see an overview on the [main branch](https://github.com/tcardlab/language-learning-dashboard/tree/main) and an example of the python sidecar on the [tauri branch](https://github.com/tcardlab/language-learning-dashboard/tree/Feat/client-tauri).

You must be logged in to vote

3 replies

Comment options

[@tcardlab](https://github.com/tcardlab) I’m interested in your example app. Not sure if this is the best place to ask a question, since I cannot find a place to write questions in the repo, thought I will write here.

Do you think it will be impossible to swap out the flask in your app for django?

I like to give it a shot just to experiment for my own learning.

Comment options

Its been years since I've touched django, but it should be possible. You'll have to set manage.py as the entry and pass the relevant cmd-line args (or edit manage.py to run without args).

I used appData(windows) as the location for the sqlite database. You may be able to reference my code if you plan to do the same (I used appdirs lib).

Its worth noting that I and others have had trouble fully closing pyinstaller sidecars when closing the app. I just used a quick hack to check if the parent process still exists, otherwise the python instance self-terminates. (on discord, some have implied this is due to using pyinstaller single-file mode. I have not tested whether that is true or not).

Also, I had trouble finding recommendations on how to handle client-side DB migrations. So, be sure to give that some thought.

Comment options

[@simkimsia](https://github.com/simkimsia) I hope you will share your code if you find success, I'd be interested to see it as well!

Comment options

i find a example for java [Java sidecar for a Tauri + Angular app](https://itnext.io/java-sidecar-for-a-tauri-angular-app-781a5d7d6db)

You must be logged in to vote

1 reply

Comment options

how about pyodide which use python wasm, pure web solution.

Category

[Q&A](https://github.com/orgs/tauri-apps/discussions/categories/q-a)

11 participants