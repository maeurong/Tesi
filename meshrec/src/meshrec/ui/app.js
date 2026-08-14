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
const flusso = new EventSource("/api/events");
let avvioStep = null;

flusso.addEventListener("stato", (evento) => {
  const stato = JSON.parse(evento.data);
  disegnaStep(stato.steps);
  const barra = document.getElementById("in-corso");
  if (stato.in_corso) {
    avvioStep = avvioStep ?? Date.now();
    const trascorsi = Math.round((Date.now() - avvioStep) / 1000);
    barra.textContent = `step ${stato.step} in corso, ${trascorsi} s`;
    barra.hidden = false;
  } else {
    avvioStep = null;
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
  if (riga) mostraNuvolaDelloStep(Number(riga.dataset.numero));
});
