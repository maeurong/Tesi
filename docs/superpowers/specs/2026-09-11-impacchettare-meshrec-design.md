# MeshRec come programma: finestra propria, identità, citabilità

**Data:** 11 settembre 2026
**Stato:** approvata dall'autore, pronta per `superpowers:writing-plans`
**Ricerca:** [`docs/ricerca/index.md`](../../ricerca/index.md) — tre ricerche
dell'11 settembre 2026: [guscio desktop](../../ricerca/2026-09-11-guscio-desktop.md),
[distribuzione binaria](../../ricerca/2026-09-11-distribuzione-binaria.md),
[identità e autorevolezza](../../ricerca/2026-09-11-identita-e-autorevolezza.md).
**Glossario:** [CONTEXT.md](../../../CONTEXT.md). I termini in grassetto alla
prima occorrenza sono quelli del glossario.

## Problem Statement

Oggi MeshRec si avvia da terminale (`uv run meshrec serve`, o il doppio clic
su `MeshRec.command` / `MeshRec.bat`) e vive in una scheda del browser accanto
alla posta. Per l'autore, che lo usa ogni giorno, va bene. Per la discussione
di tesi del 19 settembre 2026 — commissione e tutori che lo vedono usato — e
per il laboratorio che lo erediterà, deve **sembrare e usarsi come un
programma**: una finestra sua con nome e icona, un'icona nel Dock o nel menu
Start, una versione, una riga che dice chi è e come si cita, un repository
che porta il nome del programma e non «Tesi».

Le tre ricerche hanno mappato il terreno. Le decisioni prese con l'autore
l'11 settembre 2026:

- **Destinatario di questo giro: la discussione.** Il laboratorio continua con
  `uv sync`; il pacchetto scaricabile senza `uv` (cartella portabile, via A
  della ricerca sulla distribuzione) resta un passo successivo, dichiarato.
- **Piattaforme: macOS arm64 e Windows 11**, le due di `PRODUCT.md`.
- **Guscio: pywebview**, con Chromium/Edge in modalità `--app` come fallback
  automatico. PWA scartata (non avvia il server), Tauri/Electron sproporzionati.
- **Salvataggio immagini via server**, non più download del browser: in
  pywebview ogni `<a download>` apre un pannello «Salva» modale, e «salva tutti
  gli step» ne aprirebbe uno per step. Le immagini vanno accanto alla
  **corsa**.
- **Identità completa**: rename del repo `Tesi` → `meshrec`, `CITATION.cff`,
  `CHANGELOG.md`, versione `1.0.0`, GitHub Release, DOI Zenodo, screenshot e
  badge. Senza ORCID. La cartella locale `~/GitHub/Tesi` non si rinomina.

Prova fatta l'11 settembre 2026 su macOS arm64, pywebview 6.2 contro il
server acceso: viewport three.js in WebGL 2.0, titolo «MeshRec», `EventSource`
disponibile, chiusura della finestra pulita, `<a download>` con data URL apre
il pannello «Salva» nativo con nome proposto e cartella Downloads. La menu bar
dice «python»: il nome corretto arriva solo con un bundle `.app`. **Su Windows
non è stato provato**: è il rischio residuo, e la PR della finestra non si fonde
senza quell'esito.

## Fuori ambito

- Pacchetto scaricabile senza `uv` (cartella portabile, PyInstaller, installer,
  firma del codice). Ricercato, rimandato a dopo la tesi.
- Spostare `runs/`, `experiments/`, `.cache/viewport` dalla cartella corrente
  a una cartella dati utente: serve solo a un'installazione sotto
  `Program Files` o `/Applications`; i launcher fanno già `cd` nella propria
  cartella.
- Watchdog SSE (uscita del server quando nessun client è collegato): pywebview
  ha l'evento di chiusura e il fallback `--app` ha `Popen.wait`. Si aggiunge
  solo se un utente chiude la scheda del browser e trova il processo ancora
  vivo.
- Sito MkDocs, JOSS (eleggibile dal 13 febbraio 2027), video della corsa:
  «vita dopo la tesi», da dichiarare in discussione come prossimi passi.
