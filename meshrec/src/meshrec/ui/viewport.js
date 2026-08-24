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
    const coda = "la forma modale non e' disegnata, la vista mostra il modello indeformato";
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
  const COMANDI = "frecce per ruotare, piu' e meno per lo zoom";
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

  let premuto = false;
  let ultimo = { x: 0, y: 0 };
  tela.addEventListener("pointerdown", (evento) => {
    premuto = true;
    ultimo = { x: evento.clientX, y: evento.clientY };
    tela.setPointerCapture(evento.pointerId);
  });
  tela.addEventListener("pointerup", () => { premuto = false; });
  tela.addEventListener("pointermove", (evento) => {
    if (!premuto) return;
    laCameraPassaAlGesto();
    orbita.theta -= (evento.clientX - ultimo.x) * 0.005;
    orbita.phi = Math.min(Math.PI - 0.01, Math.max(0.01, orbita.phi - (evento.clientY - ultimo.y) * 0.005));
    ultimo = { x: evento.clientX, y: evento.clientY };
    aggiornaCamera();
  });
  tela.addEventListener("wheel", (evento) => {
    evento.preventDefault();
    laCameraPassaAlGesto();
    orbita.raggio *= evento.deltaY > 0 ? 1.1 : 0.9;
    aggiornaCamera();
  }, { passive: false });

  // Orbita anche da tastiera, per chi non usa il mouse: frecce per ruotare,
  // +/- per lo zoom. Stesso passo dei gesti col mouse, solo discretizzato.
  tela.addEventListener("keydown", (evento) => {
    const passi = {
      ArrowLeft: () => { orbita.theta -= 0.1; },
      ArrowRight: () => { orbita.theta += 0.1; },
      ArrowUp: () => { orbita.phi = Math.max(0.01, orbita.phi - 0.1); },
      ArrowDown: () => { orbita.phi = Math.min(Math.PI - 0.01, orbita.phi + 0.1); },
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
  // guarda `visible` (vendor/three.core.js:9730), quindi nasconderlo non
  // toglierebbe niente dalla misura. Misurato in node, non dedotto.
  function scatolaDelGruppo() {
    const scatola = new THREE.Box3();
    for (const figlio of gruppo.children) {
      if (figlio !== box) scatola.expandByObject(figlio);
    }
    return scatola;
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
