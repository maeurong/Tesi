# Fase 8 — I prompt delle nove sessioni

> **Nota del 03/09/2026.** Questo piano istruisce a costruire OpenSees, la
> sezione a fibre e l'armatura dichiarata dentro MeshRec. Tre giorni dopo la
> sua stesura la decisione di perimetro
> (`docs/superpowers/specs/2026-08-31-perimetro-del-progetto-design.md`) ha
> chiuso il prodotto sul deck, e il 2-3 settembre la mappa
> [#161](https://github.com/maeurong/Tesi/issues/161) ha rimosso tutto ciò che
> questo piano descrive. La mappa che lo generava,
> [#127](https://github.com/maeurong/Tesi/issues/127), è chiusa come
> abbandonata. Resta come registro di come si sarebbe fatto.

Da incollare, uno per chat, in una sessione nuova di Claude Code aperta su
`/mnt/c/Users/mario/GitHub/Tesi`.

**Il sequenziamento è vincolante:** [2026-08-29-meshrec-fase-8-sequenziamento.md](2026-08-29-meshrec-fase-8-sequenziamento.md).
Ogni prompt vi rimanda invece di ricopiarlo, così la conoscenza resta in un
posto solo e non diverge fra nove sessioni.

## Regola d'ordine

```
onda 0  →  1 sessione, da sola, PRIMA di tutto
onda 1  →  4 sessioni insieme        A · B · E · H-guscio
onda 2  →  2 sessioni insieme        C · F
onda 3  →  2 sessioni insieme        D · G
onda 4  →  1 sessione                H-pannelli
```

Un'onda comincia quando l'onda precedente è **fusa in `main`**, non quando è
verde su un ramo. Chi apre una sessione fa `git pull` prima di tutto.

## Prima di aprire la prima sessione

Il `.venv` in `meshrec/` è un ambiente Windows e `uv` sotto WSL non lo sa
ricreare:

```
error: failed to remove directory '.../meshrec/.venv/Scripts': Permission denied (os error 13)
```

Da Windows, in `meshrec\`: `rmdir /s /q .venv` e poi `uv sync`. Finché non è
fatto, nessuna delle nove sessioni può eseguire la suite, e una sessione che
non esegue la suite non può chiudere un compito.

---

## Onda 0 — lo schema

Ramo: `feat/fase-8-schema`. **Nessun'altra sessione parte finché questa non è fusa.**

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima, per intero:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md, sezioni
  §3 (onda 0), §4.1, §4.2, §5, §6, §7.1, §9 (paragrafo «Onda 0 — lo schema»)

Sei l'onda 0 del sequenziamento: la sola sessione che tocca lo schema. Il tuo
lavoro è esattamente la tabella di §3 «Onda 0», e i nomi che scrivi sono il
contratto di §4.2 che le altre otto sessioni leggeranno.

File in esclusiva: core/config.py, core/sweep.py, core/steps.py,
app/server.py. Non aprire nient'altro.

L'invariante di §6 è la ragione per cui esisti da sola: ventidue righe di
registro non devono cambiare impronta. PRIMA di toccare qualunque cosa,
rimisura la base con `uv run pytest tests/test_config.py -q -k "impronta or
blocchi_nuovi"` da meshrec/ — i tre nomi di test, l'aggregato e le due
impronte del caso studio in §6 sono stati LETTI dal file, non eseguiti.
Se la base non è verde prima delle tue modifiche, fermati e dillo.

Le quattro trappole di §6 sono numerate. La terza — un predefinito truthy
dentro un blocco di BLOCCHI_VUOTI_FUORI_IMPRONTA — passa il test dei blocchi
e rompe l'impronta lo stesso: ogni campo nuovo dentro `regioni` e `carichi`
nasce falso, zero, vuoto o None, e lo dichiari nel commit.

L'aggregato sha256 non si riscrive per far passare un test. Se cambia, o hai
sbagliato, o lo hai cambiato apposta e allora lo spieghi nel messaggio di
commit.

Il blocco nuovo entra con il suo test su /api/schema nello stesso commit
(§5 punto 9: il difetto è già occorso, 5d4d24b).

Skill-gate: invoca superpowers:test-driven-development e dev-workflow prima
di scrivere. Ponytail e caveman sono attivi.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per l'onda 0:
coperta / scoperta / non pertinente, con il test che la prova.

Ogni affermazione su cosa fa il codice va citata come file.ext:riga.

Lavora su un ramo `feat/fase-8-schema`. Commit piccoli. Non fondere.
```

---

## Onda 1 — quattro sessioni insieme

### A — il prior estende ciò che misura

Ramo: `feat/fase-8-prior-esteso`. **Questa ha già un piano scritto per esteso.**

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Attua, compito per compito:
  docs/superpowers/plans/2026-08-29-meshrec-fase-8-prior-esteso.md
La spec che il piano argomenta:
  docs/superpowers/specs/2026-08-29-meshrec-fase-8-prior-esteso-design.md

Skill-gate: usa superpowers:subagent-driven-development, che il piano stesso
richiede in testa.

Contesto d'onda, da leggere ma non da riaprire:
docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.3, §7.2,
§9 (paragrafo «A — il prior estende ciò che misura»).

Una divergenza dichiarata: §4.3 del sequenziamento colloca `ruoli_dell_incontro`
in un modulo nuovo core/adiacenza.py; il piano lo mette in core/wall.py. Per
questo ramo VALE IL PIANO — il sequenziamento lo dice esplicitamente. Non
creare adiacenza.py.

Sei il più sbloccante e il più costoso da sbagliare dell'onda: C, D e F
leggeranno la forma che restituisci, H la mostrerà. Se devi cambiare la forma
fissata in §4.3, non la cambi in silenzio: ti fermi e lo dici.

File in esclusiva: core/wall.py, core/hexa.py, core/pipeline.py e i loro test.
Non aprire core/config.py, core/abaqus.py, app/server.py, ui/.
Se scopri di aver bisogno di un campo di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0. Ti fermi e lo riporti.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per A.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-prior-esteso`. Non fondere.
```

### B — il catalogo dei materiali

Ramo: `feat/fase-8-materiali`. Il più economico dei quattro.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.1
  (la forma di soglie.py), §4.4 (il tuo contratto), §9 (paragrafo «B»)
- core/soglie.py per intero: è la forma che devi imitare, non una forma nuova
- i ticket #135 e #141

Costruisci core/materiali.py: il catalogo dei materiali nella forma di
soglie.py — ogni voce con `fonte`, `origine`, `fissata`, `nota` — e i test che
rifiutano la voce senza fonte o giustificata da sé, esattamente come i test di
soglie.py già fanno.

Le voci di norma sono valori CARATTERISTICI (#141 Q3). Il programma deriva i
valori di progetto con i γ di norma: α_cc=0,85, γ_c=1,5, γ_s=1,15 (NTC 2018).
Il fattore di confidenza FC resta giudizio dell'operatore e il programma non
lo sceglie.

Una casella che nessun ticket riempie, e che TU NON DECIDI: cosa fa il
programma con f_cd/f_yd quando il materiale è dichiarato a mano con
veste = "gia_ridotta" (§8.2 del sequenziamento). Se il tuo lavoro ci arriva
addosso, ti fermi e chiedi a Mario.

File in esclusiva: core/materiali.py (nuovo), tests/test_materiali.py (nuovo).
Non aprire core/config.py (è dell'onda 0), core/abaqus.py (è di F in onda 2),
core/soglie.py (§5 punto 10: nessuno ci scrive in questa fase).

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per B.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-materiali`. Non fondere.
```

### E — solutore e OpenSees

Ramo: `feat/fase-8-solutore`. Il più lungo dell'onda: parte per primo dei quattro.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.6
  (il tuo contratto), §5 punti 5, 6 e 12, §8.3, §9 (paragrafo «E»)
- i ticket #139, #138, #144
- docs/validazione/ricerca-opensees-e-armature.md
- core/solve.py per intero: i sette controlli esistenti e il contratto dei
  risultati neutro rispetto al solutore che già documenta

Costruisci: core/opensees.py (scrittore .tcl + lettore delle uscite); i sette
controlli di solve portati al secondo solutore; write_vtu con i dati per
cella; percorso dichiarabile per ccx E per OpenSees; `meshrec dottore` come
sottocomando di cli.py.

PRIMA di implementare i controlli, scrivi la tabella «quale controllo vale su
quale modello» che #138 pretende. Il ticket dice che va scritta prima, non
dedotta dopo: un controllo che gira dove non significa niente produce un
verde che non vale nulla. È il quarto errore più costoso di tutta la fase
(§7.4).

OpenSees 3.8.0 è verificato funzionante da WSL. In 3D `-GJ` è obbligatorio
nelle sezioni a fibre: verificato per esecuzione, non per lettura.

L'ordine di `casi_di_carico` è un contratto col lettore del .frd: un ordine
diverso da quello del deck scambia i risultati. Se lo tocchi, lo dichiari nel
commit.

File in esclusiva: core/opensees.py (nuovo), core/solve.py, cli.py,
core/abaqus.py MA SOLO write_vtu (~riga 1625) e i loro test.
Non aprire core/config.py (onda 0), app/server.py e ui/ (sono di H, sempre:
§5 punto 8), il resto di core/abaqus.py.
Se scopri di aver bisogno di un campo di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0. Ti fermi e lo riporti.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per E. Le tre
classi di difetto già accadute in questo repo ti riguardano tutte e tre, e la
terza — lettura di un'uscita esterna troncata o mal codificata — è il tuo
mestiere principale.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-solutore`. Non fondere.
```

### H-guscio — la seconda schermata, vuota

Ramo: `feat/fase-8-guscio`. Il meno rischioso.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §3
  (onda 1, riga H-guscio), §5 punto 8, §7.2, §9 (paragrafo «H»)
- i ticket #137 e #140
- meshrec/docs/raffinamento-interfaccia-step.md

Fai due cose e nessuna terza:
1. La colonna della pipeline scende a dodici step e si chiude con un
   collegamento alla seconda schermata (#140: lo step 13 resta il solutore, ma
   vive in una schermata sua).
2. La seconda schermata esiste, VUOTA, con i quattro stadi in ordine di
   dipendenza: modello, struttura, pre-processore, post-processore.

I pannelli NON si riempiono qui. Tutto ciò che H mostra è un numero che
qualcun altro produce, e i produttori stanno ancora lavorando. Un pannello
scritto prima del numero mostra un segnaposto, e un segnaposto in questa
applicazione è esattamente il difetto che il progetto è costruito per non
produrre. I pannelli sono l'onda 4.

Sei l'unico scrittore di ui/ e app/server.py, in tutta la fase e sempre.

File in esclusiva: ui/index.html, ui/app.js, ui/stile.css, ui/viewport.js,
app/server.py e i loro test.
Non aprire nulla in core/.
Attenzione: app/server.py lo tocca anche l'onda 0 per /api/schema. Fai
`git pull` prima di partire e non riscrivere lo schema.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per H.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-guscio`. Non fondere.
```

---

## Onda 2 — due sessioni insieme

### C — armatura e controlli di sezione

Ramo: `feat/fase-8-armatura`.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.3
  (cosa A ti passa), §4.4 (cosa B ti passa), §4.5 (il tuo contratto),
  §8.2 (la casella che non devi indovinare), §9 (paragrafo «C»)
- i ticket #141 e #136
- docs/validazione/ricerca-armature-convenzioni-normative.md
- docs/validazione/ricerca-armature-opensees-fibre.md

Costruisci core/armatura.py: i nove campi dichiarati, i tre derivati, i
controlli μ / μ_min / μ_bil / ε_ud PER STAZIONE (venti stazioni per membratura,
non una), il verdetto fragile / duttile / oltre la bilanciata, le due guardie
geometriche che fermano.

Il programma RILEVA, non progetta. Una sezione sotto il minimo di normativa è
un RISULTATO da mostrare, non un errore d'ingresso da rifiutare (#136). Non
scrivere validazioni che impediscono all'utente di descrivere ciò che ha
misurato.

A_s,min = 0,26 · (f_ctm / f_yk) · b · d — NTC 2018 §4.1.6.1.1.

Una casella che nessun ticket riempie, e che TU NON DECIDI: cosa fa il
programma con f_cd/f_yd quando il materiale è dichiarato a mano con
veste = "gia_ridotta" (§8.2). Ci arriverai addosso. Quando succede, ti fermi
e chiedi a Mario.

File in esclusiva: core/armatura.py (nuovo), tests/test_armatura.py (nuovo),
tests/test_config.py per i soli domini dei campi.
Non aprire core/abaqus.py (è di F, stessa onda), core/pipeline.py (è di F,
stessa onda), ui/ e app/server.py (sono di H).
Se scopri di aver bisogno di un blocco di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0 e ti fermi.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per C.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-armatura`. Non fondere.
```

### F — tetraedro → membratura

Ramo: `feat/fase-8-attribuzione`.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.3
  (cosa A ti passa), §4.4 (cosa B ti passa), §4.8 (il tuo contratto),
  §5 punti 3, 4, 7 e 11, §9 (paragrafo «F»)
- i ticket #135 e #142
- core/abaqus.py, in particolare la riga *SOLID SECTION (~riga 444)

Costruisci core/attribuzione.py: mappa tetraedro → membratura per baricentro,
il conteso assegnato alla maggiore, l'orfano ad analysis.material, le quattro
misure da mostrare. Poi ALL_WALL si partiziona in un *ELSET per regione e il
deck acquista molte righe *SOLID SECTION invece di una.

ALL_WALL non si rinomina e non si toglie: PRODUCT.md lo elenca fra i letterali
da preservare alla lettera. Diventa l'insieme che le regioni partizionano.

La frazione orfana è una grandezza CANDIDATA a diventare una soglia, ma non ha
ancora una fonte: per ora si misura e si mostra. Non scrivere in core/soglie.py
(§5 punto 10) — quel modulo pretende una fonte, e ratificarla dopo aver visto
il numero è precisamente il difetto che esiste per impedire.

File in esclusiva: core/attribuzione.py (nuovo), core/abaqus.py (la riga
*SOLID SECTION e il parametro elset), core/pipeline.py, tests/test_abaqus.py.
NON toccare abaqus._passo_statico (~riga 121): è di G, onda 3.
Non aprire core/armatura.py (è di C, stessa onda), ui/ e app/server.py.
Se scopri di aver bisogno di un blocco di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0 e ti fermi.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per F.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-attribuzione`. Non fondere.
```

---

## Onda 3 — due sessioni insieme

### D — il telaio a fibre

Ramo: `feat/fase-8-telaio`.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.3
  (A), §4.5 (C), §4.6 (E), §4.7 (il tuo contratto), §5 punto 7,
  §7.3, §9 (paragrafo «D»)
- il ticket #145
- docs/validazione/ricerca-armature-opensees-fibre.md

Costruisci core/telaio.py: venti elementi per membratura, ciascuno con la
sezione della PROPRIA fetta; nodi dall'adiacenza che A ha scritto; lunghezza
di calcolo da nodo a nodo; armatura riposizionata a ogni stazione.

Il tuo mestiere è COMPORRE, non inventare le parti: A, B, C ed E le hanno già
fatte. Se una parte ti manca, la parte manca davvero e lo dici.

La sezione varia lungo l'asse ed è giusto che vari: l'oggetto è rilevato, con
i suoi difetti, e appiattire le venti fette a una sezione media butterebbe via
esattamente ciò che il programma misura.

In 3D `-GJ` è obbligatorio nelle sezioni a fibre di OpenSees.

File in esclusiva: core/telaio.py (nuovo), core/pipeline.py,
tests/test_telaio.py (nuovo).
Non aprire core/abaqus.py né core/solve.py (sono di G, stessa onda), ui/ e
app/server.py.
Se scopri di aver bisogno di un blocco di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0 e ti fermi.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per D.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-telaio`. Non fondere.
```

### G — combinazioni e sismica

Ramo: `feat/fase-8-combinazioni`. **Metà del ramo non parte: vedi il prompt.**

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §4.9
  (il tuo contratto), §5 punti 4, 6 e 12, §8.1 (dove ti fermi),
  §9 (paragrafo «G»)
- il ticket #146
- core/abaqus.py:_passo_statico (~riga 121)

Costruisci core/combinazioni.py: la natura dell'azione dichiarata (senza,
nessun coefficiente si sceglie da solo), le combinazioni NTC 2018 proposte e
CORREGGIBILI dall'utente, i casi singoli che restano disponibili, la sismica
STATICA EQUIVALENTE. Poi più azioni entrano dentro un *STEP solo.

TI FERMI PRIMA DELLA MODALE CON SPETTRO. #146 la vuole, ma pretende la
combinazione delle risposte modali (SRSS o CQC) che produce una grandezza
senza segno che non appartiene a nessun caso, mentre il contratto di #138 è
«un campo per caso». La decisione MANCA: non è un rinvio, è una casella vuota.
Attui la statica equivalente e ti fermi.

L'ordine di `casi_di_carico` è un contratto col lettore del .frd: le
combinazioni entrano DOPO i casi singoli, e un ordine diverso da quello del
deck scambia i risultati in silenzio. Lo dichiari nel commit.

Vincoli e carichi si assegnano nel PRE-PROCESSORE, non altrove: carichi,
sovraccarichi, combinazioni, vincoli e combinazioni sismiche sono tutti suoi
(#137).

File in esclusiva: core/combinazioni.py (nuovo), core/abaqus.py MA SOLO
_passo_statico, core/solve.py, tests/test_abaqus.py, tests/test_solve.py.
NON aprire core/pipeline.py: è di D, stessa onda. Se scopri di doverlo
toccare, ti fermi e lo dici invece di aprirlo.
Non aprire ui/ e app/server.py.
Se scopri di aver bisogno di un blocco di configurazione nuovo, NON lo aggiungi:
appartiene all'onda 0 e ti fermi.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per G.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-combinazioni`. Non fondere.
```

---

## Onda 4 — una sessione

### H-pannelli — i quattro stadi riempiti

Ramo: `feat/fase-8-pannelli`.

```
Lavoriamo su MeshRec, in /mnt/c/Users/mario/GitHub/Tesi.

Leggi prima:
- docs/superpowers/plans/2026-08-29-meshrec-fase-8-sequenziamento.md §3
  (onda 4), §4.3-§4.9 (tutti i contratti: mostri quello che gli altri otto
  hanno prodotto), §5 punto 8, §8.4, §9 (paragrafo «H»)
- i ticket #137 e #140
- meshrec/docs/raffinamento-interfaccia-step.md

Riempi i quattro stadi della seconda schermata:
1. modello — con il solutore scelto sulla diagonale
2. struttura — con il verdetto per stazione
3. pre-processore — vincoli, carichi, combinazioni, sismica
4. post-processore — la vista con caso e grandezza

Le tre grandezze che i ticket OBBLIGANO a mostrare, e che non sono
facoltative: `riempimento_sezione`, la distanza di proiezione del nodo, la
frazione orfana.

Lo stadio 4 attua CIÒ CHE C'È GIÀ — la vista con caso e grandezza come fa
oggi lo step 13 — e non inventa il resto: mappe di colore, deformate e scelta
delle grandezze dipendono da cosa i due solutori hanno in comune come
risultato, e la mappa tiene la decisione in «Not yet specified» (§8.4).

Ogni numero che mostri ha un controllo che lo contraddice se il risultato
peggiora. È la regola di costruzione del progetto, non uno slogan.

File in esclusiva: ui/app.js, ui/index.html, ui/stile.css, app/server.py,
tests/test_app_js.py, tests/test_server.py.
Non aprire core/: se un numero che devi mostrare non esiste, NON lo calcoli
qui. Ti fermi e dici quale ramo doveva produrlo.

Skill-gate: superpowers:test-driven-development e dev-workflow prima di
scrivere.

Rispondi riga per riga alla lista «Ingressi degeneri» di §9 per H.
Ogni affermazione su cosa fa il codice va citata come file.ext:riga.
Ponytail e caveman sono attivi.

Ramo `feat/fase-8-pannelli`. Non fondere.
```

---

## Dopo ogni onda, prima della successiva

Da `meshrec/`, sul `main` con l'onda fusa dentro:

```bash
uv run pytest tests/test_config.py -q -k "impronta or blocchi_nuovi"
uv run pytest -q
```

E il controllo che non ha bisogno del venv, da `meshrec/`:

```bash
python3 - <<'EOF'
import json, pathlib
tot = ok = 0
for reg in sorted(pathlib.Path("experiments").glob("*/registro.jsonl")):
    for riga in reg.read_text(encoding="utf-8").splitlines():
        if not riga.strip():
            continue
        v = json.loads(riga); tot += 1
        cartella = v["out_dir"].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        ok += cartella == v["fingerprint"][:12]
print(f"righe: {tot}  ancorate: {ok}")
EOF
```

Atteso: `righe: 22  ancorate: 22`. Un numero diverso significa che un'onda ha
mosso l'impronta, e va trovata prima di aprire l'onda dopo.

## Le tre decisioni che mancano

Nessuna sessione le indovina. Arrivano a Mario.

| dove | che cosa manca | chi si ferma |
|---|---|---|
| §8.1 | l'inviluppo modale: SRSS o CQC, e come una grandezza senza segno sta nel contratto «un campo per caso» | G, a metà |
| §8.2 | `f_cd`/`f_yd` su un materiale dichiarato a mano con veste «già ridotta» | C, e B se ci arriva |
| §8.3 | se il controllo delle dipendenze è una tratta del server, un sottocomando, o entrambi | nessuno: E fa il sottocomando, H la tratta se serve |
