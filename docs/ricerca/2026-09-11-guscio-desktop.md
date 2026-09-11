# Guscio desktop attorno a MeshRec (FastAPI + UI statica three.js)

**Domanda.** MeshRec deve «sembrare e usarsi come un programma qualsiasi»: finestra propria con titolo e icona, avvio a doppio clic, chiusura finestra = chiusura server. Oggi: terminale + scheda browser. Quale guscio, con l'UI attuale invariata?

**Stato.** Completa. Rete caduta una volta a metà (ENOTFOUND), ripresa; nessuna sezione lasciata a metà. Fonte non raggiungibile in sessione: `developer.apple.com` (bloccato) — la struttura minima di un bundle `.app` resta `[INF]`.

**Data.** 2026-09-11. Repo `/Users/mario/GitHub/Tesi`, `meshrec/` HEAD `b711053` (main).

Tag: `[V]` fonte primaria letta · `[M]` misurato in sessione con comando · `[INF]` inferenza · `[NON TROVATO]`.

---

## 0. Premesse del brief, verificate sul codice

Tutto letto in sessione, percorsi relativi a `meshrec/`.

| Premessa del brief | Esito | Dove |
|---|---|---|
| `requires-python >=3.12,<3.13`, deps pesanti, script `meshrec = "meshrec.cli:main"` | confermata | `pyproject.toml:5-25` |
| `serve`: bind di prova, `threading.Timer(1.0, webbrowser.open)`, `uvicorn.run(create_app(...), host, port, log_level="warning")` nel thread principale | confermata | `src/meshrec/cli.py:222-272` |
| `ServerConfig`: `host="127.0.0.1"`, `port=8765`, `open_browser=True` | confermata | `src/meshrec/core/config.py:1028-1033` |
| Launcher `.bat`/`.command`: `cd` nella propria cartella, richiedono `uv`, `uv run meshrec serve` | confermata | `MeshRec.bat:10-21`, `MeshRec.command:16-33` |
| UI usa `<input type="file">` | **falsa, marginale.** Il selettore è aperto dal **server**, in un sottoprocesso `tkinter.filedialog` via `POST /api/sfoglia` (timeout 2 min). Il commento dice perché: `<input type=file>` nasconde il percorso reale (`C:\fakepath`) e al server serve il percorso. | `src/meshrec/ui/app.js:282-297`, `src/meshrec/app/server.py:417-460, 992-1043` |
| Salvataggio PNG dal browser | confermata: `renderer.toDataURL("image/png")` + `<a download>` cliccato via JS (data URL, non blob), `preserveDrawingBuffer: true` | `src/meshrec/ui/viewport.js:297, 953`, `src/meshrec/ui/app.js:2045, 2132-2136`, `index.html:262-277` |
| `vendor/three.module.js` | marginale: sono `three.core.min.js` + `three.module.min.js`, three **r180**, impronte in `tests/test_server.py` | `src/meshrec/ui/vendor/README.md` |
| — (non nel brief) | la UI tiene un canale SSE aperto: `new EventSource("/api/events")` — leva per «server sa se la finestra è viva» | `src/meshrec/ui/app.js:816-820` |
| — | nessun uso di `localStorage`/`sessionStorage`/`indexedDB` nella UI (grep: 0 occorrenze in `app.js`, `viewport.js`, `modello.js`) → il `private_mode` di default dei webview non perde nulla | `[M]` grep |
| `.venv` 965 MB | confermata | `[M] du -sh meshrec/.venv` |
| Utente su Windows 11 «operando da WSL mentre il programma resta su Windows» | il programma gira su Windows nativo, non in WSL: il guscio deve funzionare su Windows 11 e macOS arm64; WSL fuori scopo | `PRODUCT.md:16-18` |

Effetto della premessa falsa sul compito: **favorevole** a un guscio webview. Il dialog file non dipende dal browser, quindi nessun guscio deve saperlo fare; resta solo da verificare che il sottoprocesso Tk salga sopra la finestra del guscio (`radice.attributes("-topmost", True)` in `server.py:437-439` lo fa già per il browser).

Cosa deve sopravvivere invariato, in ordine di rischio: (1) WebGL2 + moduli ES di three r180; (2) `<a download>` con data URL → file PNG sul disco; (3) `EventSource` SSE; (4) `fetch` JSON/binario verso `127.0.0.1:8765`; (5) dialog Tk in sottoprocesso.

---

## 1. pywebview (Python; WebView2 su Windows, WKWebView su macOS)

