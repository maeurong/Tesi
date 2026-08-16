// Orchestrazione dell'interfaccia. Ogni numero mostrato viene dal server.

const ETICHETTE = {
  "01_load": "Lettura", "02_segment": "Segmentazione", "03_downsample": "Riduzione",
  "04_normals": "Normali", "05_reconstruct": "Superficie", "06_repair": "Riparazione",
  "07_surface_quality": "Qualità superficie", "08_simplify": "Semplificazione",
  "09_tetrahedralize": "Tetraedri", "10_volume_quality": "Qualità volume",
  "11_export": "Esportazione",
};

// Che cosa fa uno step, in una riga. L'utente successivo dichiarato in
// PRODUCT.md non conosce gli undici step, e la colonna di sinistra gli mostra
// undici sostantivi soli: «Normali» non dice a nessuno che cosa stia per
// succedere al proprio dato. Chi la pipeline la conosce a memoria non viene
// rallentato — e' una riga sotto il titolo del pannello, non un passaggio in
// piu' da fare.
const PROPOSITI = {
  "01_load": "Legge la nuvola dal file, la porta in millimetri e ne misura ingombro e spaziatura.",
  "02_segment": "Tiene i soli punti dell'oggetto: toglie il rumore e ritaglia via il resto della stanza.",
  "03_downsample": "Dirada i punti a passo costante: meno punti, stessa forma, calcolo più leggero.",
  "04_normals": "Stima in ogni punto da che parte guarda la superficie: serve alla ricostruzione.",
  "05_reconstruct": "Costruisce dai punti una superficie fatta di triangoli.",
  "06_repair": "Chiude i buchi, toglie i pezzi staccati e rigira le facce finché la superficie racchiude un volume.",
  "07_surface_quality": "Misura la superficie: se è chiusa, quanto sono regolari i triangoli, quanto si scosta dalla nuvola di partenza.",
  "08_simplify": "Rifà o dirada i triangoli. È opzionale: senza «enabled» la superficie passa avanti com'è.",
  "09_tetrahedralize": "Riempie il volume di tetraedri: è il maglio su cui si calcola.",
  "10_volume_quality": "Misura il maglio: elementi rovesciati, volumi, angoli, allungamento.",
  "11_export": "Scrive il file .inp per Abaqus o CalculiX, con materiale, gravità e set di nodi.",
};

// Il nome leggibile di uno step. La colonna di sinistra mostra i nomi, e la
// riga di stato diceva «step 9»: due lingue per la stessa cosa, e la traduzione
// a carico di chi guarda. La chiave sta in ogni voce di run_state, quindi il
// nome non va indovinato dall'ordine.
function nomeDelloStep(numero, steps = []) {
  const voce = steps.find((v) => v.numero === numero);
  const etichetta = voce ? ETICHETTE[voce.chiave] : undefined;
  return etichetta ?? `step ${numero}`;
}

// Che cosa dire quando una corsa finisce. Pura e di primo livello come
// superata() e valoreScritto(): e' la decisione che l'interfaccia non prendeva
// affatto, e presa dentro un gestore anonimo non la esegue nessun banco.
// I tre esiti sono distinti perche' sono tre fatti diversi, ed e' la voce del
// progetto: un annullamento e' una scelta di chi guarda, non un guasto.
// L'ordine dei rami conta: un annullamento arriva con un codice d'uscita non
// nullo (il segnale che lo ha fermato), quindi va guardato per primo, altrimenti
// ogni annullamento si annuncerebbe come un fallimento.
function esitoDellaCorsa(stato) {
  const nome = nomeDelloStep(stato.step, stato.steps ?? []);
  if (stato.annullato) return { errore: null, esito: `${nome} annullato` };
  // Una corsa finita senza codice d'uscita non e' piu' uno stato possibile: il
  // worker fissa exit_code prima di dichiararsi fermo, quindi in_corso: false
  // implica un codice gia' scritto. Se arriva lo stesso — una start() che
  // solleva prima di avere un figlio, un frame caduto dentro il fork — si tace.
  // Dirlo «concluso» annuncerebbe riuscita una corsa mai partita, che e' il
  // falso successo per cui esiste tutto questo ramo.
  if (stato.exit_code === null || stato.exit_code === undefined) {
    return { errore: null, esito: null };
  }
  if (stato.exit_code !== 0) {
    return {
      errore: `${nome} è fallito (codice ${stato.exit_code}). ` +
        "Il motivo è nelle ultime righe del registro, qui sotto.",
      esito: null,
    };
  }
  // La durata la misura il server e la scrive nel file di stato: run_state la
  // rilegge da li'. Quando manca non si mette uno zero ne' un trattino formattato
  // come un numero — sarebbe una misura fabbricata — si dice solo che e' finito.
  const voce = (stato.steps ?? []).find((v) => v.numero === stato.step);
  const secondi = voce ? voce.secondi : undefined;
  if (typeof secondi !== "number") return { errore: null, esito: `${nome} concluso` };
  const misura = secondi.toLocaleString("it", { maximumFractionDigits: 2 });
  return { errore: null, esito: `${nome} concluso in ${misura} s` };
}

// Dove finisce l'esito di una corsa: una regione sola per tutti e tre gli
// esiti, #esito, che sta nella testata. Il fallimento andava in #errore, che
// vive nella colonna del dettaglio, e apriDettaglio la svuota a ogni apertura:
// l'annuncio spariva il tempo di due fetch dopo essere comparso, e cio' che
// restava a video era indistinguibile da una corsa riuscita. Due meccanismi si
// contendevano la stessa riga; adesso l'esito ne ha una sua, dove nessun
// ricaricamento di pannello passa.
// La classe accanto al testo e non al posto del testo: il fallimento si legge
// per esteso comunque, e chi non distingue le tinte non perde niente (WCAG
// 1.4.1). La classe aggiunge il peso visivo, non l'informazione.
function mostraEsito(errore, esito) {
  const riga = document.getElementById("esito");
  riga.textContent = errore ?? esito ?? "";
  riga.classList.toggle("esito-fallito", errore !== null && errore !== undefined);
}

// L'ultimo elenco di step arrivato dal server. Serve ai nomi: la didascalia
// d'attesa nomina lo step che sta caricando, e il nome sta nella chiave che
// run_state porta in ogni voce.
let ultimiSteps = [];

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
  if (corpo == null || !Array.isArray(corpo.steps)) {
    dichiaraErrore(
      "il server ha risposto con uno stato della corsa che non si legge. " +
        "Ricarica la pagina; se il messaggio torna, riavvia «meshrec serve» dal terminale.",
    );
    return;
  }
  // Con l'etichetta: nudo era un percorso solo, sotto il nome del programma, e
  // niente diceva che quella cartella e' la corsa su cui l'interfaccia lavora
  // ne' che gli artefatti finiscono li'.
  document.getElementById("corsa").textContent = `corsa: ${corpo.out_dir}`;
  disegnaStep(corpo.steps);
}

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
  const nome = document.createElement("span");
  nome.className = "step-nome";
  const stato = document.createElement("span");
  stato.className = "step-stato";
  comando.append(nome, stato);
  riga.append(comando);
  return riga;
}

function disegnaStep(steps) {
  ultimiSteps = steps;
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
  if (elenco.childElementCount !== steps.length) {
    elenco.replaceChildren(...steps.map(() => nuovaRiga()));
  }
  steps.forEach((voce, indice) => {
    const comando = elenco.children[indice].firstElementChild;
    elenco.children[indice].className = `stato-${voce.stato.replace(" ", "-")}`;
    comando.dataset.numero = voce.numero;
    comando.firstElementChild.textContent = ETICHETTE[voce.chiave] ?? voce.chiave;
    comando.lastElementChild.textContent = voce.stato;
  });
  // stepAperto e' gia' inizializzato: disegnaStep gira solo da caricaStato, che
  // si sospende sulla prima attesa, e dallo scorrere degli eventi, cioe' sempre
  // dopo che il modulo e' stato valutato per intero.
  segnaStepAperto(stepAperto);
}

