# Setaccio dei brief 8-15 — affermazioni non verificate

Metodo: ogni rilievo porta il comando eseguito e il suo esito. Gli script di
verifica stanno fuori dal repository, in `/Users/mario/.claude/jobs/e87eb542/tmp/`.
Nessun file del repository e' stato toccato.

Ambiente della verifica: `numpy 2.5.2`, `pytest 9.1.1`, `ccx` presente in
`/Users/mario/.local/bin/ccx`, `gmsh` importabile.

> **Aggiornamento del 20/08/2026.** I dodici rilievi del Task 8 sono chiusi:
> `task-8-brief.md` e' stato riscritto e porta in coda la sezione «Correzione del
> 20/08/2026 (setaccio)». Su **8.2 e 8.3 la cura e' cambiata** rispetto a quella
> proposta qui sotto: non si allarga la tolleranza a 66,7 mm (curava il sintomo,
> e avrebbe legato con un `*TIE` due superfici distanti 5,5 mm), si taglia sul
> bordo del solido per bisezione. Vuoto residuo 3,4e-12 mm invece di 5,528 mm, e
> CalculiX passa da ventotto `no tied MPC` a **zero**. La diagnosi di 8.3 resta
> valida — la tolleranza va passata a `dentro` e non gonfiando il prisma — ma il
> suo valore scende da 66,7 mm a 1e-6 mm, da raggio di ricerca a margine per il
> rumore in virgola mobile.

Conteggio: **11 BLOCCANTE, 22 SERIO, 11 MINORE** (44 in tutto). Nessun task e' risultato pulito;
i piu' leggeri sono il 15 (2 SERIO, 1 MINORE, e la maggior parte delle sue
affermazioni verificate **vere**) e il 14.

---

## Task 8 — `task-8-brief.md`

### 8.1 `np.cross` su vettori 2D non esiste piu' da numpy 2.0 — BLOCCANTE

**dove:** `task-8-brief.md:263`, dentro `dentro()`.

**cosa afferma:** `verso = np.cross(lato, sezione - primo)`, con la docstring
«quattro righe e nessun algoritmo di ray casting» (righe 244-247).

**perche' e' falso:** non e' eseguibile. Copiato il codice del brief in
`tmp/t8_taglio.py` ed eseguito da `meshrec/`:

```
ValueError: Both input arrays must be (arrays of) 3-dimensional vectors,
but they are 2 and 2 dimensional instead.
```

e `uv run python -c "import numpy as np; np.cross([1.,0.],[0.,1.])"` da' lo
stesso errore su numpy 2.5.2.

La lezione e' gia' scritta nel repository, venti righe dentro la funzione che il
brief cita per nome — `wall.semplifica_contorno`, `src/meshrec/core/wall.py:322`:

> `# np.cross rifiuta vettori 2D da numpy 2.0, quindi la componente z del prodotto vettoriale si scrive per esteso`

**correzione proposta:**

```python
        lato = secondo - primo
        scostamento = sezione - primo
        verso = lato[0] * scostamento[:, 1] - lato[1] * scostamento[:, 0]
        dentro_sezione &= verso >= -1e-9
```

e nella docstring, al posto di «quattro righe e nessun algoritmo di ray
casting», la ragione vera: la componente z scritta per esteso perche' numpy 2.0
ha tolto `np.cross` sui vettori 2D — stessa nota di `wall.semplifica_contorno`.

**gravita':** BLOCCANTE (tutti i test che toccano `dentro`, `taglia_giunzioni` e
`costruisci` sollevano).

---

### 8.2 Nella geometria del test il taglio non avviene, e il test passa lo stesso — BLOCCANTE

**dove:** `task-8-brief.md:121-150`, `test_due_prismi_che_si_compenetrano_vengono_tagliati_e_il_volume_torna`.

**cosa afferma:** `assert accorciato.lunghezza < 1600.0, "la colonna doveva fermarsi sotto la trave"`.

**perche' e' falso:** con `np.cross` corretto (solo per poter eseguire), da
`tmp/t8_taglio.py`:

```
maggiore=1 minore=0 invasi=25 invaso[0]=False invaso[-1]=False
giunzioni: [{'maggiore': 1, 'minore': 0, 'accorciamento': 0.0}]
  prisma 0 origine [0. 0. 0.] lunghezza 1600.0
  prisma 1 origine [   0.    0. 1300.] lunghezza 1400.0
min-lunghezza scelto dal test: 1400.0 <1600 ? True
```

La colonna va da z=0 a z=1600, la trave occupa z 1300..1500: l'invasione e' una
**banda centrale**, quindi `invaso[0]` e `invaso[-1]` sono entrambi falsi, si
prende il ramo `else`, `libero[-1]` e' l'ultimo campione (z=1600) e la nuova
lunghezza resta 1600. Accorciamento **0,0**.

Il test passa perche' `min(tagliati, key=lambda p: p.lunghezza)` sceglie la
**trave** (1400), che non e' mai stata tagliata: l'asserzione confronta 1400 con
1600. Nessuna mutazione del taglio la uccide.

**correzione proposta:** geometria in cui l'intersezione tocca davvero
un'estremita' del prisma minore — cioe' il caso che il soffitto dichiara di
coprire — e asserzione sul prisma giusto per indice, non per `min`:

```python
    colonna = hexa.Prisma(..., lunghezza=1400.0)   # finisce DENTRO la trave
    ...
    tagliati, giunzioni = hexa.taglia_giunzioni([colonna, trave])
    assert giunzioni[0]["minore"] == 0
    assert tagliati[0].lunghezza < 1400.0, "la colonna doveva fermarsi sotto la trave"
```

Verificato in `tmp/t8_taglio_fix.py`:

```
giunzioni: [{'maggiore': 1, 'minore': 0, 'accorciamento': 105.5276381909548}]
lunghezze: [1294.4723618090452, 1400.0]
```

**gravita':** BLOCCANTE.

---

### 8.3 Sulla geometria tagliata correttamente le superfici del `*TIE` sono vuote — BLOCCANTE

**dove:** `task-8-brief.md:430-473` (costruzione delle superfici) e `:171`
(`assert modello["ties"], "due membrature che si toccano devono avere un *TIE"`).

**cosa afferma:** «per ogni giunzione, le facce del prisma minore che toccano il
maggiore, e viceversa».

**perche' e' falso:** la tolleranza gonfia il prisma **solo lungo il proprio
asse** (`origine - versore*tolleranza`, `lunghezza + 2*tolleranza`), mai nella
sezione. Dopo il taglio la colonna finisce a z≈1294,5 e la trave comincia a
z=1300: un vuoto di 5,5 mm in una direzione dove nessuna tolleranza e' applicata.
Da `tmp/t8_tie_ccx.py`, geometria con il taglio funzionante:

```
GIUNZIONE_1_D: 0 nodi vicini -> 0 facce
GIUNZIONE_1_I: 40 nodi vicini -> 18 facce
ties: () superfici: {}
accorciamenti: [105.5276381909548]
```

`ties` e' vuota: `assert modello["ties"]` fallisce. Il test del brief passa solo
perche' la sua geometria (8.2) non taglia nulla e i due solidi si compenetrano.
**Le due cose che Task 8 promette — tagliare le giunzioni e legarle con un
`*TIE` — si escludono a vicenda cosi' come sono scritte.**

**correzione proposta:** la tolleranza va nella condizione di appartenenza, non
nella geometria del prisma. Un parametro in `dentro`:

```python
def dentro(prisma, punti, tolleranza: float = 0.0) -> np.ndarray:
    ...
    nel_tratto = (lungo >= -tolleranza) & (lungo <= prisma.lunghezza + tolleranza)
    ...
        dentro_sezione &= verso >= -tolleranza * float(np.linalg.norm(lato))
```

e in `costruisci` si chiama `dentro(tagliati[altro], nodi[inizio:fine], tolleranza)`
al posto del `Prisma` gonfiato a mano. Verificato in `tmp/t8_fix_tolleranza.py`
sulla geometria tagliata:

```
D: nodi entro il prisma altro -- tolleranza 0: 0, tolleranza 66.7: 29
I: nodi entro il prisma altro -- tolleranza 0: 0, tolleranza 66.7: 65
```

**gravita':** BLOCCANTE.

---

### 8.4 Il `*TIE` scritto nel deck non lega nulla, e nessun test lo vede — SERIO

**dove:** `task-8-brief.md:364-373` (docstring di `costruisci`) e `:153-175`
(il test delle superfici).

**cosa afferma:** «il legame e' un `*TIE` fra le superfici a contatto e non una
fusione di nodi».

**perche' e' fragile:** il test verifica soltanto che i **nomi** delle superfici
esistano nel dizionario. Portato il deck fino al solutore (`tmp/t8_tie_ccx2.py`,
geometria del brief, `ccx` reale):

```
card: ['*SURFACE, TYPE=ELEMENT, NAME=GIUNZIONE_1_D',
       '*SURFACE, TYPE=ELEMENT, NAME=GIUNZIONE_1_I',
       '*TIE, NAME=GIUNZIONE_1, ADJUST=NO']
returncode: 0 | *ERROR in stdout: False | telaio.dat esiste: True
righe con 'tie': ['   tie constraints:            1', ... ' *WARNING in gentiedmpc: no tied MPC', ...]
```

CalculiX legge il deck, esce 0, non stampa `*ERROR` — e **non genera alcun MPC
di legame**. Il modello e' due blocchi slegati, e la prosa che dice il contrario
sopravvive perche' nessuno la esegue. E' esattamente la forma del difetto che
questo setaccio cerca.

**correzione proposta:** aggiungere al test un'asserzione sulla **taglia** delle
superfici, non sui soli nomi, e portare il caso `*TIE` dentro il controllo con
il solutore del Task 11 (vedi 11.4), con criterio `"no tied MPC" not in stdout`.

