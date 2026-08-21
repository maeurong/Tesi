// Scena tridimensionale. Disegna cio' che il server manda, non ricalcola nulla.
import * as THREE from "/ui/vendor/three.module.js";

// Il taglio della scala colore di un campo per nodo: al p99, non al massimo.
// Un carico nodale concentrato su mesh grossolana produce una singolarita' -
// un picco stretto su un solo nodo, non un plateau (misurato sull'as-built,
// caso CARICO_TOP: max/p99 = 5,09) - e una scala tirata su quel massimo
// schiaccerebbe tutto il resto del pezzo in un solo colore, mostrando
// l'artefatto come se fosse il risultato. Pura e fuori da mostraMeshPerCampo
// apposta: e' una decisione numerica, e questo progetto la prova eseguendola
// in node, non cercandola come sottostringa in una funzione che tocca three.js.
//
// sopraTaglio conta per valore (`v > taglio`), non per rango: `n - 1 - indice`
// e' una quota fissa, e su un campo costante o tutto a zero dichiarava cinque
// nodi sopra una soglia che nessuno supera - lo stesso testo che finisce
// nell'aria-label. E' anche la definizione che il server usa gia' per contare
// (np.count_nonzero(valori > p99)): due definizioni della stessa grandezza
// nello stesso sistema sono un difetto per conto proprio.
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
export function didascaliaDelCampo({ caso, grandezza, modale, frequenza, massimo }) {
  if (modale) {
    // Un modo oltre quelli calcolati non ha una frequenza nota: NaN.toFixed()
    // scriverebbe "NaN Hz" in silenzio, lo stesso guasto di un taglio muto.
    const hz = numeroDelCampo(frequenza, { maximumFractionDigits: 2 });
    return hz === null
      ? `${caso}: forma modale, ampiezza arbitraria (normalizzata sulla massa); frequenza non disponibile`
      : `${caso}: forma modale, ampiezza arbitraria (normalizzata sulla massa), ${hz} Hz`;
  }
  // «massimo reale» e non «massimo amplificato»: la vista non deforma nulla.
  // Il campo che arriva dal server e' una magnitudine per nodo, senza
  // direzione, e le posizioni restano quelle del contorno indeformato: una
  // didascalia che dichiarasse un'amplificazione starebbe scrivendo un numero
  // falso sopra un pezzo fermo.
  const spostamento = grandezza === "U";
  const nome = spostamento ? "spostamento" : "tensione equivalente";
  const scritto = numeroDelCampo(massimo);
  if (scritto === null) return `${caso} — ${nome}: massimo non disponibile`;
  // «reale» resta solo sullo spostamento: e' la grandezza che si guarda su una
  // vista, ed e' li' che qualcuno potrebbe leggere il colore come una misura.
  return spostamento
    ? `${caso} — ${nome}: massimo reale ${scritto} mm`
    : `${caso} — ${nome}: massimo ${scritto} MPa`;
}

export function creaViewport(contenitore) {
  const scena = new THREE.Scene();
  scena.background = new THREE.Color(0xfbfaf8);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1e6);
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
  direzionale.position.set(1, 2, 3);
  scena.add(direzionale);

  let orbita = { theta: 0.7, phi: 1.0, raggio: 1, centro: new THREE.Vector3() };

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
    orbita.theta -= (evento.clientX - ultimo.x) * 0.005;
    orbita.phi = Math.min(Math.PI - 0.01, Math.max(0.01, orbita.phi - (evento.clientY - ultimo.y) * 0.005));
    ultimo = { x: evento.clientX, y: evento.clientY };
    aggiornaCamera();
  });
  tela.addEventListener("wheel", (evento) => {
    evento.preventDefault();
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
    passo();
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
    aggiornaCamera();
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
    // un campo di tensione il rapporto fra i due vale 2,16 sotto peso proprio
    // e arriva a 5,09 su un carico concentrato (misurato sull'as-built), e una
    // scala fino al massimo schiaccerebbe quattordicimila nodi in fondo perche'
    // uno solo sta in cima. Chi supera il taglio prende un colore dichiarato,
    // e la legenda dice dov'e' il taglio e quanti nodi sono sopra: e'
    // un'informazione, non un buco.
    mostraMeshPerCampo(vertici, facce, valori, { taglio, sopraTaglio }) {
      const geometria = new THREE.BufferGeometry();
      geometria.setAttribute("position", new THREE.BufferAttribute(vertici, 3));
      geometria.setIndex(new THREE.BufferAttribute(facce, 1));
      geometria.computeVertexNormals();
      const colori = new Float32Array(valori.length * 3);
      // Un campo costante o tutto a zero non deve dividere per zero: la scala
      // resta un solo colore, non un crash ne' un taglio NaN che la renderebbe
      // silenziosamente uniforme.
      const soglia = taglio > 0 ? taglio : 1;
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
        const valore = valori[indice];
        // Un residuo NaN/Infinity nel campo non deve corrompere il resto della
        // riga di colore: resta al fondo della scala, dichiarato zero.
        const frazione = Number.isFinite(valore) ? Math.min(1, Math.max(0, valore / soglia)) : 0;
        colore.lerpColors(CHIARO, SCURO, frazione);
        colore.toArray(colori, indice * 3);
      }
      geometria.setAttribute("color", new THREE.BufferAttribute(colori, 3));
      gruppo.add(new THREE.Mesh(geometria, new THREE.MeshStandardMaterial({
        vertexColors: true, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide,
        clippingPlanes: pianiTaglio,
      })));
      descrivi(
        `campo su ${(facce.length / 3).toLocaleString("it")} facce, ` +
        `${sopraTaglio.toLocaleString("it")} nodi sopra il taglio`,
      );
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
