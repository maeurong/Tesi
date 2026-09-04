// Scena tridimensionale. Disegna cio' che il server manda, non ricalcola nulla.
import * as THREE from "/ui/vendor/three.module.min.js";

// Il taglio della scala colore di un campo per nodo: al p99, non al massimo.
// Il maglio dell'as-built ha una singolarita' di geometria che tiene il
// massimo su un solo nodo, non su un plateau: misurato il 22/08/2026 sui tre
// casi di runs/lab_telaio_v2, max/p99 vale 2,18 (GRAVITA) / 2,50
// (SPINTA_ORIZZONTALE) / 2,48 (CARICO_TOP) -- p99 al rango piu' vicino sui
// 10.968 nodi del contorno, cioe' esattamente cio' che scalaDelCampo calcola,
// non np.percentile sui 14.103 del volume, che da' 2,16 / 2,54 / 2,50 ed e' il
// numero di controlla_picco e del documento di fase -- e il picco resta lo stesso
// nodo, il 7132 del contorno. Una scala tirata su quel massimo
// schiaccerebbe tutto il resto del pezzo in un solo colore, mostrando
// l'artefatto come se fosse il risultato. Pura e fuori da mostraMeshPerCampo
// apposta: e' una decisione numerica, e questo progetto la prova eseguendola
// in node, non cercandola come sottostringa in una funzione che tocca three.js.
//
// sopraTaglio conta per valore (`v > taglio`), non per rango: `n - 1 - indice`
// e' una quota fissa, e su un campo costante o tutto a zero dichiarava cinque
// nodi sopra una soglia che nessuno supera - lo stesso testo che finisce
// nell'aria-label. Il server non conta piu' niente di suo: X-Sopra-P99 e le
// altre due intestazioni sono state tolte in f7190bb, e questo e' l'unico
// posto in cui il conteggio esiste.
export function scalaDelCampo(valori) {
  const finiti = [];
  for (let indice = 0; indice < valori.length; indice += 1) {
    if (Number.isFinite(valori[indice])) finiti.push(valori[indice]);
  }
  // NaN/Infinity ovunque: nessun valore su cui tagliare. 0 e' leggibile,
  // un taglio NaN in silenzio no.
  if (finiti.length === 0) return { taglio: 0, sopraTaglio: 0 };
  finiti.sort((a, b) => a - b);
  const n = finiti.length;
  const indice = Math.max(0, Math.ceil(n * 0.99) - 1);
  const taglio = finiti[indice];
  return { taglio, sopraTaglio: finiti.filter((v) => v > taglio).length };
}

// Dove sta un valore sulla rampa, fra 0 (chiaro) e 1 (scuro). Fuori da
// mostraMeshPerCampo per la stessa ragione di scalaDelCampo: sono le due
// guardie del colore, e dentro una funzione che costruisce materiali three.js
// nessun test le esegue - restavano provate a sottostringa, cioe' non provate.
// Un campo costante o tutto a zero non deve dividere per zero: la scala resta
// un solo colore, non un crash ne' un taglio NaN che la renderebbe
// silenziosamente uniforme. Un residuo NaN/Infinity fra i valori resta al
// fondo della scala, dichiarato zero, e non tocca il colore di nessun altro
// nodo.
export function frazioneDelCampo(valore, taglio) {
  const soglia = taglio > 0 ? taglio : 1;
  return Number.isFinite(valore) ? Math.min(1, Math.max(0, valore / soglia)) : 0;
}

// I due estremi della rampa sequenziale, in un posto solo.
//
// Esportati perche' la chiave che sta sotto la vista li deve disegnare uguali:
// scritti due volte -- un esadecimale qui per three.js e un colore nel foglio
// per il gradiente -- il giorno che uno dei due cambia la legenda dichiara una
// scala che il pezzo non ha, ed e' il difetto peggiore possibile su un colore
// che porta una misura.
//
// Stringhe e non numeri: THREE.Color le legge come gli esadecimali, e CSS pure.
// Lo scuro e' --accento, la stessa tinta della nuvola.
export const RAMPA = { chiaro: "#d9e8e4", scuro: "#2f5d50" };

// Quale asse del mondo chiede il gesto, o null per l'orbita libera di sempre.
//
// Assi del MONDO e non del pezzo: dopo una rotazione attorno a z, l'x del
// modello e' inclinato sullo schermo, e `ctrl` smetterebbe di voler dire sempre
// la stessa direzione. Cosi' invece ctrl e' x oggi e x dopo dieci trascinamenti.
//
// Priorita' dichiarata e non «piu' di un modificatore = orbita libera»: le
// combinazioni si premono per sbaglio, e un gesto che cade nell'orbita libera
// proprio quando l'utente sta cercando di vincolarlo e' il contrario di cio'
// che il vincolo serve a dare. L'ordine e' quello in cui i tre sono stati
// chiesti -- alt, ctrl, shift -- e non c'e' un ordine piu' giusto: c'e' un
// ordine, ed e' provato.
//
// cmd vale quanto ctrl: su macOS ctrl+clic e' il clic destro, e la mano che
// vuole vincolare un asse cerca il tasto accanto alla barra, che li' e' cmd.
// Questo progetto sta anche su macOS (gestoDelloStorico in app.js paga la
// stessa ragione).
//
// Pura e fuori da creaViewport per la ragione gia' pagata da scalaDelCampo:
// dentro una funzione che tocca three.js nessun banco la eseguirebbe.
export function asseDelGesto(evento) {
  if (evento.altKey) return [0, 0, 1];
  if (evento.ctrlKey || evento.metaKey) return [1, 0, 0];
  if (evento.shiftKey) return [0, 1, 0];
  return null;
}

// Di quanto la rotella chiede di avvicinare o allontanare: un fattore sul
// raggio dell'orbita, maggiore di 1 per allontanare.
//
// Proporzionale al delta e non fisso per evento. Era 1,1 per ogni evento, e
// una tacca del mouse e un colpetto del trackpad valevano uguale; il trackpad
// di un Mac ne manda decine per gesto, di pochi pixel l'uno, e una sola
// carezza a due dita moltiplicava il raggio per 1,1 trenta volte, cioe' per
// 17: la scena spariva. Qui una tacca di mouse (deltaY 100 in pixel) vale
// exp(0,1) = 1,105, quanto prima, e trenta colpetti da 3 px valgono
// exp(0,09) = 1,09: un gesto, uno scatto. Il pizzico a due dita arriva dallo
// stesso evento, con ctrlKey, e non ha bisogno di un ramo suo. deltaMode 1 e
// 2 sono righe e pagine, che Firefox manda con certe impostazioni: 16 px e
// 400 px per unita'. Il limite a una tacca per evento tiene a bada un delta
// anomalo, che altrimenti sarebbe un salto di scala in un colpo.
export function fattoreDiZoom(evento) {
  const perUnita = evento.deltaMode === 1 ? 16 : evento.deltaMode === 2 ? 400 : 1;
  const delta = Math.max(-100, Math.min(100, evento.deltaY * perUnita));
  return Math.exp(delta / 1000);
}

