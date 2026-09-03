// Orchestrazione dell'interfaccia. Ogni numero mostrato viene dal server.

const ETICHETTE = {
  "01_load": "Lettura", "02_segment": "Segmentazione", "03_downsample": "Riduzione",
  "04_normals": "Normali", "05_reconstruct": "Superficie", "06_repair": "Riparazione",
  "07_surface_quality": "Qualità superficie", "08_simplify": "Semplificazione",
  "09_tetrahedralize": "Tetraedri", "10_volume_quality": "Qualità volume",
  "11_export": "Esportazione", "12_wall": "Prior geometrico",
};

// Le etichette delle metriche e le chiavi d'allarme stanno in un modulo loro
// (etichette.js): sono dati, non logica dell'orchestrazione, e un modulo
// senza import si valuta da solo in un banco senza server.
import { ETICHETTE_METRICHE, METRICHE_D_ALLARME } from "/ui/etichette.js";

// Che cosa fa uno step, in una riga. Il nome da solo e' un'etichetta:
// «Riduzione» non dice che dirada i punti a passo costante, e chi apre il
// pannello per la prima volta deve decidere se premere «Esegui» senza sapere
// che cosa sta per succedere alla propria nuvola.
//
// Per CHIAVE e non per numero: la chiave sta in ogni voce di run_state, quindi
// il proposito non va indovinato dall'ordine -- e uno step aggiunto in mezzo
// alla catena non fa scivolare tutte le descrizioni di uno.
//
// Uno step senza una voce qui non prende una frase inventata: l'intestazione
// resta il solo titolo. E' la stessa regola di nomeDelloStep, che su una
// chiave sconosciuta ripiega sul numero invece di fabbricare un nome.
const PROPOSITI = {
  "01_load": "Legge la nuvola dal file, la porta in millimetri e ne misura ingombro e spaziatura.",
  "02_segment": "Tiene i soli punti dell'oggetto: toglie il rumore, ritaglia via il resto della stanza, estrae i piani che la delimitano e raggruppa ciò che resta, tenendo il gruppo scelto.",
  "03_downsample": "Dirada i punti a passo costante: meno punti, stessa forma, calcolo più leggero.",
  "04_normals": "Stima in ogni punto da che parte guarda la superficie: serve alla ricostruzione.",
  "05_reconstruct": "Costruisce dai punti una superficie fatta di triangoli.",
  "06_repair": "Chiude i buchi, toglie i pezzi staccati e rigira le facce finché la superficie racchiude un volume.",
  "07_surface_quality": "Misura la superficie: se è chiusa, quanto sono regolari i triangoli, quanto si scosta dalla nuvola di partenza.",
  "08_simplify": "Rifà o dirada i triangoli. È opzionale: finché non si rifanno a misura uniforme la superficie passa avanti com'è.",
  "09_tetrahedralize": "Riempie il volume di tetraedri: è il maglio su cui si calcola.",
  "10_volume_quality": "Misura il maglio: elementi invertiti, volumi, angoli, allungamento.",
  "11_export": "Scrive il file .inp per Abaqus o CalculiX, con materiale, gravità e set di nodi.",
  "12_wall": "Cerca nella geometria le regioni che sembrano membrature, e le propone come prior.",
};

// Lo step che non sta nella colonna, e quello che chiude la colonna.
//
// Per CHIAVE e non per numero, come ETICHETTE e PROPOSITI: la chiave sta in ogni
// voce di run_state, quindi il confine non va indovinato dall'ordine e uno step
// aggiunto in mezzo alla catena non lo farebbe scivolare di uno.
//
// Lo step 12 resta lo step 12 -- il numero glielo da' steps.STEP_KEYS e non
// cambia -- ma sta fuori dalla colonna: e' misura della scansione, non ha
// interfaccia, e `to_step` predefinito vale 11 (core/config.py), il deck, che
// e' dove si chiude il perimetro del prodotto.
const STEP_DEL_PRIOR = "12_wall";

// Nodo piu' proprieta' in una riga.
const elemento = (tag, proprieta) => Object.assign(document.createElement(tag), proprieta);

// La coda di ogni rifiuto che l'interfaccia non sa spiegare: un corpo che
// non si legge e' un guasto fra server e pagina, non un errore di chi guarda,
// e l'unica cosa che si puo' fare e' ripartire. Detto una volta e riusato,
// cosi' i cinque messaggi della stessa famiglia offrono lo stesso rimedio.
// Il sesto, in modello.js, ha un rimedio suo -- rieseguire lo step, che
// riscrive le metriche -- e non passa da qui apposta.
const RIMEDIO = "Ricarica la pagina; se il messaggio torna, riavvia «meshrec serve» dal terminale.";

async function caricaStato() {
  const risposta = await fetch("/api/run");
  const corpo = await corpoLetto(risposta);
  // Un 200 con un corpo che non si legge, o senza l'elenco degli step, faceva
  // sollevare qui sotto (disegnaStep su un valore che non e' un array) fuori
  // da qualunque catch: la pagina restava bianca, senza un solo messaggio.
  // == e non ===: un corpo intero non e' mai un null legittimo su questo
  // endpoint (a differenza di un campo nullabile innestato, che e' il caso per
  // cui la distinzione undefined/null di corpoLetto esiste). Un null vero
  // qui passava la guardia e faceva sollevare la riga sotto fuori da ogni
  // catch, esattamente cio' che questa guardia doveva impedire.
  // Nessuna corsa aperta non e' un errore: e' lo stato in cui il programma si
  // apre la prima volta, quando nessuno gli ha passato una configurazione.
  // `=== false` e non `!corpo?.legata`: un corpo illeggibile deve continuare a
  // cadere nella guardia qui sotto, non a mostrare la schermata d'ingresso come
  // se il server avesse detto qualcosa di sensato.
  if (corpo?.legata === false) {
    mostraIngresso();
    return;
  }
  if (corpo == null || !Array.isArray(corpo.steps)) {
    // In testata e non in #errore: a questo punto le tre schermate sono
    // ancora tutte nascoste, e #errore vive dentro #lavoro. Scritto la'
    // il messaggio esisteva e nessuno lo vedeva: la pagina restava bianca
    // con la sola testata, che e' l'unica regione sempre a video.
    // #esito e' anche la riga che aggiornaDaStato svuota sul fronte di salita
    // di una corsa e riscrive su quello di discesa: se lo stream degli eventi
    // porta un fronte mentre questo messaggio e' a video, lo copre. Accettato:
    // un fronte che arriva vuol dire che il server risponde, e la corsa che
    // annuncia e' il fatto piu' recente.
    mostraEsito(
      "il server ha risposto con uno stato della corsa che non si legge. " + RIMEDIO,
      null,
    );
    return;
  }
  mostraSchermata("lavoro");
  document.getElementById("cambia-corsa").hidden = false;
  document.getElementById("corsa").textContent = corpo.out_dir;
  disegnaStep(corpo.steps);
  // Aprire una corsa e trovare il centro bianco. La corsa ha gia' i propri
  // artefatti sul disco: si mostra il piu' avanzato che possiede, invece di
  // aspettare un clic per far vedere che il programma funziona. E' la sola
  // cosa che questa schermata puo' fare, all'apertura, per chi la pipeline non
  // l'ha mai vista girare.
  //
  // La coda della pipeline e non uno step scelto a mano: `passoDaMostrare`
  // cammina a monte da li' e si ferma sul primo disegnabile. Se non ne trova
  // nessuno cade nel ramo che scrive «esegui lo step 1» e scopre lo stato
  // vuoto, che sono due strade gia' scritte: qui non se ne aggiunge nessuna.
  // Da `corpo.steps.length` e non da un 13 battuto qui: quanti step ci sono lo
  // dichiara il server, ed e' lo stesso elenco appena disegnato.
  //
  // `stepScelto` va scritto e non lasciato a null: il cambio d'asse del taglio
  // chiama `passoDaMostrare(stepScelto)`, e con null il comando del taglio
  // sparirebbe sotto le dita di chi lo sta usando su una geometria che si vede.
  // Un clic dell'utente lo sovrascrive subito, e la generazione che apre butta
  // via questa geometria se arriva dopo.
  //
  // La zona morta di `let stepScelto` non morde: questa riga sta dopo la prima
  // attesa, e li' il modulo e' gia' stato valutato per intero -- la stessa
  // ragione per cui `disegnaStep` puo' leggere `stepAperto`.
  stepScelto = corpo.steps.length;
  ricaricaVista(stepScelto);
}

// --- Schermata d'ingresso --------------------------------------------------
//
// Una corsa nasce da un file di punti, non da uno yaml scritto a mano: e' la
// sola strada che chi riceve una scansione e apre il programma puo' davvero
// percorrere. Legata una corsa la pagina si ricarica invece di ricucire lo
// stato a mano: l'avvio e' gia' la sequenza giusta (stato, step, flusso degli
// eventi), e riscriverne una seconda copia qui sarebbe due strade
// per lo stesso risultato, con una che invecchia.

const rigaErroreIngresso = document.getElementById("ingresso-errore");

// Un contatore fresco per richiesta, come apriGeometria/apriBattuta/apriAzione:
// numera le quattro strade che scrivono nella stessa riga d'errore e nello
// stesso elenco. Due voci cliccate a breve distanza sono due PUT in volo, e il
// bottone disabilitato ferma il doppio clic sulla stessa voce ma non il clic
// sull'altra. Ogni gestore qui sotto lo apre prima della propria attesa; il
// perche' e' questo, e non viene ripetuto a ognuno.
let ultimoIngresso = 0;

function apriIngresso() {
  ultimoIngresso += 1;
  return ultimoIngresso;
}

// Le due schermate si escludono: chi ne scopre una nasconde l'altra, da un
// punto solo, cosi' non esiste uno stato in cui si vedono entrambe o nessuna.
// Quale delle due schermate e' a video, e l'esclusione sta in un punto solo.
//
// Scritta a mano in ogni transizione era gia' stata dimenticata due volte nello
// stesso giro. `#cambia-corsa` vive nella testata, cioe' fuori da <main>,
// quindi si clicca da tutte e due.
function mostraSchermata(quale) {
  for (const nome of ["ingresso", "lavoro"]) {
    document.getElementById(nome).hidden = nome !== quale;
  }
}

function mostraIngresso() {
  mostraSchermata("ingresso");
  document.getElementById("cambia-corsa").hidden = true;
  disegnaIngresso();
}

// Torna alla scelta della corsa senza riavviare `serve`. Non slega niente sul
// server: la corsa aperta resta tale finche' non se ne sceglie un'altra, e
// l'elenco la marca.
document.getElementById("cambia-corsa").addEventListener("click", mostraIngresso);

async function disegnaIngresso() {
  const richiesta = apriIngresso();
  const risposta = await fetch("/api/corse").catch(serverMuto);
  const rifiuto = risposta.ok ? null : await ragioneDelRifiuto(risposta);
  const corpo = risposta.ok ? await corpoLetto(risposta) : null;
  // Dopo l'ultima attesa e prima della prima scrittura, come le altre tratte.
  if (superata(richiesta, ultimoIngresso)) return;
  if (rifiuto !== null) {
    rigaErroreIngresso.textContent = rifiuto;
    return;
  }
  if (corpo == null || !Array.isArray(corpo.corse)) {
    rigaErroreIngresso.textContent =
      "il server ha risposto con un elenco di corse che non si legge. " + RIMEDIO;
    return;
  }
  const elenco = document.getElementById("corse-elenco");
  elenco.replaceChildren();
  document.getElementById("corse-vuoto").hidden = corpo.corse.length > 0;
  document.getElementById("corse-titolo").textContent = `Corse già in ${corpo.radice}`;
  // Dalla piu' recente: la domanda che si fa chi riapre il programma e' «quale
  // stavo usando», e l'ordine alfabetico non le risponde. Le corse che non
  // portano una data (config sparito fra la lettura e lo stat) vanno in fondo
  // invece di vincere con un undefined.
  const corse = [...corpo.corse].sort((a, b) => (b.modificata ?? 0) - (a.modificata ?? 0));
  for (const corsa of corse) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "bottone corsa-voce";
    bottone.dataset.nome = corsa.nome;
    if (corsa.nome === corpo.corrente) bottone.setAttribute("aria-current", "true");
    const stato = corsa.errore
      ? `la configurazione non si legge — ${corsa.errore}`
      : `${corsa.nuvola}${corsa.materiale ? ` — ${corsa.materiale}` : " — materiale non dichiarato"}`;
    bottone.append(
      elemento("span", {
        className: "corsa-nome", textContent: corsa.nome,
      }),
      // Cio' che il server ha letto, non una descrizione inventata: una corsa
      // rotta lo dice qui invece di sparire dall'elenco.
      elemento("small", {
        className: "aiuto",
        textContent: corsa.riferimento ? `${stato} — di riferimento, sola lettura` : stato,
      }),
    );
    // aria-disabled e non disabled: una corsa che non si legge e' l'unica voce
    // che porta una spiegazione, e `disabled` la toglierebbe dalla navigazione
    // da tastiera e dal lettore di schermo — proprio a chi quella spiegazione
    // serve di piu'. Il gestore si ferma da se'.
    if (corsa.errore) bottone.setAttribute("aria-disabled", "true");
    bottone.addEventListener("click", async () => {
      if (bottone.getAttribute("aria-disabled") === "true") return;
      const richiesta = apriIngresso();
      bottone.disabled = true;
      rigaErroreIngresso.textContent = "";
      const esito = await fetch("/api/corrente", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: corsa.nome }),
      }).catch(serverMuto);
      const rifiuto = esito.ok ? null : await ragioneDelRifiuto(esito);
      if (superata(richiesta, ultimoIngresso)) return;
      if (rifiuto === null) {
        location.reload();
        return;
      }
      rigaErroreIngresso.textContent = rifiuto;
      bottone.disabled = false;
    });
    elenco.append(bottone);
  }
}

// Le due condizioni che il modello rifiuterebbe in inglese, dette in italiano
// prima di partire. Non e' una seconda validazione: il dominio lo decide il
// modello e basta, e tutto il resto arriva ancora dal server. Sono le due
// grafie che chiunque sbaglia al primo tentativo, e i rifiuti di pydantic
// ("String should match pattern '^[A-Za-z0-9_.-]+$'") sarebbero la prima cosa
// che si legge di un'interfaccia dichiarata italiana. Pura e di primo livello,
// come valoreScritto: si prova senza un motore di DOM.
function ragioneLocale(nome, nuvola) {
  if (!nome) return "dai un nome alla corsa: diventa il nome della cartella in runs/";
  if (!/^[A-Za-z0-9_.-]+$/.test(nome)) {
    return "il nome della corsa accetta lettere, cifre, punto, trattino e trattino "
      + "basso: niente spazi, niente barre, niente accenti";
  }
  if (!nuvola) return "indica il percorso del file di punti da cui far nascere la corsa";
  return null;
}

// Il selettore file lo apre il server, non la pagina: `<input type="file">`
// restituisce un oggetto File e nasconde la via reale (`C:\fakepath\...`), che
// e' proprio il dato che serve. Il programma gira sulla stessa macchina del
// file, quindi la finestra la puo' aprire lui.
document.getElementById("sfoglia-nuvola").addEventListener("click", async (evento) => {
  const bottone = evento.currentTarget;
  const campo = document.getElementById("nuova-nuvola");
  const richiesta = apriIngresso();
  bottone.disabled = true;
  rigaErroreIngresso.textContent = "";
  const risposta = await fetch("/api/sfoglia", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Da dove era rimasto: riaprire il selettore deve tornare nella cartella
    // di prima, non alla radice ogni volta.
    body: JSON.stringify({ iniziale: campo.value.trim() }),
  }).catch(serverMuto);
  const rifiuto = risposta.ok ? null : await ragioneDelRifiuto(risposta);
  const corpo = risposta.ok ? await corpoLetto(risposta) : null;
  if (superata(richiesta, ultimoIngresso)) return;
  bottone.disabled = false;
  if (rifiuto !== null) {
    rigaErroreIngresso.textContent = rifiuto;
    return;
  }
  if (corpo === undefined) {
    rigaErroreIngresso.textContent = "il server ha risposto con un percorso che non si legge";
    return;
  }
  // Annullare non e' un errore e non cancella quello che c'era: `percorso` e'
  // null per contratto, e sovrascrivere il campo con una stringa vuota
  // punirebbe chi apre la finestra per sbaglio.
  if (corpo?.percorso) campo.value = corpo.percorso;
});

// Sul `submit` del form e non sul clic del bottone: da tastiera Invio manda il
// form, e un gestore appeso al solo clic non lo raggiungeva. Il bottone e' di
// tipo submit, quindi il clic passa di qui a sua volta -- un gestore solo, e
// non due strade da tenere allineate.
document.getElementById("nuova-corsa").addEventListener("submit", async (evento) => {
  // Il form non si manda al server da se': la corsa la crea /api/corse.
  evento.preventDefault();
  const bottone = document.getElementById("crea-corsa");
  const richiesta = apriIngresso();
  bottone.disabled = true;
  rigaErroreIngresso.textContent = "";
  const nome = document.getElementById("nuova-nome").value.trim();
  const nuvola = document.getElementById("nuova-nuvola").value.trim();
  const locale = ragioneLocale(nome, nuvola);
  if (locale !== null) {
    rigaErroreIngresso.textContent = locale;
    bottone.disabled = false;
    return;
  }
  const risposta = await fetch("/api/corse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, nuvola }),
  }).catch(serverMuto);
  const rifiuto = risposta.ok ? null : await ragioneDelRifiuto(risposta);
  if (superata(richiesta, ultimoIngresso)) return;
  if (rifiuto === null) {
    location.reload();
    return;
  }
  rigaErroreIngresso.textContent = rifiuto;
  bottone.disabled = false;
});

// Quale step e' aperto lo sapeva solo una variabile di modulo, e a video non lo
// diceva niente. Marcarlo sta in un punto solo perche' due strade lo chiedono —
// l'elenco riscritto dal flusso degli eventi e il clic che apre il pannello — e
// scritto due volte una delle due resterebbe indietro alla prima modifica.
// aria-current e non una classe: e' l'attributo che porta il significato, il
// foglio ci si aggancia sopra, e cosi' non esiste un nome da tenere allineato
// fra il modulo e il CSS.
function segnaStepAperto(numero) {
  for (const comando of document.querySelectorAll(".step")) {
    if (Number(comando.dataset.numero) === numero) comando.setAttribute("aria-current", "true");
    else comando.removeAttribute("aria-current");
  }
}

// La riga vuota, senza contenuto: il contenuto lo scrive disegnaStep, che la
// riusa. Un <button> e non il <li> con un gestore sopra — undici voci d'elenco
// con cursor: pointer erano l'intera interfaccia pilotabile col solo mouse
// (WCAG 2.1.1, livello A) e annunciate come righe inerti (WCAG 4.1.2). Il
// gestore delegato piu' sotto non cambia: il clic sale dal bottone e
// closest(".step") lo trova, e con lui Invio e Spazio, che un bottone da' di suo.
// Lo stato resta sul <li> e il comando gli sta dentro: i selettori di stato del
// foglio sono discendenti (.stato-fallito .step-stato), quindi continuano a
// valere senza toccare un solo nome di classe.
function nuovaRiga() {
  const riga = document.createElement("li");
  const comando = document.createElement("button");
  comando.type = "button";
  comando.className = "step";
  // Il numero dello step, e sta a video perche' l'interfaccia parla per numeri:
  // «esegui lo step 1», «e' lo step 12», «lo step 11 si ferma finche'...», «step
  // 5 in corso». Tutte istruzioni che indicavano una coordinata che la colonna
  // non mostrava da nessuna parte -- l'<ol> ha list-style: none -- e chi apre il
  // programma per la prima volta aveva undici nomi e nessun modo di contarli.
  // Scritto da `voce.numero` e non dalla posizione nell'elenco: il numero e' un
  // dato del server, e un contatore CSS lo indovinerebbe dalla riga.
  const numero = document.createElement("span");
  numero.className = "step-numero";
  const nome = document.createElement("span");
  nome.className = "step-nome";
  const stato = document.createElement("span");
  stato.className = "step-stato";
  comando.append(numero, nome, stato);
  riga.append(comando);
  return riga;
}

// Lo stato degli step per come il server l'ha DICHIARATO l'ultima volta. Non
// e' cio' che sta sul disco, e la differenza conta: i due rami di rifiuto piu'
// sotto esistono proprio per quando divergono. `disegnaStep` e' l'unico imbuto
// per cui arriva (dal caricamento e dallo scorrere degli eventi, che mandano
// entrambi run_state), quindi una riga la' lo tiene fresco da tutte e due le
// strade.
let ultimoStato = [];

// Lo step la cui geometria si puo' mostrare al posto di quella di `numero`.
//
// Quattro step su dodici non scrivono GEOMETRIA, per costruzione e non per
// guasto: il 7 e il 10 misurano, l'11 scrive un deck e il 12 un prior
// (pipeline.ARTIFACTS ha otto chiavi su dodici). Cliccarli svuotava il
// viewport.
//
// Servono DUE condizioni:
//
// 1. lo step deve avere SCRITTO qualcosa (`artefatto` non nullo). Non basta la
//    tabella: lo step 8 scrive solo a semplificazione abilitata
//    (`registra(8, ..., None)` altrimenti, che e' il predefinito), e una corsa
//    non ancora eseguita non ha scritto niente.
// 2. cio' che ha scritto dev'essere DISEGNABILE. Non basta il registro, e la
//    seconda condizione l'ha insegnata una corsa vera: in
//    runs/lab_crop/steps.json lo step 11 compare con
//    `artefatto: wall_model.inp`, cioe' NON nullo. Un artefatto ce l'ha
//    davvero, ma e' un deck di calcolo; chiederlo porta a /api/cloud/11, che
//    il server rifiuta perche' l'11 non e' fra le chiavi di ARTIFACTS. Lo
//    schermo vuoto di nuovo, per una strada nuova.
//
// `null` quando a monte non c'e' niente che soddisfi entrambe: e' l'unico caso
// in cui svuotare la vista e' onesto.
const STEP_CON_GEOMETRIA = new Set([1, 2, 3, 4, 5, 6, 8, 9]);

function passoDaMostrare(numero) {
  for (let n = numero; n >= 1; n -= 1) {
    const voce = ultimoStato.find((v) => v.numero === n);
    if (voce?.artefatto && STEP_CON_GEOMETRIA.has(n)) return n;
  }
  return null;
}

// Il nome che l'utente vede nella colonna, per la coda della didascalia: dire
// «artefatto dello step 6» accanto a una riga che si chiama «Riparazione»
// costringe a contare le righe per capire di quale si parla.
function nomeDelloStep(numero) {
  const voce = ultimoStato.find((v) => v.numero === numero);
  return ETICHETTE[voce?.chiave] ?? `step ${numero}`;
}

// --- Il modello al fronte ---------------------------------------------------

// La tratta del pannello «Modello» vive in modello.js: le funzioni pure e la
// parte con DOM/fetch, costruita qui perche' `superata`/`serverMuto`/
// `corpoLetto`/`valoreDellaMetrica` sono di app.js e modello.js non importa
// da qui (altrimenti sarebbe un ciclo, visto che app.js importa da li').
import { creaPannelloModello } from "/ui/modello.js";

const { aggiornaModello } = creaPannelloModello({
  fetch: (...args) => fetch(...args), elemento, superata, serverMuto, corpoLetto,
  valoreDellaMetrica, ETICHETTE, STEP_DEL_PRIOR,
});

