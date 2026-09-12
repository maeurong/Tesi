# Distribuzione binaria di MeshRec (Windows 11 + macOS Apple Silicon)

**Domanda.** Come si consegna MeshRec a un tesista o al laboratorio come programma installabile, senza terminale, `uv` o git? Confronto fra freezing (PyInstaller, Nuitka, Briefcase, py2app), vie senza freezing (uv + python-build-standalone, PyApp, conda constructor, pex/shiv/PyOxidizer), formato finale (Inno Setup, WiX, MSIX, zip, `.app`/`.dmg`, firma) e CI.

**Data** 2026-09-11 · **Stato** completa · **Autore** researcher (sessione Claude Code)

**Tag.** `[V]` fonte primaria letta e salvata in `fonti/` · `[M]` misurato in sessione con comando · `[INF]` inferenza dichiarata · `[NON TROVATO]`.

**Contesto misurato** — cwd `/Users/mario/GitHub/Tesi/meshrec`, branch `main`, HEAD `b711053`, `du -sh`, `ls`, `.venv/bin/python -c`. Tutti i numeri `[M]` qui sotto vengono da lì.

---

## 0. Premesse del brief, verificate

| Premessa | Esito |
|---|---|
| `pyproject.toml:1-25`: `requires-python = ">=3.12,<3.13"`, open3d>=0.19, tetgen, pymeshlab>=2025.7.post1, gmsh>=4.15.2, fastapi, uvicorn; build hatchling; `meshrec = "meshrec.cli:main"` | `[M]` confermato (`sed -n 1,40p pyproject.toml`). Riga 43: `artifacts = ["src/meshrec/ui/**"]`. |
| `cli.py:222-272`: `serve` prova la porta, apre il browser dopo 1 s, `uvicorn.run(create_app(args.config), host, port, log_level="warning")` | `[M]` confermato. Nota utile per il freezing: l'app viene passata **come oggetto**, non come stringa di import → niente `workers`/`reload`, quindi nessun `multiprocessing` da gestire nel binario (v. §1.4). |
| `MeshRec.bat`/`MeshRec.command`: `cd` nella propria cartella, richiedono `uv` nel PATH, `uv run meshrec serve` | `[M]` confermato. |
| `.venv` 965 MB | `[M]` `du -sh .venv` → 965M; `site-packages` 865M. |
| PRODUCT.md: Windows 11 e macOS Apple Silicon, utenti successivi senza competenze da sviluppatore, nessun budget per certificati | `[M]` `PRODUCT.md:16-31` confermato (Windows 11 → macOS Apple Silicon → rientro su Windows; «altri tesisti e il laboratorio»). Budget certificati: non citato in PRODUCT.md, preso dal brief. |

Nessuna premessa falsa. Due fatti **in più**, trovati misurando, che cambiano il peso del problema:

- **`libgmsh.4.15.dylib` (80 MB) non sta in `site-packages`**: il wheel `gmsh` lo installa in `.venv/lib/`, e `gmsh.py` (420 KB, in `site-packages/`) lo cerca a runtime in una lista di percorsi relativi al proprio file: `moduledir/libname`, poi `parentdir1/lib`, `parentdir2/lib`, `parentdir2/Library/bin`, infine `ctypes.util.find_library` (`gmsh.py:41-80`) `[M]`. Ogni freezer che raccoglie solo `site-packages` **perde la libreria**; è l'origine di Nuitka #2649 e delle issue gmsh «could not find Gmsh shared library». La cura è banale — copiare la dylib/dll accanto a `gmsh.py` nel bundle — ma va fatta a mano.
- **pymeshlab porta con sé Qt intero**: `pymeshlab/Frameworks/` 137 MB (QtCore, QtGui, QtOpenGL, QtQml, QtQuick, QtSvg, QtNetwork, QtDBus, QtPrintSupport, boost, embree, lib3mf…) + `pymeshlab/PlugIns/` 32 MB con 66 plugin `.so` `[M]`; `load_default_plugins()` gira all'import (`pymeshlab/__init__.py:15-17`) `[M]`. Il freezer deve preservare la **struttura di cartelle** (`PlugIns/` e `Frameworks/` accanto a `pmeshlab.cpython-312-darwin.so`), non solo i file.

Pesi `[M]` che dominano l'artefatto (macOS arm64, wheel universal2 per open3d):

| Pacchetto | site-packages | Note |
|---|---|---|
| open3d 0.19.0 | 287 MB | `cpu/` 243 MB (pybind + `open3d_tf_ops`/`open3d_torch_ops` dylib), `resources/` 37 MB, `libomp.dylib`, `libtbb.12.dylib` |
| pymeshlab 2025.7.post1 | 181 MB | v. sopra |
| scipy | 87 MB | |
| libgmsh 4.15 | 80 MB | in `.venv/lib/`, fuori da site-packages |
| numpy | 26 MB | |
| pydantic + pydantic_core | 8 MB | |
| fastapi + uvicorn + meshio + pymeshfix + tetgen | ~7 MB | tetgen 808 KB |
| `src/meshrec/ui` | 1,1 MB | `vendor/` 712 KB (three.js) |
| CPython 3.12.13 (python-build-standalone, `~/.local/share/uv/python/cpython-3.12-macos-aarch64-none`) | 57 MB | `du -shL` |
| binario `uv` 0.12.9 | 36 MB | `ls -la $(which uv)` |

Wheel su PyPI (compressi) `[V]` — `fonti/pypi-open3d-0-19-0.md`, `fonti/pypi-pymeshlab.md`, `fonti/pypi-gmsh-4-15-2-json.md`, `fonti/pypi-tetgen.md`: open3d cp312 win_amd64 69,2 MB / macosx universal2 103,2 MB; pymeshlab cp312 win_amd64 55,2 MB / macosx_11_0_arm64 65,0 MB; gmsh 4.15.2 `py2.py3-none` win_amd64 42,2 MB / macosx_12_0_arm64 36,4 MB; tetgen 0.8.4 cp312-abi3 0,3 MB.

**Stima artefatto** `[INF]` (somma dei wheel compressi + Python + resto): **~260–300 MB compresso su macOS arm64, ~220–260 MB su Windows**; scompattato **~0,9–1,0 GB** su macOS (universal2 di open3d contiene due slice; se il freezer sfoltisce a `arm64` scende), **~0,7–0,8 GB** su Windows. Sotto il limite di 2 GiB per asset di GitHub Releases `[V]` `fonti/github-about-releases.md`.

---

## 1. Freezing: PyInstaller e Nuitka

### 1.1 PyInstaller — stato 2026