- Nessuna grafica nuova nell'interfaccia oltre l'icona e una riga a piè di
  pagina.

## §1 Finestra propria

### Avvio

`meshrec serve` (`cli.py:222-272`) cambia così:

1. Controllo della porta come oggi (bind di prova, messaggio su porta
   occupata).
2. uvicorn parte in un **thread** con `uvicorn.Server(uvicorn.Config(...))`
   invece di `uvicorn.run`: il thread principale resta libero per il guscio,
   e `server.should_exit = True` lo ferma. uvicorn salta l'installazione dei
   gestori di segnale fuori dal thread principale, quindi Ctrl-C resta al
   processo.
3. Attesa che il server ascolti (`server.started`, con timeout di 10 s e
   messaggio d'errore se non arriva), poi scelta del guscio nell'ordine:
   - **pywebview** se `import webview` riesce e, su Windows, il runtime
     WebView2 risulta installato (chiave di registro
     `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`
     o la gemella in `HKCU`). `webview.settings['ALLOW_DOWNLOADS'] = True`
     resta per i download che non sono immagini (nessuno oggi; costa una riga
     e evita un click muto). `webview.create_window("MeshRec", indirizzo,
     width=1280, height=800)` e `webview.start()`; al ritorno,
     `should_exit = True`, join del thread, uscita 0. Mai il fallback MSHTML
     di pywebview: su Windows senza WebView2 si passa al punto seguente.
   - **Chromium in modalità app**: Edge (`msedge`) su Windows, Chrome su
     entrambe, cercati nelle posizioni standard (registro `App Paths` su
     Windows, `/Applications/*.app/Contents/MacOS/*` su macOS).
     `subprocess.Popen([exe, f"--app={indirizzo}", f"--user-data-dir={cache}/finestra",
     "--no-first-run"])`; `Popen.wait()` poi `should_exit`. Il profilo dedicato
     è ciò che fa uscire il processo alla chiusura della finestra (con il
     profilo dell'utente, Chrome aperto altrove tiene vivo il figlio e `wait`
     torna subito).
   - **Browser di sistema** come oggi (`webbrowser.open` dopo 1 s) con un
     avviso su stderr: «nessuna finestra disponibile: apro nel browser». In
     questo ramo il server resta in ascolto finché Ctrl-C, come oggi.
4. Flag: `--browser` salta pywebview e `--app` e apre il browser (per
   DevTools e debug); `--no-browser` resta com'è (server e basta).
   `ServerConfig.open_browser` (`config.py:1033`) resta e vale per il ramo
   browser.

`pywebview>=6.2` entra in `dependencies` di `pyproject.toml` (vincolo `>=6.2`:
prima di 6.2 pywebview crashava su arm64 e mancava il fallback coreclr per
pythonnet su Windows).

### Ingressi degeneri

- porta occupata → messaggio di oggi, ritorno 1, nessuna finestra aperta
- pywebview installato ma WebView2 assente (Windows) → fallback `--app` senza
  eccezione, riga su stderr che dice perché
- nessun Chromium trovato → browser di sistema con avviso, ritorno 0
- il server non ascolta entro 10 s → `should_exit`, messaggio, ritorno 1
- finestra chiusa mentre uno step è in calcolo → il worker riceve lo stop di
  oggi (`Worker.annulla`), il processo esce comunque entro pochi secondi
- `--no-browser` → nessun guscio, comportamento invariato
- `--browser` e pywebview installato → il browser, non la finestra

### Prova su Windows

`docs/prove/2026-09-finestra-windows.md`: il comando da lanciare sul PC
Windows dell'autore (`uv run meshrec serve` dopo `uv sync`), l'elenco di ciò
che va guardato (finestra con titolo, viewport 3D visibile, «Sfoglia» che porta
il dialogo Tk in primo piano, «Salva immagine» che scrive in `immagini/`,
chiusura della finestra che termina il processo, avvio senza WebView2 se si
riesce a simularlo) e lo spazio per l'esito datato. La PR della finestra si
fonde con l'esito scritto.

## §2 Salvataggio immagini via server

### Rotta

`POST /api/immagine`, corpo JSON `{numero, nome, didascalia, dati}`:
`numero` intero dello **step**, `nome` e `didascalia` stringhe come già le
compone `app.js`, `dati` data URL `image/png` prodotto da
`immagineConProvenienza` (`app.js:1962`).

Il server:

1. 409 se nessuna corsa è legata (`stato_corsa()["legata"]` falso,
   `server.py:889`).
2. 413 se il corpo supera 50 MB (limite dichiarato, sopra ogni PNG di
   viewport misurato).
3. 400 se `dati` non inizia con `data:image/png;base64,` o i byte decodificati
   non iniziano con la firma PNG `\x89PNG\r\n\x1a\n`.
4. Ricostruisce il nome del file **lato server** con la stessa regola di
   `nomeDellImmagine` (`app.js:1849-1856`): pezzi `[nome corsa, numero a due
   cifre, nome, didascalia]` in minuscolo, accenti tolti (NFD e rimozione dei
   combinanti), tutto ciò che non è `[a-z0-9]` diventa `-`, trattini ai bordi
   tolti, pezzi vuoti scartati, unione con `-`, estensione `.png`. Il nome
   non arriva dal client: così un percorso nel nome non può uscire dalla
   cartella.
5. Scrive in `<out_dir>/immagini/<nome>.png` con `scrivi_atomico`
   (`io.py:118`), creando `immagini/` se manca. Un file con lo stesso nome si
   sovrascrive: rieseguire lo step e risalvare deve dare l'immagine nuova, non
   un `-2`.
6. Risponde `{"percorso": "<out_dir>/immagini/<nome>.png"}` con il percorso
   così come il resto dell'API riporta `out_dir`.

### Interfaccia

In `salvaImmagine` (`app.js:2132-2136`) il `<a download>` diventa un `fetch`
POST. Esito 200: `#esito-salvataggio` mostra «Salvata in <percorso>» e la
funzione torna `true` come oggi. Esito diverso: `dichiaraErrore` con il
messaggio del server, ritorno `undefined`, e il giro di `salvaTuttiGliStep`
(`app.js:2162`) si ferma su quello come già fa. La regola di nome in `app.js`
resta, perché la usa il messaggio a video e va tenuta identica a quella del
server: un test lo verifica.

Vale anche nel browser: le immagini stanno accanto alla corsa, dove finiscono
in appendice, e non in Downloads.

### Ingressi degeneri

- nessuna corsa legata → 409, nessun file scritto
- `dati` vuoto, non data URL, base64 corrotto, PNG senza firma → 400, nessun
  file scritto
- corpo di 50 MB + 1 byte → 413
- `nome` o `didascalia` con `/`, `..`, accenti, spazi, vuoti → nome
  sanificato dentro `immagini/`, mai fuori; entrambi vuoti → `<corsa>-<nn>.png`
- stesso nome due volte → secondo file sovrascrive il primo, risposta 200
- `immagini/` esiste come file e non come cartella → 500 con messaggio che dice
  il percorso, nessuna eccezione non gestita
- disco pieno a metà scrittura → `scrivi_atomico` non lascia un file parziale

## §3 Icona, bundle, «Informazioni su»

### Icona

`meshrec/src/meshrec/ui/icona.svg`: marca e wordmark, proposta dall'assistente
e approvata da Mario a vista prima di derivare i formati. Registro di
`PRODUCT.md`: asciutto, stampabile accanto a un testo composto, nessuna
identità d'ateneo. Da lì `meshrec/strumenti/genera-icone.py` (Pillow è già
nel lock come dipendenza transitiva; `iconutil` di macOS per l'`.icns`)
produce `icona.icns`, `icona.ico`, e i PNG 32/180/512 per favicon e
`apple-touch-icon`. I derivati si committano: chi clona non deve avere
`iconutil`.

### macOS: `MeshRec.app`

`meshrec/MeshRec.app/Contents/Info.plist` (`CFBundleName` MeshRec,
`CFBundleIdentifier` `it.meshrec.app`, `CFBundleIconFile`,
`CFBundleShortVersionString` letto dal `pyproject.toml` dallo script che
genera le icone, `LSMinimumSystemVersion`), `Contents/MacOS/MeshRec` = script
`sh` con la logica di `MeshRec.command` (cd nella cartella del bundle risalendo
di tre livelli, `PATH` con `uv`, messaggio se `uv` manca, `uv run meshrec
serve "$@"`), `Contents/Resources/icona.icns`. `MeshRec.command` **sparisce**:
il bundle lo sostituisce, e il README lo dice. Dock, Cmd-Tab e menu bar dicono
«MeshRec».

Gatekeeper: il bundle non è firmato; al primo doppio clic macOS Sequoia chiede
di autorizzarlo da Impostazioni › Privacy e sicurezza. Il README lo dice in
una riga con il percorso esatto. Nessuna firma in questo giro.

### Windows: collegamento

`MeshRec.bat` resta. `meshrec/crea-collegamento.ps1` (una decina di righe con
`WScript.Shell`) crea `MeshRec.lnk` nel menu Start dell'utente che punta a
`MeshRec.bat` con `icona.ico` e la cartella di lavoro giusta. Si lancia una
volta; il README lo dice.

### `GET /api/info` e piè di pagina

Rotta `GET /api/info` → `{"nome": "MeshRec", "versione": <importlib.metadata.version("meshrec")>,
"commit": <sha corto o null>, "licenza": "MIT", "doi": <stringa o null>,
"repository": "https://github.com/maeurong/meshrec"}`. Il commit viene da
`git rev-parse --short HEAD` con timeout di 2 s nella cartella del pacchetto;
se `git` manca o la cartella non è un repo, `null` e nessun errore. Il DOI
viene da `CITATION.cff` in radice (campo `doi`), se il file c'è; altrimenti
`null`.

`index.html`: un `<footer class="informazioni">` dopo `#lavoro` con una riga:
«MeshRec 1.0.0 · abc1234 · MIT · [come citare]». «come citare» è un link a
`repository` con `target="_blank"`. Nel browser apre una scheda; in pywebview
il comportamento dei link esterni va **misurato** nella prova su macOS e
Windows: se non si apre nel browser di sistema, la riga mostra l'URL come
testo selezionabile e il link sparisce. Con `commit` o `doi` a `null` il
pezzo corrispondente non si scrive, niente «null» a video. Tipografia e colori quelli di `stile.css`, in
corpo piccolo: nessuna grafica nuova.

### Ingressi degeneri

- `git` assente o cartella non repo → `commit: null`, rotta 200
- `CITATION.cff` assente o senza `doi` → `doi: null`, rotta 200
- pacchetto non installato (esecuzione da sorgente senza `uv sync`) →
  `importlib.metadata` solleva `PackageNotFoundError` → `versione: "sorgente"`
- `MeshRec.app` avviato da una cartella senza `uv` nel `PATH` → messaggio di
  `MeshRec.command` di oggi, finestra del Terminale che resta aperta
- `crea-collegamento.ps1` lanciato due volte → sovrascrive il `.lnk`, nessun
  duplicato
- `genera-icone.py` senza `iconutil` (non macOS) → produce `.ico` e PNG,
  salta `.icns` con un messaggio, ritorno 0

## §4 Identità su GitHub

Ordine vincolante, perché ogni passo scrive l'URL o il numero del precedente:

1. **Rename** `gh repo rename meshrec` (GitHub reindirizza il vecchio URL);
   descrizione «MeshRec — dal rilievo fotogrammetrico al modello FEM»;
   `git remote set-url origin`; ogni URL `maeurong/meshrec` in README, docs, spec,
   `CLAUDE.md`, `AGENTS.md`, `PRODUCT.md` aggiornato con un `sed` verificato
   da `grep`. La cartella locale resta `~/GitHub/Tesi`.
2. **`CITATION.cff`** in radice: `cff-version 1.2.0`, `title` MeshRec,
   `authors` Mario Fiorenzoni (senza ORCID), `version 1.0.0`, `date-released`
   = giorno del tag, `license MIT`, `repository-code`, `abstract` di due
   righe, `keywords`. Validato con `cffconvert --validate` (`uvx cffconvert`).
3. **`CHANGELOG.md`** (Keep a Changelog): sezione `[1.0.0]` con le voci
   ricavate dalle PR fuse, raggruppate per fase, e `[Unreleased]` vuota.
   `pyproject.toml` → `version = "1.0.0"`.
4. **Screenshot e badge**: `docs/immagini/viewport.png` catturato sulla corsa
   `geoandgeo-lab-pr2` (la sola che si carica oggi) nella finestra pywebview;
   in cima al README quattro badge (licenza, ultima release, DOI — dopo il
   punto 6 —, Python 3.12) e lo screenshot sotto il primo paragrafo.
5. **Tag e Release**, a PR fuse: `git tag -a v1.0.0`, `gh release create
   v1.0.0 --generate-notes --title "MeshRec 1.0.0"`. `date-released` nel CFF
   e la data in CHANGELOG sono quel giorno.
6. **Zenodo**, a mano dell'autore e **prima** del tag: login su zenodo.org con
   GitHub, toggle sul repo `maeurong/meshrec`. Procedura in
   `docs/prove/2026-09-zenodo.md` in cinque passi con cosa si vede a schermo.
   Dopo la release Zenodo assegna il DOI: badge nel README, campo `doi` nel
   CFF, riga in `/api/info`. Una seconda PR `chore/doi` di tre righe.

### Ingressi degeneri

- rename fatto e `grep -r "maeurong/meshrec"` trova ancora una riga → il passo
  non è chiuso; il test è il `grep` a zero righe (escluso `docs/ricerca/fonti/`,
  che è materiale catturato e non si tocca)
- `cffconvert --validate` fallisce → il CFF non si committa
- release creata senza toggle Zenodo → nessun DOI; si rifà una release
  `v1.0.1` dopo il toggle, il CFF si aggiorna

## §5 Sequenza, verifica, review

Tre PR da `main`, in quest'ordine:

- **PR1 `feat/salva-immagine-server`** (§2). Test in `tests/test_server.py`
  con httpx: 200 e file su disco con il nome atteso, 409, 400 (tre corpi
  cattivi), 413, nome sporco sanificato, sovrascrittura. Test in
  `tests/test_app_js.py` che la regola di nome in `app.js` e quella in
  Python coincidono su una lista di casi con accenti e simboli.
- **PR2 `feat/finestra`** (§1 + §3). Test in `tests/test_cli.py` con
  `webview` finto in `sys.modules`: chiusura → `should_exit`; senza WebView2
  su Windows simulato → ramo `--app`; senza Chromium → browser; `--browser`
  salta la finestra. Test di `/api/info` senza git e senza CFF. Il bundle e lo
  script PowerShell si provano a mano: macOS oggi, Windows dall'autore con
  l'esito in `docs/prove/`. Icona mostrata a Mario prima dei derivati.
- **PR3 `chore/identita`** (§4 punti 1-4). Il rename è la prima azione della
  PR perché README e CFF portano l'URL nuovo. Poi tag, release, Zenodo a mano,
  PR `chore/doi`.

Ogni PR passa il round pre-commit in parallelo: `security-reviewer`
(PR1 e PR2 toccano input esterno e sottoprocessi), `code-reviewer`,
`test-writer`, `craft-reviewer` (README, piè di pagina, CHANGELOG),
`spec-reviewer` contro questa spec. Commit con `caveman:caveman-commit`.
A fine lavoro `/graphify --update` sul repo: il grafo è committato in
`graphify-out/`.

## Rischi dichiarati

- **Windows non provato** con pywebview: se la prova dell'autore fallisce
  (WebGL assente in WebView2, dialogo Tk dietro la finestra), il fallback
  `--app` è la rete; se fallisce anche quello, la PR2 si fonde con il solo
  ramo browser e il bundle, e pywebview esce dalle dipendenze.
- **pywebview** ha un autore principale solo; attivo a settembre 2026. Il
  fallback `--app` esiste anche per questo.
- **Gatekeeper e SmartScreen** mostreranno l'avviso di sviluppatore non
  verificato: accettato, documentato nel README, firma rimandata.
- **Rename del repo**: i link nelle issue e nelle PR chiuse restano validi per
  il redirect di GitHub; gli appunti locali dell'assistente e la mappa
  graphify vanno aggiornati a mano.
