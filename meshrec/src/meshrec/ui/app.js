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

async function apriDettaglio(numero) {
  schemaParametri = schemaParametri ?? await (await fetch("/api/schema")).json();
  configurazione = await (await fetch("/api/config")).json();
  const metriche = await (await fetch("/api/metrics")).json();
  const voce = schemaParametri[String(numero)];
  const dettaglio = document.getElementById("dettaglio");
  dettaglio.replaceChildren();

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
    bottone.addEventListener("click", () => fetch(percorso, { method: "POST" }));
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
      const input = document.createElement("input");
      input.value = String(configurazione[blocco][nome] ?? "");
      input.title = campo.description;
      input.addEventListener("change", async () => {
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
          input.setAttribute("aria-invalid", "true");
        } else {
          input.removeAttribute("aria-invalid");
        }
      });
      riga.append(input);
      const aiuto = document.createElement("small");
      aiuto.className = "aiuto";
      aiuto.textContent = campo.description;
      riga.append(aiuto);
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
