# Il perimetro del progetto: MeshRec si chiude sul deck

Data: 2026-08-31


> **Nota del 02/09/2026.** Questa spec resta come è stata scritta: registra la
> decisione presa il 31/08/2026 e le ragioni che la reggevano. Due giorni dopo
> l'autore ha provato l'interfaccia della linea parallela e l'ha dismessa: i due
> branch che la portavano avanti sono stati eliminati e il codice già in `main`
> è uscito con la mappa
> [#161](https://github.com/maeurong/Tesi/issues/161). Il perimetro deciso qui
> non cambia — il prodotto si chiude sul deck — ma la sezione E parla di una
> linea che non esiste più, e `docs/linea-analisi-integrata.md` è stato
> cancellato invece che scritto.
>
> Una correzione di fatto, non di decisione: qui sotto si legge che il prior
> «misura telaio, membrature e armature». L'armatura il prior non l'ha mai
> misurata — si dichiarava in configurazione. La frase era falsa già il giorno
> in cui è stata scritta.

## La decisione

MeshRec, come prodotto della tesi, va **dalla nuvola di punti al deck `.inp`**.
L'analisi strutturale si esegue in Abaqus, a mano, sul deck che il programma ha
prodotto; i suoi risultati sono materiale della tesi, non un'uscita del software.

Il pre-processore integrato (step 12, il prior geometrico) e il solutore
integrato (step 13, CalculiX e OpenSees), con la schermata che li governa,
restano nel repository e restano funzionanti, ma escono dal perimetro dichiarato:
sono una **linea di sviluppo**, portata avanti in parallelo, che un giorno potrà
diventare il prodotto principale se dimostrerà di reggere.

Questa non è una riduzione di ambizione travestita da scelta: chiudere sul deck
è la strada che i tutor avevano indicato all'inizio, e sposta il carico della
prova su un formato standard. Un deck corretto e riproducibile lo verifica
chiunque abbia Abaqus. Una soluzione prodotta da un solutore interno la verifica
soltanto chi si fida della catena che l'ha prodotta — e, se la tesi presenta
numeri Abaqus mentre il programma ne calcola altri con CalculiX, ogni scostamento
fra i due motori diventa qualcosa da spiegare in discussione, a partire dal fatto
che elementi e condizioni al contorno non si comportano identici nei due.

## Dove passa il taglio, e perché lì

Il taglio cade **fra lo step 11 e lo step 12**: il programma si chiude quando ha
scritto il deck.

Lo step 12 non è il solutore — è il prior geometrico, tutto in-process, che
misura telaio, membrature e armature. Sarebbe stato difendibile tenerlo dentro,
perché è pre-processore e non analisi. È stato messo fuori perché il perimetro
guadagna più dalla nettezza del racconto — «undici passaggi, poi Abaqus» — che
dalla capacità in più, e perché il prior serve principalmente a ciò che sta a
valle di esso.

Il costo di questa scelta è stato misurato, non stimato. La sola funzionalità
dello step 11 che dipende dal prior è l'attribuzione delle regioni per materiale:
quando `cfg.regioni` è popolato, `_membrature_del_prior`
(`meshrec/src/meshrec/core/pipeline.py:250-281`) rilegge `12_wall.json`, che a
quello step non esiste ancora in una corsa fresca. **Nessuna configurazione in
`meshrec/casi/` usa `regioni`**: la dipendenza esiste nel codice ma non è
esercitata da alcun caso reale. Chi ne avesse bisogno ha già la via d'uscita, e
il messaggio di rifiuto la nomina: eseguire il solo prior con `meshrec wall`,
oppure chiedere `--to-step 12` esplicitamente. Nessun codice va quindi
riscritto per spostare il perimetro.

## Che cosa cambia

### A. I documenti dichiarano il perimetro

Tre file portano il perimetro, e oggi due lo contraddicono.

`README.md:6-9` promette «tredici passaggi — segmentazione della nuvola di punti,
ricostruzione della superficie, riempimento a tetraedri, esportazione del
modello, soluzione». La soluzione esce dall'elenco; al suo posto entra che cosa
si fa del `.inp` una volta ottenuto, che oggi il README non dice affatto.

`PRODUCT.md` si contraddice già da solo: la sezione *Users* (riga 14) descrive
l'utente come uno che conosce «i dodici step della pipeline, il solutore che sta
nella propria schermata», mentre *Capabilities and Constraints* (righe 94-99)
elenca come capacità confermate «undici step dalla lettura della nuvola al deck
pronto all'analisi». La seconda formulazione è già quella giusta e resta; la
prima si allinea. Si aggiunge inoltre una sezione **Perimetro** che dice in
modo esplicito dove il prodotto si ferma e che cosa sta oltre — perché oggi il
documento lo lascia dedurre, e una deduzione non è una dichiarazione.
La riga 88-90, «il file `.inp` va in Abaqus o CalculiX», è già allineata e non
si tocca.

`AGENTS.md:76-77` descrive `STEP_KEYS` come «i tredici passaggi in ordine, dal
caricamento della nuvola di punti fino alla soluzione». La descrizione della
tabella resta vera — le chiavi sono tredici — ma va aggiunto che il prodotto si
ferma all'undicesima e che le ultime due appartengono alla linea di sviluppo.
È il file che legge per primo chiunque, umano o agente, apra il repository: se
il perimetro non è scritto lì, non è scritto.

### B. Il comportamento predefinito rispetta il perimetro

`RunConfig.to_step` (`meshrec/src/meshrec/core/config.py:669`) passa da **12 a
11**. È l'unica modifica di comportamento dell'intero lavoro, ed è quella che
impedisce ai documenti di raccontare una cosa mentre il programma ne fa
un'altra: senza di essa, una corsa normale continuerebbe a calcolare un
artefatto che il perimetro dichiara fuori.

La descrizione del campo va riscritta, non ritoccata. Il testo attuale
argomenta con cura perché il predefinito si fermi a 12 invece che a 13; quel
ragionamento resta valido per lo step 13 e va conservato, ma la conclusione
cambia e il motivo nuovo — il perimetro del prodotto — va scritto accanto a
quello vecchio, non al suo posto.

Restano invariati: il tetto a 13, perché la capacità non si perde e chi la
chiede la ottiene; `from_step`, che si ferma a 12 per una ragione indipendente;
e `sweep.py`, che chiede `--to-step 12` esplicito al sottoprocesso invece di
ereditare il predefinito, proprio perché non deve dipendere da come il
predefinito cambia. Quella decisione, presa allora, è ciò che rende questo
cambio innocuo oggi.

### C. La schermata dell'analisi resta, ma dice che cos'è

Nessuna rimozione: né `core/wall.py`, né `core/solve.py`, né `core/opensees.py`,
né `core/telaio.py`, né le route del server, né le circa duemila righe di
interfaccia che le servono. Rimuovere codice funzionante e testato distruggerebbe
lavoro senza guadagno, e renderebbe doloroso il rientro dei diciotto commit che
la linea parallela ha già prodotto.

Alla sezione `<section class="analisi" id="analisi">`
(`meshrec/src/meshrec/ui/index.html:317`) si aggiunge, sotto il titolo, una riga
che inquadra la schermata: è una linea di sviluppo, e i risultati della tesi
vengono da Abaqus. Una frase. Serve perché chi apre l'interfaccia e trova
«Analisi strutturale — step 13» deve poter capire, senza chiedere, perché i
documenti dicono che il prodotto si ferma prima.

### D. I risultati Abaqus entrano nel repository

Una cartella `analisi-abaqus/` a radice, con un sottodirettorio per corsa
analizzata. Ciascuno
contiene il deck che è entrato in Abaqus, l'output che ne è uscito, e una nota
di provenienza: versione di Abaqus, impostazioni dell'analisi, e la corsa
MeshRec che ha generato quel deck.

La ragione è la stessa che regge tutto il progetto. Il registro degli esperimenti
già lega ogni corsa alla propria configurazione, alle impronte degli artefatti e
al commit del codice; se i risultati vivessero solo nella tesi stampata, la
catena si spezzerebbe esattamente all'ultimo anello, quello che al lettore
interessa di più. Con i risultati accanto al deck, la provenienza è ricostruibile
per intero: dai punti al numero.

Il lavoro di questa parte è la struttura e il modello della nota. I file veri li
deposita l'autore, che è l'unico ad averli.

### E. La linea parallela viene dichiarata invece che lasciata implicita

Esistono due branch non mergiati che portano avanti l'analisi integrata:
`worktree-notte-analisi-strutturale`, **ventitre commit** avanti a `origin/main`
al 31/08/2026, con una spec dell'analisi strutturale «dal telaio alle verifiche»; e
`worktree-wayfinder-analisi-strutturale`, tre commit, con una mappa le cui issue
pianificano di costruire le verifiche NTC ed Eurocodice **dentro MeshRec**.

Il primo dei due esiste soltanto in locale. Ventitre commit che vivono in un
worktree e in nessun altro posto sono lavoro a rischio di sparizione: vanno
spinti su `origin` prima di ogni altra cosa.

Poi serve `docs/linea-analisi-integrata.md`, breve, che dica che cos'è quella linea, dove
vive, e perché sta fuori dal perimetro della tesi. Serve soprattutto a
riconciliare le sue issue con questa decisione: costruire le verifiche di norma
«in MeshRec» non contraddice il perimetro se si intende MeshRec-la-linea, lo
contraddice se si intende MeshRec-il-prodotto-di-tesi. Oggi la frase non
distingue, e una mappa che punta in direzione opposta alla spec è il genere di
ambiguità che costa settimane quando qualcuno la esegue alla lettera.

### F. La CI non si tocca

Il workflow ha due job (`.github/workflows/suite.yml`): `suite`, che gira sulla
matrice di piattaforme con gli `addopts` predefiniti e non richiede alcun
solutore esterno; e `benchmark`, che installa `calculix-ccx`, **fallisce se `ccx`
manca o non stampa una versione**, ed esegue la suite intera.

Quel secondo job verifica oggi la linea di sviluppo e non il prodotto. Continua
a dare segnale, e romperlo per coerenza formale significherebbe spegnere una
verifica che funziona. Resta com'è; la spec si limita a registrare che cosa
copre, così che nessuno lo scambi in futuro per un controllo sul perimetro.

## Che cosa non cambia

Nessun file viene cancellato. Nessun test viene rimosso o disattivato. Nessuna
route del server viene chiusa. Il tetto di `to_step` resta 13 e chi chiede lo
step 13 lo ottiene. I documenti di fase e i verbali in `docs/` restano intatti:
raccontano che cosa è successo, e ciò che è successo non cambia perché cambia il
perimetro.

## Come si verifica che è fatto

- Una corsa senza argomenti si ferma dopo `11_export` e scrive il deck.
- `--to-step 12` continua a produrre `12_wall.json`, e `meshrec solve` continua
  a risolvere.
- I test che codificano il predefinito sono aggiornati con la ragione scritta
  accanto. Sono quattro file — `test_config.py`, `test_pipeline.py`,
  `test_server.py`, `test_sweep.py` — e due di essi asserivano `to_step == 12`
  in modo diretto: il criterio «la suite passa senza toccare i test» sarebbe
  stato sbagliato, perché quei test dichiarano il predefinito, e cambiarlo senza
  cambiarli significherebbe che nessuno lo stava verificando.
- Il numero di test falliti nella suite intera resta identico a quello ottenuto
  sugli stessi sorgenti di `origin/main` nello stesso ambiente.
- `README.md`, `PRODUCT.md` e `AGENTS.md` dicono lo stesso perimetro, e nessuno
  dei tre promette la soluzione come uscita del prodotto.
- `worktree-notte-analisi-strutturale` è presente su `origin`.
