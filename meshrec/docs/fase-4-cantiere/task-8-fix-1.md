# Task 8 — giro di correzione 1 di 5

La revisione ha dato **conforme con riserva** sulla spec e **CONCERNS** sulla
qualita'. Nessun BLOCK: niente di cio' che e' gia' provato si rompe. Il banco
chiude; e' il dato reale che ha tre modi di fallire in silenzio.

**Ho riprodotto io tutti i rilievi portanti prima di passarteli** — non ti
arrivano sulla parola del revisore. I numeri qui sotto sono usciti dalla mia
esecuzione, non dal suo rapporto ne' dal brief.

Ordine consigliato: A3 (una riga), A4, A2, A1, poi i test mancanti, poi la
prosa. Un commit solo alla fine, o due se preferisci separare codice e
docstring.

---

## A1 — un telaio senza legami esce senza un fiato

`hexa.py:412` (`if not invaso.any(): continue`) e `hexa.py:571-576`
(superficie vuota → tie scartato). Con 0,1 mm di gioco fra colonna e trave —
sotto la risoluzione di qualunque scanner — `costruisci` restituisce `ties=0`,
`superfici={}`, `accorciamenti=[]` e **nessun errore**: due blocchi in aria
consegnati come telaio.

**Ruling Z, vincolante: non sollevare.** Un modello con membrature scollegate
e' legittimo qui — l'utente ha deciso che i piedistalli entrano come corpo
separato — quindi «zero `*TIE` con N≥2 membrature» non e' di per se' un errore.
Ma oggi all'operatore non arriva nulla, e il gioco da 0,1 mm e la scelta di
modellare i piedistalli separati producono lo stesso stato interno.

Quindi: `metriche` porta il conteggio delle membrature **non legate a
nessun'altra**, e quando quel numero e' maggiore di zero un `warnings.warn` lo
dice. Nel progetto c'e' gia' il precedente di `UnmetQualityConstraintWarning`
(vedi `quality.py`): usa la stessa forma, una classe di avviso propria se serve.

Un test che monta due prismi a 0,1 mm di distanza e verifica che il conteggio
sia 2 e che l'avviso venga emesso (`pytest.warns`).

## A2 — la sovrapposizione si cerca su una sola retta

`hexa.py:408-411`: si campiona la sola retta baricentrica del prisma minore. Se
quella retta manca il maggiore, `invaso.any()` e' falso, il taglio non scatta, e
il volume si conta due volte senza un segnale.

**Riprodotto da me**, con una geometria che non e' quella del revisore:

```python
colonna = Prisma(np.array([[0.,0.],[400.,0.],[400.,400.],[0.,400.]]),
                 np.array([0.,0.,0.]), np.array([0.,0.,1.]), 1000.)
trave   = Prisma(np.array([[0.,0.],[100.,0.],[100.,100.],[0.,100.]]),
                 np.array([-400.,-80.,500.]), np.array([1.,0.,0.]), 500.)
```

Campionando il volume della trave con `dentro(colonna, ...)`: **4,00% della
trave e' dentro la colonna, cioe' 200.000 mm³ di compenetrazione vera**.
`taglia_giunzioni` restituisce `giunzioni: []` e la somma dei volumi resta
165.000.000 mm³, identica a quella senza taglio. E' esattamente l'errore che il
docstring a `hexa.py:364-367` dice di cercare.

**Ruling Y, vincolante: guardia additiva, non taglio piu' furbo.** Campiona,
oltre alla baricentrica, le **quattro rette dei vertici del contorno minore**
(stessa `dentro`, stessi `_CAMPIONI_ASSE` per retta). Poi:

- baricentrica invasa → prosegui **esattamente come oggi**, qualunque cosa
  dicano le rette dei vertici. Nessuna geometria che oggi funziona puo'
  cambiare esito;
- baricentrica libera **e** almeno una retta di vertice invasa → solleva
  `ValueError`, nella stessa famiglia della guardia dell'attraversamento: il
  taglio assiale non sa togliere una sovrapposizione d'angolo, e la
  scomposizione va rivista;
- tutte libere → `continue`, come oggi.

Il costo se sbagliato e' nel verso giusto: una geometria d'angolo legittima, se
esiste, verrebbe rifiutata invece che modellata male.

Un test sulla geometria qui sopra, che verifica il `ValueError` e il messaggio.