### Stato 2026
- Ultima release **6.2.1 del 2026-04-15**; 6.2 del 2026-04-13; 6.1 del 2025-10-21; 6.0 del 2025-08-08. Repo: 6.012 stelle, 14 issue aperte, ultimo push **2026-09-11**, licenza BSD-3-Clause. `[M] gh api repos/r0x0r/pywebview/releases`, `gh api repos/r0x0r/pywebview`.
- PyPI: `pywebview 6.2.1`, `requires_python >=3.8`. Dipendenze per piattaforma: Windows `pythonnet`; macOS `pyobjc-core`, `-Cocoa`, `-Quartz`, `-WebKit`, `-security`, `-UniformTypeIdentifiers` (tutti `>=9.0`); sempre `bottle`, `proxy_tools`, `typing_extensions`. `[M] curl https://pypi.org/pypi/pywebview/json`.
- `pythonnet 3.1.0`, `requires_python >=3.10,<3.15`, classificatori fino a 3.14 → compatibile con il pin `3.12` di MeshRec. `[M] curl https://pypi.org/pypi/pythonnet/json`.
- Peso su macOS arm64: **33 MB** di `site-packages` per `pywebview` + `pyobjc` (5 pacchetti) in un venv pulito. `[M] uv venv -p 3.12 …; uv pip install pywebview; du -sh site-packages` — contro i 965 MB del `.venv` attuale, rumore.

### Motore di rendering
- Windows: **WebView2 (Edge Chromium)** di default; se il runtime manca → fallback **MSHTML (IE11)**, «the only renderer that is guaranteed to be available on any system». `[V]` guida web engine.
- Microsoft: «The Evergreen WebView2 Runtime will be included as part of the Windows 11 operating system»; per Windows 10 «the vast majority» lo ha, «a small number» no; rilevabile dalla chiave `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` valore `pv`; bootstrapper ~2 MB. `[V]` doc distribuzione WebView2.
- macOS: **WKWebView** «bundled with OS». `[V]` guida web engine.
- **Gotcha decisivo su Windows:** il fallback MSHTML è silenzioso e IE11 non ha né WebGL2 né `import` ES → viewport vuoto senza errore chiaro. Va rilevato prima di aprire la finestra (chiave di registro qui sopra, oppure `gui='edgechromium'` forzato che fallisce rumorosamente). `[INF]` sul comportamento di MSHTML con three r180, `[V]` sul fallback.

### WebGL / three.js
- Issue tracker pywebview, ricerca «webgl»: 5 risultati, nessuno su un malfunzionamento WebGL (uno è «webgal», un motore di visual novel). Ricerca «three.js OR threejs OR hardware acceleration»: 6 risultati, nessuno pertinente. `[M] gh api search/issues -f q='repo:r0x0r/pywebview webgl'`. → **[NON TROVATO]** un bug WebGL noto su WebView2/WKWebView in pywebview.
- Inferenza: WebView2 = Chromium stabile, WKWebView = motore di Safari; entrambi hanno WebGL2 e moduli ES; three r180 vendorizzato gira già su Chrome (Mario) e Safari è il target ufficiale di three. `[INF]`. Da verificare a mano con `preserveDrawingBuffer` + `toDataURL` (il combinato che serve al PNG).

### Download del PNG (`<a download>` + data URL)
- `webview.settings['ALLOW_DOWNLOADS']` è **`False` di default** («Allow file downloads. Disabled by default»); va messo a `True` **prima** di `webview.start()`. `[V]` API + esempio Downloads.
- Su macOS l'attributo `download` non forzava il download: sistemato dalla PR **#1552** «Add support for the download attribute on links for Cocoa/MacOS platform», merged **2024-12-27** («respects the suggested filename»). `[V]` PR. Quindi presente da 5.4 (2025-01-27) in poi `[INF]` sull'attribuzione alla release.
- **[NON TROVATO]**: dove finisce il file (cartella Download? dialog «salva con nome»?) e se il data URL da 1-5 MB del PNG passa come un URL http. La doc non lo dice. Prova manuale obbligatoria su entrambe le piattaforme prima di decidere.

### Icona e titolo
- `webview.create_window(title, url=…, width=800, height=600, …)`: titolo = primo argomento. `[V]` API.
- `webview.start(…, icon=None)`: «Supported formats are `.ico` on Windows and `.icns` on macOS. … Generally icon should be specified during bundling». Supporto Cocoa+Winforms arrivato in **6.2**. `[V]` API + changelog.
- Limite: l'icona di `start(icon=)` è quella della **finestra**. Nel Dock di macOS un processo Python lanciato da `.command` compare come «Python» (o «Terminal» resta aperto) finché non sta dentro un bundle `.app` con `CFBundleIconFile`; su Windows la barra applicazioni mostra l'icona dell'eseguibile (`python.exe`) salvo collegamento `.lnk` con icona propria. `[INF]` — la doc dice solo «during bundling».