**gravita':** SERIO.

---

### 8.5 La guardia dell'attraversamento rileva il contenimento, non l'attraversamento — SERIO

**dove:** `task-8-brief.md:330-339`.

**cosa afferma:** il commento «se sono invase entrambe [le estremita'] il prisma
minore attraversa il maggiore da parte a parte», e la docstring (`:295-300`) che
dichiara quel caso come il soffitto coperto da un errore esplicito.

**perche' e' falso:** `invaso[0] and invaso[-1]` e' vero quando **entrambe le
estremita' sono dentro**, cioe' quando il prisma minore e' contenuto nel
maggiore. Un prisma che attraversa da parte a parte ha le estremita' **fuori** e
la banda centrale dentro: `invaso[0]=False`, `invaso[-1]=False`. Misurato in
8.2 (`invasi=25 invaso[0]=False invaso[-1]=False`), e l'esito e' un
accorciamento silenzioso di 0,0 — proprio il caso che la docstring dice di non
coprire, e che passa senza un segnale.

**correzione proposta:**

```python
            libero = np.flatnonzero(~invaso)
            if not invaso[0] and not invaso[-1]:
                raise ValueError(
                    "un prisma attraversa un altro da parte a parte: il taglio "
                    "alle giunzioni accorcia lungo l'asse e non sa dividere un "
                    "prisma in due. Verifica la scomposizione."
                )
            if invaso[0] and invaso[-1]:
                raise ValueError(
                    "un prisma e' interamente dentro un altro: la scomposizione "
                    "ha prodotto due regioni sovrapposte, non due membrature"
                )
```

**gravita':** SERIO.

---

### 8.6 Il volume doppio vale 8·10⁶ mm³, non 12·10⁶, e la tolleranza copre l'errore — SERIO

**dove:** `task-8-brief.md:147-150`.

**cosa afferma:** `doppio = 200.0 * 200.0 * 300.0` e `rel=0.15`.

**perche' e' falso:** la sovrapposizione vera e' x∈[0,200] ∩ y∈[0,200] ∩
z∈[1300,1500] = 200·200·200 = **8 000 000 mm³**, non 12 000 000. Il 300 e' la
larghezza della trave in y, ma la colonna e' larga 200: la trave sporge, la
colonna no. Da `tmp/t8_taglio.py`:

```
somma 148000000.0 atteso 136000000.0 rel err 0.0882 passa rel=0.15? True
sovrapposizione vera (mm^3): 8000000.0
```

Con `rel=0.15` (± 20,4·10⁶) l'intervallo copre sia il caso «tagliato» sia il
caso «non tagliato»: il numero atteso e' sbagliato, la tolleranza e' scelta a
intuito, e insieme rendono il controllo cieco.

**correzione proposta:** con la geometria corretta di 8.2 (colonna 1400, che si
ferma sotto la trave) il valore atteso e' un prodotto di dimensioni senza alcuna
sottrazione, e la tolleranza discende dal campionamento:

```python
    # nessun doppio conteggio: la colonna si ferma dove comincia la trave.
    # La tolleranza e' il passo di campionamento dell'asse, 1400/199 = 7,04 mm
    # su una colonna di 1300: lo 0,54%.
    assert somma == pytest.approx(200.0 * 200.0 * 1300.0 + 300.0 * 200.0 * 1400.0, rel=0.01)
```

Misurato: `somma 135778894.47 atteso 136000000.0 rel 0.0016`.

**gravita':** SERIO.

---

### 8.7 «La superficie piu' fitta fa da dipendente» non discende dall'ordine per area — SERIO

**dove:** `task-8-brief.md:430-433`.

**cosa afferma:** «Il dipendente e' il minore, che e' la convenzione dei
solutori -- la superficie piu' fitta fa da dipendente».

**perche' e' falso:** «minore» e' deciso dall'**area** della sezione
(`taglia_giunzioni`), mentre la finezza della mesh e' decisa dall'**estensione
minima** (`passo_di_mesh` = min(target_size, min(ptp)/min_layers)). Le due cose
non hanno lo stesso ordine. Da `tmp/t8_fitta.py`:

```
A area 10000.0 passo 3.3333333333333335     (sezione 1000 x 10)
B area 8100.0  passo 30.0                   (sezione 90 x 90)
maggiore per area: A
mesh piu' fitta (passo minore): A
```

A e' il **maggiore** e ha la mesh **piu' fitta**: il codice ne farebbe
l'indipendente, cioe' l'opposto della convenzione che il commento dichiara di
seguire.

**correzione proposta:** o si sceglie il dipendente dal passo di mesh
(`blocchi[i]["passo"]`, gia' disponibile in `costruisci`), oppure il commento
dice la verita':

```python
    # Il dipendente e' il prisma di sezione minore. Non e' la regola «la
    # superficie piu' fitta fa da dipendente»: l'ordine per area e quello per
    # passo di mesh non coincidono (una sezione 1000x10 ha area maggiore di una
    # 90x90 e passo sei volte piu' fine). E' una scelta di determinismo, non di
    # convergenza numerica; la via d'aggiornamento e' ordinare per blocco["passo"].
```

**gravita':** SERIO.

---

### 8.8 Il Requisito cita `cfg.density_dispersion_limit` su un `ModelConfig` che non ce l'ha — MINORE

**dove:** `task-8-brief.md:16`.

**cosa afferma:** «`costruisci` **non puo' costruire** su una membratura con
`riempimento_stato == "vuoto"` e `densita_dispersione <= cfg.density_dispersion_limit`».

**perche' e' falso:** `costruisci` riceve un `ModelConfig`, che non ha quel
campo — il campo sta in `WallConfig`:

```
$ uv run python -c "from meshrec.core.config import ModelConfig; print(sorted(ModelConfig.model_fields))"
['element', 'lateral_nset', 'lateral_pressure', 'min_layers', 'target_size', 'tie_name_prefix']
```

Il codice dello Step 4 (righe 382-395) fa la cosa giusta — controlla il solo
stato — e la sua motivazione e' **verificata vera**: `wall.py:501-506` mette
`non_verificabile` proprio quando `densita_dispersione > cfg.density_dispersion_limit`,
quindi `vuoto` implica gia' la misura affidabile. Sbagliata e' solo la riga 16
del Requisito, che manderebbe l'implementatore a cercare un attributo inesistente.

**correzione proposta:** riga 16 → «...con `riempimento_stato == "vuoto"`. Lo
stato basta da solo: `wall.misura` mette «vuoto» solo quando la dispersione
della densita' e' entro `WallConfig.density_dispersion_limit`, e degrada a
«non_verificabile» appena non lo e' (`wall.py:501`). Nessuna soglia da rileggere
in `costruisci`, che riceve un `ModelConfig` e non ne ha una.»

**gravita':** MINORE (il codice e' giusto; e' la prosa a mentire).

---

### 8.9 «PASS su tutti e dieci» — sono quindici — MINORE

**dove:** `task-8-brief.md:500`.

**perche' e' falso:** `grep -c "^def test" tests/test_hexa.py` → **8**. Il brief
ne aggiunge 7. 8 + 7 = 15.

**correzione proposta:** «Expected: PASS su tutti e quindici (otto gia' presenti
piu' i sette di questo task).»

**gravita':** MINORE.

---

### 8.10 Il filtro `-k` dello Step 2 contiene una parola che non seleziona nulla — MINORE

**dove:** `task-8-brief.md:180`.

**cosa afferma:** `-k "primitive or appartenenza or giunzion or telaio"`.

**perche' e' falso:** nessuno dei sette test nuovi ha «giunzion» nel nome (il
test del taglio si chiama `test_due_prismi_che_si_compenetrano_vengono_tagliati_e_il_volume_torna`).
Il filtro seleziona 4 test su 7 e lascia fuori proprio quello del taglio.

**correzione proposta:** `-k "primitive or appartenenza or compenetrano or telaio or membratura"`.

**gravita':** MINORE.

---

### 8.11 `test_il_modello_primitive_conserva_le_dimensioni_misurate` sopravvive alla mutazione — MINORE

**dove:** `task-8-brief.md:96-107`.

**cosa afferma:** «raddrizzare non vuol dire inventare».

**perche' e' fragile:** la sezione del banco e' **gia'** il rettangolo
`[[0,0],[250,0],[250,175],[0,175]]`. Un `prisma_di(..., "primitive")` mutato per
restituire il contorno tal quale supera il test. Verificato in `tmp/t8_approx.py`:

```
mutante (contorno tal quale) supera il test conserva-dimensioni: True
```

**correzione proposta:** usare una sezione irregolare con lo stesso ingombro,
come fa il test precedente:

```python
    sezione = np.array([[0.0, 0.0], [250.0, 6.0], [246.0, 175.0], [4.0, 169.0]])
    ...
    assert np.ptp(primitive.contorno, axis=0) == pytest.approx([250.0, 175.0])
    assert primitive.contorno != pytest.approx(sezione)  # non e' una copia
```

**gravita':** MINORE.

---

### 8.12 `metriche["giunzioni"] == len(ties)` rilegge il valore appena scritto — MINORE

**dove:** `task-8-brief.md:175`.

**perche' e' fragile:** in `costruisci` (riga 483) `"giunzioni"` **e'**
`len(ties)`. L'asserzione non puo' fallire.

**correzione proposta:** ancorarla al dato: `assert modello["metriche"]["giunzioni"] == 1`
sulla geometria di due membrature che si incontrano una volta sola.

**gravita':** MINORE.

---

*Nota verificata **vera**, non un rilievo:* la docstring di `Prisma` dice «Il
contorno e' convesso perche' viene da `wall.semplifica_contorno`». Vero:
`wall.py:310-313` prende l'inviluppo convesso di scipy, e la riduzione
successiva toglie vertici da un poligono convesso, che resta convesso.
Verificato anche `pytest.approx` contro `np.ndarray` (`tmp/t8_approx.py`:
`ndarray == approx(ndarray): True`) e la corrispondenza dei campi di
`_membratura_finta` con `wall.Membratura`.

---

## Task 9 — `task-9-brief.md`

### 9.1 `stato["steps"]["12"]["stato"]` non e' la forma di `steps.json` — BLOCCANTE

**dove:** `task-9-brief.md:29-30`.

**cosa afferma:**

```python
    stato = steps.read_state(cfg.run.out_dir)
    assert stato["steps"]["12"]["stato"] == "riuscito"
```

**perche' e' falso:** `steps.write_state` (`steps.py:113`) scrive
`salvato[STEP_KEYS[numero - 1]] = {"impronta", "esito", "artefatto", "secondi"}`
alla radice del documento. Nessuna chiave `"steps"`, nessun campo `"stato"`.
Prova sul file vero:

```
$ head -8 runs/default/steps.json
{
  "01_load": {
    "impronta": "22b2b799...",
    "esito": "fallito",
```

e il test gia' verde nel repository usa la forma giusta
(`tests/test_pipeline.py:299`): `assert salvato["03_downsample"]["esito"] == "fallito"`.

**correzione proposta:**

```python
    stato = steps.read_state(cfg.run.out_dir)
    assert stato["12_wall"]["esito"] == "riuscito"
```

**gravita':** BLOCCANTE (KeyError).

---

### 9.2 `completa = start == 1 and stop == 12` disfa una decisione documentata — SERIO

**dove:** `task-9-brief.md:125-129`.

**cosa afferma:** «Aggiorna infine la condizione di corsa completa».

**perche' e' falso:** la condizione oggi non e' quella. `pipeline.py:287` dice
`completa = start == 1 and pipeline_completa`, e il commento che la accompagna
(`pipeline.py:115-119`) **anticipa per nome proprio questo task**:

> `# Vero solo se il flusso ha attraversato per intero l'ultimo step che questa versione di run() implementa (oggi 11_export, domani 12_wall): si aggiorna da solo spostandosi con la riga che lo mette a True, senza un numero da tenere sincronizzato a mano con cfg.run.to_step altrove.`

La modifica chiesta rimette esattamente il numero a mano che quel commento dice
di aver tolto, e lascia `pipeline_completa` assegnata e mai letta.

**correzione proposta:** non toccare la riga 287. Spostare invece
`pipeline_completa = True` **dopo** il nuovo blocco 12:

```python
        in_corso = 12
        avvio = time.monotonic()
        metrics["12_wall"] = calcola_prior(out, cfg, source_cloud, spacing)
        registra(12, avvio, WALL_FILENAME)
        pipeline_completa = True
```

togliendola da dove sta oggi (dopo `registra(11, ...)`), e aggiornare il
commento delle righe 115-119 da «oggi 11_export, domani 12_wall» a «oggi
12_wall».

**gravita':** SERIO.

---

### 9.3 Il punto d'inserimento lascia `pipeline_completa = True` prima dello step 12 — SERIO

**dove:** `task-9-brief.md:77` («subito dopo il blocco dello step 11 e prima
dell'`except _FermataRichiesta`») insieme a `:80-81` (`if stop <= 11: raise _FermataRichiesta`).

**perche' e' fragile:** il blocco dello step 11 finisce con `registra(11, ...)`
seguito da `pipeline_completa = True` (`pipeline.py:263-264`). Inserendo li' il
codice del brief, una corsa con `to_step=11` esce con `pipeline_completa` vero
pur non avendo eseguito lo step 12 — e con la riga 9.2 messa come chiede il
brief, la stessa corsa smette di essere «completa» e passa dal ramo di fusione
delle metriche invece che da quello autoritativo (`metrics.json` sostituito).
E' un cambio di comportamento sulle corse di sweep che il brief non dichiara.

**correzione proposta:** vedi 9.2. Il testo del punto d'inserimento diventa:
«subito dopo `registra(11, ...)` e **prima** di `pipeline_completa = True`, che
si sposta in fondo al nuovo blocco».

**gravita':** SERIO.

---

### 9.4 Lo Step 4 nomina un test che non esiste e tace quello che si rompe — SERIO

**dove:** `task-9-brief.md:134`.

**cosa afferma:** «Se un test preesistente attendeva `to_step` predefinito 11,
aggiornalo a 12».

**perche' e' falso:** il predefinito **e' gia' 12** (`config.py:260-263`:
`to_step: int = Field(default=12, ge=1, le=12)`), quindi nessun test puo'
attendersi 11. Il test che si rompe davvero e' un altro,
`tests/test_pipeline.py:238`:

```python
def test_una_corsa_completa_lascia_gli_undici_step_validi(tmp_path):
    ...
    assert set(per_numero.values()) == {"valido", "mai eseguito"}
    assert per_numero[12] == "mai eseguito"
```

Dopo il Task 9 lo step 12 diventa «valido» e le due asserzioni cadono entrambe.

**correzione proposta:** riga 134 → «Il test `test_una_corsa_completa_lascia_gli_undici_step_validi`
(`tests/test_pipeline.py:238`) va riscritto: dopo questo task una corsa intera
lascia **dodici** step validi. Rinominalo `..._lascia_i_dodici_step_validi`,
sostituisci le asserzioni con `assert set(per_numero.values()) == {"valido"}` e
togli la docstring che spiega perche' il dodicesimo era «mai eseguito». Il
predefinito di `to_step` e' gia' 12 dal Task 1 e non va toccato.»

**gravita':** SERIO.

---

### 9.5 `_config_di_prova` non esiste, e in `test_cli.py` mancano quattro nomi — SERIO

**dove:** `task-9-brief.md:140-170` (Step 5), e `:62` per il file dei test della
pipeline.

**cosa afferma:** lo Step 1 mette le mani avanti («se ha un altro nome usa
quello»); lo Step 5 no, e usa `_config_di_prova`, `save_config`, `RunConfig`,
`pipeline`, `Path`.

**perche' e' falso:** in `tests/test_cli.py` nessuno di quei cinque nomi e'
definito o importato. Il file importa `from meshrec.core import config, io, synth`
e usa `config.RunConfig`, `config.save_config`; l'aiuto locale si chiama
`_config_cubo_su_disco(tmp_path)` e **restituisce il percorso del yaml**, non la
configurazione. `grep -n "_config_di_prova" tests/test_cli.py tests/test_pipeline.py`
non trova nulla; `grep -n "Path" tests/test_pipeline.py` non trova nulla.

**correzione proposta:** dichiararlo una volta in testa a entrambi gli Step:
«In questo file l'aiuto e' `_config_cubo_su_disco(tmp_path)`, che restituisce il
**percorso** del `config.yaml` gia' scritto; ricava `cfg` con
`load_config(percorso)`. Aggiungi `from pathlib import Path` e
`from meshrec.core import pipeline` agli import di `tests/test_cli.py`, e
`from pathlib import Path` a quelli di `tests/test_pipeline.py`
(`cfg.run.out_dir` e' gia' un `Path`: l'avvolgimento in `Path(...)` si puo'
anche togliere).»

**gravita':** SERIO.

---

### 9.6 Dopo il Task 9 tre affermazioni nel codice diventano false, e nessuno le aggiorna — MINORE

**dove:** effetto del Task 9 su file che il brief non elenca.

**cosa afferma (nel codice, non nel brief):**
- `steps.py:19-21`: «Fino al Task 9, pipeline.run scrive solo le prime undici: is_complete() in sweep.py lo sa e non richiede "12_wall" a un candidato»;
- `steps.py:106`: «sono undici voci»;
- `steps.py:128`: «Stato dei undici step».

**perche' diventa falso:** dopo il Task 9 `pipeline.run` scrive dodici voci.
`sweep.py:130` (`REQUIRED_STEPS = tuple(c for c in STEP_KEYS if c != "12_wall")`)
resta com'e', il che e' forse giusto ma va **deciso e scritto**, non ereditato:
da questo task in poi ogni candidato di sweep paga anche il calcolo del prior,
perche' `to_step` vale 12 di predefinito. Le altre due docstring erano gia'
false dal Task 1 (STEP_KEYS ha dodici voci).

**correzione proposta:** aggiungere allo Step 3 del brief: «Aggiorna
`steps.py:17-21` («Fino al Task 9...» diventa la ragione per cui `is_complete`
continua a non richiedere `12_wall`: un candidato di sweep e' confrontabile
sulle sole undici metriche di elaborazione) e le due docstring che dicono
«undici». Dichiara nel documento del Task 15 che dopo questo task ogni candidato
di sweep calcola anche il prior.»

**gravita':** MINORE.

---

*Verificato **vero** in questo task:* `pipeline.ARTIFACTS[2] == "02_segmented.ply"`
(quindi l'asserzione sullo stderr del comando `wall` regge); `source_cloud` e
`spacing` esistono nell'ambito in cui il blocco 12 va inserito; `io.scrivi_atomico`,
`io.read_cloud`, `io.mean_spacing`, `wall.prior(points, cfg_segment, cfg, spacing)`
hanno tutti la firma usata; `wall.prior` restituisce davvero `regioni_trovate` e
`membrature`; `cli.py` ha gia' `json`, `sys`, `Path`, `pipeline`, `load_config` a
livello di modulo e **non** ha `io`, quindi l'import locale e' giusto;
`report_command` e il ramo `serve` esistono dove il brief dice.

---

## Task 10 — `task-10-brief.md`

### 10.1 La `Membratura` ricostruita manca di tre campi obbligatori — BLOCCANTE

**dove:** `task-10-brief.md:118-134`.

**cosa afferma:** la ricostruzione delle membrature dal `12_wall.json`.

**perche' e' falso:** `wall.Membratura` ha quindici campi obbligatori; il brief
ne passa dodici. Da `tmp/t10_membratura.py`:

```
TypeError: Membratura.__init__() missing 3 required positional arguments:
'riempimento_sezione', 'riempimento_stato', and 'densita_dispersione'
```

E non e' un dettaglio meccanico: `riempimento_stato` e' **il campo su cui poggia
l'unica guardia del Ruling J** (Task 8, righe 391-395). Costruita cosi', la
`Membratura` non arriva nemmeno alla guardia; ricostruita senza quel campo, la
guardia diventa muta. Nel JSON il dato c'e', ma annidato:
`wall.prior` scrive `"riempimento": riempimento(m, cfg)`, cioe' un dizionario
con `stato`, `valore`, `densita_dispersione` (`wall.py:638-646`).

**correzione proposta:**

```python
            rigonfiamento=np.zeros(0),
            volume=float(voce["volume"]),
            # il riempimento nel JSON e' il dizionario che wall.riempimento
            # scrive, non tre campi piatti: e' da li' che viene lo stato su cui
            # la guardia del Ruling J rifiuta una regione a Pi.
            riempimento_sezione=float(voce["riempimento"]["valore"]),
            riempimento_stato=str(voce["riempimento"]["stato"]),
            densita_dispersione=float(voce["riempimento"]["densita_dispersione"]),
```

**gravita':** BLOCCANTE.

---

### 10.2 `scostamento_nuvola` non viene scritto da nessuno, e il Task 12 lo legge — BLOCCANTE

**dove:** `task-10-brief.md:162-176` (il dizionario `esito`) contro
`task-12-brief.md:269`.

**cosa afferma:** implicitamente, che `modello.json` contenga tutto cio' che il
confronto legge.

**perche' e' falso:** il Task 12 legge `voce["modello"].get("scostamento_nuvola")`
e dichiara quella grandezza «il perno» del confronto
(`task-12-brief.md:185-187`). Il dizionario del Task 10 ha le chiavi `tipo`,
`sorgente`, `modello`, `blocchi`, `hexa`, `export`, `nota_giunzioni`,
`nota_armatura`: **`scostamento_nuvola` non c'e'**. Verificato eseguendo il
codice dei due task (`tmp/t12_confronto.py`):

```
scostamento_nuvola: {'as-built': 4.9, 'estruso': None, 'primitive': None}
```

Nessun test dei due brief se ne accorge, perche' il banco finto del Task 12
riproduce fedelmente il `modello.json` **senza** quella chiave.

**correzione proposta:** nel Task 10, calcolarlo dove i dati ci sono — la
funzione e' gia' scritta e il brief del Task 12 la dichiara pure fra le proprie
dipendenze (`quality.vertex_deviation`, `quality.py:439`):

```python
    # Lo scostamento dalla nuvola sorgente e' il perno del confronto (Task 12):
    # e' definito allo stesso modo per i tre modelli. Si misura qui, dove la
    # nuvola segmentata della madre e i nodi del modello sono entrambi a
    # portata; il confronto non ricalcola nulla.
    sorgente_nuvola, _ = io.read_cloud(sorgente / ARTIFACTS[2])
    scarti = quality.vertex_deviation(nodi, sorgente_nuvola)
    esito["scostamento_nuvola"] = {
        "rms": float(np.sqrt(np.mean(scarti ** 2))),
        "max": float(scarti.max()),
        "nota": "distanza punto-nuvola nei soli nodi: sottostima dove gli "
                "elementi sono grandi, come dichiara quality.vertex_deviation",
    }
```

e nel Task 12 leggere `.get("scostamento_nuvola", {}).get("rms")`, allineando il
banco finto.

**gravita':** BLOCCANTE.

---

### 10.3 `"*C3D4" not in testo` non puo' fallire, e il test non guarda le superfici che ha nel nome — SERIO

**dove:** `task-10-brief.md:38-47`,
`test_il_deck_della_corsa_figlia_e_esaedrico_e_porta_le_superfici`.

**cosa afferma:** `assert "*C3D4" not in testo`.

**perche' e' fragile:** `abaqus.write_inp` scrive il tipo solo come
`*ELEMENT, TYPE={element_type}` (`abaqus.py:103`). La stringa `*C3D4`, con
l'asterisco attaccato, non compare **in nessun deck**, nemmeno in uno
tetraedrico: nessuna mutazione la fa apparire. E il test che si chiama «porta le
superfici» non asserisce nulla su `*SURFACE` ne' su `*TIE`. Peggio: verificato
che il banco della corsa figlia (il cubo sintetico) produce **una sola**
membratura —

```
$ uv run python tmp/t10_prior_cubo.py
regioni_trovate: 1
membrature accettate: 1
  sezione [60.0, 120.0] lunghezza 240.0 riempimento pieno
```

— quindi zero giunzioni e zero superfici: su questo banco il test non potrebbe
mai vederle.

**correzione proposta:** togliere l'asserzione impossibile, sostituirla con una
mutabile, e portare le superfici su un banco che le abbia (il telaio sintetico
`synth.sample_frame_surface`, gia' usato in `tests/test_wall.py:49`):

```python
    assert "*ELEMENT, TYPE=C3D8I" in testo
    assert "TYPE=C3D4" not in testo
    assert testo.count("*NODE") == 1
```

e un secondo test, sul telaio, che asserisce `"*SURFACE, TYPE=ELEMENT"` e
`"*TIE"` nel deck.

**gravita':** SERIO.

---

### 10.4 Il Task 10 rende falsa una docstring di `quality.py` e non lo dice — SERIO

**dove:** effetto del Task 10 su `src/meshrec/core/quality.py:139-141`.

**cosa afferma (nel codice):** «Oggi la funzione [`hexa_metrics`] non ha ancora
chiamanti: questa riga e' il vincolo che li aspetta, non il resoconto di cio'
che fanno.»

**perche' diventa falso:** `genera_modello` e' il primo chiamante. Verificato
che oggi non ce ne sono in `src/`:

```
$ grep -rn "hexa_metrics" src/ tests/ | grep -v "def hexa_metrics"
tests/test_quality.py:604:    metriche = quality.hexa_metrics(nodi, esaedri)
tests/test_quality.py:615:    metriche = quality.hexa_metrics(_CUBO_NODI, _CUBO_HEX)
```

E' la stessa forma del difetto gia' pagato in questa fase con la docstring di
`report.py`: una frase al presente su chi chiama che cosa, vera quando e' stata
scritta e falsa dal task dopo.

**correzione proposta:** aggiungere allo Step 3: «Aggiorna la docstring di
`quality.hexa_metrics`: da questo task ha un chiamante, `pipeline.genera_modello`,
e il vincolo delle due colonne separate diventa un obbligo per il Task 12 invece
che un'attesa. Sostituisci «Oggi la funzione non ha ancora chiamanti» con «Il
suo unico chiamante e' `pipeline.genera_modello`; il confronto del Task 12 legge
il risultato da `modello.json`.»»

**gravita':** SERIO.

---

### 10.5 Gli stessi nomi mancanti dei test — MINORE

**dove:** `task-10-brief.md:23, 56, 58, 63-64, 69, 263-273`.

**perche' e' falso:** `_config_di_prova`, `Path`, `RunConfig`, `load_config`,
`save_config` non sono definiti ne' importati in `tests/test_pipeline.py` /
`tests/test_cli.py`. Vedi 9.5 per la verifica.

**correzione proposta:** come in 9.5. `from meshrec.core.sweep import fingerprint`
va invece verificato a parte: e' l'unico import del blocco che il brief scrive
per esteso.

**gravita':** MINORE.

---

*Verificato **vero** in questo task:* `abaqus.surface_area(aligned, elements, coppie, tipo)`
usa esattamente i nomi delle variabili locali di `export_model` (`aligned`,
`elements`, `tipo`) e la firma combacia; `abaqus.boundary_faces` gestisce gli
esaedri a 8 colonne; `NODI_PER_ELEMENTO` contiene `C3D8I`; `quality.hexa_metrics`
restituisce davvero `hexes` e `inverted`; `quality` e `np` sono gia' importati in
`pipeline.py`; il calcolo di `"primo_elemento"` con `elementi_totali[:-1]` e'
corretto; `write_inp` valida gia' i `ties` contro le superfici dichiarate.

---

## Task 11 — `task-11-brief.md`

### 11.1 `ccx` **e'** installato: la premessa del task e la formula da scrivere sono false — SERIO

**dove:** `task-11-brief.md:24-25`, `:90`, e per riflesso `task-15-brief.md:138`
e `:170`.

**cosa afferma:** «salta dove `ccx` non e' installato -- che e' il caso della
macchina di sviluppo al 18/08/2026»; «Expected: due test, **saltati** se `ccx`
non e' installato (e' il caso al 18/08/2026 sulla macchina di sviluppo:
`which ccx` non risponde)»; e allo Step 3, la formula da riportare nel documento
del Task 15: «il deck esaedrico non e' stato verificato da alcun solutore su
questa macchina, perche' `ccx` non e' installato».

**perche' e' falso:**

```
$ which ccx
/Users/mario/.local/bin/ccx
```

Ed eseguendo il controllo per intero (`tmp/t11_ccx.py`, che riproduce
esattamente `_deck` e il corpo del test):

```
ccx: /Users/mario/.local/bin/ccx
--- con_carico=False
  hexes=240 nodes=377 passo=33.33 strati=12
  base=29 cima=29 lato=65 facce LATO=48
  returncode: 0 | *ERROR in stdout: False | modello.dat esiste: True
--- con_carico=True
  ... returncode: 0 | *ERROR in stdout: False | modello.dat esiste: True
```

Il controllo **passa davvero**, in entrambe le parametrizzazioni. Scrivere nel
documento del Task 15 che il deck non e' stato verificato da alcun solutore
sarebbe falso quanto scrivere «il deck e' valido»: e' un esito reale, e va
riportato come tale.

**correzione proposta:** riga 24-25 → «Marcato feasibility come gli altri
controlli di dipendenza esterna. `ccx` **e' presente** su questa macchina
(`/Users/mario/.local/bin/ccx`, verificato il 20/08/2026), quindi il controllo
gira e non salta. Il ramo di skip resta per le macchine che non ce l'hanno, e
allora vale la regola: **un controllo saltato non e' un controllo passato**.»
Riga 90 → «Expected: due test **passati**.» Step 3 → «Riporta l'esito misurato:
versione di `ccx`, codice di uscita, esistenza di `modello.dat`. La formula
«non verificato da alcun solutore» si usa solo se il controllo e' stato
saltato — e su questa macchina non lo e'.»

**gravita':** SERIO (porterebbe una falsita' dentro il documento di esito, che e'
il prodotto della fase).

---

### 11.2 `from materiale import MATERIALE` non risolve col comando dello Step 2 — SERIO

**dove:** `task-11-brief.md:37` e `:89`.

**perche' e' falso:** non esiste alcun `conftest.py` nel progetto
(`find . -name conftest.py -not -path "./.venv/*"` → nessun risultato) e
`pyproject.toml` non dichiara `pythonpath`. pytest inserisce in `sys.path` la
**cartella del file di test**, e `tests/feasibility/` non contiene `materiale.py`
(che sta in `tests/`). Verificato con un file sonda fuori dal repository:

```
$ uv run pytest /Users/mario/.claude/jobs/e87eb542/tmp/probe/test_probe.py -s -q -o addopts=""
SYSPATH0: /Users/mario/.claude/jobs/e87eb542/tmp/probe
materiale FAIL: ModuleNotFoundError No module named 'materiale'
```

Nessun test gia' presente in `tests/feasibility/` importa `materiale`
(`grep -rn "materiale import" tests/feasibility/` → vuoto). Eseguendo la suite
intera l'import funziona per caso, perche' la collezione di `tests/*.py` ha gia'
messo `tests/` in `sys.path`; eseguendo il **comando che il brief prescrive**,
no.

**correzione proposta:** o si definisce il materiale nel file stesso (e' un
controllo di fattibilita', tre valori bastano), oppure si dichiara la dipendenza:

```python
import sys
from pathlib import Path

# tests/ non e' sulla via di ricerca quando pytest colleziona il solo file di
# feasibility: la sua cartella e' tests/feasibility/. Senza questa riga il
# comando dello Step 2 fallisce in collezione, mentre la suite intera passa.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from materiale import MATERIALE
```

**gravita':** SERIO.

---

### 11.3 «`*ERROR` non compare» non vede le card che CalculiX ignora in silenzio — SERIO

**dove:** `task-11-brief.md:83`.

**cosa afferma:** `assert "*ERROR" not in processo.stdout`.

**perche' e' fragile:** CalculiX segnala con `*WARNING` — e prosegue — le card
che non riconosce e i vincoli che non riesce a generare. Sul deck di questo
progetto, misurato in `tmp/t8_tie_ccx2.py`:

```
righe con '*WARNING': [' *WARNING reading *STEP: parameter not recognized:',
                       ' *WARNING reading *OUTPUT:',
                       ' *WARNING in gentiedmpc: no tied MPC', ...]
```

`NAME=` su `*STEP` e la card `*OUTPUT, FIELD` vengono scartate, e il criterio
del test resta verde. La forma «il solutore non si e' lamentato» non e' la stessa
di «il solutore ha letto quello che c'era scritto».

**correzione proposta:** aggiungere una terza asserzione che dichiara quali
avvisi sono attesi, cosi' che uno nuovo si veda:

```python
    ATTESI = ("reading *STEP", "reading *OUTPUT")
    inattesi = [r for r in processo.stdout.splitlines()
                if "*WARNING" in r and not any(a in r for a in ATTESI)]
    assert not inattesi, "\n".join(inattesi)
```

**gravita':** SERIO.

---

### 11.4 Il controllo col solutore non prova la card nuova piu' rischiosa, il `*TIE` — SERIO

**dove:** `task-11-brief.md:9` («Consumes: `hexa.mesh_prisma`, `abaqus.write_inp`
e `abaqus.element_surface`») e l'assenza di un caso `*TIE` nel file.

**perche' e' un vuoto:** l'intero Task 8 poggia sul fatto che un `*TIE` fra
superfici a contatto leghi due blocchi. Misurato: **non lo fa**. Vedi 8.4,
`*WARNING in gentiedmpc: no tied MPC` con `returncode 0`. Questo e' l'unico
punto del piano in cui un solutore vero tocca il deck, ed e' l'unico posto in
cui quel difetto poteva essere trovato prima del Task 15.

**correzione proposta:** aggiungere un terzo caso al file:

```python
def test_calculix_lega_davvero_due_blocchi_con_un_tie(tmp_path):
    """Un *TIE che il solutore accetta senza generare alcun MPC lascia due
    blocchi slegati, con codice di uscita 0 e nessun *ERROR: e' la forma di
    errore che questo controllo esiste per prendere."""
    ...
    assert "no tied MPC" not in processo.stdout, processo.stdout[-2000:]
```

**gravita':** SERIO.

---

*Verificato **vero** in questo task:* `abaqus.element_surface(esaedri, lato, "C3D8I")`
ha la firma giusta; `write_inp` accetta `node_sets={"BASE": ..., "TOP": ...}` con
`fixed_nset` predefinito `"BASE"`; `pytestmark = pytest.mark.feasibility` con
`-m feasibility` sulla riga di comando prevale su `addopts = "-m 'not feasibility'"`;
i tre insiemi di nodi (`base`, `cima`, `lato`) non sono vuoti e la superficie
`LATO` ha 48 facce.

---

## Task 12 — `task-12-brief.md`

### 12.1 `write_comparison_report` solleva `TypeError` su ogni insieme che contenga un modello parametrico — BLOCCANTE

**dove:** `task-12-brief.md:301-306`.

**cosa afferma:** `_numero(confronto[grandezza][nome]) if nome in confronto[grandezza] else 'non generato'`.

**perche' e' falso:** la guardia distingue **chiave assente** da chiave presente,
ma per un modello parametrico la chiave `scostamento_nuvola` **c'e'** e vale
`None` (vedi 10.2). `report._numero` (`report.py:267`) comincia con
`math.isnan(valore)`, che su `None` solleva. Eseguito il codice dei due Step
sul banco finto del brief (`tmp/t12_confronto.py`):

```
scostamento_nuvola: {'as-built': 4.9, 'estruso': None, 'primitive': None}
  tre: TypeError: must be real number, not NoneType
  due: TypeError: must be real number, not NoneType
  uno: OK, 'non generato' presente: True
```

Tre dei cinque test del Task 12 (`..._con_due_modelli_su_tre`,
`..._dichiara_le_tre_cose`, e il test del comando `compare` allo Step 7) cadono
per questa via.

**correzione proposta:** usare `_testo`, che gia' sa che cosa fare di un `None`
(`report.py:287-296`, `None` → `NON_IMPOSTATO`), e riservare `_numero` ai numeri:

```python
        celle = "".join(
            f"<td>{'non generato' if nome not in confronto[grandezza] else _testo(confronto[grandezza][nome])}</td>"
            for nome in MODELLI
        )
```

Va comunque risolto prima 10.2: la casella «non impostato» al posto del perno
del confronto e' una resa corretta di un dato che non dovrebbe mancare.

**gravita':** BLOCCANTE.

---

### 12.2 `quality.vertex_deviation` e' dichiarato fra le dipendenze e non viene mai chiamato — BLOCCANTE

**dove:** `task-12-brief.md:9` contro tutto il codice degli Step 3 e 4.

**cosa afferma:** «Consumes: ... `quality.vertex_deviation` (Fase 3)».

**perche' e' falso:** la stringa `vertex_deviation` non compare in nessuna riga
di codice del brief. E' la funzione che avrebbe prodotto lo `scostamento_nuvola`
dei modelli parametrici, cioe' la grandezza che il brief stesso chiama «il perno»
(`:185-187`) e dichiara confrontabile (`CONFRONTABILI["scostamento_nuvola"] = True`).
Il risultato e' una colonna dichiarata confrontabile e vuota, e un banco di prova
costruito per non accorgersene.

**correzione proposta:** vedi 10.2 — il calcolo va nel Task 10, dove i nodi e la
nuvola sorgente sono entrambi a portata; il Task 12 lo legge e basta, come dice
di fare («Non ricalcola nulla»). E il banco `_tre_cartelle_finte` deve scrivere
la chiave, cosi' che il test la veda mancare se qualcuno la toglie:

```python
                    "scostamento_nuvola": {"rms": 6.2, "max": 21.0, "nota": ""},
```

con un'asserzione nel primo test:
`assert confronto["scostamento_nuvola"]["estruso"] is not None`.

**gravita':** BLOCCANTE.

---

### 12.3 La colonna dei tetraedri si chiama `min_ratio` ma contiene il rapporto raggio-spigolo — SERIO

**dove:** `task-12-brief.md:263`, `:44`, `:190`.

**cosa afferma:** `qualita[nome] = {"min_ratio": volumi.get("radius_edge_ratio")}`,
il test `assert "min_ratio" in qualita["as-built"]`, e la docstring «min_ratio
per i tetraedri, Jacobiano scalato per gli esaedri».

**perche' e' falso:** `quality.volume_metrics` non ha alcuna chiave `min_ratio`:

```
$ grep -n "def volume_metrics" -A 12 src/meshrec/core/quality.py
        "min_dihedral_deg": ..., "aspect_ratio": ...,
        "radius_edge_ratio": _distribution(radius_edge_ratios(nodes, tets)),
        "radius_edge_over_reference": ..., "reference_ratio": ...,
```

`min_ratio` in questo progetto e' un **ingresso** di TetGen (`cfg.tet.min_ratio`,
il vincolo chiesto), non una misura. Chiamare cosi' la distribuzione misurata
mette nella tabella di confronto un nome che significa un'altra cosa altrove nel
codice, ed e' proprio l'errore che il resto del task esiste per evitare.

**correzione proposta:** usare il nome vero ovunque — nel codice, nella
docstring di `CONFRONTABILI` e nei due test:

```python
            qualita[nome] = {"radius_edge_ratio": volumi.get("radius_edge_ratio")}
```

```python
- qualita' degli elementi: NO. Rapporto raggio-spigolo per i tetraedri
  (`radius_edge_ratio`, la misura; `tet.min_ratio` e' invece il vincolo chiesto
  a TetGen), Jacobiano scalato per gli esaedri: due colonne separate.
```

**gravita':** SERIO.

---

### 12.4 Due asserzioni che non possono fallire — MINORE

**dove:** `task-12-brief.md:47` e `:30-33`.

**cosa afferma:** `assert "differenza" not in qualita`; e le quattro asserzioni
`confronto["confrontabili"][...] is True/False`.

**perche' e' fragile:** `qualita` e' un dizionario indicizzato per nome di
modello: «differenza» non potrebbe esserci nemmeno se qualcuno calcolasse una
differenza, perche' finirebbe **dentro** una delle voci. E le quattro asserzioni
su `confrontabili` rileggono la costante `CONFRONTABILI` che il codice ha appena
copiato: nessuna mutazione del **calcolo** le uccide, solo la modifica della
costante stessa.

**correzione proposta:** per la prima, cercare la differenza dove finirebbe
davvero:

```python
    for colonna in qualita.values():
        assert not (set(colonna) & {"differenza", "delta", "scarto"}), (
            "min_ratio e Jacobiano scalato non si sottraggono"
        )
    assert set(qualita["estruso"]) & set(qualita["as-built"]) == set()
```

Per le seconde: tenerle (sono la dichiarazione stessa, ed e' legittimo
sorvegliarla) ma dichiararlo nella docstring del test — «sorveglia la costante,
non un calcolo» — cosi' che nessuno le scambi per una verifica di comportamento.

**gravita':** MINORE.

---

### 12.5 `from tests.test_report import ...` non risolve — MINORE

**dove:** `task-12-brief.md:382`.

**perche' e' falso:** `tests/` non e' un pacchetto (nessun `__init__.py`), ed e'
`tests/` stessa a finire su `sys.path`: l'import corretto sarebbe
`from test_report import _tre_cartelle_finte`. Il brief mette le mani avanti alla
riga 392, quindi il difetto e' dichiarato.

**correzione proposta:** scegliere subito la via che il brief indica come
ripiego — `_tre_cartelle_finte` in `tests/materiale.py`, accanto a `crea_config`,
che e' gia' importato per nome semplice da entrambi i file.

**gravita':** MINORE.

---

*Verificato **vero** in questo task:* `report.py` ha gia' `_STILE`, `_numero`,
`_testo`, `METRICS_FILENAME`, `json`, `Path`; le quattro stringhe cercate nel
test delle note («as-built monolitico», «vincolati alle giunzioni», «armatura»,
«dove abbiamo tagliato») sono tutte presenti in `NOTE_NON_GEOMETRICHE`; «scheda
singola» compare nell'avviso; il filtro `-k` dello Step 2 seleziona tutti e
cinque i test nuovi; il banco finto produce davvero le tre chiavi `as-built`,
`estruso`, `primitive` e `mancanti == ["primitive"]` con due cartelle.

---

## Task 13 — `task-13-brief.md`

### 13.1 `triangoli_da_quadrilateri` non fa quello che il test afferma — BLOCCANTE

**dove:** `task-13-brief.md:61-66`, contro il test `:29-31`.

**cosa afferma:** `assert triangoli[1].tolist() == [0, 2, 3]`.

**perche' e' falso:** `np.argsort(np.repeat(np.arange(len(quad)), 2), kind="stable")`
e' l'**identita'**: `repeat([0,1],2) = [0,0,1,1]`, gia' ordinato. L'indice non
riordina nulla e la `reshape(-1,3)` e' un no-op. Da `tmp/t13_triangoli.py`:

```
indice usato: [0 1 2 3]
risultato:
 [[0 1 2]
  [4 5 6]
  [0 2 3]
  [4 6 7]]
t[0]==[0,1,2]: True
t[1]==[0,2,3]: False -> vale [4, 5, 6]
```

I due triangoli dello stesso quadrilatero finiscono agli indici 0 e 2, non 0 e 1.
Il test fallisce, e su una mesh vera l'ordine delle facce non sarebbe piu' quello
dei quadrilateri d'origine.

**correzione proposta:** l'interlacciamento si scrive con `stack(axis=1)`, senza
permutazioni:

```python
    quad = np.asarray(quadrilateri, dtype=np.int64)
    # stack sull'asse 1: i due triangoli dello stesso quadrilatero restano
    # adiacenti, e l'ordine delle facce resta quello dei quadrilateri d'origine.
    return np.ascontiguousarray(
        np.stack([quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]], axis=1).reshape(-1, 3)
    )
```

Verificato: `[[0 1 2] [0 2 3] [4 5 6] [4 6 7]]`.

**gravita':** BLOCCANTE.

---

### 13.2 Il corpo dell'errore non ha una chiave `detail` — BLOCCANTE

**dove:** `task-13-brief.md:193`.

**cosa afferma:** `assert "estruso" in risposta.json()["detail"]`.

**perche' e' falso:** il gestore globale di `create_app` (`server.py:269-277`)
risponde con un'altra forma:

```python
        return JSONResponse(
            status_code=400,
            content={"errore": type(errore).__name__, "messaggio": str(errore)},
        )
```

`detail` e' la convenzione di `HTTPException`, che qui non si usa: e' scritto per
esteso nel commento («L'errore torna strutturato, con il tipo, perche'
l'interfaccia possa dirlo»). Lo stato 400 atteso dal test e' invece **giusto**.

**correzione proposta:**

```python
    corpo = risposta.json()
    assert risposta.status_code == 400
    assert corpo["errore"] == "ValueError"
    assert "estruso" in corpo["messaggio"]
```

**gravita':** BLOCCANTE (KeyError).

---

### 13.3 `/api/membrature` etichetta con una chiave che nessuno scrive — SERIO

**dove:** `task-13-brief.md:308-311`, e la Nota vincolante a `:348`.

**cosa afferma:** `quanti = int(membratura.get("punti_disegnati", 0))`.

**perche' e' falso:** `wall.prior` scrive per ogni membratura
`"punti": int(len(m.punti))` (`wall.py:737`) — il **conteggio**, non gli indici —
e nessuna chiave `punti_disegnati` esiste da nessuna parte. Con il `get(...,0)`
il ciclo lascia l'intero array a `-1.0` e l'endpoint risponde «nessuna
membratura» per ogni punto: un difetto muto, che nessun test del brief
intercetta. La Nota vincolante trenta righe piu' sotto **ammette** che il codice
sopra e' sbagliato e prescrive di sostituirlo — ma l'implementatore che copia il
blocco e passa oltre non se ne accorge.

**correzione proposta:** togliere il codice sbagliato invece di lasciarlo
accanto alla sua smentita. Il blocco diventa la versione che la Nota descrive,
con `"indici": m.punti.tolist()` aggiunto in `wall.prior` e l'incrocio con la
mappa `gruppi` che `decimate_file` restituisce, esattamente come fa
`/api/cluster` (`server.py:570`, `cluster_del_punto_pieno`).

**gravita':** SERIO.

---

### 13.4 `/api/rigonfiamento` promette «un valore per cella» e ne restituisce tre — SERIO

**dove:** `task-13-brief.md:321` e `:339-341`.

**cosa afferma:** «La mappa di rigonfiamento di una membratura, un valore per
cella».

**perche' e' falso:** il `12_wall.json` non contiene la mappa. `wall.prior`
serializza solo l'aggregato (`wall.py:747-753`):

```python
                "rigonfiamento": {
                    "celle": int(len(m.rigonfiamento)),
                    "min": ..., "max": ..., "p95": ...,
                },
```

e infatti il codice del brief risponde `campo_per_punto(np.array([min, max, p95]))`:
**tre numeri**, con un'intestazione `X-Celle` che ne dichiara migliaia. Un
viewport che chiedesse una mappa di colore riceverebbe tre valori.

**correzione proposta:** o l'endpoint dichiara cio' che serve davvero —

```python
        """I tre estremi del rigonfiamento di una membratura: minimo, massimo e
        p95. **Non e' una mappa per cella**: il prior serializza il solo
        aggregato (vedi wall.prior), e la mappa per cella vive in memoria dentro
        Membratura.rigonfiamento. Per la mappa di colore serve prima che
        wall.prior la scriva su disco, in un .npy accanto al JSON.
        """
```

— oppure si aggiunge il compito a `wall.prior`, come gia' si fa per gli indici
(13.3), e allora la docstring e' vera. Va scelto, non lasciato ambiguo.

**gravita':** SERIO.

---

### 13.5 Lo step 12 non e' raggiungibile da «esegui da qui in poi» — SERIO

**dove:** vuoto fra `task-13-brief.md` e `task-14-brief.md`; il codice e'
`src/meshrec/app/server.py:408-410`.

**cosa afferma (nel codice):** `lavoratore.start(config_path, numero, 11)` e
`return {"avviato": numero, "fino_a": 11}`.

**perche' diventa falso:** dal Task 9 gli step sono dodici, e il Task 14 mette il
dodicesimo nella colonna dell'interfaccia (Step 5, `"12_wall": "Prior geometrico"`).
Ma `/api/step/{numero}/from` si ferma a 11 in due punti scritti a mano, quindi da
quel comando lo step 12 non parte mai — e l'utente vede una riga che resta «mai
eseguito» senza sapere perche'. Nessuno dei due brief lo nomina.

**correzione proposta:** nel Task 13, accanto agli altri endpoint:

```python
    # 12 e non 11 dalla Fase 4: lo step 12 e' il prior geometrico e chiude la
    # corsa madre. Il numero e' quello di RunConfig.to_step, che vale 12.
    @app.post("/api/step/{numero}/from")
    def esegui_da(numero: int) -> dict[str, object]:
        lavoratore.start(config_path, numero, 12)
        return {"avviato": numero, "fino_a": 12}
```

con un test che lo sorveglia: `assert cliente.post("/api/step/9/from").json()["fino_a"] == 12`.

**gravita':** SERIO.

---

### 13.6 `cfg_viewport` non esiste, e la cartella di cache e' un'altra — MINORE

**dove:** `task-13-brief.md:303-304`.

**cosa afferma:** `cfg_viewport.max_points, ..., Path(cfg.run.out_dir)` come
ultimo argomento di `decimate_file`.

**perche' e' falso:** in `server.py` non esiste alcun `cfg_viewport`; l'idioma e'
`ViewportConfig().max_points` (`server.py:498`), e l'ultimo argomento e'
`CACHE_DIR`, definito a `server.py:41` come `Path(".cache/viewport")`. Passando
la cartella della corsa, `/api/membrature` decimerebbe in una cache diversa da
quella di `/api/cloud/2`, cioe' rifarebbe il lavoro e scriverebbe cache dentro
gli artefatti.

**correzione proposta:**

```python
        punti, gruppi, _voxel = viewport.decimate_file(
            Path(cfg.run.out_dir) / pipeline.ARTIFACTS[2],
            ViewportConfig().max_points, cfg.input.spacing_sample, cfg.input.seed,
            CACHE_DIR,
        )
```

**gravita':** MINORE.

---

*Verificato **vero** in questo task:* tutti i nomi che `start_comando` tocca
esistono in `worker.py` (`_lucchetto`, `_righe`, `exit_code`, `annullato`,
`step`, `avviato`, `_processo`, `_leggi`) e `Worker()` non prende argomenti;
`viewport.to_float32` restituisce `bytes` in `<f4`; `/api/run` restituisce
davvero `out_dir`, quindi il ripiego per `_cartella_di_corsa` funziona;
`/api/config` esiste; il messaggio di `/api/wall` contiene «step 12» come il
test cerca; `report.confronta` restituisce un dizionario serializzabile in JSON
(nessun `Path` fra i valori).

---

## Task 14 — `task-14-brief.md`

### 14.1 `illeggibile` non esiste in `app.js` — BLOCCANTE

**dove:** `task-14-brief.md:116` e `:167`.

**cosa afferma:** `if (superata(ordine) || corpo === illeggibile) return;`, con
la premessa «seguendo alla lettera i due contratti che lo scanner strutturale
sorveglia ... ogni lettura di un corpo passa da `corpoLetto`».

**perche' e' falso:** `illeggibile` non e' un identificatore del modulo. Compare
una sola volta in tutto `app.js`, **dentro un commento** (riga 479: «Fuori scala
si comporta come illeggibile»):

```
$ grep -n "illeggibile" src/meshrec/ui/app.js
479:// scala si comporta come illeggibile — resta la stringa battuta, e la decide il
```

Il sentinella vero e' `undefined`, restituito da `corpoLetto` nel `catch`
(`app.js:448-454`), e l'idioma del file e' `if (corpo == null)`
(`app.js:598`, `:822`), con `==` e non `===` per prendere anche il `null`.
Le due funzioni del brief solleverebbero `ReferenceError` alla prima risposta.

**correzione proposta:**

```javascript
  const corpo = await corpoLetto(risposta);
  // == e non ===: un corpo intero non e' mai un null legittimo su questo
  // endpoint, e corpoLetto marca con undefined cio' che non si e' letto.
  if (superata(ordine) || corpo == null) return;
```

**gravita':** BLOCCANTE.

---

### 14.2 Un'asserzione terminata da `or True` — SERIO

**dove:** `task-14-brief.md:39`.

**cosa afferma:**

```python
    assert "prior-vuoto" not in _senza_commenti_js(_modulo()).split("createElement")[0] or True
```

**perche' e' falso:** `X or True` e' `True` per qualunque `X`. L'asserzione non
puo' fallire, in nessuna condizione, e sta in un test la cui docstring promette
di sorvegliare proprio la lezione della regione d'errore («uno stato vuoto creato
nell'istante in cui ci si scrive dentro non preesiste a cio' che annuncia»).
E' decorazione con la forma di un controllo.

**correzione proposta:** o si toglie la riga — le due asserzioni sul markup
sopra bastano a dire che lo stato vuoto **preesiste** — oppure si scrive la
proprieta' vera, che e' «il modulo non crea l'elemento, lo trova»:

```python
    modulo = _senza_commenti_js(_modulo())
    corpo = _sorgente_di("caricaPrior", modulo)
    assert 'getElementById("prior-vuoto")' in corpo
    assert "createElement" not in corpo, (
        "caricaPrior deve trovare lo stato vuoto nel markup, non fabbricarlo"
    )
```

**gravita':** SERIO.

---

### 14.3 Il ciclo dei due modelli e' codice morto, e il brief lo sa — SERIO

**dove:** `task-14-brief.md:206` e la nota `:214`.

**cosa afferma:** `while ((await (await fetch("/api/run")).json()) && false) break;`

**perche' e' falso:** `X && false` e' sempre falso: il corpo non si esegue mai,
la `fetch` viene comunque emessa e scartata. Il brief lo dichiara in grassetto
subito sotto («se il codice sopra viene copiato com'e', il secondo modello non
parte e l'interfaccia tace»), il che e' onesto ma lascia nel piano un blocco che
un implementatore puo' incollare senza leggere oltre — e' la stessa forma di
13.3.

**correzione proposta:** togliere la riga inerte dal blocco e lasciare al suo
posto un segnaposto che non compila per sbaglio:

```javascript
      await fetch(`/api/model/${tipo}`, { method: "POST" });
      // DA SCRIVERE: attendere la fine del primo modello prima del secondo.
      // Il worker esegue un solo sottoprocesso e la seconda POST solleverebbe
      // RuntimeError. L'attesa si legge dal flusso SSE gia' aperto, sullo
      // stesso stato che il pannello degli step usa per sapere che una corsa
      // e' finita. Senza, il secondo modello non parte e l'interfaccia tace.
      await attendiFineComando();
```

cosi' che l'assenza di `attendiFineComando` fermi chi copia, invece di
lasciar passare un `while` che non fa niente.

**gravita':** SERIO.

---

*Verificato **vero** in questo task, e vale la pena dirlo perche' sono le
affermazioni piu' facili da sbagliare:* `markup.count('class="viewport"') == 1`
e' vero oggi (`index.html:27`, unica occorrenza), quindi il test coglierebbe
davvero un secondo contenitore; `disegnaStep` (`app.js:67-89`) legge
`steps.length` e non conta a mano, quindi **regge dodici voci senza modifiche**
come il brief afferma; `ETICHETTE` (`app.js:3-9`) arriva a `"11_export"` e non
ha `"12_wall"`, quindi l'aggiunta chiesta e' quella giusta; `_elemento` e
`_sorgente_di` hanno la firma con cui il brief li chiama; i due gestori dello
Step 4 mettono `bottone.disabled = true` **prima** della prima `await fetch(`,
quindi passano lo scanner di `test_ogni_gestore_che_scrive_dopo_un_attesa_si_difende`
(`tests/test_app_js.py:570`); il markup delle caselle soddisfa le asserzioni su
`checked`/`disabled`.

---

## Task 15 — `task-15-brief.md`

### 15.1 La formula prescritta per lo stato del deck e' falsa su questa macchina — SERIO

**dove:** `task-15-brief.md:138` (punto 7 del documento) e `:170` («Rischi
dichiarati»).

**cosa afferma:** «Task 11 salta se `ccx` non e' installato, che al 18/08/2026 e'
il caso».

**perche' e' falso:** `which ccx` → `/Users/mario/.local/bin/ccx`, e il controllo
del Task 11 passa davvero (vedi 11.1, misurato: `returncode 0`, `modello.dat`
scritto, entrambe le parametrizzazioni). Il punto 7 e' scritto con un «Se» e
quindi regge, ma il paragrafo dei rischi no, ed e' quello che l'autore del
documento leggera' per sapere che cosa scrivere.

**correzione proposta:** riga 170 → «Task 11 gira: `ccx` e' installato su questa
macchina (`/Users/mario/.local/bin/ccx`, verificato il 20/08/2026). Il documento
riporta l'esito misurato — versione, codice di uscita, `.dat` prodotto — e la
formula «non verificato da alcun solutore» resta per le macchine dove il
controllo salta. **Un controllo saltato non e' un controllo passato**, ma un
controllo passato non va raccontato come saltato.»

E al punto 7 va aggiunto l'esito di 8.4/11.4: se il `*TIE` non genera alcun MPC,
il documento deve dirlo con la stessa precisione, perche' e' la differenza fra
«il solutore legge il deck» e «il modello e' legato».

**gravita':** SERIO.

---

### 15.2 La Self-Review dichiara una coerenza dei tipi che non c'e' — SERIO

**dove:** `task-15-brief.md:168`.

**cosa afferma:** «`wall.prior` restituisce sempre lo stesso dizionario, ed e'
quello che `pipeline.calcola_prior` scrive, che `pipeline.genera_modello` rilegge
e che `/api/wall` inoltra.»

**perche' e' falso:** `genera_modello` **non** riesce a rileggerlo: la
ricostruzione della `Membratura` manca di tre campi obbligatori e solleva
`TypeError` (10.1, misurato), e il campo del riempimento nel JSON e' annidato
sotto `"riempimento"`, non piatto. La stessa riga prosegue con «`ties` e' sempre
una tupla di terne ... che e' esattamente la forma che `write_inp` accetta» —
vero come forma (verificato: `abaqus.py:42` e `:74`), falso come sostanza,
perche' sulla geometria tagliata `ties` e' sempre **vuota** (8.3, misurato).

**correzione proposta:** riscrivere il paragrafo dopo aver chiuso 10.1 e 8.3, e
aggiungere la riga che oggi manca: «lo `scostamento_nuvola` che il Task 12 legge
da `modello.json` e' scritto dal Task 10; se non c'e', la colonna dichiarata
confrontabile e' vuota e `write_comparison_report` solleva.»

**gravita':** SERIO.

---

### 15.3 «34,39 secondi» e «circa 400 MB» — NON VERIFICATO, e in tensione con un altro numero del repository — MINORE

**dove:** `task-15-brief.md:93`.

**cosa afferma:** «sulla scansione di riferimento il singolo step piu' lento dura
34,39 secondi e gli artefatti pesano circa 400 MB».

**perche' e' sospetto:** non ho potuto eseguire la corsa (152 MB di nuvola, ore
di calcolo), quindi **NON VERIFICATO**. Segnalo pero' una tensione: `sweep.py:151`
porta un numero diverso per una grandezza dal nome uguale — «La corsa completa
piu lenta documentata vale 134 s e il singolo step piu lento 186 s» — e
`app.js:74` ne porta un terzo, «uno step da 34 secondi». Verosimilmente si
riferiscono a corse diverse (muro contro `lab_crop`), ma nessuno dei tre lo dice.

**correzione proposta:** citare la fonte accanto al numero, come lo stesso brief
impone alla riga 142 («Ogni numero del documento va ricavato da una lettura e
citato con la propria fonte»): «34,39 s e' il singolo step piu' lento della corsa
`lab_crop` (fonte: `docs/...`, tabella dei tempi); i 186 s citati in `sweep.py`
sono la corsa del muro, che e' un'altra geometria.»

**gravita':** MINORE (sospetto, non difetto).

---

*Verificato **vero** in questo task — e' il piu' pulito degli otto:*
`.gitignore:13` contiene davvero `Nuvole di punti/`
(`git check-ignore -v "Nuvole di punti/lab_frame.pcd"` → `.gitignore:13`);
`lab_frame.pcd` esiste ed e' 151 898 491 byte, cioe' i «152 MB» della riga 170;
`lab.yaml` ha davvero `crop_min = [1690, -470, -480]` e `crop_max = [4460, -180, 1230]`,
quindi «`crop_min` z = -480, y da -470 a -180 ... largo 290 mm» e' esatto in tutte
e tre le sue parti; `lab.yaml` non ha blocchi `wall:` ne' `model:`, quindi
«aggiungi i due blocchi» e' corretto; tutte e quattordici le chiavi del blocco
`wall:` esistono in `WallConfig` e tutte e sei quelle di `model:` in `ModelConfig`;
`volume_atteso: 477700000.0` e' esattamente 0,4777 m³ in mm³; le sezioni nominali
elencate sommano a sei membrature (2 zapatas + viga inferior + 2 columnas + viga
superior), coerenti con `membrature_attese: 6`; il nome di cartella prodotto da
`meshrec model` senza `--out-dir` e' `runs/lab_telaio-estruso`, cioe' quello che
il comando `compare` del passo 6 usa.

---

## Contraddizioni **fra** task

Sono le cose che nessun implementatore singolo puo' vedere, perche' ciascuno
legge solo il proprio brief.

### A. Task 8 chiede il campo che il Task 10 non ricostruisce — BLOCCANTE

Il Ruling J vive tutto in `membratura.riempimento_stato` (Task 8, righe 16 e
391-395), con un test dedicato. Il Task 10 ricostruisce le `Membratura` dal JSON
**senza quel campo** (10.1): con il `TypeError` la corsa figlia non parte; tolto
il `TypeError` aggiungendo un valore qualunque, la guardia diventa muta e una
regione a Π diventa un modello parametrico — cioe' esattamente il costo che il
Ruling J dichiara di voler pagare per evitare. Nel JSON il dato c'e', annidato
sotto `"riempimento"`: e' un problema di lettura, non di informazione mancante.

### B. Task 12 legge una grandezza che il Task 10 non scrive — BLOCCANTE

`scostamento_nuvola` e' il perno dichiarato del confronto (Task 12, riga 185) e
non e' prodotto da nessuno (10.2, 12.1, 12.2). Effetto misurato: la colonna vale
`None` per i due modelli parametrici e `write_comparison_report` solleva
`TypeError` (`tmp/t12_confronto.py`). Il Task 12 dichiara di consumare
`quality.vertex_deviation` e non la chiama mai: e' la funzione che avrebbe
chiuso il buco, ed e' rimasta nel titolo delle dipendenze.

### C. Dentro il Task 8, tagliare le giunzioni e legarle con un `*TIE` si escludono — BLOCCANTE

Non e' una contraddizione fra due brief ma fra due Step dello stesso, e nessuno
dei due test la vede perche' condividono una geometria in cui il taglio non
avviene (8.2). Misurato: taglio corretto → `ties: ()` e `superfici: {}` (8.3);
nessun taglio → `ties` piena ma i solidi si compenetrano, il volume e' contato
due volte, e CalculiX accetta il deck **senza generare alcun MPC** (8.4). Il
Task 10 passa `ties=modello["ties"]` a `write_inp` e il Task 12 stampa una nota
che promette «parametrici vincolati alle giunzioni»: la promessa attraversa tre
task e non e' mai vera.

### D. Il Task 9 rende falso un commento che il Task 1 aveva scritto — MINORE

`steps.py:19-21` dice «Fino al Task 9, pipeline.run scrive solo le prime undici:
is_complete() in sweep.py lo sa e non richiede "12_wall"». Dopo il Task 9 la
prima meta' e' falsa; la seconda resta vera perche' `sweep.REQUIRED_STEPS`
(`sweep.py:130`) non cambia — ma quella e' ora una **decisione**, non un
adattamento, e va scritta come tale. Conseguenza non dichiarata da nessun brief:
dal Task 9 in poi ogni candidato di sweep calcola anche il prior, perche'
`to_step` vale 12 di predefinito.

### E. L'interfaccia mostra uno step che i suoi comandi non sanno eseguire — SERIO

Il Task 14 mette `"12_wall": "Prior geometrico"` nella colonna (Step 5), il Task
13 aggiunge `POST /api/wall` per calcolarlo — ma `/api/step/{numero}/from`
(`server.py:408-410`) resta fermo a `11` in due punti scritti a mano, e nessuno
dei due brief lo tocca. L'utente che preme «esegui da qui in poi» vede la riga
dodici restare «mai eseguito» senza spiegazione (13.5).

### F. Il Task 10 e' il primo chiamante di `hexa_metrics`, e la sua docstring dice il contrario — SERIO

`quality.py:139-141` afferma al presente «Oggi la funzione non ha ancora
chiamanti». Verificato vero **oggi** (nessun riferimento in `src/`), falso dal
Task 10 in poi (10.4). E' letteralmente la stessa forma del difetto gia' pagato
in questa fase con la docstring di `report.py`.

### G. L'unico controllo col solutore non tocca la card nuova piu' rischiosa — SERIO

Il Task 11 e' il solo punto in cui un solutore vero legge un deck del progetto, e
prova `*ELEMENT C3D8I`, `*SURFACE` e `*DSLOAD` — non `*TIE`, che e' la card su
cui poggia l'intero modello di telaio (11.4). Misurato che sarebbe stato il posto
giusto: eseguendo il deck con `*TIE`, `ccx` esce 0 senza `*ERROR` e stampa
`*WARNING in gentiedmpc: no tied MPC`.

### H. La numerazione dello Step 12 nella pipeline e la condizione di completezza — SERIO

Il Task 9 chiede `completa = start == 1 and stop == 12` (9.2), che rimette a mano
il numero che il Task 1 aveva tolto con `pipeline_completa`, e il punto
d'inserimento del blocco lascia `pipeline_completa = True` prima dello step 12
(9.3). Le due cose insieme cambiano, senza dichiararlo, quali corse sostituiscono
`metrics.json` e quali lo fondono — che e' il comportamento da cui dipende lo
sweep della Fase 2.

---

## Sul prompt di questo setaccio

Una cosa chiesta di verificare: il campionario diceva che il difetto ricorrente
e' «un'affermazione di fatto scritta senza eseguire nulla per verificarla», e la
priorita' suggerita era Task 8-9-10-11 perche' poggiano su codice esistente.
Confermato: dei 44 rilievi, 27 stanno in quei quattro task, e i cinque piu' gravi
sono tutti li'. Ma il Task 12 ne ha due bloccanti che non dipendono da codice
futuro — dipendono da `report._numero`, che e' scritto da settimane — e il Task
14 uno, `illeggibile`, che dipende da `app.js` per intero.

Un'affermazione del prompt e' risultata **falsa**: non riguarda il metodo ma un
fatto della macchina. `ccx` e' installato (`/Users/mario/.local/bin/ccx`), quindi
il Task 11 non salta, e la formula che il piano prescrive due volte per il
documento del Task 15 direbbe il falso. L'ho verificato eseguendo davvero il
controllo: passa, in entrambe le parametrizzazioni.
