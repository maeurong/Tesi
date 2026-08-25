// Scena tridimensionale. Disegna cio' che il server manda, non ricalcola nulla.
import * as THREE from "/ui/vendor/three.module.js";

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
export function didascaliaDelCampo({ caso, grandezza, modale, frequenza, massimo, taglio, sopraTaglio }) {
  if (modale) {
    // Un modo oltre quelli calcolati non ha una frequenza nota: NaN.toFixed()
    // scriverebbe "NaN Hz" in silenzio, lo stesso guasto di un taglio muto.
    const hz = numeroDelCampo(frequenza, { maximumFractionDigits: 2 });
    // La vista di un modo e' il modello grigio e indeformato: mostraStep(13),
    // nessuna forma applicata alle posizioni. «Ampiezza arbitraria» annunciava
    // un'ampiezza che non e' a schermo, ed e' la stessa classe dell'«amplificato
    // ×1779» che questo ramo ha gia' pagato: la didascalia dice solo cio' che
    // la vista fa davvero.
    const coda = "la forma modale non è disegnata, la vista mostra il modello indeformato";
    return hz === null
      ? `${caso}: frequenza non disponibile; ${coda}`
      : `${caso} — ${hz} Hz: ${coda}`;
  }
  // «massimo reale» e non «massimo amplificato»: la vista non deforma nulla.
  // Il campo che arriva dal server e' una magnitudine per nodo, senza
  // direzione, e le posizioni restano quelle del contorno indeformato: una
  // didascalia che dichiarasse un'amplificazione starebbe scrivendo un numero
  // falso sopra un pezzo fermo.
  const spostamento = grandezza === "U";
  const nome = spostamento ? "spostamento" : "tensione equivalente";
  const unita = spostamento ? "mm" : "MPa";
  // Entrambi i numeri passano da numeroDelCampo, che dichiara quello che non
  // si puo' scrivere invece di stamparlo. Il conteggio ha il proprio formato:
  // e' un numero di nodi, non una misura, e non va arrotondato a cifre
  // significative.
  const tagliato = numeroDelCampo(taglio);
  const nodi = numeroDelCampo(sopraTaglio, { maximumFractionDigits: 0 });
  const scala = tagliato === null || nodi === null
    ? "scala non disponibile, il campo non ha valori leggibili"
    : `scala tagliata a ${tagliato} ${unita} (p99), ${nodi} nodi sopra`;
  const scritto = numeroDelCampo(massimo);
  if (scritto === null) return `${caso} — ${nome}: ${scala}; massimo non disponibile`;
  // «reale» resta solo sullo spostamento: e' la grandezza che si guarda su una
  // vista, ed e' li' che qualcuno potrebbe leggere il colore come una misura.
  // «fuori scala» solo quando lo e' davvero: su un campo costante il massimo
  // coincide col taglio, ed e' rappresentabile.
  const fuori = Number.isFinite(massimo) && Number.isFinite(taglio) && massimo > taglio;
  return `${caso} — ${nome}: ${scala}; massimo ${spostamento ? "reale " : ""}${scritto} ${unita}`
    + (fuori ? ", fuori scala" : "");
}

// --- L'arrivo ---------------------------------------------------------------
//
// Il movimento della vista, e ce n'e' uno solo: l'arrivo di una geometria
// nell'inquadratura. Ogni strada che disegna passa da inquadra() -- mostraNuvola,
// mostraMesh, mostraMeshPerCampo, mostraNuvolaPerMembratura -- quindi il
// movimento sta li' dentro e non in quattro copie da tenere allineate.
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

// --- I fermi del raggio -----------------------------------------------------
//
// Il raggio non aveva fermi: `raggio *= 0.9` ripetuto lo porta sotto il piano
// vicino della camera -- si finisce dentro il pezzo e non si torna indietro --
// e `*= 1.1` ripetuto lo porta oltre il piano lontano, dove il pezzo e' un
// punto. Nessuna delle due solleva, nessuna delle due lascia un segnale: la
// scena si svuota e sembra un guasto del programma.
//
// I due fermi sono relativi all'ingombro inquadrato e non assoluti, perche' un
// millimetro e' vicino su lab_crop (2,76 m) e lontanissimo su un provino da
// dieci centimetri. Le due frazioni sono guardie contro il degenere, non una
// taratura del gesto: servono a tenere la camera in un posto che esiste.
//
// Senza un riferimento -- prima che la prima geometria sia arrivata -- non si
// stringe niente: si rifiuta solo cio' che non e' un raggio.
export function raggioAmmesso(raggio, riferimento) {
  if (!Number.isFinite(raggio) || raggio <= 0) return riferimento > 0 ? riferimento : 1;
  if (!(riferimento > 0)) return raggio;
  return Math.min(Math.max(raggio, riferimento / 1000), riferimento * 100);
}