### Ciclo di vita con `uvicorn.run` già presente in `cli.py`
- `webview.start()` «starts a GUI loop and blocks further code from execution until the last window is destroyed»; `start(func, args)` «will launch a separate thread». Su macOS Cocoa vuole il **thread principale** (stessa ragione per cui `server.py:423-426` mette Tk in sottoprocesso). `[V]` doc usage + API.
- Conseguenza: uvicorn va **fuori dal thread principale** (thread o sottoprocesso). Uvicorn lo regge: in `uvicorn/server.py:332-336` `capture_signals()` fa «Signals can only be listened to from the main thread. if threading.current_thread() is not threading.main_thread(): yield; return» → nessun `ValueError` da `signal.signal` in un thread. Fermata pulita: `server.should_exit = True` (`server.py:73, 244-249`). `[V]` sorgente uvicorn (0.52.4, 2026-08-19 `[M]`).
- Riferimento implementativo reale: **NiceGUI** fa l'inverso — uvicorn nel processo principale, pywebview in `multiprocessing` (`native.SPAWN_CONTEXT.Process(target=_open_window, …, daemon=True)`, `native_mode.py:205`), aspetta la porta con `while not helpers.is_port_open(host, port): time.sleep(0.1)` (`:46`), aggancia `window.events.closed += closed.set` (`:77`) e un thread di guardia chiama `core.stop_and_exit()` quando il processo finestra muore (`:188`). `[V]` sorgente.
- Eventi: `window.events.closing` («If event handler returns False, the close operation will be cancelled») e `closed`. `[V]` API. Per MeshRec: `closed` → `server.should_exit = True`; `closing` potrebbe chiedere conferma se una corsa è in esecuzione (il `Worker` in `app/worker.py`), ma è decisione di prodotto, non di guscio.
- Forma minima in `cli.py:222-272` (descrizione, non implementazione): tenere il bind di prova; sostituire `threading.Timer(webbrowser.open)` + `uvicorn.run` con `server = uvicorn.Server(uvicorn.Config(create_app(cfg), host, port, log_level="warning"))` in un `threading.Thread(daemon=True)`, poi `webview.create_window("MeshRec", indirizzo)`, `webview.start(icon=…)`, e al ritorno `server.should_exit = True`. `--no-browser` resta; un `--browser` (o fallback automatico se `import webview` fallisce) mantiene la via attuale. `[INF]` — pattern derivato da doc pywebview + sorgente uvicorn.

### Freezing (fase 2, non ora)
- macOS: py2app; Windows/Linux: PyInstaller; Nuitka supportato. WebView2 impacchettabile via `WEBVIEW2_RUNTIME_PATH` (6.1). `[V]` guida freezing + changelog. Con open3d/gmsh/pymeshlab nel venv un freeze è un progetto a sé: **non serve** per l'obiettivo del brief (icona + finestra), serve solo se un giorno si vuole un installer senza `uv`.

### Gotcha Windows 11 + macOS arm64
- Windows: `MeshRec.bat` apre comunque una finestra `cmd` accanto alla finestra webview; per nasconderla serve `pythonw.exe` del venv o un `.vbs`/`.lnk` minimizzato — `uv run` non ha un flag «senza console». `[INF]`.
- macOS: 6.2 «Fix Cocoa use-after-free crash on ARM64» → prima di 6.2 (aprile 2026) c'era un crash arm64: **pin `pywebview>=6.2`**. `[V]` changelog.
- macOS: `SHOW_DEFAULT_MENUS: True` mette la barra menu standard (Edit/Window); il nome nel menu sarà «Python» finché non c'è un bundle. `[V]` sul setting, `[INF]` sul nome.
- Entrambe: `private_mode=True` di default → cookie/storage azzerati a ogni avvio; MeshRec non usa storage (§0) → indifferente. `[V]` API + `[M]` grep.

---

## 2. Chromium/Edge in modalità `--app=URL`

### Cosa fa e da dove viene
- Switch `--app`: «Specifies that the associated value should be launched in "application" mode», definito in `chrome/common/chrome_switches.h:89` (`kApp`). `--user-data-dir`: «Specifies the user data directory, which is where the browser will look for all of its state». `--window-size=w,h`. `--no-first-run`: «Skip First Run tasks as well as not showing additional dialogs, prompts or bubbles». Elenco derivato dal sorgente Chromium «as of September 11, 2026». `[V]` peter.sh (derivato dal sorgente; `source.chromium.org` non raggiunto in sessione).
- Edge è Chromium: stessi switch (`msedge.exe --app=…`). Nessuna doc Microsoft dedicata trovata, solo Q&A e blog → `[INF]` sul comportamento identico, `[NON TROVATO]` una pagina ufficiale Microsoft su `--app`.

