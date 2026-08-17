// Scena tridimensionale. Disegna cio' che il server manda, non ricalcola nulla.
import * as THREE from "/ui/vendor/three.module.js";

// L'apertura dell'obiettivo, in gradi. Scritta qui e non dentro la costruzione
// della camera perche' la guardia della camera la deve leggere: dalle due parti
// e' lo stesso numero, e due letterali uguali si scollano al primo che cambia.
const FOV_GRADI = 50;

// Il centro del nuovo ingombro e' uscito da cio' che la camera sta mostrando?
// La soglia e' la semialtezza visibile sul piano del centro, raggio * tan(fov/2)
// — non il raggio dell'orbita, che e' la distanza fra camera e centro e con fov
// 50 vale piu' del doppio di cio' che si vede: misurata su quello, la guardia
// lasciava passare un centro fuori dallo schermo, e a video restava il vuoto.
//
// Resta un'euristica, e lo e' due volte: confronta un punto con una misura di
// altezza, quindi verso i bordi decide per approssimazione, e non guarda quanto
// e' grande l'ingombro nuovo, percio' una geometria concentrica ma molto piu'
// larga passa e deborda. Sono errori che costano un clic: il comando
// «Inquadra» rimette la vista sulla geometria quando la guardia sbaglia. Una
// guardia esatta vorrebbe la proiezione degli otto vertici, cioe' la camera
// dentro una funzione che esiste apposta per starne fuori.
//
// Pura e di primo livello: e' la sola decisione di questa camera, e cosi' si
// prova da fuori senza costruire un three.js finto. Per la stessa ragione il
// fov arriva come parametro invece che dalla camera.
// centro e vecchioCentro sono terne in millimetri, raggio uno scalare.
export function fuoriDallaVista(centro, vecchioCentro, raggio, fovGradi) {
  const semialtezzaVisibile = raggio * Math.tan(((fovGradi / 2) * Math.PI) / 180);
  return Math.hypot(
    centro[0] - vecchioCentro[0],
    centro[1] - vecchioCentro[1],
    centro[2] - vecchioCentro[2],
  ) > semialtezzaVisibile;
}

// Quanto vale un pixel di trascinamento, in unita' di scena, alla distanza a
// cui la camera sta guardando. 2*raggio*tan(fov/2) e' l'altezza visibile a
// quella distanza; divisa per l'altezza della tela da' i millimetri per pixel,
// ed e' cio' che fa restare sotto il cursore il punto che ci stava.
// fovGradi arriva come parametro per la stessa ragione di fuoriDallaVista: la
// funzione si prova da fuori, e il numero vero e' uno solo, FOV_GRADI.
export function scalaDelloSpostamento(raggio, altezzaTela, fovGradi) {
  return (2 * raggio * Math.tan((fovGradi * Math.PI) / 360)) / altezzaTela;
}

// I colori della scena stanno in stile.css con tutti gli altri. Erano quattro
// esadecimali scritti qui, dove nessuno dei controlli di contrasto del progetto
// li raggiungeva: il fondo restava uguale a --sfondo solo per la coincidenza di
// due letterali identici, e cambiarne uno solo dei due non avrebbe fatto rosso
// nulla.
//
// Letti a ogni uso e non una volta all'importazione: un modulo puo' valutarsi
// prima che il foglio sia applicato, e li' ogni token tornerebbe vuoto. Nessuno
// di questi usi sta su un cammino caldo — uno per geometria caricata, uno alla
// nascita del box — quindi il ricalcolo di stile che getComputedStyle forza si
// paga una volta per gesto.
//
// Vuoto si alza, non si disegna: THREE.Color di una stringa vuota rende nero
// senza dire niente, cioe' una scena illeggibile che si presenta come una scena.
function tinta(nome) {
  const valore = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  if (valore === "") throw new Error(`il colore ${nome} non e' dichiarato in stile.css`);
  return new THREE.Color(valore);
}