// --- Quanto ha girato la rotella --------------------------------------------
//
// `deltaY > 0 ? 1.1 : 0.9` guarda il SEGNO e butta via la misura. Con una
// rotella a scatti, un evento per scatto, il conto torna; con un trackpad, che
// di un solo gesto emette una raffica di eventi piccoli, ogni evento della
// raffica moltiplica il raggio del dieci per cento.
//
// E `deltaY` non e' nemmeno nella stessa unita' su tutti i browser: deltaMode
// dice se sono pixel (0), righe (1) o pagine (2). Chi lo ignora zooma sedici
// volte piu' in fretta dove il browser conta a righe.
//
// Le sedici sono l'altezza di riga presunta quando il browser non la dice: e'
// una stima dichiarata, non una misura, e serve solo a non trattare una riga
// come un pixel.
export function passoDellaRotella(deltaY, deltaMode, altezza) {
  if (!Number.isFinite(deltaY)) return 0;
  const perRiga = 16;
  const scala = deltaMode === 1 ? perRiga
    : deltaMode === 2 ? (Number.isFinite(altezza) && altezza > 0 ? altezza : perRiga * 20)
    : 1;
  return deltaY * scala;
}

// --- L'arco piu' corto ------------------------------------------------------
//
// L'azimut e' un angolo che gira: da 6,2 a 0,1 ci sono 0,18 radianti in avanti
// e 6,1 all'indietro. Interpolare fra i due numeri come fra due grandezze
// qualsiasi prende la strada lunga, cioe' fa girare il pezzo su se stesso per
// arrivare a un lato che era li' accanto. Si sceglie l'arco corto riportando
// lo scarto dentro meno pi greco / piu' pi greco.
export function arcoPiuCorto(da, a) {
  const giro = Math.PI * 2;
  return da + (((a - da) % giro) + giro + Math.PI) % giro - Math.PI;
}

