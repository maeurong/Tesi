// La tratta del pannello «Modello»: descrive il fronte, cioe' lo step valido
// di numero piu' alto, con i numeri che metrics.json porta gia'.
//
// Le funzioni pure (nessun `document`, nessuna `fetch`, a livello di modulo)
// stanno separate dalla parte con DOM/fetch: le prime si importano da un node
// nudo e si provano senza finzioni, la seconda si costruisce con
// `creaPannelloModello`, che prende le proprie dipendenze come argomenti
// invece di leggerle da app.js -- altrimenti questo modulo importerebbe da
// li' e app.js importa da qui, un ciclo.
// Relativo e non "/ui/etichette.js": un banco importa questo file per davvero
// da un percorso assoluto qualunque (node non e' il server), e un percorso
// relativo resta valido li' come nel browser.
import { METRICHE_D_ALLARME } from "./etichette.js";

// Lo step valido di numero piu' alto, prior escluso: e' cio' che si ha in
// mano adesso. Pura: `stepDelPrior` arriva come argomento (e' `STEP_DEL_PRIOR`
// in app.js) invece che letto da un modulo che non importa.
export function fronteDelloStato(steps, stepDelPrior) {
  let fronte = null;
  for (const voce of steps) {
    if (voce.stato !== "valido" || voce.chiave === stepDelPrior) continue;
    if (fronte === null || voce.numero > fronte.numero) fronte = voce;
  }
  return fronte;
}

// Cio' che, cambiando, chiede una rilettura di /api/metrics: un'esecuzione
// finita cambia i secondi, un annullamento l'impronta o il numero, un
// parametro modificato l'impronta. Il flusso SSE arriva ogni mezzo secondo,
// e rileggere a ogni fotogramma sarebbero due richieste al secondo per niente.
export function chiaveDelFronte(fronte) {
  if (fronte === null) return "";
  return `${fronte.numero}|${fronte.impronta}|${fronte.secondi}`;
}

export const NON_MISURATO = "non misurato";

// Un valore di metrics.json reso come testo del pannello.
//
// Il numero lo formatta `formatta` (in app.js e' `valoreDellaMetrica`, quello
// che la colonna del dettaglio usa gia'): un secondo formattatore avrebbe
// messo la stessa quantita' a due passi di distanza con due arrotondamenti
// diversi, che e' il difetto che quella funzione porta scritto nel proprio
// commento. Passato come argomento e non importato: questa funzione resta
// pura, provabile da node senza il resto di app.js.
//
// Qui sopra restano le sole due differenze che il pannello ha davvero.
// `chiusura` e' il solo booleano che si legge come stato e non come si'/no; e
// un ingombro e' tre numeri accanto, non il JSON di una lista, perche' qui le
// liste sono corte e note (`extent`) e non le matrici quattro per quattro che
// la colonna del dettaglio deve chiudere.
export function valoreDelModello(valore, forma, formatta) {
  if (valore === undefined || valore === null) return NON_MISURATO;
  if (forma === "chiusura") return valore ? "chiusa" : "aperta";
  // Vuota, la lista non e' un valore: unita darebbe la stringa vuota, e una
  // riga vuota a schermo si legge «misurato, e non c'e' niente».
  if (Array.isArray(valore)) {
    if (valore.length === 0) return NON_MISURATO;
    return valore.map((v) => valoreDelModello(v, undefined, formatta)).join(" × ");
  }
  return formatta(valore);
}

// [etichetta, percorso nelle metriche, forma]. Il percorso parte dalla chiave
// dello step: alcune righe leggono lo step a monte (il 4 non conta i punti,
// li ha contati il 3). Le chiavi sono quelle che pipeline.py scrive davvero,
// verificate su runs/lab_telaio_v2/metrics.json il 03/09/2026.
export const RIGHE_DELLA_SUPERFICIE = (chiave) => [
  ["vertici", [chiave, "vertices"]],
  ["triangoli", [chiave, "triangles"]],
  ["superficie", [chiave, "watertight"], "chiusura"],
  ["spigoli di bordo", [chiave, "boundary_edges"]],
  ["area [mm²]", [chiave, "area"]],
  ["volume racchiuso [mm³]", [chiave, "volume"]],
];