- Versione corrente **6.22.2, 17/08/2026**; Python supportato fino a 3.15; hook numpy/scipy aggiornati nel 2025-2026 `[V]` `fonti/pyinstaller-changes.md`.
- Python 3.12 pin: nessun problema, è nel range.
- Modalità: `--onedir` (default, cartella con eseguibile) e `--onefile` (un file che a ogni avvio si scompatta in `_MEIxxxxxx` sotto la temp). Il manuale sconsiglia `--onefile` + `--windowed` su macOS: «Such app bundles are inefficient, because they require unpacking on each run» `[V]` `fonti/pyinstaller-usage.md`. Con ~1 GB di dylib, l'onefile significherebbe **scompattare ~1 GB a ogni doppio clic** `[INF]`: **onedir obbligatorio** per MeshRec. Onefile su POSIX ha anche controlli di proprietà/permessi sulla temp aggiunti nel 2025-2026 `[V]` `fonti/pyinstaller-changes.md`.
- macOS: **«By default, PyInstaller ad-hoc (re)signs all collected binaries and the generated executable itself»**; con `--codesign-identity` accende l'hardened runtime (`--options=runtime`) — funziona solo con certificato Apple, «Trying to use self-signed certificate as a codesign identity will result in shared libraries failing to load» `[V]` `fonti/pyinstaller-feature-notes.md`. `--target-arch arm64|x86_64|universal2`, `--osx-bundle-identifier`, `--windowed` produce il `.app` `[V]` `fonti/pyinstaller-usage.md`.
- Issue #7937 (2023): un onefile firmato «Developer ID» + `-o runtime` a mano dopo il build **si rompe** («Error loading Python lib … code signature in …») — la firma va fatta **dal build** con `--codesign-identity`, non riapplicata dopo, e onefile + firma è la combinazione più fragile `[V]` `fonti/pyinstaller-issue-7937-notarization.md`.

### 1.2 PyInstaller — le quattro dipendenze native