// --- Le sei viste dichiarate ------------------------------------------------
//
// Nominate per ASSE e non per anatomia -- non «fronte», «destra» -- e la
// ragione e' scritta nel prodotto: i nomi delle facce sono convenzioni e non
// identificazioni delle facce fisiche, misurato sui set FACE_FRONT e FACE_BACK
// di una scansione vera. Una vista chiamata «fronte» che guarda il fianco
// direbbe con sicurezza una cosa falsa; «+X» dice cio' che e' e non di piu'.
//
// Angoli fissi e non relativi a dov'e' la camera adesso: e' cio' che rende due
// catture della stessa vista confrontabili fra una corsa e l'altra, che e' il
// motivo per cui queste sei esistono -- le viste finiscono in appendice a un
// documento stampato.
//
// Sopra e sotto non stanno sul polo esatto ma a un millesimo di radiante: la'
// `up` e' parallelo all'asse della camera, `lookAt` produce NaN e la scena
// sparisce senza un errore. E' lo stesso millesimo, e lo stesso motivo, di
// oltreIlPolo.
export const VISTE = [
  { tasto: "1", nome: "+X", theta: 0, phi: Math.PI / 2 },
  { tasto: "2", nome: "-X", theta: Math.PI, phi: Math.PI / 2 },
  { tasto: "3", nome: "+Y", theta: 0, phi: 1e-3 },
  { tasto: "4", nome: "-Y", theta: 0, phi: Math.PI - 1e-3 },
  { tasto: "5", nome: "+Z", theta: Math.PI / 2, phi: Math.PI / 2 },
  { tasto: "6", nome: "-Z", theta: -Math.PI / 2, phi: Math.PI / 2 },
];

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

  // Il canvas non ha testo proprio: senza un'alternativa, chi usa uno
  // screen reader vede un buco muto. L'aria-label aggiornato ad ogni disegno
  // da' il contenuto testuale equivalente; tabindex lo rende raggiungibile da
  // tastiera. Il ruolo e' "application" e non "img" perche' la tela si comanda
  // davvero dalla tastiera: "img" la annuncerebbe come figura ferma e lo
  // screen reader intercetterebbe le frecce invece di passarle qui.
  const COMANDI = "frecce per ruotare, maiuscolo e frecce per spostare, più e meno per lo zoom, da 1 a 6 per le viste sugli assi, F per rinquadrare";
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
  // Gli appoggi del gesto, distinti da quelli della luce: aggiornaCamera
  // riscrive _destra e _alto a ogni fotogramma, e la panoramica li legge prima
  // di chiamarla. Condividerli funzionerebbe finche' l'ordine resta questo,
  // cioe' finche' nessuno lo cambia senza sapere che qualcuno ci contava.
  const _destraGesto = new THREE.Vector3();
  const _altoGesto = new THREE.Vector3();
  const _direzione = new THREE.Vector3();
  const _punto = new THREE.Vector3();
  const _cursore = new THREE.Vector2();
  const _lancio = new THREE.Raycaster();
  const _pianoDelFuoco = new THREE.Plane();

  let orbita = { theta: 0.7, phi: 1.0, raggio: 1, centro: new THREE.Vector3() };

  // L'ingombro dell'ultima inquadratura, cioe' la scala del pezzo che si sta
  // guardando. E' il riferimento dei fermi del raggio: null finche' non e'
  // arrivata nessuna geometria, e li' non si stringe niente.
  let raggioInquadrato = null;

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

  // Quanto mondo vale un pixel, sul piano che passa per il centro dell'orbita.
  // E' cio' che rende la panoramica indipendente dallo zoom: senza, lo stesso
  // trascinamento sposta il pezzo di un capello da lontano e lo butta fuori
  // dall'inquadratura da vicino.
  function passoPerPixel() {
    const altezza = contenitore.clientHeight || 1;
    return (2 * orbita.raggio * Math.tan((camera.fov * Math.PI / 180) / 2)) / altezza;
  }

  // Il punto del mondo sotto il cursore, preso sul piano del fuoco.
  //
  // ponytail: il piano del fuoco e non la geometria vera. Il punto esatto
  // vorrebbe un raycast contro la nuvola, che in three.js e' una scansione
  // lineare di tutti i punti -- 4,2 milioni su lab_crop, a ogni scatto di
  // rotella. Il piano passa per il centro dell'orbita, quindi la profondita'
  // e' quella del pezzo e non quella della faccia colpita: la direzione e'
  // giusta, la distanza approssimata. Se servisse il punto vero, il posto e'
  // questo e la strada e' un BVH sulla geometria.
  //
  // Torna null dove non c'e' una risposta: tela di area nulla, oppure raggio
  // parallelo al piano. Chi chiama non muove niente invece di muovere a caso.
  function puntoSottoIlCursore(evento) {
    const riquadro = tela.getBoundingClientRect?.();
    if (!riquadro || !(riquadro.width > 0) || !(riquadro.height > 0)) return null;
    _cursore.set(
      ((evento.clientX - riquadro.left) / riquadro.width) * 2 - 1,
      -((evento.clientY - riquadro.top) / riquadro.height) * 2 + 1,
    );
    _lancio.setFromCamera(_cursore, camera);
    camera.getWorldDirection(_direzione);
    _pianoDelFuoco.setFromNormalAndCoplanarPoint(_direzione, orbita.centro);
    return _lancio.ray.intersectPlane(_pianoDelFuoco, _punto);
  }

  // La panoramica: si sposta il centro dell'orbita, non la camera. Il pezzo
  // segue il cursore, quindi il centro va dalla parte opposta al trascinamento.
  function sposta(dx, dy) {
    const passo = passoPerPixel();
    camera.updateMatrixWorld();
    _destraGesto.setFromMatrixColumn(camera.matrixWorld, 0);
    _altoGesto.setFromMatrixColumn(camera.matrixWorld, 1);
    orbita.centro
      .addScaledVector(_destraGesto, -dx * passo)
      .addScaledVector(_altoGesto, dy * passo);
  }

  // Lo zoom, ancorato al cursore. Il raggio cambia per fattore -- una scala e'
  // moltiplicativa, non additiva -- e il centro scivola verso il punto puntato
  // della stessa quota di cui il raggio si e' accorciato: cosi' quel punto
  // resta dov'e' ed e' il resto della scena a venirgli incontro. Allargando,
  // la quota e' negativa e il centro si allontana: il gesto e' reversibile.
  function avvicina(passo, evento) {
    const prima = orbita.raggio;
    orbita.raggio = raggioAmmesso(prima * Math.exp(passo * 0.0015), raggioInquadrato);
    const bersaglio = evento === undefined ? null : puntoSottoIlCursore(evento);
    if (bersaglio !== null) orbita.centro.lerp(bersaglio, 1 - orbita.raggio / prima);
  }

  let premuto = false;
  // Quale gesto e' in corso: il tasto lo decide alla pressione e non a ogni
  // spostamento, altrimenti lasciare il maiuscolo a meta' trascinamento
  // cambierebbe gesto sotto la mano.
  let gesto = "orbita";
  let ultimo = { x: 0, y: 0 };
  tela.addEventListener("pointerdown", (evento) => {
    premuto = true;
    // Destro e centrale sono la panoramica di ogni programma di modellazione;
    // maiuscolo e sinistro e' la stessa cosa per chi ha un tasto solo.
    gesto = (evento.button === 1 || evento.button === 2 || evento.shiftKey)
      ? "panoramica" : "orbita";
    ultimo = { x: evento.clientX, y: evento.clientY };
    tela.setPointerCapture(evento.pointerId);
  });
  tela.addEventListener("pointerup", () => { premuto = false; });
  // Senza, il tasto destro apre il menu del browser a meta' panoramica.
  tela.addEventListener("contextmenu", (evento) => evento.preventDefault());
  tela.addEventListener("pointermove", (evento) => {
    if (!premuto) return;
    laCameraPassaAlGesto();
    const dx = evento.clientX - ultimo.x;
    const dy = evento.clientY - ultimo.y;
    if (gesto === "panoramica") {
      sposta(dx, dy);
    } else {
      orbita.theta -= dx * 0.005;
      orbita.phi = oltreIlPolo(orbita.phi, -dy * 0.005);
    }
    ultimo = { x: evento.clientX, y: evento.clientY };
    aggiornaCamera();
  });
  tela.addEventListener("wheel", (evento) => {
    evento.preventDefault();
    laCameraPassaAlGesto();
    avvicina(passoDellaRotella(evento.deltaY, evento.deltaMode, contenitore.clientHeight), evento);
    aggiornaCamera();
  }, { passive: false });

  // Il doppio clic porta il centro dell'orbita dove si e' puntato: e' il modo
  // di girare attorno a un dettaglio invece che attorno al pezzo intero.
  tela.addEventListener("dblclick", (evento) => {
    const bersaglio = puntoSottoIlCursore(evento);
    if (bersaglio === null) return;
    laCameraPassaAlGesto();
    orbita.centro.copy(bersaglio);
    aggiornaCamera();
  });

  // Gli stessi comandi da tastiera, per chi non usa il mouse. Il passo e'
  // quello dei gesti col mouse, solo discretizzato. Vedi COMANDI: quell'elenco
  // e' cio' che il lettore di schermo annuncia, e va tenuto d'accordo con
  // questo blocco.
  tela.addEventListener("keydown", (evento) => {
    const vista = VISTE.find((voce) => voce.tasto === evento.key);
    if (vista !== undefined) {
      evento.preventDefault();
      laCameraPassaAlGesto();
      portaLaCamera(vista);
      return;
    }
    if (evento.key === "f" || evento.key === "F" || evento.key === "Home") {
      evento.preventDefault();
      laCameraPassaAlGesto();
      portaLaCamera(null);
      return;
    }
    // Il passo della panoramica e' in pixel di mano, non in millimetri di
    // mondo: passa da sposta(), che lo converte con lo zoom di adesso.
    const passi = evento.shiftKey ? {
      ArrowLeft: () => sposta(-10, 0),
      ArrowRight: () => sposta(10, 0),
      ArrowUp: () => sposta(0, -10),
      ArrowDown: () => sposta(0, 10),
    } : {
      ArrowLeft: () => { orbita.theta -= 0.1; },
      ArrowRight: () => { orbita.theta += 0.1; },
      ArrowUp: () => { orbita.phi = oltreIlPolo(orbita.phi, -0.1); },
      ArrowDown: () => { orbita.phi = oltreIlPolo(orbita.phi, 0.1); },
      "+": () => avvicina(-100),
      "-": () => avvicina(100),
    };
    const passo = passi[evento.key];
    if (!passo) return;
    evento.preventDefault();
    laCameraPassaAlGesto();
    passo();
    aggiornaCamera();
  });

  // La pulsantiera delle sei viste. Il contenitore viene dal markup -- cosi'
  // preesiste a cio' che annuncia, come lo stato vuoto e la didascalia -- ma i
  // bottoni li costruisce VISTE, che e' anche chi conosce gli angoli: scriverne
  // i nomi anche nell'HTML darebbe due elenchi da tenere d'accordo a mano.
  //
  // I tasti sono nominati nell'aria-label e non solo nel testo: chi legge lo
  // schermo sente «Vista da +X, tasto 1» e impara la scorciatoia dal comando
  // che gia' sta usando, invece di doverla trovare altrove.
  const comandiVista = contenitore.querySelector("#viste");
  for (const vista of comandiVista === null ? [] : VISTE) {
    const bottone = document.createElement("button");
    bottone.type = "button";
    bottone.className = "bottone";
    bottone.textContent = vista.nome;
    bottone.setAttribute("aria-label", `Vista da ${vista.nome}, tasto ${vista.tasto}`);
    bottone.addEventListener("click", () => {
      laCameraPassaAlGesto();
      portaLaCamera(vista);
    });
    comandiVista.append(bottone);
  }

  // Sei bottoni che non muovono niente sopra una vista vuota sarebbero comandi
  // inerti: la pulsantiera compare con la geometria e se ne va con lei.
  function mostraLeViste(visibili) {
    if (comandiVista !== null) comandiVista.hidden = !visibili;
  }

  function disegna() {
    if (transizione !== null) {
      const frazione = frazioneDellArrivo(performance.now() - transizione.inizio);
      orbita.centro.lerpVectors(transizione.daCentro, transizione.aCentro, frazione);
      orbita.raggio = transizione.daRaggio + (transizione.aRaggio - transizione.daRaggio) * frazione;
      // Anche gli angoli, da quando le sei viste sugli assi girano la camera.
      // Prima l'arrivo interpolava solo centro e raggio, e bastava: nessuna
      // strada cambiava l'inquadratura ruotando.
      orbita.theta = transizione.daTheta + (transizione.aTheta - transizione.daTheta) * frazione;
      // L'elevazione passa da oltreIlPolo come ogni altra sua scrittura, e qui
      // non e' una formalita'. phi vive in [0, 2 pi greco): oltre pi greco si
      // guarda il pezzo capovolti, ed e' uno stato raggiungibile trascinando in
      // su oltre la cima. Da li' l'arrivo a una vista con phi = pi greco mezzi
      // ATTRAVERSA il polo, dove `up` e' parallelo all'asse della camera e
      // lookAt produce NaN: la scena sparisce senza un errore in console.
      //
      // Si passa il PASSO e non il risultato: il segno dice da che parte uscire
      // dal polo, ed e' il verso in cui l'arrivo stava andando.
      const phiVoluto = transizione.daPhi + (transizione.aPhi - transizione.daPhi) * frazione;
      orbita.phi = oltreIlPolo(orbita.phi, phiVoluto - orbita.phi);
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
  // guarda `visible` (vendor/three.core.js:9730), quindi nasconderlo non
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

  // Porta la camera sull'ingombro di adesso, e se le si da' una vista anche
  // sui suoi angoli. Torna false quando non c'e' niente da inquadrare.
  //
  // Separata da inquadra() per via della comparsa. La dissolvenza della tela
  // dichiara «questa e' una vista nuova»: vero quando arriva una geometria,
  // falso quando si preme F o un tasto di vista, dove il pezzo e' lo stesso e a
  // muoversi e' solo la camera. Farla lampeggiare a ogni comando annuncerebbe
  // un cambiamento che non e' avvenuto.
  //
  // Le sei viste inquadrano oltre a ruotare, e non e' un di piu': una vista che
  // lasciasse l'inquadratura dov'era darebbe due catture diverse dello stesso
  // lato a seconda di dove si era arrivati, cioe' toglierebbe a quelle sei la
  // sola ragione per cui esistono -- essere confrontabili fra una corsa e
  // l'altra, in appendice a un documento stampato.
  function portaLaCamera(vista) {
    const scatola = scatolaDelGruppo();
    if (scatola.isEmpty()) {
      mostraLeViste(false);
      return false;
    }
    const centro = scatola.getCenter(new THREE.Vector3());
    const raggio = scatola.getSize(new THREE.Vector3()).length() * 1.2;
    raggioInquadrato = raggio;
    // L'arco corto e non il numero scritto: da 6,2 a 0,1 ci sono 0,18 radianti
    // in avanti, non 6,1 all'indietro.
    const aTheta = vista === null ? orbita.theta : arcoPiuCorto(orbita.theta, vista.theta);
    const aPhi = vista === null ? orbita.phi : vista.phi;
    // Il salto resta dove l'assestamento non avrebbe niente da raccontare: alla
    // prima geometria, e a chi ha chiesto meno movimento.
    if (!inquadratoUnaVolta || menoMovimento?.matches) {
      orbita.centro.copy(centro);
      orbita.raggio = raggio;
      orbita.theta = aTheta;
      // Come sopra: mai una scrittura diretta dell'elevazione. Con vista nulla
      // il passo e' zero e non cambia niente; con una vista, il segno del passo
      // e' il verso da cui uscire se la meta' cade su un polo.
      orbita.phi = oltreIlPolo(orbita.phi, aPhi - orbita.phi);
      transizione = null;
      aggiornaCamera();
    } else {
      transizione = {
        daCentro: orbita.centro.clone(),
        daRaggio: orbita.raggio,
        daTheta: orbita.theta,
        daPhi: orbita.phi,
        aCentro: centro,
        aRaggio: raggio,
        aTheta,
        aPhi,
        inizio: performance.now(),
      };
    }
    inquadratoUnaVolta = true;
    mostraLeViste(true);
    return true;
  }

  function inquadra() {
    // La comparsa vale anche dove l'inquadratura salta: l'informazione «questa
    // e' una vista nuova» non si toglie con lo spostamento, si porta su un
    // altro canale.
    if (portaLaCamera(null)) comparsa();
  }

  return {
    svuota() {
      // Il fantasma e' del passaggio che si sta lasciando, e se ne va con lui.
      // In testa e non in fondo: ogni strada che disegna chiama svuota() due
      // volte -- una al caricamento e una prima di disegnare -- e cosi' la
      // seconda lo trova gia' tolto invece di lasciarlo sotto la geometria
      // nuova.
      togliFantasma();
      mostraLeViste(false);
      // Togliere un oggetto dalla scena non libera i suoi buffer: in three.js
      // sono gli eventi di dispose a cancellarli davvero (three.module.js:3821,
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
    // Vale anche per la mesh esaedrica: la sua superficie di contorno e' fatta
    // di quadrilateri, che il server ha gia' diviso in triangoli con
    // core.viewport.triangoli_da_quadrilateri. Qui non arriva mai un
    // quadrilatero.
    mostraMesh(vertici, facce) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      geometria.computeVertexNormals();
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
    mostraMeshPerCampo(vertici, facce, valori, { taglio, descrizione }) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      geometria.computeVertexNormals();
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
      const CHIARO = new THREE.Color(0xd9e8e4);
      const SCURO = new THREE.Color(0x2f5d50); // --accento, come la nuvola
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
    // Colore per membratura. E' la prova visiva che la scomposizione ha capito
    // il pezzo, e si legge in un secondo dove nessuna metrica sarebbe cosi'
    // rapida. -1 significa «nessuna membratura» e resta grigio: e'
    // un'informazione, non un buco.
    mostraNuvolaPerMembratura(punti, etichette) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(punti, 3));
      const colori = new Float32Array(etichette.length * 3);
      let massima = 0;
      for (const valore of etichette) massima = Math.max(massima, valore);
      for (let indice = 0; indice < etichette.length; indice += 1) {
        const colore = new THREE.Color();
        if (etichette[indice] < 0) colore.setRGB(0.68, 0.68, 0.65);
        else colore.setHSL((etichette[indice] / (massima + 1)) * 0.8, 0.55, 0.45);
        colore.toArray(colori, indice * 3);
      }
      geometria.setAttribute("color", new THREE.BufferAttribute(colori, 3));
      gruppo.add(new THREE.Points(geometria, new THREE.PointsMaterial({
        size: 1.5, sizeAttenuation: false, vertexColors: true, clippingPlanes: pianiTaglio,
      })));
      descrivi(`nuvola divisa in ${massima + 1} membrature`);
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
    mostraFantasma(vertici, facce = null) {
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
        geometria.computeVertexNormals();
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
    // fotogramma (three.core.js:57620, updateMatrixWorld), quindi riscrivere
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
      pianoTaglio.normal.set(asse === 0 ? 1 : 0, asse === 1 ? 1 : 0, asse === 2 ? 1 : 0);
      pianoTaglio.constant = -quota;
      pianiTaglio[0] = pianoTaglio;
    },
    disattivaTaglio() {
      pianiTaglio.length = 0;
    },
    cattura() {
      renderer.render(scena, camera);
      return tela.toDataURL("image/png");
    },
  };
}