## A3 — `metriche["giunzioni"]` mente sul proprio nome

`hexa.py:587` scrive `len(ties)`, non `len(giunzioni)`. E' il solo campo che
renderebbe visibili A1 e A2 a valle, e rilegge il risultato del **legame**
invece di quello del **taglio**. Con `_TOLLERANZA_CONTATTO = 0` il dizionario si
contraddice da solo: `giunzioni=0` accanto ad `accorciamenti=[100.0]`.

**Ruling AA:** `"giunzioni": len(giunzioni)` e, accanto, `"ties": len(ties)`.
Due numeri che coincidono nel caso buono e divergono solo quando qualcosa non
va. Il test in fondo al file diventa allora un controllo di due cose diverse:
aggiornalo perche' le distingua.

## A4 — `primitive` non usa la sezione misurata, e nessun test puo' accorgersene

`hexa.py:253` prende `np.ptp(membratura.contorno, axis=0)`, cioe' il contorno
gia' passato da `semplifica_contorno`. `Membratura.sezione` (`wall.py:435`) e'
invece il `ptp` dei punti **grezzi**, prima della semplificazione.

**Riprodotto da me** — rettangolo 200×140 con una gobba di 5 mm su un lato,
come ne ha qualunque sezione rilevata:

```
toll=  1.0  ptp(semplificato)=(205.0, 140.0)  vertici=5
toll=  5.0  ptp(semplificato)=(200.0, 140.0)  vertici=4     <- contour_tolerance predefinita
sezione (ptp dei punti grezzi): (205.0, 140.0)
```

Alla tolleranza predefinita le due grandezze divergono di 5 mm. Il modello che
la tesi presenta come «rettangolo dei valori misurati» pubblicherebbe una
dimensione che non e' quella misurata.

**Ruling AB:** squadra su `membratura.sezione`. Tieni l'ancoraggio attuale
(`minimo` del contorno) e cambia solo le due estensioni; scrivi nel docstring
perche' le due grandezze non sono la stessa cosa.

E **cambia la fixture**: `_membratura_finta` (`test_hexa.py:163`) impone
`sezione=(ptp(contorno[:,0]), ptp(contorno[:,1]))`, cioe' rende vera per
costruzione l'identita' che sul dato reale non vale. Finche' resta cosi',
nessun test puo' vedere la differenza. Passa una `sezione` **diversa** da
`ptp(contorno)` e aggiungi un test che distingue i due valori.

---

## B1, B2 — due guardie senza test

Il revisore ha mutato e la suite e' rimasta verde 16/16 in entrambi i casi:

- `hexa.py:418` (guardia del **contenimento**) → `if False`: verde. Meta' del
  soffitto dichiarato non e' provata.
- `hexa.py:569` (superficie vuota → niente tie) → `if True`: verde. Ed e' il
  modo di fallire `no tied MPC` che da' il nome all'intero task.

Un test per ciascuna. Per ognuno, **applica tu la mutazione, verifica che il
test nuovo muoia, ripristina**: e' l'unico modo di sapere che non e'
decorazione.

## B3 — tre numeri falsi in un docstring che dice «verificate»

`test_hexa.py:316-318`. **I numeri vengono dal brief** (`task-8-brief.md:184-186`),
non da te: e' un difetto del piano, il quinto di questa forma in questa fase.
Quello che e' tuo e' la frase «entrambe le mutazioni verificate» aggiunta a
numeri che non erano stati rifatti.

Rifatti da me sulla geometria del test:

| affermazione nel docstring | valore vero |
|---|---|
| senza taglio, «volume in eccesso dell'8,8%» | **+2,941%** (l'8,8 viene da `8,8e-16` del brief, che e' il residuo *dopo* la cura: un'altra grandezza) |
| senza bisezione, «accorciamento 94,5» | **105,528** — il segno e' invertito: fermarsi sul campione taglia **di piu'**, non di meno |
| senza bisezione, «volume in eccesso dello 0,16%» | volume in **difetto** dello **0,163%** |

Correggili. E da qui in avanti, regola vincolante: **un docstring che dichiara
un numero di mutazione riporta il numero che la mutazione ha davvero prodotto in
questa sessione, oppure non lo dichiara affatto.** Togliere una frase costa meno
che verificarla.