Nessun hook ufficiale per open3d, pymeshlab, gmsh, tetgen: nel repo `pyinstaller-hooks-contrib/stdhooks` esiste `hook-scipy.py`; **non** esistono hook per open3d, pymeshlab, gmsh, tetgen, uvicorn, fastapi, meshio, pymeshfix `[V]` `fonti/pyinstaller-hooks-contrib-stdhooks.md` (la lista letta è lunga; per pydantic v2 esiste una PR #611 di aggiornamento hook `[V]` `fonti/pyinstaller-hooks-contrib-pr-611-pydantic.md`, quindi pydantic è coperto).

| Pacchetto | Problema noto | Ricetta (da fonti + struttura misurata) |
|---|---|---|
| **open3d** | Open3D #6624 (gen 2024, Windows): «DLL load failed while importing pybind: A dynamic link library (DLL) initialization routine failed» su macchine **senza runtime C++** — l'exe funzionava sul PC dello sviluppatore e falliva altrove; chiusa senza soluzione nel thread `[V]` `fonti/open3d-issue-6624-pyinstaller.md`. | `--collect-all open3d` (porta `cpu/`, `resources/`, `libomp`, `libtbb`) `[INF]` da struttura `[M]`; su Windows **includere il VC++ Redistributable nell'installer** (Inno Setup lo può lanciare) `[INF]` — è la lettura più plausibile di #6624. Nessuna issue 2025-2026 trovata su GitHub Open3D per PyInstaller `[NON TROVATO]`: assenza di segnalazioni, non prova di funzionamento. |
| **pymeshlab** | Discussion #114 (2021, pymeshlab 0.2.1, Win10): freezato, `pymeshlab.number_plugins()` → plugin non caricati, «Unknown format for load: ply»; il maintainer rimanda a hidden import, nessuna ricetta completa `[V]` `fonti/pymeshlab-discussion-114-pyinstaller.md`. Nulla di più recente `[NON TROVATO]`. | `--collect-all pymeshlab` preservando `PlugIns/` e `Frameworks/` accanto al `.so` `[INF]` da `[M]`; **test di accettazione**: `pymeshlab.number_plugins()` nel bundle uguale a quello nel venv. Su macOS i framework Qt dentro un `.app` PyInstaller sono un caso noto di firma ricorsiva (`--deep`) `[V]` `fonti/pyinstaller-feature-notes.md`. |
| **gmsh** | La dylib/dll sta fuori da site-packages (`[M]` sopra); Nuitka #2649 (gen 2024, gmsh 4.12): «Warning: could not find Gmsh shared library libgmsh.so.4.12», workaround «copiare manualmente il file .so nella dist» `[V]` `fonti/nuitka-issue-2649-gmsh.md`. Le issue GitLab gmsh #1355/#2750 sono dietro Anubis: `[NON TROVATO]` in sessione (Access Denied). | `--add-binary ".venv/lib/libgmsh.4.15.dylib:."` (macOS) / `--add-binary ".venv/Lib/gmsh-4.15.dll;."` (Windows): `gmsh.py:54` cerca **prima** `moduledir/libname`, quindi accanto a `gmsh.py` nella dist funziona senza toccare il codice `[M]`. |
| **tetgen** | Estensione singola `_tetgen.abi3.so` 808 KB `[M]`. Nessuna issue trovata `[NON TROVATO]`. | Analisi statica di PyInstaller la vede; rischio basso `[INF]`. |
| **scipy** | Hook ufficiale, aggiornato per 1.14→ `[V]` `fonti/pyinstaller-changes.md`. | Nulla da fare. |
| **uvicorn/fastapi** | #7339 (2022): in `--windowed` `sys.stdout` è `None` e uvicorn fallisce «Unable to configure formatter 'default'» (`isatty()`); chiusa «not-our-bug» `[V]` `fonti/pyinstaller-issue-7339-uvicorn.md`. Discussion uvicorn #1820: guai solo con `workers>1` + stringa di import `[V]` `fonti/uvicorn-discussion-1820-pyinstaller.md`. | MeshRec passa l'app come oggetto e senza workers (`cli.py:268-270` `[M]`): #1820 non si applica. Per #7339: costruire **console** (o, se windowed, riassegnare `sys.stdout/err` a un file di log prima di `uvicorn.run`) `[INF]`. Hidden import da aggiungere per prudenza: `uvicorn.logging`, `uvicorn.loops.auto`, `uvicorn.protocols.http.auto`, `uvicorn.protocols.websockets.auto`, `uvicorn.lifespan.on` (ricorrenti nelle segnalazioni, non da doc ufficiale) `[INF]`. |
| **ui statica** | `src/meshrec/ui/**` è un artefatto hatchling `[M]`. | `--add-data "src/meshrec/ui:meshrec/ui"` e risolvere il percorso con `importlib.resources`/`sys._MEIPASS` `[INF]`. |

**Percorsi relativi** (`runs/`, `experiments/`, `.cache/viewport` — `MeshRec.command:10-14` `[M]`): in un `.app` la cwd al doppio clic è `/`, in un onedir dentro `Program Files` la cartella non è scrivibile. Qualunque via binaria richiede che il programma scelga una cartella dati dell'utente (`~/Documents/MeshRec` o simile) — non è nel perimetro di questa ricerca, ma è un prerequisito di tutte le vie qui sotto `[INF]`.

**Dimensione/avvio** `[INF]`: onedir ≈ 0,7–1,0 GB scompattato (v. §0); avvio ≈ import normali (qualche secondo, dominati da open3d/pymeshlab, come oggi). Onefile: escluso.

### 1.3 Nuitka — stato 2026

- Versione corrente **4.2**, Python 3.4–3.14 supportato, 3.15 sperimentale; richiede compilatore C11 (VS 2022 / MinGW64 / clang-cl su Windows, clang su macOS) `[V]` `fonti/nuitka-changelog.md`, `fonti/nuitka-user-manual.md`. Python 3.12: ok.
- **open3d**: «Standalone: Added support for open3d package» in Nuitka 2.4 `[V]` `fonti/nuitka-release-2-4.md`. pymeshlab e gmsh: **mai citati** in release notes/changelog `[V]` stessi file → gmsh resta a mano (`--include-data-files=.venv/lib/libgmsh.4.15.dylib=libgmsh.4.15.dylib`) come in #2649, pymeshlab senza precedenti `[NON TROVATO]`.
- **scipy 1.17**: #3780 (17/02/2026, Nuitka 4.0.1, Python 3.12.8, Win11): «ModuleNotFoundError: No module named 'scipy._cyutility'» in standalone; PR #3781 associata `[V]` `fonti/nuitka-issue-3780-scipy.md`; il changelog 4.2 dice «Added support for newer scipy» `[V]`. Segnale che ogni bump di scipy può rompere lo standalone finché Nuitka non lo rincorre.
- Modalità `--standalone` (cartella) / `--onefile` (estrae in temp) / `--macos-create-app-bundle` `[V]` `fonti/nuitka-user-manual.md`. Firma macOS: **non documentata** nel manuale letto `[NON TROVATO]`.
- Tempi/dimensioni: issue #599 (storica, 2019) documenta compile time lunghi e dist grandi con numpy/pandas/matplotlib `[V]` `fonti/nuitka-issue-599-compile-time.md`; le comparazioni terze (CodersLegacy, blog 2026) riportano «anche più di un'ora» e cartelle ~2× PyInstaller — non le salvo come primarie, le cito come tendenza `[INF]`. Per MeshRec: **compila C per tutto il codice Python raggiungibile** — inclusi scipy/numpy puri-Python — con MSVC/clang sui runner GitHub; vantaggio (offuscamento, velocità del codice Python) irrilevante qui: il tempo di MeshRec sta nelle librerie native, non nel Python.

### 1.4 Verdetto sezione 1

PyInstaller onedir è **praticabile** con quattro correzioni manuali (open3d collect-all + vcredist, pymeshlab collect-all + test `number_plugins()`, gmsh add-binary, uvicorn console/stdout) e nessuna ricetta pubblica già pronta per open3d+pymeshlab insieme `[NON TROVATO]`: chi lo adotta scrive la prima. Nuitka aggiunge compilatore, tempi e un inseguimento continuo su scipy senza vantaggio per questo caso.

---

## 2. Briefcase (BeeWare) e py2app

### 2.1 Briefcase

- Richiede Python ≥ 3.11 `[V]` `fonti/briefcase-macos.md`, `fonti/briefcase-windows.md`. 3.12: ok.
- macOS: **«By default, apps will be both signed and notarized when they are packaged»**; `--adhoc-sign` produce app «eseguibili solo sulla macchina dello sviluppatore»; `.pkg` è **il formato obbligatorio per le app console**, `.dmg` per le GUI; iCloud Drive impedisce la firma `[V]` `fonti/briefcase-macos.md`. MeshRec (server + browser, senza finestra Toga) è un'app console → `.pkg` + notarizzazione, cioè Apple Developer Program.
- Windows: MSI via WiX o zip; usa il **Python.org embeddable package**; firma con certificato o `--adhoc-sign` = non firmato `[V]` `fonti/briefcase-windows.md`.
- Dipendenze binarie: solo wheel già costruiti; per universal2 prova a fondere wheel arm64+x86_64 e avvisa su numpy (`.a`, `.h`, `__config__.py` non fondibili) `[V]` `fonti/briefcase-macos.md`. Nessuna traccia di open3d/pymeshlab/gmsh con Briefcase `[NON TROVATO]`; la dylib di gmsh fuori da site-packages è un caso che Briefcase non contempla `[INF]`.
- **napari ha lasciato Briefcase per conda constructor** (NAP-2, luglio 2022) citando incompatibilità ABI fra wheel PyPI, metadati insufficienti, e «PyPI non distribuisce Python: quella responsabilità ricade su Briefcase, altre parti mobili» `[V]` `fonti/napari-nap-2-conda.md`. È il precedente scientifico più vicino a MeshRec (app con pila nativa pesante).

### 2.2 py2app

- 0.29.10, Python ≥ 3.10; supporto 3.12 dalla 0.28.7, 3.13 dalla 0.28.8; ricette numpy/scipy storiche; «won't work with editable installs» `[V]` `fonti/py2app-changelog.md`.
- Solo macOS: non risolve Windows. Escluso per questo, non per demeriti.

---

## 3. Vie senza freezing

### 3.1 uv + python-build-standalone + lockfile (installer «portabile»)

Idea: l'artefatto è una cartella con `uv.exe`/`uv` (36 MB `[M]`), un CPython da python-build-standalone (57 MB `[M]`), i wheel del lockfile pre-scaricati e uno script di avvio; al primo avvio `uv sync --frozen --no-dev --offline` costruisce il venv in loco.

- uv usa distribuzioni **python-build-standalone**; `UV_PYTHON_INSTALL_DIR`/`--install-dir` scelgono dove sta Python; `python-downloads = never|manual|automatic` `[V]` `fonti/uv-python-versions.md`.
- `--frozen` usa il lockfile senza verificarlo; `--no-dev` esclude il gruppo dev `[V]` `fonti/uv-projects-sync.md`.
- `UV_OFFLINE` (= `--offline`), `UV_CACHE_DIR`, `UV_PROJECT_ENVIRONMENT` (cartella del venv), `UV_PYTHON_INSTALL_MIRROR` accetta **`file://`** locale per il tarball di Python `[V]` `fonti/uv-environment-vars.md`. Con cache pre-riempita e mirror `file://`, il primo avvio è **offline** `[INF]`.
- **uv-pack** (davnn, 56 stelle, 19 commit, MIT) fa esattamente questo: export del lock, download wheel, download python-build-standalone, cartella `pack/` con script sh/PowerShell di unpack; **solo stessa piattaforma** (niente cross-build), download via `pip download` lento `[V]` `fonti/uv-pack-readme.md`. Piccolo e giovane: da leggere come dimostrazione che la ricetta sta in ~200 righe di script, non come dipendenza da adottare `[INF]`.
- `uv.lock` esiste già nel repo `[M]`, `MeshRec.bat/.command` già fanno `uv run` `[M]`: la distanza da oggi è **sostituire «installa uv e clona» con «scompatta lo zip»**.
- Rischio open3d/pymeshlab/gmsh: **zero** — i wheel vengono installati come nel venv di sviluppo, `libgmsh` finisce in `lib/` dove `gmsh.py` la trova. È l'unica via in cui il comportamento a destinazione è identico a quello misurato in sviluppo.
- Trade-off: niente `.app` vero (doppio clic su `.command` = Terminale aperto), niente icona nel Dock, cartella ~1 GB a destinazione, e **la cartella non deve stare in `Program Files`/`Applications`** (venv scrivibile) → destinazione `~/MeshRec` o `%LOCALAPPDATA%\MeshRec` `[INF]`. Aggiornamento = nuovo zip (o `uv sync` contro una release, se si accetta la rete).
- `uv tool install git+https://…`: richiede uv e git sul PC del tesista → è la situazione di oggi, non risolve la domanda.

### 3.2 PyApp (ofek) / `hatch build -t binary`

- Binario Rust che al primo avvio scarica python-build-standalone e installa il progetto; opzioni `PYAPP_DISTRIBUTION_EMBED` (Python dentro il binario), `PYAPP_PROJECT_PATH` (wheel locale), `PYAPP_UV_ENABLED`; comandi di self-update; `hatch build -t binary` lo integra `[V]` `fonti/pyapp-docs.md`. MeshRec è già hatchling `[M]`.
- Limite: i **wheel delle dipendenze** non sono embeddabili nel binario dalle opzioni lette — servono rete al primo avvio o un indice locale (`PIP_INDEX_URL`/`UV_INDEX` verso una cartella) `[INF]`; richiede toolchain Rust in CI `[INF]`. Utile come «installer sottile» se si accetta il primo avvio online; non offline nativo.

### 3.3 conda constructor

- Produce `.exe` (Windows), `.pkg`/`.sh` (macOS), `.msi` sperimentale; `specs` accetta **solo pacchetti conda**; pip solo via `post_install` `.bat`/`.sh`; firma con `signing_identity_name` (installer) + `notarization_identity_name` (Application cert) su macOS, `windows_signing_tool: signtool|azuresigntool` `[V]` `fonti/constructor-construct-yaml.md`.
- Tutte e quattro le native esistono su conda-forge: pymeshlab 2025.7.post1 (win-64, osx-arm64; upload 31/01/2026) `[V]` `fonti/conda-forge-pymeshlab.md`; open3d 0.19.0 (win-64, osx-arm64; 24/01/2025) `[V]` `fonti/conda-forge-open3d.md`; gmsh e tetgen (feedstock esistenti, non salvati) `[INF]`.
- Precedente: napari (NAP-2) `[V]`. Costo: **seconda catena di dipendenze** (conda-forge invece di PyPI/uv.lock) da mantenere allineata al `pyproject.toml`, `menuinst` per le scorciatoie, e installer senza firma che su macOS produce l'avviso pkg `[INF]`. Adatto a chi vive già in conda; MeshRec non ci vive.

### 3.4 PyOxidizer, pex, shiv

- **PyOxidizer**: il maintainer, 17/03/2024: «I haven't meaningfully updated PyOxidizer … since January 2023 … the future of PyOxidizer is uncertain, possibly dead» `[V]` `fonti/pyoxidizer-issue-741-status.md`. Escluso.
- **pex `--scie`**: eseguibile nativo con CPython python-build-standalone dentro (`eager`) o scaricato al bisogno (`lazy`); esempi solo Linux nella doc letta, Windows/macOS arm64 non menzionati `[V]` `fonti/pex-scie.md`. Supporto Windows di pex storicamente parziale `[INF]` → non per Windows 11.
- **shiv**: zipapp che estrae in `~/.shiv` perché «Shared objects loaded via the dlopen syscall require a regular filesystem»; **richiede Python sul target** (non lo distribuisce) `[V]` `fonti/shiv-docs.md`. Non risponde alla domanda.

---

## 4. Installer e formato finale

### 4.1 Windows

- **Inno Setup**: un `setup.exe`, supporta «digitally signed installs and uninstalls», Windows 7→11 incl. Arm; gratuito per uso non commerciale, licenza commerciale per commercial users `[V]` `fonti/inno-setup-info.md`. Adatto a impacchettare la cartella onedir/portabile, creare scorciatoia e — se serve per open3d — lanciare `vc_redist.x64.exe` `[INF]`.
- **WiX**: MSI; è ciò che Briefcase usa sotto `[V]` `fonti/briefcase-windows.md`. Più formale, più verboso; nessun vantaggio per un tesista `[INF]`.
- **MSIX**: la firma è **obbligatoria**; Windows 11 accetta pacchetti non firmati solo via PowerShell con OID speciale nel manifest (scenario di test), altrimenti serve certificato fidato sul PC `[INF]` da ricerca (doc Microsoft `unsigned-package`, non salvata perché il dominio learn.microsoft.com era bloccato in sessione — `[NON TROVATO]` come fonte salvata). Via Store: Microsoft ri-firma gratis `[V]` `fonti/ms-code-signing-options.md`. Store = account, certificazione, tempi: fuori scala per una tesi `[INF]`.
- **Portable zip**: nessun installer, nessun avviso «installer», ma SmartScreen si applica **all'exe** scaricato (Mark-of-the-Web) e la cartella va messa in una posizione scrivibile `[INF]`.

**SmartScreen** (doc Microsoft via mirror GitHub `[V]` `fonti/ms-smartscreen-reputation.md`, `fonti/ms-code-signing-options.md`):
- Due reputazioni: **publisher** (certificato) e **file hash** («Has this specific file been downloaded by users without indications of malicious behavior?»). «Even when signed, a newly created binary could still show a SmartScreen warning until its hash or publisher certificate accumulates sufficient evidence of positive reputation».
- Non firmato: «Windows protected your PC» → «More info» → «Run anyway»; in ambienti gestiti l'opzione può essere disabilitata da policy. Un laboratorio universitario con PC a dominio è esattamente quel caso `[INF]`.
- Opzioni e costi (tabella Microsoft): **Azure Artifact Signing** (ex Trusted Signing) ~9,99 $/mese, organizzazioni USA/Canada/UE/UK, **individui solo USA e Canada**; OV 150–300 $/anno, mondiale; EV 400+ $/anno e «dal 2024 non bypassa più SmartScreen»; self-signed = blocco per il pubblico `[V]` `fonti/ms-code-signing-options.md`. Il blog Melatonin (aggiornato 2026) conferma 9,99 $/mese e che «dal aprile 2026 gli autonomi possono candidarsi, senza più i 3 anni di storia» — ma resta il vincolo geografico Microsoft: **un individuo in Italia non è idoneo**; un'organizzazione UE (l'ateneo) sì `[V]` `fonti/melatonin-azure-trusted-signing.md`.
- **SignPath Foundation**: firma gratuita per progetti OSS con licenza OSI-approved, sviluppo attivo, release già pubblicate, MFA per tutto il team, ruoli Author/Reviewer/Approver dichiarati e policy di firma pubblicata; il certificato è **a nome della Foundation** `[V]` `fonti/signpath-terms.md`. MeshRec è MIT e il repo è pubblico (`gh repo view` → PUBLIC) `[M]`: **idoneo sulla carta**; costo = burocrazia (candidatura, policy sul README, ruoli), non denaro. Reputazione SmartScreen comunque da accumulare (vale per ogni firma OV).

