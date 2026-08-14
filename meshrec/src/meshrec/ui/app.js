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

async function mostraNuvolaDelloStep(numero) {
  const risposta = await fetch(`/api/cloud/${numero}`);
  if (!risposta.ok) {
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
  vista.svuota();
  vista.mostraNuvola(new Float32Array(grezzi));
  // Sempre entrambi: una nuvola decimata che non lo dichiara e' un dato falso.
  document.getElementById("conteggi").textContent =
    `${disegnati.toLocaleString("it")} punti disegnati su ${pieni.toLocaleString("it")}`;
}

document.getElementById("elenco-step").addEventListener("click", (evento) => {
  const riga = evento.target.closest(".step");
  if (!riga) return;
  const numero = Number(riga.dataset.numero);
  mostraNuvolaDelloStep(numero);
  apriDettaglio(numero);
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

async function apriDettaglio(numero) {
  const dettaglio = document.getElementById("dettaglio");
  if (schemaParametri === null) {
    const risposta = await fetch("/api/schema");
    // Solo una risposta valida entra in memoria: memorizzare un corpo
    // d'errore avvelenerebbe il pannello per tutta la vita della pagina,
    // perche' nessun click successivo ritenterebbe.
    if (!risposta.ok) {
      dettaglio.replaceChildren(paragrafoErrore(await ragioneDelRifiuto(risposta)));
      return;
    }
    schemaParametri = await risposta.json();
  }
  configurazione = await (await fetch("/api/config")).json();
  const metriche = await (await fetch("/api/metrics")).json();
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
      // Un click rifiutato in silenzio non e' distinguibile da uno andato a
      // buon fine: il server ha gia' scritto il perche', e va mostrato.
      if (!risposta.ok) dichiaraErrore(await ragioneDelRifiuto(risposta));
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
