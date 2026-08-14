// Orchestrazione dell'interfaccia. Ogni numero mostrato viene dal server.

const ETICHETTE = {
  "01_load": "Lettura", "02_segment": "Segmentazione", "03_downsample": "Riduzione",
  "04_normals": "Normali", "05_reconstruct": "Superficie", "06_repair": "Riparazione",
  "07_surface_quality": "Qualita superficie", "08_simplify": "Semplificazione",
  "09_tetrahedralize": "Tetraedri", "10_volume_quality": "Qualita volume",
  "11_export": "Esportazione",
};

async function caricaStato() {
  const risposta = await fetch("/api/run");
  const corpo = await risposta.json();
  document.getElementById("corsa").textContent = corpo.out_dir;
  disegnaStep(corpo.steps);
}

function disegnaStep(steps) {
  const elenco = document.getElementById("elenco-step");
  elenco.replaceChildren(...steps.map((voce) => {
    const riga = document.createElement("li");
    riga.className = `step stato-${voce.stato.replace(" ", "-")}`;
    riga.dataset.numero = voce.numero;
    const nome = document.createElement("span");
    nome.className = "step-nome";
    nome.textContent = ETICHETTE[voce.chiave] ?? voce.chiave;
    const stato = document.createElement("span");
    stato.className = "step-stato";
    stato.textContent = voce.stato;
    riga.append(nome, stato);
    return riga;
  }));
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
    barra.textContent = `step ${stato.step} in corso, ${Math.round(stato.da_secondi)} s`;
    barra.hidden = false;
  } else {
    barra.hidden = true;
  }
  // Solo sul fronte di discesa: la colonna degli step si aggiorna da questo
  // stesso flusso, e senza questa riga uno step diventerebbe "valido" a
  // sinistra mentre a destra restano le metriche di prima, o nessuna. Non a
  // ogni evento, perche' lo stato arriva ogni mezzo secondo e il pannello si
  // riscriverebbe sotto le dita di chi sta compilando un campo.
  if (eraInCorso && !stato.in_corso && stepAperto !== null) apriDettaglio(stepAperto);
  eraInCorso = stato.in_corso;
});

flusso.addEventListener("riga", (evento) => {
  const registro = document.getElementById("registro");
  const riga = document.createElement("div");
  riga.className = "riga-log";
  riga.textContent = JSON.parse(evento.data);
  registro.append(riga);
  registro.scrollTop = registro.scrollHeight;
});

document.getElementById("annulla").addEventListener("click", async () => {
  await fetch("/api/cancel", { method: "POST" });
});

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

async function mostraNuvolaDelloStep(numero, ordine) {
  const risposta = await fetch(`/api/cloud/${numero}`);
  if (!risposta.ok) {
    if (superata(ordine)) return;
    // Svuotare e' obbligatorio: senza, la scena resta quella dello step
    // precedente mentre il testo dice che non c'e' nulla. Una vista che
    // contraddice la sua didascalia e' peggio di una vista vuota.
    vista.svuota();
    document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
    return;
  }
  const disegnati = Number(risposta.headers.get("X-Points-Drawn"));
  const pieni = Number(risposta.headers.get("X-Points-Total"));
  const grezzi = await risposta.arrayBuffer();
  // Il controllo sta dopo l'ultima attesa e prima della prima scrittura: piu'
  // in alto lascerebbe passare cio' che e' stato superato mentre il corpo
  // arrivava.
  if (superata(ordine)) return;
  vista.svuota();
  vista.mostraNuvola(new Float32Array(grezzi));
  // Sempre entrambi: una nuvola decimata che non lo dichiara e' un dato falso.
  document.getElementById("conteggi").textContent =
    `${disegnati.toLocaleString("it")} punti disegnati su ${pieni.toLocaleString("it")}`;
}

// Gli step che producono una superficie o un volume: dal 5 in poi l'artefatto
// non e' piu' una nuvola, e disegnarne i soli vertici mostrerebbe punti dove
// c'e' un solido.
const STEP_CON_MESH = new Set([5, 6, 8, 9]);