function disegnaStep(steps) {
  // Lo stato di prima, letto prima di sovrascriverlo: e' l'unica cosa che
  // distingue «lo step 6 e' appena diventato valido» da «lo step 6 e' valido»,
  // e la colonna diceva il secondo anche nell'istante in cui accadeva il primo.
  // Da qui e non dal DOM: `className` sulla riga e' cio' che il foglio legge, e
  // farlo portare anche la memoria di cio' che c'era prima significherebbe
  // riscrivere lo stato per esprimere un evento.
  //
  // Vuoto alla prima passata, e non e' un caso limite da tollerare ma il
  // comportamento voluto: al primo disegno tutti gli step sarebbero
  // «cambiati» rispetto a niente, e la colonna si accenderebbe tutta all'avvio
  // dicendo che e' appena successo qualcosa che invece era gia' cosi'. Legare
  // una corsa ricarica la pagina, quindi non esiste una seconda strada per cui
  // questa mappa arrivi popolata da una corsa diversa.
  const precedente = new Map(ultimoStato.map((voce) => [voce.numero, voce.stato]));
  ultimoStato = steps;
  // Lo stato resta intero e a essere filtrata e' la sola VISTA. `passoDaMostrare`
  // cammina a monte da `corpo.steps.length`, che vale 12: filtrando `ultimoStato`
  // invece dell'elenco, la geometria del prior diventerebbe irraggiungibile per
  // una strada che non guarda nessuno.
  const pipeline = steps.filter((voce) => voce.chiave !== STEP_DEL_PRIOR);
  const elenco = document.getElementById("elenco-step");
  // Le righe si costruiscono una volta sola e poi si aggiornano sul posto.
  // Ricostruirle a ogni evento — due volte al secondo mentre la pipeline gira —
  // le buttava via tutte: finche' erano <li> inerti non si perdeva niente, ma
  // da quando lo step e' un comando focalizzabile chi naviga da tastiera
  // perderebbe il fuoco su <body> una sessantina di volte durante uno step da
  // 34 secondi, e un lettore di schermo la posizione del cursore. La
  // correzione della tastiera, da sola, avrebbe aperto il difetto che chiudeva.
  // Il foglio aveva gia' visto meta' del problema: la nota sul movimento
  // rinuncia ad animare l'elenco per la stessa riscrittura continua.
  if (elenco.childElementCount !== pipeline.length) {
    elenco.replaceChildren(...pipeline.map(() => nuovaRiga()));
  }
  pipeline.forEach((voce, indice) => {
    const riga = elenco.children[indice];
    const comando = riga.firstElementChild;
    riga.className = `stato-${voce.stato.replace(" ", "-")}`;
    // Il marchio del cambio, che il foglio anima per mezzo secondo. Messo nel
    // giro in cui lo stato cambia e tolto in quello dopo -- gli eventi di stato
    // arrivano ogni mezzo secondo -- cosi' la volta seguente l'attributo torna
    // ad apparire e l'animazione riparte da se': un attributo che restasse
    // attaccato la lascerebbe girare una volta sola e mai piu'.
    if (precedente.has(voce.numero) && precedente.get(voce.numero) !== voce.stato) {
      riga.dataset.cambiato = "";
    } else {
      delete riga.dataset.cambiato;
    }
    comando.dataset.numero = voce.numero;
    const [numero, nome, stato] = comando.children;
    numero.textContent = voce.numero;
    nome.textContent = ETICHETTE[voce.chiave] ?? voce.chiave;
    stato.textContent = voce.stato;
  });
  // stepAperto e' gia' inizializzato: disegnaStep gira solo da caricaStato, che
  // si sospende sulla prima attesa, e dallo scorrere degli eventi, cioe' sempre
  // dopo che il modulo e' stato valutato per intero.
  segnaStepAperto(stepAperto);
  // Non attesa: `disegnaStep` e' sincrona e gira a ogni fotogramma del flusso.
  // Il ripiego su un guasto a meta' rilettura (azzerare la terna mostrata,
  // cosi' il fotogramma dopo riprova) sta dentro `aggiornaModello` stessa,
  // in modello.js: la terna e' privata di quel modulo, e non e' piu' cosa
  // che questa chiamata possa aggiustare da fuori.
  aggiornaModello(steps);
}

caricaStato();

// Il progresso non e' una percentuale: le librerie di calcolo non ne
// forniscono una, e una barra fabbricata sarebbe un numero plausibile che
// nessuna misura smentisce. Si mostra quale step gira, da quanto, e le righe
// che scrive.
// Il tempo trascorso lo misura il server, dove lo step parte davvero: contato
// qui conterebbe da quando questa pagina ha visto lo stato "in corso", e
// tornerebbe a zero a ogni ricarica mentre il calcolo prosegue.
// Una durata misurata, letta come la direbbe una persona. Sotto il minuto e
// mezzo i secondi bastano; sopra, «312 s» smette di essere una durata e torna
// a essere un numero -- e in questa riga adesso ce ne stanno due accanto, il
// tempo di adesso e quello dell'ultima volta.
//
// Sotto il secondo NON si arrotonda a «0 s». Lo step 8 a semplificazione
// disabilitata dura 1,3e-05 s (misurato, runs/prova/steps.json), e uno zero li'
// si legge «non e' partito» invece di «e' finito prima che si potesse
// misurare»: sarebbe il difetto che PRODUCT.md nomina, uno zero che significa
// «sotto la risoluzione della misura» presentato come «esatto».
//
// Arrotonda PRIMA di dividere: 119,6 s diviso e poi arrotondato dava
// «1 min 60 s».
function durataMisurata(secondi) {
  if (secondi < 1) return "meno di 1 s";
  const tondo = Math.round(secondi);
  if (tondo < 90) return `${tondo} s`;
  return `${Math.floor(tondo / 60)} min ${tondo % 60} s`;
}

// Il tempo che questo stesso step ha impiegato l'ultima volta, se il disco lo
// sa e se e' una misura.
//
// La guardia sul fallito non e' prudenza generica: pipeline.py:574 registra
// `0.0` fisso quando uno step fallisce, che e' un segnaposto e non un
// cronometro. Uno step che e' morto dopo venti secondi di lavoro ha su disco
// «secondi: 0.0», e mostrarlo scriverebbe «0 s» accanto a un numero vero --
// esattamente il numero senza controllo che il primo principio di prodotto
// vieta. "mai eseguito" non ha `secondi` affatto e cade sul typeof.
function ultimaDurata(voce) {
  if (voce === undefined || voce === null) return null;
  if (voce.stato === "fallito") return null;
  if (typeof voce.secondi !== "number") return null;
  return durataMisurata(voce.secondi);
}

// --- Di che cosa parla una corsa, e come e' finita -------------------------

// Un solo `meshrec run` copre from_step..to_step, ma `stato.step` e' il capo di
// PARTENZA e non avanza mai: si fissa in worker.start() e resta li'. Finche' la
// riga portava il solo capo, una corsa da 1 a 11 si annunciava «step 1 in
// corso» dall'inizio alla fine -- misurato: a quattro secondi dall'avvio
// diceva ancora Lettura, che ne era durata 0,03.
//
// Una superficie sola perche' la riga che pulsa e quella dell'esito devono
// nominare la stessa cosa: scritte due volte, una delle due resterebbe
// indietro.
//
// `unoSolo` non e' un dettaglio di resa: e' la condizione che decide se una
// durata si puo' mostrare. `secondi` e' il tempo del solo step di partenza, e
// appiccicarlo a una corsa di undici step lo dichiarerebbe durata dell'intera
// corsa.
function descrizioneDellaCorsa(stato) {
  // Un comando fuori pipeline -- «Ricalcola il prior», «Ricostruisci il
  // modello» -- non ha un numero di step: `worker.start_comando` lascia `step`
  // e `a_step` a null. `nomeDelloStep(null)` ripiega sulla forma «step
  // <numero>», quindi la testata annunciava alla lettera «step null: esecuzione
  // conclusa». Qui un nome da dire non c'e', e si dice quello che la cosa e'.
  // La riga che pulsa il caso lo trattava gia'; l'esito no.
  if (stato.step === null || stato.step === undefined) {
    return { testo: "il comando", unoSolo: true };
  }
  const nome = nomeDelloStep(stato.step);
  // a_step assente e' un frame che non lo porta -- una corsa aperta prima che
  // il server lo mandasse, o un comando fuori pipeline. Si torna al nome del
  // capo, che e' cio' che si sapeva prima e non e' un'invenzione.
  if (stato.a_step === null || stato.a_step === undefined || stato.a_step === stato.step) {
    return { testo: nome, unoSolo: true };
  }
  return { testo: `da ${nome} a ${nomeDelloStep(stato.a_step)}`, unoSolo: false };
}

// Che cosa dire quando una corsa finisce. Pura e di primo livello come
// superata(): e' la decisione che l'interfaccia non prendeva affatto, e presa
// dentro un gestore anonimo non la esegue nessun banco.
//
// Il soggetto delle tre frasi e' «esecuzione» e non il nome dello step: nove
// degli undici nomi sono femminili (Lettura, Segmentazione, Riduzione,
// Superficie, Riparazione, Semplificazione, Esportazione, le due Qualita') e
// due no (Normali, Tetraedri), quindi «Lettura concluso» era sbagliato in nove
// casi su undici e nessun participio accorda con tutti. Con un soggetto fisso
// e femminile l'accordo torna senza una tabella dei generi, e la parola e' gia'
// quella del titolo «Registro dell'esecuzione».
//
// I tre esiti sono distinti perche' sono tre fatti diversi, ed e' la voce del
// progetto: un annullamento e' una scelta di chi guarda, non un guasto.
// L'ordine dei rami conta: un annullamento arriva con un codice d'uscita non
// nullo (il segnale che lo ha fermato), quindi va guardato per primo,
// altrimenti ogni annullamento si annuncerebbe come un fallimento.

// L'ultima riga non vuota che il flusso ha portato: quella che dice che cosa
// e' successo, senza le venti che dicono da dove. E' la riga che chi legge
// cercherebbe per prima, e chi non apre il registro la ha gia' in testata.
function ultimaRigaDelRegistro() {
  const righe = Array.from(document.getElementById("registro").children);
  for (let i = righe.length - 1; i >= 0; i -= 1) {
    const testo = righe[i].textContent.trim();
    if (testo !== "") return testo;
  }
  return "nessun dettaglio";
}

function esitoDellaCorsa(stato) {
  const { testo: soggetto, unoSolo } = descrizioneDellaCorsa(stato);
  // Una corsa finita senza codice d'uscita non e' piu' uno stato possibile: il
  // worker fissa exit_code prima di dichiararsi fermo. Se arriva lo stesso --
  // una start() che solleva prima di avere un figlio, un frame caduto dentro
  // il fork -- si tace. Dirlo «concluso» annuncerebbe riuscita una corsa mai
  // partita, che e' il falso successo per cui esiste tutto questo ramo.
  if (stato.exit_code === null || stato.exit_code === undefined) {
    return { errore: null, esito: null };
  }
  // «interrotta» e non «annullata», e la ragione sta gia' scritta sul bottone
  // (index.html): «Annulla» accanto a una corsa che gira si legge anche come
  // «disfa quello che hai fatto», e il bottone non disfa niente. Rinominato
  // li' e non qui, l'esito continuava a usare proprio la parola da cui il
  // bottone era stato allontanato.
  if (stato.annullato) return { errore: null, esito: `${soggetto}: esecuzione interrotta` };
  if (stato.exit_code !== 0) {
    return {
      // Dove sta, non «qui sotto»: #esito e' nella testata e il registro e'
      // l'ultimo dei quattro titoli della terza colonna, dentro un contenitore
      // che scorre. E' la stessa distanza che il pannello aveva dal proprio
      // nome, e per cui il nome e' stato portato dentro il pannello.
      errore: `${soggetto}: esecuzione fallita (codice ${stato.exit_code}). `
        + `Il motivo è nel registro, in fondo alla colonna Dettaglio: ${ultimaRigaDelRegistro()}`,
      esito: null,
    };
  }
  // La durata la misura il server e la scrive nel file di stato. Quando manca
  // non si mette uno zero ne' un trattino formattato come un numero -- sarebbe
  // una misura fabbricata -- si dice solo che e' finito. Su un intervallo non
  // si mette affatto, per la ragione scritta sopra `descrizioneDellaCorsa`: era
  // il numero piu' in vista dell'applicazione e diceva 0,03 s per una corsa che
  // ne aveva impiegati dieci. La durata intera nessuno la misura oggi, e tacere
  // e' l'unica alternativa che non inventa.
  //
  // Su un intervallo la misura c'e' adesso, e viene dal lavoratore: `durata` e'
  // il tempo del sottoprocesso, cioe' esattamente l'attesa che c'e' stata.
  // Il worker la cronometrava dal primo istante -- `avviato` si fissa in
  // start() e vale per la corsa intera -- e la buttava via a processo morto,
  // quando `da_secondi()` smette di rispondere: la corsa piu' lunga che questo
  // programma sappia fare finiva con la stessa riga muta di uno step da 0,03 s.
  //
  // Sul capo singolo resta invece la misura del file di stato, che e' il tempo
  // dello step senza l'avvio dell'interprete. Due numeri diversi per la stessa
  // attesa sullo stesso schermo sarebbero il difetto, non la copertura: il
  // pannello dello step dichiara quella, e questa riga non la contraddice.
  const misura = unoSolo
    ? ultimaDurata((stato.steps ?? []).find((v) => v.numero === stato.step))
    : durataDellaCorsa(stato);
  // Il deck raggiunto, detto dove si guarda quando la corsa finisce. Lo step 11
  // e' il perimetro dichiarato del prodotto -- dalla nuvola di punti al deck, e
  // li' si ferma -- e atterrava con la stessa riga di uno step qualunque.
  //
  // Solo se e' questa corsa ad arrivarci: un deck valido lasciato li' da una
  // corsa di ieri non e' una cosa appena successa, e annunciarlo adesso sarebbe
  // datare un fatto vecchio col momento in cui lo si legge.
  //
  // E nessun numero: a questo istante `corpoMetriche` e' ancora quello di
  // prima -- apriDettaglio rilegge le metriche DOPO, nel chiamante, ed e' un
  // ordine voluto -- quindi un conteggio di elementi preso da li' descriverebbe
  // la corsa precedente. `stato.steps` invece arriva con questo stesso evento.
  const arrivo = stato.a_step ?? stato.step;
  const deck = arrivo === STEP_CON_DECK
    && (stato.steps ?? []).find((v) => v.numero === STEP_CON_DECK)?.artefatto != null;
  const coda = deck ? " · il deck è pronto, si scarica dallo step 11" : "";
  return {
    errore: null,
    esito: misura === null
      ? `${soggetto}: esecuzione conclusa${coda}`
      : `${soggetto}: esecuzione conclusa in ${misura}${coda}`,
  };
}

// La durata della corsa intera, quando il lavoratore l'ha conservata.
//
// Separata da `ultimaDurata`, che legge la voce di uno step nel file di stato:
// sono due misure di due cose, e una funzione sola che accettasse entrambe le
// forme sarebbe il punto in cui le due si confondono.
function durataDellaCorsa(stato) {
  if (stato.durata_secondi === null || stato.durata_secondi === undefined) return null;
  return durataMisurata(stato.durata_secondi);
}

// Dove finisce l'esito di una corsa: una regione sola per tutti e tre gli
// esiti, #esito, che sta nella testata. Il fallimento sarebbe finito in
// #errore, che vive nella colonna del dettaglio, e apriDettaglio la svuota a
// ogni apertura: l'annuncio sparirebbe il tempo di due fetch dopo essere
// comparso, e cio' che resta a video sarebbe indistinguibile da una corsa
// riuscita. L'esito ha una riga sua, dove nessun ricaricamento di pannello
// passa.
//
// La classe ACCANTO al testo e non al posto del testo: il fallimento si legge
// per esteso comunque, e chi non distingue le tinte non perde niente (WCAG
// 1.4.1). La classe aggiunge il peso visivo, non l'informazione.
// Il titolo della scheda come segnale: chi ha cambiato finestra durante i
// minuti di uno step vede il segno nella barra delle schede. Torna «MeshRec»
// al fuoco sulla pagina.
function titoloConEsito(errore, esito) {
  if (errore) return "✗ MeshRec";
  if (esito) return "✓ MeshRec";
  return "MeshRec";
}

// L'esito anche fuori dalla scheda, e solo dove serve davvero.
//
// Niente a pagina a fuoco: la stessa frase sta gia' a video nella testata, e
// ripeterla in un riquadro di sistema e' rumore. Niente senza testo: una
// notifica vuota non dice come e' finita la corsa. E il permesso non si chiede
// da qui -- la finestra che compare nel mezzo di un esito e' quella che ogni
// sito apre senza motivo.
function notificaFuoriDallaScheda(testo) {
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  if (!testo || document.hasFocus()) return;
  new Notification("MeshRec", { body: testo });
}

// Il permesso si chiede da un bottone, una volta, e il bottone sparisce con la
// risposta -- tranne quando la finestra viene chiusa senza scegliere
// («default»), che lascia tutto com'era e si potra' richiedere.
//
// Un browser senza l'API non e' un caso di guasto: il bottone si nasconde e il
// resto della pagina non se ne accorge.
function preparaLeNotifiche(bottone) {
  if (typeof Notification === "undefined" || Notification.permission !== "default") {
    bottone.hidden = true;
    return;
  }
  bottone.hidden = false;
  bottone.addEventListener("click", async () => {
    bottone.hidden = (await Notification.requestPermission()) !== "default";
  });
}

// `riuscita` e' vera solo per una corsa che e' arrivata in fondo: e' il terzo
// colore della riga, dopo il grigio e il rosso, e chiude la simmetria con la
// colonna degli step (valido / mai eseguito / fallito). Non si deduce dal
// testo: «interrotta» e «configurazione ripristinata» arrivano come esiti e
// non sono riuscite di una corsa -- la prima e' una scelta, la seconda un
// ritorno -- quindi lo dice il chiamante, che sa da quale fatto viene.
function mostraEsito(errore, esito, riuscita = false) {
  const riga = document.getElementById("esito");
  riga.textContent = errore ?? esito ?? "";
  riga.classList.toggle("esito-fallito", errore !== null && errore !== undefined);
  riga.classList.toggle("esito-riuscito", riuscita && esito !== null && esito !== undefined);
}

// Vera mentre una corsa gira. La sa lo scorrere degli eventi, e serve ai due
// «Esegui»: un pannello aperto in mezzo a una corsa nasceva con i bottoni vivi,
// perche' il fronte di salita che li spegne era gia' passato.
let corsaInCorso = false;

// I due «Esegui» seguono la corsa come «Annulla», e dallo stesso carico.
// Restare vivi e affidarsi al 400 del worker e' un rifiuto che si poteva
// evitare, e un bottone che risponde «no» non si distingue da uno che non ha
// fatto niente -- che e' esattamente il difetto per cui «Annulla» era stato
// legato allo stato.
function spegniLeEsecuzioni(inCorso) {
  corsaInCorso = inCorso;
  for (const bottone of document.querySelectorAll(".esecuzione")) {
    bottone.disabled = inCorso;
  }
}

const flusso = new EventSource("/api/events");

// Il server caduto, dichiarato invece che taciuto.
//
// EventSource riprova da se', e finche' non ci riesce nessuno riceve piu' un
// evento: l'ultimo stato ricevuto resta stampato uguale a uno fresco. La
// colonna continua a dire «valido» e lo stadio del modello uno stato che
// nessuno sta piu' confermando -- una schermata che finge di essere aggiornata.
//
// Di primo livello e non frecce dentro addEventListener, per la stessa ragione
// di aggiornaDaStato: dentro la freccia non le esegue nessun banco.
function perdiIlCollegamento() {
  document.getElementById("collegamento-perso").hidden = false;
}

function riprendiIlCollegamento() {
  document.getElementById("collegamento-perso").hidden = true;
}

flusso.addEventListener("error", perdiIlCollegamento);
flusso.addEventListener("open", riprendiIlCollegamento);

let eraInCorso = false;

// Di primo livello e non una freccia dentro addEventListener: dentro la freccia
// non lo esegue nessun banco. La decisione su come finisce una corsa e' pura e
// gia' a tiro dei test; il CABLAGGIO -- quale regione riceve il testo, e chi la
// svuota subito dopo -- era la meta' che restava fuori.
// Le righe della colonna che stanno girando adesso. Mentre una corsa dura i
// suoi secondi l'unico segnale era la riga «in corso» della testata, e la
// colonna -- che e' la mappa della pipeline -- non diceva dove si stava.
// Si segna l'INTERVALLO da `step` ad `a_step` e non lo step corrente, perche'
// il server non lo sa: `stato.step` e' il capo di partenza e non avanza mai
// (vedi descrizioneDellaCorsa). Un intervallo e' cio' che si sa, e non
// inventa una posizione. Ogni frame rifa' tutte le righe, e le toglie tutte a
// corsa ferma o su un comando fuori pipeline, che non ha uno step.
// `aria-busy` e non un attributo dati: e' il segno che il markup ha per «ci
// sto lavorando», e lo stesso attributo lo legge il foglio e lo sente chi non
// vede ne' il fondo ne' il pallino -- come aria-current sullo step aperto.
function segnaIntervalloInEsecuzione(stato) {
  const dentro = stato.in_corso === true && stato.step !== null && stato.step !== undefined;
  const a = stato.a_step ?? stato.step;
  for (const riga of document.getElementById("elenco-step").children) {
    const numero = Number(riga.firstElementChild?.dataset.numero);
    if (dentro && numero >= stato.step && numero <= a) riga.setAttribute("aria-busy", "true");
    else riga.removeAttribute("aria-busy");
  }
}