caricaStato();

// Il progresso non e' una percentuale: le librerie di calcolo non ne
// forniscono una, e una barra fabbricata sarebbe un numero plausibile che
// nessuna misura smentisce. Si mostra quale step gira, da quanto, e le righe
// che scrive.
// Il tempo trascorso lo misura il server, dove lo step parte davvero: contato
// qui conterebbe da quando questa pagina ha visto lo stato "in corso", e
// tornerebbe a zero a ogni ricarica mentre il calcolo prosegue.
const flusso = new EventSource("/api/events");

let eraInCorso = false;

// Che cosa succede quando arriva un frame di stato. Di primo livello e non una
// freccia dentro addEventListener, per la stessa ragione di esitoDellaCorsa:
// dentro la freccia non lo esegue nessun banco. La decisione su come finisce
// una corsa era gia' stata portata a tiro dei test; il *cablaggio* — quale
// regione riceve il testo e chi la svuota subito dopo — era rimasto qui dentro,
// ed e' li' che il difetto peggiore del giro e' sopravvissuto a otto revisioni.
function aggiornaDaStato(stato) {
  disegnaStep(stato.steps);
  const barra = document.getElementById("in-corso");
  if (stato.in_corso && stato.da_secondi !== null) {
    // Il nome e non il numero: la colonna di sinistra mostra i nomi, e questa
    // riga diceva «step 9». Sono le due lingue per la stessa cosa che
    // nomeDelloStep esiste per togliere, e la riga di stato era rimasta indietro.
    barra.textContent =
      `${nomeDelloStep(stato.step, stato.steps)} in corso, ${Math.round(stato.da_secondi)} s`;
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
  // I due «Esegui» seguono la stessa corsa, dallo stesso carico: vivi durante
  // una corsa altrui si affiderebbero al 400 del worker per dire di no.
  corsaInCorso = stato.in_corso;
  spegniLeEsecuzioni(stato.in_corso);
  // Solo sul fronte di discesa: la colonna degli step si aggiorna da questo
  // stesso flusso, e senza questa riga uno step diventerebbe "valido" a
  // sinistra mentre a destra restano le metriche di prima, o nessuna. Non a
  // ogni evento, perche' lo stato arriva ogni mezzo secondo e il pannello si
  // riscriverebbe sotto le dita di chi sta compilando un campo.
  // Sul fronte di salita si pulisce: l'esito della corsa precedente, lasciato
  // li', descriverebbe un lavoro diverso da quello che sta girando adesso.
  // L'errore va con l'esito, per la stessa ragione: lasciato a video per
  // tutta la corsa nuova, non solo per l'istante del cambio di stato.
  if (!eraInCorso && stato.in_corso) {
    mostraEsito(null, null);
    dichiaraErrore(null);
  }
  if (eraInCorso && !stato.in_corso) {
    const { errore, esito } = esitoDellaCorsa(stato);
    // Tutti e tre gli esiti vanno in #esito, fallimento compreso, e #errore si
    // svuota. Il fallimento scritto in #errore non sopravviveva alla riga qui
    // sotto: apriDettaglio svuota quella regione dopo le proprie attese, e
    // stepAperto !== null e' lo stato normale perche' il bottone Esegui sta
    // dentro il pannello che si riapre. Un errore di prima lasciato a video
    // contraddirebbe comunque la corsa appena conclusa, quindi si svuota anche
    // quando la corsa e' andata bene.
    dichiaraErrore(null);
    mostraEsito(errore, esito);
    if (stepAperto !== null) apriDettaglio(stepAperto);
    // La vista quanto il pannello: senza questa riga lo step rieseguito mostra
    // a destra le metriche nuove e nel viewport il contorno vecchio, col
    // cursore del taglio tarato su un ingombro che non esiste piu'.
    // Una corsa partita dallo step N riscrive gli artefatti dall'N in giu',
    // quindi solo un numero >= N puo' essere scaduto: sotto non c'e' niente da
    // ricaricare, e ogni ricaricamento e' una richiesta in piu'.
    if (stepMostrato !== null && stato.step !== null && stepMostrato >= stato.step) {
      ricaricaVista(stepMostrato);
    }
  }
  eraInCorso = stato.in_corso;
}

flusso.addEventListener("stato", (evento) => aggiornaDaStato(JSON.parse(evento.data)));

// Quante righe restano nel registro. E' una finestra di lettura, non una
// misura: chi vuole tutto lo stdout ha il file della corsa su disco.
const RIGHE_DEL_REGISTRO = 500;

flusso.addEventListener("riga", (evento) => {
  const registro = document.getElementById("registro");
  // Letto PRIMA di appendere: dopo, scrollHeight e' gia' cresciuto e la
  // risposta e' sempre «no».
  // La soglia di due unita' assorbe l'arrotondamento subpixel che i browser
  // fanno su un contenitore che scorre: senza, «in fondo» risulterebbe falso
  // per una frazione di pixel e il registro non seguirebbe mai la coda.
  const inFondo =
    registro.scrollTop + registro.clientHeight >= registro.scrollHeight - 2;
  const riga = document.createElement("div");
  riga.className = "riga-log";
  riga.textContent = JSON.parse(evento.data);
  registro.append(riga);
  // Il registro cresceva senza tetto: una corsa lunga lascia nel DOM ogni riga
  // che il sottoprocesso ha scritto, e nessuna veniva mai tolta. Il tetto e'
  // sulle righe e non sui caratteri perche' e' cio' che si conta guardando, e
  // le piu' vecchie escono dalla testa, che e' il verso in cui si legge un log.
  while (registro.childElementCount > RIGHE_DEL_REGISTRO) registro.firstElementChild.remove();
  // Solo per chi ci era gia'. Incondizionato, riportava in fondo due volte al
  // secondo per i 34 secondi di uno step: la riga che si stava leggendo veniva
  // strappata via a meta'.
  if (inFondo) registro.scrollTop = registro.scrollHeight;
});

// Con un nome, non inline: cosi' il test che sorveglia la regola dell'ordine
// la vede e la puo' escludere per iscritto invece di non incontrarla mai.
// Nessuna scrittura dopo l'attesa — lo stato torna dallo scorrere degli
// eventi — quindi non c'e' nulla che una generazione superata contraddica.
async function annullaLaCorsa() {
  await fetch("/api/cancel", { method: "POST" });
}

document.getElementById("annulla").addEventListener("click", annullaLaCorsa);

import { creaViewport } from "/ui/viewport.js";

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
  return ultimaGeometria;
}

// Prima dell'attesa, non dopo. La lettura di un artefatto costa 27-34 secondi a
// freddo sulla scansione vera, e in quella finestra la tela mostrava la
// geometria dello step precedente, i conteggi i suoi numeri, e il pannello con
// aria-current gia' il nuovo: lo schermo affermava che i parametri di uno step
// vanno con la mesh di un altro. E' la stessa «vista che contraddice la sua
// didascalia» contro cui esistono le due generazioni, vista dall'altro capo: le
// generazioni difendono dalle scritture vecchie, questa dalle letture vecchie
// ancora a video.
// Nessuna percentuale: le librerie non ne danno una. Si dice che cosa si sta
// leggendo, che e' un fatto e non una stima.
function dichiaraCaricamento(numero) {
  vista.svuota();
  document.getElementById("conteggi").textContent =
    `caricamento di ${nomeDelloStep(numero, ultimiSteps)}...`;
  document.getElementById("viewport").setAttribute("aria-busy", "true");
}

