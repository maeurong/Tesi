## Task 11: il deck esaedrico letto da un solutore vero

> ### Questo brief e' stato riscritto il 20/08/2026, e il task e' molto piu' piccolo di com'era
>
> La prima stesura chiedeva di costruire da zero il controllo col solutore sul
> deck esaedrico. **Nel frattempo quel lavoro e' stato fatto altrove**, e
> ridispacciarlo sarebbe rifare due volte la stessa cosa. Lo stato reale di
> `tests/feasibility/test_calculix.py` oggi:
>
> | test | che cosa gia' prova | da dove viene |
> |---|---|---|
> | `test_calculix_solves_a_column_under_self_weight` | deck **tetraedrico** C3D4, peso proprio | Fase 1 |
> | `test_la_pressione_su_s4_sposta_la_faccia_x_massimo_e_non_un_altra` | deck **esaedrico** C3D8I, `*SURFACE` + `*DSLOAD`, e che la faccia che si muove sia quella fisica giusta | Task 5, Ruling M(b) |
> | `test_i_tie_del_telaio_a_quattro_membrature_legano_davvero` | deck esaedrico di un **telaio intero** con quattro `*TIE`, generato da `hexa.costruisci` | Task 8, giro 6 |
>
> Quindi C3D8I, `*SURFACE`, `*DSLOAD` e `*TIE` sono **gia' verificati da
> CalculiX vero**. Il rilievo 11.4 del setaccio — «il controllo col solutore non
> prova la card nuova piu' rischiosa, il `*TIE`» — **e' gia' chiuso**, e per una
> ragione che vale la pena sapere: quel controllo, appena scritto, ha scoperto
> che i `*TIE` non legavano il 77% dei nodi dipendenti. E' costato sei giri di
> correzione al Task 8 ed e' il difetto piu' grave della fase.
>
> Resta un vuoto solo, ed e' quello che questo task chiude adesso.

**Files:**
- Modify: `tests/feasibility/test_calculix.py`

**Interfaces:**
- Consumes: `hexa.mesh_prisma` (Task 7), `abaqus.write_inp` (Fase 1), `abaqus.element_surface` (Task 5).
- Produces: nessuna interfaccia nuova. Questo task aggiunge controlli, non codice di produzione.

### Il vuoto che resta: «il solutore non si e' lamentato» non e' «il solutore ha letto quello che c'era scritto»

I tre test esistenti verificano il codice di uscita, l'assenza di `*ERROR` e —
il terzo — una soglia sugli avvisi `no tied MPC`. Nessuno dei tre si accorge di
una card che **CalculiX scarta in silenzio**.

CalculiX segnala con `*WARNING` e **prosegue** le card che non riconosce. Sul
deck di questo progetto compaiono, misurati:

```
 *WARNING reading *STEP: parameter not recognized:
 *WARNING reading *OUTPUT:
```

`NAME=` su `*STEP` e la card `*OUTPUT, FIELD` vengono scartate, e ogni criterio
attuale resta verde. Se domani `write_inp` scrivesse male una card nuova, il
solutore la ignorerebbe e nessun test lo direbbe.

- [ ] **Step 1: L'elenco degli avvisi attesi, in tutti e tre i test**

L'idea e' dichiarare quali avvisi conosciamo, cosi' che **uno nuovo si veda**.
Non silenziarli: elencarli.

```python
# Avvisi che CalculiX stampa su questi deck e che sono noti e accettati. Non
# e' un elenco per farli tacere: e' il contrario. Ogni avviso fuori da qui e'
# una card che il solutore ha scartato in silenzio, ed e' esattamente cio' che
# «returncode 0 e nessun *ERROR» non sa vedere.
AVVISI_NOTI = (
    "reading *STEP",
    "reading *OUTPUT",
)


def avvisi_inattesi(stdout: str) -> list[str]:
    return [
        riga for riga in stdout.splitlines()
        if "*WARNING" in riga and not any(noto in riga for noto in AVVISI_NOTI)
    ]
```

**Il terzo test ha un avviso in piu' che gli e' proprio**, `no tied MPC`, gia'
governato da una soglia dichiarata: li' l'elenco va esteso localmente, non
globalmente, o la soglia perde significato.

Aggiungi a ciascuno dei tre test, dopo le asserzioni esistenti:

```python
    assert not avvisi_inattesi(processo.stdout), "\n".join(avvisi_inattesi(processo.stdout))
```

adattando il nome della variabile del processo a quello che ogni test usa gia'.

- [ ] **Step 2: Eseguire e **misurare** cosa esce**

Run: `uv run pytest tests/feasibility -m feasibility -q`

**Non do' per scontato che passi.** Se un avviso che non conoscevo compare, e'
una scoperta e non un fastidio: **riportalo nel rapporto e fermati** prima di
aggiungerlo a `AVVISI_NOTI`. Aggiungere una riga a quell'elenco e' una decisione,
non una correzione — l'elenco esiste per rendere visibile ciò che il solutore
scarta, e allungarlo senza capire perché lo svuota di senso.

Se invece passa, riporta l'elenco esatto degli avvisi che ciascun deck produce.

- [ ] **Step 3: Il deck di `mesh_prisma` da solo**

`hexa.mesh_prisma` arriva al solutore solo **attraverso** `hexa.costruisci`, nel
test del telaio. Un prisma singolo — l'uscita piu' semplice di `mesh_prisma`,
molti elementi e piu' strati nello spessore — non e' mai stato risolto.

Aggiungi un test che genera un prisma con `mesh_prisma`, lo vincola alla base,
lo carica col peso proprio e lo risolve. Asserzioni: codice di uscita zero,
nessun `*ERROR`, nessun avviso inatteso, e il file `.dat` dei risultati esiste.

**Il materiale lo definisci nel file stesso**, con valori tuoi: tre numeri
bastano per un controllo di fattibilita'. **Non** importare `MATERIALE` da
`tests/materiale.py`: quando pytest colleziona il solo `tests/feasibility/`, la
cartella sulla via di ricerca e' `tests/feasibility/` e non `tests/`, quindi
`from materiale import MATERIALE` fallisce in collezione — mentre la suite
intera passa, perche' la collezione di `tests/*.py` ha gia' messo `tests/` in
`sys.path`. Verificato: non esiste alcun `conftest.py` nel progetto e
`pyproject.toml` non dichiara `pythonpath`.

- [ ] **Step 4: L'esito misurato, per il documento della fase**

Il Task 15 deve riportare che cosa il solutore ha detto. **La formula «il deck
esaedrico non e' stato verificato da alcun solutore su questa macchina» e'
falsa** e non va scritta: `ccx` e' presente in `/Users/mario/.local/bin/ccx`,
verificato oggi, e ha risolto il deck del telaio — `Job finished`, sistema di
31.674 equazioni fattorizzato.

Nel rapporto scrivi, misurati in questa sessione: la versione di `ccx`, il
codice di uscita di ciascun test, gli avvisi di ciascun deck, e quali card sono
state effettivamente lette. Sono i numeri che il Task 15 riportera'.

Il ramo di skip resta per le macchine senza `ccx`, e con esso la regola:
**un controllo saltato non e' un controllo passato.**

- [ ] **Step 5: Commit**

```bash
git add meshrec/tests/feasibility/test_calculix.py
git commit -m "test(fase-4): gli avvisi inattesi di CalculiX non passano piu' inosservati"
```