function aggiornaDaStato(stato) {
  // A nessuna corsa aperta il flusso manda comunque lo stato del lavoratore,
  // con `steps` vuoto: la colonna degli step non esiste ancora e disegnarla
  // sarebbe disegnare undici righe di una corsa che nessuno ha scelto.
  if (Array.isArray(stato.steps) && stato.steps.length > 0) disegnaStep(stato.steps);
  segnaIntervalloInEsecuzione(stato);
  const barra = document.getElementById("in-corso");
  if (stato.in_corso && stato.da_secondi !== null) {
    // stato.step e' null per un comando che non e' uno step della pipeline
    // (il prior, un modello parametrico: worker.start_comando, non
    // worker.start): la colonna non ha una riga per un comando del genere,
    // e "step null in corso" sarebbe il numero di un ramo che non esiste.
    // Quanto duro' l'ultima volta questo stesso step. E' l'unico numero che
    // questo programma possiede davvero sull'attesa che sta facendo fare: una
    // percentuale non gliela fornisce nessuna libreria, e fabbricarla e' vietato
    // per nome. Non promette niente su questa esecuzione -- i parametri possono
    // essere cambiati -- e infatti la riga non dice «mancano», dice «l'ultima
    // volta». Quando il tempo di adesso lo supera, il ritardo si legge da se',
    // che e' informazione e non allarme.
    //
    // Da `stato.steps` e non da `ultimoStato`: e' lo stesso evento, quindi non
    // dipende dall'ordine in cui disegnaStep lo ha gia' assorbito. Il file di
    // stato si riscrive solo a step finito (steps.write_state, un solo punto),
    // quindi mentre lo step gira quel numero e' ancora quello di prima.
    //
    // Solo per uno step: un comando fuori pipeline (il prior, un modello
    // parametrico) non ha una riga nel file di stato, e non c'e' nessuna ultima
    // volta da leggere.
    //
    // E solo su UNO step, non su un intervallo: `secondi` e' il tempo del solo
    // capo di partenza, e su una corsa da 1 a 11 «l'ultima volta 0,03 s»
    // starebbe sotto un'attesa di dieci minuti. E' lo stesso motivo per cui
    // esitoDellaCorsa tace la durata sugli intervalli.
    const { testo: soggetto, unoSolo } = descrizioneDellaCorsa(stato);
    const prima = stato.step !== null && unoSolo
      ? ultimaDurata((stato.steps ?? []).find((voce) => voce.numero === stato.step))
      : null;
    const scorso = durataMisurata(stato.da_secondi);
    barra.textContent = stato.step !== null
      ? `${soggetto} in corso, ${scorso}${prima !== null ? ` · l'ultima volta ${prima}` : ""}`
      : `un comando è in corso, ${scorso}`;
    barra.hidden = false;
  } else {
    barra.hidden = true;
  }
  // Il bottone segue la corsa. Sempre acceso, un clic a corsa ferma tornava
  // {"annullato": false} e il modulo lo scartava: il silenzio di «non c'era
  // niente da annullare» era identico a quello di un annullamento riuscito.
  // Spento, la domanda non si pone piu' — ed e' il ritorno che il clic non
  // dava, perche' il bottone si spegne quando la corsa finisce.
  document.getElementById("annulla").disabled = !stato.in_corso;
  // I due «Esegui» dallo stesso carico, e nel verso opposto: «Annulla» vive
  // mentre la corsa gira, loro mentre e' ferma.
  spegniLeEsecuzioni(stato.in_corso);
  // Solo sul fronte di discesa: la colonna degli step si aggiorna da questo
  // stesso flusso, e senza questa riga uno step diventerebbe "valido" a
  // sinistra mentre a destra restano le metriche di prima, o nessuna. Non a
  // ogni evento, perche' lo stato arriva ogni mezzo secondo e il pannello si
  // riscriverebbe sotto le dita di chi sta compilando un campo.
  // `esitoPronto` e non il solo `!in_corso`: `is_running()` e' `poll() is
  // None`, mentre `exit_code` lo fissa `_leggi` DOPO aver svuotato stdout,
  // quindi esiste una finestra -- il drain della pipe -- in cui la corsa e' gia'
  // dichiarata ferma e il codice non c'e' ancora. Consumando il fronte li', al
  // frame dopo `eraInCorso` era gia' falso e per quella corsa l'esito non si
  // annunciava MAI: ne' conclusa, ne' fallita, ne' annullata. Era il rigetto
  // silenzioso che questa funzione esiste per togliere.
  //
  // Aspettare invece di consumare e' anche cio' che tiene il fronte UNO: finche'
  // l'esito non c'e' non scatta niente, e se non arrivasse mai non scatta mai --
  // meglio di un pannello che si riapre ogni mezzo secondo su una corsa di cui
  // non si sa com'e' finita. `esitoDellaCorsa` la stessa condizione ce l'ha gia'
  // dentro: adesso il chiamante gliela dice d'accordo.
  const esitoPronto = stato.exit_code !== null && stato.exit_code !== undefined;
  if (eraInCorso && !stato.in_corso && esitoPronto) {
    // L'esito PRIMA di riaprire il pannello, e in una regione che il pannello
    // non tocca. apriDettaglio svuota #errore a ogni apertura: annunciato la',
    // il fallimento sparirebbe due righe piu' sotto, nella stessa passata, e a
    // video resterebbe qualcosa di indistinguibile da una corsa riuscita.
    const { errore, esito } = esitoDellaCorsa(stato);
    mostraEsito(errore, esito, errore === null && !stato.annullato);
    // Fuori dalla scheda l'esito non si vede: il titolo lo porta nella barra
    // delle schede, e la notifica raggiunge chi sta guardando altro.
    document.title = titoloConEsito(errore, esito);
    notificaFuoriDallaScheda(errore ?? esito ?? "");
    // Il registro si apre solo quando c'e' un motivo da leggere: aperto a
    // ogni esecuzione riuscita sarebbe la sezione di prima con un clic in piu'.
    if (errore !== null) document.getElementById("registro-dettagli").open = true;
    if (stepAperto !== null) apriDettaglio(stepAperto);
    // La vista quanto il pannello: senza questa riga lo step rieseguito mostra
    // a destra le metriche nuove e nel viewport il contorno vecchio, col
    // cursore del taglio tarato su un ingombro che non esiste piu'.
    // Una corsa partita dallo step N riscrive gli artefatti dall'N in giu',
    // quindi solo un numero >= N puo' essere scaduto: sotto non c'e' niente da
    // ricaricare, e ogni ricaricamento e' una richiesta in piu'.
    if (stepScelto !== null && stato.step !== null && stepScelto >= stato.step) {
      ricaricaVista(stepScelto);
    }
  }
  // Sul fronte di SALITA l'esito di prima se ne va: lasciato li', «esecuzione
  // fallita» resterebbe a video sopra la corsa nuova che sta partendo proprio
  // per correggere quel fallimento, e sarebbe il piu' vecchio dei due testi a
  // descrivere il piu' recente dei due fatti.
  if (!eraInCorso && stato.in_corso) {
    mostraEsito(null, null);
    // Il titolo con lo stesso movimento: il segno se ne va col fuoco sulla
    // pagina, ma una corsa finita MENTRE si guardava il fuoco ce l'ha gia' e
    // quell'evento non scatta piu'. Senza questa riga, lanciato lo step dopo e
    // cambiata finestra, la scheda dice «✓» su una corsa che sta girando.
    document.title = "MeshRec";
    // Il registro non si svuota da solo fra due corse: senza, una corsa
    // morta prima di scrivere una riga cita quella di prima, e il worker
    // azzera le proprie righe qui allo stesso modo, all'avvio.
    document.getElementById("registro").replaceChildren();
    document.getElementById("registro-dettagli").open = false;
  }
  // Il fronte si consuma solo quando c'e' un esito da annunciare: dentro la
  // finestra sopra, `eraInCorso` resta vero e aspetta il frame che porta il
  // codice.
  if (stato.in_corso || esitoPronto) eraInCorso = stato.in_corso;
}

flusso.addEventListener("stato", (evento) => aggiornaDaStato(JSON.parse(evento.data)));

// --- Annullare e rifare una modifica ---------------------------------------

// I tipi di campo che hanno un undo NATIVO da difendere. Per tipo e non per
// tag: la casella del fantasma e il cursore del taglio sono <input> anche loro,
// ma un undo non ce l'hanno, e lasciare li' il gesto lo renderebbe un tasto
// morto proprio sui due comandi che si toccano di continuo.
const CAMPI_SCRITTI = new Set(["text", "search", "url", "tel", "email", "password", "number"]);

// Il verso che i tasti premuti chiedono, o null se non chiedono niente. Pura e
// di primo livello come superata(): e' l'unico punto in cui una combinazione di
// tasti diventa una scrittura su disco, e da fuori si prova senza un motore di
// DOM.
//
// metaKey oltre a ctrlKey: su macOS il gesto e' cmd+z, e questo progetto sta su
// macOS. toLowerCase perche' col maiusc il browser riporta "Z": legato alla
// sola minuscola, il rifare non risponderebbe mai.
function gestoDelloStorico(evento) {
  if (!(evento.ctrlKey || evento.metaKey)) return null;
  if (evento.key.toLowerCase() !== "z") return null;
  // La ripetizione automatica del tasto tenuto premuto batte una trentina di
  // eventi al secondo, e ognuno qui e' un POST che riscrive config.yaml
  // davvero — e, per un'esecuzione, sposta anche gli artefatti: un secondo di
  // tasto premuto riavvolgerebbe lo storico fino all'avvio. La guardia
  // dell'ordine non limita quel danno, lo NASCONDE -- lascia a video il solo
  // messaggio dell'ultima risposta.
  if (evento.repeat) return null;
  // Dentro un campo scritto il gesto e' gia' preso, e da chi ha piu' diritto:
  // il browser annulla la scrittura nel campo. Questo ascoltatore sta sul
  // documento e lo vedrebbe comunque; scavalcarlo toglierebbe l'undo del testo
  // per darne uno che ripristina un'altra cosa -- e sui campi dei parametri
  // quella «altra cosa» e' proprio la modifica che si sta scrivendo a mano.
  const bersaglio = evento.target;
  const tag = bersaglio?.tagName;
  if (tag === "TEXTAREA" || bersaglio?.isContentEditable) return null;
  // `type` assente e' un campo di testo, che e' cio' che il DOM stesso dice di
  // un <input> senza type.
  if (tag === "INPUT" && CAMPI_SCRITTI.has(bersaglio.type ?? "text")) return null;
  return evento.shiftKey ? "avanti" : "indietro";
}

// Che cosa e' cambiato davvero, nei due versi, dai due elenchi di stato.
//
// Il server manda lo stato INTERO e non un elenco di cambiamenti, e il calcolo
// sta qui perche' qui ci sono tutti e due i termini. Un campo `invalidati` col
// solo elenco degli step passati a «non valido» era stato provato e tolto per
// questo: nel flusso che si usa -- cambio un parametro, poi Ctrl+Z -- quegli
// step erano gia' non validi per via della modifica, e l'undo li fa tornare
// VALIDI. Sarebbe arrivato vuoto, e la frase avrebbe detto «nessuno step cambia
// stato» mentre a sinistra le righe passano da rosso a verde: il caso
// dominante, e falso.
//
// I nomi e non i numeri: la colonna di sinistra mostra i nomi, e «step 2» sono
// le due lingue per la stessa cosa che nomeDelloStep esiste per togliere. Dal
// nuovo stato e non da `ultimoStato`, che a questo punto porta ancora quello
// vecchio.
function fraseDelRitorno(prima, dopo, esecuzione = null, verso = "indietro") {
  const era = new Map(prima.map((voce) => [voce.numero, voce.stato]));
  const nome = (voce) => ETICHETTE[voce.chiave] ?? `step ${voce.numero}`;
  const passatiA = (stato) =>
    dopo.filter((voce) => voce.stato === stato && era.get(voce.numero) !== stato).map(nome);
  const validi = passatiA("valido");
  const nonValidi = passatiA("non valido");
  const pezzi = [];
  if (validi.length) {
    pezzi.push(`${validi.join(", ")} ${validi.length === 1 ? "torna «valido»" : "tornano «validi»"}`);
  }
  if (nonValidi.length) {
    pezzi.push(
      `${nonValidi.join(", ")} ${nonValidi.length === 1 ? "passa a «non valido»" : "passano a «non validi»"}`,
    );
  }
  const stati = pezzi.length ? pezzi.join("; ") : "nessuno step cambia stato";
  if (esecuzione === null) return `configurazione ripristinata: ${stati}`;
  const dove = esecuzione.da === esecuzione.a
    ? `dello step ${esecuzione.da}`
    : `dallo step ${esecuzione.da} ${esecuzione.a === 11 ? "all'11" : `al ${esecuzione.a}`}`;
  // Il verso e' del gesto, non della versione: «avanti» RIFA' l'esecuzione che
  // «indietro» aveva annullato, e chiamarla «annullata» direbbe a chi ha appena
  // premuto Ctrl+Maiusc+Z il contrario di quello che e' successo. La
  // configurazione resta «ripristinata» nei due versi, perche' e' quello che
  // le capita davvero: torna a essere quella di un'altra volta.
  return `esecuzione ${dove} ${verso === "avanti" ? "rifatta" : "annullata"}: ${stati}`;
}

// Un contatore suo, non apriGenerazione(). La generazione e' condivisa, e
// bumparla scarterebbe ogni tratta in volo. Questa e' anche la prima strada che
// puo' uscire senza ripartire -- «niente da annullare», guasto, corpo nullo,
// rifiuto -- ed e' la stessa ragione per cui la geometria ha `ultimaGeometria`
// e il velo `ultimoFantasma`.
let ultimoRitorno = 0;

function apriRitorno() {
  ultimoRitorno += 1;
  return ultimoRitorno;
}

async function chiediStorico(verso) {
  // L'ordine si apre PRIMA dell'attesa, non dopo: due gesti ravvicinati
  // finiscono in volo insieme, e aperto dopo sarebbe il numero di ARRIVO invece
  // che quello di partenza, cioe' vincerebbe la risposta vecchia.
  const ordine = apriRitorno();
  // Lo stato di partenza si prende ADESSO, prima di qualunque attesa. Qui c'era
  // scritto che bastasse comporre la frase prima di `caricaStato()`, ma non e'
  // `caricaStato` a riscrivere `ultimoStato`: e' `disegnaStep`, che il flusso
  // SSE chiama a OGNI frame, mezzo secondo l'uno, del tutto indipendente da
  // questo gesto. E `_ripristina` scrive config.yaml prima di calcolare la
  // risposta, quindi un frame emesso in quella finestra porta gia' gli step
  // nuovi: se arrivava prima della risposta, i due termini erano lo stesso
  // stato, `passatiA` tornava vuoto in tutti e due i versi e la riga diceva
  // «nessuno step cambia stato» mentre la colonna a sinistra passava da rosso a
  // verde. `disegnaStep` riassegna e non muta, quindi questa copia regge.
  //
  // Senza controllo, e dichiarato: sorvegliarlo vuole un banco che ritagli
  // `chiediStorico` intera -- fetch, corpoLetto, ragioneDelRifiuto, superata,
  // caricaStato, ricaricaVista, apriDettaglio -- e poi faccia arrivare un frame
  // SSE nel mezzo di una fetch. E' un cantiere suo, non una riga di banco.
  // `fraseDelRitorno` il proprio controllo ce l'ha (test_app_js.py); quel che
  // resta scoperto e' da dove arriva il primo dei suoi due argomenti.
  const prima = ultimoStato;
  const risposta = await fetch(`/api/storico/${verso}`, { method: "POST" }).catch(serverMuto);
  // Tutto l'esito del gesto esce dalla stessa riga, #esito, compresi i rifiuti:
  // chi preme un tasto guarda dove sono comparse le risposte a quel tasto, non
  // la classificazione interna del guasto. E #errore vive nella colonna del
  // dettaglio, che apriDettaglio svuota a ogni apertura -- cioe' proprio qualche
  // riga piu' sotto: scritti la', due messaggi su cinque sparirebbero nel tempo
  // di due fetch.
  if (!risposta.ok) {
    const ragione = await ragioneDelRifiuto(risposta);
    if (superata(ordine, ultimoRitorno)) return;
    mostraEsito(ragione, null);
    return;
  }
  const corpo = await corpoLetto(risposta);
  // Dopo l'ultima attesa e prima della prima scrittura, come le due strade che
  // disegnano: un ripristino superato da uno piu' recente non scrive niente.
  if (superata(ordine, ultimoRitorno)) return;
  // == e non ===: il corpo di questa tratta non e' mai legittimamente null.
  if (corpo == null) {
    mostraEsito(
      "il server ha risposto con un corpo che non si legge. " + RIMEDIO,
      null,
    );
    return;
  }
  // Il corpo si legge anche quando la risposta e' riuscita: scartarlo qui
  // renderebbe il silenzio di «non c'era niente da annullare» identico a quello
  // di un ritorno riuscito, che e' il difetto gia' prodotto e corretto una volta
  // sul bottone «Annulla».
  if (!corpo.annullato) {
    // Si legge `guasto` e non il testo del «perche'»: il nome dell'eccezione
    // dentro quel testo cambia col guasto, il bit no. Un deposito rotto chiede
    // di mettere le mani dentro .storico, e annunciato col peso di «niente da
    // annullare» resterebbe indistinguibile da un gesto a vuoto.
    mostraEsito(corpo.guasto ? corpo.perche : null, corpo.guasto ? null : corpo.perche);
    return;
  }
  // `prima`, catturato in cima: il termine di confronto e' lo stato che era a
  // video quando il tasto e' stato premuto, non quello che c'e' adesso.
  mostraEsito(
    null,
    fraseDelRitorno(prima, corpo.steps, corpo.tipo === "esecuzione" ? { da: corpo.da, a: corpo.a } : null, verso),
  );
  await caricaStato();
  // Il config e' cambiato sotto: la geometria di prima con lo stato nuovo a
  // sinistra e' la vista che contraddice la propria didascalia. Senza ordine
  // proprio, come il ricaricamento del fronte di discesa: prende la generazione
  // in corso, cosi' non annulla una geometria in volo e un clic dell'utente lo
  // batte.
  if (stepScelto !== null) ricaricaVista(stepScelto);
  if (stepAperto !== null) apriDettaglio(stepAperto);
}

// L'unico tasto globale dell'interfaccia. I comandi della tela -- frecce, +, -,
// f, maiusc -- restano legati al canvas col fuoco sopra (viewport.js), e un
// gestore globale su quelli li ruberebbe a chi orbita da tastiera.
document.addEventListener("keydown", (evento) => {
  const verso = gestoDelloStorico(evento);
  if (verso === null) return;
  // Solo quando il gesto e' davvero nostro: incondizionato, preventDefault
  // toglierebbe l'undo del browser anche dove gestoDelloStorico ha appena
  // deciso di lasciarglielo.
  evento.preventDefault();
  chiediStorico(verso);
});

// Quante righe restano nel registro. E' una finestra di lettura, non una
// misura: chi vuole tutto lo stdout ha il file della corsa su disco.
const RIGHE_DEL_REGISTRO = 500;

flusso.addEventListener("riga", (evento) => {
  const registro = document.getElementById("registro");
  const riga = document.createElement("div");
  riga.className = "riga-log";
  riga.textContent = JSON.parse(evento.data);
  registro.append(riga);
  // Il registro cresceva senza tetto: una corsa lunga lascia nel DOM ogni riga
  // che il sottoprocesso ha scritto, e nessuna veniva mai tolta. Il tetto e'
  // sulle righe e non sui caratteri perche' e' cio' che si conta guardando, e
  // le piu' vecchie escono dalla testa, che e' il verso in cui si legge un log.
  while (registro.childElementCount > RIGHE_DEL_REGISTRO) registro.firstElementChild.remove();
  registro.scrollTop = registro.scrollHeight;
});

// Con un nome, non inline: cosi' il test che sorveglia la regola dell'ordine
// la vede e la puo' escludere per iscritto invece di non incontrarla mai.
// Nessuna scrittura dopo l'attesa — lo stato torna dallo scorrere degli
// eventi — quindi non c'e' nulla che una generazione superata contraddica.
async function annullaLaCorsa() {
  await fetch("/api/cancel", { method: "POST" });
}

document.getElementById("annulla").addEventListener("click", annullaLaCorsa);

// Il segno nel titolo dura finche' non lo si e' letto: chi torna sulla pagina
// l'ha appena letto, e la testata dice il resto.
window.addEventListener("focus", () => { document.title = "MeshRec"; });
preparaLeNotifiche(document.getElementById("notifiche"));

import {
  creaViewport, scalaDelCampo, numeroDelCampo, didascaliaDelloScarto, RAMPA,
} from "/ui/viewport.js";

const vista = creaViewport(document.getElementById("viewport"));

// Le richieste si accavallano, e senza un ordine una risposta vecchia vince su
// una nuova: si clicca lo step 9, che ci mette quindici secondi, si clicca lo
// step 1, compare la nuvola giusta, e quindici secondi dopo la mesh del 9 la
// sostituisce con la propria didascalia mentre il pannello mostra il 1. E'
// proprio la vista che contraddice la sua didascalia.
// Ogni clic apre una generazione; chi torna da una generazione chiusa non
// scrive nulla. Un contatore basta: non servono AbortController ne' code.
let generazione = 0;

function apriGenerazione() {
  generazione += 1;
  return generazione;
}

// Pura apposta, cosi' la regola dell'ordine si puo' guardare da fuori invece
// di doverla dedurre dai punti in cui e' usata.
function superata(ordine, corrente = generazione) {
  return ordine !== corrente;
}

// Le generazioni ordinano i clic, ma dentro una sola generazione possono
// esserci due richieste di geometria in volo: il fronte di discesa ricarica la
// vista senza aprire una generazione (aprirla butterebbe via il clic che
// l'utente ha appena fatto), quindi il suo ricaricamento e una risposta partita
// prima portano lo stesso ordine. Con quel solo numero superata() non puo'
// dirimerli e vince chi arriva ultimo, che e' la geometria vecchia: si riclicca
// lo step 9 mentre gira, la risposta del clic arriva dopo il ricaricamento, e
// il viewport torna al contorno di prima. E' IM-4 per un'altra strada.
// Un secondo contatore basta, e la regola e' la stessa: numera le richieste di
// geometria e lascia scrivere solo l'ultima partita. Due requisiti diversi,
// due contatori — il ricaricamento non apre una generazione, ma apre sempre
// una richiesta, quindi batte le proprie precedenti senza toccare i clic.
let ultimaGeometria = 0;

function apriGeometria() {
  ultimaGeometria += 1;
  // La chiave della scala se ne va con la vista che descriveva, e se ne va IN
  // TESTA: e' la stessa forma di togliFantasma dentro svuota(). Ogni strada che
  // disegna passa di qui, e solo le due che colorano per misura la riaccendono
  // dopo aver disegnato. Spenta in coda, una barra rimasta da un campo starebbe
  // sotto una nuvola grigia dichiarando che quel grigio vale qualcosa.
  //
  // Scritta qui e non delegata a una funzione: `apriGeometria` e' il biglietto
  // dell'arbitrato e viene ritagliata da una trentina di banchi, che una
  // chiamata in piu' costringerebbe a elencare una dipendenza in piu' ciascuno.
  document.getElementById("scala").hidden = true;
  return ultimaGeometria;
}

function scalaDellaVista() {
  return document.getElementById("scala");
}

// La chiave della scala colore: da zero al taglio, con l'unita' accanto.
//
// Gli stessi due numeri della didascalia e la stessa rampa dei vertici -- il
// gradiente viene da RAMPA, che e' la costante che li colora -- perche' una
// legenda che dichiarasse una scala diversa da quella dipinta sarebbe peggio
// di nessuna legenda.
//
// Da ZERO e non dal minimo del campo: `frazioneDelCampo` divide per il taglio e
// blocca sotto lo zero, quindi l'estremo chiaro E' lo zero, qualunque sia il
// valore piu' piccolo che il pezzo porta. Scrivere qui il minimo misurato
// dichiarerebbe un capo della rampa che la rampa non ha.
//
// Senza un taglio scrivibile la chiave resta spenta invece di mostrare due
// trattini: la didascalia in quel caso dice gia' «scala non disponibile», e una
// barra colorata sotto quella frase la contraddirebbe.
function mostraLaScala(taglio, unita) {
  const scritto = numeroDelCampo(taglio);
  if (scritto === null) return;
  scalaDellaVista().hidden = false;
  document.getElementById("scala-minimo").textContent = "0";
  document.getElementById("scala-massimo").textContent = `${scritto} ${unita}`;
  document.getElementById("scala-rampa").style.background =
    `linear-gradient(to right, ${RAMPA.chiaro}, ${RAMPA.scuro})`;
}

// --- L'attesa dichiarata, e l'artefatto che non arriva ----------------------

// Nessuna percentuale: le librerie non ne danno una, e inventarne una sarebbe
// il principio 3 del prodotto rovesciato. Si dice CHE COSA si sta leggendo,
// che e' un fatto.
//
// La geometria di prima NON si svuota qui, ed e' deliberato. Su una scansione
// vera la lettura costa 27-34 secondi a freddo, e svuotare in testa
// scambierebbe mezzo minuto di geometria vecchia con mezzo minuto di tela
// bianca -- peggio, non meglio. Cio' che non deve restare non e' l'immagine ma
// l'AFFERMAZIONE: in quella finestra i conteggi portavano i numeri dello step
// precedente mentre la colonna aveva gia' aria-current sul nuovo, cioe' lo
// schermo diceva che i parametri di uno step vanno con la mesh di un altro.
// E' la «vista che contraddice la propria didascalia» vista dall'altro capo:
// le due generazioni difendono dalle scritture vecchie, questa riga dalle
// letture vecchie ancora a video.
// NIENTE aria-busy su #viewport, e non e' una dimenticanza. #conteggi e' figlio
// diretto di #viewport (index.html:135-136) ed e' lui la regione viva:
// aria-busy su un antenato zittisce la regione che contiene. Messo qui,
// spegnerebbe l'annuncio scritto la riga sopra, nello stesso blocco sincrono --
// cioe' proprio la sola cosa che dichiara l'attesa a chi non guarda lo schermo.
// Non aggiungeva nemmeno un fatto: «caricamento di Riduzione...» dice gia' che
// si sta leggendo, e che cosa. Se un giorno servisse davvero, va sulla tela che
// viewport.js appende dentro #viewport, mai sul contenitore.
function dichiaraCaricamento(numero) {
  document.getElementById("conteggi").textContent =
    `caricamento di ${nomeDelloStep(numero)}...`;
}