export function creaViewport(contenitore) {
  const scena = new THREE.Scene();
  scena.background = tinta("--sfondo");

  const camera = new THREE.PerspectiveCamera(FOV_GRADI, 1, 0.1, 1e6);
  camera.position.set(1, 1, 1);

  // preserveDrawingBuffer: senza, il canvas e' vuoto al momento della cattura
  // per il report, perche' il browser lo azzera dopo la presentazione.
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
  const COMANDI = "frecce per ruotare, maiusc con le frecce o col trascinamento per spostare la vista, piu' e meno per lo zoom, f per inquadrare di nuovo la geometria";
  const tela = renderer.domElement;
  tela.setAttribute("role", "application");
  tela.setAttribute("tabindex", "0");
  // La descrizione viaggia con la geometria e non accanto: il confronto mette a
  // video la geometria di prima, e l'etichetta deve dire quella, non quella che
  // c'era un istante fa. Tenute separate — una variabile qui e una scrittura
  // la' — si scollerebbero al primo ramo che sposta l'una e non l'altra.
  let descrizione = "vuota";
  let descrizionePrecedente = null;
  function applicaEtichetta(contenuto) {
    tela.setAttribute("aria-label", `Vista tridimensionale: ${contenuto}. Comandi: ${COMANDI}.`);
  }
  function descrivi(contenuto) {
    descrizione = contenuto;
    applicaEtichetta(contenuto);
  }
  descrivi("vuota");
  contenitore.append(tela);

  const gruppo = new THREE.Group();
  scena.add(gruppo);

  // La geometria dello step guardato prima di questo, tenuta sulla scheda per il
  // confronto. Fratello di `gruppo` e non figlio: scatolaDelGruppo() percorre i
  // figli di `gruppo`, e da dentro finirebbe nell'ingombro, cioe' il cursore del
  // taglio si tarerebbe sull'unione di due geometrie di cui una non e' a video.
  // Una sola, e non una pila: due geometrie sulla scheda sono 9,6 MB di
  // attributi nel caso peggiore misurato dal commento di svuota(), una pila
  // sarebbero 7,6 MB per ogni clic su uno step.
  const precedente = new THREE.Group();
  precedente.visible = false;
  scena.add(precedente);

  // Il box di ritaglio: uno solo, tenuto in una variabile di chiusura come
  // pianoTaglio e non su this, perche' svuota() deve poterlo azzerare quando
  // libera la geometria. Sta dentro il gruppo apposta: cosi' la stessa
  // traversata che libera nuvola e mesh libera anche lui.
  let box = null;
  scena.add(new THREE.AmbientLight(0xffffff, 0.7));
  const direzionale = new THREE.DirectionalLight(0xffffff, 0.8);
  direzionale.position.set(1, 2, 3);
  scena.add(direzionale);

  let orbita = { theta: 0.7, phi: 1.0, raggio: 1, centro: new THREE.Vector3() };

  // Il centro dell'ingombro inquadrato l'ultima volta, e null finche' non si e'
  // inquadrato niente. Il primo disegno dopo l'avvio inquadra; dal secondo in
  // poi la camera resta dove l'utente l'ha messa. Era il «di passaggio in
  // passaggio si riparte da zero»: la stessa nuvola inquadrata da un altro
  // punto sembra un'altra nuvola, e mostraNuvola/mostraMesh riscrivevano centro
  // e raggio a ogni step.
  //
  // Tenuto a parte e non letto da orbita.centro, che sarebbe la stessa cosa
  // finche' inquadra() ne e' l'unico scrittore: da quando esiste il pan lo
  // scrive anche trasla(), e la guardia misurerebbe la distanza dal punto in
  // cui l'utente ha portato la vista invece che da cio' che ha inquadrato.
  // Zoomato su un dettaglio e traslato lungo il muro, il passaggio di step
  // riazzererebbe la vista: lo stesso difetto, rientrato per un'altra porta.
  // Una copia e non un riferimento, per la stessa ragione: al riferimento il
  // pan sposterebbe anche la memoria.
  let centroInquadrato = null;

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
  }

  // Quaranta pixel per pressione: l'ordine di grandezza di un trascinamento
  // corto, cosi' il comando da tastiera e quello col mouse spostano la vista
  // dello stesso passo percepito.
  const PASSO_TASTIERA = 40;

  // I tre assi della camera, riusati invece di riallocarli a ogni movimento del
  // puntatore: pointermove scatta a ogni fotogramma mentre si trascina.
  const destra = new THREE.Vector3();
  const alto = new THREE.Vector3();
  const avanti = new THREE.Vector3();

  // Sposta il centro dell'orbita nel piano della camera, di dx e dy pixel di
  // trascinamento. Gli assi vengono dalla matrice della camera e non da un
  // sistema fisso: ruotata l'orbita, «destra» non e' piu' l'asse x della scena,
  // e traslare lungo quello farebbe scorrere la vista di traverso rispetto al
  // gesto.
  // I segni fanno seguire il contenuto al dito: trascinando a destra la
  // geometria va a destra, quindi la camera va a sinistra.
  // updateMatrixWorld prima di leggerla: lookAt scrive il quaternione, ma la
  // matrice del mondo three.js la ricalcola al disegno, quindi senza questa
  // riga si leggerebbero gli assi del fotogramma precedente.
  function trasla(dx, dy) {
    const scala = scalaDelloSpostamento(orbita.raggio, tela.clientHeight || 1, camera.fov);
    camera.updateMatrixWorld();
    camera.matrixWorld.extractBasis(destra, alto, avanti);
    orbita.centro.addScaledVector(destra, -dx * scala);
    orbita.centro.addScaledVector(alto, dy * scala);
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
    const dx = evento.clientX - ultimo.x;
    const dy = evento.clientY - ultimo.y;
    ultimo = { x: evento.clientX, y: evento.clientY };
    // Maiusc trasla, altrimenti ruota: sul telaio largo 2.759 mm senza pan non
    // si raggiunge uno spigolo, perche' orbita.centro cambiava solo dentro
    // inquadra().
    if (evento.shiftKey) {
      trasla(dx, dy);
    } else {
      orbita.theta -= dx * 0.005;
      orbita.phi = Math.min(Math.PI - 0.01, Math.max(0.01, orbita.phi - dy * 0.005));
    }
    aggiornaCamera();
  });
  tela.addEventListener("wheel", (evento) => {
    evento.preventDefault();
    orbita.raggio *= evento.deltaY > 0 ? 1.1 : 0.9;
    aggiornaCamera();
  }, { passive: false });

  // Orbita, zoom, traslazione e inquadratura da tastiera, per chi non usa il
  // mouse: frecce per ruotare, maiusc con le frecce per spostare, +/- per lo
  // zoom, f per riportare la vista sulla geometria. Stessi gesti del mouse,
  // solo discretizzati.
  //
  // Una tabella sola, e maiusc arriva alla voce invece di scegliere fra due
  // tabelle. Con due tabelle un tasto non-freccia premuto con maiusc non
  // trovava nessuna voce e smetteva di funzionare: su una tastiera americana
  // «+» **e'** maiusc piu' «=», quindi lo zoom sarebbe sparito proprio dove il
  // segno lo richiede.
  // Le frecce spostano il punto di vista e non il contenuto, come lo scorrere
  // di una pagina: freccia sinistra porta la vista a sinistra, cioe' la
  // geometria scorre a destra.
  tela.addEventListener("keydown", (evento) => {
    const comandi = {
      ArrowLeft: (maiusc) => {
        if (maiusc) trasla(PASSO_TASTIERA, 0);
        else orbita.theta -= 0.1;
      },
      ArrowRight: (maiusc) => {
        if (maiusc) trasla(-PASSO_TASTIERA, 0);
        else orbita.theta += 0.1;
      },
      ArrowUp: (maiusc) => {
        if (maiusc) trasla(0, PASSO_TASTIERA);
        else orbita.phi = Math.max(0.01, orbita.phi - 0.1);
      },
      ArrowDown: (maiusc) => {
        if (maiusc) trasla(0, -PASSO_TASTIERA);
        else orbita.phi = Math.min(Math.PI - 0.01, orbita.phi + 0.1);
      },
      "+": () => { orbita.raggio *= 0.9; },
      "-": () => { orbita.raggio *= 1.1; },
      // L'uscita di sicurezza dalla tastiera, gemella del bottone «Inquadra».
      f: () => { inquadra(); },
    };
    const passo = comandi[evento.key];
    if (!passo) return;
    evento.preventDefault();
    passo(evento.shiftKey);
    aggiornaCamera();
  });

  function disegna() {
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
    scatola.getCenter(orbita.centro);
    orbita.raggio = scatola.getSize(new THREE.Vector3()).length() * 1.2;
    centroInquadrato = orbita.centro.clone();
    aggiornaCamera();
  }

  function inquadraSeServe() {
    if (centroInquadrato === null) {
      inquadra();
      return;
    }
    const scatola = scatolaDelGruppo();
    if (scatola.isEmpty()) return;
    const centro = scatola.getCenter(new THREE.Vector3());
    if (fuoriDallaVista(centro.toArray(), centroInquadrato.toArray(), orbita.raggio, FOV_GRADI)) {
      inquadra();
    }
  }

  // Libera davvero cio' che sta nel precedente. Togliere un oggetto dalla scena
  // non libera i suoi buffer: in three.js sono gli eventi di dispose a
  // cancellarli (three.module.js:3821, onGeometryDispose, toglie l'indice e ogni
  // attributo). Senza questa chiamata il precedente diventerebbe una pila e ogni
  // clic su uno step lascerebbe sulla scheda i 7,6 MB di attributi del clic
  // prima — lo stesso difetto che svuota() era stato scritto per chiudere, con
  // l'aria di una funzione nuova.
  // Ogni oggetto ha il materiale che gli ha creato mostraNuvola o mostraMesh, e
  // nessun altro lo usa: liberarlo qui non lascia scoperto nessuno.
  function liberaIlPrecedente() {
    precedente.traverse((oggetto) => {
      oggetto.geometry?.dispose();
      oggetto.material?.dispose();
    });
    precedente.clear();
    descrizionePrecedente = null;
  }

  return {
    // Sposta la geometria a video nel precedente e restituisce se l'ha fatto.
    // NON la distrugge piu': e' cio' con cui il confronto confronta. Il valore
    // di ritorno serve a chi tiene il nome dello step mostrato: la geometria e
    // la sua etichetta devono passare al precedente nello stesso istante,
    // altrimenti il comando del confronto nomina uno step e ne mostra un altro.
    // Falso quando non c'era niente da spostare, ed e' il caso normale: ogni
    // strada che disegna chiama svuota() due volte — una al caricamento e una
    // prima di disegnare — e la seconda deve essere inerte, non deve buttare via
    // il precedente appena messo da parte.
    // pianiTaglio non si tocca: non e' una risorsa della scheda grafica ed e'
    // condiviso apposta perche' sopravviva alla geometria. Azzerarlo qui farebbe
    // nascere la geometria nuova senza taglio mentre il comando lo dichiara
    // attivo. Vale anche per il precedente, che porta lo stesso elenco: il
    // confronto guarda le due geometrie tagliate alla stessa quota, che e' il
    // solo modo in cui un confronto e' un confronto.
    svuota() {
      // Il box di ritaglio non si sposta: e' un attrezzo, non un risultato, e
      // nel precedente sarebbe il rettangolo di una manovra finita. Si libera
      // qui come faceva la traversata di prima, e il riferimento si azzera
      // perche' tenerlo lascerebbe mostraBox a riscrivere una geometria che non
      // esiste piu' sulla scheda.
      if (box !== null) {
        box.geometry?.dispose();
        box.material?.dispose();
        gruppo.remove(box);
        box = null;
      }
      const daSpostare = [...gruppo.children];
      if (daSpostare.length === 0) return false;
      liberaIlPrecedente();
      // add() stacca da se' i nodi dal genitore di prima: nessun remove().
      precedente.add(...daSpostare);
      precedente.visible = false;
      gruppo.visible = true;
      descrizionePrecedente = descrizione;
      descrivi("vuota");
      return true;
    },
    // Il confronto: si scambia quale dei due gruppi e' visibile, senza toccare
    // ne' la camera ne' i buffer. E' cio' che rende il confronto un confronto —
    // la stessa inquadratura sulle due geometrie — e cio' che lo rende
    // istantaneo: le due sono gia' sulla scheda, non si scarica niente.
    // L'etichetta segue la geometria, altrimenti chi non vede si sentirebbe
    // descrivere quella che non e' a video.
    mostraPrecedente(attivo) {
      precedente.visible = attivo;
      gruppo.visible = !attivo;
      applicaEtichetta(attivo ? descrizionePrecedente ?? "vuota" : descrizione);
    },
    mostraNuvola(punti) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(punti, 3));
      const materiale = new THREE.PointsMaterial({
        size: 1.5, sizeAttenuation: false, color: tinta("--nuvola"), clippingPlanes: pianiTaglio,
      });
      gruppo.add(new THREE.Points(geometria, materiale));
      descrivi(`nuvola di ${(punti.length / 3).toLocaleString("it")} punti`);
      inquadraSeServe();
    },
    mostraMesh(vertici, facce) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      geometria.computeVertexNormals();
      gruppo.add(new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
        color: tinta("--ricostruzione"), roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
        clippingPlanes: pianiTaglio,
      })));
      descrivi(`superficie di ${(facce.length / 3).toLocaleString("it")} facce`);
      inquadraSeServe();
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
        // La tinta si legge qui dentro e non fuori dal ramo: mostraBox e' anche
        // il gestore dei sei campi del ritaglio, cioe' gira a ogni tasto
        // premuto, e il box lo si costruisce una volta sola.
        box = new THREE.Box3Helper(new THREE.Box3(), tinta("--attrezzo"));
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
