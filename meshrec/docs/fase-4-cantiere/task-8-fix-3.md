# Task 8 — giro di correzione 3 di 5

Il Task 8 era chiuso. Lo riapro io, e il difetto non l'ha trovato una revisione:
l'ho trovato preparando il Task 10, facendo girare `hexa.costruisci` sul telaio
sintetico a quattro membrature invece di leggere il codice.

**`hexa.costruisci` solleva su un portale normale.** Non su una geometria
inventata per rompere: sul `TELAIO` di `tests/test_wall.py:33-38`, che è la
geometria più vicina al caso reale che il progetto abbia e su cui i test del
prior già girano.

```
costruisci SOLLEVA: ValueError un vertice del contorno del prisma minore entra
nel prisma maggiore ma la retta baricentrica no: e' una sovrapposizione
d'angolo che il taglio lungo l'asse non sa togliere. Verifica la scomposizione
```

## La diagnosi, misurata su tutte e sei le coppie

```
aree: [43188, 126870, 62735, 39484]

coppia (0,1): asse di 0 dentro 1:   0   asse di 1 dentro 0:   0   per area cederebbe 0
coppia (0,2): asse di 0 dentro 2:   0   asse di 2 dentro 0:  10   per area cederebbe 0   <-- SBAGLIATO
coppia (0,3): asse di 0 dentro 3:   0   asse di 3 dentro 0:   4   per area cederebbe 3
coppia (1,2): asse di 1 dentro 2:   0   asse di 2 dentro 1:   8   per area cederebbe 2
coppia (1,3): asse di 1 dentro 3:   0   asse di 3 dentro 1:   6   per area cederebbe 3
coppia (2,3): asse di 2 dentro 3:   0   asse di 3 dentro 2:   0   per area cederebbe 3
```

(numero = quanti dei 200 campioni della retta baricentrica cadono dentro l'altro
prisma.)

In ogni coppia che si sovrappone, **esattamente una** delle due direzioni ha
l'asse invaso, e non è mai ambigua. Il criterio per sezione minore sbaglia una
volta su quattro: sulla coppia (0,2) sceglie di accorciare il traverso, ma la
sovrapposizione è il montante che entra nel traverso **da sotto** — accorciare
il traverso lungo il proprio asse non la toglie, ed è esattamente il caso che la
guardia d'angolo del Ruling Y intercetta.

## Ruling AD — chi cede è chi ha l'asse invaso

Il criterio «cede il prisma di sezione minore» va sostituito da: **cede il
prisma il cui asse baricentrico entra nell'altro**. Ha anche il significato
fisico giusto — cede la membratura che *finisce dentro* l'altra. Una trave
appoggiata su un pilastro accorcia il pilastro, non la trave.

Casi e loro trattamento:

- **un solo asse invaso** → quello è il minore, l'altro il maggiore. È il caso
  normale, ed è quello che oggi sbaglia.
- **entrambi gli assi invasi** → attraversamento o contenimento: le due guardie
  esistenti sollevano già, e vanno lasciate esattamente come sono. Per la scelta
  dei ruoli, in questo caso l'area resta lo spareggio, che è deterministico.
- **nessun asse invaso, ma vertici invasi** → la guardia del Ruling Y **resta e
  serve ancora**: è una sovrapposizione d'angolo vera, che il taglio assiale non
  sa togliere.
- **nessun asse e nessun vertice** → `continue`, come oggi.

Nota che la guardia del Ruling Y non era sbagliata: ha fatto esattamente il
proprio lavoro, cioè trasformare in un errore un caso che prima contava due
volte il volume in silenzio. È stata lei a rendere visibile questo difetto.

## L'ho già provato, e ti allego l'esperimento

Ho applicato una patch sperimentale e poi rimossa. Il diff sta in
`/Users/mario/.claude/jobs/e87eb542/tmp/esperimento-asse-invaso.patch`.
**Non è la soluzione da consegnare** — è una prova grezza, con una funzione
annidata definita dentro un doppio ciclo e nessun test. Leggila come misura, non
come progetto: la forma pulita la scegli tu, e ponytail dice che la strada più
corta che regge è quella giusta.

Il risultato della prova, sul telaio sintetico:

```
giunzioni: 4   ties: 2   membrature non legate: 0
superfici: ['GIUNZIONE_1_D', 'GIUNZIONE_1_I', 'GIUNZIONE_4_D', 'GIUNZIONE_4_I']
```

e **tutti e 23 i test di `test_hexa.py` restano verdi**, comprese le due guardie
e il test del Ruling Y. Nessuna regressione osservata.

## Che cosa devi consegnare

1. **Il cambio di criterio**, in forma pulita, con il docstring di
   `taglia_giunzioni` aggiornato: oggi dice «Chi cede e' il prisma di sezione
   minore, che e' un criterio del dato e non dell'ordine in cui i prismi
   arrivano» — la ragione nuova è migliore, perché è un criterio del *dato* e
   ha per giunta un senso fisico. Scrivilo.

2. **Un test sul telaio a quattro membrature.** È il controllo che oggi manca e
   che avrebbe trovato questo difetto: la banco di prova a due prismi non lo
   poteva vedere, perché con due prismi il criterio per area e quello per asse
   invaso coincidono. Usa `synth.sample_frame_surface` con la costante `TELAIO`
   di `tests/test_wall.py` (i numeri del provino nei test sono ammessi: è in
   `src/` che non devono comparire) e `wall.prior` per ricavare le membrature —
   così il dato di ingresso lo produce il codice vero e non la tua mano.

   Il test deve fallire sul criterio vecchio. **Verificalo applicando la
   mutazione**, cioè rimettendo la scelta per area, e riportando che muore.

3. **Le due giunzioni che non diventano `*TIE`.** Sul telaio escono `giunzioni:
   4` ma `ties: 2`: due giunzioni tagliano e poi non trovano superfici a
   contatto. **Indaga perché** e riporta la causa. Non ti chiedo di forzarle a
   diventare quattro: ti chiedo di sapere se è geometria legittima (due
   membrature che si toccano su uno spigolo e non su una faccia, dove un `*TIE`
   non ha superficie su cui posare) oppure un difetto del taglio. Se è
   legittima, va scritta come tale nel docstring; se è un difetto, dillo e
   fermati prima di correggerlo, che decidiamo insieme il verso.

   Questo si vede **solo** perché il giro 1 ha separato `giunzioni` da `ties`:
   col campo unico di prima sarebbe rimasto invisibile.

## Regole del giro

- Ogni numero che scrivi in un docstring o in un commento: o l'hai misurato in
  questa sessione, o non lo scrivi.
- Ogni test nuovo dichiara quale mutazione lo uccide, e tu quella mutazione
  **l'applichi davvero** e verifichi che uccida. Se sopravvive, dillo invece di
  aggiustare il test finché torna.
- Nessun numero del provino in `src/`. Nei test sì.
- Percorsi espliciti nel `git add`. Niente push, niente merge.
- **Niente `git stash`**: lo stash è condiviso con il checkout principale e con
  ogni altra sessione. Se trovi nell'albero una modifica che non è tua, non
  toccarla: segnalala e fermati.

La suite parte da **500 passati**. Riporta il numero che leggi tu.

E come sempre: se questa correzione ti risulta sbagliata, fermati e dillo con la
prova. In questa fase è già successo cinque volte che avesse ragione chi eseguiva
e non chi scriveva il piano — questo giro nasce dalla sesta.