## B4 — narrazione falsa sulla guardia dell'attraversamento

`test_hexa.py:357-359` e la sezione «Correzione del 20/08/2026» del brief dicono
che prima della correzione il caso «produceva un accorciamento di zero in
silenzio». Falso: senza quella guardia si arriva a `passo[libero[-1] + 1]` con
`libero[-1] == 199` su un array di 200, cioe'
`IndexError: index 200 is out of bounds for axis 0 with size 200` a
`hexa.py:445`. Non silenzio: schianto.

La guardia serve lo stesso — un `IndexError` non dice all'operatore che la
scomposizione e' sbagliata — ma la ragione va scritta giusta.

## B5, B6 — numeri del banco di prova ancora in `src/`

Vincolo dell'utente, non preferenza mia: **nessun numero del provino di
laboratorio in `src/`**. Stanno bene in config e nei test, non nel sorgente. Ne
avevo tolto uno; ne restano quattro:

- `hexa.py:324` — «un intervallo di sette millimetri» (e' 1400/199, la colonna
  del provino divisa per i campioni)
- `hexa.py:326` — «Sul banco del telaio il residuo misurato e' 3,4e-12 mm»: e'
  del banco **e** e' un numero di macchina congelato in un docstring — il tuo
  stesso rapporto ne ha misurato 4,09e-12
- `hexa.py:337` — «portano 20 e 12 facce»: sulla geometria del revisore sono 20
  e 6, quindi e' un numero di quel banco e non una proprieta'
- `hexa.py:374` — «5,5 mm sul banco del telaio»

In ogni caso la cura e' la stessa e migliora il testo: scrivi la **ragione
generale** al posto della misura. Il residuo della bisezione e' sotto
`_ARROTONDAMENTO` per costruzione, non «3,4e-12 su questo banco»; il vuoto che
il campionamento lascia e' grande quanto il passo di campionamento, cioe'
`lunghezza / (_CAMPIONI_ASSE - 1)`, non «5,5 mm».

Cerca anche quello che non ho elencato: `rg` sui numeri del provino in tutto
`src/`, non solo in `hexa.py`.

## B7 — «passo sei volte piu' fine» sono nove

`hexa.py:544`. Verificato da me con `passo_di_mesh` e `ModelConfig()`:
1000×10 → **3,333**; 90×90 → **30,0**; rapporto **9,0**. Correggi il numero (o
togli il fattore e lascia l'esempio, che regge da solo).

---

## Rilievi minori — falli se non allungano il giro

- `hexa.py:549`: `from meshrec.core import abaqus` locale senza ciclo d'import
  (`abaqus` non importa `hexa`): va in testa al modulo.
- `hexa.py:525`: `sum(len(e) for e in elementi_totali[:-1])` a ogni giro, O(n²).
  Un contatore che si somma e' una riga.
- `hexa.py:590-596`: cinque righe di prosa dentro `metriche`. Nessun test la
  tocca e finira' duplicata dove il report la riscrive. Sta nel generatore del
  report, non nel dizionario dei numeri.
- `hexa.py:286`: `prisma.asse / norm(prisma.asse)` senza guardia su asse nullo →
  `nan` silenzioso.
- `hexa.py:219-223`: la convessita' e' dichiarata precondizione e mai
  verificata, e `Prisma` e' pubblica.
- `mesh_prisma` non dichiara la serialita' obbligatoria (`gmsh` tiene stato
  globale di modulo). Una riga di docstring: un `ThreadPoolExecutor` esiste gia'
  in `sweep.py:617`, oggi innocuo solo perche' lancia sottoprocessi.

---

## Come si chiude

Alla fine: `uv run pytest tests -q --ignore=tests/feasibility`. La suite parte
da **487 passati**; i test nuovi la alzano. Riporta il numero che leggi tu, non
quello che ti aspetti.

Per ogni test nuovo, nel rapporto una riga: **quale mutazione lo uccide, e che
l'hai applicata davvero**. Se una mutazione lascia il test verde, dillo invece
di aggiustare il test finche' torna.

Se uno di questi rilievi ti risulta sbagliato — capita, e in questa fase e'
capitato quattro volte che avesse ragione chi eseguiva e non chi scriveva il
piano — **fermati e dillo**, con la prova. Non adattare il codice per far
tornare una mia affermazione.