### Come si rileva il browser
- Python `webbrowser.open(url, new=0, autoraise=True)` **non passa argomenti** al browser: solo `%s` nella variabile `BROWSER`. `[V]` doc Python. Quindi `--app` richiede `subprocess.Popen` sull'eseguibile trovato a mano.
- Windows: chiave **App Paths** — `HKLM` o `HKCU` `\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\<file.exe>`, valore `(Default)` = «the fully qualified path to the application». `msedge.exe` e `chrome.exe` si registrano lì (`winreg` stdlib). `[V]` doc Microsoft sulla chiave; `[INF]` che Edge/Chrome la popolino (è la prassi, non verificata su una macchina Windows in sessione).
- macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` oppure `open -na "Google Chrome" --args --app=…`. Sulla macchina di Mario c'è Chrome (`[M] ls /Applications`), non Edge.
- Windows 11 ha Edge preinstallato → zero dipendenze nuove sulla piattaforma primaria. `[INF]` (fatto notorio, non documentato qui).

### Limiti, in ordine di gravità
1. **Chiusura finestra ≠ fine processo.** Chrome è un processo singolo per profilo: se Chrome è già aperto, `Popen` ritorna subito perché la richiesta è inoltrata all'istanza viva → `wait()` non dice nulla. Con `--user-data-dir=<cartella dedicata>` (es. `.cache/guscio`) si ottiene un processo separato, `Popen.wait()` ritorna alla chiusura della finestra, e il server si può fermare. `[INF]` — dal semantico documentato di `--user-data-dir` («all of its state») + comportamento noto del singleton, non da una pagina primaria. Rete di sicurezza indipendente dal browser: il canale SSE `/api/events` (`app.js:816`): quando il server non ha più client SSE per N secondi, esce. Funziona anche con la scheda browser di oggi. `[INF]`.
2. **Icona.** La finestra ha l'icona di Chrome/Edge nel Dock e nella barra applicazioni; il favicon compare solo nella barra del titolo. Con profilo dedicato il gruppo in taskbar è separato ma l'icona resta quella del browser. `[INF]`.
3. **Rumore del browser.** Prima esecuzione con profilo nuovo: bolle «imposta come predefinito», «ripristina pagine» dopo chiusura brusca, aggiornamenti; `--no-first-run` toglie parte, non tutto. `[V]` sul flag, `[INF]` sul resto.
4. Il profilo dedicato è una cartella nuova da tenere in `.gitignore` (già c'è `.cache/`).

### Cosa funziona senza toccare nulla
WebGL2, `<a download>` (barra download di Chrome, file in `Download`), SSE, dialog Tk in sottoprocesso: è lo stesso Chrome di oggi. Costo di adozione: **~30 righe in `cli.py`**, zero dipendenze. Aspetto: «finestra senza barra», non «programma».

---

## 3. PWA installabile (manifest + «Installa app»)

### Cosa serve davvero
- Contesto sicuro: «`localhost` or `127.0.0.1` (with or without a port number)» valgono come sicuri per l'installazione. `[V]` MDN.
- Manifest (Chromium): `name` o `short_name`; `icons` con **192 e 512 px**; `start_url`; `display` (`standalone`) e/o `display_override`; `prefer_related_applications` assente o `false`. `[V]` MDN + web.dev.
- Service worker: «Service workers are NOT required for installability». `[V]` MDN. Chrome: requisito del `fetch()` handler tolto in **108 mobile / 112 desktop**; per chi non ha una pagina offline propria «we launched a default custom page». `[V]` blog Chrome. web.dev aggiunge euristiche d'ingaggio («at least one click/tap and 30 seconds viewing time») e HTTPS. `[V]`.
- In `index.html`: `<link rel="manifest" href="/manifest.webmanifest">` + due PNG serviti da FastAPI. Dieci righe. `[INF]` sulla quantità.

### Cosa succede a server spento
L'icona installata lancia una finestra Chrome standalone che tenta `http://127.0.0.1:8765/`: server spento → pagina di errore di Chrome (o la «default custom page» offline) dentro una finestra con l'icona di MeshRec. **La PWA non può avviare il server**: il doppio clic sull'icona non fa partire Python. `[V]` sul meccanismo, `[INF]` sull'esperienza.

### Via seria o trucco
Trucco elegante, non una via. Dà l'icona migliore fra le opzioni browser (Dock/Start con l'icona di MeshRec, finestra standalone, gruppo taskbar proprio) ma **spezza la catena d'avvio in due gesti**: `.bat/.command` per il server, poi l'icona PWA. L'ordine inverso mostra un errore. Possibile complemento di §2 (un manifest costa poco e migliora il titolo/icona anche in `--app`), non un sostituto di un guscio. Dipende inoltre dal fatto che l'utente accetti «Installa» in Chrome/Edge: un passo in più da spiegare ai tesisti successivi.

---

## 4. Tauri 2 con sidecar Python, ed Electron

