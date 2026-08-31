# MeshRec — come funziona

## A cosa serve

MeshRec parte da una scansione laser di una parete in muratura — una nuvola di
punti — e arriva a un modello a elementi finiti pronto per l'analisi, passando
per la superficie ricostruita e per il riempimento a tetraedri. Il programma che
sostituisce, `MeshReconstructorPro`, faceva un lavoro simile ma non citabile in
una tesi: interfaccia obbligata, parametri non salvati, nessuna misura della
qualità degli elementi, nessun confronto fra la superficie ottenuta e i punti da
cui nasce, riparazioni della geometria non ispezionabili. Qui ogni corsa conserva
i propri parametri e le proprie misure, quindi un risultato si può rifare e
difendere.

## Come si usa

Si avvia con `uv run meshrec serve`, oppure con doppio clic su `MeshRec.bat`
(Windows) o `MeshRec.command` (macOS): si apre nel browser un elenco delle corse
già fatte e la possibilità di crearne una nuova indicando un file di punti
(`.pcd`, `.ply`, `.xyz`). I passaggi si eseguono uno alla volta, e ognuno scrive
il proprio risultato e le proprie misure nella cartella della corsa, insieme alla
configurazione usata. Il materiale non viene chiesto all'inizio né indovinato: si
dichiara al passaggio 11, il primo che lo pretende. La configurazione del caso
studio è `casi/lab.yaml`; i valori citati sotto vengono da lì dove il caso
li fissa, altrimenti sono i predefiniti del programma.

## I tredici passaggi

**1. Caricamento** (`io.load_cloud`) — legge il file di punti e lo porta in
millimetri. Manopola: `input.scale`, nel caso studio `1000.0` perché la scansione
è in metri. Sbagliarla scala tutto il modello, e il controllo facoltativo
`expected_size` serve proprio a smascherarla.

**2. Segmentazione** (`segment.segment_cloud`) — isola l'oggetto dal resto della
scena. Nel caso studio `segment.method: crop`, cioè un ritaglio a scatola fra
`crop_min` e `crop_max`. Scatola stretta: si perdono pezzi di parete; larga:
restano pavimento e arredi, che poi la superficie ingloba. L'alternativa `auto`
individua i piani e i gruppi di punti da sola.

**3. Riduzione** (`surface.downsample`) — dirada i punti su una griglia cubica.
Manopola: `downsample.voxel_size`, `10.0` mm nel caso studio. Voxel più grande =
meno punti, corsa più veloce, dettaglio perso; più piccolo = più fedeltà e più
tempo in tutti i passaggi successivi.

**4. Normali** (`surface.estimate_normals`) — stima la direzione perpendicolare
alla superficie in ogni punto: senza, il passaggio 5 non sa cosa è dentro e cosa
è fuori. Manopola: `normals.knn`, 30 punti vicini. Pochi vicini = normali
rumorose; troppi = spigoli smussati.

**5. Ricostruzione** (`surface.reconstruct`) — trasforma i punti in una
superficie chiusa di triangoli, col metodo di Poisson. È il passaggio dove si
sceglie quanto è fine la superficie: `surface.poisson_depth`, `7` nel caso studio
contro un valore predefinito di `9`. Ogni unità in più raddoppia circa il
dettaglio e il numero di triangoli (misurato su un muro: da 9 a 8 i triangoli
scendono da 908.118 a 221.369). Troppo alta, la superficie riproduce anche il
rumore; troppo bassa, arrotonda le aperture.

**6. Riparazione** (`repair.repair_surface`) — chiude la superficie e registra
ogni operazione fatta. Manopola: `repair.largest_component_only`, attiva: tiene
solo il pezzo più grande e butta i frammenti staccati. Disattivarla li conserva,
e il passaggio 9 fallirà su di essi.

**7. Qualità della superficie** — solo misure, nessuna manopola:
`quality.surface_metrics` (chiusura, bordi aperti, area, volume, forma dei
triangoli) e `quality.geometric_error`, che confronta la superficie con la nuvola
di partenza nei due versi.

**8. Semplificazione** (`surface.simplify`) — rifà i triangoli a misura uniforme.
Manopola: `simplify.enabled`, spenta nel caso studio e per impostazione
predefinita. Accesa, `remesh_target_len_pct` fissa il lato del triangolo in
percentuale della diagonale: alzarlo alleggerisce il modello ma allontana la
superficie dal rilievo.

**9. Tetraedrizzazione** (`volume.tetrahedralize_with_metrics`) — riempie di
tetraedri il volume racchiuso dalla superficie. Manopola principale:
`tet.min_ratio`, `1.8`, il rapporto raggio-spigolo massimo ammesso. Abbassarlo dà
elementi più regolari ma il riempimento può non arrivare in fondo: su questo muro
1.7 converge, 1.6 no. `tet.element` sceglie il tipo di elemento: `C3D10`
(tetraedro quadratico) è il predefinito; il caso studio usa `C3D4`, il lineare,
che è più rigido, proprio per misurare quanto quella rigidità costi.

**10. Qualità del volume** — solo misure, nessuna manopola che cambi la mesh:
`quality.volume_metrics` conta elementi rovesciati, angoli diedri minimi, volumi
e rapporti raggio-spigolo. `tet.reference_ratio` (1.8) è solo il metro con cui si
contano gli elementi fuori vincolo, non un vincolo imposto al riempimento.

**11. Esportazione** (`abaqus.export_model`) — scrive il modello a elementi
finiti: nodi, elementi, insiemi di nodi, materiale, carichi. Manopole: il
materiale (`analysis.material`, qui calcestruzzo C25/30 con modulo elastico
31.500 MPa e Poisson 0,2), la gravità (`9810` mm/s²) e `analysis.fixed_nset`,
l'insieme incastrato, qui `BASE`. Cambiare il modulo elastico cambia gli
spostamenti in proporzione inversa; cambiare l'insieme incastrato cambia lo
schema statico.

**12. Lettura geometrica del pezzo** (`calcola_prior`) — scompone l'oggetto in
membrature prismatiche a spessore quasi costante e ne misura sezioni e volumi.
Manopola: `wall.thickness_tolerance`, predefinita a 0,15, lo scarto entro cui due zone contano
come lo stesso spessore. Alzarla fonde membrature diverse in una; abbassarla
spezza una membratura reale in più pezzi.

**13. Soluzione** (`_step_solutore`, `_step_telaio`) — lancia il calcolo vero e
proprio. Non parte da solo: una corsa si ferma al 12 e questo passaggio si chiede
dalla sua schermata. Manopola: `solutore.nome`, cioè `calculix` sul modello
solido oppure `opensees` sul telaio di membrature del passaggio 12.

## Perché i risultati sono affidabili

Tre cose lavorano insieme. La prima: ogni passaggio che produce geometria è
seguito da misure che possono contraddirlo — la superficie viene confrontata con
la nuvola originale punto per punto (`quality.geometric_error`), i triangoli e i
tetraedri vengono pesati per forma e regolarità (`quality.surface_metrics`,
`quality.volume_metrics`). La seconda: la configurazione è salvata dentro la
corsa, quindi un numero che finisce in tesi è sempre riconducibile ai parametri
che l'hanno prodotto. La terza: quando si cambia un parametro, il programma sa
quali passaggi ne dipendevano e segna come non più validi solo quelli e i
successivi, lasciando validi tutti quelli a monte. Cambiare il materiale non
obbliga a rifare la ricostruzione della superficie; cambiare `poisson_depth` sì.