async function mostraStep(numero, ordine) {
  if (!STEP_CON_MESH.has(numero)) return mostraNuvolaDelloStep(numero, ordine);
  const risposta = await fetch(`/api/mesh/${numero}`);
  if (!risposta.ok) {
    if (superata(ordine)) return;
    // Come per la nuvola: svuotare e' obbligatorio, una vista che contraddice
    // la sua didascalia e' peggio di una vista vuota.
    vista.svuota();
    document.getElementById("conteggi").textContent = "nessun artefatto per questo step";
    return;
  }
  const vertici = Number(risposta.headers.get("X-Vertices"));
  const triangoli = Number(risposta.headers.get("X-Triangles"));
  const grezzi = await risposta.arrayBuffer();
  // Qui la latenza e' quella vera: e' la mesh dello step 9 che arriva tardi a
  // posarsi sulla nuvola di un altro step.
  if (superata(ordine)) return;
  vista.svuota();
  vista.mostraMesh(
    new Float32Array(grezzi, 0, vertici * 3),
    new Uint32Array(grezzi, vertici * 3 * 4, triangoli * 3),
  );
  // I conteggi sono quelli che il server ha contato sull'artefatto: per lo
  // step 9 sono i vertici e i triangoli del contorno, non i nodi del volume.
  document.getElementById("conteggi").textContent =
    `${vertici.toLocaleString("it")} vertici, ${triangoli.toLocaleString("it")} triangoli`;
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
  vista.attivaTaglio(Number(asseTaglio.value), quota);
  // La quota e' una coordinata della geometria, che il progetto tiene in
  // millimetri (lo stesso sistema che l'esportazione dichiara nel .inp).
  const testo = `${quota.toLocaleString("it", { maximumFractionDigits: 1 })} mm`;
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
  if (ingombro === null) return vista.disattivaTaglio();
  const asse = Number(asseTaglio.value);
  const minimo = ingombro.min[asse];
  const massimo = ingombro.max[asse];
  quotaTaglio.min = minimo;
  quotaTaglio.max = massimo;
  quotaTaglio.step = (massimo - minimo) / SCATTI_DEL_CURSORE;
  // Al minimo il piano non toglie niente: si riparte dal volume intero.
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
  // riporterebbe il cursore al minimo sotto le dita di chi lo sta muovendo.
  mostraStep(numero, ordine).then(() => {
    if (!superata(ordine)) riallineaTaglio(numero);
  });
  apriDettaglio(numero, ordine);
});

// Lo schema e le descrizioni vengono dai modelli di config.py: l'interfaccia
// non li riscrive, e la validazione di cio' che si scrive resta quella dei
// modelli, non una copia lato browser.
let schemaParametri = null;
let configurazione = null;
let stepAperto = null;
let rigaErrore = null;

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

function paragrafoErrore(testo) {
  // role="alert": chi usa un lettore di schermo deve sentire il rifiuto senza
  // andarlo a cercare.
  const paragrafo = document.createElement("p");
  paragrafo.className = "errore";
  paragrafo.setAttribute("role", "alert");
  paragrafo.textContent = testo;
  return paragrafo;
}

function dichiaraErrore(testo) {
  rigaErrore.textContent = testo ?? "";
  rigaErrore.hidden = !testo;
}