### Tauri 2
- Ultima release `tauri-v2.11.5` del **2026-07-01**. `[M] gh api repos/tauri-apps/tauri/releases`.
- Prerequisiti: macOS «Command Line Tools» (`xcode-select --install`) + Rust; Windows «Microsoft C++ Build Tools» + Rust; «WebView 2 is already installed on Windows 10 (from version 1803 onward)»; Node «Only if you intend to use a JavaScript frontend framework». `[V]` prerequisites. Motore: WebView2 / WKWebView, gli stessi di pywebview.
- Sidecar: `bundle.externalBin` in `tauri.conf.json`; il binario deve chiamarsi `<nome>-<target-triple>` (`-aarch64-apple-darwin`, `-x86_64-pc-windows-msvc.exe`); permesso `shell:allow-execute` con `"sidecar": true`; spawn da Rust `app.shell().sidecar("…")` o da JS `Command.sidecar(...)`. La doc cita «Python CLI applications or API servers bundled using pyinstaller» come caso d'uso, senza dettagli. `[V]` doc sidecar.
- Uccidere il sidecar: **problema noto**. Esempio di riferimento (`dieharders/example-tauri-v2-python-server-sidecar`): «we cannot use process.kill() for one-file Python executables since Tauri only knows the pid of the PyInstaller bootloader process and not its' child process» → spegnimento via comando su stdin. `[V]` README. Discussione ufficiale #2759: «I and others have had trouble fully closing pyinstaller sidecars when closing the app», workaround «check if the parent process still exists, otherwise the python instance self-terminates». `[V]`.
- Costo reale per MeshRec: (a) toolchain Rust + Build Tools/CLT su ogni macchina che compila; (b) **PyInstaller di un venv da 965 MB** con open3d, gmsh, pymeshlab, tetgen — un binario per piattaforma, quindi una macchina Windows e una macOS arm64 per ogni release, più i falsi positivi antivirus tipici dei bootloader PyInstaller `[INF]`; (c) firma/notarizzazione per non avere l'avviso Gatekeeper `[INF]`; (d) un secondo repo di configurazione (Rust + `tauri.conf.json` + capabilities). Alternativa «Tauri come sola finestra» che lancia `uv run meshrec serve` invece del sidecar: toglie (b), tiene (a) e (d).
- Vantaggio vero: bundle nativo con icona, installer `.msi`/`.dmg`, nessun `uv` da installare per l'utente. Per «altri tesisti e laboratorio» (pochi, tecnici, con `uv` già richiesto dai launcher) il vantaggio non ripaga (a)-(d).

### Electron
- Ultima release `v44.3.0` del **2026-09-08**; zip prebuilt **123 MiB darwin-arm64, 150 MiB win32-x64**. `[M] gh api repos/electron/electron/releases/latest`.
- Distribuzione: binario Electron prebuilt + cartella `app` (o `app.asar`) in `resources/`; consigliato Electron Forge; Node richiesto per lo sviluppo. `[V]` doc distribution (`[INF]` su Node: la pagina quick-start non è stata raggiunta, ma Forge è un pacchetto npm).
- Stesso problema di sidecar di Tauri, più 120-150 MiB di Chromium duplicato accanto a un Chrome/Edge già presente. Nessun vantaggio rispetto a Tauri per questo caso; scartato.

---

## 5. Altre vie

### Neutralinojs
- `v6.9.0` del 2026-07-24, 8.632 stelle. `[M] gh api`. «doesn't bundle Chromium and uses the existing web browser library in the operating system (e.g., gtk-webkit2 on Linux)»; estendibile «with any programming language (via extensions IPC)». `[V]` docs.
- `url` nel `neutralino.config.json` «accepts both relative and absolute URLs» (es. `http://example.com`) → può puntare a `http://127.0.0.1:8765/`; `modes.window.title`, `modes.window.icon` (PNG). `[V]` config.
- **Gotcha:** «When Neutralino exits, it does not send kill signals to all extension instances» → il server Python deve accorgersi da sé della chiusura (WebSocket che cade, o SSE come in §2). `[V]` extensions overview.
- Giudizio: stessa architettura di pywebview (webview di sistema + processo Python separato) ma con un binario C++ per piattaforma da tenere nel repo, un file di config JS, e nessuna integrazione Python nativa. Meno lavoro di Tauri, più di pywebview, nessun vantaggio in cambio. `[INF]`.

### NiceGUI `native=True`
- Usa **pywebview** sotto: «Pick any parameter as it is defined by the internally used pywebview module for the `webview.create_window` and `webview.start` functions»; `app.native.window_args / start_args / settings`. `[V]` doc (pagina JS, catturato solo il sorgente `native_mode.py`).
- Incompatibile come framework: richiede riscrivere la UI in componenti NiceGUI. Utile solo come **implementazione di riferimento** del ciclo uvicorn + pywebview + chiusura (§1). `[V]` sorgente.

### Flet
Esclusa senza lettura: UI Flutter, non HTML — non può servire `index.html` + `app.js` invariati. `[NON TROVATO]` (non cercato oltre, incompatibile per definizione).

### Briefcase (BeeWare)
- «a tool for converting a Python project into a standalone native application»: macOS «standalone .app», Windows «MSI installer», Linux pacchetto nativo. `[V]` home. Se bundli un Python proprio e se accetta un progetto arbitrario (non Toga): `[NON TROVATO]` in sessione.
- Ruolo: fase 2 eventuale, per trasformare `pywebview + meshrec` in `.app`/`.msi` con icona senza Rust. Stesso scoglio del freeze delle dipendenze scientifiche.

### Launcher a `uv` con icona (senza guscio nuovo)
- macOS: un bundle minimo `MeshRec.app/Contents/{Info.plist, MacOS/MeshRec, Resources/MeshRec.icns}` con `CFBundleExecutable` = script shell (`uv run meshrec serve`) e `CFBundleIconFile`: Finder mostra l'icona, il Dock mostra il bundle, nessun Terminale aperto. `[INF]` — `developer.apple.com` bloccato in sessione; corroborato solo da guide di terzi (Tom Mewett, Joseph Long) non catturate.
- Windows: collegamento `.lnk` con icona propria verso `MeshRec.bat` (o `pythonw.exe -m meshrec serve` per non avere console). `[INF]`.
- Da soli non danno la finestra: servono **insieme** a §1 o §2. Sono il pezzo «icona nel Dock/Start» che nessun guscio Python risolve da solo senza freeze.