// Ogni numero che finisce a video passa di qui, e null e' «non si puo'
// scrivere»: chi chiama sceglie la frase, non stampa NaN. Cifre significative
// e non decimali fissi perche' gli spostamenti veri sono submillimetrici
// (0,0367 mm, misurato) e quattro decimali spostano la soglia di tre ordini
// invece di toglierla: 2e-5 mm si legge ancora "0". I conteggi di nodi non
// sono misure e passano di qui con il proprio formato, altrimenti 13 957 nodi
// diventerebbero 13 960.
export function numeroDelCampo(valore, formato = { maximumSignificantDigits: 4 }) {
  return Number.isFinite(valore) ? valore.toLocaleString("it", formato) : null;
}

// Che cosa si sta guardando quando la superficie porta il proprio scarto, e
// soprattutto che cosa NON si sta guardando.
//
// Il limite non e' prudenza generica. `quality.vertex_deviation` campiona i
// SOLI vertici, nel verso dalla superficie alla nuvola: dove la superficie
// sbaglia FRA un vertice e l'altro questa mappa non lo vede, e la tabella
// accanto porta anche cloud_to_mesh, che e' il verso opposto e da' un numero
// piu' grande (4,897 mm contro 3,898 su lab_crop). Sta nella didascalia e non
// solo in un commento perche' l'immagine finisce in appendice a un documento
// stampato, staccata dalla tabella: deve reggersi da sola.
export function didascaliaDelloScarto({ massimo, taglio, sopraTaglio }) {
  const tagliato = numeroDelCampo(taglio);
  const vertici = numeroDelCampo(sopraTaglio, { maximumFractionDigits: 0 });
  const scala = tagliato === null || vertici === null
    ? "scala non disponibile, il campo non ha valori leggibili"
    : `scala tagliata a ${tagliato} mm (p99), ${vertici} vertici sopra`;
  const limite = "misurato sui soli vertici, nel verso dalla superficie alla nuvola";
  const scritto = numeroDelCampo(massimo);
  if (scritto === null) {
    return `scarto dalla nuvola: ${scala}; massimo non disponibile — ${limite}`;
  }
  const fuori = Number.isFinite(massimo) && Number.isFinite(taglio) && massimo > taglio;
  return `scarto dalla nuvola: ${scala}; massimo ${scritto} mm`
    + (fuori ? ", fuori scala" : "") + ` — ${limite}`;
}

// Che cosa si sta guardando, sempre accanto alla vista: un'immagine di
// spostamento e una forma modale si confondono a colpo d'occhio - la Fase 5 ha
// gia' pagato l'errore di una von Mises calcolata su una forma modale (fino a
// 88,5 MPa, privi di senso: una forma e' normalizzata sulla massa, non uno
// spostamento fisico).
// Una frase sola, e non due paragrafi: il taglio della scala e il massimo
// erano su due righe separate a mezzo schermo di distanza dalla vista, e
// l'occhio mappava la macchia piu' scura sul massimo. Sotto peso proprio quel
// massimo vale 0,5056 MPa contro un taglio di 0,2321 (misurato il 22/08/2026
// su runs/lab_telaio_v2, sul contorno che il browser colora): una sovrastima
// di 2,18 volte, e proprio sul
// nodo-scheggia che il documento spende una sezione a rinnegare. Accostati
// nella stessa frase, e col massimo marcato quando sta oltre il taglio, i due
// numeri si leggono per quello che sono.
// --- L'arrivo ---------------------------------------------------------------
//
// Il movimento della vista, e ce n'e' uno solo: l'arrivo di una geometria
// nell'inquadratura. Ogni strada che disegna passa da inquadra() -- mostraNuvola,
// mostraMesh, mostraMeshPerCampo -- quindi il movimento sta li' dentro e non in
// tre copie da tenere allineate.
//
// Che cosa dice, perche' non e' una rifinitura. Fra lo step 5, il 6 e il 9 si
// guarda lo stesso pezzo tre volte, e le tre superfici si somigliano: sostituite
// in un fotogramma, una vista nuova e' indistinguibile da una vista che non e'
// cambiata. E' la stessa ambiguita' che il marchio sullo step aperto chiude
// dall'altra parte della finestra -- «si modifica il parametro di uno credendo
// di essere su un altro» -- e qui non la chiudeva nessuno. La comparsa dichiara
// che cio' che si guarda e' arrivato adesso; l'inquadratura che si assesta
// invece di saltare dice che e' lo stesso pezzo misurato da un'altra parte, non
// un pezzo diverso. Toglierle, si perde quella distinzione, non un effetto.
//
// Una durata sola, e in un posto solo: la comparsa della tela e lo spostamento
// della camera sono lo stesso movimento, e due numeri sarebbero due movimenti
// che invecchiano separati. Sta qui e non fra le durate di stile.css perche' e'
// la camera a leggerla, e un valore scritto in CSS e riletto da JS sarebbe la
// stessa duplicazione al contrario.
export const DURATA_ARRIVO = 400;

// Dove sta l'arrivo, fra 0 (l'inquadratura di prima) e 1 (quella nuova).
// Pura e fuori da creaViewport per la ragione gia' pagata da scalaDelCampo e
// frazioneDelCampo: dentro una chiusura che tocca three.js e
// requestAnimationFrame nessun banco la esegue, e resterebbe provata cercando
// una sottostringa.
//
// Chiusa a 1, e a 1 esatto quando il tempo e' scaduto: chi chiama smonta la
// transizione su questo confronto, e una frazione che si ferma a 0,999 la
// lascerebbe accesa per sempre -- un aggiornaCamera in piu' a ogni fotogramma
// per tutta la sessione, su una pagina che resta aperta per ore. Una durata
// nulla o un trascorso non finito valgono 1 e non NaN: un NaN moltiplicato per
// il raggio porta la camera in una posizione che non esiste, e la scena
// sparisce senza che niente lo dica.
export function frazioneDellArrivo(trascorso, durata = DURATA_ARRIVO) {
  if (!(durata > 0) || !Number.isFinite(trascorso)) return 1;
  const quota = Math.min(1, Math.max(0, trascorso / durata));
  // Decelerazione e nient'altro: l'inquadratura arriva e si posa. E' la gemella
  // in cifre di cubic-bezier(0.16, 1, 0.3, 1), la --curva del foglio di stile;
  // una curva elastica qui farebbe oltrepassare l'ingombro e tornare indietro,
  // cioe' mostrerebbe un pezzo piu' grande di quello che e'.
  return 1 - (1 - quota) ** 5;
}