// ordine: la generazione del clic che ha chiesto questo pannello. Il
// ricaricamento dallo scorrere degli eventi non ne apre una: prende quella in
// corso, cosi' un clic dell'utente arrivato nel frattempo lo batte.
async function apriDettaglio(numero, ordine = generazione) {
  const dettaglio = document.getElementById("dettaglio");
  if (schemaParametri === null) {
    const risposta = await fetch("/api/schema");
    // Solo una risposta valida entra in memoria: memorizzare un corpo
    // d'errore avvelenerebbe il pannello per tutta la vita della pagina,
    // perche' nessun click successivo ritenterebbe.
    if (!risposta.ok) {
      const ragione = await ragioneDelRifiuto(risposta);
      if (superata(ordine)) return;
      dettaglio.replaceChildren(paragrafoErrore(ragione));
      return;
    }
    schemaParametri = await risposta.json();
  }
  configurazione = await (await fetch("/api/config")).json();
  const metriche = await (await fetch("/api/metrics")).json();
  // Dopo l'ultima attesa e prima della prima scrittura: qui sono tre andate e
  // ritorni, e in mezzo l'utente puo' aver scelto un altro step. Anche
  // stepAperto sta sotto la guardia, perche' e' lui a dire allo scorrere degli
  // eventi quale pannello ricaricare.
  if (superata(ordine)) return;
  const voce = schemaParametri[String(numero)];
  stepAperto = numero;
  dettaglio.replaceChildren();

  // Svuotata a ogni apertura e prima di ogni tentativo: un errore gia' risolto
  // lasciato a video contraddice cio' che il pannello mostra.
  rigaErrore = paragrafoErrore("");
  rigaErrore.hidden = true;
  dettaglio.append(rigaErrore);

  const azioni = document.createElement("div");
  azioni.className = "azioni";
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
      const risposta = await fetch(percorso, { method: "POST" });
      if (risposta.ok) return;
      const ragione = await ragioneDelRifiuto(risposta);
      // rigaErrore e' quella del pannello aperto adesso: se nel frattempo ne e'
      // stato aperto un altro, questo rifiuto finirebbe scritto sotto lo step
      // sbagliato, e accuserebbe uno step che nessuno ha lanciato.
      if (superata(ordine)) return;
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
      const riga = document.createElement("label");
      riga.className = "campo";
      riga.append(Object.assign(document.createElement("span"), { textContent: nome }));
      const valore = configurazione[blocco][nome];
      // Una lista o un modello annidato non sono scritti in una casella di
      // testo: String() li renderebbe come "1,2,4" o "[object Object]", cioe'
      // un testo che nessuna lettura produce, e ogni modifica tornerebbe
      // comunque rifiutata dal modello.
      const scalare = valore === null || ["string", "number", "boolean"].includes(typeof valore);
      const input = document.createElement("input");
      input.value = scalare ? String(valore ?? "") : JSON.stringify(valore);
      input.title = campo.description;
      const messaggio = document.createElement("small");
      messaggio.className = "errore-campo";
      messaggio.id = `errore-${blocco}-${nome}`;
      messaggio.hidden = true;
      if (!scalare) {
        // readOnly e non disabled: disabled lo toglierebbe anche dalla
        // navigazione da tastiera e dal lettore di schermo.
        input.readOnly = true;
      } else {
        input.addEventListener("change", async () => {
          const precedente = configurazione[blocco][nome];
          const grezzo = input.value;
          const numerico = Number(grezzo);
          configurazione[blocco][nome] =
            grezzo === "true" ? true : grezzo === "false" ? false :
            grezzo === "" ? null : Number.isNaN(numerico) ? grezzo : numerico;
          const risposta = await fetch("/api/config", {
            method: "PUT",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(configurazione),
          });
          input.classList.toggle("campo-rifiutato", !risposta.ok);
          if (!risposta.ok) {
            // Il valore rifiutato non resta nell'oggetto: la PUT manda
            // l'intera configurazione, e tenerlo farebbe rifiutare ogni
            // modifica successiva accusando il campo sbagliato.
            configurazione[blocco][nome] = precedente;
            messaggio.textContent = await ragioneDelRifiuto(risposta);
            messaggio.hidden = false;
            input.setAttribute("aria-invalid", "true");
            // aria-invalid da solo dice che c'e' un errore, mai quale.
            input.setAttribute("aria-errormessage", messaggio.id);
          } else {
            messaggio.hidden = true;
            messaggio.textContent = "";
            input.removeAttribute("aria-invalid");
            input.removeAttribute("aria-errormessage");
          }
        });
      }
      riga.append(input);
      const aiuto = document.createElement("small");
      aiuto.className = "aiuto";
      aiuto.textContent = scalare
        ? campo.description
        : [campo.description, "si modifica dal file di configurazione"]
            .filter(Boolean).join(" — ");
      riga.append(aiuto, messaggio);
      gruppo.append(riga);
    }
    dettaglio.append(gruppo);
  }

  const chiave = Object.keys(metriche).find((k) => k.startsWith(String(numero).padStart(2, "0")));
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
