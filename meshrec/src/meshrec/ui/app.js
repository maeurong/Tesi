// Orchestrazione dell'interfaccia. Ogni numero mostrato viene dal server.

const ETICHETTE = {
  "01_load": "Lettura", "02_segment": "Segmentazione", "03_downsample": "Riduzione",
  "04_normals": "Normali", "05_reconstruct": "Superficie", "06_repair": "Riparazione",
  "07_surface_quality": "Qualita superficie", "08_simplify": "Semplificazione",
  "09_tetrahedralize": "Tetraedri", "10_volume_quality": "Qualita volume",
  "11_export": "Esportazione", "12_wall": "Prior geometrico", "13_solve": "Analisi strutturale",
};

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
    dichiaraErrore("il server ha risposto con uno stato della corsa che non si legge");
    return;
  }
  document.getElementById("corsa").textContent = corpo.out_dir;
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

flusso.addEventListener("stato", (evento) => {
  const stato = JSON.parse(evento.data);
  disegnaStep(stato.steps);
  const barra = document.getElementById("in-corso");
  if (stato.in_corso && stato.da_secondi !== null) {
    // stato.step e' null per un comando che non e' uno step della pipeline
    // (il prior, un modello parametrico: worker.start_comando, non
    // worker.start): la colonna non ha una riga per un comando del genere,
    // e "step null in corso" sarebbe il numero di un ramo che non esiste.
    barra.textContent = stato.step !== null
      ? `step ${stato.step} in corso, ${Math.round(stato.da_secondi)} s`
      : `un comando e' in corso, ${Math.round(stato.da_secondi)} s`;
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
  // Solo sul fronte di discesa: la colonna degli step si aggiorna da questo
  // stesso flusso, e senza questa riga uno step diventerebbe "valido" a
  // sinistra mentre a destra restano le metriche di prima, o nessuna. Non a
  // ogni evento, perche' lo stato arriva ogni mezzo secondo e il pannello si
  // riscriverebbe sotto le dita di chi sta compilando un campo.
  if (eraInCorso && !stato.in_corso) {
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

import { creaViewport, scalaDelCampo, fattoreAmplificazione, didascaliaDelCampo } from "/ui/viewport.js";

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

async function mostraNuvolaDelloStep(numero, ordine) {
  const emissione = apriGeometria();
  const risposta = await fetch(`/api/cloud/${numero}`);
  if (!risposta.ok) {
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    // Svuotare e' obbligatorio: senza, la scena resta quella dello step
    // precedente mentre il testo dice che non c'e' nulla. Una vista che
    // contraddice la sua didascalia e' peggio di una vista vuota.
    vista.svuota();
    document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
    return true;
  }
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const grezzi = await risposta.arrayBuffer();
  // Il controllo sta dopo l'ultima attesa e prima della prima scrittura: piu'
  // in alto lascerebbe passare cio' che e' stato superato mentre il corpo
  // arrivava.
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
// c'e' un solido. Lo step 13 e' anche lui un volume (13_solution.vtu, lo
// stesso contorno di /api/campo): senza di lui in questo insieme un clic sullo
// step 13 chiederebbe /api/cloud/13, che non esiste.
const STEP_CON_MESH = new Set([5, 6, 8, 9, 13]);

async function mostraStep(numero, ordine) {
  // La delega sta prima del contatore: incrementarlo qui e di nuovo la' sotto
  // farebbe battere questa richiesta da se stessa, e nessuna nuvola verrebbe
  // piu' disegnata. Ogni strada apre esattamente una richiesta.
  if (!STEP_CON_MESH.has(numero)) return mostraNuvolaDelloStep(numero, ordine);
  const emissione = apriGeometria();
  const risposta = await fetch(`/api/mesh/${numero}`);
  if (!risposta.ok) {
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    // Come per la nuvola: svuotare e' obbligatorio, una vista che contraddice
    // la sua didascalia e' peggio di una vista vuota.
    vista.svuota();
    document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
    return true;
  }
  const vertici = Number(risposta.headers.get("X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await risposta.arrayBuffer();
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

// Lo step che risolve: /api/campo/{caso}/{grandezza} vive fuori da
// STEP_CON_MESH/STEP_CON_TAGLIO apposta, sono comandi diversi (un campo per
// nodo, non un artefatto di step) che condividono solo il numero di step.
const STEP_CON_CAMPO = 13;

// Il testo della legenda: dichiara sempre dove sta il taglio e quanti nodi lo
// superano, anche su un campo costante (taglio == massimo, nessun picco da
// isolare) o tutto a zero. Number.isFinite guarda solo `taglio`: sopraTaglio
// esce gia' finito da scalaDelCampo, che conta per rango e non per valore.
function testoLegendaDelCampo(taglio, sopraTaglio, unita) {
  // Gli spostamenti veri sono submillimetrici (0,0367 mm, misurato): un solo
  // decimale li arrotonderebbe tutti a "0 mm", la stessa scala muta che il
  // taglio esiste per evitare.
  const cifre = unita === "mm" ? 4 : 1;
  const numero = Number.isFinite(taglio)
    ? taglio.toLocaleString("it", { maximumFractionDigits: cifre })
    : "n/d";
  return `scala tagliata a ${numero} ${unita} — ${sopraTaglio.toLocaleString("it")} nodi sopra il taglio`;
}

// Mesh e campo arrivano insieme, con la stessa arbitrazione di
// mostraNuvolaDelloStep/mostraStep (apriGeometria/ultimaGeometria): due
// selezioni del menu a cascata di seguito non devono far vincere la piu'
// vecchia. Vero se questa chiamata ha scritto (disegno o rifiuto dichiarato),
// falso se e' stata scartata perche' superata.
// legenda/didascalia arrivano come argomenti e non da document.getElementById:
// pannelloCampo li crea e li appende al proprio fieldset nello stesso istante
// in cui costruisce il pannello, prima che quel fieldset sia agganciato al
// documento — getElementById non troverebbe un nodo ancora staccato.
async function mostraCampoDelloStep(caso, grandezza, ordine, legenda, didascalia) {
  const emissione = apriGeometria();
  const [rispostaMesh, rispostaCampo] = await Promise.all([
    fetch(`/api/mesh/${STEP_CON_CAMPO}`).catch(serverMuto),
    fetch(`/api/campo/${caso}/${grandezza}`).catch(serverMuto),
  ]);
  if (!rispostaMesh.ok || !rispostaCampo.ok) {
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
    // Il server risponde sempre 400 (mai 404): un caso/grandezza inesistenti,
    // o il .vtu assente perche' la corsa si e' fermata allo step 12, sono lo
    // stesso rifiuto dichiarato, non una pagina bianca ne' uno stack.
    const ragione = await ragioneDelRifiuto(rispostaMesh.ok ? rispostaCampo : rispostaMesh);
    legenda.textContent = "";
    didascalia.textContent = ragione;
    return true;
  }
  const massimo = Number(rispostaCampo.headers.get("X-Max"));
  const vertici = Number(rispostaMesh.headers.get("X-Vertices"));
  const triangoli = Number(rispostaMesh.headers.get("X-Triangles"));
  const grezziMesh = await rispostaMesh.arrayBuffer();
  const grezziCampo = await rispostaCampo.arrayBuffer();
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return false;
  const valori = new Float32Array(grezziCampo);
  const { taglio, sopraTaglio } = scalaDelCampo(valori);
  const ingombro = vista.ingombro();
  const diagonale = ingombro
    ? Math.hypot(...ingombro.max.map((v, indice) => v - ingombro.min[indice]))
    : NaN;
  const fattore = fattoreAmplificazione(massimo, diagonale);
  const unita = grandezza === "U" ? "mm" : "MPa";
  vista.svuota();
  vista.mostraMeshPerCampo(
    new Float32Array(grezziMesh, 0, vertici * 3),
    new Uint32Array(grezziMesh, vertici * 3 * 4, triangoli * 3),
    valori,
    { taglio, sopraTaglio },
  );
  legenda.textContent = testoLegendaDelCampo(taglio, sopraTaglio, unita);
  didascalia.textContent = didascaliaDelCampo({ caso, grandezza, massimo, fattore });
  return true;
}

// Una forma modale non ha ne' U ne' VM (/api/campo la rifiuta sempre, per
// costruzione: la sua forma e' normalizzata sulla massa, non uno spostamento
// fisico), quindi non c'e' nessun campo da colorare. Delega interamente a
// mostraStep, che disegna gia' la mesh grigia dello step 13 con la propria
// arbitrazione: le didascalie seguono solo se quella chiamata ha vinto.
async function mostraModoDelloStep(numero, frequenza, ordine, legenda, didascalia) {
  const disegnato = await mostraStep(STEP_CON_CAMPO, ordine);
  if (!disegnato) return false;
  legenda.textContent = "";
  didascalia.textContent = didascaliaDelCampo({ caso: `MODO_${numero}`, modale: true, frequenza });
  return true;
}

// Il pannello dello step 13: due <select> (caso, grandezza), non un parametro
// del modello — a differenza dei campi di campoParametro non scrivono nulla
// in config.yaml, quindi non passano da scriviParametro. I nomi dei casi e i
// modi vengono da metriche["13_solve"] (casi, modi, frequenze_hz), non da un
// elenco tenuto qui a mano: un deck futuro con un quarto caso statico non
// richiederebbe di toccare questo file.
function pannelloCampo(ordine, metriche13) {
  const contenitore = document.createElement("fieldset");
  contenitore.className = "gruppo";
  contenitore.append(Object.assign(document.createElement("legend"), { textContent: "Campo" }));
  const casi = Object.keys(metriche13?.casi ?? {});
  const modi = metriche13?.modi ?? 0;
  if (casi.length === 0 && modi === 0) {
    contenitore.append(Object.assign(document.createElement("p"), {
      className: "aiuto",
      textContent: "Lo step 13 non ha ancora prodotto casi di carico ne' modi da mostrare.",
    }));
    return contenitore;
  }
  const selCaso = document.createElement("select");
  for (const nome of casi) selCaso.append(new Option(nome, nome));
  for (let n = 1; n <= modi; n += 1) {
    const hz = metriche13.frequenze_hz?.[n - 1];
    selCaso.append(new Option(`Modo ${n}${Number.isFinite(hz) ? ` (${hz.toFixed(2)} Hz)` : ""}`, `MODO_${n}`));
  }
  const rigaCaso = document.createElement("label");
  rigaCaso.className = "campo";
  rigaCaso.append(Object.assign(document.createElement("span"), { textContent: "caso" }), selCaso);

  const selGrandezza = document.createElement("select");
  selGrandezza.append(new Option("spostamento (U)", "U"), new Option("tensione equivalente (VM)", "VM"));
  const rigaGrandezza = document.createElement("label");
  rigaGrandezza.className = "campo";
  rigaGrandezza.append(Object.assign(document.createElement("span"), { textContent: "grandezza" }), selGrandezza);

  const legenda = Object.assign(document.createElement("p"), { className: "aiuto", id: "campo-legenda" });
  const didascalia = Object.assign(document.createElement("p"), { className: "aiuto", id: "campo-didascalia" });

  async function aggiorna() {
    const caso = selCaso.value;
    const modale = caso.startsWith("MODO_");
    // hidden e non disabled: un modo non ha grandezza, non e' un comando spento.
    rigaGrandezza.hidden = modale;
    if (modale) {
      const numero = Number(caso.slice("MODO_".length));
      await mostraModoDelloStep(numero, metriche13.frequenze_hz?.[numero - 1], ordine, legenda, didascalia);
    } else {
      await mostraCampoDelloStep(caso, selGrandezza.value, ordine, legenda, didascalia);
    }
  }
  selCaso.addEventListener("change", aggiorna);
  selGrandezza.addEventListener("change", aggiorna);
  contenitore.append(rigaCaso, rigaGrandezza, legenda, didascalia);
  aggiorna();
  return contenitore;
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

// Il worker esegue un solo sottoprocesso alla volta (worker.py), e il prior e
// i modelli parametrici passano dallo stesso worker degli step della pipeline
// (start_comando, non start): "in corso" e il suo fronte di discesa sono lo
// stesso stato che il pannello degli step gia' guarda qui sopra. Un
// ascoltatore in piu' sullo stesso flusso, non una fetch in piu': si toglie
// da solo appena risolve, cosi' un secondo clic non ne lascia uno appeso.
function attendiFineComando() {
  return new Promise((risolvi) => {
    flusso.addEventListener("stato", function ascolta(evento) {
      const stato = JSON.parse(evento.data);
      if (stato.in_corso) return;
      flusso.removeEventListener("stato", ascolta);
      risolvi();
    });
  });
}

// Lo step 12 e i modelli sono AZIONI e non parametri: nessuno di questi
// gestori tocca la configurazione, e per questo nessuno chiama scriviParametro.
async function caricaPrior(ordine = generazione) {
  const risposta = await fetch("/api/wall");
  if (superata(ordine)) return;
  const corpo = await corpoLetto(risposta);
  // == e non ===: un corpo intero non e' mai un null legittimo su questo
  // endpoint, e corpoLetto marca con undefined cio' che non si e' letto.
  if (superata(ordine) || corpo == null) return;

  const vuoto = document.getElementById("prior-vuoto");
  vuoto.hidden = corpo.calcolato;
  if (!corpo.calcolato) {
    vuoto.textContent = corpo.motivo;
    document.getElementById("prior-membrature").replaceChildren();
    document.getElementById("prior-scartate").replaceChildren();
    return;
  }
  disegnaMembrature(corpo.prior.membrature);
  disegnaScartate(corpo.prior.scartate);
  await mostraMembratureNelViewport(ordine);
}

function disegnaMembrature(membrature) {
  const contenitore = document.getElementById("prior-membrature");
  contenitore.replaceChildren();
  membrature.forEach((membratura, numero) => {
    const riga = document.createElement("p");
    const sezione = membratura.sezione.map((v) => v.toFixed(1)).join(" x ");
    riga.textContent =
      `Membratura ${numero + 1}: sezione ${sezione} mm, lunghezza ` +
      `${membratura.lunghezza.toFixed(1)} mm, fuori piombo ` +
      `${membratura.fuori_piombo_deg.toFixed(2)} gradi`;
    contenitore.append(riga);
  });
}

function disegnaScartate(scartate) {
  // «quale controllo ha detto no, e quale numero glielo ha fatto dire»: un
  // rifiuto senza il proprio numero non dice a chi legge che cosa cambiare.
  const contenitore = document.getElementById("prior-scartate");
  contenitore.replaceChildren();
  for (const voce of scartate) {
    for (const nome of voce.controlli_falliti) {
      const esito = voce.esiti[nome];
      const riga = document.createElement("p");
      riga.className = "rifiuto";
      riga.textContent =
        `Regione ${voce.regione + 1} non e' una membratura: il controllo ` +
        `«${nome}» ha misurato ${esito.valore.toFixed(3)} contro una soglia di ` +
        `${esito.soglia.toFixed(3)}.`;
      contenitore.append(riga);
    }
  }
}

// /api/membrature manda un'etichetta per punto, non le posizioni: sono quelle
// gia' note allo step 2 (stessa decimazione, stessa cache di /api/cloud/2 —
// vedi server.py, viewport.decimate_file con gli stessi argomenti). Le due
// risposte condividono l'arbitro della geometria (apriGeometria/
// ultimaGeometria) gia' provato su mostraStep: scrivono nello stesso
// viewport, e un clic su uno step mentre questa e' in volo non deve perdere
// ne' vincere per caso.
async function mostraMembratureNelViewport(ordine) {
  const emissione = apriGeometria();
  const [rispostaPunti, rispostaEtichette] = await Promise.all([
    fetch("/api/cloud/2"),
    fetch("/api/membrature"),
  ]);
  if (!rispostaPunti.ok || !rispostaEtichette.ok) {
    if (superata(ordine) || superata(emissione, ultimaGeometria)) return;
    vista.svuota();
    document.getElementById("conteggi").textContent = "nessuna mappa delle membrature da mostrare";
    return;
  }
  const punti = new Float32Array(await rispostaPunti.arrayBuffer());
  const membrature = Number(rispostaEtichette.headers.get("X-Membrature"));
  const etichette = new Float32Array(await rispostaEtichette.arrayBuffer());
  if (superata(ordine) || superata(emissione, ultimaGeometria)) return;
  vista.svuota();
  vista.mostraNuvolaPerMembratura(punti, etichette);
  document.getElementById("conteggi").textContent =
    `${(punti.length / 3).toLocaleString("it")} punti, ${membrature} membrature`;
  // Il taglio si riferisce all'ultimo volume disegnato: la mappa delle
  // membrature e' una nuvola, non lo step 9, quindi non ha un comando di
  // taglio proprio. Senza questa riga il comando resterebbe a video puntato
  // su un ingombro che non e' piu' quello disegnato -- la vista che
  // contraddice il proprio comando, la stessa ragione per cui riallineaTaglio
  // esiste.
  riallineaTaglio(null);
}

async function caricaConfronto(ordine = generazione) {
  const risposta = await fetch("/api/compare");
  if (superata(ordine)) return;
  if (!risposta.ok) {
    // /api/compare rifiuta sia alla prima apertura (ne' 12_wall.json ne'
    // modello.json in nessuna cartella) sia quando una corsa figlia e'
    // fallita a meta' (cartella orfana, ne' modello ne' corsa madre). I due
    // casi non sono lo stesso stato: il messaggio del gestore globale li
    // distingue gia', quindi lo si legge invece di mostrare sempre lo stesso
    // testo statico. Verificato nel browser: senza questo ramo `corpo[grandezza]`
    // sotto e' undefined e il pannello del confronto solleva fuori da ogni catch.
    const vuoto = document.getElementById("confronto-vuoto");
    vuoto.textContent = await ragioneDelRifiuto(risposta);
    vuoto.hidden = false;
    document.getElementById("confronto-tabella").replaceChildren();
    return;
  }
  const corpo = await corpoLetto(risposta);
  if (superata(ordine) || corpo == null) return;

  const vuoto = document.getElementById("confronto-vuoto");
  vuoto.textContent = vuoto.dataset.testoVuoto;
  vuoto.hidden = !corpo.scheda_singola;
  const tabella = document.getElementById("confronto-tabella");
  tabella.replaceChildren();
  for (const grandezza of ["volume", "massa", "scostamento_nuvola"]) {
    const riga = document.createElement("p");
    // Un modello assente si nomina, non si riempie con un trattino: un
    // trattino in mezzo ai numeri somiglia a un valore.
    const celle = ["as-built", "estruso", "primitive"].map((nome) =>
      nome in corpo[grandezza] ? `${nome}: ${corpo[grandezza][nome]}` : `${nome}: non generato`,
    );
    riga.textContent = `${grandezza} — ${celle.join(" · ")}`;
    tabella.append(riga);
  }

  // Il limite dichiarato della fase (F2): parte dei nodi dipendenti non e'
  // vincolata, quindi una differenza di cedevolezza fra i modelli puo' venire
  // dal *TIE e non dalla forma. Il report HTML lo dice gia' (write_comparison_report);
  // qui e' lo stesso dato, gia' nel payload, solo mai reso finora.
  const note = document.createElement("p");
  note.textContent = `note — ${corpo.note_non_geometriche.join(" ")}`;
  tabella.append(note);

  const vincoliRiga = document.createElement("p");
  const celleVincoli = ["as-built", "estruso", "primitive"].map((nome) => {
    if (!(nome in corpo.vincoli_giunzioni)) return `${nome}: non generato`;
    const v = corpo.vincoli_giunzioni[nome];
    return v === "non applicabile"
      ? `${nome}: non applicabile`
      : `${nome}: ${v.nodi_dipendenti_legati}/${v.nodi_dipendenti_totali} nodi dipendenti legati`;
  });
  vincoliRiga.textContent = `vincoli alle giunzioni — ${celleVincoli.join(" · ")}`;
  tabella.append(vincoliRiga);

  if (corpo.chiusura_volume) {
    const chiusura = document.createElement("p");
    chiusura.textContent =
      `chiusura del volume alle giunzioni — ${corpo.chiusura_volume.passato ? "passato" : "NON passato"}`;
    tabella.append(chiusura);
  }
}

caricaPrior();
caricaConfronto();

document.getElementById("calcola-prior").addEventListener("click", async () => {
  const bottone = document.getElementById("calcola-prior");
  const altro = document.getElementById("genera-modelli");
  // Presa prima dell'attesa, non dopo: mostraMembratureNelViewport scrive nello
  // stesso viewport di mostraStep. Se un clic su uno step arriva mentre il
  // prior sta ancora calcolando, quello step e' cio' che l'utente guarda
  // adesso, e la mappa delle membrature -- piu' vecchia di quel clic -- non
  // deve scriverci sopra.
  const ordine = generazione;
  bottone.disabled = true;
  altro.disabled = true;
  try {
    await fetch("/api/wall", { method: "POST" });
    await attendiFineComando();
    if (!superata(ordine)) caricaPrior(ordine);
  } finally {
    bottone.disabled = false;
    altro.disabled = false;
  }
});

document.getElementById("genera-modelli").addEventListener("click", async () => {
  const bottone = document.getElementById("genera-modelli");
  const altro = document.getElementById("calcola-prior");
  const ordine = generazione;
  bottone.disabled = true;
  altro.disabled = true;
  try {
    for (const tipo of ["estruso", "primitive"]) {
      if (!document.getElementById(`modello-${tipo}`).checked) continue;
      // uno alla volta: il worker esegue un solo sottoprocesso, ed e' apposta
      await fetch(`/api/model/${tipo}`, { method: "POST" });
      await attendiFineComando();
    }
    if (!superata(ordine)) caricaConfronto(ordine);
  } finally {
    bottone.disabled = false;
    altro.disabled = false;
  }
});

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
  for (const estremo of ["min", "max"]) {
    for (const asse of [0, 1, 2]) {
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(Object.assign(document.createElement("span"), {
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
        ? `${corpo.points_after.toLocaleString("it")} punti: e' quanti ne terrebbe lo step 2 ` +
          "rieseguito con questo box."
        : `${corpo.points_after.toLocaleString("it")} punti dopo il ritaglio: con ` +
          "questo metodo lo step 2 prosegue con i piani e i cluster, e non ne terra' di piu'.") +
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
  input.value = scalare ? String(valore ?? "") : JSON.stringify(valore);
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
    : [campo.description, "si modifica dal file di configurazione"]
        .filter(Boolean).join(" — ");
  riga.append(aiuto, messaggio);
  return riga;
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
      fallisciDettaglio(dettaglio, "il server ha risposto con uno schema che non si legge");
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
    fallisciDettaglio(dettaglio, "il server ha risposto con un corpo che non si legge");
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
  for (const [etichetta, percorso] of [
    ["Esegui questo step", `/api/step/${numero}`],
    ["Esegui da qui in giu'", `/api/step/${numero}/from`],
  ]) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "bottone";
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

  for (const blocco of voce.blocchi) {
    const gruppo = document.createElement("fieldset");
    gruppo.className = "gruppo";
    const titolo = document.createElement("legend");
    titolo.textContent = blocco;
    gruppo.append(titolo);
    for (const [nome, campo] of Object.entries(voce.campi[blocco])) {
      gruppo.append(campoParametro(blocco, nome, campo, ordine));
    }
    dettaglio.append(gruppo);
  }

  // Presa qui, prima dei due pannelli sotto: pannelloCampo la legge per
  // costruire i propri <select> dai casi e dai modi gia' risolti, la sezione
  // Metriche piu' sotto la legge per il resto.
  const chiave = Object.keys(metriche).find((k) => k.startsWith(String(numero).padStart(2, "0")));

  // Dentro dettaglio, che replaceChildren() svuota a ogni apertura: cosi' il
  // pannello non puo' sopravvivere a uno step che non e' il suo.
  if (numero === STEP_CON_RITAGLIO) dettaglio.append(pannelloRitaglio(ordine));
  if (numero === STEP_CON_CAMPO) dettaglio.append(pannelloCampo(ordine, metriche[chiave]));

  if (chiave) {
    const titolo = document.createElement("h3");
    titolo.textContent = "Metriche";
    const tabella = document.createElement("dl");
    tabella.className = "metriche";
    for (const [nome, valore] of Object.entries(metriche[chiave])) {
      tabella.append(
        Object.assign(document.createElement("dt"), { textContent: nome }),
        Object.assign(document.createElement("dd"), {
          textContent: typeof valore === "object" ? JSON.stringify(valore) : String(valore),
        }),
      );
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
    return bottone;
  }));
}

caricaGalleria();

// Le colonne e le celle arrivano gia' formattate dal server (report._COLUMNS
// e report._cell, riusate in server.py): questa funzione si limita a
// disegnarle, senza una seconda scelta di colonne che potrebbe divergere da
// quella dell'appendice della tesi.
function disegnaTabellaGalleria(corpo) {
  const contenitore = document.getElementById("galleria-tabella");
  contenitore.replaceChildren();
  if (corpo.righe.length === 0) {
    contenitore.append(Object.assign(document.createElement("p"), {
      className: "vuoto",
      textContent: `${corpo.nome}: registro vuoto.`,
    }));
    return;
  }
  const rigaTesta = document.createElement("tr");
  for (const colonna of corpo.colonne) {
    rigaTesta.append(Object.assign(document.createElement("th"), { textContent: colonna.etichetta }));
  }
  const testa = document.createElement("thead");
  testa.append(rigaTesta);
  const corpoTabella = document.createElement("tbody");
  corpo.righe.forEach((riga, indice) => {
    const rigaHtml = document.createElement("tr");
    // "fronte", non un nuovo nome: e' la stessa classe che report.write_report
    // scrive sulla riga di fronte dell'appendice della tesi.
    if (riga.on_front) rigaHtml.className = "fronte";
    for (const cella of corpo.celle[indice]) {
      rigaHtml.append(Object.assign(document.createElement("td"), { textContent: cella }));
    }
    corpoTabella.append(rigaHtml);
  });
  const tabella = document.createElement("table");
  tabella.append(testa, corpoTabella);
  contenitore.append(
    Object.assign(document.createElement("p"), {
      className: "aiuto",
      textContent: `${corpo.nome}: ${corpo.righe.length} candidati, ${corpo.fronte} sul fronte.`,
    }),
    tabella,
  );
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
    dichiaraErrore("il server ha risposto con un registro che non si legge");
    return true;
  }
  dichiaraErrore(null);
  disegnaTabellaGalleria(corpo);
  return true;
}

document.getElementById("galleria-elenco").addEventListener("click", (evento) => {
  const bottone = evento.target.closest("button");
  if (!bottone) return;
  mostraEsperimento(bottone.dataset.nome);
});