export const RIGHE_DEL_MODELLO = {
  "01_load": [
    ["punti", ["01_load", "points_kept"]],
    ["spaziatura media [mm]", ["01_load", "spacing"]],
    ["ingombro [mm]", ["01_load", "extent"]],
  ],
  "02_segment": [
    ["punti", ["02_segment", "points_after"]],
    ["punti tolti come rumore", ["02_segment", "outliers_removed"]],
    ["punti ritagliati", ["02_segment", "cropped_points"]],
  ],
  "03_downsample": [
    ["punti", ["03_downsample", "points_after"]],
    ["voxel [mm]", ["03_downsample", "voxel_size"]],
    ["riduzione", ["03_downsample", "reduction"]],
  ],
  "04_normals": [
    ["punti", ["03_downsample", "points_after"]],
    ["normali degeneri", ["04_normals", "degenerate_normals"]],
  ],
  "05_reconstruct": RIGHE_DELLA_SUPERFICIE("05_reconstruct"),
  "06_repair": RIGHE_DELLA_SUPERFICIE("06_repair"),
  "07_surface_quality": [
    ...RIGHE_DELLA_SUPERFICIE("07_surface_quality"),
    // Il verso e' mesh_to_cloud e non cloud_to_mesh: e' quello che il progetto
    // chiama «scarto dalla nuvola» dappertutto -- il report lo legge cosi'
    // (report.py), la legenda della vista e' alimentata dallo scarto
    // per-vertice, che e' lo stesso verso, e i numeri gia' pubblicati vengono
    // da li'. Leggere l'altro verso metterebbe sotto lo stesso nome una misura
    // diversa da quella che sta in tesi.
    ["scarto dalla nuvola, RMS [mm]", ["07_surface_quality", "geometric_error", "mesh_to_cloud", "RMS"]],
    ["scarto dalla nuvola, massimo [mm]", ["07_surface_quality", "geometric_error", "mesh_to_cloud", "max"]],
  ],
  "08_simplify": RIGHE_DELLA_SUPERFICIE("08_simplify"),
  "09_tetrahedralize": [
    ["nodi", ["09_tetrahedralize", "nodes"]],
    ["tetraedri", ["09_tetrahedralize", "tets"]],
    ["punti di Steiner", ["09_tetrahedralize", "steiner_points"]],
    ["Steiner saturato", ["09_tetrahedralize", "steiner_saturated"]],
  ],
  "10_volume_quality": [
    ["nodi", ["10_volume_quality", "nodes"]],
    ["tetraedri", ["10_volume_quality", "tets"]],
    ["volume totale [mm³]", ["10_volume_quality", "total_volume"]],
    ["diedro minimo [°]", ["10_volume_quality", "min_dihedral_deg", "min"]],
    ["elementi rovesciati", ["10_volume_quality", "inverted"]],
  ],
  "11_export": [
    ["tipo di elemento", ["11_export", "element_type"]],
    ["nodi", ["10_volume_quality", "nodes"]],
    ["tetraedri", ["10_volume_quality", "tets"]],
    ["massa [t]", ["11_export", "mass"]],
    ["volume [mm³]", ["11_export", "volume"]],
  ],
};

// Le righe del pannello per il fronte dato: coppie [etichetta, testo]. Pura:
// `formatta` sostituisce `valoreDellaMetrica` di app.js, per lo stesso motivo
// di `valoreDelModello`.
export function righeDelModello(fronte, metriche, formatta) {
  // `Object.hasOwn` e non `?? []`: una chiave come "constructor" o "toString"
  // trova qualcosa sulla catena dei prototipi, e `??` la lascerebbe passare.
  const righe = Object.hasOwn(RIGHE_DEL_MODELLO, fronte.chiave) ? RIGHE_DEL_MODELLO[fronte.chiave] : [];
  return righe.map(([etichetta, percorso, forma]) => {
    let valore = metriche;
    for (const passo of percorso) {
      valore = valore !== null && typeof valore === "object" ? valore[passo] : undefined;
    }
    // Terza voce e non una classe scritta qui: questa funzione e' pura e non
    // tocca il DOM. Si cerca alla FOGLIA, come righeDellaMetrica: e' la chiave
    // che il set nomina, e la famiglia varrebbe per misure diverse.
    const foglia = percorso[percorso.length - 1];
    return [etichetta, valoreDelModello(valore, forma, formatta), METRICHE_D_ALLARME.has(foglia) && valore === true];
  });
}