---

## 6. Tabella comparativa

| Via | Costo adozione (stima) | Dipendenze nuove | Aspetto «programma vero» | Chiusura finestra = stop server | Rischio principale |
|---|---|---|---|---|---|
| **1. pywebview** | ~60-80 righe in `cli.py` + `.icns/.ico` + prova PNG/WebGL su 2 OS | `pywebview>=6.2` (+ `pythonnet` / `pyobjc`, 33 MB su mac `[M]`) | finestra propria, titolo, icona finestra; Dock/taskbar propri solo con bundle/`.lnk` (§5) | sì, `events.closed` → `should_exit` `[V]` | fallback MSHTML silenzioso su Windows senza WebView2; download data URL non documentato `[NON TROVATO]` |
| **2. Chromium `--app`** | ~30 righe in `cli.py` (rileva exe, `Popen`, profilo dedicato) | nessuna (Edge su Win11, Chrome su mac) | finestra senza barra, ma icona di Chrome/Edge | sì con `--user-data-dir` dedicato (`Popen.wait`) `[INF]`; altrimenti solo via watchdog SSE | rumore di prima esecuzione; se manca il browser → oggi già stesso problema |
| **3. PWA** | manifest + 2 PNG (~10 righe) | nessuna | la migliore fra le vie browser (icona propria in Dock/Start) | **no**: non avvia il server; server spento = pagina d'errore | due gesti d'avvio; installazione manuale per ogni utente |
| **4a. Tauri 2** | giorni: Rust + PyInstaller di 965 MB × 2 OS + capabilities + firma | Rust, Build Tools/CLT, PyInstaller, `tauri-cli` | il migliore (bundle, installer) | sì ma con lavoro (pid del bootloader PyInstaller) `[V]` | costo di build/release sproporzionato per ≤10 utenti tecnici |
| **4b. Electron** | come Tauri + Node | Node, 123-150 MiB di Chromium `[M]` | come Tauri | come Tauri | nessun vantaggio su Tauri qui |
| **5. Neutralino** | binario per OS nel repo + config JS + rilevazione chiusura lato Python | binario Neutralino | finestra + icona PNG | **no** di suo (non uccide le estensioni) `[V]` | terzo runtime senza vantaggi su pywebview |
| **5. `.app` / `.lnk`** | un bundle e un collegamento, a mano | nessuna | risolve solo icona/Dock/Start | n/a | `[INF]` senza doc Apple letta in sessione |

---

## 7. Raccomandazione (argomentata; decide Mario)

**Raccomandazione: pywebview (§1) come guscio, con la via `--app` di Chromium (§2) come fallback automatico, e il bundle `.app` / collegamento `.lnk` (§5) per l'icona nel Dock/Start.** In quest'ordine:

1. **Prova di 20 minuti prima di ogni riga di codice:** in un venv con `pywebview>=6.2`, `webview.settings['ALLOW_DOWNLOADS']=True; webview.create_window("MeshRec", "http://127.0.0.1:8765/"); webview.start()` contro il server già acceso da terminale. Verificare su macOS arm64 e Windows 11: viewport three visibile, «Salva immagine» produce un PNG leggibile e dove, SSE che aggiorna, «Sfoglia» che porta il dialog Tk in primo piano. È il punto `[NON TROVATO]` più pesante (download data URL) e va chiuso con un fatto, non con questa ricerca.
2. Se la prova passa: `cli.py` come descritto in §1 (uvicorn in thread, `should_exit` alla chiusura, `--no-browser`/`--browser` conservati). Rilevare WebView2 da registro su Windows e, se manca, cadere su §2 o sul browser di oggi con un messaggio, mai su MSHTML.
3. Watchdog SSE (nessun client su `/api/events` per N secondi → uscita) come rete indipendente dal guscio: costa poco, protegge anche il caso `--app` e il caso «utente chiude la scheda».
4. Icona: `.icns`/`.ico` per la finestra ora; bundle `.app` e `.lnk` quando si vuole l'icona nel Dock/Start (verificare prima la doc Apple, non letta qui).

Perché non le altre: `--app` da solo lascia l'icona di Chrome e il rumore del browser — resta un ottimo **fallback** perché costa zero dipendenze; PWA non avvia il server, quindi non risponde al brief; Tauri/Electron chiedono una pipeline di build a due piattaforme per un pubblico di pochi tecnici che hanno già `uv`; Neutralino aggiunge un runtime senza dare nulla in più di pywebview.

Rischi residui della raccomandazione: manutenzione di pywebview è di un solo autore principale (ma attiva a settembre 2026 `[M]`); pythonnet su Windows tira .NET (Fallback a coreclr aggiunto in 6.2 `[V]`); nessuna prova fatta in sessione su Windows.

---

## 8. Riferimenti