// --- Il giro completo -------------------------------------------------------
//
// L'elevazione correva fra 0,01 e pi greco meno 0,01: un fermo appena prima dei
// due poli, e arrivati li' il trascinamento non muoveva piu' niente. Ogni lato
// del pezzo restava raggiungibile -- l'azimut non ha fermi -- ma il gesto si
// bloccava senza dire perche', e un gesto che si blocca in silenzio si legge
// come un guasto, non come un limite.
//
// Adesso phi corre come theta e si continua oltre il polo. Il prezzo e' che di
// la' dal polo il mondo e' capovolto: passato pi greco il seno di phi diventa
// negativo, la posizione si specchia sull'azimut opposto, e con `up` fermo a
// +Y l'immagine si ribalterebbe di scatto. `up` segue il segno del seno (vedi
// aggiornaCamera), che e' esattamente cio' che scavalcare un polo fa
// all'orizzonte: per chi guarda il movimento resta continuo.
//
// I due poli esatti si scavalcano e non si toccano. La' la camera sta
// sull'asse e `up` le e' parallelo: `lookAt` produce NaN, la camera esce dal
// mondo e la scena sparisce senza un errore in console. Non e' un caso di
// scuola -- phi nasce a 1,0 e la freccia in su lo scala di 0,1, quindi dieci
// battute arrivano esattamente a zero. Il salto e' un millesimo di radiante,
// cioe' sei centesimi di grado: non si vede.
//
// Prende l'elevazione di adesso e il passo, non il risultato gia' sommato: il
// segno del passo e' il verso del gesto, ed e' l'unica cosa che dice da che
// parte uscire quando si finisce sopra un polo. Uscire «dal lato piu' vicino»
// senza saperlo rimanderebbe indietro chi sta arrivando, cioe' fermerebbe il
// gesto proprio dove questa correzione esiste per non fermarlo.
//
// La fascia si misura per distanza e non per uguaglianza, e la differenza non e'
// formale: il modulo non restituisce mai pi greco esatto -- 3*pi greco meno
// 2*pi greco vale pi greco piu' 4e-16 -- quindi un `=== Math.PI` non
// riconoscerebbe il polo raggiunto girando. E non serve che sia esatto per fare
// danno: a 4e-16 dall'asse il prodotto vettoriale con `up` e' lungo 1e-31, e
// normalizzarlo amplifica il solo errore di arrotondamento.
//
// Pura e di primo livello come frazioneDellArrivo, e senza costanti di modulo:
// dentro la chiusura che tocca three.js nessun banco la eseguirebbe, e con le
// costanti qui dentro il banco non deve ricostruire niente.
function oltreIlPolo(phi, passo) {
  const giro = Math.PI * 2;
  const scarto = 1e-3;
  const chiudi = (valore) => ((valore % giro) + giro) % giro;
  const grezzo = chiudi(phi + passo);
  // Tre poli e non due: 0 e il giro intero sono lo stesso punto, e la fascia
  // attorno a ciascuno va guardata dalla propria parte.
  for (const polo of [0, Math.PI, giro]) {
    if (Math.abs(grezzo - polo) < scarto) return chiudi(polo + (passo >= 0 ? scarto : -scarto));
  }
  return grezzo;
}

// Le normali: quelle che il server manda, o quelle che il browser si calcola.
//
// `computeVertexNormals` gira sul thread principale, e finche' dura e' ferma
// la pagina intera -- non solo la vista. Misurato qui dentro il 04/09/2026 su
// 908.118 triangoli, il conteggio che l'aiuto dello step 5 cita per la
// scansione di riferimento a `poisson_depth` 9: mediano di sette prove,
// 1078 ms. Adesso quel calcolo lo fa il server in numpy e le manda in coda al
// corpo (`viewport.vertex_normals`, replica riga per riga di questo stesso
// algoritmo di three.js), quindi di la' non resta niente da fare.
//
// Il ripiego non e' cortesia verso un server vecchio: e' la sola strada per un
// chiamante che le normali non le ha, come `mostraFantasma` sul fantasma di uno
// step a monte, che riceve la geometria da una risposta gia' consumata. Dove
// arrivano si usano, dove non arrivano si calcolano, e in nessuno dei due casi
// la scena e' diversa -- e' la stessa definizione applicata dalle due parti.
function posaLeNormali(geometria, normali) {
  if (normali) geometria.setAttribute("normal", new THREE.BufferAttribute(normali, 3));
  else geometria.computeVertexNormals();
}