// Chiude cio' che dichiaraCaricamento ha aperto. Una superficie sola e non
// tante copie letterali della stessa riga: una superficie sola e' anche
// l'unica che un test puo' sorvegliare per tutti i punti che la chiamano.
function chiudiCaricamento() {
  document.getElementById("viewport").removeAttribute("aria-busy");
}

// Il corpo binario di una risposta ok, letto senza lasciare uscire un rigetto
// a meta' del download: stesso principio di corpoLetto per il JSON, qui
// duplicato apposta per non far dipendere le due tratte binarie da quella che
// legge testo. undefined marca "il download non e' arrivato" — un
// ArrayBuffer vuoto (byteLength 0) e' un dato legittimo, non un errore, e
// confonderli con undefined tratterebbe una mesh vuota come un guasto di
// rete. Usata da entrambe le tratte binarie: cosi' un rigetto a meta' del
// download si racconta nello stesso modo su nuvola e mesh, senza due try/catch
// copiati che potrebbero divergere.
async function corpoBinarioLetto(risposta) {
  try {
    return await risposta.arrayBuffer();
  } catch {
    return undefined;
  }
}

// Il testo di un artefatto che non e' arrivato. status 0 e' la firma di
// serverMuto (vedi sopra): un server che non ha risposto — alla fetch
// iniziale o a meta' del download, che e' lo stesso fatto letto piu' tardi —
// non e' lo stesso fatto di un server che ha risposto "questo step non ha
// ancora un artefatto". Confonderli direbbe un dato negativo documentato dove
// invece il server non e' mai stato interrogato con successo. Duplicata fra
// nuvola e mesh prima di questa correzione, e con lei il rischio di
// modificarne una copia e dimenticare l'altra.
async function messaggioArtefattoMancante(risposta) {
  return risposta.status === 0
    ? await ragioneDelRifiuto(risposta)
    : "nessun artefatto per questo step: eseguilo per vederne il risultato.";
}

// Il messaggio quando il download si ferma a meta', dopo che gli header erano
// gia' arrivati: lo stesso fatto di un server muto (sopra), letto piu' tardi.
// Riusa serverMuto/messaggioArtefattoMancante invece di un testo proprio, cosi'
// la formula "il server non ha risposto: ..." resta una sola in tutto il file,
// e non due copie fra nuvola e mesh che potrebbero divergere.
function messaggioDownloadInterrotto() {
  return messaggioArtefattoMancante(serverMuto(new Error("connessione interrotta durante il download")));
}

// Sposta la vista nello stato "niente da mostrare", con un messaggio gia'
// calcolato. Sincrona apposta: il chiamante calcola il messaggio (che puo'
// aspettare ragioneDelRifiuto) e controlla la guardia dell'ordine PRIMA di
// chiamare questa funzione, cosi' una risposta scartata non arriva mai qui —
// spostare la guardia dentro sposterebbe la scrittura dopo un'altra attesa
// invece di tenerla subito dopo l'ultima, riaprendo la corsa che le
// generazioni esistono per chiudere.
function segnalaArtefattoMancante(messaggio) {
  chiudiCaricamento();
  // Svuotare e' obbligatorio: senza, la scena resta quella dello step
  // precedente mentre il testo dice che non c'e' nulla. Una vista che
  // contraddice la sua didascalia e' peggio di una vista vuota.
  vista.svuota();
  document.getElementById("conteggi").textContent = messaggio;
}