// Le dipendenze che `aggiornaModello` non puo' chiudere su se stesso: `fetch`
// ed `elemento` vengono dal browser, `superata`/`serverMuto`/`corpoLetto`
// leggono variabili di modulo di app.js (`generazione`), `valoreDellaMetrica`
// e' il formattatore condiviso con la colonna del dettaglio, `ETICHETTE` e
// `STEP_DEL_PRIOR` sono dati di app.js. Un nome mancante solleva SUBITO, alla
// costruzione: un `undefined` scoperto al primo fotogramma sarebbe un crash
// lontano dalla propria causa.
const DIPENDENZE_DEL_PANNELLO = [
  "fetch", "elemento", "superata", "serverMuto", "corpoLetto",
  "valoreDellaMetrica", "ETICHETTE", "STEP_DEL_PRIOR",
];

export function creaPannelloModello(dipendenze) {
  for (const nome of DIPENDENZE_DEL_PANNELLO) {
    if (dipendenze[nome] === undefined) throw new TypeError(`creaPannelloModello: manca ${nome}`);
  }
  const { fetch, elemento, superata, serverMuto, corpoLetto, valoreDellaMetrica, ETICHETTE, STEP_DEL_PRIOR } = dipendenze;

  let fronteMostrato = "";
  let ultimoModello = 0;

  function apriModello() {
    ultimoModello += 1;
    return ultimoModello;
  }

  async function aggiornaModello(steps) {
    const fronte = fronteDelloStato(steps, STEP_DEL_PRIOR);
    const chiave = chiaveDelFronte(fronte);
    if (chiave === fronteMostrato) return;
    fronteMostrato = chiave;
    // L'ordine si apre QUI, prima di ogni uscita anticipata, e non dentro il ramo
    // che chiede le metriche. Aperto la', il ramo del vuoto usciva senza
    // invalidare cio' che stava arrivando: il fronte spariva mentre una rilettura
    // era in volo, il pannello si svuotava, e la risposta vecchia lo ripopolava
    // con i numeri di un fronte che non c'era piu'. Peggio, il vuoto aveva gia'
    // segnato la propria terna, quindi ogni fotogramma successivo usciva subito e
    // quei numeri restavano li'. Stesso precedente di `chiediStorico`, dove
    // l'ordine si apre prima della prima attesa.
    const ordine = apriModello();
    const vuoto = document.getElementById("modello-vuoto");
    const righe = document.getElementById("modello-righe");
    const titolo = document.getElementById("modello-fronte");
    if (fronte === null) {
      titolo.textContent = "";
      vuoto.textContent = "Nessuno step valido: esegui lo step 1.";
      vuoto.hidden = false;
      righe.hidden = true;
      return;
    }
    let metriche;
    try {
      const risposta = await fetch("/api/metrics").catch(serverMuto);
      metriche = risposta.ok ? await corpoLetto(risposta) : null;
    } catch {
      // Non prudenza generica: `fronteMostrato` e' gia' scritto sopra, quindi
      // un rigetto qui (una risposta che solleva quando la si guarda, non il
      // rifiuto della fetch -- quello lo prende `serverMuto`) lascerebbe il
      // pannello con il contenuto vecchio e la terna nuova, e nessun
      // fotogramma successivo lo riparerebbe perche' la terna non cambia
      // piu'. Azzerarla riapre la strada al fotogramma dopo. Prima app.js
      // faceva questo dal `.catch` su `aggiornaModello(steps)`: la terna e'
      // privata di questo modulo, quindi il ripiego trasloca qui dentro.
      fronteMostrato = "";
      return;
    }
    if (superata(ordine, ultimoModello)) return;
    titolo.textContent = `dopo lo step ${fronte.numero}, ${ETICHETTE[fronte.chiave] ?? fronte.chiave}`;
    if (metriche === null || typeof metriche !== "object") {
      vuoto.textContent = "metriche non leggibili";
      vuoto.hidden = false;
      righe.hidden = true;
      return;
    }
    righe.replaceChildren(...righeDelModello(fronte, metriche, valoreDellaMetrica).flatMap(([etichetta, testo, allarme]) => {
      const dd = elemento("dd", { textContent: testo });
      // Lo stesso marchio della colonna del dettaglio, e per lo stesso motivo:
      // una mesh troncata in silenzio non sta fra righe che si somigliano. Chi
      // guarda questo pannello non sta guardando l'altra colonna.
      if (allarme) dd.classList.add("metrica-avviso");
      return [elemento("dt", { textContent: etichetta }), dd];
    }));
    vuoto.hidden = true;
    righe.hidden = false;
  }

  return { aggiornaModello };
}