export function creaViewport(contenitore) {
  const scena = new THREE.Scene();
  scena.background = new THREE.Color(0xfbfaf8);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1e6);
  camera.position.set(1, 1, 1);

  // preserveDrawingBuffer: senza, il canvas e' vuoto al momento in cui lo si
  // legge, perche' il browser lo azzera dopo la presentazione.
  // ponytail: il flag e cattura() qui sotto sono meta' di una funzione. Il
  // consumatore esiste gia' — report._sezione_viste incorpora i PNG delle
  // viste e _conteggio_viste ne dichiara «0 attese» — ma nessuno collega le
  // due meta': non c'e' un comando che chiami cattura() ne' un endpoint che
  // riceva il PNG. Restano perche' sono il solo produttore possibile di
  // quell'artefatto; il giorno che il report resta senza viste, il chiamante
  // va scritto qui e non altrove.
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = true;

  // Il taglio: un solo piano, e un solo elenco condiviso da tutti i materiali.
  // Condividere l'elenco invece di ripercorrere il gruppo a ogni comando chiude
  // il caso della geometria che entra dopo: un materiale nuovo riceve lo stesso
  // elenco e nasce gia' tagliato, percio' la vista non puo' contraddire il
  // comando. three.js ricompila da se' quando cambia il numero di piani.
  const pianoTaglio = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);
  const pianiTaglio = [];
  // Che cosa il comando del taglio ha chiesto, in coordinate del MODELLO.
  //
  // Serve perche' il piano non e' piu' scritto una volta sola: three.js tiene i
  // piani di taglio nel mondo, e il modello adesso puo' girare sotto di loro.
  // Ricostruirlo a ogni rotazione da (asse, quota) e' l'unico modo perche' il
  // taglio resti quello che il menu dichiara; tenendolo fermo nel mondo il
  // cursore avrebbe una corsa presa da un ingombro che non e' piu' quello, e la
  // sezione a video mostrerebbe una quota che nessuno ha chiesto.
  let tagliaAttivo = null;

  // Appoggi del giro, creati una volta: ruotaIlModello gira a ogni pointermove,
  // cioe' decine di volte per trascinamento, e allocare li' e' la stessa spesa
  // che il resto di questo file evita gia'.
  const asseDelGiro = new THREE.Vector3();
  const giro = new THREE.Quaternion();
  const perno = new THREE.Vector3();
  const pernoRuotato = new THREE.Vector3();

  // Il canvas non ha testo proprio: senza un'alternativa, chi usa uno
  // screen reader vede un buco muto. L'aria-label aggiornato ad ogni disegno
  // da' il contenuto testuale equivalente; tabindex lo rende raggiungibile da
  // tastiera. Il ruolo e' "application" e non "img" perche' la tela si comanda
  // davvero dalla tastiera: "img" la annuncerebbe come figura ferma e lo
  // screen reader intercetterebbe le frecce invece di passarle qui.
  const COMANDI = "frecce per ruotare, più e meno per lo zoom";
  const tela = renderer.domElement;
  tela.setAttribute("role", "application");
  tela.setAttribute("tabindex", "0");
  function descrivi(contenuto) {
    tela.setAttribute("aria-label", `Vista tridimensionale: ${contenuto}. Comandi: ${COMANDI}.`);
  }
  descrivi("vuota");
  contenitore.append(tela);

  const gruppo = new THREE.Group();
  scena.add(gruppo);

  // Il box di ritaglio: uno solo, tenuto in una variabile di chiusura come
  // pianoTaglio e non su this, perche' svuota() deve poterlo azzerare quando
  // libera la geometria. Sta dentro il gruppo apposta: cosi' la stessa
  // traversata che libera nuvola e mesh libera anche lui.
  let box = null;

  // Il fantasma: la geometria del passaggio a monte, disegnata insieme a quella
  // corrente e quasi trasparente. Passando da uno step al successivo si riparte
  // da zero — la vista si riassesta, i conteggi si riscrivono — e cio' che il
  // passaggio ha TOLTO non si vede da nessuna parte: si legge un numero prima e
  // un numero dopo, mai le due geometrie insieme. Sovrapporle e' l'unico modo
  // di vedere che cosa un passaggio ha tolto mentre lo si guarda.
  //
  // In `scena` e non dentro `gruppo`: `gruppo` e' cio' che scatolaDelGruppo()
  // misura, e da li' il fantasma allargherebbe l'ingombro su cui si fissano
  // l'inquadratura e l'intervallo del cursore del taglio. Fuori da `gruppo`
  // l'ingombro resta quello della sola geometria corrente senza che quella
  // funzione debba sapere che il fantasma esiste.
  let fantasma = null;

  scena.add(new THREE.AmbientLight(0xffffff, 0.7));
  const direzionale = new THREE.DirectionalLight(0xffffff, 0.8);
  scena.add(direzionale);
  // Il bersaglio va aggiunto alla scena, non basta spostarlo: una
  // DirectionalLight punta da `position` verso `target.position`, e un target
  // che non sta nel grafo non viene aggiornato dal render -- il suo
  // matrixWorld resterebbe quello con cui e' nato.
  scena.add(direzionale.target);

  // Due vettori d'appoggio tenuti qui e non dentro aggiornaCamera: quella gira
  // a ogni pointermove, cioe' decine di volte per ogni trascinamento.
  const _destra = new THREE.Vector3();
  const _alto = new THREE.Vector3();

  let orbita = { theta: 0.7, phi: 1.0, raggio: 1, centro: new THREE.Vector3() };

  // L'arrivo in corso, o null. Vedi DURATA_ARRIVO. disegna() lo guarda a ogni
  // fotogramma: fuori da un arrivo il ciclo di disegno paga un confronto.
  let transizione = null;
  // La prima inquadratura non ha un «da»: orbita nasce con raggio 1 e centro
  // all'origine, e interpolare da li' sarebbe una picchiata da un millimetro
  // fino a qualche metro -- un movimento che non racconta nessun cambiamento,
  // perche' prima non c'era niente da cambiare. Non si azzera in svuota():
  // svuotare e ridisegnare e' proprio la sostituzione che l'assestamento deve
  // rendere leggibile.
  let inquadratoUnaVolta = false;
  // Interrogata a ogni arrivo e non copiata all'avvio: la preferenza di sistema
  // si cambia mentre la pagina e' aperta, e una copia resterebbe indietro.
  const menoMovimento = window.matchMedia?.("(prefers-reduced-motion: reduce)") ?? null;
  let comparsaDellaTela = null;

  // La comparsa: la tela intera, non i materiali. Con transparent e
  // side: DoubleSide three.js disegna le due facce nell'ordine di costruzione e
  // non di profondita', e un pezzo che compare mostrando il proprio interno e'
  // un difetto, non una comparsa. Sotto la tela c'e' --sfondo, che e' anche lo
  // sfondo della scena (0xfbfaf8 qui sopra): cio' che si vede durante la
  // comparsa e' la stessa carta, non un buco. I conteggi, il comando del taglio
  // e la didascalia sono fratelli della tela e non figli: non sfarfallano.
  //
  // Resta accesa anche a movimento ridotto: e' un'opacita' e non uno
  // spostamento, ed e' l'unico canale che dichiara «questa e' una vista nuova»
  // a chi ha appena ricevuto il salto d'inquadratura invece dell'assestamento.
  function comparsa() {
    comparsaDellaTela?.cancel();
    comparsaDellaTela = tela.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: DURATA_ARRIVO, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
  }

  // Il gesto vince sull'arrivo. Senza, chi trascina mentre l'inquadratura si
  // assesta comanda una camera che il fotogramma dopo viene riscritta
  // dall'interpolazione: due mani sullo stesso volante, e la vista torna
  // indietro a ogni fotogramma finche' l'arrivo non e' finito.
  function laCameraPassaAlGesto() {
    transizione = null;
  }

  function ridimensiona() {
    const larghezza = contenitore.clientWidth || 1;
    const altezza = contenitore.clientHeight || 1;
    // Il terzo argomento di setSize e' updateStyle, e va lasciato al suo
    // valore vero. Con false three.js dimensiona il buffer di disegno a
    // larghezza * pixelRatio ma non scrive la misura in CSS, e la tela viene
    // impaginata alla dimensione del buffer: su uno schermo con
    // devicePixelRatio 1,25 una tela di 881x576 si impagina 1101x720, esce
    // dal contenitore e lo fa scorrere, tagliando la scena. Misurato nel
    // browser, non dedotto.
    renderer.setSize(larghezza, altezza);
    camera.aspect = larghezza / altezza;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(ridimensiona).observe(contenitore);

  function aggiornaCamera() {
    const { theta, phi, raggio, centro } = orbita;
    camera.position.set(
      centro.x + raggio * Math.sin(phi) * Math.cos(theta),
      centro.y + raggio * Math.cos(phi),
      centro.z + raggio * Math.sin(phi) * Math.sin(theta),
    );
    // Scritto prima di lookAt, che lo legge. Vedi oltreIlPolo: oltre il polo il
    // seno di phi e' negativo e l'alto del mondo e' dall'altra parte. Senza
    // questa riga il giro resta possibile ma l'immagine si capovolge di scatto
    // nel punto esatto in cui il gesto dovrebbe essere piu' continuo.
    camera.up.set(0, Math.sin(phi) >= 0 ? 1 : -1, 0);
    camera.lookAt(centro);

    // La luce segue la camera, e non e' una rifinitura. Ferma nel mondo
    // (com'era, a (1, 2, 3)) lasciava senza rilievo tutto il lato opposto:
    // li' la superficie riceveva solo l'ambiente e diventava una sagoma grigia
    // uniforme, in cui la forma non si legge. Misurato nel browser il
    // 24/08/2026 girando attorno al telaio di lab_crop -- mezzo giro, e la
    // figura e' piatta come un ritaglio di carta.
    //
    // Scostata in alto e a destra, non esattamente sull'occhio: una luce
    // sull'asse dello sguardo illumina di fronte e non lascia ombre, che e'
    // lo stesso difetto per un'altra strada. Le due frazioni del raggio sono
    // una direzione, non una distanza: una direzionale non ha decadimento, e
    // conta solo da che parte arriva.
    camera.updateMatrixWorld();
    _destra.setFromMatrixColumn(camera.matrixWorld, 0);
    _alto.setFromMatrixColumn(camera.matrixWorld, 1);
    direzionale.position.copy(camera.position)
      .addScaledVector(_destra, raggio * 0.6)
      .addScaledVector(_alto, raggio * 0.4);
    // Il centro dell'orbita e non l'origine del mondo: il modello sta a
    // qualche metro dall'origine (lab_crop e' fra 1697 e 4457 mm in X), e una
    // direzionale puntata all'origine lo illuminerebbe di taglio.
    direzionale.target.position.copy(centro);
    direzionale.target.updateMatrixWorld();
  }

  // Il piano di taglio come sta nel mondo adesso: costruito in coordinate del
  // modello e portato di la' dalla matrice del gruppo. `applyMatrix4` e' di
  // three.js e fa gia' la cosa giusta anche alla normale -- riscriverla a mano
  // qui sarebbe matematica che la libreria possiede.
  //
  // Da capo ogni volta e non accumulando: applicata due volte alla stessa
  // istanza, la matrice ruoterebbe un piano gia' ruotato.
  function riscriviIlPiano() {
    if (tagliaAttivo === null) return;
    const { asse, quota } = tagliaAttivo;
    pianoTaglio.normal.set(asse === 0 ? 1 : 0, asse === 1 ? 1 : 0, asse === 2 ? 1 : 0);
    pianoTaglio.constant = -quota;
    pianoTaglio.applyMatrix4(gruppo.matrixWorld);
    pianiTaglio[0] = pianoTaglio;
  }

  // Gira il modello su se' stesso, attorno a un asse del mondo.
  //
  // Il perno e' `orbita.centro` e non l'origine: il gruppo non ha posizione
  // propria, quindi `rotateOnWorldAxis` girerebbe attorno all'origine del
  // mondo -- e il pezzo non ci sta sopra. Sulla scansione di riferimento vive
  // fra x = 1,697 e x = 4,456: attorno all'origine il gesto lo scaglierebbe
  // fuori campo invece di girarlo dov'e'.
  //
  // La forma e' quella della rotazione attorno a un perno, p' = R(p - c) + c,
  // che sul gruppo si scrive come quaternione R e posizione c - R·c.
  // `premultiply` e non `multiply`: il giro nuovo va applicato DOPO quelli
  // gia' fatti, cioe' nel mondo, ed e' esattamente la differenza fra un asse
  // del mondo e un asse del pezzo.
  function ruotaIlModello(asse, angolo) {
    giro.setFromAxisAngle(asseDelGiro.set(asse[0], asse[1], asse[2]), angolo);
    gruppo.quaternion.premultiply(giro);
    perno.copy(orbita.centro);
    pernoRuotato.copy(perno).applyQuaternion(gruppo.quaternion);
    gruppo.position.copy(perno).sub(pernoRuotato);
    gruppo.updateMatrixWorld(true);
    riscriviIlPiano();
  }

  let premuto = false;
  let premutoConCtrl = false;
  let ultimo = { x: 0, y: 0 };
  // I puntatori giu' in questo momento -- `puntatori` e non `dita`, perche' qui
  // dentro finisce anche il mouse: ogni `pointerdown` ci passa, e il nome deve
  // dire che cosa la mappa contiene e non il caso per cui e' stata scritta.
  // Col mouse ce n'e' sempre uno solo e questa mappa non cambia niente; col
  // dito ce ne possono essere due o piu', ed e' l'unico modo di sapere che il
  // gesto in corso e' una pinza e non una rotazione. `pointerId` come chiave
  // perche' e' cio' che il browser promette stabile per la vita di un
  // puntatore sullo schermo.
  const puntatori = new Map();
  // Sotto questa distanza in pixel due puntatori non sono una pinza ma una
  // mis-lettura, e il rapporto fra le loro distanze e' un numero qualunque.
  const DISTANZA_MINIMA = 12;
  // La distanza fra i due diti all'ultimo fotogramma: null quando i diti non
  // sono due, cosi' la pinza riparte pulita ogni volta invece di ereditare la
  // distanza di una pinza di prima.
  let pinza = null;

  const distanzaFraIPrimiDue = () => {
    const [a, b] = [...puntatori.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  };

  tela.addEventListener("pointerdown", (evento) => {
    puntatori.set(evento.pointerId, { x: evento.clientX, y: evento.clientY });
    // Il secondo dito chiude la rotazione invece di continuarla: senza,
    // appoggiando il secondo dito il modello scatterebbe di un mezzo giro,
    // perche' `ultimo` resterebbe la posizione del primo mentre i pointermove
    // cominciano ad arrivare anche dall'altro.
    premuto = puntatori.size === 1;
    pinza = puntatori.size === 2 ? distanzaFraIPrimiDue() : null;
    premutoConCtrl = evento.ctrlKey;
    ultimo = { x: evento.clientX, y: evento.clientY };
    tela.setPointerCapture(evento.pointerId);
  });
  const alzato = (evento) => {
    puntatori.delete(evento.pointerId);
    pinza = null;
    // Tolto un dito da una pinza ne resta uno solo, e da li' il gesto e' di
    // nuovo una rotazione: riparte dalla posizione di quel dito, non da dove
    // stava il primo prima della pinza.
    if (puntatori.size === 1) {
      const [restante] = [...puntatori.values()];
      ultimo = { x: restante.x, y: restante.y };
      premuto = true;
    } else {
      premuto = false;
    }
  };
  tela.addEventListener("pointerup", alzato);
  // Il browser puo' togliere il puntatore alla tela senza un pointerup: un
  // menu che si apre, una finestra che prende il fuoco. Senza questa riga il
  // trascinamento interrotto cosi' restava «premuto», e la scena seguiva il
  // mouse a tasto alzato finche' non si cliccava di nuovo.
  tela.addEventListener("pointercancel", alzato);
  // Su macOS ctrl+clic e' il clic destro, e apriva il menu contestuale sopra
  // la tela proprio nel gesto che vincola a x. Si tace il menu solo con ctrl
  // premuto: il clic destro vero lo tiene, e con lui «Salva immagine con
  // nome» del browser. Il ctrl lo si legge dal pointerdown, che precede il
  // menu e riporta i modificatori su ogni motore; sul contextmenu che macOS
  // sintetizza dal ctrl+clic WebKit non lo ha sempre riportato.
  tela.addEventListener("contextmenu", (evento) => { if (evento.ctrlKey || premutoConCtrl) evento.preventDefault(); });
  tela.addEventListener("pointermove", (evento) => {
    if (puntatori.has(evento.pointerId)) {
      puntatori.set(evento.pointerId, { x: evento.clientX, y: evento.clientY });
    }
    // La pinza: due diti che si allontanano avvicinano il pezzo, ed e' lo
    // stesso verso della rotella. Il fattore e' il rapporto fra le due
    // distanze, quindi il pezzo segue i diti invece di scorrere a velocita'
    // propria -- allargando del doppio si dimezza il raggio, e riavvicinando
    // i diti si torna esattamente da dove si era partiti.
    if (puntatori.size >= 2) {
      const adesso = distanzaFraIPrimiDue();
      // `>= 2` e non `=== 2`: col terzo dito giu' -- un palmo appoggiato sul
      // vetro mentre si pizzica -- il ramo esatto non scattava e nemmeno
      // quello della rotazione, perche' `premuto` e' vero solo col primo dito
      // solo. L'interazione si fermava, senza niente a schermo che lo
      // dicesse, finche' non si staccava una mano. I diti oltre i primi due si
      // ignorano invece di bloccare tutto.
      //
      // Sotto i pochi pixel la distanza non e' un gesto ma una mis-lettura, e
      // un rapporto calcolato li' sopra e' un numero qualunque. Il tetto per
      // fotogramma e' la stessa difesa che `fattoreDiZoom` porta sulla
      // rotella, dove il limite al delta esiste per una scala saltata di
      // colpo: nessuna pinza vera cambia la distanza fra i diti di quattro
      // volte dentro un fotogramma, quindi il tetto non tocca il gesto e
      // prende solo il caso patologico. La proprieta' che conta -- il pezzo
      // segue i diti, e riavvicinandoli si torna da dove si era partiti --
      // resta intatta per ogni gesto che una mano possa fare.
      if (pinza !== null && adesso >= DISTANZA_MINIMA && pinza >= DISTANZA_MINIMA) {
        const fattore = Math.min(4, Math.max(0.25, pinza / adesso));
        laCameraPassaAlGesto();
        orbita.raggio *= fattore;
        aggiornaCamera();
      }
      pinza = adesso;
      return;
    }
    if (!premuto) return;
    laCameraPassaAlGesto();
    // Col modificatore conta il solo spostamento orizzontale: un asse, un
    // delta. E' il vincolo a rendere il gesto ripetibile -- con due gradi di
    // liberta' vivi insieme, inquadrare di preciso vuole mano ferma, ed e'
    // proprio quello che un'immagine da appendice non deve chiedere.
    const asse = asseDelGesto(evento);
    if (asse !== null) {
      ruotaIlModello(asse, (evento.clientX - ultimo.x) * 0.005);
    } else {
      orbita.theta -= (evento.clientX - ultimo.x) * 0.005;
      orbita.phi = oltreIlPolo(orbita.phi, -(evento.clientY - ultimo.y) * 0.005);
    }
    ultimo = { x: evento.clientX, y: evento.clientY };
    aggiornaCamera();
  });
  tela.addEventListener("wheel", (evento) => {
    evento.preventDefault();
    laCameraPassaAlGesto();
    orbita.raggio *= fattoreDiZoom(evento);
    aggiornaCamera();
  }, { passive: false });

  // Orbita anche da tastiera, per chi non usa il mouse: frecce per ruotare,
  // +/- per lo zoom. Stesso passo dei gesti col mouse, solo discretizzato.
  tela.addEventListener("keydown", (evento) => {
    const passi = {
      ArrowLeft: () => { orbita.theta -= 0.1; },
      ArrowRight: () => { orbita.theta += 0.1; },
      ArrowUp: () => { orbita.phi = oltreIlPolo(orbita.phi, -0.1); },
      ArrowDown: () => { orbita.phi = oltreIlPolo(orbita.phi, 0.1); },
      "+": () => { orbita.raggio *= 0.9; },
      "-": () => { orbita.raggio *= 1.1; },
    };
    const passo = passi[evento.key];
    if (!passo) return;
    evento.preventDefault();
    laCameraPassaAlGesto();
    passo();
    aggiornaCamera();
  });

  function disegna() {
    if (transizione !== null) {
      const frazione = frazioneDellArrivo(performance.now() - transizione.inizio);
      orbita.centro.lerpVectors(transizione.daCentro, transizione.aCentro, frazione);
      orbita.raggio = transizione.daRaggio + (transizione.aRaggio - transizione.daRaggio) * frazione;
      // Smontata sul confronto, non sul tempo: frazioneDellArrivo torna 1 esatto
      // a tempo scaduto apposta, e questa e' la riga che ci conta sopra.
      if (frazione >= 1) transizione = null;
      aggiornaCamera();
    }
    renderer.render(scena, camera);
    requestAnimationFrame(disegna);
  }
  ridimensiona();
  disegna();

  // L'ingombro della sola geometria. Il box di ritaglio sta dentro `gruppo`
  // perche' svuota() lo liberi con gli altri, ma `gruppo` e' anche cio' che
  // questa misura: contandolo, ingombro() smetterebbe di restituire l'ingombro
  // della geometria e restituirebbe l'unione con un rettangolo che l'utente
  // allarga a piacere, che poi taglia il cursore del taglio (Task 13) e
  // riprecompila i sei campi del ritaglio, allargandosi a ogni giro.
  // Escluso a mano e non con box.visible = false: Box3.expandByObject non
  // guarda `visible` (three.js r180), quindi nasconderlo non
  // toglierebbe niente dalla misura. Misurato in node, non dedotto.
  function scatolaDelGruppo() {
    const scatola = new THREE.Box3();
    for (const figlio of gruppo.children) {
      if (figlio !== box) scatola.expandByObject(figlio);
    }
    return scatola;
  }

  // Libera davvero, per la ragione scritta dentro svuota(): togliere un oggetto
  // dalla scena non cancella i suoi buffer, sono gli eventi di dispose a farlo.
  // Senza, ogni clic su uno step lascerebbe sulla scheda gli attributi del
  // fantasma di prima. Il riferimento azzerato e' cio' che impedisce di
  // perderne uno in scena sostituendolo col successivo.
  function togliFantasma() {
    if (fantasma === null) return;
    fantasma.geometry.dispose();
    fantasma.material.dispose();
    scena.remove(fantasma);
    fantasma = null;
  }

  function inquadra() {
    const scatola = scatolaDelGruppo();
    if (scatola.isEmpty()) return;
    const centro = scatola.getCenter(new THREE.Vector3());
    const raggio = scatola.getSize(new THREE.Vector3()).length() * 1.2;
    // Il salto resta dove l'assestamento non avrebbe niente da raccontare: alla
    // prima geometria, e a chi ha chiesto meno movimento. La comparsa qui sotto
    // vale in entrambi i casi -- l'informazione «questa e' una vista nuova» non
    // si toglie con lo spostamento, si porta su un altro canale.
    if (!inquadratoUnaVolta || menoMovimento?.matches) {
      orbita.centro.copy(centro);
      orbita.raggio = raggio;
      transizione = null;
      aggiornaCamera();
    } else {
      transizione = {
        daCentro: orbita.centro.clone(),
        daRaggio: orbita.raggio,
        aCentro: centro,
        aRaggio: raggio,
        inizio: performance.now(),
      };
    }
    inquadratoUnaVolta = true;
    comparsa();
  }

  return {
    svuota() {
      // Il fantasma e' del passaggio che si sta lasciando, e se ne va con lui.
      // In testa e non in fondo: ogni strada che disegna chiama svuota() due
      // volte -- una al caricamento e una prima di disegnare -- e cosi' la
      // seconda lo trova gia' tolto invece di lasciarlo sotto la geometria
      // nuova.
      togliFantasma();
      // Togliere un oggetto dalla scena non libera i suoi buffer: in three.js
      // sono gli eventi di dispose a cancellarli davvero (three.js r180,
      // onGeometryDispose, toglie l'indice e ogni attributo). Senza, ogni
      // passaggio fra lo step 5, il 6 e il 9 lasciava sul posto 7,6 MB di
      // attributi piu' un materiale, e il ciclo fra gli step e' un gesto che
      // si ripete.
      // Ogni oggetto ha il materiale che gli ha creato mostraNuvola o
      // mostraMesh, e nessun altro lo usa: liberarlo qui non lascia scoperto
      // nessuno.
      // pianiTaglio non si tocca: non e' una risorsa della scheda grafica ed
      // e' condiviso apposta perche' sopravviva alla geometria. Azzerarlo qui
      // farebbe nascere la geometria nuova senza taglio mentre il comando lo
      // dichiara attivo.
      gruppo.traverse((oggetto) => {
        oggetto.geometry?.dispose();
        oggetto.material?.dispose();
      });
      gruppo.clear();
      // La rotazione a mano se ne va con la geometria che descriveva.
      // Sopravvivendo a un ridisegno metterebbe a video -- e in appendice, che
      // e' dove queste immagini vanno a finire -- un orientamento che le
      // coordinate dell'artefatto nuovo non hanno, senza che niente lo dica.
      // La camera invece non si azzera: quella inquadra, non descrive il pezzo.
      gruppo.quaternion.identity();
      gruppo.position.set(0, 0, 0);
      gruppo.updateMatrixWorld(true);
      riscriviIlPiano();
      // Il box e' appena stato liberato dalla traversata qui sopra: tenerne il
      // riferimento lascerebbe mostraBox a riscrivere una geometria che non
      // esiste piu' sulla scheda.
      box = null;
      descrivi("vuota");
    },
    mostraNuvola(punti) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(punti, 3));
      const materiale = new THREE.PointsMaterial({
        size: 1.5, sizeAttenuation: false, color: 0x2f5d50, clippingPlanes: pianiTaglio,
      });
      gruppo.add(new THREE.Points(geometria, materiale));
      descrivi(`nuvola di ${(punti.length / 3).toLocaleString("it")} punti`);
      inquadra();
    },
    // Qui arrivano solo triangoli: l'unico .vtu servito e' tetraedrico, e
    // `_contorno_del_volume` (app/server.py) solleva su una griglia che non
    // porta celle "tetra".
    mostraMesh(vertici, facce, normali = null) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      posaLeNormali(geometria, normali);
      gruppo.add(new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
        color: 0xb8b2a7, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
        clippingPlanes: pianiTaglio,
      })));
      descrivi(`superficie di ${(facce.length / 3).toLocaleString("it")} facce`);
      inquadra();
    },
    // Il campo per nodo (spostamento o tensione equivalente) sopra la
    // superficie di contorno. La scala si taglia al p99 e non al massimo: su
    // un campo di tensione il rapporto fra i due vale 2,18 sotto peso proprio
    // e arriva a 2,50 sotto spinta orizzontale (misurato il 22/08/2026 sul
    // contorno di
    // runs/lab_telaio_v2), e una scala fino al massimo schiaccerebbe in fondo
    // i 10.968 nodi del contorno perche' uno solo sta in cima. Non
    // quattordicimila: 14.103 sono i nodi dell'intero volume, e qui arrivano
    // solo quelli che il contorno tocca. Chi supera il taglio prende un colore
    // dichiarato, e la didascalia dice dov'e' il taglio e quanti nodi sono
    // sopra: e' un'informazione, non un buco.
    //
    // descrizione: la stessa frase che finisce sotto la vista, cosi' chi
    // ascolta lo screen reader riceve il caso di carico, la grandezza, l'unita'
    // e i due numeri della scala invece di un conteggio di facce.
    mostraMeshPerCampo(vertici, facce, valori, { taglio, descrizione, normali = null }) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      posaLeNormali(geometria, normali);
      const colori = new Float32Array(valori.length * 3);
      // Sequenziale: una tinta sola, chiara verso scura al crescere del
      // valore. Non un arcobaleno che attraversa piu' tinte: una scala di
      // grandezza vuole un ordine che l'occhio legga come "quanto", non un
      // ciclo di colori che si legge come identita'. Chi e' al taglio o oltre
      // satura all'estremo scuro: e' il colore dichiarato di cui parla il
      // commento sopra, non una tinta in piu' da inventare.
      // I due estremi sono costanti e la rampa e' l'interpolazione fra loro:
      // il giro precedente ricostruiva la rampa da tinta+saturazione+chiarezza
      // con quattro costanti, e il suo estremo scuro finiva a 0x178264, che
      // non e' --accento (misurato in node, non dedotto).
      const CHIARO = new THREE.Color(RAMPA.chiaro);
      const SCURO = new THREE.Color(RAMPA.scuro);
      const colore = new THREE.Color();
      for (let indice = 0; indice < valori.length; indice += 1) {
        colore.lerpColors(CHIARO, SCURO, frazioneDelCampo(valori[indice], taglio));
        colore.toArray(colori, indice * 3);
      }
      geometria.setAttribute("color", new THREE.BufferAttribute(colori, 3));
      gruppo.add(new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
        vertexColors: true, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
        clippingPlanes: pianiTaglio,
      })));
      descrivi(descrizione);
      inquadra();
    },
    // Un metodo solo per nuvola e superficie: `facce` a null da' dei punti, e
    // le tre coppie del fantasma sono due nuvole e una superficie.
    //
    // NON chiama inquadra(): il fantasma sta a monte della geometria corrente e
    // per costruzione la contiene, quindi inquadrarlo allontanerebbe la camera
    // da cio' che si e' chiesto di vedere. E' anche il motivo per cui non entra
    // in `gruppo` (vedi dove `fantasma` e' dichiarato).
    //
    // depthWrite falso e non solo transparent: scrivendo nel buffer di
    // profondita' il velo nasconderebbe la geometria corrente nei punti in cui
    // le sta davanti, cioe' proprio dove serve leggere le due insieme.
    //
    // ponytail: il colore e' un esadecimale come gli altri di questo file
    // (mostraNuvola usa 0x2f5d50, mostraMesh 0xb8b2a7), quindi nessun controllo
    // sul foglio di stile lo raggiunge. Se i colori della scena passeranno ai
    // token CSS, questo passa con loro: non vale aprire quel cantiere per un
    // colore solo.
    mostraFantasma(vertici, facce = null, normali = null) {
      togliFantasma();
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      if (facce === null) {
        fantasma = new THREE.Points(geometria, new THREE.PointsMaterial({
          size: 1.5, sizeAttenuation: false, color: 0x9a5f4a,
          transparent: true, opacity: 0.15, depthWrite: false,
          clippingPlanes: pianiTaglio,
        }));
      } else {
        geometria.setIndex(new THREE.BufferAttribute(facce, 1));
        posaLeNormali(geometria, normali);
        fantasma = new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
          color: 0x9a5f4a, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
          transparent: true, opacity: 0.15, depthWrite: false,
          clippingPlanes: pianiTaglio,
        }));
      }
      scena.add(fantasma);
    },
    togliFantasma,
    inquadra,
    // L'ingombro di cio' che e' disegnato ora, nelle stesse unita' della
    // geometria (millimetri). Serve a chi comanda il taglio per fissare
    // l'intervallo del cursore su una lettura invece che su numeri scelti a
    // mano. null quando la scena e' vuota: non c'e' nessuna quota da scorrere.
    ingombro() {
      const scatola = scatolaDelGruppo();
      if (scatola.isEmpty()) return null;
      return { min: scatola.min.toArray(), max: scatola.max.toArray() };
    },
    // Il box di ritaglio disegnato sopra la nuvola, in millimetri come lei.
    // Un solo Box3Helper riusato: si ridisegna a ogni tasto premuto nei sei
    // campi, e crearne uno nuovo ogni volta lascerebbe sulla scheda la
    // geometria di quello di prima. three.js rilegge this.box a ogni
    // fotogramma (three.js r180, Box3Helper.updateMatrixWorld), quindi riscrivere
    // gli estremi basta e non serve ricostruire nulla.
    mostraBox(basso, alto) {
      if (box === null) {
        box = new THREE.Box3Helper(new THREE.Box3(), new THREE.Color(0xc4671b));
        gruppo.add(box);
      }
      box.box.set(new THREE.Vector3(...basso), new THREE.Vector3(...alto));
    },
    // asse: 0 per x, 1 per y, 2 per z. Resta visibile la meta' oltre la quota,
    // perche' three.js tiene i punti dove normale . punto + costante > 0.
    attivaTaglio(asse, quota) {
      tagliaAttivo = { asse, quota };
      riscriviIlPiano();
    },
    disattivaTaglio() {
      tagliaAttivo = null;
      pianiTaglio.length = 0;
    },
    cattura() {
      renderer.render(scena, camera);
      return tela.toDataURL("image/png");
    },
  };
}