// Il corpo binario di una risposta ok, letto senza lasciare uscire un rigetto
// a meta' del download. Stesso principio di corpoLetto per il JSON, duplicato
// apposta per non far dipendere le due tratte binarie da quella che legge
// testo.
//
// `undefined` marca «il download non e' arrivato». Un ArrayBuffer vuoto
// (byteLength 0) e' un dato legittimo, non un errore: confonderli tratterebbe
// una mesh vuota come un guasto di rete.
async function corpoBinarioLetto(risposta) {
  try {
    return await risposta.arrayBuffer();
  } catch {
    return undefined;
  }
}

// Il download si e' fermato a meta', dopo che gli header erano gia' arrivati:
// e' lo stesso fatto di un server muto, letto piu' tardi. Riusa serverMuto
// invece di un testo proprio, cosi' la formula «il server non ha risposto: ...»
// resta una sola in tutto il file e non due copie fra nuvola e mesh che
// potrebbero divergere.
function messaggioDownloadInterrotto() {
  return ragioneDelRifiuto(
    serverMuto(new Error("connessione interrotta durante il download")),
  );
}

// Porta la vista nello stato «niente da mostrare», con un messaggio gia'
// calcolato. Sincrona apposta: il chiamante calcola il messaggio (che puo'
// aspettare ragioneDelRifiuto) e controlla la guardia dell'ordine PRIMA di
// chiamare questa, cosi' una risposta scartata non arriva mai qui. Spostare la
// guardia dentro sposterebbe la scrittura dopo un'altra attesa invece di
// tenerla subito dopo l'ultima, riaprendo la corsa che le generazioni esistono
// per chiudere.
//
// Il messaggio arriva dal server e non e' una frase fissa di qui: `server.py`
// nomina l'artefatto che manca -- «lo step 9 non ha ancora prodotto
// 09_volume.vtu» -- e il nome del file e' la cosa concreta, mentre «riesegui lo
// step 9» era un'istruzione che il browser inventava.
function segnalaArtefattoMancante(messaggio) {
  // Svuotare e' obbligatorio: senza, la scena resta quella dello step
  // precedente mentre il testo dice che non c'e' nulla. Una vista che
  // contraddice la sua didascalia e' peggio di una vista vuota.
  vista.svuota();
  document.getElementById("conteggi").textContent = messaggio;
}

async function mostraNuvolaDelloStep(numero, ordine) {
  const emissione = apriGeometria();
  dichiaraCaricamento(numero);
  // `.catch(serverMuto)`: senza, un server fermo o una rete caduta faceva
  // uscire il rigetto da questa funzione asincrona, cioe' dentro una promessa
  // che nessuno guarda (ricaricaVista la consuma con .then). A video restava la
  // geometria di prima sotto la scritta «caricamento di ...», per sempre, e
  // nessuno diceva perche'. Le tre tratte che ne erano scoperte stavano
  // tutte nella schermata dell'analisi, e sono uscite con lei.
  const risposta = await fetch(`/api/cloud/${numero}`).catch(serverMuto);
  if (!risposta.ok) {
    const messaggio = await ragioneDelRifiuto(risposta);
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    // "vuoto" e non true: ha SCRITTO (quindi non e' una risposta scartata, e
    // chi guarda l'ordine deve saperlo) ma non ha DISEGNATO. Chi ci scrive
    // sopra una didascalia deve poter distinguere i due casi.
    return "vuoto";
  }
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const grezzi = await corpoBinarioLetto(risposta);
  if (grezzi === undefined) {
    // Su una nuvola vera il download dura secondi, e la rete puo' cadere in
    // quella finestra tanto quanto prima della prima risposta.
    const messaggio = await messaggioDownloadInterrotto();
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return "vuoto";
  }
  // Il controllo sta dopo l'ultima attesa e prima della prima scrittura: piu'
  // in alto lascerebbe passare cio' che e' stato superato mentre il corpo
  // arrivava.
  //
  // Chi esce di qui non tocca la scritta dell'attesa: e' stato superato, e a
  // riscriverla e' la richiesta che l'ha superato. Toccarla qui cancellerebbe
  // l'annuncio di una lettura ancora in corso.
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  vista.svuota();
  vista.mostraNuvola(new Float32Array(grezzi));
  // Sempre entrambi: una nuvola decimata che non lo dichiara e' un dato falso.
  document.getElementById("conteggi").textContent =
    `${disegnati.toLocaleString("it")} punti disegnati su ${pieni.toLocaleString("it")}`;
  // Vero solo se questa risposta ha davvero scritto: il cursore del taglio si
  // rifa' sull'ingombro di cio' che e' disegnato, e rifarlo dopo una risposta
  // scartata lo tarerebbe sulla geometria di qualcun altro.
  return true;
}

// Gli step che producono una superficie o un volume: dal 5 in poi l'artefatto
// non e' piu' una nuvola, e disegnarne i soli vertici mostrerebbe punti dove
// c'e' un solido. Il 13 e' anche lui un volume (13_solution.vtu): l'insieme lo
// tiene perche' chiedere /api/cloud/13 non troverebbe niente, anche se oggi
// nessuna strada dell'interfaccia ci arriva.
const STEP_CON_MESH = new Set([5, 6, 8, 9]);

