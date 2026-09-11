# Identità e autorevolezza di MeshRec come «programma vero»

**Domanda.** A parte guscio desktop e installer (ricercati da altri, qui esclusi), cosa rende un tool scientifico accademico credibile davanti a commissione, tutori e laboratorio? Come si presentano i tool di riferimento, come si diventa citabili, quali segnali di maturità costano poco, il nome «MeshRec» tiene, cosa si mostra in discussione.

**Stato.** Completa. Rete caduta una volta a metà; tutte le sezioni scritte. Un solo buco dichiarato: tempi mediani di revisione JOSS (pagina analytics non catturata) — marcato `[NON TROVATO]`.

**Tag.** `[V]` fonte primaria letta e catturata in `fonti/` · `[M]` misurato in sessione con comando · `[INF]` inferenza · `[NON TROVATO]`.

**Data.** 2026-09-11. Repo `/Users/mario/GitHub/Tesi`, branch `main`, HEAD `b711053`.

---

## 0. Premesse del brief verificate

Tutte lette da `/Users/mario/GitHub/Tesi`, `main`, HEAD `b711053`:

- `meshrec/pyproject.toml:1-4` → `name = "meshrec"`, `version = "0.1.0"`, descrizione in italiano; `:37-39` build backend `hatchling` (conta per la sezione 3.4). `[M]`
- Nessun `CITATION.cff` (né in radice né in `meshrec/`). `[M]` `ls CITATION.cff meshrec/CITATION.cff` → «No such file».
- **Correzione marginale al brief:** esiste `LICENSE` in radice, **MIT, © 2026 Mario Fiorenzoni**; GitHub lo riconosce (`gh repo view --json licenseInfo` → `mit`). Il brief non lo negava ma non lo diceva; cambia la sezione 2.4 (la licenza c'è già, resta da verificare che regga). `[M]`
- Nessun tag git (`git tag | wc -l` → 0), nessuna release GitHub (`gh release list` vuoto). `[M]`
- Favicon PNG in `data:` URI in `meshrec/src/meshrec/ui/index.html:12`, aggiunta per zittire il 404; nessuna schermata «Informazioni su», nessuna stringa di versione nella UI (`grep -i "version\|about\|informazioni" index.html` → vuoto). `[M]`
- `versione_corrente()` in `meshrec/src/meshrec/app/storico.py:160` è la versione dello storico annulla/ripeti, **non** la versione del programma: non c'è oggi nulla nel codice che esponga «MeshRec 0.1.0». `[M]`
- Repo GitHub `maeurong/Tesi`, pubblico, creato `2026-08-13T13:48:22Z`, 773 commit da `2026-08-12`, 10 topic già impostati (`scan-to-fem`, `point-cloud`, `reinforced-concrete`, …), descrizione «Pipeline scan-to-FEM da fotogrammetria», `homepageUrl` vuoto. `[M]` `gh repo view maeurong/Tesi --json createdAt,repositoryTopics,description,homepageUrl`
- `docs/meshreconstructorpro-panoramica.md:1-4`: il programma dei tutor è un eseguibile Windows nativo con CPython 3.12, PySide6/Qt6, Open3D, VTK/PyVista, TetGen, meshio. `[V]` (file interno)

---

## 1. Come si presentano i tool di riferimento

### 1.1 Schede

- **URL** https://gmsh.info/ · `[V]` (`fonti/gmsh-home.md`)
  **perché conta qui** è il tool accademico più vicino per pubblico (mesh FEM, autori universitari, ULiège/UCLouvain) e il modello più asciutto: una sola pagina fa da sito, download, manuale, licenza e citazione.
  **cosa se ne prende** la sequenza della pagina: nome + una riga descrittiva (*«a three-dimensional finite element mesh generator with built-in pre- and post-processing facilities»*), «Current stable release (version 4.15.2, 24 March 2026)» con data, licenza dichiarata due volte (GPL), frase esplicita *«If you use Gmsh please cite the following reference»* con l'articolo IJNME 2009, manuale in HTML+PDF+testo, due screenshot (tema chiaro/scuro). Il **sottotitolo descrittivo** e la **data accanto alla versione** sono i due dettagli da copiare.

- **URL** https://www.meshlab.net/ · `[V]` (`fonti/meshlab-home.md`) e https://raw.githubusercontent.com/cnr-isti-vclab/meshlab/main/README.md · `[V]` (`fonti/meshlab-readme.md`)
  **perché conta qui** tool nato in un laboratorio di ricerca (CNR-ISTI VCLab, Pisa), quindi la biografia più simile a quella che MeshRec vorrebbe avere; Eurographics Software Award.
  **cosa se ne prende** (a) la home è un **changelog di release datate** (2025.07 con ARM64, 2023.12 sul Microsoft Store…) con link alla pagina release di GitHub: la pagina «novità» *è* la prova di vita; (b) il README apre con `# ![MeshLab Logo](eye64.png) MeshLab` — icona 64 px inline nel titolo; badge di build e **badge DOI Zenodo** `10.5281/zenodo.5114037`; (c) sezione «cite»: *«if you are lazy just cite»* + BibTeX del record Zenodo del software **e** dell'articolo Eurographics Italian Chapter 2008. Due citazioni: una per il software (DOI Zenodo), una per il paper.

- **URL** https://www.cloudcompare.org/doc/wiki/index.php/Introduction · `[V]` (`fonti/cloudcompare-wiki-intro.md`) e https://raw.githubusercontent.com/CloudCompare/CloudCompare/master/README.md · `[V]` (`fonti/cloudcompare-readme.md`)
  **perché conta qui** è il tool che i tutor e il laboratorio usano per le nuvole di punti; la wiki racconta l'origine (EDF R&D 2004, pubblico dal 2009 sotto GPL) — la **storia dichiarata** è parte dell'autorevolezza.
  **cosa se ne prende** README minimo: badge `img.shields.io/github/release/...` come prima riga, licenza GPL con una frase su cosa comporta, link donazioni. Versione corrente 2.1.1 in home (`[M]` `curl … | grep`). Nessuna richiesta di citazione nel README catturato `[NON TROVATO]` — CloudCompare si regge sulla wiki e sul forum, non sulla citazione.

- **URL** https://www.paraview.org/ · `[V]` (`fonti/paraview-home.md`) e https://raw.githubusercontent.com/Kitware/ParaView/master/README.md · `[V]` (`fonti/paraview-readme.md`)
  **perché conta qui** modello «industriale» (Kitware): la home è un'immagine cliccabile che apre un video Vimeo; licenza BSD 3-clause.
  **cosa se ne prende** l'idea della **schermata cliccabile che apre il video** — costa una GIF/MP4 di 30 s e uno screenshot; e la scelta BSD/MIT come licenza «amichevole verso l'integrazione» (vedi 2.4).

- **URL** https://github.com/wjakob/instant-meshes · `[V]` (`fonti/instant-meshes-readme.md`)
  **perché conta qui** tool di ricerca (SIGGRAPH Asia 2015) mantenuto da un singolo autore: dimostra che un README solo, fatto bene, basta a farlo «considerare un programma».
  **cosa se ne prende** ordine del README: icona (`resources/icon.png`) in cima, una riga di adozione esterna (*«Since version 10.2, Modo uses the Instant Meshes algorithm»* — l'equivalente per MeshRec: «usato per il caso studio X nel laboratorio Y»), sezione «Screenshot» con un'unica immagine, download binari per tre OS, istruzioni di compilazione. Sezione citazione non presente nel README catturato `[NON TROVATO]`.

- **URL** https://github.com/isl-org/Open3D · `[V]` (`fonti/open3d-readme.md`)
  **perché conta qui** è già dipendenza di MeshRec (`meshrec/pyproject.toml:9`) e del programma dei tutor: il pubblico la conosce.
  **cosa se ne prende** logo orizzontale PNG come prima riga; tre badge CI (Ubuntu/macOS/Windows); comando di verifica `python -c "import open3d as o3d; print(o3d.__version__)"` — la **versione interrogabile da riga di comando** è un segnale di maturità gratuito (cfr. 3.4); screenshot del viewer + GIF; «Citation: Please cite our work» con l'arXiv 1801.09847.

- **URL** https://github.com/nschloe/meshio · `[V]` (`fonti/meshio-readme.md`)
  **perché conta qui** libreria di un singolo autore, MIT, che scrive `.inp` Abaqus — stesso formato d'uscita di MeshRec; è citabile senza paper: **badge DOI Zenodo** `10.5281/zenodo.1173115` accanto a PyPI/conda/downloads.
  **cosa se ne prende** la prova che Zenodo + badge basta a dare una citazione formale a una libreria senza articolo; e il fatto che il README elenca i formati supportati con le estensioni (`.inp`, `.ply`, `.vtu`…): MeshRec dovrebbe elencare ingressi (`.pcd`, `.ply`, `.xyz`) e uscite (`.inp`) allo stesso modo.

### 1.2 Tool nati in laboratorio con vita dopo

- **URL** https://joss.theoj.org/papers/10.21105/joss.01450 · `[V]` (`fonti/pyvista-joss.md`)
  **perché conta qui** PyVista (Sullivan & Kaszynski 2019, JOSS 4(37) 1450): wrapper VTK partito da due sviluppatori, oggi standard; JOSS gli ha dato DOI e riga bibliografica.
  **cosa se ne prende** la forma della citazione JOSS (autori, anno, titolo, rivista, volume, DOI) e il BibTeX pronto: è ciò che un tesista/collega copia in bibliografia. Origine da tesi: `[NON TROVATO]`.

- **URL** https://joss.theoj.org/papers/10.21105/joss.06105 · `[V]` (`fonti/sectionproperties-joss.md`)
  **perché conta qui** sectionproperties (van Leeuwen & Ferster 2024, JOSS 9(96) 6105): pacchetto Python di **ingegneria strutturale** (proprietà di sezione FEM), due autori, pubblicato su JOSS cinque anni dopo la nascita — dimostra che nel dominio di MeshRec la strada JOSS esiste ed è percorsa da progetti piccoli.
  **cosa se ne prende** il precedente di dominio da citare quando si spiega ai tutor cosa sia JOSS. Origine da tesi: `[NON TROVATO]`.

- **URL** https://cris.unibo.it/bitstream/11585/895272/1/1-s2.0-S235271102200067X-main.pdf · `[V]` (`fonti/cloud2fem-softwarex-pdf.md`) e https://github.com/gcastellazzi/Cloud2FEM · `[V]` (`fonti/cloud2fem-github.md`), https://github.com/gcastellazzi/Cloud2FEM-portable · `[V]` (`fonti/cloud2fem-portable.md`)
  **perché conta qui** Cloud2FEM (Castellazzi, Lo Presti, D'Altri, de Miranda 2022, *SoftwareX* 18, 101099; DICAM, Università di Bologna) fa **esattamente il mestiere di MeshRec** — nuvola di punti di strutture esistenti → mesh FEM — ed è il precedente italiano più vicino. È l'esempio da conoscere prima della discussione: un commissario che lo conosce chiederà «in cosa differisce».
  **cosa se ne prende** (a) la **tabella metadati di SoftwareX** (`fonti/cloud2fem-softwarex-pdf.md` righe 43-49): «Current code version v1.0 · Permanent link · Legal code license GPL v3 · Code versioning system used: **None** · languages Python · dependencies PyQt5, PyQtGraph, VisPy, NumPy, pyntcloud, Shapely, ezdxf» — è la «carta d'identità» minima che una rivista chiede a un software, e va bene come slide (vedi 5); nota che Cloud2FEM dichiara *nessun* versionamento: MeshRec con 773 commit e un tag è già oltre `[INF]`; (b) README che apre con la citazione del paper e tre figure della GUI; (c) repo separato «portable» per Windows — la distribuzione è un problema che hanno risolto a parte, come qui. Differenza di metodo (voxel/esaedri contro ricostruzione di superficie + tetraedri) e di scope (Cloud2FEM si ferma alla mesh; MeshRec salva parametri e misure di qualità per passo, `README.md:6-9`) `[INF]` — da verificare leggendo il paper per intero prima della discussione.

### 1.3 Denominatore comune (sintesi `[INF]` sulle otto schede)

1. **Nome corto + una riga descrittiva** («Gmsh: a three-dimensional finite element mesh generator…», «Cloud2FEM: a finite element mesh generator based on point clouds…»).
2. **Icona/logo nella prima riga del README** (MeshLab, Instant Meshes, Open3D).
3. **Versione con data** e pagina di release/download (Gmsh, MeshLab, CloudCompare).
4. **Licenza dichiarata** in README e file (tutti).
5. **Frase «se usi X, cita»** con BibTeX — paper o record Zenodo (Gmsh, MeshLab, Open3D, meshio).
6. **Uno screenshot** (tutti) e spesso un video/GIF (ParaView, Open3D).
7. **Manuale** almeno in HTML (Gmsh, CloudCompare wiki, Open3D docs).
8. **Badge** release/DOI/CI (MeshLab, CloudCompare, Open3D, meshio).

Ciò che manca oggi a MeshRec rispetto a questa lista: 2, 3, 5, 6 (screenshot nel README: `[NON TROVATO]` in `README.md:1-40`), 8. Ha già 1 (descrizione repo), 4 (MIT), 7 in forma di `docs/`.

---

## 2. Citabilità e riconoscimento

### 2.1 `CITATION.cff`

- **URL** https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files · `[V]` (`fonti/github-citation-files.md`)
  **perché conta qui** con il file nel branch predefinito GitHub mostra «Cite this repository» nella barra laterale, con **APA e BibTeX generati** (`@software{...}` con versione e DOI). È il modo più economico di far apparire il repo «come un programma qualsiasi» a chi lo apre.
  **cosa se ne prende** l'esempio minimo (cff-version, message, authors con ORCID, title, version, doi, date-released, url) e il campo `preferred-citation` per puntare, in futuro, alla tesi o a un articolo invece che al software.

- **URL** https://citation-file-format.github.io/ · `[V]` (`fonti/cff-home.md`) e https://raw.githubusercontent.com/citation-file-format/citation-file-format/main/schema-guide.md · `[V]` (`fonti/cff-schema-guide.md`)
  **perché conta qui** spiega *perché* il file serve (nome del software, versione da citare, chi sono gli autori — domande che chi cita non sa rispondere da solo) e chi lo legge: GitHub, Zenodo, Zotero.
  **cosa se ne prende** il tipo `thesis` esiste in CFF (`schema-guide.md`, elenco `type:`): `preferred-citation` può puntare alla tesi stessa dopo la discussione, con `institution` e `year`. Esiste un form web (cff-initializer) per non scriverlo a mano.

- **URL** https://help.zenodo.org/docs/github/describe-software/citation-file/ · `[V]` (`fonti/zenodo-citation-file.md`)
  **perché conta qui** Zenodo legge `CITATION.cff` per popolare il record del DOI; se c'è anche `.zenodo.json` usa solo quello.
  **cosa se ne prende** un solo file, `CITATION.cff`, senza `.zenodo.json`: meno da tenere allineato.

### 2.2 DOI via Zenodo

- **URL** https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content · `[V]` (`fonti/github-zenodo.md`) e https://help.zenodo.org/docs/github/ · `[V]` (`fonti/zenodo-github.md`)
  **perché conta qui** cinque passi (login con GitHub, autorizza, toggle sul repo) e **ogni release GitHub produce un DOI nuovo** più un concept-DOI stabile; Zenodo archivia anche su Software Heritage.
  **cosa se ne prende** il DOI è la cosa che un commissario riconosce come «pubblicazione»: va in bibliografia della tesi (*Fiorenzoni, M. (2026). MeshRec (Version 1.0.0) [Computer software]. https://doi.org/10.5281/zenodo.NNNN*) e nel badge del README. Prerequisito: la release (3.2). Costo: 30 minuti dopo la release. Ordine obbligato: prima `CITATION.cff` e `LICENSE`, poi il toggle, poi la release — Zenodo legge i metadati al momento della release.

- **URL** https://force11.org/info/software-citation-principles-published-2016/ · `[V]` (`fonti/force11-software-citation.md`)
  **perché conta qui** i sei principi (importance, credit, unique identification, persistence, accessibility, **specificity** = versione) sono la base normativa che le riviste citano quando accettano software in bibliografia.
  **cosa se ne prende** l'argomento da usare con i tutor: «il software si cita come un articolo, con versione e identificatore persistente» (§1, §6). Da lì discendono CFF + DOI.

### 2.3 JOSS: requisiti reali e se ha senso per una tesi

- **URL** https://joss.readthedocs.io/en/latest/submitting.html · `[V]` (`fonti/joss-submitting.md`) e https://joss.readthedocs.io/en/latest/review_criteria.html · `[V]` (`fonti/joss-review-criteria.md`), https://joss.theoj.org/about · `[V]` (`fonti/joss-about.md`)
  **perché conta qui** JOSS è la rivista con DOI Crossref e ISSN che pubblica *software*, gratis (diamond OA), con revisione pubblica su GitHub. È la forma massima di «programma riconosciuto» accessibile a un singolo autore.
  **cosa se ne prende** i requisiti misurabili:
  - «obvious research application», licenza OSI, «feature-complete», pacchettizzato secondo le convenzioni Python, non «minor utility»;
  - **repo pubblico da più di sei mesi** con sviluppo distribuito nel periodo — «We run automated checks on commit distribution — a repo dump is not a history»; progetti sviluppati in privato non sono eleggibili finché non c'è storia pubblica;
  - per **autore singolo** la soglia si può passare con più indicatori insieme: storia di commit, **release taggate o changelog, test e CI, documentazione chiara, CONTRIBUTING, dichiarazione di supporto**; «single author with no evidence of community engagement… not acceptable» — ma «the author list itself as evidence of collaborative context»: un tesista con relatore/laboratorio coautori è considerato diverso da un solitario;
  - se il software è pronto, il paper (`paper.md`: titolo, sommario, statement of need, riferimenti) costa «perhaps an hour or two»; risposte ai revisori entro 2 settimane, modifiche entro 4-6; ad accettazione: tag + deposito Zenodo con DOI;
  - AI usage disclosure obbligatoria per codice/doc/paper assistiti — rilevante per questo repo `[INF]`;
  - tempi mediani da sottomissione a pubblicazione: `[NON TROVATO]` (pagina analytics non catturata).
  **Per la tesi** `[INF]`: repo pubblico dal 2026-08-13 → i sei mesi scadono il **2027-02-13**; con discussione al 19/09/2026 JOSS è **post-tesi**, non pre. Ha senso come «prossimo passo» dichiarato in discussione, non come deliverable. Ciò che JOSS chiede (release taggate, changelog, test, docs, CONTRIBUTING) coincide con la lista a basso costo della sezione 3: farlo ora prepara JOSS senza costare JOSS.

### 2.4 Licenza per un lavoro di tesi in un ateneo italiano (senza consulenza legale)

- **URL** https://didattica.polito.it/guida/2025/it/diritto_autore_magistrale?cds=932&sdu=32 · `[V]` (`fonti/polito-diritto-autore-guida.md`) e https://www.polito.it/sites/default/files/2022-09/DIRITTO_AUTORE_ITA.pdf · `[V]` (`fonti/polito-diritto-autore-pdf.md`)
  **perché conta qui** guida ufficiale di un ateneo tecnico italiano agli studenti magistrali: *«Chi ha redatto la tesi è l'autore… ha piena titolarità dei diritti, sia morali che patrimoniali»*; le tesi possono contenere «programmi per elaboratore (software)» tutelati dal diritto d'autore, e per il software *«si raccomanda di darne comunicazione ai competenti Uffici»* (la segretazione/embargo è per i brevettabili). Rimanda al regolamento IP d'ateneo, accettato all'iscrizione.
  **cosa se ne prende** tre mosse: (1) il codice è dell'autore salvo regolamento contrario — quindi la riga `Copyright (c) 2026 Mario Fiorenzoni` nel `LICENSE` è coerente; (2) leggere il **regolamento proprietà intellettuale del proprio ateneo** (qui `[NON TROVATO]`: l'ateneo di Mario non è nel brief) cercando le parole «studenti», «tesi», «software»; (3) comunicare ai tutor per iscritto la licenza scelta prima della discussione — costo: una mail.

- **URL** https://amm.units.it/normativa/regolamenti/articolo-54242/art-4-titolarit-diritti-propriet-intellettuale-sulle-creazioni · `[V]` (`fonti/units-art4-titolarita.md`)
  **perché conta qui** esempio di regolamento d'ateneo (Trieste) con l'articolo dedicato: c. 6 *«La titolarità dei diritti derivanti da un'invenzione brevettabile realizzata da studenti spetta agli stessi»*; è il personale strutturato/non strutturato e i **dottorandi** a cedere all'ateneo (c. 1, 3, 4). Uno studente magistrale non è in quelle categorie.
  **cosa se ne prende** la struttura tipica: studenti = titolari, con opzione di deposito a nome dell'università su richiesta. Cambia se ci sono borse, contratti o dati di terzi (il rilievo del laboratorio `[INF]`: verificare chi possiede la nuvola di punti del caso studio, non il codice).

- **URL** https://www.brocardi.it/legge-diritto-autore/titolo-i/capo-iii/sezione-i/art12bis.html · `[V]` (`fonti/lda-art12bis.md`)
  **perché conta qui** art. 12-bis L. 633/1941: il datore di lavoro è titolare del software creato dal **lavoratore dipendente** nelle sue mansioni; la nota estende per interpretazione a rapporti di collaborazione. Uno studente non è dipendente `[INF]` — ma il rischio sta nei rapporti «ibridi» (tirocinio retribuito, borsa).
  **cosa se ne prende** se il lavoro è stato svolto senza contratto con l'ateneo o il laboratorio, l'articolo non si applica; se c'è un contratto, leggere la clausola IP.

- **URL** https://choosealicense.com/licenses/ · `[V]` (`fonti/choosealicense-licenses.md`) e https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510 · `[V]` (`fonti/plos-good-enough-practices.md`)
  **perché conta qui** spettro copyleft→permissivo; Wilson et al. 2017 (*Good enough practices*, §3d) raccomandano per il software **MIT/BSD/Apache** e sconsigliano le clausole NC perché ostacolano il riuso; la guida Polito consiglia CC BY-NC-ND *per il testo della tesi*, non per il codice.
  **cosa se ne prende** MIT già scelto è coerente con la letteratura e con meshio/Open3D/ParaView (BSD); i tool GPL (Gmsh, MeshLab, CloudCompare, Cloud2FEM) sono progetti con strategia commerciale duale o storica. Un dettaglio da chiudere: `LICENSE` è in radice del repo `Tesi`, non in `meshrec/`; se il pacchetto viene distribuito da solo (wheel, guscio) va copiato o referenziato in `pyproject.toml` (`license = {file = ...}`) `[INF]`. Tesi (testo) e codice possono avere licenze diverse: CC BY(-NC-ND) per il PDF, MIT per il codice — la guida Polito lo lascia all'autore.

---

## 3. Segnali di maturità a basso costo

Costo in ore di Mario, esclusa l'implementazione UI che spetta a chi dispaccia.

### 3.1 Versionamento semantico e CHANGELOG (1-2 h)

- **URL** https://semver.org/ · `[V]` (`fonti/semver.md`)
  **perché conta qui** regola 4: «Major version zero (0.y.z) is for initial development. Anything MAY change»; regola 5: «Version 1.0.0 defines the public API». `0.1.0` oggi in `pyproject.toml:3` dice al lettore «non finito».
  **cosa se ne prende** `[INF]` per un software di tesi la «API pubblica» è il contratto ingressi→deck (`.pcd/.ply/.xyz` → `.inp` + parametri e misure per passo): taggare **`v1.0.0` alla consegna della tesi** è onesto e leggibile; correzioni post-discussione → `1.0.x`; nuovo prior/passo → `1.1.0`.

- **URL** https://keepachangelog.com/en/1.1.0/ · `[V]` (`fonti/keepachangelog.md`)
  **perché conta qui** formato standard: sezione `Unreleased` in testa, versioni in ordine inverso, date ISO 8601, gruppi `Added/Changed/Fixed`.
  **cosa se ne prende** un `CHANGELOG.md` con una sola voce `1.0.0 — 2026-09-19` scritta a mano dai titoli delle PR (#186-#196 e precedenti) basta; le versioni successive si accumulano.

### 3.2 GitHub Releases con note (30 min per release)

- **URL** https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository · `[V]` (`fonti/github-releases.md`) e https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes · `[V]` (`fonti/github-auto-release-notes.md`)
  **perché conta qui** la release nasce da un tag, ha note, allegati (qui: il launcher/installer dei colleghi, il PDF del manuale), e le note si **generano dalle PR fuse** con un click; `.github/release.yml` le raggruppa per etichetta.
  **cosa se ne prende** il repo lavora già per PR (`b711053` è «Merge pull request #196»): «Generate release notes» produce l'elenco senza scrivere nulla. La release è anche l'evento che fa scattare il DOI Zenodo (2.2).

### 3.3 Badge nel README (15 min)

- **URL** https://shields.io/ · `[V]` (`fonti/shields-home.md`)
  **perché conta qui** badge dinamici (release GitHub, licenza, DOI Zenodo, Python version) e statici con testo libero.
  **cosa se ne prende** i quattro che i tool di riferimento usano: `github/release`, `license`, DOI Zenodo (badge fornito da Zenodo stesso), CI se esiste. Non di più: MeshLab ne ha due, CloudCompare uno.

### 3.4 Schermata «Informazioni su» con versione/commit/licenza/citazione (mezza giornata di implementazione, non di Mario)

- **URL** https://docs.python.org/3/library/importlib.metadata.html · `[V]` (`fonti/python-importlib-metadata.md`)
  **perché conta qui** `importlib.metadata.version("meshrec")` legge la versione dal pacchetto installato: **una sola fonte di verità** (`pyproject.toml`), niente costante duplicata nella UI.
  **cosa se ne prende** il server espone un endpoint tipo `/about` con `{name, version, commit, license, citation}` e la UI lo mostra in un pannello o nel piè di pagina già esistente, senza rifare la grafica. Il commit: `[INF]` o inciso al build, o `git rev-parse --short HEAD` a runtime se `.git` esiste, altrimenti «n/d».

- **URL** https://github.com/ofek/hatch-vcs · `[V]` (`fonti/hatch-vcs.md`)
  **perché conta qui** il backend è `hatchling` (`meshrec/pyproject.toml:37-39`): `hatch-vcs` fa derivare la versione dal **tag git** (`[tool.hatch.version] source = "vcs"`), così `v1.0.0` taggato = `1.0.0` in `importlib.metadata` senza toccare `pyproject.toml` a ogni release.
  **cosa se ne prende** opzionale; alternativa a costo zero: aggiornare a mano `version = "1.0.0"` prima del tag. Con hatch-vcs si evita di dimenticare l'allineamento; contro: una dipendenza di build in più e versione «sporca» (`1.0.0.dev3+g…`) fuori dai tag `[INF]`.

### 3.5 Associazione dei file (`.pcd`, `.ply`, `.yaml`) — dipende dal guscio, fuori perimetro

- **URL** https://learn.microsoft.com/en-us/windows/win32/shell/fa-intro · `[V]` (`fonti/ms-file-associations.md`)
  **perché conta qui** su Windows l'associazione è registrazione di ProgID nel registro («How to Register a File Type for a New Application»): la fa l'installer, non il programma.
  **cosa se ne prende** passare ai colleghi del guscio/installer; per macOS `CFBundleDocumentTypes` nell'`Info.plist` del bundle — pagina Apple non catturata `[NON TROVATO]`. Nota di prodotto `[INF]`: `.pcd/.ply` sono già di CloudCompare/MeshLab sulle macchine del laboratorio; contendersi l'associazione è più fastidio che autorevolezza. Ha senso solo per un formato proprio (es. il `.yaml` di configurazione del caso, o una cartella-corsa).

### 3.6 Manuale breve: PDF o sito (1-2 giorni)

- **URL** https://raw.githubusercontent.com/squidfunk/mkdocs-material/master/README.md · `[V]` (`fonti/mkdocs-material-readme.md`) e https://squidfunk.github.io/mkdocs-material/ · `[V]` (`fonti/mkdocs-material.md`)
  **perché conta qui** è lo standard de facto per la doc dei pacchetti Python (screenshot nel README, `mkdocs.yml` + Markdown); pubblica su GitHub Pages con un'azione. `docs/` ha già decine di file Markdown (`docs/validazione/` 20+ file) — la materia prima c'è.
  **cosa se ne prende** `[INF]` un sito con 4 pagine (Installazione, Avvio, Gli undici passaggi, Citazione) più il rimando alle ricerche; il PDF si ottiene dallo stesso sorgente. Costo vero: scegliere cosa *non* mettere. Il sito dà anche un `homepageUrl` al repo, oggi vuoto `[M]`.

### 3.7 Video/GIF di 30 s e screenshot (1-2 h)

- **URL** https://support.apple.com/en-us/102618 · `[V]` (`fonti/apple-screen-record.md`)
  **perché conta qui** Shift-Cmd-5 registra lo schermo o una porzione senza installare nulla.
  **cosa se ne prende** un MP4 di 30 s su una corsa del caso studio, e uno screenshot del viewport three.js per il README (pattern ParaView/Open3D). Convertire in GIF solo se il README deve animarsi; altrimenti link al MP4 nella release.

### 3.8 Logo senza grafico (1-2 h)

- **URL** https://lucide.dev/license · `[V]` (`fonti/lucide-license.md`)
  **perché conta qui** icone ISC/MIT: uso, modifica e ridistribuzione permessi anche a fini commerciali, con nota di copyright — quindi un glifo Lucide può diventare l'icona di MeshRec senza rischio di licenza.
  **cosa se ne prende** il pattern accademico è **un glifo semplice + il nome in un font di sistema** (MeshLab: un occhio 64 px; Instant Meshes: icona quadrata; Open3D: wordmark). Un glifo di rete/mesh (`hexagon`, `box`, `scan`, `grid-3x3` in Lucide) ricolorato in un colore già in uso nella UI.

- **URL** https://inkscape.org/ · `[V]` (`fonti/inkscape-home.md`)
  **perché conta qui** editor vettoriale libero: da un SVG Lucide si esportano `icon.png` 64/256/512 e il favicon; gli stessi PNG servono ai colleghi del guscio (`.icns`/`.ico`).
  **cosa se ne prende** una sola sorgente SVG in `meshrec/src/meshrec/ui/` che sostituisce il PNG in `data:` URI di `index.html:12` — il commento lì spiega che si è evitato l'SVG per l'`xmlns` bloccato dal banco di rete; un PNG esportato da Inkscape resta compatibile con quel vincolo `[INF]`.

### 3.9 Lista di controllo «software robusto» (0 h: è una verifica)

- **URL** https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005412 · `[V]` (`fonti/plos-ten-rules-robust.md`)
  **perché conta qui** Taschuk & Wilson 2017, *Ten simple rules for making research software more robust*: le 10 regole sono ciò che un revisore di software scientifico controlla.
  **cosa se ne prende** stato MeshRec `[INF]` dai file letti: R1 version control ✓; R2 documentazione ✓ (`README.md`, `docs/`); R4 «version your releases» ✗ (0 tag); R6 build tool/package manager ✓ (`uv sync`); R7 no privilegi root ✓; R9 «small test set» — 590+ test noti dalla memoria di progetto, da rimisurare; R10 «identical results for identical inputs» — è la promessa di prodotto (`README.md:6-9`), da mostrare in discussione (5.3). Manca solo R4, che è la sezione 3.1-3.2.

---

## 4. Nome: «MeshRec» tiene?

### 4.1 Collisioni misurate `[M]` (2026-09-11)

| controllo | comando | esito |
|---|---|---|
| PyPI `meshrec` | `curl -o /dev/null -w "%{http_code}" https://pypi.org/pypi/meshrec/json` | **404** — libero |
| PyPI `mesh-rec` | idem | 404 — libero |
| org/utente GitHub `meshrec` | `curl … https://github.com/meshrec` | 404 — libero |
| `meshrec.org`, `meshrec.io` | `curl` | 000 — DNS non risolve, non registrati |
| repo GitHub con «meshrec» | `gh search repos meshrec --limit 10 --json fullName,stargazersCount` | `Tsyshnatiy/Meshrec` (0 stelle, senza descrizione); il resto sono `MeshReconstruction`/`MeshReconstructor` (max 182 stelle, `Magnus2/MeshReconstruction`, marching cubes C++) |
| web | WebSearch `"MeshRec" software mesh` | nessun prodotto con quel nome; vicini di nome: MeshInspector, MeshLab, Meshmixer, MESHFREE |

Conclusione `[INF]`: **il nome tiene**. Nessun pacchetto, nessun prodotto, nessun dominio. Il vicino più stretto è il `MeshReconstructorPro` dei tutor — e qui la vicinanza è un pregio: dice «stessa famiglia, nuova generazione» a chi conosce il vecchio.

### 4.2 Il vero problema d'identità: `maeurong/Tesi`

`[M]` il repo si chiama `Tesi`, non `meshrec`. Ogni URL, badge, citazione e DOI Zenodo porterà «Tesi» — il contrario di «considerato come un programma qualsiasi». GitHub rinomina con redirect automatico dei vecchi URL (documentato nelle stesse pagine release/repo lette; il remote locale va aggiornato con `git remote set-url`). Costo: 10 minuti; da fare **prima** della release e del toggle Zenodo, perché il record DOI congela il nome.

### 4.3 Sottotitolo

Pattern osservato (1.3, punto 1): nome + una riga. Candidati coerenti con `PRODUCT.md` e con la descrizione repo già impostata («Pipeline scan-to-FEM da fotogrammetria»):

- **MeshRec — dal rilievo al modello FEM** (italiano, per tesi e commissione);
- **MeshRec — from scan to FEM** (inglese, per README/JOSS; il topic `scan-to-fem` c'è già);
- variante lunga alla Gmsh, per la prima riga del README: «MeshRec: pipeline riproducibile da nuvola di punti fotogrammetrica a modello a elementi finiti di strutture in cemento armato» — è quasi la `description` di `pyproject.toml:4`.

Raccomandazione (non decisione): tenere «MeshRec», rinominare il repo, sottotitolo italiano in UI/tesi e inglese nel README. Registrare un dominio non serve: GitHub Pages con MkDocs (3.6) dà un URL sufficiente.

---

## 5. In discussione di tesi: cosa mostrano i candidati che presentano software

Fonti accademiche dirette su «demo dal vivo vs video in una discussione di tesi»: **scarse** — le guide degli atenei trovate parlano di discussioni a distanza, non di demo. Si compone da tre fonti primarie vicine.

- **URL** https://ewh.ieee.org/conf/vnc/2021/presenter.html · `[V]` (`fonti/ieee-vnc-presenters.md`)
  **perché conta qui** istruzioni ufficiali di una conferenza IEEE agli autori di demo: **video di backup obbligatorio** («serves as a backup in case of technical difficulties»), per le demo ≤5 min, «avoid spoken comments… use subtitles», 720p/1080p H.264, OBS gratuito.
  **cosa se ne prende** la regola: **demo dal vivo, video pronto**. Il video di 5 min sottotitolato è lo stesso artefatto che finisce nella release e nel README (3.7): un lavoro, tre usi.

- **URL** https://gradschool.umd.edu/coronavirus/advice-remote-dissertationthesis-defenses · `[V]` (`fonti/umd-remote-defense.md`)
  **perché conta qui** guida di una graduate school: «practice in the [same] environment», test dell'attrezzatura dal luogo della discussione, presenza 15 minuti prima, un responsabile tecnico che non sia il candidato.
  **cosa se ne prende** provare la demo **sul proiettore dell'aula** e sul portatile che si userà, con la corsa del caso studio già eseguita (lo storico delle corse in `meshrec serve` permette di aprire un risultato senza ricalcolare `[INF]` da `README.md:37-39`).

- **URL** https://joss.readthedocs.io/en/latest/review_criteria.html · `[V]` (`fonti/joss-review-criteria.md`) e la tabella metadati SoftwareX in `fonti/cloud2fem-softwarex-pdf.md:43-49` · `[V]`
  **perché conta qui** sono le griglie con cui *chi valuta software* lo valuta: statement of need, installazione, esempio d'uso, test/verifica, documentazione; e la scheda versione/licenza/dipendenze.
  **cosa se ne prende** `[INF]` struttura di 4-5 slide sul software, nell'ordine dei criteri: (1) *statement of need* — cosa non faceva MeshReconstructorPro (chiuso, non riproducibile) in una riga; (2) **carta d'identità**: nome, versione `1.0.0`, licenza MIT, DOI, dipendenze principali, dove scaricarlo — la tabella SoftwareX come slide; (3) architettura: gli undici passaggi come un solo diagramma; (4) **validazione**: le metriche già in `docs/validazione/` (benchmark NAFEMS, convergenza, mensola di Benzley, scarto C3D4/C3D10) — un numero per riga, con la fonte; (5) demo dal vivo di **un** passaggio con la stessa configurazione ripetuta = stesso risultato (PLOS R10, la promessa riproducibile), poi il deck `.inp` aperto in Abaqus — o il video se qualcosa cede.
  Cosa **non** mostrare `[INF]`: il codice; la UI intera passaggio per passaggio (undici passi dal vivo = tempo e rischio); i log.

---

## 6. Lista ordinata per rapporto autorevolezza/costo

Ordine: alto guadagno percepito da commissione/laboratorio diviso ore. Costi in ore di Mario, `[INF]`.

| # | azione | costo | cosa produce | sezione |
|---|---|---|---|---|
| 1 | Rinominare il repo `Tesi` → `meshrec`, sottotitolo in descrizione | 10 min | URL, badge e DOI col nome del programma | 4.2 |
| 2 | `CITATION.cff` in radice (autore, ORCID, versione, url) | 30 min | «Cite this repository» su GitHub, BibTeX pronto | 2.1 |
| 3 | `CHANGELOG.md` + `version = "1.0.0"` + tag `v1.0.0` + GitHub Release con note generate | 1-2 h | «Versione 1.0.0, 2026-09-19»: R4 di PLOS, release page come Gmsh/MeshLab | 3.1-3.2 |
| 4 | Toggle Zenodo prima della release → DOI → badge + riga in bibliografia della tesi | 30 min | il software diventa citabile con DOI | 2.2 |
| 5 | Screenshot del viewport + 4 badge nel README, elenco formati in/out | 1 h | il README somiglia a quelli della sezione 1 | 1.3, 3.3 |
| 6 | Icona: glifo Lucide + wordmark, SVG in Inkscape → PNG/favicon | 1-2 h | identità visiva; input per il guscio dei colleghi | 3.8 |
| 7 | Pannello/piè di pagina «Informazioni su»: nome, versione via `importlib.metadata`, commit, licenza, citazione | ½ giornata (dispatch) | il programma sa dire chi è; nessuna grafica nuova | 3.4 |
| 8 | Video 5 min sottotitolato della corsa sul caso studio (backup demo + release + README) | ½ giornata | assicurazione per la discussione, materiale per il README | 3.7, 5 |
| 9 | Mail ai tutor: licenza MIT del codice, regolamento IP d'ateneo letto | 1 h di lettura + 1 mail | nessuna sorpresa in discussione | 2.4 |
| 10 | Sito MkDocs Material (4 pagine) su GitHub Pages, PDF derivato | 1-2 giorni | manuale utente, `homepageUrl` | 3.6 |
| 11 | Associazione file | 0 h per Mario | ai colleghi del guscio; solo per un formato proprio | 3.5 |
| 12 | JOSS | settimane, non prima del 2027-02-13 | DOI Crossref + revisione pubblica | 2.3 |

**Raccomandazione** (marcata come tale; decide Mario): fare 1-5 in blocco in **mezza giornata**, nell'ordine scritto (il rename prima del DOI, il CFF prima della release), poi 6-8 nella settimana prima della discussione. 10 e 12 sono «vita dopo la tesi» e vanno *dichiarati* in discussione come prossimi passi, non fatti ora. Non registrare domini, non cambiare nome.

---

## Artefatti consultati

Interni (`/Users/mario/GitHub/Tesi`, `main`, `b711053`): `PRODUCT.md`, `README.md:1-40`, `LICENSE:1-3`, `meshrec/pyproject.toml:1-39`, `meshrec/src/meshrec/ui/index.html:10-14`, `meshrec/src/meshrec/app/storico.py:160-170`, `docs/meshreconstructorpro-panoramica.md:1-30`, elenco `docs/validazione/`, `graphify query "identità del programma: nome, versione, licenza, citazione, About, release"` (141 nodi, nessun nodo di versione-programma).

Esterni: 47 pagine in `docs/ricerca/fonti/` (47 `.md` + 47 `.provenance.json`), catturate con `defuddle 0.19.1`, `curl` (README grezzi) e `pdftotext` (due PDF). Scartate per contenuto vuoto: `gitlab.onelab.info` README di Gmsh (challenge anti-bot), pagina ScienceDirect di Cloud2FEM (sostituita dal PDF open access UniBo CRIS), pagina Apple `CFBundleDocumentTypes` (fetch fallito), PeerJ software citation principles (fetch fallito; sostituita dalla pagina FORCE11).

Skill: `research` (gate), `caveman:caveman`. `defuddle` usato come CLI da `cattura.sh`, non invocata come skill: la skill si limita a descrivere il comando `defuddle parse <url> --md`, già eseguito così.