async function mostraNuvolaDelloStep(numero, ordine) {
  const emissione = apriGeometria();
  const risposta = await fetch(`/api/cloud/${numero}`).catch(serverMuto);
  if (!risposta.ok) {
    const messaggio = await messaggioArtefattoMancante(risposta);
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return true;
  }
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const grezzi = await corpoBinarioLetto(risposta);
  if (grezzi === undefined) {
    // Su una nuvola vera il download dura alcuni secondi, e la rete puo'
    // cadere in quella finestra tanto quanto prima della prima risposta.
    const messaggio = await messaggioDownloadInterrotto();
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return true;
  }
  // Il controllo sta dopo l'ultima attesa e prima della prima scrittura: piu'
  // in alto lascerebbe passare cio' che e' stato superato mentre il corpo
  // arrivava.
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  chiudiCaricamento();
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
// c'e' un solido.
const STEP_CON_MESH = new Set([5, 6, 8, 9]);

async function mostraStep(numero, ordine) {
  // In testa e sopra la delega: ogni strada passa di qui una volta sola, e
  // metterla anche dentro mostraNuvolaDelloStep la eseguirebbe due volte sugli
  // step senza mesh.
  dichiaraCaricamento(numero);
  // La delega sta prima del contatore: incrementarlo qui e di nuovo la' sotto
  // farebbe battere questa richiesta da se stessa, e nessuna nuvola verrebbe
  // piu' disegnata. Ogni strada apre esattamente una richiesta.
  if (!STEP_CON_MESH.has(numero)) return mostraNuvolaDelloStep(numero, ordine);
  const emissione = apriGeometria();
  const risposta = await fetch(`/api/mesh/${numero}`).catch(serverMuto);
  if (!risposta.ok) {
    const messaggio = await messaggioArtefattoMancante(risposta);
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return true;
  }
  const vertici = Number(risposta.headers.get("X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await corpoBinarioLetto(risposta);
  if (grezzi === undefined) {
    // Come per la nuvola: la connessione caduta a meta' del download e' lo
    // stesso fatto di un server muto, letto piu' tardi.
    const messaggio = await messaggioDownloadInterrotto();
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    segnalaArtefattoMancante(messaggio);
    return true;
  }
  // Qui la latenza e' quella vera: e' la mesh dello step 9 che arriva tardi a
  // posarsi sulla nuvola di un altro step.
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  chiudiCaricamento();
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

// Il piano di taglio serve a guardare dentro il volume, percio' il comando
// compare solo sullo step che il volume lo produce, e solo se qualcosa e'
// stato davvero disegnato.
const STEP_CON_TAGLIO = 9;
// Lo step la cui geometria e' nel viewport: non e' sempre quello del pannello,
// che resta aperto anche mentre la geometria nuova sta arrivando.
let stepMostrato = null;
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
asseTaglio.addEventListener("change", () => riallineaTaglio(stepMostrato));

document.getElementById("elenco-step").addEventListener("click", (evento) => {
  const riga = evento.target.closest(".step");
  if (!riga) return;
  const numero = Number(riga.dataset.numero);
  stepMostrato = numero;
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
  // `disegnato` e' falso quando la risposta e' stata scartata: senza guardarlo,
  // il cursore si rifarebbe sull'ingombro di una geometria che qualcun altro
  // ha disegnato, cioe' su una lettura che non appartiene a questo numero.
  mostraStep(numero, ordine).then((disegnato) => {
    if (disegnato && !superata(ordine)) riallineaTaglio(numero);
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
      messaggio:
        `il server non ha risposto: ${errore.message}. ` +
        "Controlla il terminale in cui gira «meshrec serve».",
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

// Il valore che finisce nella configurazione, dalla stringa lasciata nel campo.
// Pura e di primo livello apposta, come superata(): e' l'unico punto in cui dei
// tasti diventano un dato scritto su disco, e da fuori si puo' provare senza un
// motore di DOM.
// trim() perche' Number(" ") e' 0, non NaN: uno spazio scriveva zero in un
// campo che a video sembra vuoto. Tolto lo spazio, un campo che sembra vuoto e'
// vuoto, e vuoto vale null — che e' cio' che il campo mostra.
// Quello che non si legge come numero resta la stringa battuta e parte cosi':
// il modello la rifiuta con un 422 leggibile, che e' l'unico posto dove il tipo
// vero si conosce. Trasformarla in null qui la farebbe accettare in silenzio.
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
  contenitore.append(Object.assign(document.createElement("legend"), { textContent: "Ritaglio" }));
  const ingombro = vista.ingombro();
  // Senza geometria non c'e' nessun ingombro da leggere, e ingombro() lo dice
  // con null apposta: una scatola vuota darebbe +Infinity e -Infinity, che
  // sono valori accettabili per un campo numerico e per nient'altro.
  if (ingombro === null) {
    contenitore.append(Object.assign(document.createElement("p"), {
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
  const applica = document.createElement("button");
  applica.type = "button";
  applica.className = "bottone";
  applica.textContent = "Applica il ritaglio";
  // Quali dei sei estremi non si leggono adesso. Un insieme e non un booleano:
  // con due campi rotti, risolverne uno riaccenderebbe il bottone mentre
  // l'altro e' ancora illeggibile.
  const rifiutati = new Set();
  for (const estremo of ["min", "max"]) {
    for (const asse of [0, 1, 2]) {
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(Object.assign(document.createElement("span"), {
        textContent: `${estremo} ${"xyz"[asse]} [mm]`,
      }));
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = valori[estremo][asse].toFixed(1);
      const messaggio = document.createElement("small");
      messaggio.className = "errore-campo";
      messaggio.id = `errore-ritaglio-${estremo}-${asse}`;
      messaggio.hidden = true;
      const chiave = `${estremo}${asse}`;
      input.addEventListener("input", () => {
        const scritto = Number(input.value);
        // Number("") e' 0, non NaN: senza questa guardia svuotare il campo
        // porterebbe l'estremo all'origine e il box salterebbe li'.
        // Prima usciva in silenzio, e li' finiva: il box smetteva di muoversi
        // senza dire perche', e «Applica» mandava comunque l'ultimo array
        // valido — cioe' un ritaglio diverso da quello che i campi mostravano,
        // scritto su disco con un messaggio di successo sopra.
        // Gli stessi tre canali dei campi di parametro, con la stessa funzione:
        // bordo, testo, e aria-invalid con aria-errormessage.
        if (input.value.trim() === "" || !Number.isFinite(scritto)) {
          rifiutati.add(chiave);
          segnalaCampo(input, messaggio, "serve un numero: il box non si muove e «Applica» resta spento.");
          applica.disabled = true;
          return;
        }
        rifiutati.delete(chiave);
        segnalaCampo(input, messaggio, null);
        // Non `false` secco: gli altri cinque campi possono essere ancora rotti.
        applica.disabled = rifiutati.size > 0;
        valori[estremo][asse] = scritto;
        vista.mostraBox(valori.min, valori.max);
      });
      riga.append(input, messaggio);
      contenitore.append(riga);
    }
  }
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
      dichiaraErrore(
        "il server ha risposto con un corpo che non descrive il ritaglio applicato: " +
          "riapri lo step 2 per rileggere che cosa c'è nella configurazione della corsa.",
      );
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
          "questo metodo lo step 2 prosegue con i piani e i cluster, e non ne terrà di più.") +
      " crop_min e crop_max sono stati scritti nella configurazione della corsa.";
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
async function scriviParametro(blocco, nome, input, messaggio, ordine) {
  const chiave = `${blocco}.${nome}`;
  const battuta = apriBattuta(chiave);
  const precedente = configurazione[blocco][nome];
  configurazione[blocco][nome] = valoreScritto(input.value);
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
      "il server ha accettato la modifica ma non ne ha confermato il valore: " +
      "ricarica la pagina per rileggere che cosa c'è sul disco.");
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
  input.value = String(configurazione[blocco][nome] ?? "");
  segnalaCampo(input, messaggio, null);
}

// La riga di un parametro: etichetta, casella, aiuto e messaggio d'errore.
// Estratta dal ciclo che la costruiva perche' e' il punto in cui la casella
// nasce e in cui il gestore le viene attaccato, e da dentro un ciclo dentro una
// funzione da duecento righe non la esegue nessun banco.
// Casella di testo, e il tipo non si indovina. type="number" era stato messo
// guardando `typeof` del valore corrente, cioe' indovinando il tipo dal valore:
// i quattro campi numerici nullabili scalari erano testo finche' valevano None
// e numerici appena valevano qualcosa, e i quattordici interi ricevevano
// step="any", che il passo unitario lo toglie invece di metterlo. Ma il guasto
// vero e' un altro: Chrome sanifica cio' che non sa leggere: battuto `1e`,
// `.value` torna `""` mentre a video resta scritto `1e`, e `""` diventava null.
// La configurazione della corsa finiva su disco col parametro azzerato e sullo
// schermo non compariva niente. Il tipo lo conosce solo il modello, e
// /api/schema oggi non lo manda: finche' non lo manda, la casella lascia
// passare cio' che e' stato battuto e il rifiuto torna visibile come 422.
// Se questa corsa ha spostato il parametro da cio' che il modello scrive quando
// nessuno tocca niente. /api/schema manda il predefinito di ogni campo e
// l'interfaccia lo buttava via: in un prodotto la cui tesi e' la
// riproducibilita', «che cosa ho cambiato dallo stock» e' la prima domanda, e
// la risposta era gia' nel browser.
// Il confronto e' sul testo reso e non sui valori: il campo mostra una
// stringa, e /api/schema serializza i predefiniti con per_json — i modelli
// annidati come oggetti JSON, tutto il resto per str(), quindi un Path arriva
// gia' come testo. Confrontare i valori grezzi segnerebbe come cambiato un
// parametro che nessuno ha toccato.
//
// Come si legge un valore di configurazione, in un punto solo. Le due
// domande — «e' cambiato?» e «da che cosa?» — devono per forza rispondere
// nella stessa lingua: il confronto usava questa resa e il segno accanto al
// campo usava String(), che su un modello annidato scrive «[object Object]»
// e su una lista «1,2,4». Sono esattamente i due testi che il commento di
// campoParametro vieta per nome trentaquattro righe sopra, e comparivano al
// primo parametro che un lavoro strutturale sposta (material.young).
function reso(v) {
  if (v === null || v === undefined) return "";
  return ["string", "number", "boolean"].includes(typeof v) ? String(v) : JSON.stringify(v);
}

function cambiatoDalPredefinito(valore, predefinito) {
  return reso(valore) !== reso(predefinito);
}

// Il glossario delle metriche. La chiave resta quella di metrics.json — e'
// l'identificatore che finisce nella tesi e nei registri della Fase 2, e
// tradurla la farebbe sparire — e accanto le si mette la frase che la spiega,
// con l'unita' in cui e' misurata. Una chiave che questo elenco non nomina
// compare comunque, senza glossa: una metrica nuova del server appare da se',
// e non si inventa una spiegazione per un dato che non si conosce.
const GLOSSARIO_METRICHE = {
  points_read: "punti letti dal file",
  points_dropped: "punti scartati: avevano una coordinata non finita",
  points_kept: "punti tenuti dopo lo scarto",
  points_before: "punti in ingresso a questo step",
  points_after: "punti rimasti dopo questo step",
  scale: "fattore applicato per portare il file in mm",
  spacing: "distanza media fra un punto e il suo vicino più prossimo [mm]",
  extent: "ingombro lungo x, y, z [mm]",
  bbox_min: "spigolo inferiore dell'ingombro [mm]",
  bbox_max: "spigolo superiore dell'ingombro [mm]",
  size_check: "esito del controllo di scala contro le dimensioni attese",
  method: "metodo usato in questo step",
  outliers_removed: "punti isolati tolti come rumore",
  cropped: "se il box di ritaglio è stato applicato",
  voxel_size: "lato del cubo di riduzione [mm]",
  reduction: "frazione di punti tolti dalla riduzione: 0,97 vuol dire che ne resta il 3%",
  knn: "vicini usati per stimare le normali",
  orient_knn: "vicini usati per orientarle tutte dallo stesso lato",
  degenerate_normals: "normali di lunghezza quasi nulla: non indicano nessuna direzione",
  vertices_trimmed: "vertici tagliati via perché in zona poco densa",
  density_threshold: "densità sotto la quale i vertici sono stati tagliati",
  vertices: "vertici della superficie",
  triangles: "triangoli della superficie",
  volume_before: "volume racchiuso prima della riparazione [mm^3]: negativo vuol dire superficie rovesciata",
  volume_after: "volume racchiuso dopo la riparazione [mm^3]",
  duplicate_vertices_merged: "vertici coincidenti fusi in uno",
  degenerate_faces_removed: "triangoli di area nulla tolti",
  duplicate_faces_removed: "triangoli ripetuti tolti",
  components_before: "pezzi staccati trovati nella superficie",
  components_kept: "pezzi tenuti",
  orphan_vertices_removed: "vertici che nessun triangolo usava",
  holes_before: "buchi chiusi trovati prima della chiusura",
  hole_areas: "area di ogni buco [mm^2], dal più grande",
  open_boundary_paths: "bordi aperti che non si richiudono: non sono buchi, sono bordo non manifold",
  holes_over_threshold: "buchi oltre max_hole_area [mm^2]",
  open_paths_over_threshold: "bordi aperti oltre max_hole_area [mm^2]",
  watertight_after: "se dopo la riparazione la superficie è chiusa",
  watertight: "se la superficie è chiusa: nessun buco, nessun bordo",
  orientation_flipped: "se le facce sono state rigirate per far uscire le normali",
  boundary_edges: "spigoli lasciati sul bordo: su una superficie chiusa sono 0",
  area: "area della superficie [mm^2]",
  volume: "volume racchiuso [mm^3]",
  aspect_ratio: "allungamento degli elementi: 1 è regolare, più alto è più schiacciato",
  geometric_error: "distanza fra la nuvola sorgente e la superficie ricostruita [mm]",
  cloud_to_mesh: "da ogni punto della nuvola alla superficie [mm]",
  mesh_to_cloud: "da ogni vertice della superficie alla nuvola [mm]",
  hausdorff: "la peggiore delle due distanze qui sopra [mm]",
  enabled: "se lo step è stato eseguito",
  mode: "modo di semplificazione usato",
  triangles_before: "triangoli in ingresso",
  triangles_after: "triangoli in uscita",
  nodes: "nodi del maglio di volume",
  tets: "tetraedri del maglio di volume",
  seconds: "durata dello step [s]",
  element: "tipo di elemento scritto nel deck",
  min_ratio: "vincolo raggio-spigolo chiesto a TetGen",
  max_volume: "volume massimo chiesto per un elemento [mm^3]",
  max_steiner_points: "tetto ai punti che TetGen poteva aggiungere; -1 = nessun tetto",
  nobisect: "se a TetGen è stato vietato suddividere le facce di ingresso",
  largest_element_volume: "volume del tetraedro più grande [mm^3]",
  steiner_points: "punti che TetGen ha aggiunto per raffinare",
  steiner_saturated: "se il tetto ai punti aggiunti è stato raggiunto: la mesh sarebbe troncata",
  radius_edge_ratio_over_limit: "frazione di elementi oltre il vincolo chiesto",
  radius_edge_ratio_p99: "rapporto raggio-spigolo al 99esimo percentile: la coda peggiore",
  inverted: "tetraedri rovesciati, di volume negativo: devono essere 0",
  total_volume: "somma dei volumi degli elementi [mm^3]",
  element_volume: "volume dei singoli elementi [mm^3]",
  min_dihedral_deg: "angolo diedro minimo di ogni elemento [gradi]: vicino a 0 è una lama",
  radius_edge_ratio: "rapporto raggio-spigolo degli elementi",
  radius_edge_over_reference: "frazione di elementi oltre reference_ratio, il metro fisso del confronto",
  reference_ratio: "metro fisso con cui si conta la frazione qui sopra",
  non_finite: "valori non finiti incontrati nel calcolo",
  transform: "matrice 4x4 che allinea il modello agli assi prima dell'esportazione",
  boundary_spacing: "distanza media fra i nodi sul bordo [mm]",
  set_tolerance: "tolleranza con cui i set di faccia sono stati estratti [mm]",
  fixed_nset_coverage: "frazione della superficie d'appoggio coperta dal set vincolato",
  node_sets: "quanti nodi ha ciascun set scritto nel deck",
  mass: "massa del modello [t]: volume per densità del materiale",
  inp: "file .inp scritto, da aprire in Abaqus o CalculiX",
  vtu: "file .vtu scritto, per la visualizzazione",
};

// Le cifre di un numero mostrato. maximumFractionDigits e non un numero di
// cifre significative: significative arrotonderebbe 168.845.511 a 168.846.000,
// cioe' scriverebbe un numero che nessuna misura ha prodotto.
// Sotto il millesimo pero' le tre cifre decimali scrivono «0», e uno zero che
// vuol dire «sotto la risoluzione di questa resa» presentato come zero esatto
// e' il principio 3 del prodotto rovesciato: misurato a video sul volume
// dell'elemento piu' piccolo di lab_crop, 1,76e-06 mm^3, che compariva come
// «min 0» accanto a un massimo di 85.788. Li' comandano le cifre
// significative, che tengono la misura invece della scala.
function numeroReso(valore) {
  return valore !== 0 && Math.abs(valore) < 0.001
    ? valore.toLocaleString("it", { maximumSignificantDigits: 3 })
    : valore.toLocaleString("it", { maximumFractionDigits: 3 });
}

// Le distribuzioni di quality.py sono quattro numeri e un conteggio, e
// JSON.stringify le rendeva come {"min":0.32,"median":...}: le graffe e le
// virgolette sono la struttura del trasporto, non il dato. min a null e' il
// caso dichiarato in cui nessun valore finito esiste, e va detto invece di
// stampare «null».
function riassuntoDistribuzione(valore) {
  if (valore.min === null) return "nessun valore finito";
  const coda = valore.non_finite > 0 ? ` · non finiti: ${numeroReso(valore.non_finite)}` : "";
  return `min ${numeroReso(valore.min)} · mediana ${numeroReso(valore.median)}` +
    ` · media ${numeroReso(valore.mean)} · max ${numeroReso(valore.max)}${coda}` ;
}

// Come si legge una metrica. Pura e di primo livello come reso(): e' l'unico
// punto in cui un valore del disco diventa una frase, e da fuori si prova
// senza un motore di DOM.
// La profondita' ferma la ricorsione a due livelli, che e' quanto sono
// profonde le metriche vere: geometric_error porta due riassunti di distanza
// dentro di se', e i loro campi (RMS, n_samples) sono scalari. Piu' sotto non
// c'e' niente nel formato di oggi, e li' torna il JSON, che e' brutto ma non
// mente.
function resaMetrica(valore, profondita = 0) {
  if (valore === null || valore === undefined) return "non impostato";
  if (typeof valore === "boolean") return valore ? "sì" : "no";
  if (typeof valore === "number") return numeroReso(valore);
  if (typeof valore === "string") return valore;
  if (Array.isArray(valore)) {
    if (valore.length === 0) return "nessuno";
    return valore.every((v) => typeof v === "number")
      ? valore.map(numeroReso).join(" · ")
      : JSON.stringify(valore);
  }
  if (["min", "median", "mean", "max"].every((k) => k in valore)) {
    return riassuntoDistribuzione(valore);
  }
  if (profondita > 1) return JSON.stringify(valore);
  // Il separatore cambia col livello: dentro un gruppo il punto mediano, fra un
  // gruppo e l'altro il trattino. Con lo stesso segno a tutti e due i livelli,
  // geometric_error rendeva una riga sola di quindici voci in cui non si vedeva
  // piu' dove finisse cloud_to_mesh e cominciasse mesh_to_cloud.
  return Object.entries(valore)
    .map(([nome, dentro]) => `${nome}: ${resaMetrica(dentro, profondita + 1)}`)
    .join(profondita === 0 ? " — " : " · ");
}

function campoParametro(blocco, nome, campo, ordine) {
  const riga = document.createElement("label");
  riga.className = "campo";
  riga.append(Object.assign(document.createElement("span"), { textContent: nome }));
  const valore = configurazione[blocco][nome];
  // Una lista o un modello annidato non sono scritti in una casella di testo:
  // String() li renderebbe come "1,2,4" o "[object Object]", cioe' un testo che
  // nessuna lettura produce, e ogni modifica tornerebbe comunque rifiutata dal
  // modello.
  const scalare = valore === null || ["string", "number", "boolean"].includes(typeof valore);
  const input = document.createElement("input");
  input.value = reso(valore);
  input.title = campo.description;
  const messaggio = document.createElement("small");
  messaggio.className = "errore-campo";
  messaggio.id = `errore-${blocco}-${nome}`;
  messaggio.hidden = true;
  if (!scalare) {
    // readOnly e non disabled: disabled lo toglierebbe anche dalla navigazione
    // da tastiera e dal lettore di schermo.
    input.readOnly = true;
  } else {
    input.addEventListener("change", () => scriviParametro(blocco, nome, input, messaggio, ordine));
  }
  riga.append(input);
  const aiuto = document.createElement("small");
  aiuto.className = "aiuto";
  aiuto.textContent = scalare
    ? campo.description
    : [campo.description, "casella di sola lettura"]
        .filter(Boolean).join(" — ");
  riga.append(aiuto, messaggio);
  // Un campo obbligatorio non ha un predefinito da cui scostarsi, quindi non
  // puo' essere «cambiato»: il confronto trovava il valore vivo diverso da
  // null e ogni corsa dichiarava «cambiato — predefinito: nessuno» su
  // input.path, che e' il primo campo del primo step e che nessuno ha mai
  // spostato da niente. Dove il dato manca si dichiara che manca, e questo e'
  // il caso: manca il predefinito, non e' cambiato il valore.
  if (campo.obbligatorio) {
    const segno = document.createElement("small");
    segno.className = "aiuto";
    segno.textContent = "obbligatorio: non ha un valore predefinito";
    riga.append(segno);
  } else if (cambiatoDalPredefinito(valore, campo.default)) {
    // Due canali: la classe per chi guarda, il predefinito scritto per chi
    // legge. Il colore da solo lascerebbe fuori chi non distingue le tinte, e
    // il valore di partenza e' l'informazione vera — sapere che «e' cambiato»
    // senza sapere «da che cosa» non chiude nessuna domanda.
    riga.classList.toggle("campo-cambiato", true);
    const segno = document.createElement("small");
    segno.className = "aiuto segno-cambiato";
    const stock = campo.default === null || campo.default === undefined
      ? "nessuno"
      : reso(campo.default);
    segno.textContent = `cambiato — predefinito: ${stock}`;
    riga.append(segno);
  }
  return riga;
}

// Il fieldset di un blocco. `segment` rende undici campi, `surface` nove: molto
// oltre i quattro elementi che si tengono in mente insieme, e senza nessun
// ordine dentro.
// Il taglio fra cio' che si apre e cio' che si richiude non lo decide il gusto:
// e' cio' che questa corsa ha spostato dal predefinito. Un elenco
// base/avanzato scritto qui sarebbe una classificazione che nessun dato
// sostiene, e i nomi dei parametri non ne portano una — la stessa ragione per
// cui l'ordine dei gruppi del viewport e' diventato funzione del dato.
// <details> nativo e non un pannello richiudibile scritto a mano: porta con se'
// il proprio ruolo, la propria tastiera e il proprio stato, e nessuno dei tre
// va reimplementato.
function gruppoDelBlocco(blocco, campi, ordine) {
  const gruppo = document.createElement("fieldset");
  gruppo.className = "gruppo";
  gruppo.append(Object.assign(document.createElement("legend"), { textContent: blocco }));
  const cambiati = [];
  const fermi = [];
  for (const [nome, campo] of Object.entries(campi)) {
    const riga = campoParametro(blocco, nome, campo, ordine);
    // Un obbligatorio resta in vista con i cambiati: nella piega finirebbe
    // sotto un titolo che dice «al valore predefinito», e un predefinito non
    // ce l'ha. E' anche il campo che di solito conta di piu' — input.path e'
    // la nuvola su cui gira tutto il resto.
    const spostato =
      campo.obbligatorio || cambiatoDalPredefinito(configurazione[blocco][nome], campo.default);
    (spostato ? cambiati : fermi).push(riga);
  }
  gruppo.append(...cambiati);
  if (fermi.length > 0) {
    const piega = document.createElement("details");
    const titolo = document.createElement("summary");
    titolo.textContent = fermi.length === 1
      ? "1 parametro al valore predefinito"
      : `${fermi.length} parametri al valore predefinito`;
    piega.append(titolo, ...fermi);
    // Aperta quando non c'e' nient'altro: alla prima corsa nessun parametro e'
    // stato spostato, e un pannello che mostra solo una riga da cliccare non
    // insegna niente a chi apre lo step per la prima volta.
    if (cambiati.length === 0) piega.open = true;
    gruppo.append(piega);
  }
  return gruppo;
}

// L'intestazione del pannello: quale step si sta guardando e che cosa fa. Il
// pannello si apriva sui due bottoni d'esecuzione, senza nominare lo step: il
// solo canale che lo diceva era il marchio nella colonna a sinistra, a 1100 px
// di distanza. Di primo livello come le altre funzioni del modulo, cosi' un
// banco la esegue senza aprire un pannello intero.
// Uno step di cui non si conosce la chiave non prende un nome inventato: resta
// il numero, che e' l'unica cosa che si sa.
function intestazioneDelloStep(numero, steps = []) {
  const voce = steps.find((v) => v.numero === numero);
  const nome = voce ? ETICHETTE[voce.chiave] : undefined;
  const titolo = document.createElement("h3");
  titolo.textContent = nome === undefined ? `Step ${numero}` : `Step ${numero} · ${nome}`;
  const proposito = voce ? PROPOSITI[voce.chiave] : undefined;
  if (proposito === undefined) return [titolo];
  return [titolo, Object.assign(document.createElement("p"), {
    className: "aiuto",
    textContent: proposito,
  })];
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

// Vera mentre una corsa gira. La sa lo scorrere degli eventi, e serve ai due
// «Esegui»: un pannello aperto in mezzo a una corsa nasceva con i bottoni vivi.
let corsaInCorso = false;

// I due «Esegui» seguono la corsa come Annulla, e dallo stesso carico. Restare
// vivi e affidarsi al 400 del worker e' un rifiuto che si poteva evitare, e un
// bottone che risponde «no» non si distingue da uno che non ha fatto niente.
function spegniLeEsecuzioni(inCorso) {
  for (const bottone of document.querySelectorAll(".esecuzione")) {
    bottone.disabled = inCorso;
    // Una corsa partita altrove disarma anche la conferma: senza, un
    // "Confermi?" dimenticato su un bottone spento aspetta solo che si
    // riaccenda per sparare senza chiedere niente una seconda volta.
    if (inCorso) bottone.disarma();
  }
}

// L'ultimo step della catena. La ripetono le due etichette qui sotto, e un
// terzo posto in cui scriverlo di nuovo sarebbe un terzo punto da aggiornare
// il giorno che la catena cambia lunghezza: un solo nome, usato ovunque serve.
const ULTIMO_STEP = 11;

// I due comandi d'esecuzione del pannello. Estratti da apriDettaglio per la
// stessa ragione di campoParametro e scriviParametro: dentro una funzione di
// centocinquanta righe non li esegue nessun banco, e qui c'e' una conferma da
// provare.
function azioniDelloStep(numero, ordine) {
  const azioni = document.createElement("div");
  azioni.className = "azioni";
  // I due bottoni condividono `ordine` (la generazione del pannello) e la
  // stessa rigaErrore: due clic — sullo stesso bottone o su quello diverso —
  // condividono `ordine` senza distinguersi fra loro. Un contatore per clic,
  // condiviso dai due perche' condividono il canale d'errore che protegge.
  let ultimaAzione = 0;
  function apriAzione() {
    ultimaAzione += 1;
    return ultimaAzione;
  }
  const comandi = [
    { etichetta: "Esegui questo step", percorso: `/api/step/${numero}`, primario: true },
    {
      // La portata sta nell'etichetta: «da qui in giu'» non dice quanti step
      // riscrive, e sono tutti quelli dallo step aperto all'ultimo.
      etichetta: `Esegui dallo step ${numero} all'${ULTIMO_STEP}`,
      percorso: `/api/step/${numero}/from`,
      primario: false,
    },
  ];
  // I bottoni del gruppo, cosi' ciascuno puo' disarmare gli altri: una scelta
  // diversa e' un cambio idea, e la domanda rimasta sul primo non lo era piu'.
  const bottoni = [];
  for (const { etichetta, percorso, primario } of comandi) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = primario ? "bottone bottone-primario esecuzione" : "bottone esecuzione";
    bottone.textContent = etichetta;
    bottone.disabled = corsaInCorso;
    // Conferma in linea e non una finestra modale: la modale e' la risposta
    // pigra, e questa azione non e' distruttiva in astratto — riscrive
    // artefatti che si possono rifare — e' cara. Una seconda pressione basta a
    // separare il clic voluto da quello sbagliato di mira.
    let chiesta = false;
    // Un solo punto che riporta il bottone al riposo. Lo chiamano il clic su
    // un fratello (una scelta diversa e' un cambio idea) e spegniLeEsecuzioni
    // quando una corsa parte altrove: senza, un bottone armato restava armato
    // oltre la corsa che lo aveva reso muto, e un clic successivo — non piu'
    // distinguibile da una prima pressione — partiva senza chiedere niente,
    // proprio il difetto che la conferma esiste per chiudere.
    bottone.disarma = () => {
      chiesta = false;
      bottone.textContent = etichetta;
    };
    bottone.addEventListener("click", async () => {
      for (const altro of bottoni) if (altro !== bottone) altro.disarma();
      if (!primario && !chiesta) {
        chiesta = true;
        bottone.textContent = `Confermi? riscrive dallo step ${numero} all'${ULTIMO_STEP}`;
        return;
      }
      bottone.disarma();
      dichiaraErrore(null);
      const azione = apriAzione();
      const risposta = await fetch(percorso, { method: "POST" }).catch(serverMuto);
      if (risposta.ok) return;
      const ragione = await ragioneDelRifiuto(risposta);
      // rigaErrore e' quella del pannello aperto adesso: se nel frattempo ne e'
      // stato aperto un altro, o e' partito un secondo clic, questo rifiuto
      // finirebbe scritto sotto lo step o il clic sbagliato.
      if (superata(ordine) || superata(azione, ultimaAzione)) return;
      dichiaraErrore(ragione);
    });
    bottoni.push(bottone);
    azioni.append(bottone);
  }
  return azioni;
}

// ordine: la generazione del clic che ha chiesto questo pannello. Il
// ricaricamento dallo scorrere degli eventi non ne apre una: prende quella in
// corso, cosi' un clic dell'utente arrivato nel frattempo lo batte.
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
      fallisciDettaglio(
        dettaglio,
        "il server ha risposto con uno schema che non si legge. Ricarica la pagina; se il messaggio torna, riavvia «meshrec serve» dal terminale.",
      );
      return;
    }
    schemaParametri = corpo;
  }
  // Come il ramo dello schema qui sopra: senza guardare risposta.ok, .json()
  // solleva un SyntaxError sul corpo d'errore e il pannello resta bianco senza
  // dire perche'.
  // Insieme e non in fila: sono due letture indipendenti, e in fila il pannello
  // aspettava la somma delle due latenze invece della maggiore. `.catch` resta
  // su ciascuna, cosi' un server muto prende la forma del rifiuto su entrambe.
  const [rispostaConfig, rispostaMetriche] = await Promise.all([
    fetch("/api/config").catch(serverMuto),
    fetch("/api/metrics").catch(serverMuto),
  ]);
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
    fallisciDettaglio(
      dettaglio,
      "il server ha risposto con un corpo che non si legge. Ricarica la pagina; se il messaggio torna, riavvia «meshrec serve» dal terminale.",
    );
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

  dettaglio.append(...intestazioneDelloStep(numero, ultimiSteps));
  dettaglio.append(azioniDelloStep(numero, ordine));

  for (const blocco of voce.blocchi) {
    dettaglio.append(gruppoDelBlocco(blocco, voce.campi[blocco], ordine));
  }

  // Dentro dettaglio, che replaceChildren() svuota a ogni apertura: cosi' il
  // pannello non puo' sopravvivere a uno step che non e' il suo.
  if (numero === STEP_CON_RITAGLIO) dettaglio.append(pannelloRitaglio(ordine));

  const chiave = Object.keys(metriche).find((k) => k.startsWith(String(numero).padStart(2, "0")));
  if (chiave) {
    const titolo = document.createElement("h3");
    titolo.textContent = "Metriche";
    const tabella = document.createElement("dl");
    tabella.className = "metriche";
    for (const [nome, valore] of Object.entries(metriche[chiave])) {
      const cella = document.createElement("dd");
      cella.append(document.createTextNode(resaMetrica(valore)));
      // La glossa sta con il valore e non con la chiave: la colonna delle
      // chiavi e' larga «auto», e una frase dentro la porterebbe a occupare
      // tutto il pannello lasciando i numeri in un filo.
      const glossa = GLOSSARIO_METRICHE[nome];
      if (glossa !== undefined) {
        cella.append(Object.assign(document.createElement("small"), {
          className: "aiuto",
          textContent: glossa,
        }));
      }
      tabella.append(Object.assign(document.createElement("dt"), { textContent: nome }), cella);
    }
    dettaglio.append(titolo, tabella);
  }

  // Lo step 7 non ha parametri propri: senza metriche il pannello resterebbe
  // i soli bottoni, e un riquadro vuoto non distingue "niente da mostrare" da
  // "non ha caricato".
  if (voce.blocchi.length === 0 && !chiave) {
    dettaglio.append(Object.assign(document.createElement("p"), {
      className: "vuoto",
      textContent: "Questo step non ha parametri propri e non ha ancora prodotto metriche.",
    }));
  }
}

// Galleria di curazione: i registri della Fase 2 (/api/experiments*), in
// sola lettura. Nessun clic da qui scrive mai sul disco.

async function caricaGalleria() {
  const risposta = await fetch("/api/experiments").catch(serverMuto);
  const corpo = await corpoLetto(risposta);
  // Silenzioso e non un errore a video: una corsa senza cartella experiments/
  // accanto (la comune, durante lo sviluppo di uno step) non e' un guasto
  // della galleria, e' solo che non c'e' niente da elencare.
  if (corpo == null || !Array.isArray(corpo.esperimenti)) return;
  const elenco = document.getElementById("galleria-elenco");
  elenco.replaceChildren(...corpo.esperimenti.map((nome) => {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "bottone";
    bottone.textContent = nome;
    bottone.dataset.nome = nome;
    // Nessuno stato scelto: due bottoni identici e nessun segno di quale
    // tabella si sta guardando. .step ha aria-current e un doppio canale con
    // sei righe di commento a difenderlo; qui non c'era niente.
    bottone.setAttribute("aria-pressed", "false");
    return bottone;
  }));
}

caricaGalleria();

// L'ordine dell'appendice stampata non e' l'ordine di una colonna da 22rem:
// l'impronta SHA-256 e' 64 caratteri che non vanno a capo, e da sola sfondava
// il riquadro, lasciando fuori schermo tutte e sette le grandezze per cui il
// pannello esiste.
// L'insieme resta quello di report._COLUMNS: qui si sceglie per chiave, e una
// chiave che questo elenco non nomina compare comunque, in coda. Una colonna
// aggiunta al server domani appare da sola, che e' la proprieta' per cui le
// colonne sono riusate invece di riscelte.
const ORDINE_GALLERIA = [
  "outcome", "thickness_error", "tets", "over", "dihedral", "duration_s", "axes", "fingerprint",
];

// Le colonne nel verso di lettura, ognuna con il proprio indice di partenza:
// e' quello con cui si indicizzano le celle, che il server manda nell'ordine
// suo. Perderlo vorrebbe dire mettere i numeri sotto l'intestazione sbagliata,
// che e' peggio di una tabella troppo larga.
function colonneOrdinate(colonne, ordine = ORDINE_GALLERIA) {
  const posizione = (colonna) => {
    const trovata = ordine.indexOf(colonna.chiave);
    return trovata === -1 ? ordine.length : trovata;
  };
  return colonne
    .map((colonna, indice) => ({ colonna, indice }))
    .sort((a, b) => posizione(a.colonna) - posizione(b.colonna) || a.indice - b.indice);
}

// Le colonne e le celle arrivano gia' formattate dal server (report._COLUMNS
// e report._cell, riusate in server.py): questa funzione si limita a
// disegnarle, senza una seconda scelta di colonne che potrebbe divergere da
// quella dell'appendice della tesi.
function disegnaTabellaGalleria(corpo) {
  const contenitore = document.getElementById("galleria-tabella");
  const didascalia = document.getElementById("galleria-didascalia");
  contenitore.replaceChildren();
  // Un nome solo per la region e per la didascalia della tabella: scritto due
  // volte, cambiare la dicitura in un posto farebbe divergere in silenzio il
  // nome annunciato da quello visto. E' il rispecchiamento a mano che la
  // colonna della galleria ha gia' pagato una volta.
  const nomeDelRegistro = `Registro dell'esperimento ${corpo.nome}`;
  // Insieme allo svuotamento, e prima del ritorno anticipato: scritto piu' in
  // basso, un esperimento senza righe lasciava annunciato il nome di quello di
  // prima — un nome fermo e generico e' meglio di uno attivamente sbagliato.
  contenitore.setAttribute("aria-label", nomeDelRegistro);
  if (corpo.righe.length === 0) {
    didascalia.textContent = `${corpo.nome}: registro vuoto.`;
    return;
  }
  didascalia.textContent =
    `${corpo.nome}: ${corpo.righe.length} candidati, ${corpo.fronte} sul fronte.`;
  const ordinate = colonneOrdinate(corpo.colonne);
  const rigaTesta = document.createElement("tr");
  // La colonna del fronte e' derivata, non una grandezza in piu': nell'appendice
  // lo stesso fatto e' gia' li', come classe della riga. A video una classe non
  // si legge, e il colore da solo non basta (WCAG 1.4.1).
  const testaFronte = document.createElement("th");
  testaFronte.textContent = "fronte";
  testaFronte.setAttribute("scope", "col");
  rigaTesta.append(testaFronte);
  for (const { colonna } of ordinate) {
    const testa = document.createElement("th");
    testa.textContent = colonna.etichetta;
    // scope="col": senza, un lettore di schermo non lega la cella alla sua
    // intestazione, e otto numeri di fila non dicono di che cosa siano.
    testa.setAttribute("scope", "col");
    rigaTesta.append(testa);
  }
  const testa = document.createElement("thead");
  testa.append(rigaTesta);
  const corpoTabella = document.createElement("tbody");
  corpo.righe.forEach((riga, indice) => {
    const rigaHtml = document.createElement("tr");
    // "fronte", non un nuovo nome: e' la stessa classe che report.write_report
    // scrive sulla riga di fronte dell'appendice della tesi.
    if (riga.on_front) rigaHtml.className = "fronte";
    const cellaFronte = document.createElement("td");
    cellaFronte.textContent = riga.on_front ? "fronte" : "";
    rigaHtml.append(cellaFronte);
    for (const { colonna, indice: originale } of ordinate) {
      const testo = String(corpo.celle[indice][originale] ?? "");
      const cella = document.createElement("td");
      // L'impronta troncata, con il valore pieno nel titolo: e' un
      // identificatore da riconoscere, non da leggere, e otto caratteri di
      // SHA-256 bastano a distinguere undici candidati. Il titolo pero'
      // raggiunge solo chi usa il mouse: il valore intero vive anche in un
      // nodo .fuori-vista dentro la stessa cella, cosi' chi usa un lettore di
      // schermo lo raggiunge quanto chi punta il cursore.
      if (colonna.chiave === "fingerprint") {
        cella.setAttribute("title", testo);
        const breve = document.createElement("span");
        breve.className = "impronta-breve";
        breve.textContent = testo.slice(0, 8);
        const completa = document.createElement("span");
        completa.className = "fuori-vista";
        completa.textContent = testo;
        cella.append(breve, completa);
      } else {
        cella.textContent = testo;
      }
      rigaHtml.append(cella);
    }
    corpoTabella.append(rigaHtml);
  });
  const tabella = document.createElement("table");
  const nome = document.createElement("caption");
  nome.textContent = nomeDelRegistro;
  tabella.append(nome, testa, corpoTabella);
  contenitore.append(tabella);
}

// Un contatore fresco per clic, come apriGeometria/apriBattuta: due clic su
// due esperimenti sovrapposti — o due riaperture dello stesso — non devono
// far vincere la risposta piu' vecchia.
let ultimaGalleria = 0;

function apriGalleria() {
  ultimaGalleria += 1;
  return ultimaGalleria;
}

// Vero se questa richiesta ha scritto (compresa la dichiarazione di un
// rifiuto), falso se e' stata scartata perche' superata da una piu' recente.
async function mostraEsperimento(nome) {
  const richiesta = apriGalleria();
  const risposta = await fetch(`/api/experiments/${encodeURIComponent(nome)}`).catch(serverMuto);
  if (!risposta.ok) {
    const ragione = await ragioneDelRifiuto(risposta);
    // Dopo l'ultima attesa e prima della prima scrittura, come le altre
    // tratte del modulo.
    if (superata(richiesta, ultimaGalleria)) return false;
    dichiaraErrore(ragione);
    return true;
  }
  const corpo = await corpoLetto(risposta);
  if (superata(richiesta, ultimaGalleria)) return false;
  if (corpo == null || !Array.isArray(corpo.righe) || !Array.isArray(corpo.colonne) || !Array.isArray(corpo.celle)) {
    dichiaraErrore("il server ha risposto con un registro che non si legge. Ricarica la pagina; se il messaggio torna, riavvia «meshrec serve» dal terminale.");
    return true;
  }
  dichiaraErrore(null);
  disegnaTabellaGalleria(corpo);
  return true;
}

document.getElementById("galleria-elenco").addEventListener("click", (evento) => {
  const bottone = evento.target.closest("button");
  if (!bottone) return;
  mostraEsperimento(bottone.dataset.nome).then((scritto) => {
    // Solo se questa richiesta ha davvero scritto: marcare un bottone la cui
    // risposta e' stata scartata direbbe che si sta guardando una tabella che
    // non e' a video.
    if (!scritto) return;
    for (const altro of document.querySelectorAll(".bottone")) {
      if (altro.dataset.nome !== undefined) {
        altro.setAttribute("aria-pressed", String(altro === bottone));
      }
    }
  });
});