async function mostraStep(numero, ordine) {
  // La delega sta prima del contatore: incrementarlo qui e di nuovo la' sotto
  // farebbe battere questa richiesta da se stessa, e nessuna nuvola verrebbe
  // piu' disegnata. Ogni strada apre esattamente una richiesta.
  if (!STEP_CON_MESH.has(numero)) return mostraNuvolaDelloStep(numero, ordine);
  const emissione = apriGeometria();
  dichiaraCaricamento(numero);
  // Come nella tratta della nuvola, e per la stessa ragione: senza la guardia
  // il rigetto usciva dentro una promessa che nessuno guarda.
  const risposta = await fetch(`/api/mesh/${numero}`).catch(serverMuto);
  if (!risposta.ok) {
    const messaggio = await ragioneDelRifiuto(risposta);
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    // Come nella tratta della nuvola: ha scritto, non ha disegnato.
    return "vuoto";
  }
  const vertici = Number(risposta.headers.get("X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await corpoBinarioLetto(risposta);
  if (grezzi === undefined) {
    const messaggio = await messaggioDownloadInterrotto();
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return "vuoto";
  }
  // Qui la latenza e' quella vera: e' la mesh dello step 9 che arriva tardi a
  // posarsi sulla nuvola di un altro step.
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  vista.svuota();
  vista.mostraMesh(
    new Float32Array(grezzi, 0, vertici * 3),
    new Uint32Array(grezzi, vertici * 3 * 4, triangoli * 3),
  );
  // I conteggi sono quelli che il server ha contato sull'artefatto: per lo
  // step 9 sono i vertici e i triangoli del contorno, non i nodi del volume.
  document.getElementById("conteggi").textContent =
    `${vertici.toLocaleString("it")} vertici, ${triangoli.toLocaleString("it")} triangoli`;
  return true;
}

// --- Il fantasma del passaggio a monte --------------------------------------
// «Che cosa ha fatto questo step alla geometria» a video non aveva risposta:
// gli undici artefatti si guardano di fila, mai due insieme, e di cio' che un
// passaggio ha TOLTO restano due numeri letti in due momenti diversi. Il
// fantasma mette la geometria di prima dietro quella corrente: i due conteggi
// pieni si leggono nello stesso istante invece che uno al posto dell'altro.

// Da quale step viene il fantasma. Acceso solo dove il conteggio cala davvero:
// il ritaglio dello step 2, lo sfoltimento del 3, la semplificazione dell'8.
// Scritte a mano e non calcolate come `numero - 1`: sullo step 8 il precedente
// con geometria propria e' il 6, perche' il 7 misura e non produce niente.
// Fuori da queste tre coppie due geometrie sovrapposte -- il 5 contro il 6, per
// dire -- fanno z-fighting e non informano nessuno.
const FANTASMA_DI = { 2: 1, 3: 2, 8: 6 };
let fantasmaAcceso = true;

// Pura apposta, cosi' la regola si guarda da fuori invece di dedurla dai punti
// in cui e' usata. `sorgente` e' lo step da cui viene la geometria a video:
// quando non e' quello chiesto, la geometria corrente e' gia' quella di un
// altro passaggio e il fantasma la ridisegnerebbe sopra se stessa.
// L'interruttore non entra qui: e' un predicato solo, e decide sia se il velo
// si disegna sia se la casella si mostra. Con due predicati -- la tabella per
// mostrare, questo per disegnare -- sullo step 8 di una corsa senza
// semplificazione la casella comparirebbe spuntata e toccarla nei due versi non
// farebbe nulla, perche' li' la geometria a video e' gia' quella dello step 6.
// E l'interruttore non puo' entrarci: spento farebbe sparire la propria casella.
function fantasmaHaSenso(chiesto, sorgente) {
  return sorgente === chiesto && FANTASMA_DI[chiesto] !== undefined;
}

function comandoDelFantasma() {
  return document.getElementById("fantasma-comando");
}

// Un contatore suo, e NON apriGeometria(). `ultimaGeometria` e' l'arbitro fra
// due geometrie della stessa generazione -- vince quella partita dopo -- e il
// velo si posa dentro il `then` di mostraStep, cioe' proprio in mezzo a due
// richieste che possono essere ancora tutt'e due in volo (il clic e il fronte
// di discesa condividono la generazione).
// L'ordine in cui morde e' questo: arriva per prima la richiesta VECCHIA, che
// disegna e fa partire il suo velo; il velo bumpa `ultimaGeometria`; arriva la
// richiesta nuova e si trova superata da un numero che non e' di nessuna
// geometria. A video resta la geometria vecchia, e nessuno lo dice.
// Provato eseguendo, in tutte e due i versi:
// test_server.py::test_il_velo_non_arbitra_al_posto_delle_geometrie.
// Col contatore suo il velo arbitra solo contro altri veli, che e' l'unica
// corsa che gli appartiene.
let ultimoFantasma = 0;

function apriFantasma() {
  ultimoFantasma += 1;
  return ultimoFantasma;
}

async function mostraFantasmaDelloStep(numero, ordine) {
  // Prima di toccare la casella e non solo prima di disegnare: chi e' stato
  // superato non deve nemmeno decidere se il comando si vede. Un clic sullo
  // step 2 che arriva tardi, dopo un clic sul 9, riaccenderebbe la casella su
  // una vista che non e' piu' la sua.
  if (superata(ordine)) return;
  const haSenso = fantasmaHaSenso(numero, passoDaMostrare(numero));
  comandoDelFantasma().hidden = !haSenso;
  if (!haSenso || !fantasmaAcceso) return;
  const da = FANTASMA_DI[numero];
  // La frontiera fra nuvola e superficie e' STEP_CON_MESH, e si legge di la'.
  // Scritta qui una seconda volta come `da <= 4` sarebbe la stessa frontiera
  // detta due volte nello stesso file: il giorno che la pipeline guadagna uno
  // step, una si sposta e l'altra no, e il fantasma dell'8 chiederebbe una
  // nuvola dove c'e' una superficie.
  const nuvola = !STEP_CON_MESH.has(da);
  const emissione = apriFantasma();
  const risposta = await fetch(nuvola ? `/api/cloud/${da}` : `/api/mesh/${da}`)
    .catch(serverMuto);
  // Un fantasma che non arriva non e' un errore da annunciare: lo step a monte
  // puo' semplicemente non essere ancora girato, e la geometria corrente resta
  // quella che e'. Il silenzio qui non nasconde niente che l'utente abbia
  // chiesto -- cio' che ha chiesto e' a video, con la sua didascalia.
  // Un termine solo: `serverMuto` rende sempre un oggetto con ok: false, quindi
  // da quando la fetch qui sopra ha il .catch, `undefined` non arriva piu'.
  if (!risposta.ok) return;
  const pieni = Number(risposta.headers.get(nuvola ? "X-Points-Total" : "X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await corpoBinarioLetto(risposta);
  // Il velo aveva lo stesso `arrayBuffer()` nudo delle due tratte grandi, e
  // qui il corpo e' il piu' pesante di tutti: il fantasma dello step 2 e' la
  // nuvola piena dello step 1. Un download caduto a meta' non si annuncia --
  // vale la stessa ragione della riga qui sopra, cio' che l'utente ha chiesto
  // e' a video con la sua didascalia -- ma senza questa riga uscirebbe comunque
  // rumoroso, perche' `new Float32Array(undefined)` solleva.
  if (grezzi === undefined) return;
  // Dopo l'ultima attesa e prima della prima scrittura, come le due strade che
  // disegnano: un fantasma partito per lo step 2 non deve posarsi sul 9. Sullo
  // step 2 sono 6,3 milioni di punti, decine di secondi a freddo, e in quel
  // tempo si fa in tempo a cliccare altrove piu' di una volta.
  if (superata(ordine) || superata(emissione, ultimoFantasma)) return;
  if (nuvola) {
    vista.mostraFantasma(new Float32Array(grezzi));
  } else {
    vista.mostraFantasma(
      new Float32Array(grezzi, 0, pieni * 3),
      new Uint32Array(grezzi, pieni * 3 * 4, triangoli * 3),
    );
  }
}

function alternaFantasma(acceso) {
  fantasmaAcceso = acceso;
  if (!acceso) {
    vista.togliFantasma();
    return undefined;
  }
  // Lo step MOSTRATO e non quello scelto: e' la stessa distinzione che
  // ricaricaVista fa, e passare qui lo scelto accenderebbe il velo su un numero
  // che a video non c'e'.
  if (stepScelto === null) return undefined;
  return mostraFantasmaDelloStep(stepScelto, generazione);
}

comandoDelFantasma().addEventListener("change", (evento) => {
  alternaFantasma(evento.target.checked);
});

// Lo step che misura lo scarto geometrico, e la superficie su cui lo misura.
// Sono due numeri e non uno perche' lo step 7 non ha un artefatto proprio: la
// mesh che dipinge e' quella riparata dello step 6, la stessa che `pipeline.run`
// gli passa. Il server tiene la coppia dalla sua parte (`_SCARTO_MESH`), e la
// corrispondenza fra i due file la garantisce lui leggendoli entrambi.
const STEP_CON_SCARTO = 7;
const STEP_CON_SUPERFICIE = 6;

// Lo scarto dipinto sulla superficie: gli stessi numeri di
// metriche["07_surface_quality"].geometric_error, nel posto in cui sono.
//
// Stessa arbitrazione di mostraStep, e per la stessa ragione: due clic di
// seguito non devono far vincere la richiesta piu' vecchia.
async function mostraScartoDelloStep(ordine) {
  const didascalia = didascaliaDellaVista();
  const emissione = apriGeometria();
  const [rispostaMesh, rispostaScarto] = await Promise.all([
    fetch(`/api/mesh/${STEP_CON_SUPERFICIE}`).catch(serverMuto),
    fetch("/api/scarto").catch(serverMuto),
  ]);
  if (!rispostaMesh.ok || !rispostaScarto.ok) {
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    const ragione = await ragioneDelRifiuto(rispostaMesh.ok ? rispostaScarto : rispostaMesh);
    didascalia.textContent = ragione;
    return true;
  }
  const grezzoMassimo = rispostaScarto.headers.get("X-Max");
  const massimo = grezzoMassimo ? Number(grezzoMassimo) : NaN;
  const vertici = Number(rispostaMesh.headers.get("X-Vertices"));
  const triangoli = Number(rispostaMesh.headers.get("X-Triangles"));
  const grezziMesh = await rispostaMesh.arrayBuffer();
  const grezziScarto = await rispostaScarto.arrayBuffer();
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  const valori = new Float32Array(grezziScarto);
  // La stessa guardia del campo, e non e' cintura sopra bretelle: i due corpi
  // arrivano da due risposte, e una corsa rieseguita mentre la vista arriva
  // poserebbe i colori di una superficie sulle posizioni di un'altra. Uscirebbe
  // un pezzo dipinto sfalsato, senza nessun errore -- cioe' una mappa
  // diagnostica che indica il posto sbagliato.
  if (valori.length !== vertici) {
    didascalia.textContent =
      `lo scarto e la superficie non corrispondono (${valori.length} valori su ${vertici} vertici): `
      + "la corsa è cambiata mentre la vista arrivava, riprova";
    return true;
  }
  const { taglio, sopraTaglio } = scalaDelCampo(valori);
  const testo = didascaliaDelloScarto({ massimo, taglio, sopraTaglio });
  // Lo scarto e' una distanza: millimetri.
  mostraLaScala(taglio, "mm");
  vista.svuota();
  vista.mostraMeshPerCampo(
    new Float32Array(grezziMesh, 0, vertici * 3),
    new Uint32Array(grezziMesh, vertici * 3 * 4, triangoli * 3),
    valori,
    { taglio, descrizione: testo },
  );
  document.getElementById("conteggi").textContent =
    `${vertici.toLocaleString("it")} vertici, ${triangoli.toLocaleString("it")} triangoli`;
  didascalia.textContent = testo;
  return true;
}

// Il pannello dello step 7: un comando solo, che non scrive niente in
// config.yaml. A differenza dei campi dei blocchi non passa da
// scriviParametro.
//
// Le due voci si leggono da `ultimoStato` e non si chiede al server: un bottone
// che si puo' premere e risponde «quel file non c'e'» e' un rifiuto che si
// poteva evitare, ed e' la stessa regola per cui «Annulla» segue la corsa.
function pannelloScarto(ordine) {
  const contenitore = document.createElement("fieldset");
  contenitore.className = "gruppo";
  contenitore.append(elemento("legend", { textContent: "Scarto dalla nuvola" }));
  const superficie = ultimoStato.find((v) => v.numero === STEP_CON_SUPERFICIE);
  const nuvola = ultimoStato.find((v) => v.numero === 2);
  if (!superficie?.artefatto || !nuvola?.artefatto) {
    contenitore.append(elemento("p", {
      className: "aiuto",
      textContent: "Lo scarto si misura fra la superficie riparata dello step 6 e la nuvola "
        + "segmentata dello step 2: questa corsa non le ha ancora prodotte entrambe.",
    }));
    return contenitore;
  }
  contenitore.append(elemento("p", {
    className: "aiuto",
    textContent: "Gli stessi numeri della tabella qui sotto, nel posto in cui sono: ogni "
      + "vertice prende il colore della propria distanza dalla nuvola.",
  }));
  const bottone = elemento("button", {
    type: "button",
    className: "bottone",
    textContent: "Dipingi lo scarto",
  });
  // Spento mentre la misura gira, e non e' prudenza generica: dall'altra parte
  // c'e' un albero costruito sulla nuvola segmentata -- 4.229.538 punti su
  // lab_crop -- e due clic di seguito lo fanno costruire due volte, perche' la
  // memoria del server tiene UNA voce e la scrive solo a conto finito. Sono
  // secondi di attesa e un centinaio di megabyte, spesi per un risultato
  // identico che l'arbitrato butterebbe via comunque.
  //
  // E l'attesa si dichiara: senza, un clic su una nuvola vera lascia lo schermo
  // identico per qualche secondo, che e' indistinguibile da un bottone rotto.
  // La misura vera non c'e' -- nessuno cronometra un albero prima di costruirlo
  // -- quindi si dice che cosa sta succedendo, non quanto manca: e' la stessa
  // regola per cui l'attesa di uno step non porta una percentuale.
  bottone.addEventListener("click", async () => {
    bottone.disabled = true;
    didascaliaDellaVista().textContent =
      "misura dello scarto in corso: ogni vertice cerca il proprio punto più vicino nella nuvola";
    try {
      await mostraScartoDelloStep(ordine);
    } finally {
      // Il pannello puo' essere stato rifatto sotto le dita, e in quel caso
      // questo bottone e' un orfano staccato dal documento: riaccenderlo non
      // fa niente e non fa danno, mentre saltare il finally lascerebbe spento
      // quello vero nel caso in cui il pannello e' ancora il suo.
      bottone.disabled = false;
    }
  });
  contenitore.append(bottone);
  return contenitore;
}

// La didascalia della vista sta nel markup, dentro la zona della vista e sotto
// la tela, non nel pannello della terza colonna: proiettata in discussione,
// quella frase e' l'unica cosa che dice quale caso di carico e quale grandezza
// si sta guardando, e nella terza colonna finiva sotto la piega (ventidue
// tacche di rotella per portarla in vista, misurato nel browser il
// 22/08/2026). Come #conteggi: sta nel markup e nessun ramo del modulo la puo'
// distruggere.
function didascaliaDellaVista() {
  return document.getElementById("didascalia-vista");
}

// Il piano di taglio serve a guardare dentro il volume, percio' il comando
// compare solo quando nel viewport C'E' il volume, e solo se qualcosa e' stato
// davvero disegnato. Da quando la vista ripiega, «c'e' il volume» non coincide
// piu' con «e' selezionato lo step 9»: scelto il 10, l'11 o il 12 il ripiego
// atterra sul 9 e il comando compare anche li'. E' voluto -- il volume e'
// davvero sullo schermo e si puo' davvero tagliare -- e i chiamanti passano
// per questo lo step MOSTRATO, non quello scelto.
const STEP_CON_TAGLIO = 9;
// Lo step che l'utente ha SCELTO, non quello la cui geometria e' a schermo:
// quella e' `passoDaMostrare(stepScelto)`, che puo' essere piu' a monte. Il
// nome vecchio (`stepMostrato`) diceva l'una cosa mentre il codice faceva
// l'altra. Non e' sempre quello del pannello, che resta aperto anche mentre la
// geometria nuova sta arrivando.
let stepScelto = null;
const comandoTaglio = document.getElementById("taglio");
const asseTaglio = document.getElementById("taglio-asse");
const quotaTaglio = document.getElementById("taglio-quota");
const valoreTaglio = document.getElementById("taglio-valore");

// Quanti scatti percorrono l'asse da un capo all'altro. E' una risoluzione,
// non una misura: il passo in millimetri esce dall'ingombro, percio' resta
// utile sia sull'asse lungo due metri e mezzo sia su quello spesso ventitre
// centimetri, dove un passo fisso sarebbe grossolano o inutilmente fitto.
const SCATTI_DEL_CURSORE = 1000;

function applicaTaglio() {
  const quota = Number(quotaTaglio.value);
  // Il primo scatto del cursore, il minimo dell'ingombro, e' la posizione
  // spenta: li' il piano non esiste. E' l'unico modo di rivedere il volume
  // intero senza uscire dallo step, ed e' il comando che il viewport esponeva
  // (disattivaTaglio) senza che l'interfaccia lo raggiungesse.
  // Spenta e non «taglio che non toglie niente» apposta: alla quota del
  // minimo il piano sarebbe complanare alla faccia estrema, e three.js tiene i
  // punti con normale . punto + costante > 0, cioe' quei vertici li
  // toglierebbe. Cosi' invece nessuna quota tagliata e' mai complanare: la
  // prima vale minimo + passo.
  const intero = quota <= Number(quotaTaglio.min);
  if (intero) vista.disattivaTaglio();
  else vista.attivaTaglio(Number(asseTaglio.value), quota);
  // La quota e' una coordinata della geometria, che il progetto tiene in
  // millimetri (lo stesso sistema che l'esportazione dichiara nel .inp).
  const testo = intero
    ? "volume intero"
    : `${quota.toLocaleString("it", { maximumFractionDigits: 1 })} mm`;
  valoreTaglio.textContent = testo;
  // Senza aria-valuetext un lettore di schermo legge il numero grezzo, senza
  // unita': su un cursore che va da 1697 a 4168 non dice nulla.
  quotaTaglio.setAttribute("aria-valuetext", testo);
}

// Rifatto a ogni geometria nuova e a ogni cambio d'asse: l'intervallo del
// cursore e' quello della geometria mostrata adesso, non quello di prima.
function riallineaTaglio(numero) {
  const ingombro = numero === STEP_CON_TAGLIO ? vista.ingombro() : null;
  comandoTaglio.hidden = ingombro === null;
  // Comando nascosto e taglio ancora attivo sarebbe la vista che contraddice
  // il suo comando: quando sparisce, sparisce anche il piano.
  if (ingombro === null) {
    // E con lui la sua quota: lasciata li', resterebbe l'ultima lettura su un
    // comando che non c'e' piu', cioe' un numero che non misura piu' niente.
    valoreTaglio.textContent = "";
    quotaTaglio.removeAttribute("aria-valuetext");
    return vista.disattivaTaglio();
  }
  const asse = Number(asseTaglio.value);
  const minimo = ingombro.min[asse];
  const massimo = ingombro.max[asse];
  quotaTaglio.min = minimo;
  quotaTaglio.max = massimo;
  quotaTaglio.step = (massimo - minimo) / SCATTI_DEL_CURSORE;
  // Si riparte dal volume intero, e questa volta e' vero: il minimo e' la
  // posizione spenta, non un taglio che non toglie niente. L'intervallo del
  // cursore resta quello dell'ingombro, misurato a video.
  quotaTaglio.value = minimo;
  applicaTaglio();
}

quotaTaglio.addEventListener("input", applicaTaglio);
// Lo step mostrato e non quello scelto, per la stessa ragione di ricaricaVista:
// scelto lo step 11 il viewport porta il volume dello step 9, e passare qui 11
// spegnerebbe il comando del taglio sotto una geometria che si puo' tagliare.
asseTaglio.addEventListener("change", () => riallineaTaglio(passoDaMostrare(stepScelto)));

// Il nome del file: corsa, step e didascalia, cosi' l'immagine in appendice
// dice da sola da dove viene e che cosa mostra. Solo lettere, cifre e
// trattini: e' un nome di file su tre sistemi diversi, e la didascalia porta
// accenti, virgole e unita'.
function nomeDellImmagine(outDir, numero, nome, didascalia) {
  const corsa = String(outDir).split(/[\\/]/).filter(Boolean).pop() ?? "corsa";
  return [corsa, String(numero).padStart(2, "0"), nome, didascalia]
    .map((pezzo) => String(pezzo).toLowerCase().normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))
    .filter(Boolean)
    .join("-") + ".png";
}

// Il PNG lo scrive il browser, dove chi lo salva lo trova gia': nessuna rotta
// nuova, nessun file lasciato sul disco del server, nessuna cartella da
// scegliere. `cattura()` e `preserveDrawingBuffer` esistono in viewport.js da
// agosto ed erano meta' di una funzione: questo e' il chiamante che mancava.
//
// Di primo livello e non una freccia dentro addEventListener, per la stessa
// ragione di `aggiornaDaStato`: dentro la freccia non la esegue nessun banco.
function salvaImmagine() {
  // Nessuno step scelto, niente da salvare: succede solo prima che una corsa
  // sia aperta, e un file col nome di nessuna corsa sarebbe peggio del niente.
  if (stepScelto === null) return;
  const voce = ultimoStato.find((passo) => passo.numero === stepScelto);
  const collegamento = document.createElement("a");
  collegamento.href = vista.cattura();
  collegamento.download = nomeDellImmagine(
    document.getElementById("corsa").textContent,
    stepScelto,
    // La chiave non si stampa mai, si stampa la sua etichetta -- e dove
    // l'etichetta non c'e' resta il numero, non «undefined».
    ETICHETTE[voce?.chiave] ?? `step ${stepScelto}`,
    didascaliaDellaVista().textContent,
  );
  // Nell'albero durante il clic: Firefox ignora in silenzio un <a download>
  // staccato. Tolto subito dopo, perche' un salvataggio non lascia residui
  // nella pagina.
  document.body.append(collegamento);
  collegamento.click();
  collegamento.remove();
}

// «Inquadra» rimette la camera sull'ingombro del pezzo: trascinando la si
// perde, e non c'era modo di tornare indietro se non ricaricando lo step. A
// scena vuota `inquadra()` torna senza fare niente (viewport.js), quindi non
// serve una guardia qui.
document.getElementById("inquadra").addEventListener("click", () => vista.inquadra());
document.getElementById("salva-immagine").addEventListener("click", salvaImmagine);

document.getElementById("elenco-step").addEventListener("click", (evento) => {
  const riga = evento.target.closest(".step");
  if (!riga) return;
  const numero = Number(riga.dataset.numero);
  stepScelto = numero;
  // Una sola generazione per il clic, passata a tutte e due le tratte: se la
  // guardia stesse su mostraStep e non su apriDettaglio, meta' del difetto
  // resterebbe con l'aria di essere risolta.
  const ordine = apriGenerazione();
  // Il comando del taglio si rifa' quando la geometria e' arrivata, non prima:
  // il suo intervallo esce dall'ingombro di cio' che e' disegnato. Non si rifa'
  // affatto se questo clic e' stato superato, altrimenti una risposta vecchia
  // riporterebbe il cursore sullo spento sotto le dita di chi lo sta muovendo.
  ricaricaVista(numero, ordine);
  apriDettaglio(numero, ordine);
});

// La geometria mostrata e il cursore che ne dipende, in un punto solo: due
// gesti lo chiedono, il clic su uno step e la fine di una corsa, e scriverlo
// due volte lascerebbe che uno dei due perda la guardia dell'ordine.
// ordine: dal clic arriva la generazione appena aperta; dallo scorrere degli
// eventi quella in corso, cosi' il ricaricamento non annulla una geometria in
// volo ma viene battuto da un clic dell'utente.
function ricaricaVista(numero, ordine = generazione) {
  // La didascalia della vista sta nel markup e sopravvive al cambio di step:
  // senza questa riga, lasciato lo step 7 resterebbe la frase dello scarto
  // sotto la nuvola dello step 2. Qui e non altrove perche'
  // questo e' l'unico imbuto per cui la vista cambia, dal clic e dal fronte di
  // discesa; chi disegna un campo la riscrive subito dopo.
  didascaliaDellaVista().textContent = "";
  // Lo stato vuoto se ne va appena si chiede una geometria, e torna solo dal
  // ramo qui sotto. Basta questo punto perche' questo e' l'unico imbuto per cui
  // la vista cambia (lo dice il commento qui sopra): scriverlo in ognuno dei
  // rami che disegnano sarebbe la stessa riga in quattro posti, con uno che
  // prima o poi resta indietro e lascia la frase sopra il pezzo.
  const vuotoDellaVista = document.getElementById("vista-vuota");
  vuotoDellaVista.hidden = true;
  // Il ripiego sta QUI e non dentro mostraStep: mostraStep disegna la
  // geometria di UNO step, e chi ci scrive sopra una didascalia conta su
  // quello. Un ripiego la' dentro farebbe posare la frase di uno step sul
  // pezzo di un altro.
  const mostrato = passoDaMostrare(numero);
  if (mostrato === null) {
    // L'unico caso in cui svuotare e' onesto: non c'e' proprio niente a monte.
    // Il testo non da' la colpa allo step scelto -- non e' lui che manca, e'
    // che la corsa non e' mai partita.
    vista.svuota();
    document.getElementById("conteggi").textContent =
      "nessuno step ha ancora prodotto un artefatto: esegui lo step 1";
    // I due si dividono il lavoro e non si ripetono: i conteggi dicono cosa
    // manca adesso, lo stato vuoto dice cosa e' questa superficie e che la
    // colonna a sinistra e' fatta di comandi.
    vuotoDellaVista.hidden = false;
    // Niente geometria, niente passaggio a monte da sovrapporre: la casella se
    // ne va con la vista. Lasciata li' offrirebbe di confrontare due cose che
    // non ci sono.
    comandoDelFantasma().hidden = true;
    riallineaTaglio(null);
    return;
  }
  // `disegnato` e' falso quando la risposta e' stata scartata: senza guardarlo,
  // il cursore si rifarebbe sull'ingombro di una geometria che qualcun altro
  // ha disegnato, cioe' su una lettura che non appartiene a questo numero.
  mostraStep(mostrato, ordine).then((disegnato) => {
    if (disegnato && !superata(ordine)) {
      // `=== true` e non solo truthy: mostraStep torna "vuoto" dal ramo del
      // rifiuto dichiarato, dove ha svuotato la vista e scritto perche'.
      // Attaccarci la coda direbbe «artefatto dello step 9 (Tetraedri)» in fondo
      // a «non c'e' piu' sul disco», cioe' attribuirebbe a uno step una
      // geometria che sullo schermo non c'e'. E' il difetto che vista.svuota()
      // esisteva per chiudere, riaperto dalla correzione che lo chiudeva.
      //
      // riallineaTaglio resta fuori dal `=== true` apposta: sulla vista vuota
      // ingombro() torna null (viewport.js:405) e il comando del taglio si
      // nasconde, che e' cio' che deve succedere.
      if (disegnato === true && mostrato !== numero) {
        const conteggi = document.getElementById("conteggi");
        conteggi.textContent +=
          ` — artefatto dello step ${mostrato} (${nomeDelloStep(mostrato)})`;
      }
      // Lo step MOSTRATO e non quello scelto: il cursore del taglio si rifa'
      // sull'ingombro di cio' che e' disegnato, e la sua stessa nota lo dice.
      riallineaTaglio(mostrato);
    }
    // Dopo mostraStep e dentro il then, non accanto alla chiamata: ogni strada
    // che disegna passa da vista.svuota(), che il velo lo toglie. Posato prima,
    // sparirebbe sotto la geometria che lo doveva accompagnare.
    // Fuori dal `disegnato &&` qui sopra apposta: quando la risposta e' stata
    // scartata o l'artefatto non c'e' piu', mostraFantasmaDelloStep serve
    // comunque a NASCONDERE la casella, che e' cio' che deve succedere.
    mostraFantasmaDelloStep(numero, ordine);
  });
}

// Lo schema e le descrizioni vengono dai modelli di config.py: l'interfaccia
// non li riscrive, e la validazione di cio' che si scrive resta quella dei
// modelli, non una copia lato browser.
let schemaParametri = null;
let configurazione = null;
let stepAperto = null;
// Presa dal markup, non creata qui. La regione role="alert" deve preesistere a
// cio' che annuncia: creata nell'istante in cui ci si scrive dentro, l'annuncio
// non e' garantito. E' la ragione per cui il difetto e' tornato tre volte —
// hidden, poi una regola di stile, poi replaceChildren() che la distruggeva a
// ogni apertura di pannello. Fuori da #dettaglio non c'e' piu' un ramo che
// possa toglierla.
const rigaErrore = document.getElementById("errore");

// Il server manda sempre la ragione di un rifiuto: {"errore", "messaggio"} dal
// gestore generico, il "detail" di pydantic da un 422 su /api/config. Leggerla
// e' l'ultimo metro del contratto, che senza questo si interrompe nel browser.
// Nessun ramo resta muto: se il corpo non e' leggibile, resta lo stato.
async function ragioneDelRifiuto(risposta) {
  const grezzo = await risposta.text();
  try {
    const corpo = JSON.parse(grezzo);
    if (typeof corpo.messaggio === "string") return corpo.messaggio;
    const voce = Array.isArray(corpo.detail) ? corpo.detail[0] : null;
    if (voce?.msg) return `${(voce.loc ?? []).slice(1).join(".")}: ${voce.msg}`;
  } catch {
    // Non e' JSON: sotto si mostra il testo grezzo accorciato.
  }
  return `il server ha risposto ${risposta.status}: ${grezzo.slice(0, 200)}`;
}

// La risposta di un server che non ha risposto. `fetch` solleva quando il
// server non c'e' — fermo, riavviato, rete caduta — e l'eccezione usciva dal
// gestore: tutto cio' che viene dopo non girava, ne' il messaggio a video ne'
// il ripristino del valore di prima, che restava in `configurazione` e partiva
// con la PUT successiva, quella di un altro campo. L'utente toccava knn e sul
// disco cambiava anche voxel_size.
// Un server che non risponde e' un rifiuto come gli altri, quindi prende la
// forma del rifiuto e i rami che gia' mostrano la ragione lo trattano senza
// sapere che e' successo: la stessa coppia {errore, messaggio} del gestore
// generico del server, cosi' ragioneDelRifiuto la legge come qualunque altra.
// Si usa come `.catch(serverMuto)` e non come una fetch avvolta: la fetch resta
// dentro la tratta che la chiede, dove la regola dell'ordine la puo' vedere.
function serverMuto(errore) {
  return {
    ok: false,
    status: 0,
    text: async () => JSON.stringify({
      errore: errore.name,
      messaggio: `il server non ha risposto: ${errore.message}`,
    }),
  };
}

// Un 200 che ha gia' superato risposta.ok puo' comunque rispondere spazzatura:
// corpo malformato (JSON invalido) o corpo che non e' piu' un oggetto leggibile.
// `await risposta.json()` da solo solleva un SyntaxError fuori da qualunque
// catch, e il gestore muore a meta' senza dire niente — l'utente resta davanti
// a un pannello fermo. undefined marca "il corpo non si legge", ed e' diverso
// da null: null e' cio' che il server ha davvero risposto (un campo nullabile
// letto per bene), undefined e' che qui non si e' letto niente. E' la stessa
// distinzione che valoreScritto fa fra un numero e una stringa che non lo e'.
async function corpoLetto(risposta) {
  try {
    return await risposta.json();
  } catch {
    return undefined;
  }
}

// Niente hidden: un elemento nascosto cosi' esce dall'albero di accessibilita',
// e role="alert" non ha piu' una regione viva da sorvegliare, quindi l'annuncio
// non e' garantito. La regione resta sempre nell'albero e cambia solo
// contenuto; a vuota non occupa spazio (.errore:empty in stile.css).
function dichiaraErrore(testo) {
  rigaErrore.textContent = testo ?? "";
}

// Un valore reso come testo, per CONFRONTARLO e non per mostrarlo. Gemella nel
// verso opposto di valoreScritto, che legge cio' che l'utente ha battuto.
//
// Serve perche' un predefinito e il valore corrente arrivano da due strade
// diverse -- lo schema e la configurazione della corsa -- e la stessa cosa puo'
// portare due forme: una tupla contro una lista, un Path contro la stringa in
// cui il server lo ha reso (`default=str` nel carico di /api/schema). Un `!==`
// diretto le direbbe diverse e mostrerebbe come «spostato» un campo che nessuno
// ha toccato.
//
// Niente toLocaleString qui: questo testo non si mostra, e una virgola decimale
// al posto del punto renderebbe diversi due numeri uguali.
function reso(v) {
  if (v === null || v === undefined) return "";
  return ["string", "number", "boolean"].includes(typeof v) ? String(v) : JSON.stringify(v);
}

function cambiatoDalPredefinito(valore, predefinito) {
  return reso(valore) !== reso(predefinito);
}

// Il valore che finisce nella configurazione, dalla stringa lasciata nel campo.
// Pura e di primo livello apposta, come superata(): e' l'unico punto in cui dei
// tasti diventano un dato scritto su disco, e da fuori si puo' provare senza un
// motore di DOM.
//
// trim() perche' Number(" ") e' 0, non NaN: uno spazio scriveva zero in un
// campo che a video sembra vuoto. Tolto lo spazio, un campo che sembra vuoto e'
// vuoto, e vuoto vale null — che e' cio' che il campo mostra.
//
// Quello che non si legge come numero resta la stringa battuta e parte cosi':
// il modello la rifiuta con un 422 leggibile, che e' l'unico posto dove il tipo
// vero si conosce. Trasformarla in null qui la farebbe accettare in silenzio.
//
// isFinite e non isNaN: Number("1e999") e Number("Infinity") non sono NaN, ma
// JSON.stringify li scrive `null`. Passavano la guardia come numeri e il corpo
// della PUT partiva gia' azzerato: chi batteva `1e999` su max_volume credendo
// di alzare il tetto se lo vedeva tolto, con un 200 e lo schermo muto. Fuori
// scala si comporta come illeggibile — resta la stringa battuta, e la decide il
// modello. (Sul residuo che il modello oggi non ferma, vedi il rapporto.)
function valoreScritto(grezzo) {
  const testo = grezzo.trim();
  const numerico = Number(testo);
  return testo === "true" ? true : testo === "false" ? false :
    testo === "" ? null : Number.isFinite(numerico) ? numerico : testo;
}

// Il ritaglio si comanda dallo step che lo esegue: crop_min e crop_max sono
// parametri di segment, e lo step 2 e' quello che li applica.
const STEP_CON_RITAGLIO = 2;

// Sei campi sull'ingombro della nuvola disegnata, il box ridisegnato a ogni
// modifica, e un bottone che manda gli estremi a /api/crop. Il conteggio non
// lo calcola il browser: lo restituisce segment.crop_box, la stessa funzione
// che la pipeline usa allo step 2.
function pannelloRitaglio(ordine) {
  const contenitore = document.createElement("fieldset");
  contenitore.className = "gruppo";
  contenitore.append(elemento("legend", { textContent: "Ritaglio" }));
  const ingombro = vista.ingombro();
  // Senza geometria non c'e' nessun ingombro da leggere, e ingombro() lo dice
  // con null apposta: una scatola vuota darebbe +Infinity e -Infinity, che
  // sono valori accettabili per un campo numerico e per nient'altro.
  if (ingombro === null) {
    contenitore.append(elemento("p", {
      className: "aiuto",
      textContent: "Nessuna nuvola disegnata: esegui lo step per vedere i punti e ritagliarli.",
    }));
    return contenitore;
  }
  // Il pannello si ricostruisce da zero a ogni apertura e leggeva sempre
  // l'ingombro disegnato: dopo un'applicazione riuscita non c'era modo di
  // vedere che cosa fosse davvero scritto su disco. crop_min/crop_max sono
  // null (il default del modello, core/config.py) finche' nessun ritaglio e'
  // stato applicato — solo allora l'ingombro disegnato e' l'unico punto di
  // partenza sensato. Da quel momento in poi il persistito e' la fonte:
  // anche quando coincide con l'ingombro su una nuvola invariata, non e' la
  // stessa domanda, ed e' l'unica che risponde a "che cosa c'e' sul disco".
  const persistito = configurazione.segment.crop_min != null && configurazione.segment.crop_max != null
    ? configurazione.segment
    : null;
  const valori = persistito
    ? { min: [...persistito.crop_min], max: [...persistito.crop_max] }
    : { min: [...ingombro.min], max: [...ingombro.max] };
  // Che cosa sono i sei numeri, in che unita', e che cosa fa il bottone --
  // detto PRIMA di premerlo. La sorgente dei numeri cambia con `persistito`:
  // l'ingombro disegnato e cio' che sta sul disco non sono la stessa domanda,
  // e la frase non deve confonderli.
  contenitore.append(elemento("p", {
    className: "aiuto",
    textContent: (persistito
      ? "Gli estremi del box in mm, come sono scritti nella configurazione della corsa. "
      : "Gli estremi del box in mm, presi dall'ingombro della nuvola disegnata. ")
      + "«Applica il ritaglio» li scrive fra i parametri della segmentazione, "
      + "e conta i punti che resterebbero.",
  }));
  for (const estremo of ["min", "max"]) {
    for (const asse of [0, 1, 2]) {
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(elemento("span", {
        textContent: `${estremo} ${"xyz"[asse]}`,
      }));
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = valori[estremo][asse].toFixed(1);
      input.addEventListener("input", () => {
        const scritto = Number(input.value);
        // Number("") e' 0, non NaN: senza questa riga svuotare il campo
        // porterebbe l'estremo all'origine, il box salterebbe li' e «Applica»
        // manderebbe 0 al server. Un campo vuoto, o a meta' di un numero, non
        // muove il box: si aspetta che ci sia scritto qualcosa di finito.
        if (input.value.trim() === "" || !Number.isFinite(scritto)) return;
        valori[estremo][asse] = scritto;
        vista.mostraBox(valori.min, valori.max);
      });
      riga.append(input);
      contenitore.append(riga);
    }
  }
  const applica = document.createElement("button");
  applica.type = "button";
  applica.className = "bottone";
  applica.textContent = "Applica il ritaglio";
  const esito = document.createElement("p");
  esito.className = "aiuto";
  // Il bottone si riclicca per affinare il box: e' il flusso normale, non un
  // incidente. `ordine` e' la generazione del pannello e non distingue un
  // clic dall'altro nello stesso pannello, esattamente come per i campi
  // (Rilievo 1): un contatore per clic, stessa meccanica di apriBattuta.
  let ultimaRichiesta = 0;
  function apriRichiesta() {
    ultimaRichiesta += 1;
    return ultimaRichiesta;
  }
  applica.addEventListener("click", async () => {
    dichiaraErrore(null);
    const richiesta = apriRichiesta();
    // Il server rilegge la nuvola piena e ne toglie gli outlier, come fa lo
    // step 2: su lab_crop sono 26 s la prima volta, poi la nuvola ripulita
    // resta in memoria. Senza questa riga il bottone resta muto per mezzo
    // minuto e sembra non aver fatto niente.
    esito.textContent = "ritaglio in corso: la prima volta rilegge la nuvola piena, circa mezzo minuto.";
    const risposta = await fetch("/api/crop", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(valori),
    }).catch(serverMuto);
    if (!risposta.ok) {
      const ragione = await ragioneDelRifiuto(risposta);
      // Dopo l'ultima attesa e prima della prima scrittura, come le altre
      // tratte: il ritaglio legge la nuvola piena e puo' metterci qualche
      // secondo, e in quel tempo il pannello sotto puo' essere un altro, o lo
      // stesso pannello puo' aver gia' visto un secondo clic.
      if (superata(ordine) || superata(richiesta, ultimaRichiesta)) return;
      // Senza questa riga «ritaglio in corso» resta scritta qui sotto mentre
      // la riga d'errore appena sopra dice il contrario: l'utente legge
      // insieme "sto lavorando" e "e' fallito".
      esito.textContent = "";
      dichiaraErrore(ragione);
      return;
    }
    const corpo = await corpoLetto(risposta);
    if (superata(ordine) || superata(richiesta, ultimaRichiesta)) return;
    // Un 200 il cui corpo non si legge, o senza points_after, e' un rifiuto
    // come gli altri: senza questo, la riga sotto solleva su un valore che
    // non c'e' e il bottone resta muto per sempre — esattamente il silenzio
    // che il testo appena scritto ("ritaglio in corso") promette di rompere.
    // == e non ===: un corpo null qui non e' mai una risposta legittima (a
    // differenza di un campo nullabile innestato), e passava la guardia.
    if (corpo == null || typeof corpo.points_after !== "number") {
      esito.textContent = "";
      dichiaraErrore("il server ha risposto con un corpo che non descrive il ritaglio applicato");
      return;
    }
    // Il bottone dice «Applica», non «Anteprima»: /api/crop scrive crop_min e
    // crop_max nella configurazione della corsa, e chi sta esplorando deve
    // saperlo qui, non riaprendo il pannello.
    // Che numero sia lo dice il server, non questa riga: `completo` e' vero
    // solo quando l'anteprima e' tutto lo step 2. Con `method: auto` lo step
    // prosegue dopo il ritaglio con i piani e i cluster e ne tiene molti meno
    // (5 000 contro 82 su una nuvola di prova), e affermare la coincidenza li'
    // sarebbe un numero falso con una didascalia che lo garantisce.
    // «questo metodo» e non «method: auto»: l'endpoint dichiara completa solo
    // la tratta di `crop`, cosi' che un terzo metodo futuro cada dalla parte
    // prudente, e nominare `auto` disferebbe proprio quella prudenza.
    // «non ne terra' di piu'» e non «ne terra' di meno»: il cluster scelto e'
    // un sottoinsieme del ritagliato, e nel caso degenere — nessun piano
    // trovato, un cluster solo, nessun rumore — i due numeri coincidono.
    esito.textContent =
      (corpo.completo
        ? `${corpo.points_after.toLocaleString("it")} punti: è quanti ne terrebbe lo step 2 ` +
          "rieseguito con questo box."
        : `${corpo.points_after.toLocaleString("it")} punti dopo il ritaglio: con ` +
          "questo metodo lo step 2 prosegue con i piani e i gruppi, e non ne terrà di più.") +
      " I due spigoli del box sono stati scritti nella configurazione della corsa.";
  });
  contenitore.append(applica, esito);
  vista.mostraBox(valori.min, valori.max);
  return contenitore;
}

// Lo stato di un campo a video, in un punto solo: `rifiuto` e' la ragione
// oppure null. Tre canali insieme perche' due su tre lasciano fuori qualcuno —
// il bordo non lo vede chi non distingue i colori, il testo non lo trova chi
// naviga a tastiera senza aria-errormessage, e aria-invalid da solo dice che
// c'e' un errore ma mai quale.
function segnalaCampo(input, messaggio, rifiuto) {
  input.classList.toggle("campo-rifiutato", rifiuto !== null);
  messaggio.textContent = rifiuto ?? "";
  messaggio.hidden = rifiuto === null;
  if (rifiuto === null) {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-errormessage");
  } else {
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-errormessage", messaggio.id);
  }
}

// Le scritture di parametro sono il terzo requisito con lo stesso raggio del
// difetto dell'ordine, alla granularita' del singolo campo. Due battute sullo
// stesso campo, nello stesso pannello aperto, condividono `ordine` — che e' la
// generazione del clic che ha aperto il pannello, non della battuta — quindi
// superata(ordine) da solo non le distingue fra loro: se la PUT della prima
// battuta rientra dopo la seconda, riscrive sul campo (e sulla prossima PUT di
// un altro campo, che riparte da `configurazione`) un valore piu' vecchio di
// quello appena battuto. E' la stessa famiglia di difetto — l'ordine fra
// risposte — gia' corretta due volte su questo file, sulla generazione del
// clic (`generazione`) e sulla richiesta di geometria (`ultimaGeometria`); qui
// il requisito e' un terzo, non coperto da nessuno dei due: un contatore per
// campo.
const ultimaBattutaDelCampo = new Map();

function apriBattuta(chiave) {
  const battuta = (ultimaBattutaDelCampo.get(chiave) ?? 0) + 1;
  ultimaBattutaDelCampo.set(chiave, battuta);
  return battuta;
}

// Dai tasti al disco: e' l'unica strada per cui una battuta diventa un dato
// persistito, quindi sta di primo livello come valoreScritto() e si esegue da
// fuori con una fetch finta. Dentro un gestore anonimo non era raggiungibile da
// nessun banco, e due difese che mancavano — il ripristino dopo una rete caduta
// e la riscrittura del valore accettato — non le fermava nessun controllo.
// ordine: la generazione del clic che ha aperto questo pannello.
//
// Il valore lo legge dalla casella; `scriviValore` fa il resto. La divisione
// esiste da quando due comandi dello step 1 -- i due menu della scala e le tre
// caselle delle dimensioni attese -- scrivono un campo del modello senza che
// una casella sola lo contenga: la parte che parla col server e ricuce
// l'ordine delle risposte resta una, e non se ne fabbrica una seconda copia.
async function scriviParametro(blocco, nome, input, messaggio, ordine) {
  return scriviValore(blocco, nome, valoreScritto(input.value), input, messaggio, ordine);
}

// La scrittura vera: mette il valore nella configurazione, la manda intera, e
// riporta a video cio' che il server ha accettato.
// riporta: come il valore accettato torna nei comandi. Il predefinito e' la
// casella singola; chi ne ha piu' d'una passa il proprio.
async function scriviValore(
  blocco, nome, valore, input, messaggio, ordine,
  riporta = (accettato) => { input.value = String(accettato ?? ""); },
) {
  const chiave = `${blocco}.${nome}`;
  const battuta = apriBattuta(chiave);
  const precedente = configurazione[blocco][nome];
  configurazione[blocco][nome] = valore;
  const risposta = await fetch("/api/config", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(configurazione),
  }).catch(serverMuto);
  const rifiuto = risposta.ok ? null : await ragioneDelRifiuto(risposta);
  const salvata = risposta.ok ? await corpoLetto(risposta) : null;
  // Dopo l'ultima attesa e prima della prima scrittura: configurazione e' di
  // modulo e la riapre ogni pannello, quindi un rifiuto tornato tardi
  // rimetterebbe il proprio valore di prima dentro la configurazione di un
  // altro step. superata(battuta, ...) scarta anche la risposta di una
  // battuta piu' vecchia sullo stesso campo, che superata(ordine) da solo non
  // vede perche' tutte le battute di questo pannello condividono `ordine`.
  if (superata(ordine) || superata(battuta, ultimaBattutaDelCampo.get(chiave))) return;
  if (rifiuto !== null) {
    // Il valore rifiutato non resta nell'oggetto: la PUT manda l'intera
    // configurazione, e tenerlo farebbe rifiutare ogni modifica successiva
    // accusando il campo sbagliato — o, quando il rifiuto e' una rete caduta,
    // lo scriverebbe su disco alla prima modifica riuscita di un altro campo.
    configurazione[blocco][nome] = precedente;
    segnalaCampo(input, messaggio, rifiuto);
    return;
  }
  // Un 200 il cui corpo non si legge, o non descrive piu' il blocco appena
  // scritto, non ripristina precedente: la PUT e' stata accettata (risposta.ok),
  // quindi il valore appena battuto e' gia' su disco. Ripristinare precedente
  // qui lo terrebbe sbagliato in memoria, e la prossima PUT di un altro campo
  // lo riscriverebbe sopra — lo stesso guasto per cui un rifiuto vero, sotto,
  // non tocca mai un valore che il server ha davvero accettato. Non si cachea
  // nemmeno: `configurazione = salvata` resta fuori da questo ramo.
  // == e non ===: il corpo intero di /api/config non e' mai un null
  // legittimo (a differenza di un campo nullabile innestato, come
  // downsample.voxel_size, che e' il caso per cui esiste la distinzione
  // undefined/null). Un null vero qui bypassava il primo `?.` non c'e' sul
  // primo livello e faceva sollevare la riga sotto fuori da ogni catch.
  if (salvata == null || salvata[blocco]?.[nome] === undefined) {
    segnalaCampo(input, messaggio,
      "il server ha accettato la modifica ma non ne ha confermato il valore");
    return;
  }
  // Nel campo finisce il valore che il server ha accettato, non quello battuto.
  // Non e' grafia: `1_0` diventa 10, `0x10` diventa 16, `9.0` su un intero
  // diventa 9, `no` diventa false. Tutte accettate con 200 e schermo muto,
  // tutte con il campo che continuava a mostrare la battuta. Riscriverlo e' cio'
  // che rende la differenza visibile invece che caso per caso: a video finisce
  // cio' che e' stato salvato.
  // La memoria segue il disco per intero, non solo su questo campo: la risposta
  // e' la configurazione canonica appena scritta, ed e' quella che la PUT
  // successiva deve mandare.
  configurazione = salvata;
  riporta(configurazione[blocco][nome]);
  segnalaCampo(input, messaggio, null);
}

// La scala del rilievo, letta come si legge su un disegno: un rapporto e
// l'unita' a cui si riferisce. `1` con `cm` vuol dire «la nuvola e' gia' in
// centimetri e ci resta»; `10` con `cm` vuol dire 1:10 in centimetri.
//
// Nel modello `input.scale` resta il numero che e' sempre stato -- il fattore
// verso i millimetri -- e la composizione vive soltanto qui. Non e' pigrizia:
// quel campo sta nei `config.yaml` delle corse registrate e dentro l'impronta,
// e due campi nuovi sposterebbero l'impronta di ventidue righe di registro che
// sono la provenienza di una tabella sperimentale.
const FATTORI_DI_SCALA = [1, 2, 5, 10, 20, 50, 100, 1000];
const UNITA_DI_SCALA = { m: 1000, cm: 10, mm: 1 };

// La coppia che produce quel numero, o null se nessuna lo produce.
//
// Le unita' si provano dalla piu' grande: 1000 e' sia `1 m` sia `100 cm` sia
// `1000 mm`, e fra tre letture dello stesso fatto si mostra quella col fattore
// piu' piccolo, che e' come la si direbbe a voce. Un numero che nessuna coppia
// produce -- `scale: 3` in una corsa vecchia -- torna null: il pannello lo
// mostra com'e' invece di arrotondarlo alla coppia piu' vicina, che
// cambierebbe in silenzio la scala di una corsa gia' registrata.
function coppiaDiScala(valore) {
  for (const [unita, inMillimetri] of Object.entries(UNITA_DI_SCALA)) {
    const fattore = valore / inMillimetri;
    if (FATTORI_DI_SCALA.includes(fattore)) return { fattore, unita };
  }
  return null;
}

// L'unita' con cui si scrivono le dimensioni attese: quella scelta per la
// scala. Dove la scala non si compone da nessuna coppia restano i millimetri,
// che sono l'unita' in cui il modello le tiene.
function unitaDellaScala() {
  return coppiaDiScala(configurazione.input?.scale ?? 1)?.unita ?? "mm";
}

// Lo scheletro comune alle due righe composte: etichetta, contenitore dei
// comandi, aiuto e messaggio di rifiuto, nello stesso ordine e con gli stessi
// identificativi delle righe scalari.
function rigaComposta(blocco, nome, campo) {
  const identita = `${blocco}-${nome}`;
  const riga = elemento("div", { className: "campo" });
  const etichetta = elemento("label", {
    id: `etichetta-${identita}`,
    textContent: campo.etichetta ?? nome,
  });
  const comandi = elemento("span", { className: "campo-riga" });
  const aiuto = elemento("small", { className: "aiuto", id: `aiuto-${identita}` });
  const messaggio = elemento("small", { className: "errore-campo", id: `errore-${identita}` });
  messaggio.hidden = true;
  return { identita, riga, etichetta, comandi, aiuto, messaggio };
}

// I due menu della scala. Scrivono un numero solo, quello di sempre.
function campoScala(blocco, nome, campo, ordine) {
  const { identita, riga, etichetta, comandi, aiuto, messaggio } = rigaComposta(blocco, nome, campo);
  riga.append(etichetta);
  const valore = (configurazione[blocco] ?? {})[nome] ?? null;
  const coppia = valore === null ? null : coppiaDiScala(valore);
  if (coppia === null) {
    // Nessuna coppia lo produce: resta la casella, col numero dentro, e la
    // riga dice perche' i due menu non ci sono. Detto e non arrotondato.
    const casella = elemento("input", { id: `campo-${identita}` });
    casella.value = valore === null ? "" : String(valore);
    etichetta.setAttribute("for", casella.id);
    casella.addEventListener("change", () => scriviParametro(blocco, nome, casella, messaggio, ordine));
    aiuto.textContent = `Nessuna coppia di fattore e unità dà ${valore}: resta il numero, `
      + "che è il fattore verso i millimetri, e si scrive a mano.";
    casella.setAttribute("aria-describedby", aiuto.id);
    riga.append(casella, aiuto, messaggio);
    return riga;
  }
  const fattore = elemento("select", { id: `campo-${identita}-fattore` });
  for (const ammesso of FATTORI_DI_SCALA) {
    fattore.append(elemento("option", { value: String(ammesso), textContent: `1:${ammesso}` }));
  }
  fattore.value = String(coppia.fattore);
  const unita = elemento("select", { id: `campo-${identita}-unita` });
  for (const ammessa of Object.keys(UNITA_DI_SCALA)) {
    unita.append(elemento("option", { value: ammessa, textContent: ammessa }));
  }
  unita.value = coppia.unita;
  // L'etichetta nomina il fattore per `for` e l'unita' per riferimento: sono
  // due comandi di uno stesso parametro, come il cursore e la sua casella.
  etichetta.setAttribute("for", fattore.id);
  unita.setAttribute("aria-labelledby", etichetta.id);
  const riporta = (accettato) => {
    const tornata = coppiaDiScala(accettato);
    if (tornata === null) return;
    fattore.value = String(tornata.fattore);
    unita.value = tornata.unita;
  };
  const scrivi = () => scriviValore(
    blocco, nome, Number(fattore.value) * UNITA_DI_SCALA[unita.value],
    fattore, messaggio, ordine, riporta,
  );
  fattore.addEventListener("change", scrivi);
  unita.addEventListener("change", scrivi);
  comandi.append(fattore, unita);
  aiuto.textContent = "Si leggono insieme: fattore 1 con unità cm vuol dire che la nuvola "
    + "è già in centimetri e ci resta.";
  fattore.setAttribute("aria-describedby", aiuto.id);
  riga.append(comandi, aiuto, messaggio);
  return riga;
}

// Le tre dimensioni reali misurate, nell'unità scelta per la scala.
//
// Possono restare tutte e tre vuote, ed è il predefinito: vuote significa
// «nessun controllo di scala richiesto», cioè `expected_size = None`. Una
// terna a metà e una misura non numerica sono due rifiuti detti qui, prima
// della PUT: dal server tornerebbe un errore di validazione sul tipo, che non
// dice all'operatore che cosa manca.
const ASSI_DELLE_DIMENSIONI = ["x", "y", "z"];

function campoDimensioniAttese(blocco, nome, campo, ordine) {
  const { identita, riga, etichetta, comandi, aiuto, messaggio } = rigaComposta(blocco, nome, campo);
  riga.append(etichetta);
  const unita = unitaDellaScala();
  const inMillimetri = UNITA_DI_SCALA[unita];
  const misure = (configurazione[blocco] ?? {})[nome] ?? null;
  const caselle = ASSI_DELLE_DIMENSIONI.map((asse, indice) => {
    const casella = elemento("input", { id: `campo-${identita}-${asse}` });
    casella.value = misure === null ? "" : String(misure[indice] / inMillimetri);
    casella.setAttribute("aria-label", `${campo.etichetta ?? nome}, ${asse}`);
    return casella;
  });
  etichetta.setAttribute("for", caselle[0].id);
  const scrivi = () => {
    const battute = caselle.map((casella) => casella.value.trim());
    if (battute.every((battuta) => battuta === "")) {
      return scriviValore(blocco, nome, null, caselle[0], messaggio, ordine, riporta);
    }
    if (battute.some((battuta) => battuta === "")) {
      segnalaCampo(caselle[0], messaggio,
        "servono tutte e tre le misure, oppure nessuna: tre caselle vuote valgono «nessun controllo di scala»");
      return undefined;
    }
    const numeri = battute.map(Number);
    const guasta = numeri.findIndex((numero) => !Number.isFinite(numero));
    if (guasta !== -1) {
      segnalaCampo(caselle[0], messaggio,
        `«${battute[guasta]}» non è un numero: la misura ${ASSI_DELLE_DIMENSIONI[guasta]} va scritta in cifre`);
      return undefined;
    }
    return scriviValore(
      blocco, nome, numeri.map((numero) => numero * inMillimetri),
      caselle[0], messaggio, ordine, riporta,
    );
  };
  function riporta(accettate) {
    caselle.forEach((casella, indice) => {
      casella.value = accettate === null ? "" : String(accettate[indice] / inMillimetri);
    });
  }
  for (const casella of caselle) casella.addEventListener("change", scrivi);
  comandi.append(...caselle, elemento("span", { className: "unita", textContent: unita }));
  aiuto.textContent = `Le misure reali del pezzo, in ${unita}. Vuote tutte e tre: nessun `
    + "controllo di scala, che è il predefinito.";
  caselle[0].setAttribute("aria-describedby", aiuto.id);
  riga.append(comandi, aiuto, messaggio);
  return riga;
}

// La riga di un parametro: etichetta, casella, aiuto e messaggio d'errore.
// Estratta dal ciclo che la costruiva perche' e' il punto in cui la casella
// nasce e in cui il gestore le viene attaccato, e da dentro un ciclo dentro una
// funzione da duecento righe non la esegue nessun banco.
// La forma della casella viene dal tipo, e il tipo viene dallo schema. Prima
// veniva da `typeof` del valore corrente, cioe' era indovinato: i campi
// numerici nullabili erano testo finche' valevano None e numerici appena
// valevano qualcosa, e gli interi ricevevano step="any", che il passo unitario
// lo toglie invece di metterlo. Il guasto vero era un altro: Chrome sanifica
// cio' che non sa leggere -- battuto `1e`, `.value` torna `""` mentre a video
// resta scritto `1e`, e `""` diventava null. La configurazione della corsa
// finiva su disco col parametro azzerato e sullo schermo non compariva niente.
//
// Il tipo lo conosce solo il modello, e adesso /api/schema lo manda
// (`_forma_del_campo` in app/server.py). Da li' discende la forma:
// Il testo dell'aiuto sotto un campo. Il predefinito si dice: chi ha girato
// min_ratio tre volte deve sapere da dove e' partito, e /api/schema lo manda
// gia' -- il pannello lo usava solo per piegare i campi fermi.
//
// `!== undefined && !== null` e non `if (campo.default)`: `0`, `false` e la
// stringa vuota sono predefiniti veri, e un controllo sul valore li
// nasconderebbe proprio dove ce n'e' piu' bisogno.
function testoDellAiuto(campo, scalare, bloccoAssente) {
  return [
    campo.description,
    campo.default !== undefined && campo.default !== null
      ? `predefinito: ${String(campo.default)}`
      : null,
    !scalare && !bloccoAssente ? "si modifica dal file di configurazione" : null,
  ].filter(Boolean).join(" — ");
}

// un'enumerazione e' un menu, un booleano una spunta, un numero con entrambi
// gli estremi un cursore con la sua casella accanto. Nessuna di queste e'
// `type="number"`: la sanificazione silenziosa resta fuori dal pannello, e cio'
// che il browser non sa leggere continua a partire com'e' stato battuto,
// perche' il rifiuto lo dica il modello con un 422 leggibile.
//
// Dove la forma scelta non saprebbe mostrare cio' che c'e' gia' scritto -- un
// valore fuori dal dominio in una corsa vecchia, un nullabile che vale il
// vuoto -- si torna alla casella di testo: una casella che non sa
// rappresentare un valore esistente lo cancellerebbe.
function campoParametro(blocco, nome, campo, ordine) {
  // I due campi dello step 1 che non sono una casella sola, e vanno prima di
  // tutto: nulla di cio' che segue saprebbe costruirne la riga. Per blocco e
  // nome, non per tipo -- sono due composizioni decise, non una regola che
  // vale per ogni campo che ha quella forma.
  if (blocco === "input" && nome === "scale") return campoScala(blocco, nome, campo, ordine);
  if (blocco === "input" && nome === "expected_size") {
    return campoDimensioniAttese(blocco, nome, campo, ordine);
  }
  // La riga e' un <div> e l'etichetta nomina per `for`. Era una <label> che
  // avvolgeva tutto, e dentro la <label> stavano anche l'aiuto e il messaggio
  // di rifiuto: il nome accessibile della casella non era «voxel_size» ma
  // «voxel_size» seguito dalla descrizione intera, ripetuta a ogni fuoco e a
  // ogni tabulazione, e col rifiuto attaccato in coda quando ce n'era uno.
  // E' la stessa lezione gia' scritta nell'ingresso -- il commento sopra
  // #nuova-nome in index.html, dove il <small> e' uscito dalla <label> per
  // questo: descritto e' cio' che serve, nominato no.
  const identita = `${blocco}-${nome}`;
  const riga = document.createElement("div");
  riga.className = "campo";
  const etichetta = document.createElement("label");
  etichetta.id = `etichetta-${identita}`;
  etichetta.setAttribute("for", `campo-${identita}`);
  // «Una chiave non si stampa mai, si stampa la sua etichetta» (PRODUCT.md).
  // Dove lo schema non ne porta una la chiave resta l'unica cosa che si sa, e
  // una frase inventata qui sarebbe peggio del nome vero.
  etichetta.textContent = campo.etichetta ?? nome;
  riga.append(etichetta);
  const valore = (configurazione[blocco] ?? {})[nome] ?? null;
  // Una lista o un modello annidato non sono scritti in una casella di testo:
  // String() li renderebbe come "1,2,4" o "[object Object]", cioe' un testo che
  // nessuna lettura produce, e ogni modifica tornerebbe comunque rifiutata dal
  // modello.
  // Il blocco intero puo' mancare, non solo il singolo valore: `analysis` non
  // esiste finche' il materiale non e' dichiarato. Un campo di un blocco
  // assente non si scrive uno alla volta -- la PUT manderebbe un blocco a
  // meta' -- e va dichiarato tutto insieme dal pannello piu' sotto, che dice
  // gia' che il blocco non c'e': qui basta il campo in sola lettura.
  const bloccoAssente = configurazione[blocco] == null;
  // Il tipo dallo schema. Uno schema che non lo dichiara -- o che dichiara un
  // tipo che questo pannello non conosce -- non spegne la riga: si ricade sulla
  // casella di testo, che e' cio' che il pannello ha sempre fatto.
  const scalare = campo.tipo === undefined
    ? valore === null || ["string", "number", "boolean"].includes(typeof valore)
    : campo.tipo !== "composto";
  const valori = campo.tipo === "enumerazione" ? campo.valori ?? [] : [];
  // Un `Literal` con un valore solo non e' una scelta: un menu con una voce
  // sola e' un menu che mente. Resta il valore, in un campo che non si scrive.
  const senzaScelta = valori.length === 1;
  const vivo = scalare && !bloccoAssente && !senzaScelta;
  // `ge`/`le` sono inclusi, `gt`/`lt` esclusi: distinguerli e' cio' che tiene
  // il cursore dentro il dominio invece di offrire l'estremo che il modello
  // rifiuta. Un estremo solo non fa un cursore -- sarebbe un cursore su un
  // intervallo inventato.
  const minimo = campo.ge ?? campo.gt;
  const massimo = campo.le ?? campo.lt;
  const numerico = campo.tipo === "intero" || campo.tipo === "reale";
  // Un intero si muove di 1; un reale, di un centesimo del proprio intervallo.
  const passo = campo.tipo === "intero" ? 1 : (massimo - minimo) / 100;
  // Nullabile mai: il vuoto significa «decidi tu» (`voxel_size`,
  // `max_hole_area`), e ne' un cursore ne' una spunta ne' un menu sanno
  // esprimerlo. Quei campi restano caselle di testo, da cui il vuoto si scrive.
  const scorrevole = vivo && numerico && !campo.nullabile
    && minimo !== undefined && massimo !== undefined;
  const menu = vivo && !campo.nullabile && valori.length > 1 && valori.includes(valore);
  const spunta = vivo && !campo.nullabile && campo.tipo === "booleano"
    && (valore === true || valore === false);
  const input = document.createElement(menu ? "select" : "input");
  input.id = `campo-${identita}`;
  if (menu) {
    for (const ammesso of valori) {
      input.append(elemento("option", { value: ammesso, textContent: String(ammesso) }));
    }
  }
  if (spunta) input.type = "checkbox";
  // Il vuoto prima di tutto: `String(null)` e `JSON.stringify(null)` danno
  // tutti e due la stringa "null", quattro lettere in una casella che e'
  // vuota, e chi la riscrive senza toccarla manda al modello quella stringa.
  input.value = valore === null ? "" : scalare ? String(valore) : JSON.stringify(valore);
  if (spunta) input.checked = valore === true;
  // Niente `input.title`: era la stessa frase dell'aiuto qui sotto, detta una
  // seconda volta in un fumetto che non si apre da tastiera ne' col dito, e che
  // il lettore di schermo accoda al nome. Detta una volta sola, sotto la
  // casella, dove si legge senza doverla chiedere.
  const messaggio = document.createElement("small");
  messaggio.className = "errore-campo";
  messaggio.id = `errore-${identita}`;
  messaggio.hidden = true;
  if (!vivo) {
    // readOnly e non disabled: disabled lo toglierebbe anche dalla navigazione
    // da tastiera e dal lettore di schermo.
    input.readOnly = true;
  } else {
    // La spunta lascia nel campo il testo che `valoreScritto` sa leggere: e'
    // l'unico punto in cui dei tasti diventano un dato scritto su disco, e
    // resta uno solo. Attaccato prima del gestore che scrive, perche' i
    // gestori corrono nell'ordine in cui sono stati aggiunti.
    if (spunta) input.addEventListener("change", () => { input.value = String(input.checked); });
    if (scorrevole) {
      const cursore = document.createElement("input");
      cursore.type = "range";
      cursore.id = `cursore-${identita}`;
      // L'estremo escluso si sposta dentro di un passo: `lt: 1.0` con passo
      // 0,01 arriva a 0,99, non a 1, che il modello rifiuterebbe.
      cursore.min = String(campo.gt === undefined ? minimo : minimo + passo);
      cursore.max = String(campo.lt === undefined ? massimo : massimo - passo);
      cursore.step = String(passo);
      cursore.value = String(valore ?? "");
      // Il cursore e la casella sono due comandi per lo stesso parametro:
      // l'etichetta li nomina entrambi, ma `for` ne punta uno solo.
      cursore.setAttribute("aria-labelledby", etichetta.id);
      // I due versi. Il cursore muove la casella mentre si trascina e scrive
      // quando si lascia; la casella riporta il cursore dove e' stato battuto.
      // Scrive sempre la casella: e' l'unica delle due che sa mostrare un
      // valore fuori dall'intervallo del cursore senza cancellarlo.
      cursore.addEventListener("input", () => { input.value = cursore.value; });
      cursore.addEventListener("change", () => scriviParametro(blocco, nome, input, messaggio, ordine));
      input.addEventListener("change", () => { cursore.value = input.value; });
      riga.append(cursore);
    }
    input.addEventListener("change", () => scriviParametro(blocco, nome, input, messaggio, ordine));
  }
  riga.append(input);
  // Dire il predefinito e non saperlo rimettere lascerebbe il lavoro a chi
  // legge: il bottone rimette il valore e lo scrive, per la stessa strada di
  // una battuta a mano -- `change` sul comando, cioe' il gestore che gia' c'e'.
  // Passare da li' e non da `scriviValore` diretto e' cio' che tiene allineati
  // anche il cursore e la spunta, che sono l'altra meta' di quel comando.
  // Solo su un campo vivo: dove la casella e' in sola lettura -- blocco
  // assente, scelta unica -- non c'e' nessun gestore da scatenare, e la
  // scrittura cadrebbe su un blocco che non esiste.
  if (vivo && campo.default !== undefined && campo.default !== null) {
    const riporta = elemento("button", {
      type: "button", className: "bottone riporta", textContent: "Riporta",
      title: `riporta al predefinito (${String(campo.default)})`,
      // Venti «Riporta» in un pannello sono venti bottoni identici per chi
      // ascolta: il nome accessibile dice quale campo, e lo dice con
      // l'etichetta che si legge a video, non con la chiave.
      ariaLabel: `Riporta ${etichetta.textContent} al predefinito`,
    });
    riporta.addEventListener("click", () => {
      input.value = String(campo.default);
      if (spunta) input.checked = campo.default === true;
      input.dispatchEvent(new Event("change"));
    });
    riga.append(riporta);
  }
  const aiuto = document.createElement("small");
  aiuto.className = "aiuto";
  aiuto.id = `aiuto-${identita}`;
  aiuto.textContent = testoDellAiuto(campo, scalare, bloccoAssente);
  // Legato solo se c'e' qualcosa da leggere: uno schema che non descrive il
  // campo lascia l'aiuto vuoto, e un aria-describedby che punta a una riga muta
  // e' una descrizione promessa e non mantenuta.
  if (aiuto.textContent !== "") input.setAttribute("aria-describedby", aiuto.id);
  riga.append(aiuto, messaggio);
  return riga;
}

// Il catalogo di norma, letto una volta sola per sessione.
//
// Non cambia mai mentre il programma gira -- e' una tabella delle NTC 2018
// compilata in `core/materiali.py` -- e il pannello del materiale si riapre a
// ogni clic sullo step: rileggerlo ogni volta sarebbe una richiesta al server
// per un dato che non si muove.
//
// Un catalogo che non si carica lascia le quattro caselle esattamente come
// erano: il materiale si dichiara ancora a mano, che e' la strada che c'era
// prima del menu'. Il menu' e' una scorciatoia, non l'unica via.
let catalogoDeiMateriali = null;

// L'esito dell'ultima scrittura riuscita del materiale, in attesa del ridisegno
// che lo mostra e lo consuma. Di modulo perche' il pannello che lo scrive viene
// distrutto dal ridisegno che deve mostrarlo: vedi `pannelloMateriale`.
let esitoDelMateriale = null;

async function catalogoMateriali() {
  if (catalogoDeiMateriali !== null) return catalogoDeiMateriali;
  const risposta = await fetch("/api/materiali").catch(serverMuto);
  if (!risposta.ok) return [];
  const corpo = await corpoLetto(risposta);
  // Le voci senza `classe` cadono qui e non piu' avanti. E' l'unico punto in
  // cui il catalogo entra nel programma, e cio' che passa arriva a tre lettori
  // diversi: il menu' ne farebbe righe senza testo, e la rilettura del nome ci
  // si romperebbe dentro -- dentro una `.then`, cioe' con una promessa rifiutata
  // che nessuno cattura e niente a video.
  catalogoDeiMateriali = Array.isArray(corpo?.voci)
    ? corpo.voci.filter((voce) => typeof voce?.classe === "string")
    : [];
  return catalogoDeiMateriali;
}

// La classe scritta come nome di materiale: «C25/30» diventa «C25_30».
//
// La barra non passa `NomeSet` (`core/config.py`), il tipo che vincola il nome
// del materiale insieme ai nomi di elset, di passo e di selettore: la ragione
// sta nel campo `Material.name` e non si ricopia qui, e allargare quel vincolo
// non sarebbe una scelta di questo pannello. La sostituzione specchia la classe
// di caratteri invece di elencarne uno: nel catalogo di oggi la barra e' il solo
// carattere vietato, ma una voce futura con uno spazio o un accento non
// ritroverebbe il 422.
//
// Trattino basso e non il taglio del pezzo dopo la barra: il menu' riaperto
// ritrova la classe gia' dichiarata confrontando i nomi, quindi la
// trasformazione deve reggere all'indietro, e un «C25» tagliato darebbe lo
// stesso nome a C25/30 e a C25/35.
function nomeDellaClasse(classe) {
  return classe.replace(/[^A-Za-z0-9_.-]/g, "_");
}

// Dal catalogo e da una classe, i quattro valori che vanno nelle caselle.
//
// La classe diventa il **nome** del materiale, e non un campo a parte: il nome
// e' cio' che il deck interpola in `*MATERIAL, NAME=...` e cio' che
// `config.yaml` conserva, quindi e' l'unico posto in cui la provenienza dei
// tre numeri sopravvive fino a chi legge il modello. Un campo nuovo nello
// schema avrebbe mosso l'impronta di ogni corsa senza aggiungere nulla che
// questo non dica.
//
// Poisson e densita' passano come sono: nel catalogo sono costanti esatte
// (0,2 e 2,5493e-9), non risultati di un conto. Il modulo elastico invece e'
// derivato dalla [11.2.2] e in doppia precisione esce 31475,806210019346 su
// C25/30: quattordici decimali in una casella, e poi in `config.yaml`, sono
// rumore che si legge come precisione. Si arrotonda al centesimo di MPa --
// tre parti su dieci milioni, mentre le NTC e l'EC2 tabulano E_cm a tre cifre
// significative. Restano 31475,81, che e' il valore di norma; il 31500 che una
// corsa reale portava scritto a mano e' un'altra cosa, e sbaglia di 24 MPa.
//
// `null` e non una voce di ripiego quando la classe non c'e': la voce vuota
// del menu' e una classe sconosciuta significano tutte e due «non riempire
// niente», e riempire con la prima voce del catalogo metterebbe in un modello
// un calcestruzzo che nessuno ha scelto.
function valoriDellaClasse(voci, classe) {
  const voce = voci.find((v) => v.classe === classe);
  if (voce === undefined) return null;
  return {
    name: nomeDellaClasse(voce.classe),
    young: String(Math.round(voce.young * 100) / 100),
    poisson: String(voce.poisson),
    density: String(voce.density),
  };
}

// Il materiale, dichiarato dagli step che lo pretendono e non prima.
//
// `campoParametro` scrive un campo scalare per volta, e il materiale e' un
// modello annidato: senza questo pannello restava modificabile solo dal file
// di configurazione, cioe' da nessuna parte per chi il programma lo apre e
// basta. I quattro campi partono insieme perche' un materiale a meta' non e'
// un materiale, e le caselle vuote non portano suggerimenti (vedi il docstring
// di `config.Material` per il difetto misurato da cui discende la regola).
function pannelloMateriale(numero, ordine) {
  const gruppo = document.createElement("fieldset");
  gruppo.className = "gruppo";
  gruppo.append(elemento("legend", { textContent: "materiale" }));
  const dichiarato = configurazione.analysis?.material ?? null;
  gruppo.append(elemento("p", {
    className: "aiuto",
    textContent: dichiarato
      ? "Dichiarato da chi analizza. Il programma non lo deduce dalla nuvola."
      : `Non dichiarato: lo step ${numero} si ferma finché questi quattro valori non ci sono. `
        + "Il programma non ne mette uno per conto suo.",
  }));
  // L'esito dell'ultima scrittura riuscita, letto e consumato qui.
  //
  // Una variabile di modulo e non un nodo scritto dal gestore: dopo la PUT il
  // pannello si ridisegna da capo (`apriDettaglio`), e una frase scritta in un
  // nodo di questo fieldset sparirebbe nell'istante in cui compare. Consumata
  // dal disegno perche' dice «appena scritto»: riaperto lo step domani, la
  // stessa frase sarebbe la lapide di una scrittura vecchia.
  const esitoScritto = esitoDelMateriale;
  esitoDelMateriale = null;
  // Il menu' sta SOPRA le quattro caselle perche' e' il gesto che viene
  // prima: si sceglie una classe e le caselle si riempiono. Sotto, sarebbe
  // una correzione di cio' che si e' gia' battuto.
  const rigaClasse = document.createElement("label");
  // `campo-catalogo` oltre a `campo`: lo stile e' lo stesso, ma questa riga
  // non e' uno dei quattro valori dichiarati -- e' il gesto che li riempie.
  // Il banco che conta le caselle del materiale cerca `campo` esatto, e senza
  // la seconda classe questa riga si sarebbe contata come quinta.
  rigaClasse.className = "campo campo-catalogo";
  // «classe (NTC 2018)» e non piu' «Tab. 4.1.I»: quella tabella e' l'elenco
  // delle classi e nient'altro, mentre sotto l'etichetta compaiono anche E,
  // Poisson e densita', che vengono dal §11.2.10.1, dal §11.2.10.4 e dalla
  // Tab. 3.1.I. Chi citava questa riga in tesi citava la tabella sbagliata per
  // tre numeri su quattro. La fonte per esteso la porta la voce scelta, qui
  // sotto: e' il catalogo a saperla, non questa etichetta.
  rigaClasse.append(elemento("span", { textContent: "classe (NTC 2018)" }));
  const menuClasse = document.createElement("select");
  // La voce vuota e' la prima e resta selezionata: un menu' che nasce su
  // «C8/10» direbbe che quella classe e' stata scelta, e nessuno l'ha scelta.
  const voceVuota = elemento("option", { value: "", textContent: "— scegli una classe —" });
  menuClasse.append(voceVuota);
  rigaClasse.append(menuClasse);
  // La provenienza della classe scelta, sotto il menu' e fuori dalla <label>:
  // dentro finirebbe nel nome accessibile del menu' invece che nella sua
  // descrizione, ed e' la lezione gia' pagata dalle righe dei parametri.
  //
  // `fonte` e `avvertenze` le serve /api/materiali per ogni voce, e la sua
  // docstring dice perche': senza la fonte, i tre valori che il menu' scrive
  // nelle caselle sono indistinguibili da valori inventati; e le avvertenze
  // sono dove C8/10 dichiara di stare sotto la classe minima per le strutture
  // semplicemente armate, che chi sceglie quella voce deve leggere qui perche'
  // altrove non lo leggerebbe.
  //
  // La `nota` no, benche' la tratta la serva: e' la provenienza per intero, e
  // le sue prime mille battute difendono la scelta di Poisson e della densita'
  // -- vere per ogni classe, quindi non una risposta a cio' che si e' appena
  // scelto. Mostrata qui, seppelliva l'unica frase che riguardava la scelta.
  const provenienza = document.createElement("small");
  provenienza.className = "aiuto";
  // A voce assente resta vuota, e vuota non occupa spazio: nessuna classe
  // scelta vuol dire nessuna fonte da affermare, e affermarne una sopra quattro
  // numeri battuti a mano sarebbe precisamente la bugia che questa riga esiste
  // per impedire. `filter(Boolean)` e non un template: una voce senza le due
  // chiavi scriverebbe «undefined», e una classe senza avvertenze -- la
  // maggioranza -- lascerebbe un separatore appeso dopo la fonte.
  // Le `**` cadono: nel catalogo le note sono scritte per essere lette anche in
  // un documento, dove i doppi asterischi sono un grassetto. Dentro un <small>
  // non lo sono, e a video comparirebbero come asterischi.
  const mostraProvenienza = () => {
    const voce = (catalogoDeiMateriali ?? []).find((v) => v.classe === menuClasse.value);
    provenienza.textContent = [voce?.fonte, ...(voce?.avvertenze ?? [])]
      .filter(Boolean).join(" — ").replaceAll("**", "");
  };
  // L'aiuto del menu' sta PRIMA del menu', non dopo la fonte della classe
  // scelta: la fonte e' lunga quanto la norma che cita, e un aiuto che spiega
  // il menu' letto quindici righe sotto il menu' arriva a chi ha gia' scelto.
  gruppo.append(elemento("p", {
    className: "aiuto",
    textContent: "Solo calcestruzzi: lo step 11 dichiara il materiale del continuo solido, e"
      + " in un cemento armato è il calcestruzzo. L'acciaio si dichiara nelle sezioni delle"
      + " membrature. Scelta la classe, i tre valori restano modificabili: un calcestruzzo"
      + " esistente provato in sito ha il modulo che è stato misurato, non quello di norma."
      + " Nel nome la barra diventa un trattino basso: C25/30 → C25_30.",
  }));
  gruppo.append(rigaClasse, provenienza);

  const caselle = {};
  for (const [nome, etichetta] of [
    ["name", "nome"],
    ["young", "modulo elastico E [MPa]"],
    ["poisson", "coefficiente di Poisson"],
    ["density", "densità [t/mm³]"],
  ]) {
    const riga = document.createElement("label");
    riga.className = "campo";
    riga.append(elemento("span", { textContent: etichetta }));
    const casella = document.createElement("input");
    casella.value = dichiarato ? String(dichiarato[nome]) : "";
    riga.append(casella);
    caselle[nome] = casella;
    gruppo.append(riga);
  }
  menuClasse.addEventListener("change", () => {
    // Prima della guardia sotto: tornare sulla voce vuota lascia le caselle
    // com'erano, ma scelto non c'e' piu' niente, e la fonte di prima resterebbe
    // affermata sopra valori che nessuno ha piu' dichiarato di aver preso di
    // li'.
    mostraProvenienza();
    const scelto = valoriDellaClasse(catalogoDeiMateriali ?? [], menuClasse.value);
    // Voce vuota o classe sconosciuta: le caselle restano come sono. Non si
    // svuotano, perche' chi torna sulla voce vuota dopo aver scelto non sta
    // chiedendo di buttare via cio' che aveva scritto.
    if (scelto === null) return;
    for (const nome of ["name", "young", "poisson", "density"]) {
      caselle[nome].value = scelto[nome];
    }
  });
  // Le voci arrivano dopo che il pannello e' gia' a video: il menu' nasce con
  // la sola voce vuota e si riempie quando la tratta risponde. `superata`
  // prima di scrivere, come ovunque qui: fra la richiesta e la risposta
  // l'utente puo' aver aperto un altro step, e questo menu' non e' piu' nel
  // documento.
  catalogoMateriali().then((voci) => {
    if (superata(ordine)) return;
    // Catalogo muto e catalogo che sta arrivando si somigliavano: la sola voce
    // vuota, che invita a scegliere in un menu' dove non c'e' niente da
    // scegliere. Detto qui, chi legge sa che le quattro caselle restano l'unica
    // strada e non aspetta un elenco che non arrivera'.
    if (voci.length === 0) {
      voceVuota.textContent = "catalogo non disponibile: batti i quattro valori";
      return;
    }
    for (const voce of voci) {
      menuClasse.append(elemento("option", { value: voce.classe, textContent: voce.classe }));
    }
    // La classe gia' dichiarata si rilegge dal nome, che e' dove il menu'
    // l'aveva scritta: riaprendo il pannello il menu' mostra quella scelta
    // invece di ripartire da «scegli una classe», che direbbe il falso. Il
    // confronto passa per `nomeDellaClasse`, la stessa trasformazione che ha
    // scritto quel nome: senza, non riconoscerebbe nessuna classe del catalogo.
    const gia = dichiarato && voci.find((voce) => nomeDellaClasse(voce.classe) === dichiarato.name);
    if (gia) {
      menuClasse.value = gia.classe;
      mostraProvenienza();
    }
  });

  const bottone = document.createElement("button");
  bottone.type = "button";
  bottone.className = "bottone";
  bottone.textContent = dichiarato ? "Aggiorna il materiale" : "Dichiara il materiale";
  // Il rifiuto sta qui sotto e non in cima al pannello.
  //
  // `dichiaraErrore` scrive in `#errore`, che sta in testa all'aside e fuori da
  // `#dettaglio`: fra il bottone e quella regione ci sono il titolo, le azioni,
  // la durata, i fieldset dei blocchi e il riquadro intero. La colonna scorre e
  // la regione non e' sticky, quindi comparire non sposta niente sotto gli
  // occhi di chi ha appena premuto -- un utente ci ha perso mezza giornata su
  // un rifiuto che c'era e non si vedeva. Le righe dei parametri, in questo
  // stesso pannello, non hanno mai avuto il problema: hanno il proprio slot
  // accanto al comando. Il materiale prende lo stesso, con gli stessi tre
  // canali di `segnalaCampo`.
  const messaggio = document.createElement("small");
  messaggio.className = "errore-campo";
  messaggio.id = "errore-materiale";
  messaggio.hidden = true;
  bottone.addEventListener("click", async () => {
    bottone.disabled = true;
    segnalaCampo(bottone, messaggio, null);
    const nuova = {
      ...configurazione,
      analysis: {
        ...(configurazione.analysis ?? {}),
        material: {
          name: caselle.name.value.trim(),
          young: valoreScritto(caselle.young.value),
          poisson: valoreScritto(caselle.poisson.value),
          density: valoreScritto(caselle.density.value),
        },
      },
    };
    const risposta = await fetch("/api/config", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(nuova),
    }).catch(serverMuto);
    const rifiuto = risposta.ok ? null : await ragioneDelRifiuto(risposta);
    const salvata = risposta.ok ? await corpoLetto(risposta) : null;
    // Dopo l'ultima attesa e prima della prima scrittura, come scriviParametro:
    // `configurazione` e' di modulo e la riapre ogni pannello.
    if (superata(ordine)) return;
    if (rifiuto !== null) {
      segnalaCampo(bottone, messaggio, rifiuto);
      bottone.disabled = false;
      return;
    }
    if (salvata == null || salvata.analysis == null) {
      // La PUT e' passata (risposta.ok): il materiale e' gia' sul disco, e
      // dirlo salvato sarebbe vero. Quello che non si puo' fare e' cachear in
      // `configurazione` un corpo che non descrive cio' che si e' scritto.
      segnalaCampo(
        bottone,
        messaggio,
        "il materiale è stato scritto, ma il server ha risposto con una configurazione che non si legge",
      );
      bottone.disabled = false;
      return;
    }
    configurazione = salvata;
    // La riuscita si vede, e non solo la prima volta.
    //
    // La prima dichiarazione cambiava due cose a video -- il bottone da
    // «Dichiara» ad «Aggiorna», l'aiuto da «Non dichiarato» a «Dichiarato da
    // chi analizza» -- e ogni scrittura successiva non cambiava niente:
    // stesso bottone, stesso aiuto, stesse caselle. L'assenza d'errore non e'
    // una conferma. E' la stessa riga d'esito che il Ritaglio tiene accanto al
    // proprio bottone, e l'ora la distingue dalla scrittura di prima.
    esitoDelMateriale = "Il materiale è stato scritto nella configurazione della corsa, alle "
      + new Date().toLocaleTimeString("it") + ".";
    // Ridisegnato dalla stessa strada che lo disegna sempre: il pannello deve
    // mostrare cio' che il server ha accettato, e una seconda copia della
    // logica di disegno invecchierebbe alla prima modifica dell'altra.
    apriDettaglio(numero);
  });
  gruppo.append(bottone, messaggio);
  if (esitoScritto !== null) {
    gruppo.append(elemento("p", { className: "aiuto", textContent: esitoScritto }));
  }
  return gruppo;
}