### 4.2 macOS

- **Gatekeeper da Sequoia (15)**: Apple, developer news: «In macOS Sequoia, users will no longer be able to Control-click to override Gatekeeper when opening software that isn't signed correctly or notarized» (citato via Michael Tsai; il dominio developer.apple.com era irraggiungibile in sessione per la pagina news, raggiungibile per `programs/whats-included`) `[V]` `fonti/mjtsai-sequoia-gatekeeper.md`. Procedura ufficiale per l'utente (guida macOS Tahoe 26): doppio clic → avviso → **System Settings › Privacy & Security › Open Anyway** (compare entro circa un'ora dal tentativo) → password → Open; Apple avverte che «Overriding security settings to open an app is the most common way that a Mac gets infected with malware» `[V]` `fonti/apple-support-open-unknown-developer.md`. Il tesista vede quindi: un dialogo che gli dice che l'app può contenere malware, con i soli bottoni «Done» e «Move to Trash», e deve sapere di andare nelle Impostazioni `[INF]` da `[V]`.
- `xattr -d com.apple.quarantine MeshRec.app` (o `-rc` ricorsivo) toglie l'attributo di quarantena messo dal browser e salta l'avviso; è un comando da Terminale, cioè esattamente ciò che la domanda vuole evitare; può stare in uno script `.command` di primo avvio, ma anche quel `.command` scaricato è in quarantena `[INF]`.
- **Firma ad-hoc**: PyInstaller la fa da sé `[V]` `fonti/pyinstaller-feature-notes.md`; su Apple Silicon è obbligatoria per caricare i binari, ma **non** soddisfa Gatekeeper (serve Developer ID + notarizzazione) `[V]` stessa fonte + `fonti/briefcase-macos.md` («ad-hoc … only on the developer's machine»).
- **Apple Developer Program: 99 USD/anno**, include certificati (Developer ID) e strumenti; la pagina non nomina la notarizzazione ma il servizio `notarytool` è riservato ai membri `[V]` `fonti/apple-developer-program-whats-included.md` + `[INF]`. Briefcase automatizza firma+notarizzazione con `--resume` sulle attese lunghe («in some cases, hours») `[V]` `fonti/briefcase-macos.md`; con PyInstaller si fa a mano (`--codesign-identity` al build, poi `xcrun notarytool submit` + `stapler`) `[INF]`. Constructor ha `signing_identity_name`/`notarization_identity_name` `[V]` `fonti/constructor-construct-yaml.md`.
- **`.dmg`**: `create-dmg` (brew, 2,6k stelle, mantenuto), opzioni `--codesign`, `--notarize`, `--app-drop-link` `[V]` `fonti/create-dmg-readme.md`. Senza firma il dmg si monta comunque; l'avviso arriva all'apertura dell'app.
- **Cosa si fa gratis in modo dignitoso**: (a) ad-hoc + pagina di istruzioni con screenshot del percorso «Privacy & Security › Open Anyway» — funziona, umilia un po'; (b) chiedere all'ateneo/laboratorio se ha un **Apple Developer account di ente** (molti dipartimenti lo hanno per iOS) e farsi rilasciare un Developer ID Application — costo zero per Mario, notarizzazione vera `[INF]`; (c) 99 USD/anno personali.

---

## 5. CI: GitHub Actions + Releases

- Runner: `macos-latest`, `macos-14`, `macos-15`, `macos-26` sono **arm64 (M1, 3 CPU, 7 GB)**; Intel su `macos-15-intel`/`macos-26-intel`; Windows `windows-latest`/`windows-2025`/`windows-2022`; **repo pubblici: «free and unlimited»** con runner standard `[V]` `fonti/github-hosted-runners.md`. Repo privati: 2 000 min/mese Free, moltiplicatore macOS 0,062 $/min contro 0,006 Linux `[V]` `fonti/github-actions-billing.md`. Il repo Tesi è pubblico `[M]` → costo CI zero.
- Releases: asset < 2 GiB ciascuno, fino a 1 000 asset, «no limit on the total size of a release, nor bandwidth usage» `[V]` `fonti/github-about-releases.md`. Un artefatto da 300 MB per piattaforma ci sta.
- `softprops/action-gh-release@v3` (v2.6.2 è l'ultima v2, non più mantenuta), `on: push: tags: v*`, `permissions: contents: write`, `files:` con glob `[V]` `fonti/action-gh-release-readme.md`.
- Schema `[INF]`: matrix `{windows-latest, macos-latest}` → `uv sync --frozen --no-dev` → build (PyInstaller onedir **o** confezionamento della cartella portabile) → test fumo nel bundle (`meshrec --version`, `pymeshlab.number_plugins()`, `import gmsh; gmsh.initialize()`, `import open3d`) → zip/dmg/Inno → upload. 7 GB di RAM sul runner macOS bastano per PyInstaller su ~1 GB di binari `[INF]`; Nuitka con MSVC/clang su quei runner è l'unica via che rischia il tempo massimo del job `[INF]`.
- Firma in CI: Azure Artifact Signing ha action ufficiale con sei segreti `[V]` `fonti/melatonin-azure-trusted-signing.md`; Apple via `codesign` + `notarytool` con certificato importato da secret `[INF]`.

---

## 6. Tabella comparativa

Legenda costo di adozione: giorni-persona stimati `[INF]` per arrivare al primo artefatto che passa il test fumo su entrambe le piattaforme, incluso ricavare le ricette mancanti.

| Via | Costo adozione | Artefatto (compresso / a terra) `[INF]` | Esperienza utente finale | Manutenzione | Rischio specifico open3d/pymeshlab/gmsh |
|---|---|---|---|---|---|
| **A. Cartella portabile: uv + python-build-standalone + wheel del lock, `uv sync --frozen --offline` al primo avvio** | 1–2 gg (script di build + zip; base già in `MeshRec.bat/.command`) | ~300 MB / ~1 GB | Scompatta zip, doppio clic su `MeshRec.command`/`.bat`; **Terminale visibile**; avviso Gatekeeper/SmartScreen sullo script e su `uv`, primo avvio 30–60 s per il sync | Bassissima: stesso `uv.lock` dello sviluppo, nessuna ricetta di freezing | **Nullo**: identico al venv misurato |
| **B. PyInstaller onedir + Inno Setup / `.app`+`.dmg`** | 3–6 gg (quattro ricette manuali, test `number_plugins`, vcredist, gestione cwd) | ~300 MB / 0,7–1 GB | `setup.exe` con scorciatoia; `.app` nel Dock; avvisi SmartScreen/Gatekeeper se non firmato | Media: ogni bump di open3d/pymeshlab/scipy può rompere hook e va ritestato nel bundle; PyInstaller stesso attivo (6.22.2, 08/2026) | Medio: #6624 (DLL init su PC senza runtime C++), #114 (plugin pymeshlab), libgmsh fuori da site-packages — tutti risolvibili, nessuno documentato insieme |
| **C. Nuitka standalone** | 5–10 gg (come B + compilatore + tempi di build + inseguimento scipy #3780) | ~2× B a terra (tendenza) | Come B | Alta: rincorsa continua (scipy 1.17 rotto a feb 2026) | Medio-alto: open3d supportato da 2.4, pymeshlab e gmsh mai citati |
| **D. Briefcase** | 3–5 gg + **99 USD/anno obbligatori** su macOS (console app → `.pkg` notarizzato; ad-hoc = solo PC dello sviluppatore) | come B | MSI + `.pkg`, il più «da installer» | Media; napari l'ha abbandonato per pile native pesanti | Medio-alto: nessun precedente; libgmsh fuori da site-packages non gestito |
| **E. conda constructor** | 4–8 gg (seconda catena di dipendenze su conda-forge, `post_install`, menuinst) | ~400–600 MB `[INF]` | Installer nativo `.exe`/`.pkg`, il più «professionale» (napari, Spyder) | Alta: due lock (uv + conda) da tenere allineati | Basso: tutte e quattro su conda-forge; ma versioni possono divergere da PyPI |
| **F. PyApp / hatch binary** | 2–3 gg + toolchain Rust | ~60 MB binario + download al primo avvio | Un exe; **serve rete al primo avvio** | Bassa | Nullo (installa i wheel veri) |
| **G. py2app** | — | — | — | — | Solo macOS: fuori |
| **H. pex scie / shiv / PyOxidizer** | — | — | — | PyOxidizer «possibly dead»; shiv richiede Python; pex Windows non documentato | Fuori |

Firma (ortogonale alla via):

| | Costo | Effetto | Idoneità Mario |
|---|---|---|---|
| Nessuna firma | 0 | Sequoia: Impostazioni › Privacy & Security › Open Anyway; Win: «Windows protected your PC» → Run anyway (disattivabile da policy) | — |
| Apple Developer Program | 99 USD/anno | notarizzazione, nessun avviso | sì (o via ateneo) |
| Azure Artifact Signing | 9,99 USD/mese | reputazione SmartScreen legata all'identità, si accumula | **no come individuo in Italia**; sì come organizzazione UE |
| OV da CA | 150–300 USD/anno + token hardware | come sopra | sì |
| SignPath Foundation | 0 | firma OV a nome della Foundation | sì sulla carta (MIT, pubblico); burocrazia |

---

## 7. Raccomandazione (argomentata; la decisione resta a Mario)

**Raccomandazione: via A subito, via B come secondo passo solo se il laboratorio la chiede.**

1. **A (cartella portabile con uv)** risponde alla domanda letterale — niente terminale da digitare, niente `uv` da installare, niente git — con il rischio tecnico più basso di tutte le vie, perché **non cambia nulla di ciò che gira**: stesso `uv.lock`, stessi wheel, `libgmsh` nel posto in cui `gmsh.py` la cerca. Le quattro trappole di §1.2 non esistono. Costa uno script di build in CI e un README con tre screenshot (Open Anyway / Run anyway). Il prezzo è estetico: si vede una finestra di Terminale/cmd e non c'è icona nel Dock. Per «altri tesisti e il laboratorio» è un prezzo sostenibile; per un prodotto no.
2. **B (PyInstaller onedir)** è la via giusta se serve un `.app`/`setup.exe` vero. Non è bloccata da nulla di noto, ma **nessuno ha pubblicato la ricetta open3d + pymeshlab + gmsh insieme**: chi la fa deve misurare `number_plugins()` nel bundle, aggiungere `libgmsh` a mano, includere il VC++ redistributable su Windows e tenere il build in console per uvicorn. Da riconsiderare a pipeline stabile, non prima della consegna.
3. **Firma**: senza budget, la via dignitosa e gratuita è (i) istruzioni chiare per Open Anyway / Run anyway, (ii) chiedere all'ateneo un Developer ID di ente per la notarizzazione macOS, (iii) valutare SignPath per Windows se il progetto resta pubblico e attivo dopo la tesi. Azure Artifact Signing è chiuso agli individui in Italia; EV non compra più nulla.
4. **Scartare** Nuitka (costo senza beneficio qui), Briefcase (99 USD obbligatori su macOS per un'app console + nessun precedente con questa pila), constructor (doppia catena di dipendenze), PyOxidizer/pex/shiv (morto / non Windows / richiede Python).
5. **Prerequisito comune a tutte le vie**, fuori da questa ricerca ma da mettere nel piano: i percorsi `runs/`, `experiments/`, `.cache/viewport` relativi alla cwd (`MeshRec.command:10-14`) vanno spostati in una cartella dati utente, altrimenti né un `.app` né un onedir sotto `Program Files` funzionano.

---

## 8. Caveat

- **Nessun build di prova** eseguito (il brief vieta il PoC): tempi di avvio e dimensioni delle vie B/C sono `[INF]` da pesi misurati, non `[M]`.
- **Staleness**: Open3D #6624 (2024) e PyMeshLab #114 (2021) sono le uniche segnalazioni trovate; nulla del 2025-2026 su PyInstaller + open3d/pymeshlab `[NON TROVATO]` — silenzio, non conferma. Nuitka #3780 è di febbraio 2026 e mostra che il terreno si muove.
- **Domini irraggiungibili in sessione**: `developer.apple.com/news` (annuncio Gatekeeper: citato via mjtsai.com), `learn.microsoft.com` (letti via mirror `raw.githubusercontent.com/MicrosoftDocs`), `gitlab.onelab.info` (issue gmsh #1355/#2750 dietro Anubis: non lette).
- **Azure Artifact Signing**: la pagina prezzi Azure non mostra cifre senza sessione (`$-`); i 9,99 USD vengono dalla tabella Microsoft nel doc `code-signing-options` e dal blog Melatonin. Idoneità individui verificata solo nel doc Microsoft (USA/Canada).
- **conda-forge gmsh/tetgen**: presenza vista solo nei risultati di ricerca, non salvata come fonte.
- Il thread parallelo sta scrivendo un'altra ricerca sull'app shell (pywebview/Tauri/Electron, `fonti/pywebview-*`, `tauri-*`, `briefcase-home`): non sovrapposta a questa, che copre la distribuzione del runtime Python, non la finestra.

---

## Riferimenti

Ogni voce: URL · tag · perché conta qui · cosa se ne prende. Copia in `fonti/<slug>.md` + `<slug>.provenance.json`.

### Freezing

- **URL** https://pyinstaller.org/en/stable/CHANGES.html · [V] `fonti/pyinstaller-changes.md`
  **perché conta qui** stato 2026 di PyInstaller (6.22.2, 17/08/2026; Python fino a 3.15; hook numpy/scipy aggiornati)
  **cosa se ne prende** PyInstaller vivo e compatibile col pin 3.12; scipy coperto da hook ufficiale
- **URL** https://pyinstaller.org/en/stable/usage.html · [V] `fonti/pyinstaller-usage.md`
  **perché conta qui** onefile vs onedir, `--collect-all`, `--add-binary`, `--target-arch`, `--windowed` → `.app`
  **cosa se ne prende** onedir obbligatorio (onefile «require unpacking on each run»); sintassi delle quattro correzioni manuali
- **URL** https://pyinstaller.org/en/stable/feature-notes.html · [V] `fonti/pyinstaller-feature-notes.md`
  **perché conta qui** firma ad-hoc automatica, `--codesign-identity` + hardened runtime, `--deep` sui bundle, self-signed che rompe i dylib
  **cosa se ne prende** senza Developer ID si resta ad-hoc; firma da fare al build, mai dopo
- **URL** https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html · [V] `fonti/pyinstaller-common-issues.md`
  **perché conta qui** `multiprocessing.freeze_support()`, temp con symlink per onefile
  **cosa se ne prende** MeshRec non usa workers → non serve; conferma che onefile ha vincoli extra
- **URL** https://github.com/pyinstaller/pyinstaller/issues/7937 · [V] `fonti/pyinstaller-issue-7937-notarization.md`
  **perché conta qui** onefile ri-firmato con Developer ID + `-o runtime` fallisce «Error loading Python lib … code signature»
  **cosa se ne prende** onefile + notarizzazione è la combinazione più fragile; onedir + `--codesign-identity`
- **URL** https://github.com/pyinstaller/pyinstaller-hooks-contrib/tree/master/_pyinstaller_hooks_contrib/stdhooks · [V] `fonti/pyinstaller-hooks-contrib-stdhooks.md`
  **perché conta qui** inventario hook: c'è `hook-scipy.py`, non ci sono open3d/pymeshlab/gmsh/tetgen/uvicorn/fastapi
  **cosa se ne prende** le quattro native vanno a mano
- **URL** https://github.com/pyinstaller/pyinstaller-hooks-contrib/pull/611 · [V] `fonti/pyinstaller-hooks-contrib-pr-611-pydantic.md`
  **perché conta qui** hook pydantic aggiornato per v2
  **cosa se ne prende** pydantic 2.13 coperto, non è un rischio
- **URL** https://github.com/isl-org/Open3D/issues/6624 · [V] `fonti/open3d-issue-6624-pyinstaller.md`
  **perché conta qui** exe PyInstaller con open3d: «DLL load failed while importing pybind» su PC senza runtime C++ (Windows, 2024)
  **cosa se ne prende** includere VC++ redistributable nell'installer Windows; testare il bundle su una macchina pulita
- **URL** https://github.com/cnr-isti-vclab/PyMeshLab/discussions/114 · [V] `fonti/pymeshlab-discussion-114-pyinstaller.md`
  **perché conta qui** pymeshlab freezato perde i plugin («Unknown format for load: ply»), diagnosi `number_plugins()`
  **cosa se ne prende** test di accettazione `number_plugins()` nel bundle; `PlugIns/` da preservare
- **URL** https://github.com/pyinstaller/pyinstaller/issues/7339 · [V] `fonti/pyinstaller-issue-7339-uvicorn.md`
  **perché conta qui** uvicorn in `--windowed`: `sys.stdout` None → «Unable to configure formatter 'default'»
  **cosa se ne prende** build console, o redirigere stdout/stderr prima di `uvicorn.run`
- **URL** https://github.com/Kludex/uvicorn/discussions/1820 · [V] `fonti/uvicorn-discussion-1820-pyinstaller.md`
  **perché conta qui** worker uvicorn che non partono in exe PyInstaller con `workers>1` e stringa di import
  **cosa se ne prende** MeshRec passa l'app come oggetto e senza workers: non si applica
- **URL** https://nuitka.net/changelog/Changelog.html · [V] `fonti/nuitka-changelog.md`
  **perché conta qui** Nuitka 4.2, Python 3.4–3.14, «Added support for newer scipy», nessuna menzione di pymeshlab/gmsh
  **cosa se ne prende** 3.12 ok; scipy rincorso di release in release
- **URL** https://nuitka.net/posts/nuitka-release-24.html · [V] `fonti/nuitka-release-2-4.md`
  **perché conta qui** «Standalone: Added support for open3d package»
  **cosa se ne prende** open3d ha una config Nuitka; pymeshlab e gmsh no
- **URL** https://nuitka.net/user-documentation/user-manual.html · [V] `fonti/nuitka-user-manual.md`
  **perché conta qui** `--standalone`/`--onefile`/`--macos-create-app-bundle`, `--include-data-files`, compilatore C11 richiesto
  **cosa se ne prende** toolchain e forma delle inclusioni manuali; firma macOS non documentata
- **URL** https://github.com/Nuitka/Nuitka/issues/2649 · [V] `fonti/nuitka-issue-2649-gmsh.md`
  **perché conta qui** «could not find Gmsh shared library libgmsh.so.4.12» in standalone; fix = copiare la lib nella dist
  **cosa se ne prende** libgmsh va aggiunta a mano in ogni freezer
- **URL** https://github.com/Nuitka/Nuitka/issues/3780 · [V] `fonti/nuitka-issue-3780-scipy.md`
  **perché conta qui** scipy 1.17 + Nuitka 4.0.1 + Python 3.12: `No module named 'scipy._cyutility'` (feb 2026)
  **cosa se ne prende** ogni bump scipy può rompere lo standalone Nuitka
- **URL** https://github.com/Nuitka/Nuitka/issues/599 · [V] `fonti/nuitka-issue-599-compile-time.md`
  **perché conta qui** compile time e dist grandi con numpy/pandas/matplotlib (storica)
  **cosa se ne prende** tendenza: Nuitka costa tempo di build sulle pile scientifiche
- **URL** https://briefcase.beeware.org/en/stable/reference/platforms/macOS/ · [V] `fonti/briefcase-macos.md`
  **perché conta qui** firma+notarizzazione di default, ad-hoc solo sul PC dello sviluppatore, `.pkg` obbligatorio per console app, Python ≥ 3.11, wheel non fondibili
  **cosa se ne prende** Briefcase implica Apple Developer Program per MeshRec
- **URL** https://briefcase.beeware.org/en/stable/reference/platforms/windows/ · [V] `fonti/briefcase-windows.md`
  **perché conta qui** MSI via WiX o zip, Python embeddable, firma con certificato o nessuna
  **cosa se ne prende** su Windows Briefcase non aggiunge nulla a Inno Setup
- **URL** https://napari.org/dev/naps/2-conda-based-packaging.html · [V] `fonti/napari-nap-2-conda.md`
  **perché conta qui** progetto scientifico con pila nativa che ha lasciato Briefcase per constructor: ABI PyPI, metadati, «PyPI non distribuisce Python»
  **cosa se ne prende** precedente contro Briefcase su pile native pesanti; precedente a favore di constructor per chi vive in conda
- **URL** https://py2app.readthedocs.io/en/latest/changelog.html · [V] `fonti/py2app-changelog.md`
  **perché conta qui** 0.29.10, Python 3.12 dalla 0.28.7, no editable installs
  **cosa se ne prende** vivo e compatibile, ma solo macOS

### Vie senza freezing

- **URL** https://docs.astral.sh/uv/concepts/python-versions/ · [V] `fonti/uv-python-versions.md`
  **perché conta qui** uv usa python-build-standalone; `UV_PYTHON_INSTALL_DIR`/`--install-dir`; `python-downloads = never`
  **cosa se ne prende** Python impacchettabile in una cartella scelta, download disattivabile
- **URL** https://docs.astral.sh/uv/concepts/projects/sync/ · [V] `fonti/uv-projects-sync.md`
  **perché conta qui** `--frozen` usa il lock senza verificarlo, `--no-dev`
  **cosa se ne prende** comando di primo avvio: `uv sync --frozen --no-dev`
- **URL** https://docs.astral.sh/uv/reference/environment/ · [V] `fonti/uv-environment-vars.md`
  **perché conta qui** `UV_OFFLINE`, `UV_CACHE_DIR`, `UV_PROJECT_ENVIRONMENT`, `UV_PYTHON_INSTALL_MIRROR` con `file://`
  **cosa se ne prende** primo avvio offline con cache pre-riempita e mirror locale di Python
- **URL** https://github.com/davnn/uv-pack · [V] `fonti/uv-pack-readme.md`
  **perché conta qui** implementazione esistente della via A (export lock, download wheel, python-build-standalone, script unpack); stessa piattaforma soltanto
  **cosa se ne prende** prova che la via A è ~uno script; da imitare, non da dipendere
- **URL** https://ofek.dev/pyapp/latest/ · [V] `fonti/pyapp-docs.md`
  **perché conta qui** binario Rust che installa Python + progetto al primo avvio; `PYAPP_DISTRIBUTION_EMBED`, `PYAPP_UV_ENABLED`; `hatch build -t binary`
  **cosa se ne prende** installer sottile, ma primo avvio online
- **URL** https://conda.github.io/constructor/construct-yaml/ · [V] `fonti/constructor-construct-yaml.md`
  **perché conta qui** solo pacchetti conda in `specs`, pip via `post_install`; `signing_identity_name`, `notarization_identity_name`, `windows_signing_tool`
  **cosa se ne prende** seconda catena di dipendenze; firma integrata
- **URL** https://anaconda.org/conda-forge/pymeshlab · [V] `fonti/conda-forge-pymeshlab.md`
  **perché conta qui** pymeshlab 2025.7.post1 su conda-forge, win-64 e osx-arm64
  **cosa se ne prende** via constructor possibile per pymeshlab
- **URL** https://anaconda.org/conda-forge/open3d · [V] `fonti/conda-forge-open3d.md`
  **perché conta qui** open3d 0.19.0 su conda-forge, win-64 e osx-arm64
  **cosa se ne prende** via constructor possibile per open3d
- **URL** https://github.com/indygreg/PyOxidizer/issues/741 · [V] `fonti/pyoxidizer-issue-741-status.md`
  **perché conta qui** «the future of PyOxidizer is uncertain, possibly dead» (17/03/2024)
  **cosa se ne prende** escluso
- **URL** https://docs.pex-tool.org/scie.html · [V] `fonti/pex-scie.md`
  **perché conta qui** eseguibile nativo con python-build-standalone (`--scie eager|lazy`); esempi solo Linux
  **cosa se ne prende** non documentato per Windows/macOS arm64: escluso
- **URL** https://shiv.readthedocs.io/en/latest/ · [V] `fonti/shiv-docs.md`
  **perché conta qui** estrae in `~/.shiv` per i `.so`; richiede Python sul target
  **cosa se ne prende** non distribuisce Python: escluso

### Installer, firma, Gatekeeper, SmartScreen

- **URL** https://jrsoftware.org/isinfo.php · [V] `fonti/inno-setup-info.md`
  **perché conta qui** setup.exe unico, firma supportata, Windows 7–11, gratuito per uso non commerciale
  **cosa se ne prende** confezionatore Windows per onedir/portabile; può lanciare vcredist
- **URL** https://github.com/create-dmg/create-dmg · [V] `fonti/create-dmg-readme.md`
  **perché conta qui** dmg con `--app-drop-link`, `--codesign`, `--notarize`; mantenuto
  **cosa se ne prende** confezionatore macOS
- **URL** https://raw.githubusercontent.com/MicrosoftDocs/windows-dev-docs/docs/hub/apps/package-and-deploy/smartscreen-reputation.md · [V] `fonti/ms-smartscreen-reputation.md`
  **perché conta qui** reputazione publisher + hash; avviso anche su binario firmato finché non accumula storia
  **cosa se ne prende** la firma non cancella l'avviso al primo rilascio; serve continuità di identità
- **URL** https://raw.githubusercontent.com/MicrosoftDocs/windows-dev-docs/docs/hub/apps/package-and-deploy/code-signing-options.md · [V] `fonti/ms-code-signing-options.md`
  **perché conta qui** tabella Microsoft: Artifact Signing ~9,99 $/mese (individui solo USA/Canada), OV 150–300 $, EV 400+ $ senza più bypass, self-signed blocca
  **cosa se ne prende** per un individuo in Italia restano OV a pagamento, SignPath gratis, o nessuna firma
- **URL** https://melatonin.dev/blog/code-signing-on-windows-with-azure-trusted-signing/ · [V] `fonti/melatonin-azure-trusted-signing.md`
  **perché conta qui** 9,99 $/mese confermato, autonomi ammessi da aprile 2026, action GitHub con sei segreti, reputazione legata all'identità
  **cosa se ne prende** procedura CI se un'organizzazione UE (ateneo) apre l'account
- **URL** https://signpath.org/terms.html · [V] `fonti/signpath-terms.md`
  **perché conta qui** firma gratuita OSS: licenza OSI, sviluppo attivo, release esistenti, MFA, ruoli, policy pubblicata; certificato a nome della Foundation
  **cosa se ne prende** MeshRec (MIT, pubblico) è idoneo sulla carta; costo = burocrazia
- **URL** https://developer.apple.com/programs/whats-included/ · [V] `fonti/apple-developer-program-whats-included.md`
  **perché conta qui** 99 USD/anno, certificati e Developer ID inclusi
  **cosa se ne prende** prezzo della notarizzazione
- **URL** https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac · [V] `fonti/apple-support-open-unknown-developer.md`
  **perché conta qui** procedura ufficiale «Privacy & Security › Open Anyway» (macOS 26) e avviso Apple sul malware
  **cosa se ne prende** testo per il README del tesista; cosa vede l'utente senza firma
- **URL** https://mjtsai.com/blog/2024/07/05/sequoia-removes-gatekeeper-contextual-menu-override/ · [V] `fonti/mjtsai-sequoia-gatekeeper.md`
  **perché conta qui** cita la developer news Apple: da Sequoia niente Control-click per aggirare Gatekeeper
  **cosa se ne prende** il vecchio trucco «tasto destro › Apri» non vale più; solo Impostazioni

### CI e canale di consegna

- **URL** https://docs.github.com/en/actions/reference/runners/github-hosted-runners · [V] `fonti/github-hosted-runners.md`
  **perché conta qui** `macos-latest/14/15/26` = arm64 M1; `windows-latest`; repo pubblici gratuiti e illimitati
  **cosa se ne prende** matrix `{windows-latest, macos-latest}` a costo zero per il repo pubblico
- **URL** https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions · [V] `fonti/github-actions-billing.md`
  **perché conta qui** 2 000 min/mese Free su privati; macOS 0,062 $/min
  **cosa se ne prende** se il repo diventasse privato, i job macOS pesano 10× Linux
- **URL** https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases · [V] `fonti/github-about-releases.md`
  **perché conta qui** asset < 2 GiB, nessun limite totale né di banda
  **cosa se ne prende** un artefatto da ~300 MB per piattaforma è consegnabile via Releases
- **URL** https://raw.githubusercontent.com/softprops/action-gh-release/master/README.md · [V] `fonti/action-gh-release-readme.md`
  **perché conta qui** v3 (Node 24), `on: push: tags`, `permissions: contents: write`, `files:` glob
  **cosa se ne prende** step di upload del workflow

### Pesi dei wheel (per la stima dell'artefatto)

- **URL** https://pypi.org/project/open3d/0.19.0/ · [V] `fonti/pypi-open3d-0-19-0.md`
  **perché conta qui** cp312 win_amd64 69,2 MB, macosx universal2 103,2 MB
  **cosa se ne prende** open3d è metà dell'artefatto compresso
- **URL** https://pypi.org/project/pymeshlab/ · [V] `fonti/pypi-pymeshlab.md`
  **perché conta qui** 2025.7.post1 cp312 win_amd64 55,2 MB, macosx_11_0_arm64 65,0 MB
  **cosa se ne prende** secondo peso
- **URL** https://pypi.org/pypi/gmsh/4.15.2/json · [V] `fonti/pypi-gmsh-4-15-2-json.md`
  **perché conta qui** wheel `py2.py3-none` win_amd64 42,2 MB, macosx_12_0_arm64 36,4 MB
  **cosa se ne prende** terzo peso; wheel per-piattaforma pur senza tag cp
- **URL** https://pypi.org/project/tetgen/ · [V] `fonti/pypi-tetgen.md`
  **perché conta qui** 0.8.4 cp312-abi3 win/macos arm64 ~0,3 MB
  **cosa se ne prende** trascurabile

### Misure locali `[M]` (non in `fonti/`, riproducibili)

- `du -sh .venv .venv/lib/python3.12/site-packages/{open3d,pymeshlab,scipy,numpy} .venv/lib/libgmsh.4.15.dylib` — cwd `meshrec/`, HEAD b711053
- `grep -n libpath .venv/lib/python3.12/site-packages/gmsh.py` → righe 41-80, ordine di ricerca della libreria
- `ls .venv/lib/python3.12/site-packages/pymeshlab/{Frameworks,PlugIns}` → Qt frameworks; 66 plugin
- `gh repo view maeurong/meshrec --json isPrivate,visibility` → PUBLIC; `head -1 LICENSE` → MIT
- `du -shL ~/.local/share/uv/python/cpython-3.12-macos-aarch64-none` → 57M; `uv --version` → 0.12.9