Ogni voce: URL · tag · perché conta qui · cosa se ne prende. Copie in `docs/ricerca/fonti/<slug>.md` con sidecar `.provenance.json`.

- **URL** https://pywebview.flowrl.com/api/ · [V] · `fonti/pywebview-api.md`
  **perché conta qui** firma di `create_window`/`start`, settings, eventi, parametro `icon`
  **cosa se ne prende** `ALLOW_DOWNLOADS` False di default; `icon` `.ico`/`.icns` «during bundling»; `closing` cancellabile, `closed`; `start` blocca il thread principale
- **URL** https://pywebview.flowrl.com/changelog.html · [V] · `fonti/pywebview-changelog.md`
  **perché conta qui** date reali delle release e fix arm64
  **cosa se ne prende** 6.2 (13/04/2026) icona Cocoa+Winforms, fix use-after-free ARM64 → pin `>=6.2`; 6.1 `WEBVIEW2_RUNTIME_PATH`; 5.0 download «disabled by default»
- **URL** https://pywebview.flowrl.com/examples/downloads · [V] · `fonti/pywebview-downloads.md`
  **perché conta qui** unico esempio ufficiale di download
  **cosa se ne prende** il setting va impostato prima di `create_window`; la doc non dice dove finisce il file
- **URL** https://pywebview.flowrl.com/guide/web_engine · [V] · `fonti/pywebview-web-engine.md`
  **perché conta qui** motore per piattaforma e fallback
  **cosa se ne prende** WebView2 di default, MSHTML se manca il runtime («only renderer guaranteed»), WKWebView su macOS; `gui=`/`PYWEBVIEW_GUI` per forzare
- **URL** https://pywebview.flowrl.com/guide/installation.html · [V] · `fonti/pywebview-installation.md`
  **perché conta qui** dipendenze native per OS
  **cosa se ne prende** pythonnet (> .NET 4.0) + WebView2 Runtime su Windows; pyobjc su macOS
- **URL** https://pywebview.flowrl.com/guide/freezing.html · [V] · `fonti/pywebview-freezing.md`
  **perché conta qui** fase 2 (installer)
  **cosa se ne prende** py2app su macOS, PyInstaller su Windows, Nuitka; non necessario per il brief
- **URL** https://github.com/r0x0r/pywebview/pull/1552 · [V] · `fonti/pywebview-pr1552.md`
  **perché conta qui** `<a download>` su macOS è esattamente il meccanismo del PNG
  **cosa se ne prende** attributo `download` rispettato su Cocoa da merge 2024-12-27, con nome file suggerito
- **URL** https://github.com/encode/uvicorn/blob/master/uvicorn/server.py · [V] · `fonti/uvicorn-server-py.md`
  **perché conta qui** uvicorn deve girare fuori dal thread principale sotto pywebview
  **cosa se ne prende** `capture_signals` salta i segnali fuori dal main thread (righe 332-336); `should_exit` ferma il loop
- **URL** https://github.com/encode/uvicorn/blob/master/docs/deployment/index.md · [V] · `fonti/uvicorn-deployment.md`
  **perché conta qui** forma ufficiale del run programmatico
  **cosa se ne prende** `uvicorn.run(app, host, port)` accetta l'istanza; stesso set di opzioni della CLI
- **URL** https://github.com/zauberzeug/nicegui/blob/main/nicegui/native/native_mode.py · [V] · `fonti/nicegui-native-mode-py.md`
  **perché conta qui** implementazione in produzione di «uvicorn + pywebview + chiusura finestra»
  **cosa se ne prende** `Process(daemon=True)` per la finestra, attesa porta con `is_port_open`, `events.closed`, `stop_and_exit()` da thread di guardia
- **URL** https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable · [V] · `fonti/mdn-pwa-installable.md`
  **perché conta qui** requisiti reali per «Installa app»
  **cosa se ne prende** `localhost`/`127.0.0.1` valgono come sicuri; manifest con icone 192+512, `start_url`, `display`; service worker non richiesto
- **URL** https://web.dev/articles/install-criteria · [V] · `fonti/webdev-install-criteria.md`
  **perché conta qui** criteri Chrome
  **cosa se ne prende** euristiche di ingaggio (clic + 30 s), `prefer_related_applications` false
- **URL** https://developer.chrome.com/blog/update-install-criteria · [V] · `fonti/chrome-install-criteria-update.md`
  **perché conta qui** cosa succede offline senza service worker
  **cosa se ne prende** requisito `fetch()` tolto in 108/112; «default custom page» a server spento
- **URL** https://peter.sh/experiments/chromium-command-line-switches/ · [V] (elenco derivato dal sorgente Chromium, 2026-09-11) · `fonti/chromium-switches.md` (estratto)
  **perché conta qui** semantica ufficiale di `--app`, `--user-data-dir`, `--window-size`, `--no-first-run`
  **cosa se ne prende** «application mode»; profilo dedicato = «all of its state» separato