const STEP_CON_DECK = 11;

// L'esportazione del deck: il file esce dalla cartella della corsa e arriva
// dove l'utente lo cerca.
//
// Un collegamento e non un bottone che fabbrica il file: il deck sta gia' sul
// disco, e' il server a consegnarlo con il proprio nome (Content-Disposition,
// /api/deck) ed e' il browser a scaricarlo. Passare per fetch vorrebbe dire
// tenere in memoria i 35.931.310 byte del deck di `muro` per riscriverli
// identici in un Blob.
//
// Il comando c'e' solo dove c'e' un file: un collegamento a un deck mai scritto
// porterebbe su un corpo d'errore invece che su un file. Il registro dice tutte
// e due le cose che servono -- se lo step 11 ha scritto (`artefatto`) e se
// l'impronta di allora e' ancora quella della configurazione di adesso
// (`stato`, vedi steps.run_state) -- e nessuna delle due si deduce a video.
function pannelloDeck() {
  const contenitore = document.createElement("fieldset");
  contenitore.className = "gruppo";
  contenitore.append(elemento("legend", { textContent: "Esportazione" }));
  const voce = ultimoStato.find((v) => v.numero === STEP_CON_DECK);
  if (!voce || voce.artefatto == null) {
    contenitore.append(elemento("p", {
      className: "aiuto",
      textContent: "Nessun deck da esportare: lo scrive lo step 11, che questa corsa "
        + "non ha ancora eseguito.",
    }));
    return contenitore;
  }
  // Il deck sul disco e i parametri qui sopra possono raccontare due corse
  // diverse: si consegna quello che c'e' -- e' l'unico che porti un'impronta
  // nel registro -- ma il pannello non lo puo' spacciare per il modello dei
  // valori a video. Solo quando l'impronta non coincide: un cartello che
  // comparisse sempre smetterebbe di dire qualcosa il giorno in cui e' vero.
  contenitore.append(elemento("p", {
    className: "aiuto",
    textContent: voce.stato === "non valido"
      ? "Il deck sul disco è stato scritto con parametri diversi da quelli qui sopra: "
        + "si scarica com'è, e non viene rigenerato. Riesegui lo step 11 per averlo "
        + "dei parametri correnti."
      : "Il file che lo step 11 ha scritto, così com'è sul disco: non viene ricalcolato.",
  }));
  contenitore.append(elemento("a", {
    className: "bottone",
    href: "/api/deck",
    textContent: "Scarica il deck (.inp)",
  }));
  return contenitore;
}

// Le due uscite d'errore di apriDettaglio, in un punto solo. Il pannello resta
// vuoto, quindi non c'e' nessuno step aperto: il marchio non puo' restare su
// quello di prima. Restandoci, l'unico canale che dice «stai guardando questo»
// nominava lo step 3 mentre la riga d'errore, il pannello e il viewport erano
// tutti sul 5 — lo stesso guasto contro cui il foglio motiva il marchio.
// stepAperto va con lui: e' lui a dire allo scorrere degli eventi quale
// pannello ricaricare a fine corsa, e non c'e' nessun pannello da ricaricare.
function fallisciDettaglio(dettaglio, ragione) {
  dettaglio.replaceChildren();
  dichiaraErrore(ragione);
  stepAperto = null;
  segnaStepAperto(null);
}

// Il fieldset di un blocco, con i campi rimasti al predefinito richiusi.
//
// `segment` rende undici campi e `surface` nove: molto oltre i quattro che si
// tengono in mente insieme, e senza nessun ordine dentro. Il taglio fra cio'
// che si apre e cio' che si richiude non lo decide il gusto -- e' cio' che
// QUESTA corsa ha spostato dal predefinito. Un elenco base/avanzato scritto qui
// sarebbe una classificazione che nessun dato sostiene, e i nomi dei parametri
// non ne portano una.
//
// `<details>` nativo e non un pannello richiudibile scritto a mano: porta con
// se' il gesto da tastiera, il ruolo e lo stato annunciato, e non c'e' niente
// da mantenere.
// Il nome del blocco di configurazione come si legge, non come si scrive nel
// file: «una chiave non si stampa mai, si stampa la sua etichetta» (PRODUCT.md)
// valeva gia' per i campi e per le metriche, e il titolo del gruppo la
// violava in maiuscoletto -- «DOWNSAMPLE» sopra «lato del voxel [mm]». Le
// parole sono quelle della colonna degli step, cosi' il gruppo e lo step che
// lo esegue si chiamano allo stesso modo. Un blocco che la tabella non
// conosce resta la chiave, come nomeDelloStep fa con uno step ignoto.
// Su una riga sola: il banco la estrae con `_costante`, che ne vede una.
const ETICHETTE_DEI_BLOCCHI = { input: "lettura", segment: "segmentazione", downsample: "riduzione", normals: "normali", surface: "superficie", repair: "riparazione", simplify: "semplificazione", tet: "tetraedri", analysis: "analisi", carichi: "carichi", selettori: "selettori", regioni: "regioni", wall: "prior geometrico" };