- **URL** https://learn.microsoft.com/en-us/windows/win32/shell/app-registration · [V] · `fonti/ms-app-registration.md`
  **perché conta qui** come trovare `msedge.exe`/`chrome.exe` senza PATH
  **cosa se ne prende** `App Paths\<exe>` `(Default)` = percorso completo, in HKLM o HKCU
- **URL** https://docs.python.org/3/library/webbrowser.html · [V] · `fonti/python-webbrowser.md`
  **perché conta qui** `cli.py:264` usa `webbrowser.open`
  **cosa se ne prende** non passa argomenti al browser → `--app` richiede `subprocess`
- **URL** https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution · [V] · `fonti/webview2-distribution.md`
  **perché conta qui** presenza di WebView2 su Windows 11 e come rilevarla
  **cosa se ne prende** Evergreen incluso in Windows 11; chiave `EdgeUpdate\Clients\{F3017226-…}` `pv`; bootstrapper ~2 MB; Fixed Version > 250 MB
- **URL** https://v2.tauri.app/develop/sidecar/ · [V] · `fonti/tauri-sidecar.md`
  **perché conta qui** meccanica del sidecar Python
  **cosa se ne prende** `externalBin` con suffisso target-triple; permesso `shell:allow-execute`; PyInstaller citato senza dettagli
- **URL** https://v2.tauri.app/start/prerequisites/ · [V] · `fonti/tauri-prerequisites.md`
  **perché conta qui** costo toolchain
  **cosa se ne prende** Rust + CLT/Build Tools; WebView2 già presente da Win10 1803; Node facoltativo
- **URL** https://github.com/tauri-apps/tauri/discussions/2759 · [V] · `fonti/tauri-discussion-2759.md`
  **perché conta qui** esperienza reale su Python come sidecar
  **cosa se ne prende** «trouble fully closing pyinstaller sidecars»; workaround controllo del pid padre
- **URL** https://github.com/dieharders/example-tauri-v2-python-server-sidecar · [V] · `fonti/tauri-python-sidecar-example.md`
  **perché conta qui** esempio FastAPI + Tauri 2 funzionante
  **cosa se ne prende** `process.kill()` inutilizzabile con PyInstaller one-file (pid del bootloader); spegnimento via stdin
- **URL** https://www.electronjs.org/docs/latest/tutorial/application-distribution · [V] · `fonti/electron-distribution.md`
  **perché conta qui** costo di distribuzione Electron
  **cosa se ne prende** prebuilt + cartella `app`/`app.asar`; Electron Forge
- **URL** https://neutralino.js.org/docs/ · [V] · `fonti/neutralino-docs.md`
  **perché conta qui** cos'è e su cosa gira
  **cosa se ne prende** webview di sistema, estensioni «any programming language»
- **URL** http://neutralino.js.org/docs/configuration/neutralino.config.json/ · [V] · `fonti/neutralino-config.md`
  **perché conta qui** può caricare l'URL del server FastAPI?
  **cosa se ne prende** `url` accetta URL assoluti http; `modes.window.title/icon`
- **URL** http://neutralino.js.org/docs/how-to/extensions-overview/ · [V] · `fonti/neutralino-extensions.md`
  **perché conta qui** chiusura del processo Python
  **cosa se ne prende** «does not send kill signals to all extension instances» → auto-terminazione lato Python
- **URL** https://briefcase.beeware.org/en/stable/ · [V] · `fonti/briefcase-home.md`
  **perché conta qui** via senza Rust verso `.app`/`.msi`
  **cosa se ne prende** formati d'uscita per OS; Python bundlato e progetto arbitrario `[NON TROVATO]`
- **Misure in sessione** `[M]`, cwd `/Users/mario/GitHub/Tesi`, 2026-09-11:
  `gh api repos/r0x0r/pywebview/releases` (6.2.1 2026-04-15), `gh api repos/r0x0r/pywebview` (6012 stelle, push 2026-09-11, 14 issue), `gh api search/issues -f q='repo:r0x0r/pywebview webgl'` (5, nessuno WebGL), `curl https://pypi.org/pypi/{pywebview,pythonnet}/json` (6.2.1 `>=3.8`; 3.1.0 `>=3.10,<3.15`), `uv venv -p 3.12 + uv pip install pywebview + du -sh site-packages` (33 MB, macOS arm64), `gh api repos/electron/electron/releases/latest` (v44.3.0, 123/150 MiB), `gh api repos/tauri-apps/tauri/releases` (2.11.5 2026-07-01), `gh api repos/neutralinojs/neutralinojs/releases/latest` (v6.9.0 2026-07-24), `gh api repos/encode/uvicorn/releases/latest` (0.52.4 2026-08-19), `du -sh meshrec/.venv` (965M), `ls /Applications | grep -i chrome` (Google Chrome.app), `sw_vers` (macOS 26.6.2).
- **Non raggiunti in sessione** `[NON TROVATO]`: `developer.apple.com` (bundle `.app`), `source.chromium.org` (letto via peter.sh), `pywebview.flowrl.com/guide/usage.html` (404; usata la pagina API), pagina NiceGUI native (app JS; usato il sorgente).