function gruppoDelBlocco(blocco, campi, ordine) {
  const gruppo = document.createElement("fieldset");
  gruppo.className = "gruppo";
  gruppo.append(elemento("legend", { textContent: ETICHETTE_DEI_BLOCCHI[blocco] ?? blocco }));
  const cambiati = [];
  const fermi = [];
  for (const [nome, campo] of Object.entries(campi)) {
    const riga = campoParametro(blocco, nome, campo, ordine);
    // Un obbligatorio resta in vista con i cambiati: nella piega finirebbe
    // sotto un titolo che dice «al valore predefinito», e un predefinito non
    // ce l'ha. E' anche il campo che di solito conta di piu' -- `input.path` e'
    // la nuvola su cui gira tutto il resto.
    const spostato = campo.obbligatorio
      || cambiatoDalPredefinito(configurazione?.[blocco]?.[nome], campo.default);
    (spostato ? cambiati : fermi).push(riga);
  }
  gruppo.append(...cambiati);
  if (fermi.length > 0) {
    const piega = document.createElement("details");
    const titolo = elemento("summary", {
      textContent: fermi.length === 1
        ? "1 parametro al valore predefinito"
        : `${fermi.length} parametri al valore predefinito`,
    });
    piega.append(titolo, ...fermi);
    // Aperta quando non c'e' nient'altro: alla prima corsa nessun parametro e'
    // stato spostato, e un pannello che mostra solo una riga da cliccare non
    // insegna niente a chi apre lo step per la prima volta.
    if (cambiati.length === 0) piega.open = true;
    gruppo.append(piega);
  }
  return gruppo;
}

// L'intestazione del pannello: quale step si sta guardando, e che cosa fa.
// Di primo livello come le altre funzioni del modulo, cosi' un banco la esegue
// senza aprire un pannello intero.
//
// Il numero E il nome, non uno dei due: il numero e' come lo step si chiama
// negli artefatti sul disco (`09_volume.vtu`) e nei messaggi del server, il
// nome e' come si chiama nella colonna a sinistra. Chi legge il pannello ha
// bisogno di tutti e due per collegare le due lingue.
//
// Uno step di cui non si conosce la chiave non prende un nome inventato: resta
// il numero, che e' l'unica cosa che si sa. Stessa regola di nomeDelloStep.
function intestazioneDelloStep(numero) {
  const voce = ultimoStato.find((v) => v.numero === numero);
  const nome = voce ? ETICHETTE[voce.chiave] : undefined;
  const titolo = elemento("h3", {
    className: "titolo-step",
    textContent: nome === undefined ? `Step ${numero}` : `Step ${numero} · ${nome}`,
  });
  const proposito = voce ? PROPOSITI[voce.chiave] : undefined;
  if (proposito === undefined) return [titolo];
  return [titolo, elemento("p", {
    className: "aiuto",
    textContent: proposito,
  })];
}

// ordine: la generazione del clic che ha chiesto questo pannello. Il
// ricaricamento dallo scorrere degli eventi non ne apre una: prende quella in
// corso, cosi' un clic dell'utente arrivato nel frattempo lo batte.
// Che cosa vuol dire lo stato che la colonna scrive accanto allo step, e che
// cosa farne. «non valido» sta nella colonna, nel registro, nella CLI e nella
// spec, e la parola non si cambia; ma a chi non conosce la pipeline suona
// come «rotto», mentre dice solo che l'artefatto sul disco viene da
// parametri diversi da quelli correnti. La frase sta nel pannello dello step
// aperto, subito prima dei due bottoni di esecuzione: e' il posto in cui si
// decide se rieseguire. Uno stato che non si conosce non prende una frase.
// La tabella sta dentro la funzione e non a livello di modulo: il banco la
// estrae con `_funzioni`, che prende la funzione intera, e una costante su
// piu' righe non la vedrebbe.
function fraseDelloStato(voce) {
  const frasi = {
    "valido": "Eseguito con i parametri correnti: l'artefatto sul disco li rispecchia.",
    "non valido": "Eseguito con parametri diversi da quelli correnti: l'artefatto sul disco "
      + "non li rispecchia. Riesegui lo step per aggiornarlo.",
    "mai eseguito": "Mai eseguito in questa corsa.",
    "fallito": "L'ultima esecuzione è fallita: il motivo è nel registro, in fondo a questa colonna.",
  };
  return frasi[voce?.stato] ?? null;
}

async function apriDettaglio(numero, ordine = generazione) {
  const dettaglio = document.getElementById("dettaglio");
  if (schemaParametri === null) {
    const risposta = await fetch("/api/schema").catch(serverMuto);
    // Solo una risposta valida entra in memoria: memorizzare un corpo
    // d'errore avvelenerebbe il pannello per tutta la vita della pagina,
    // perche' nessun click successivo ritenterebbe.
    if (!risposta.ok) {
      const ragione = await ragioneDelRifiuto(risposta);
      if (superata(ordine)) return;
      fallisciDettaglio(dettaglio, ragione);
      return;
    }
    const corpo = await corpoLetto(risposta);
    if (superata(ordine)) return;
    // Solo uno schema che si legge entra in memoria: un corpo malformato che
    // finisse in schemaParametri avvelenerebbe il pannello per tutta la vita
    // della pagina, perche' schemaParametri non e' piu' null e nessun clic
    // successivo ritenterebbe la richiesta.
    // == e non ===: lo schema non e' mai legittimamente null per intero.
    if (corpo == null) {
      fallisciDettaglio(dettaglio, "il server ha risposto con uno schema che non si legge. " + RIMEDIO);
      return;
    }
    schemaParametri = corpo;
  }
  // Come il ramo dello schema qui sopra: senza guardare risposta.ok, .json()
  // solleva un SyntaxError sul corpo d'errore e il pannello resta bianco senza
  // dire perche'.
  const rispostaConfig = await fetch("/api/config").catch(serverMuto);
  const rispostaMetriche = await fetch("/api/metrics").catch(serverMuto);
  if (!rispostaConfig.ok || !rispostaMetriche.ok) {
    const ragione = await ragioneDelRifiuto(rispostaConfig.ok ? rispostaMetriche : rispostaConfig);
    if (superata(ordine)) return;
    fallisciDettaglio(dettaglio, ragione);
    return;
  }
  const corpoConfig = await corpoLetto(rispostaConfig);
  const corpoMetriche = await corpoLetto(rispostaMetriche);
  // Dopo l'ultima attesa e prima della prima scrittura: qui sono tre andate e
  // ritorni, e in mezzo l'utente puo' aver scelto un altro step. Anche
  // stepAperto sta sotto la guardia, perche' e' lui a dire allo scorrere degli
  // eventi quale pannello ricaricare.
  if (superata(ordine)) return;
  // configurazione e' di modulo e resta quella dell'apertura precedente finche'
  // non si assegna: un corpo che non si legge non deve entrarci, altrimenti la
  // prossima PUT di scriviParametro partirebbe da una configurazione rotta.
  // == e non ===: ne' la configurazione ne' le metriche sono mai
  // legittimamente null per intero.
  if (corpoConfig == null || corpoMetriche == null) {
    fallisciDettaglio(dettaglio, "il server ha risposto con un corpo che non si legge. " + RIMEDIO);
    return;
  }
  configurazione = corpoConfig;
  const metriche = corpoMetriche;
  const voce = schemaParametri[String(numero)];
  stepAperto = numero;
  // Il marchio segue il pannello nello stesso istante: rimandarlo alla
  // prossima riscrittura dell'elenco lo farebbe comparire mezzo secondo dopo
  // il clic, e a corsa ferma resterebbe indietro finche' qualcosa non si muove.
  segnaStepAperto(numero);
  dettaglio.replaceChildren();

  // Svuotata a ogni apertura e prima di ogni tentativo: un errore gia' risolto
  // lasciato a video contraddice cio' che il pannello mostra. La riga adesso
  // vive nel markup e non viene ricreata: si svuota, non si sostituisce.
  dichiaraErrore(null);

  // In TESTA, prima dei due bottoni: il pannello si apriva su «Esegui questo
  // step» senza dire quale, e il solo canale che lo nominava era il marchio
  // nella colonna a sinistra, a 1100 px di distanza su uno schermo largo. Chi
  // guarda la terza colonna deve sapere che cosa sta per eseguire senza
  // riattraversare lo schermo.
  dettaglio.append(...intestazioneDelloStep(numero));
  const statoSuDisco = fraseDelloStato(ultimoStato.find((v) => v.numero === numero));
  if (statoSuDisco !== null) {
    dettaglio.append(elemento("p", { className: "aiuto stato-dello-step", textContent: statoSuDisco }));
  }

  const azioni = document.createElement("div");
  azioni.className = "azioni";
  // I due bottoni condividono `ordine` (la generazione del pannello) e la
  // stessa rigaErrore: due clic — sullo stesso bottone o su quello diverso —
  // condividono `ordine` senza distinguersi fra loro, la stessa famiglia di
  // Rilievo 1. Un contatore per clic, condiviso dai due bottoni perche'
  // condividono il canale d'errore che proteggono.
  let ultimaAzione = 0;
  function apriAzione() {
    ultimaAzione += 1;
    return ultimaAzione;
  }
  // Il primo dei due porta il fondo pieno: e' lo scopo del pannello, e sopra
  // sei gruppi di campi due bottoni identici non dicono da quale si comincia.
  // Uno solo, e per zona: il foglio spiega perche' la rarita' e' la forza di
  // quel colore. Dall'indice e non dall'etichetta, che e' testo da leggere.
  for (const [indice, [etichetta, percorso]] of [
    ["Esegui questo step", `/api/step/${numero}`],
    ["Esegui da qui fino al deck", `/api/step/${numero}/from`],
  ].entries()) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    // `esecuzione` e' come spegniLeEsecuzioni li trova: il pannello si
    // ricostruisce a ogni apertura, quindi non esiste un riferimento da
    // conservare -- solo una classe da interrogare quando serve.
    bottone.className = indice === 0
      ? "bottone bottone-primario esecuzione"
      : "bottone esecuzione";
    // Un pannello aperto in mezzo a una corsa nasceva coi bottoni vivi: il
    // fronte di salita che li spegne e' gia' passato, e questa apertura non lo
    // sa. Si chiede allo stesso stato che lo scorrere degli eventi tiene.
    bottone.disabled = corsaInCorso;
    bottone.textContent = etichetta;
    bottone.addEventListener("click", async () => {
      dichiaraErrore(null);
      const azione = apriAzione();
      const risposta = await fetch(percorso, { method: "POST" }).catch(serverMuto);
      if (risposta.ok) return;
      const ragione = await ragioneDelRifiuto(risposta);
      // rigaErrore e' quella del pannello aperto adesso: se nel frattempo ne e'
      // stato aperto un altro, o e' partito un secondo clic su uno dei due
      // bottoni, questo rifiuto finirebbe scritto sotto lo step o il clic
      // sbagliato.
      if (superata(ordine) || superata(azione, ultimaAzione)) return;
      // Un click rifiutato in silenzio non e' distinguibile da uno andato a
      // buon fine: il server ha gia' scritto il perche', e va mostrato.
      dichiaraErrore(ragione);
    });
    azioni.append(bottone);
  }
  dettaglio.append(azioni);

  // Quanto costa il bottone qui sopra, detto prima di premerlo. E' la stessa
  // misura che la riga dell'attesa mostra mentre lo step gira, letta nel
  // momento in cui serve per decidere: lo step 7 dura 33 secondi sulla
  // scansione di riferimento, e finora l'unico modo di saperlo era averlo gia'
  // aspettato una volta. Vale doppio per l'utente successivo confermato, che
  // gli undici step non li ha mai visti girare.
  //
  // Da `ultimoStato`, che e' lo stato piu' recente arrivato dal flusso. Vuoto
  // finche' la prima risposta non e' tornata: in quel caso la riga non c'e', e
  // una riga assente e' l'unica alternativa onesta a un numero che non si ha.
  const misurato = ultimaDurata(ultimoStato.find((v) => v.numero === numero));
  if (misurato !== null) {
    dettaglio.append(elemento("p", {
      className: "aiuto",
      textContent: `L'ultima esecuzione di questo step è durata ${misurato}.`,
    }));
  }

  for (const blocco of voce.blocchi) {
    dettaglio.append(gruppoDelBlocco(blocco, voce.campi[blocco], ordine));
  }

  // Presa qui, prima dei pannelli sotto: la sezione Metriche piu' sotto la
  // legge, e cercarla due volte direbbe che sono due chiavi diverse.
  const chiave = Object.keys(metriche).find((k) => k.startsWith(String(numero).padStart(2, "0")));

  // Dentro dettaglio, che replaceChildren() svuota a ogni apertura: cosi' il
  // pannello non puo' sopravvivere a uno step che non e' il suo.
  // Dallo schema e non da un numero scritto qui: gli step che pretendono il
  // materiale sono quelli che dichiarano il blocco `analysis` in
  // steps.STEP_BLOCKS, e un elenco a mano resterebbe indietro al primo step
  // nuovo che lo legge.
  if (voce.blocchi.includes("analysis")) dettaglio.append(pannelloMateriale(numero, ordine));
  if (numero === STEP_CON_RITAGLIO) dettaglio.append(pannelloRitaglio(ordine));
  if (numero === STEP_CON_DECK) dettaglio.append(pannelloDeck());
  if (numero === STEP_CON_SCARTO) dettaglio.append(pannelloScarto(ordine));

  if (chiave) {
    const titolo = document.createElement("h3");
    titolo.textContent = "Metriche";
    const tabella = document.createElement("dl");
    tabella.className = "metriche";
    // Costruite tutte, poi marcate: il confronto col giro precedente vuole i
    // nomi gia' appiattiti, e righeDellaMetrica li appiattisce solo tornando.
    tabella.append(...marcaLeMetricheCambiate(
      numero,
      Object.entries(metriche[chiave]).flatMap(
        ([nome, valore]) => righeDellaMetrica(nome, valore, ETICHETTE_METRICHE[chiave]),
      ),
    ));
    dettaglio.append(titolo, tabella);
  }

  // Lo step 7 non ha parametri propri: senza metriche il pannello resterebbe
  // i soli bottoni, e un riquadro vuoto non distingue "niente da mostrare" da
  // "non ha caricato".
  if (voce.blocchi.length === 0 && !chiave) {
    dettaglio.append(elemento("p", {
      className: "vuoto",
      textContent: "Questo step non ha parametri propri e non ha ancora prodotto metriche.",
    }));
  }
}

// Una metrica annidata diventa una riga per foglia, non una riga di JSON.
//
// E' il collaudo dello step 7 a pagarne il prezzo piu' alto: `geometric_error`
// e' annidato DUE livelli (`cloud_to_mesh` -> `mean`, `max`, ...), quindi lo
// scarto fra la superficie ricostruita e la nuvola da cui e' nata -- il numero
// per cui quello step esiste -- finiva a video dentro una graffa. Anche
// `aspect_ratio` (step 7) e la distribuzione dello step 10 sono annidati.
//
// Ricorsiva perche' i due livelli sono misurati, non ipotizzati: appiattirne
// uno solo lascerebbe `geometric_error . cloud_to_mesh` ancora in JSON.
//
// Le liste invece restano in JSON, e la guardia che le tiene chiuse e'
// portante: le metriche di liste ne hanno eccome -- misurate su
// runs/lab_crop/metrics.json, otto, fra cui `01_load.extent` (tre numeri),
// `06_repair.hole_areas` (sei) e `11_export.transform`, che e' una matrice
// quattro per quattro. Aperte darebbero una riga per elemento, e per la
// matrice una riga per riga di matrice: rumore al posto di una misura.
//
// I numeri passano da toLocaleString come i conteggi sotto la vista: senza,
// sullo stesso schermo convivevano `19.314 triangoli` e
// `4.442869663238525`. Sei cifre significative perche' sedici non si leggono e
// non aggiungono niente -- metrics.json conserva la precisione piena, ed e' da
// li' che si citano i numeri, non dallo schermo.
// Oltre questa lunghezza un valore non entra nella colonna del numero e passa
// sotto la propria etichetta, a tutta larghezza (vedi .metrica-larga nel
// foglio). 14 e' la larghezza dichiarata di quella colonna, non un numero
// scelto: sopra, il valore si spezzerebbe comunque.
// La classe sta in una costante perche' la cerca il banco: scritta a mano in
// due file, il nome puo' divergere e il foglio smette di vestire cio' che il
// modulo scrive, senza che niente diventi rosso.
const VALORE_LARGO = 14;
const CLASSE_VALORE_LARGO = "metrica-larga";

function righeDellaMetrica(nome, valore, etichette) {
  const annidata = valore !== null && typeof valore === "object" && !Array.isArray(valore);
  // Un dizionario vuoto non lascia righe: «{}» a video non e' una misura.
  if (annidata) {
    return Object.entries(valore).flatMap(
      ([interno, dentro]) => righeDellaMetrica(`${nome} · ${interno}`, dentro, etichette),
    );
  }
  const testo = valoreDellaMetrica(valore);
  const dd = elemento("dd", { textContent: testo });
  if (testo.length > VALORE_LARGO) dd.className = CLASSE_VALORE_LARGO;
  // Il controllo che contraddice: un vero su una chiave d'allarme e' la «mesh
  // troncata in silenzio» del primo principio di prodotto, e non sta fra
  // tredici righe uguali. `classList` e non `className`: la classe del valore
  // largo la scrive la riga qui sopra, e sostituirla la perderebbe.
  if (METRICHE_D_ALLARME.has(nome) && valore === true) {
    dd.classList.add("metrica-avviso");
  }
  // Il percorso appiattito e' la chiave: si cerca alla FOGLIA e non famiglia per
  // famiglia, perche' `aspect_ratio · mean` dello step 7 conta i triangoli e
  // quello del 10 i tetraedri, e un'etichetta di famiglia varrebbe per
  // entrambi. Senza etichetta si stampa la chiave: e' la stessa regola di
  // `nomeDelloStep`, che su una chiave sconosciuta ripiega invece di
  // fabbricare un nome.
  return [elemento("dt", { textContent: etichette?.[nome] ?? nome }), dd];
}

// Quali numeri il pannello mostrava l'ultima volta, e per quale step.
//
// Fuori dal pannello perche' il pannello non sopravvive: apriDettaglio lo
// svuota con replaceChildren a ogni apertura, e cio' che deve durare piu' di
// una passata non puo' stare dentro cio' che quella passata distrugge.
let metricheMostrate = { numero: null, valori: new Map() };

// Il marchio del cambio sui numeri, gemello di quello sulle righe della colonna
// e per lo stesso motivo: quando una corsa finisce, il pannello dello step
// aperto si riscrive da se' -- nessuno lo ha chiesto in quel momento -- e un
// valore sostituito in silenzio e' indistinguibile da quello di prima.
//
// Tre condizioni, e tolta una qualsiasi il marchio dichiara un evento che non
// e' successo:
//
//   - lo stesso step. Aprendone un altro a cambiare e' il soggetto, non la
//     misura: accendere tutto direbbe che sono cambiati numeri che sono solo
//     stati guardati per la prima volta.
//   - un valore gia' visto. Una metrica che compare adesso -- lo step che gira
//     la prima volta -- non e' cambiata, e' nata.
//   - un valore diverso. Riaprire lo stesso pannello due volte non cambia
//     niente, e riaprirlo e' cio' che si fa piu' spesso.
//
// Nessuna coda da pulire: le righe marcate le butta via il replaceChildren
// dell'apertura seguente, ed e' il rinascere del `dd` a far ripartire
// l'animazione la volta dopo.
function marcaLeMetricheCambiate(numero, righe) {
  const valori = new Map();
  // A coppie perche' righeDellaMetrica torna [dt, dd] appiattite: l'etichetta
  // e' la chiave, e per una metrica annidata porta gia' dentro il percorso.
  for (let i = 0; i + 1 < righe.length; i += 2) {
    const nome = righe[i].textContent;
    const dd = righe[i + 1];
    const prima = numero === metricheMostrate.numero ? metricheMostrate.valori.get(nome) : undefined;
    if (prima !== undefined && prima !== dd.textContent) dd.dataset.cambiato = "";
    valori.set(nome, dd.textContent);
  }
  metricheMostrate = { numero, valori };
  return righe;
}

// Solo qui dentro l'`Array.isArray`: dopo la guardia di `annidata`, `typeof
// valore === "object"` e' vero per le sole liste e per null -- e `String(null)`
// e `JSON.stringify(null)` danno la stessa cosa. Nominare le liste dice cosa si
// intende; il typeof lasciava credere che coprisse anche i dizionari.
function valoreDellaMetrica(valore) {
  if (Array.isArray(valore)) return JSON.stringify(valore);
  // `String(true)` dava «true» in un'interfaccia dichiarata italiana, accanto a
  // etichette italiane. Prima dei numeri perche' in JavaScript un booleano non
  // e' un numero ma ci somiglia in troppi controlli scritti in fretta.
  if (typeof valore === "boolean") return valore ? "sì" : "no";
  if (typeof valore !== "number") return String(valore);
  // Gli interi NON si arrotondano: sono conteggi, e un conteggio arrotondato e'
  // un conteggio sbagliato. Misurato a schermo il 24/08/2026 sulla corsa
  // lab_crop: con le sole sei cifre significative `points_read` usciva
  // 6.329.100 mentre il valore e' 6.329.096 -- e due centimetri sotto la vista
  // #conteggi scriveva «su 6.329.096», cioe' due numeri diversi per la stessa
  // quantita' sullo stesso schermo.
  if (Number.isInteger(valore)) return valore.toLocaleString("it");
  return valore.toLocaleString("it", { maximumSignificantDigits: 6 });
}

