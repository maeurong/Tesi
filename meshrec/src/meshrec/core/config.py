"""Modelli di configurazione: unico luogo dove un parametro ha un valore predefinito.

Sistema di unita di lavoro: mm, N, MPa, tonnellata, secondo.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

GRAVITY_MM_S2: float = 9810.0

NomeSet = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+$")]


def _caso_canonico_dei_sei(nome: str) -> str:
    """Uno dei sei nomi di faccia riscritto nel proprio caso canonico, gli altri intatti.

    `node_sets` porta i sei nomi di faccia nel caso canonico (`TOP`, non
    `top`): un confronto esatto a valle (`core/selezione.py`,
    `abaqus.write_inp`) fallirebbe su un nome che collide solo ignorando le
    maiuscole, ed e' un errore che arriva dopo la tetraedralizzazione invece
    che a validazione. Un nome fuori dai sei passa intatto: chi lo rifiuta e'
    la guardia a valle, che sa quali insiemi il deck contiene davvero.
    """
    return _mappa_casefold(NOMI_SET_DI_FACCIA).get(nome.casefold(), nome)


NomeSetDiFaccia = Annotated[NomeSet, AfterValidator(_caso_canonico_dei_sei)]


def _mappa_casefold(nomi: Iterable[str]) -> dict[str, str]:
    """`nome.casefold()` -> nome canonico: un solo spazio di nomi nel deck.

    `ccx` risolve gli `*NSET` senza distinguere le maiuscole (misurato in
    `docs/fase-6-cantiere/sonda-caso-nomi/README.md`): ogni punto che
    confronta un nome di set con un altro deve normalizzare il caso allo
    stesso modo, o due nomi che per `ccx` sono lo stesso `*NSET` passerebbero
    controlli diversi. Estratta qui perche' e' la quarta volta che il
    confronto ricorre (i sei nomi di faccia, i passi riservati, i selettori
    dichiarati, e ora `SelettoreNset.nome`): la soglia per estrarla era il
    terzo punto, e questo modulo l'ha gia' superata.
    """
    return {nome.casefold(): nome for nome in nomi}


def _nomi_senza_collisioni(
    nomi: Iterable[str],
    soggetto: str,
    plurale: str,
    tipo_di_set: str,
    fabbricati: Iterable[str],
) -> None:
    """Rifiuta i nomi dell'operatore che il deck confonderebbe fra loro o coi propri.

    Nel deck c'e' un solo spazio di nomi per tipo di insieme, e `ccx` lo
    risolve senza distinguere le maiuscole (misurato in
    `docs/fase-6-cantiere/sonda-caso-nomi/README.md`): due chiavi distinte in
    un dizionario python possono essere un solo nome nel file.

    Estratta perche' e' la seconda famiglia di nomi che la segue -- i selettori
    (`*NSET`) e le regioni (`*ELSET`) -- e due copie della stessa regola sono
    due copie che possono divergere. E' la stessa ragione per cui
    `_mappa_casefold` esiste, un livello piu' in su.

    `fabbricati` sono i nomi che il deck si costruisce da se' **di quel tipo di
    insieme**, e sono un parametro e non la costante dei sei: i sei sono
    `*NSET` e una regione e' un `*ELSET`, cioe' due spazi di nomi distinti.
    Confrontare entrambe le famiglie con i sei rifiutava la regione `BASE`, che
    non collide con niente, e accettava la regione `ALL_WALL`, che collide con
    l'insieme che le regioni partizionano.

    `soggetto` e `plurale` portano l'articolo con se' ("il selettore", "le
    regioni"): il genere cambia fra le due famiglie, e un articolo fisso nel
    formato produceva «il regione», che si vede a video.
    """
    casi_fabbricati = _mappa_casefold(fabbricati)
    visti: dict[str, str] = {}
    for nome in nomi:
        chiave = nome.casefold()
        if chiave in casi_fabbricati:
            raise ValueError(
                f"{soggetto} {nome!r} collide, ignorando le maiuscole, con "
                f"l'insieme {casi_fabbricati[chiave]!r} che il deck fabbrica da "
                "sé: nel deck c'è un solo spazio di nomi per tipo di insieme, "
                "case-insensitive (vedi "
                "docs/fase-6-cantiere/sonda-caso-nomi/README.md), e il "
                f"{tipo_di_set} dell'operatore lo sovrascriverebbe"
            )
        if chiave in visti:
            raise ValueError(
                f"{plurale} {visti[chiave]!r} e {nome!r} differiscono solo per "
                "maiuscole: nel deck sono lo stesso nome, case-insensitive "
                "(vedi docs/fase-6-cantiere/sonda-caso-nomi/README.md)"
            )
        visti[chiave] = nome


class _ModelloBase(BaseModel):
    """Base comune a ogni modello del file: rifiuta infinito e NaN nei campi decimali.

    Un valore infinito battuto in un campo decimale dell'interfaccia arriva al
    server come stringa; senza questo vincolo pydantic lo legge come infinito
    e lo scrive sul disco come .inf, da cui /api/config non torna piu'
    indietro (risponde null su quel campo). Sta sulla base e non sul singolo
    modello apparso nel difetto: i campi decimali sono sparsi su piu' modelli,
    e allow_inf_nan=False sul modello sbagliato lascia gli altri esposti con
    l'aria di averli coperti. pydantic unisce model_config lungo la catena di
    ereditarieta', quindi RunConfig puo' ancora aggiungere
    validate_assignment=True senza perdere questo vincolo.
    """

    model_config = ConfigDict(allow_inf_nan=False)


class Material(_ModelloBase):
    """Materiale elastico isotropo, dichiarato per intero dall'operatore.

    Nessun campo ha un predefinito, e la mancanza e' deliberata. Il predefinito
    precedente (muratura, 1500 MPa) e' finito in silenzio nella configurazione
    del telaio in calcestruzzo di `lab_frame`, dove il modulo elastico giusto e'
    piu di venti volte piu grande: nessuno aveva scelto quel materiale, era li'
    perche' il modello lo metteva da solo. La classe e i parametri meccanici
    sono una decisione di chi analizza, non un valore che il programma possa
    dedurre dalla nuvola o supplire per conto suo.
    """

    # I quattro `title` sono le etichette del riquadro «materiale», ripetute
    # qui verbatim e non riscritte: sono cio' che il rifiuto del server stampa
    # (`_etichetta_del_percorso` in app/server.py legge `title`), e senza di
    # essi sotto il bottone compariva «young: deve superare 0». `young` e
    # `density` nell'interfaccia non esistono -- lo dice gia' il docstring di
    # `analisi_dichiarata`, che manda chi sbaglia al pannello e non al YAML --
    # e una chiave non si stampa mai, si stampa la sua etichetta (PRODUCT.md).
    # Dove il titolo dice tutto, la `description` non lo ripete: sarebbe la
    # stessa frase due volte, una dentro l'altra.
    name: NomeSet = Field(
        title="nome",
        description=(
            "nome del materiale. Il vincolo non è cosmetico: il nome viene interpolato "
            "in `*MATERIAL, NAME=...` e il deck è scritto in ascii, quindi un carattere "
            "fuori tabella romperebbe l'esportazione dopo l'intera pipeline, e un a capo "
            "inietterebbe card nel deck senza che nulla se ne accorga"
        ),
    )
    young: float = Field(gt=0.0, title="modulo elastico E [MPa]")
    poisson: float = Field(ge=0.0, lt=0.5, title="coefficiente di Poisson")
    density: float = Field(gt=0.0, title="densità [t/mm³]")


class InputConfig(_ModelloBase):
    """Step 1: ingresso e scala."""

    path: Path = Field(title="file della nuvola di punti")
    scale: float = Field(
        default=1.0,
        gt=0.0,
        title="fattore di scala verso i millimetri",
    )
    max_points: int = Field(default=20_000_000, gt=0, title="punti massimi letti dal file")
    expected_size: tuple[float, float, float] | None = Field(
        default=None,
        title="dimensioni reali misurate",
        description="il controllo di scala dello step 1 le confronta con l'ingombro letto",
    )
    size_tolerance: float = Field(
        default=0.2,
        gt=0.0,
        title="scarto relativo ammesso sul controllo di scala",
    )
    spacing_sample: int = Field(
        default=20_000,
        gt=1,
        title="punti campionati per stimare la spaziatura",
    )
    seed: int = Field(default=0, title="seme del campionamento")


class SegmentConfig(_ModelloBase):
    """Step 2: segmentazione."""

    method: Literal["crop", "auto"] = Field(default="crop", title="come si isola l'oggetto")
    outlier_neighbors: int = Field(
        default=20,
        gt=0,
        title="vicini con cui si riconosce un punto isolato",
    )
    outlier_std_ratio: float = Field(
        default=2.0,
        gt=0.0,
        title="scarti tipo oltre i quali un punto è rumore",
    )
    crop_min: tuple[float, float, float] | None = Field(
        default=None, title="spigolo minimo del box di ritaglio [mm]"
    )
    crop_max: tuple[float, float, float] | None = Field(
        default=None, title="spigolo massimo del box di ritaglio [mm]"
    )
    plane_distance_factor: float = Field(
        default=3.0,
        gt=0.0,
        title="distanza dal piano, in multipli della spaziatura",
    )
    plane_max_count: int = Field(default=4, ge=0, title="piani estratti al massimo")
    plane_min_points_ratio: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        title="frazione minima di punti perché un piano conti",
    )
    cluster_eps_factor: float = Field(
        default=4.0,
        gt=0.0,
        title="raggio del gruppo, in multipli della spaziatura",
    )
    cluster_min_points: int = Field(default=50, gt=0, title="punti minimi perché un gruppo esista")
    cluster_index: int = Field(
        default=0,
        ge=0,
        description="0 è il gruppo più numeroso",
        title="quale gruppo si tiene",
    )


class DownsampleConfig(_ModelloBase):
    """Step 3: riduzione a voxel."""

    voxel_size: float | None = Field(
        default=None,
        description="vuoto: due volte la spaziatura media",
        title="lato del voxel [mm]",
    )
    voxel_factor: float = Field(
        default=2.0,
        gt=0.0,
        title="lato del voxel, in multipli della spaziatura",
    )


class NormalsConfig(_ModelloBase):
    """Step 4: normali."""

    knn: int = Field(default=30, gt=2, title="vicini con cui si stima la normale")
    orient_knn: int = Field(default=30, gt=2, title="vicini con cui si orientano le normali")


class SurfaceConfig(_ModelloBase):
    """Step 5: ricostruzione della superficie."""

    method: Literal["poisson"] = Field(default="poisson", title="algoritmo di ricostruzione")
    poisson_depth: int = Field(
        default=9,
        ge=4,
        le=14,
        title="profondità dell'ottree di Poisson",
        description=(
            "più alta, superficie più fitta: su muro, 9 -> 8 porta i triangoli "
            "da 908.118 a 221.369"
        ),
    )
    poisson_width: float = Field(default=0.0, ge=0.0, title="lato della cella più fine [mm]")
    poisson_scale: float = Field(default=1.1, gt=0.0, title="margine attorno alla nuvola")
    density_quantile: float = Field(
        default=0.05,
        ge=0.0,
        lt=1.0,
        title="quantile di densità sotto cui i vertici si scartano",
    )
    poisson_n_threads: int = Field(
        default=1, description="thread per il solutore Poisson; 1 = riproducibile, -1 = automatico",
        title="thread del solutore Poisson",
    )


class RepairConfig(_ModelloBase):
    """Step 6: riparazione."""

    largest_component_only: bool = Field(default=True, title="tiene il solo pezzo più grande")
    max_hole_area: float | None = Field(
        default=None,
        title="area oltre cui un'apertura viene segnalata [mm²]",
        description=(
            "vale sia per un ciclo di bordo chiuso sia per un cammino aperto"
        ),
    )
    join_components: bool = Field(default=False, title="unisce i pezzi staccati")


class SimplifyConfig(_ModelloBase):
    """Step 8: semplificazione, opzionale."""

    # `title` e' l'etichetta che il pannello mostra al posto della chiave:
    # «enabled» dice che si accende qualcosa senza dire che cosa, e il
    # rifacimento dei triangoli e' il piu' costoso degli step facoltativi.
    enabled: bool = Field(default=False, title="rifà i triangoli a misura uniforme")
    mode: Literal["remesh"] = Field(default="remesh", title="come si rifanno i triangoli")
    remesh_target_len_pct: float = Field(
        default=1.0,
        gt=0.0,
        title="lato del triangolo, in percentuale della diagonale",
    )
    taubin_iterations: int = Field(default=0, ge=0, title="passate di lisciatura Taubin")


class TetConfig(_ModelloBase):
    """Step 9: tetraedrizzazione."""

    min_ratio: float = Field(
        default=1.8,
        gt=0.0,
        title="rapporto raggio-spigolo massimo chiesto a TetGen",
        description=(
            "valori più bassi danno elementi più regolari, ma il raffinamento può "
            "non convergere su geometrie difficili. "
            "Sul muro di riferimento 1.6 e valori inferiori interrompono TetGen con un "
            "errore interno mentre 1.7 converge: il predefinito 1.8 non è quindi il "
            "valore più severo che porta a termine il lavoro, ma quello che tiene un "
            "decimo di margine sopra di esso. Misura completa da 1.4 a 2.5 in "
            "docs/fase-1-min-ratio.md"
        ),
    )
    max_volume: float | None = Field(
        default=None,
        gt=0.0,
        title="volume massimo dell'elemento [mm³]",
    )
    max_steiner_points: int = Field(
        default=-1,
        ge=-1,
        title="punti che TetGen può aggiungere",
        description=(
            "-1 = nessun limite. "
            "Il predefinito della libreria tetgen è 100000: su geometrie a scala "
            "reale quel tetto viene raggiunto e il raffinamento si ferma li, "
            "restituendo una mesh troncata che nessuna metrica segnalava"
        ),
    )
    nobisect: bool = Field(
        default=False,
        title="vieta a TetGen di suddividere le facce di ingresso",
        description=(
            "Serve dove la scala locale della superficie è minuscola: la "
            "suddivisione per invasione ricorre fino alla distanza fra lembi "
            "opposti, e su lab_frame.pcd, che ha strozzature sotto il millimetro, "
            "il raffinamento non converge a nessun min_ratio finché resta "
            "consentita. Attenzione: con nobisect attivo TetGen non aggiunge punti "
            "sul bordo, quindi su una superficie di ingresso grossolana max_volume "
            "può restare disatteso; il caso è segnalato con "
            "IneffectiveVolumeLimitWarning. Vedi docs/fase-1-min-ratio.md"
        ),
    )
    reference_ratio: float = Field(
        default=1.8,
        gt=0.0,
        title="metro con cui lo step 10 conta gli elementi fuori vincolo",
        description=(
            "metro fisso con cui lo step 10 conta la frazione di elementi fuori "
            "vincolo raggio-spigolo. Non è il vincolo chiesto a TetGen: nel "
            "motore di sweep min_ratio è una variabile della griglia, e una "
            "frazione contata contro il proprio min_ratio confronterebbe "
            "candidati contro vincoli diversi. Il valore 1.8 coincide con il "
            "predefinito di min_ratio perché è il metro con cui sono state "
            "misurate le due corse di riferimento (8,10% e 9,55%)"
        ),
    )
    element: Literal["C3D10", "C3D4"] = Field(
        default="C3D10",
        title="elemento del maglio di volume",
        description=(
            "C3D10 è il tetraedro quadratico ed è il predefinito: il manuale "
            "CalculiX dice del lineare «not suited for "
            "structural calculations... the element is too stiff», e la suite di "
            "verifica ufficiale non contiene un solo deck C3D4 su 610. C3D4 resta "
            "dichiarabile perché serve a misurare quanto quella rigidità costi su "
            "questa geometria"
        ),
    )


# La natura di un'azione, che decide quale coefficiente parziale e quale
# coefficiente di combinazione le spetta (#146, NTC 2018 Tab. 2.6.I). Non e' un
# attributo del carico in se': la stessa forza e' permanente su una struttura e
# variabile su un'altra, quindi la dichiara chi analizza e non la deduce il
# programma.
Natura = Literal["permanente_strutturale", "permanente_non_strutturale", "variabile"]

# La descrizione che le quattro azioni mostrano nel pannello accanto al campo
# `natura`. In una costante e non ricopiata quattro volte: e' testo che
# l'utente legge, e quattro copie sono quattro cose da tenere allineate a mano.
DESCRIZIONE_NATURA = (
    "natura dell'azione ai fini delle combinazioni (#146). Il predefinito "
    "è None e non una natura plausibile: «non dichiarata» è uno stato che "
    "il generatore delle combinazioni legge per rifiutarsi, perché senza "
    "la natura nessun coefficiente parziale può scegliersi da solo"
)


class SpintaOrizzontale(_ModelloBase):
    """Forza di massa orizzontale, come frazione dell'accelerazione di gravita.

    E' la stessa card `*DLOAD, GRAV` del peso proprio, diretta di lato: non
    tocca nessun set di faccia, quindi non pretende di sapere quale faccia sia
    quale. `FACE_FRONT` e `FACE_BACK` sono misurati inutilizzabili su una
    scansione reale, e i nomi dei set di faccia sono convenzioni e non
    identificazioni fisiche (PRODUCT.md): un carico applicato a una faccia
    nominata sarebbe applicato dove crediamo, non dove sappiamo.

    Nessun predefinito: il coefficiente e' una decisione di chi analizza.
    """

    coefficiente: float = Field(
        gt=0.0, description="frazione dell'accelerazione di gravita, adimensionale"
    )
    asse: Literal["x", "y"] = Field(
        description="asse orizzontale del modello lungo cui la spinta agisce"
    )
    natura: Natura | None = Field(default=None, description=DESCRIZIONE_NATURA)


class CaricoSommita(_ModelloBase):
    """Risultante verticale ripartita sui nodi di un insieme, per area tributaria.

    Pesata per area tributaria dalla Fase 6 (la stessa `ripartisci` dei
    carichi posizionati): un nodo non riceve piu' carico solo perche' la
    mesh e' piu' fitta li'. L'insieme e' comunque costruito per tolleranza e
    non e' la faccia superiore certificata del pezzo: quello resta da
    dichiarare accanto ai risultati di questo caso.
    """

    risultante: float = Field(
        gt=0.0, description="risultante in N, ripartita per area tributaria sui nodi"
    )
    nset: NomeSetDiFaccia = Field(description="insieme di nodi su cui ripartire, di norma TOP")
    natura: Natura | None = Field(default=None, description=DESCRIZIONE_NATURA)


class Modale(_ModelloBase):
    """Analisi in frequenza.

    Costa poco e smentisce molto: un modello mal vincolato ha una prima
    frequenza fuori scala. Misurato il 21/08/2026 sull'as-built del telaio:
    21,19 Hz col vincolo corretto, 4,03 Hz col vincolo su un piede solo.

    **Perche' `modi` ha un predefinito mentre il materiale non ce l'ha.** Il
    programma non indovina i parametri **meccanici**: modulo, coefficiente di
    Poisson, densita' e carichi li dichiara l'operatore, perche' nessun dato
    del rilievo li suggerisce. Il numero di modi non e' di quella specie. Non
    e' una proprieta' del corpo ne' una scelta di progetto: e' un parametro di
    **discretizzazione**, come `set_tolerance_factor`, e come quello ha un
    predefinito **misurato**. Chi ne dichiara uno proprio lo ottiene: il
    predefinito non e' un cancello.

    **Da dove viene il 40**, misurato il 26/08/2026 e ricostruibile con
    `docs/fase-7-cantiere/modi-per-la-normativa.py`. Il criterio non e' nostro:
    EN 1998-1 §4.3.3.3.1(3) chiede che i modi considerati catturino almeno il
    90% della massa partecipante, e le NTC 2018 lo riportano al §7.3.3.1 -- lo
    stesso criterio del verdetto `massa_modale` in `core/solve.py`, dove sta
    anche la nota che dichiara il contesto preso in prestito.

    La frazione non sale liscia al crescere dei modi: sale a **gradini**,
    perche' i modi entrano in coppie e ognuna porta la sua quota in un colpo.
    Su due corpi -- il telaio col materiale calcestruzzo e il ritaglio intero
    col materiale muratura -- la direzione traslazionale peggiore misura:

    ==========  =====================  =====================
    modi        telaio (14.103 nodi)   ritaglio (13.264 nodi)
    ==========  =====================  =====================
    20                        87,46%                  87,96%
    31                        88,31%                  88,93%
    32                        90,83%                  90,87%
    37                        93,96%                  90,89%
    40                        93,98%                  94,43%
    ==========  =====================  =====================

    **Perche' 40 e non 32**, che e' il piu' piccolo che regge. Il 32 sta sul
    bordo del gradino, con 0,83 punti di margine, e il gradino largo cade a
    **37 sul telaio ma a 38 sul ritaglio**: il bordo si sposta col maglio. Non
    e' un dettaglio, e' il difetto n. 66 -- TetGen e gmsh danno maglie diverse
    su Linux x86-64 e macOS arm64 a parita' di versione e di ingresso -- e un
    predefinito appoggiato sul bordo di un gradino mobile passa qui e fallisce
    altrove. Il 40 sta dentro il pianerottolo largo su entrambi i corpi, con
    circa quattro punti di margine e **otto modi sopra lo scavallamento**.

    **Cio' che questa misura non dimostra.** I due corpi non sono
    indipendenti: `lab_crop` e' il ritaglio della stessa scena che contiene il
    telaio, e scalare il modulo elastico non cambia le forme modali. Che
    concordino era atteso e non e' una seconda conferma. Il 40 e' un punto di
    partenza tarato su una scena sola, non una costante universale: su una
    struttura diversa puo' non bastare, ed e' precisamente per questo che il
    verdetto `massa_modale` resta a misurare la frazione invece di fidarsi del
    predefinito.
    """

    modi: int = Field(
        default=40,
        gt=0,
        description=(
            "numero di modi da estrarre. Il predefinito 40 è misurato e non "
            "indovinato: è il numero che porta ogni direzione traslazionale "
            "sopra il 90% di massa partecipante che EN 1998-1 §4.3.3.3.1(3) "
            "chiede, con margine. Sotto resta comunque il verdetto "
            "`massa_modale` a dire se è bastato"
        ),
    )


# Le etichette che `abaqus.export_model` assegna da se' agli altri casi di
# carico (il suo `casi_di_carico`), e che `solve.risolvi` usa come chiavi di
# `point_data`: non sono disponibili per il nome del passo di peso proprio.
NOMI_PASSO_RISERVATI = ("SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE")


class AnalysisConfig(_ModelloBase):
    """Materiale e analisi."""

    material: Material = Field(title="materiale del modello")
    gravity: float = Field(
        default=GRAVITY_MM_S2,
        gt=0.0,
        title="accelerazione di gravità [mm/s²]",
    )
    fixed_nset: NomeSetDiFaccia = Field(default="BASE", title="set di nodi incastrati")
    step_name: NomeSet = Field(default="GRAVITA", title="nome del passo di carico")
    set_tolerance_factor: float = Field(
        default=6.0,
        gt=0.0,
        title="tolleranza dei set di faccia, in multipli della spaziatura dei nodi",
        description=(
            "moltiplica la spaziatura dei nodi sul bordo del maglio di volume e "
            "dà la tolleranza con cui i set di faccia sono estratti. Il "
            "predefinito 6 è misurato: è il più piccolo intero che copre almeno "
            "il 95% della superficie d'appoggio su entrambe le corse di "
            "riferimento e per i quattro set utilizzabili. Il margine ha la "
            "stessa struttura di quello di tet.min_ratio: 5 è il primo valore "
            "che non regge (SIDE_LEFT di lab_crop si ferma al 94,37%), 4 il primo "
            "che crolla (77,89%), e sopra 6 si compra copertura marginale a "
            "prezzo pieno (a 8 il BASE del muro cresce del 41% per l'1,58% di "
            "copertura). Il predefinito precedente, 0,5 volte il volume medio "
            "dell'elemento, lasciava BASE al 55,78% della base sul muro e al "
            "34,76% su lab_crop. Vedi docs/fase-1-tolleranza-set.md"
        ),
    )

    @model_validator(mode="after")
    def _il_nome_del_passo_non_e_riservato(self) -> "AnalysisConfig":
        """Due passi con la stessa etichetta non sono due casi di carico.

        `solve.risolvi` indicizza `point_data` col nome del caso: `U_<CASO>`,
        `VM_<CASO>`. Se `step_name` ripete uno dei nomi che `export_model`
        assegna agli altri carichi, il secondo passo sovrascrive il primo e
        un caso sparisce dal `.vtu` -- nessuna eccezione, nessun avviso, un
        file con una chiave in meno di quanti passi il deck contiene.
        """
        if self.step_name.upper() in NOMI_PASSO_RISERVATI:
            raise ValueError(
                f"step_name={self.step_name!r} è un nome riservato: "
                f"{', '.join(NOMI_PASSO_RISERVATI)} sono le etichette che la "
                "pipeline assegna da sé agli altri casi di carico, e due passi "
                "sulla stessa etichetta si sovrascriverebbero a vicenda nel .vtu"
            )
        return self


class SolutoreConfig(_ModelloBase):
    """Quale motore risolve lo step 13, e dove sta il suo eseguibile (#139).

    Fuori dall'impronta per esclusione **secca** (`sweep.BLOCCHI_FUORI_IMPRONTA`):
    il motore e il percorso del suo binario non cambiano ne' il maglio ne' il
    deck, e sono una proprieta' della macchina che esegue, non
    dell'esperimento. Due corse identiche risolte da due motori diversi restano
    lo stesso esperimento, e devono finire nella stessa cartella.

    E' anche la ragione per cui `nome` puo' avere un predefinito **truthy**:
    dentro l'esclusione condizionata (`BLOCCHI_VUOTI_FUORI_IMPRONTA`) una
    stringa non vuota renderebbe il blocco sempre non vuoto, l'omissione non
    scatterebbe mai e le ventidue righe dei registri si muoverebbero.
    """

    # `title` e' l'etichetta che il pannello mostra al posto della chiave
    # (PRODUCT.md: una chiave non si stampa mai, si stampa la sua etichetta).
    # Senza, l'utente dello step 13 leggeva «nome» e «percorso»: nome di che
    # cosa.
    nome: Literal["calculix", "opensees"] = Field(
        default="calculix",
        title="motore di calcolo",
        description=(
            "quale motore risolve lo step 13. Enumerazione chiusa e non testo "
            "libero: un nome che nessuno scrittore di deck conosce fallirebbe "
            "soltanto allo step 13, cioè dopo l'intera elaborazione"
        ),
    )
    percorso: Path | None = Field(
        default=None,
        title="percorso dell'eseguibile",
        description=(
            "il campo lasciato vuoto dichiara «cercalo nel PATH», "
            "che è il caso normale di una macchina dove il solutore è "
            "installato a sistema: la stringa vuota non è quella dichiarazione, "
            "è la cartella corrente, ed è rifiutata insieme a ogni directory "
            "esistente. Un file che ancora non c'è passa: dire che il binario "
            "manca spetta al passo che lo esegue, non a questa configurazione"
        ),
    )

    @model_validator(mode="after")
    def _il_percorso_non_e_una_cartella(self) -> "SolutoreConfig":
        """Questo campo sceglie il binario che verra' eseguito.

        Il ramo del solutore lo consuma in un `subprocess.run` con lista di
        argomenti, quindi nessuna shell lo interpreta -- ma un `config.yaml`
        copiato da altri, o una `PUT /api/config`, sceglie comunque quale
        programma parte. I due modi in cui la scelta e' muta si vedono da qui e
        si chiudono da qui; che il file esista e funzioni no, e resta di
        `solve.verifica`, che lo dichiara invece di ripiegare in silenzio.

        Una sola guardia per due ingressi: `Path("")` e' `Path(".")`, quindi la
        stringa vuota -- che sembra «non dichiarato» e invece e' la cartella
        corrente -- cade nello stesso controllo della directory esistente. Un
        percorso che non esiste non e' una directory e passa.
        """
        if self.percorso is not None and self.percorso.is_dir():
            raise ValueError(
                f"solutore.percorso '{self.percorso}' è una directory e non un "
                "eseguibile. La stringa vuota finisce qui: vale la cartella "
                "corrente, non «non dichiarato». Per «cercalo nel PATH» il "
                "valore è None, cioè la chiave omessa"
            )
        return self


class RunConfig(_ModelloBase):
    """Esecuzione: percorsi e ripresa."""

    # La riga di comando e, in Fase 3, l'interfaccia assegnano questi campi
    # direttamente: senza validate_assignment pydantic non li verifica e un
    # valore fuori dominio arriva silenziosamente fino alla pipeline.
    model_config = ConfigDict(validate_assignment=True)

    out_dir: Path = Path("runs/default")
    from_step: int = Field(
        default=1,
        ge=1,
        le=12,
        description=(
            "la ripresa arriva fino allo step 12 (prior geometrico). Il tetto è "
            "stato 9 fino al 30/08/2026, quando gli step 10, 11 e 12 non erano "
            "punti di ripresa perché nessuno di loro ha lavoro costoso da "
            "saltare. Quel ragionamento valeva per una corsa intera e non per "
            "l'interfaccia, che esegue uno step alla volta assegnando "
            "from_step = to_step = numero: con il tetto a 9 quei tre step non "
            "erano eseguibili singolarmente, e il pannello rispondeva «Input "
            "should be less than or equal to 9» invece di eseguirli. "
            "Lo step 13 resta fuori: è l'unico che paga un processo esterno "
            "vero, e si invoca come azione con `meshrec solve`. Anche il solo "
            "prior ha la propria azione, `meshrec wall`."
        ),
    )
    to_step: int = Field(
        default=11,
        ge=1,
        le=13,
        description=(
            "ultimo step eseguito. Serve all'interfaccia, che esegue uno step "
            "alla volta: from_step e to_step uguali eseguono soltanto quello. "
            "Il tetto è 13 dalla Fase 5, ma il predefinito è 11 e non coincide "
            "più con esso, per due ragioni sovrapposte. La prima è di "
            "perimetro: il prodotto va dalla nuvola al deck `.inp` e si chiude "
            "lì, mentre il prior geometrico dello step 12 e il solutore dello "
            "step 13 appartengono a una linea di sviluppo che sta fuori -- "
            "docs/linea-analisi-integrata.md. Il predefinito coincide quindi "
            "con l'ultimo artefatto che il prodotto promette, e una corsa "
            "senza argomenti non calcola più nulla che i documenti dichiarino "
            "fuori. La seconda ragione riguarda il solo step 13 e precede la "
            "prima: dalla Fase 8 (#140) il solutore vive in una schermata "
            "dedicata e si invoca da lì. Chi li chiede esplicitamente li "
            "ottiene ancora -- la capacità non si perde, smette solo di essere "
            "ciò che accade senza chiederlo. Restano da conoscere le "
            "operazioni che il prior lo pretendono: l'attribuzione per regione "
            "dello step 11 quando la configurazione dichiara `regioni` (nessuna "
            "in casi/ lo fa oggi), `meshrec model`, `meshrec solve` con "
            "OpenSees, e `meshrec compare` per la chiusura di volume. Tutte si "
            "sbloccano con `meshrec wall`, e non con una corsa chiesta fino a "
            "12: con `regioni` dichiarate lo step 11 legge il prior prima che "
            "lo step 12 lo scriva, quindi una corsa 1->12 si ferma a 11 e non "
            "arriva mai a calcolarlo. "
            "Lo step 13 è del resto diverso dagli altri: è l'unico che paga "
            "un processo esterno vero (ccx) invece di lavoro in-process, e "
            "chi lo invoca su molti candidati -- uno sweep -- paga quel "
            "processo e i suoi artefatti per ciascuno, senza che la "
            "selezione se ne serva: misurati sull'unica corsa vera "
            "(runs/lab_telaio_v2), .frd 81 MiB, .vtu 8,2 MiB e .dat 4,3 MiB, "
            "cioè 93,6 MiB per candidato. sweep.py chiede to_step=11 "
            "esplicito al sottoprocesso invece di ereditare questo "
            "predefinito, e REQUIRED_STEPS in sweep.py non lo richiede: è una "
            "decisione del chiamante, che non deve dipendere da come il "
            "predefinito cambia. "
            "from_step non segue questo tetto e si ferma a 12: lo step 13 non è "
            "un punto di ripresa, perché non c'è lavoro a monte da saltare — ci "
            "sono artefatti da rileggere e un processo esterno da lanciare su di "
            "essi. La ragione per esteso è scritta là. "
            "Con validate_assignment attivo il validatore incrociato rifiuta "
            "ogni stato intermedio incoerente, e nessun ordine di assegnazione "
            "è sicuro: restringendo un intervallo verso l'alto rompe to_step "
            "per primo, verso il basso rompe from_step. I due campi si "
            "assegnano quindi insieme, con una sola validazione dell'oggetto "
            "intero (RunConfig.model_validate su model_dump aggiornato), mai "
            "uno alla volta"
        ),
    )

    @model_validator(mode="after")
    def _intervallo_coerente(self) -> "RunConfig":
        if self.to_step < self.from_step:
            raise ValueError(f"to_step={self.to_step} precede from_step={self.from_step}")
        return self


class WallConfig(_ModelloBase):
    """Step 12: il prior geometrico. Il pezzo e' un telaio di membrature prismatiche.

    Nessun valore qui dentro viene dal provino di laboratorio. Le soglie sono
    angoli, frazioni e multipli della spaziatura media della nuvola: la
    grandezza sorvegliata e' la costanza dello spessore, non il suo valore, e
    una soglia di quota sarebbe una costante tarata sulla scansione di oggi
    (secondo principio di prodotto).
    """

    cell_factor: float = Field(
        default=4.0,
        gt=0.0,
        title="lato della cella, in multipli della spaziatura",
        description=(
            "È il «metodo delle colonne» di docs/fase-1-tolleranza-set.md, dove il "
            "fattore 4 è misurato e non scelto: con una cella larga quanto la "
            "spaziatura la griglia diventa più fine dei triangoli della faccia e "
            "una colonna su dieci risulta vuota per puro artefatto di griglia"
        ),
    )
    spacing_sample: int = Field(
        default=20_000,
        gt=1,
        title="punti campionati per la spaziatura locale",
        description=(
            "stessa semantica del campionamento dello step 1, ma per il riempimento della "
            "sezione: la spaziatura del pezzo intero non descrive una regione "
            "campionata più rada (più lontana dallo scanner, parzialmente "
            "occlusa), e usarla al posto di quella locale sposta la soglia sulla "
            "grandezza sbagliata"
        ),
    )
    seed: int = Field(default=0, title="seme del campionamento")
    """Seme del campionamento di spacing_sample, stessa semantica di input.seed."""
    thickness_tolerance: float = Field(
        default=0.15,
        gt=0.0,
        lt=1.0,
        title="scarto relativo entro cui lo spessore è lo stesso",
        description=(
            "due celle adiacenti dentro questo scarto sono la stessa membratura. "
            "È la forma numerica di "
            "«quasi costante»: le membrature sono le regioni connesse a spessore "
            "quasi costante, e questa è l'unica soglia della scomposizione"
        ),
    )
    min_cells: int = Field(
        default=12,
        gt=0,
        title="celle minime perché una regione sia una membratura",
        description=(
            "sotto questo numero la regione è rumore di griglia e non ha abbastanza "
            "celle perché una direzione principale sia stimabile"
        ),
    )
    floor_angle_deg: float = Field(
        default=15.0,
        gt=0.0,
        lt=90.0,
        title="angolo dalla verticale entro cui un piano è pavimento [°]",
        description=(
            "un piano estratto con la normale entro questo angolo dalla verticale "
            "è candidato pavimento. Il pavimento non è una membratura e va "
            "scartato come piano, mai come quota"
        ),
    )
    floor_min_ratio: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        title="frazione minima di punti perché un piano sia il pavimento",
        description=(
            "un piano quasi orizzontale ed esteso è il pavimento, non la faccia "
            "superiore di una membratura. Le due "
            "condizioni valgono insieme: orizzontale e esteso"
        ),
    )
    contour_tolerance: float = Field(
        default=5.0,
        gt=0.0,
        title="tolleranza con cui il contorno viene semplificato [mm]",
        description=(
            "tolleranza [mm] con cui il contorno di sezione misurato viene "
            "semplificato. Un contorno con un vertice per punto rilevato porta "
            "nella mesh il rumore dello scanner invece della forma della sezione"
        ),
    )
    parallelism_deg: float = Field(
        default=5.0,
        gt=0.0,
        lt=90.0,
        title="angolo massimo fra le due facce opposte [°]",
        description=(
            "controllo intrinseco: angolo massimo fra le due facce opposte di una "
            "regione. Oltre, la regione non ha una sezione e il prior si rifiuta "
            "invece di darne una media priva di senso"
        ),
    )
    face_coverage: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        title="frazione minima di celle che vedono entrambe le facce",
        description=(
            "controllo intrinseco: frazione minima delle celle della regione che "
            "vedono entrambe le facce. E' la lezione già pagata su FACE_FRONT e "
            "FACE_BACK: una faccia vista da pochi punti produce un piano finto"
        ),
    )
    section_dispersion: float = Field(
        default=0.10,
        gt=0.0,
        title="dispersione relativa massima della sezione lungo l'asse",
        description=(
            "controllo intrinseco: dispersione relativa massima della sezione "
            "lungo l'asse. Oltre, la regione non è un prisma e viene riportata "
            "come tale invece di essere spacciata per una membratura. E' l'unica "
            "difesa contro una sezione a Π riportata come (pieno, affidabile): "
            "riempimento e affidabilità misurano l'ingombro locale per fetta e "
            "non vedono due membrature uguali unite a Π, che restano piene di "
            "bounding box da un capo all'altro"
        ),
    )
    section_fill_ratio: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        title="confine fra sezione piena e sezione vuota",
        description=(
            "confine fra i due esiti «pieno» e «vuoto» del riempimento di "
            "sezione: frazione (mediana sulle fette lungo l'asse) delle celle "
            "del proprio ingombro locale che la sezione occupa davvero. "
            "L'estensione e la dispersione sono entrambe misure di bounding box "
            "e non vedono un vuoto interno -- due membrature identiche unite a Π "
            "restano piene di bounding box da un capo all'altro. Stessa "
            "convenzione di metà di face_coverage: sotto metà delle celle del "
            "proprio ingombro, l'ingombro non è la sezione ma il suo "
            "contenitore. Non scarta nulla: il riempimento è un esito "
            "dichiarato, e il rifiuto spetta a chi costruisce i modelli"
        ),
    )
    density_dispersion_limit: float = Field(
        default=1.0,
        gt=0.0,
        title="dispersione massima delle distanze al vicino più prossimo",
        description=(
            "condizione di validità della misura di riempimento, non criterio "
            "di qualità del pezzo: dispersione massima delle distanze al vicino "
            "più prossimo rispetto alla loro media. Sopra questo limite lo "
            "scarto tipo eguaglia la media, la media smette di essere la scala "
            "della nuvola, e la griglia costruita su di essa (cell_factor per la "
            "spaziatura) non risolve più la parte rada: il riempimento si "
            "dichiara «non verificabile» invece di dare un numero che misura il "
            "campionamento e non la sezione. Il valore uno è il confine fra "
            "«descrivibile da una media» e no, non un numero tarato su un caso: "
            "una nuvola a densità unica sta ben sotto (una griglia regolare dà "
            "zero, un campionamento casuale uniforme di superficie circa 0,52), "
            "una nuvola con una parte rada oltre cell_factor volte la media "
            "sta sopra"
        ),
    )
    union_tolerance: float = Field(
        default=0.02,
        gt=0.0,
        title="scarto ammesso fra somma dei volumi e volume dell'unione",
        description=(
            "controllo intrinseco: scarto relativo ammesso fra la somma dei "
            "volumi delle membrature e il volume della loro unione. Oltre c'è "
            "doppio conteggio alle giunzioni, che nessuna metrica di qualità "
            "vedrebbe"
        ),
    )
    union_step_factor: float = Field(
        default=2.0,
        gt=0.0,
        title="passo del conteggio di celle, in multipli della spaziatura",
        description=(
            "con questo passo si misura il volume dell'unione. Più fine, più "
            "lento e più preciso: l'errore di discretizzazione viene riportato "
            "accanto al risultato, non nascosto"
        ),
    )
    membrature_attese: int | None = Field(
        default=None,
        gt=0,
        title="membrature attese, facoltativo",
        description=(
            "RISCONTRO DICHIARATO, facoltativo: quante membrature l'operatore si "
            "aspetta. Assente per definizione su un pezzo nuovo. Se dichiarato il "
            "prior riporta lo scarto; se assente riporta ciò che ha trovato e "
            "non inventa un'aspettativa"
        ),
    )
    sezioni_nominali: list[tuple[float, float]] | None = Field(
        default=None,
        title="sezioni nominali attese [mm], facoltativo",
        description=(
            "RISCONTRO DICHIARATO, facoltativo: le sezioni nominali attese [mm], "
            "dal disegno se esiste. Non sono la fonte del modello: i modelli "
            "parametrici misurano la sezione sulla nuvola, e il nominale serve "
            "solo a contraddire la misura"
        ),
    )
    volume_atteso: float | None = Field(
        default=None,
        gt=0.0,
        title="volume complessivo atteso [mm³], facoltativo",
        description=(
            "RISCONTRO DICHIARATO, facoltativo: il volume complessivo atteso "
            "[mm³], dal disegno se esiste"
        ),
    )


class ModelConfig(_ModelloBase):
    """I due modelli parametrici e il loro deck. Non e' letto da alcuno step di run().

    La scelta di quali modelli generare non sta qui, ed e' deliberato: e'
    un'azione, non un parametro di elaborazione. Se ci stesse, rigenerare un
    modello in piu' cambierebbe l'impronta di una corsa che non e' cambiata.
    """

    element: Literal["C3D8I", "C3D8", "C3D8R"] = Field(
        default="C3D8I",
        description=(
            "un telaio lavora a flessione. C3D8 a integrazione piena si "
            "irrigidisce a taglio e restituisce spostamenti troppo piccoli, un "
            "errore invisibile guardando la mesh; C3D8R ha il problema opposto, i "
            "modi a clessidra. C3D8I è supportato sia da Abaqus sia da CalculiX"
        ),
    )
    min_layers: int = Field(
        default=3,
        ge=3,
        description=(
            "strati di elementi minimi nello spessore, imposti dal codice e non "
            "suggeriti. Con uno o due la flessione nello spessore non è "
            "rappresentata e il risultato è sbagliato senza alcun segnale. Il "
            "vincolo ge=3 è il vincolo stesso: non si scende sotto"
        ),
    )
    target_size: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "passo caratteristico della mesh [mm]. None = la sezione minima "
            "divisa per min_layers, cioè il passo più grosso che rispetta il "
            "vincolo degli strati"
        ),
    )
    tie_name_prefix: NomeSet = Field(
        default="GIUNZIONE",
        description=(
            "prefisso dei nomi dei vincoli *TIE fra membrature adiacenti. Stesso "
            "vincolo di caratteri del nome del materiale, e per la stessa "
            "ragione: finisce interpolato in un deck scritto in ascii"
        ),
    )
    lateral_nset: NomeSet | None = Field(
        default=None,
        description=(
            "CARICO LATERALE, facoltativo: nome della superficie di elemento su "
            "cui agisce la pressione. Assente se non richiesto"
        ),
    )
    lateral_pressure: float | None = Field(
        default=None,
        description="CARICO LATERALE, facoltativo: pressione [MPa] sulla superficie nominata",
    )

    @model_validator(mode="after")
    def _carico_completo_o_assente(self) -> "ModelConfig":
        if (self.lateral_nset is None) != (self.lateral_pressure is None):
            raise ValueError(
                "il carico laterale si dichiara per intero o non si dichiara: "
                f"lateral_nset={self.lateral_nset!r} e "
                f"lateral_pressure={self.lateral_pressure!r}. Metà dichiarazione "
                "produrrebbe un deck con una card muta o con una pressione "
                "applicata a nulla"
            )
        return self


# I sei nomi che `abaqus.build_node_sets` fabbrica a ogni esportazione.
# Stanno qui e non in `core/abaqus.py` perche' la validazione della
# configurazione deve conoscerli e `abaqus` importa gia' `config`: l'altro
# verso sarebbe un ciclo. `build_node_sets` **non** li importa da qui: e' un
# dizionario letterale che li riscrive, per tenere ogni nome sulla riga del
# proprio criterio geometrico (il perche' e' scritto li'). L'accordo fra le
# due liste lo tengono due test, non il tipo: se questa costante cambia e
# quel dizionario no, sono loro a dirlo.
NOMI_SET_DI_FACCIA: tuple[str, ...] = (
    "BASE", "TOP", "FACE_FRONT", "FACE_BACK", "SIDE_LEFT", "SIDE_RIGHT",
)

# L'unico `*ELSET` che il deck fabbrica da se': il parametro `elset` di
# `abaqus.write_inp`, che vale "ALL_WALL" e finisce sia sulla card `*ELEMENT`
# sia sulla `*SOLID SECTION`. E' l'insieme che le regioni partizionano, quindi
# una regione omonima farebbe prendere alla `*SOLID SECTION` la partizione
# sbagliata e il muro intero riceverebbe il materiale di quella regione.
#
# Sta in una costante propria e non insieme ai sei perche' e' un tipo di
# insieme diverso: i sei sono `*NSET`, questo e' un `*ELSET`, e nel deck sono
# due spazi di nomi distinti. Confrontare una famiglia con i nomi fabbricati
# dell'altra rifiuta il nome innocuo e lascia passare quello che collide.
NOMI_ELSET_FABBRICATI: tuple[str, ...] = ("ALL_WALL",)


class SelettoreBox(_ModelloBase):
    """Tutti i nodi dentro un parallelepipedo allineato agli assi del modello.

    Le coordinate sono nel sistema di riferimento **dopo** `align_to_axes`,
    lo stesso di `wall_model.vtu`: e' il maglio che il deck contiene.
    L'estensione in quel sistema e' pubblicata in
    `metrics["11_export"]["extent"]`, e la bbox dei nodi presi in
    `metrics["11_export"]["selettori"]`, perche' l'operatore possa
    collocare una box senza indovinare.
    """

    tipo: Literal["box"]
    min: tuple[float, float, float] = Field(description="angolo minimo [mm]")
    max: tuple[float, float, float] = Field(description="angolo massimo [mm]")

    @model_validator(mode="after")
    def _la_box_non_e_rovesciata(self) -> "SelettoreBox":
        for asse, minimo, massimo in zip("xyz", self.min, self.max, strict=True):
            if minimo > massimo:
                raise ValueError(
                    f"la box ha min > max sulla componente {asse}: {minimo} > {massimo}. "
                    "Risolverebbe zero nodi, con lo stesso sintomo di altre quattro "
                    "condizioni diverse, e nessuno saprebbe quale sia successa"
                )
        return self


class SelettoreSfera(_ModelloBase):
    """Tutti i nodi entro un raggio da un centro. Coordinate come in SelettoreBox."""

    tipo: Literal["sfera"]
    centro: tuple[float, float, float] = Field(description="centro [mm]")
    raggio: float = Field(gt=0.0, description="raggio [mm]. Zero non è una sfera piccola")


class SelettoreNodo(_ModelloBase):
    """Il singolo nodo piu' vicino a un punto. Coordinate come in SelettoreBox.

    Per costruzione non puo' rendere zero nodi: `argmin` un vincitore ce l'ha
    sempre, anche a chilometri di distanza. L'oracolo sta a valle, sulla
    distanza, e non qui.
    """

    tipo: Literal["nodo"]
    punto: tuple[float, float, float] = Field(description="punto di riferimento [mm]")


class SelettoreNset(_ModelloBase):
    """Un insieme di nodi gia' esistente nel deck, per nome."""

    tipo: Literal["nset"]
    nome: NomeSetDiFaccia = Field(
        description="nome di un *NSET già scritto, di norma uno dei sei di faccia"
    )


Selettore = Annotated[
    SelettoreBox | SelettoreSfera | SelettoreNodo | SelettoreNset,
    Field(discriminator="tipo"),
]


class Momento(_ModelloBase):
    """Momento realizzato come coppia di forze staticamente equivalente.

    Non come `*CLOAD` sui gradi 4-6: misurato su un deck di sonda dato a
    `ccx` 2.22, un momento concentrato su un C3D4 e' scartato **in
    silenzio** -- zero occorrenze di `warning` o `error`, `number of
    equations 3`, spostamento `0.000000E+00` su tutte e tre le componenti.
    La guardia di `core/solve.py:438` non lo intercetta perche' non c'e'
    nessun warning da intercettare.

    `braccio` fissa la soglia di separazione fra i due gruppi di nodi, e il
    programma la contraddice se i nodi presi non la sostengono. Il momento
    realizzato resta `modulo`: e' la forza a calibrarsi sul braccio
    effettivo che i nodi offrono davvero -- maggiore di quello dichiarato,
    ed e' nel resoconto -- non il momento a scostarsi da quello dichiarato.
    """

    asse: tuple[float, float, float] = Field(
        description="asse del momento, versore non normalizzato"
    )
    modulo: float = Field(gt=0.0, description="modulo del momento [N*mm]")
    braccio: float = Field(
        gt=0.0,
        description=(
            "soglia di separazione dei due gruppi di nodi [mm]; il braccio "
            "effettivo fra i baricentri pesati risulta maggiore ed è nel resoconto"
        ),
    )

    @model_validator(mode="after")
    def _lasse_non_e_nullo(self) -> "Momento":
        if not any(self.asse):
            raise ValueError(
                "l'asse del momento è [0, 0, 0]: non è una direzione, si vede "
                "dalla configurazione senza aver letto la mesh"
            )
        return self


class CaricoPosizionato(_ModelloBase):
    """Un carico che porta con se' il proprio indirizzo.

    E' la differenza vera dagli altri tre casi di `CarichiConfig`, che sono
    dichiarati a mano anche loro ma citano un insieme che il deck fabbrica.
    """

    nome: NomeSet = Field(description="nome del passo statico nel deck")
    selettore: NomeSet = Field(description="nome di un selettore dichiarato in `selettori`")
    forza: tuple[float, float, float] | None = Field(
        default=None, description="risultante [N], ripartita per area sui nodi presi"
    )
    momento: Momento | None = None
    natura: Natura | None = Field(default=None, description=DESCRIZIONE_NATURA)

    @model_validator(mode="after")
    def _o_forza_o_momento(self) -> "CaricoPosizionato":
        if (self.forza is None) == (self.momento is None):
            raise ValueError(
                f"il carico '{self.nome}' deve dichiarare uno solo fra `forza` e "
                "`momento`: entrambi sono due carichi e vanno scritti come due voci, "
                "nessuno dei due non è un carico"
            )
        if self.forza is not None and not any(self.forza):
            raise ValueError(
                f"il carico '{self.nome}' ha forza di modulo nullo: scriverebbe un "
                "passo statico identico al peso proprio, con un nome che promette altro"
            )
        return self


class CaricoDistribuito(_ModelloBase):
    """Una pressione sulla pelle del solido, presa dai nodi di un selettore (#10).

    **La differenza da `CaricoPosizionato`, che e' il motivo per cui esiste.**
    Un posizionato dichiara una **risultante** e una direzione, e il programma
    la spalma sui nodi presi: tutte le quote spingono nello stesso verso, anche
    dove la parete e' girata. Una pressione invece agisce **normale alla
    faccia**, punto per punto, quindi sull'as-built -- che e' una superficie
    rilevata, storta e irregolare -- il carico **segue la forma**. E' l'unico
    dei due che sappia descrivere il vento su un muro, la spinta della terra o
    quella dell'acqua.

    **Chi integra, e perche' conta.** Qui non si ripartisce nulla a mano: la
    pressione va nel deck come `*DSLOAD, P` sulla superficie di elemento, ed e'
    il solutore a integrarla sulle facce. Ne discende che questa strada
    funziona sui **tetraedri quadratici**, dove `abaqus.ripartisci` deve
    fermarsi: la ripartizione per area darebbe tutto ai vertici, mentre i
    carichi consistenti di una faccia a sei nodi vogliono **zero** ai vertici
    (Abaqus Theory Guide §3.2.6, vedi `docs/validazione/carichi-consistenti-tet10.md`).

    **Il segno**, come lo intende la card `P`: positivo **preme dentro** la
    faccia. Il negativo resta ammesso perche' la depressione e' un carico
    fisico -- il vento che solleva una falda -- mentre lo zero no: sarebbe un
    passo statico identico al peso proprio, con un nome che promette altro.

    Infinito e NaN non si controllano qui: `_ModelloBase` porta
    `allow_inf_nan=False` e li rifiuta gia' per ogni campo decimale del file.
    Ripeterlo darebbe una guardia che non salta mai.
    """

    nome: NomeSet = Field(description="nome del passo statico e della superficie nel deck")
    selettore: NomeSet = Field(description="nome di un selettore dichiarato in `selettori`")
    pressione: float = Field(
        description="pressione [N/mm²] normale alla faccia; positiva preme dentro"
    )
    natura: Natura | None = Field(default=None, description=DESCRIZIONE_NATURA)

    @model_validator(mode="after")
    def _la_pressione_non_e_nulla(self) -> "CaricoDistribuito":
        if self.pressione == 0.0:
            raise ValueError(
                f"il carico '{self.nome}' ha pressione nulla: scriverebbe un passo "
                "statico identico al peso proprio, con un nome che promette altro"
            )
        return self


class Combinazione(_ModelloBase):
    """Una combinazione di azioni, proposta dal programma o corretta a mano (#146).

    `proposta` distingue le due cose, ed e' la ragione per cui il campo esiste:
    il programma non puo' sapere la categoria d'uso di un edificio rilevato, e
    generare senza chiedere sarebbe indovinare. Propone, l'operatore corregge,
    e il flag dice quali voci nessuno ha ancora guardato.
    """

    nome: NomeSet = Field(
        description=(
            "nome del passo nel deck. Stesso vincolo di caratteri degli altri "
            "nomi: finisce interpolato in un file scritto in ascii"
        ),
    )
    tipo: Literal[
        "slu_fondamentale",
        "sle_rara",
        "sle_frequente",
        "sle_quasi_permanente",
        "sismica",
    ] = Field(description="stato limite della combinazione, NTC 2018 §2.5.3")
    termini: tuple[tuple[NomeSet, float], ...] = Field(
        min_length=1,
        description=(
            "le azioni combinate e il loro coefficiente: (nome dell'azione, "
            "coefficiente). Il nome dell'azione è il `nome` di un carico "
            "dichiarato, oppure una delle etichette riservate "
            f"({', '.join(NOMI_PASSO_RISERVATI)}) e il nome del passo di peso "
            "proprio, che sono passi che il programma fabbrica da sé e che "
            "nessun carico dichiara. Stesso vincolo di caratteri di `nome`, e "
            "per la stessa ragione: il termine è l'altra metà della riga di "
            "deck, e un a capo dentro il nome vi aprirebbe una scheda `*` "
            "arbitraria. Almeno un termine: uno `*STEP` senza azioni risolve e "
            "dà spostamenti nulli, indistinguibili da una struttura scarica. "
            "L'ordine è quello con cui i termini entrano nel deck"
        ),
    )
    proposta: bool = Field(
        description=(
            "True = generata dal programma e non ancora toccata dall'operatore. "
            "Nessun predefinito: chi scrive una combinazione a mano deve dire "
            "che è sua, e chi la genera deve dire che è da rivedere"
        ),
    )


class CarichiConfig(_ModelloBase):
    """Casi di carico applicati al modello, oltre al peso proprio.

    I tre campi nullabili lo sono perché la dichiarazione e' opzionale: chi non
    dichiara nulla ottiene il solo peso proprio, l'unico caso che il programma
    puo' derivare dai dati (densita' e gravita' sono gia' nella configurazione).

    Nessun campo ha un predefinito numerico, per la stessa ragione del materiale:
    un carico non e' una congettura che il programma fa, e' una decisione di chi
    analizza.
    """

    spinta: SpintaOrizzontale | None = None
    carico_sommita: CaricoSommita | None = None
    modale: Modale | None = None
    posizionati: tuple[CaricoPosizionato, ...] = Field(
        default=(),
        description=(
            "carichi che portano con sé il proprio selettore. Tupla vuota e non "
            "None: il codice a valle itera, e una corsa senza posizionati e una "
            "con la lista vuota sono lo stesso esperimento -- è la regola che "
            "l'impronta di sweep già applica al blocco intero"
        ),
    )
    distribuiti: tuple[CaricoDistribuito, ...] = Field(
        default=(),
        description=(
            "pressioni normali alla faccia, sulla superficie che i nodi del "
            "selettore delimitano. Tupla vuota e non None per la stessa ragione "
            "dei posizionati"
        ),
    )
    combinazioni: tuple[Combinazione, ...] = Field(
        default=(),
        description=(
            "le combinazioni delle azioni dichiarate. Tupla vuota e non None, e "
            "vuota è anche l'unico predefinito ammesso: `carichi` esce "
            "dall'impronta solo quando ogni suo campo di primo livello è falso, e "
            "un predefinito truthy qui sposterebbe le ventidue righe dei registri "
            "lasciando verde il test dei blocchi"
        ),
    )


class MaterialeDichiarato(_ModelloBase):
    """Il materiale di una regione, con cio' che dichiara di se' (#141).

    Sta qui e non dentro `Material`, che e' congelato: un campo nuovo la'
    sposterebbe l'impronta di tutte le ventidue righe dei registri, perche'
    `analysis` non e' fra i blocchi esclusi. Il modello congelato viene riusato
    intero e il resto -- resistenza, provenienza, norma -- gli sta accanto.

    **Non c'e' un campo `veste`, ed e' una decisione e non una dimenticanza.**
    La proposta di dichiarare se un valore fosse «caratteristico» o «gia'
    ridotto» apriva la strada a una doppia riduzione o a nessuna, senza che
    nulla se ne accorgesse. #141 vale senza eccezioni: le voci sono **sempre**
    caratteristiche, e i valori di progetto li deriva il programma applicando i
    coefficienti di norma. Le parole «gia' ridotte» di #146 riguardano il
    fattore di confidenza e il livello di conoscenza, che si applicano alla
    muratura e non a un calcestruzzo.
    """

    material: Material = Field(
        description="il modello elastico isotropo, dichiarato per intero come altrove"
    )
    f_k: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "resistenza CARATTERISTICA [MPa]: f_ck per un calcestruzzo, f_yk per "
            "un acciaio. Mai un valore di progetto: i γ di norma li applica il "
            "programma, e una voce già ridotta verrebbe ridotta due volte"
        ),
    )
    provenienza: Literal["catalogo", "a_mano"] = Field(
        description=(
            "da dove viene questa voce: da una classe del catalogo dei materiali "
            "oppure battuta a mano. Senza dichiararlo un numero non ha provenienza, "
            "ed è la sola cosa che distingue un valore di norma da uno inventato"
        ),
    )
    classe: str | None = Field(
        default=None,
        description=(
            "la voce del catalogo, es. «C25/30» o «B450C», quando la provenienza "
            "è `catalogo`. Assente per una voce battuta a mano, e obbligatoria "
            "per una che viene dal catalogo: i due campi si dichiarano insieme"
        ),
    )
    norma: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        description=(
            "la norma con cui il valore è dichiarato, per articolo e non per "
            "pagina di una dispensa: es. «NTC 2018 Tab. 4.1.I», la tabella che "
            "porta i valori delle classi -- la 4.1.II dice invece dove una "
            "classe si può impiegare. Non può essere vuota: è la sola cosa che "
            "distingue un valore di norma da uno inventato, e vuota passerebbe "
            "fino alla tabella di provenienza"
        ),
    )

    @model_validator(mode="after")
    def _la_provenienza_e_la_classe_si_dichiarano_insieme(self) -> "MaterialeDichiarato":
        """La provenienza dice da dove viene il numero, la classe dice quale voce.

        Erano indipendenti: `provenienza='catalogo'` senza `classe` passava, e
        `provenienza='a_mano'` con `classe` pure. La prima manda a cercare nel
        catalogo una voce `None`; la seconda mette in tabella «da catalogo»
        senza dire quale voce, che e' il difetto preciso che #141 esiste per
        impedire.
        """
        if (self.provenienza == "catalogo") != (self.classe is not None):
            raise ValueError(
                f"provenienza='{self.provenienza}' e classe={self.classe!r} non "
                "stanno insieme: una voce dal catalogo dichiara quale voce è, e "
                "una battuta a mano non ne ha una. Senza, la tabella di "
                "provenienza direbbe «da catalogo» senza dire di che cosa"
            )
        return self


class ArmaturaConfig(_ModelloBase):
    """I nove campi che l'operatore dichiara di un'armatura (#136).

    Base e altezza NON stanno qui: vengono da `wall.misura`, e chiederle
    disferebbe il programma -- la sezione si misura sulla nuvola, non si batte.

    Nessun campo ha un predefinito, per la stessa ragione di `Material` e dei
    casi di carico: sono grandezze che nessun dato del rilievo puo' suggerire.
    Un copriferro predefinito sarebbe lo stesso errore del modulo elastico a
    1500 MPa finito su un telaio in calcestruzzo senza che nessuno l'avesse
    scelto.
    """

    classe_calcestruzzo: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(
        description=(
            "classe del calcestruzzo, es. «C25/30». Resta testo e non "
            "enumerazione finché il catalogo dei materiali non esiste: "
            "un'enumerazione scritta a mano qui sarebbe una seconda verità da "
            "tenere allineata a quel catalogo. Vuota però non è una classe"
        ),
    )
    classe_acciaio: Literal["B450A", "B450C"] = Field(
        description="classe dell'acciaio da armatura, NTC 2018 §11.3.2.1-2",
    )
    barre_tese: int = Field(
        ge=2,
        description=(
            "numero di barre longitudinali in zona tesa. Il minimo è due, non "
            "una: una barra sola non è un'armatura "
            "(docs/validazione/ricerca-armature-convenzioni-normative.md §7.1). "
            "ISO 3766 §3 regge il nome del campo, «number», non il minimo di due"
        ),
    )
    diametro_teso: int = Field(
        gt=0,
        description="diametro delle barre tese [mm]. La serie commerciale è 6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40 mm con B450C e 5, 6, 8, 10 mm con B450A (docs/validazione/ricerca-armature-convenzioni-normative.md §7.1): il dominio resta l'intero positivo e non un'enumerazione, per la stessa ragione di `classe_calcestruzzo`, ma 17 mm non esiste in commercio",
    )
    barre_compresse: int = Field(
        ge=0,
        description=(
            "numero di barre longitudinali in zona compressa. Zero è ammesso ed è "
            "l'armatura semplice, non un errore"
        ),
    )
    diametro_compresso: int = Field(
        gt=0,
        description=(
            "diametro delle barre compresse [mm]. Si dichiara anche con zero "
            "barre compresse: il campo non ha predefinito, come tutti gli "
            "altri. La serie commerciale è 6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40 mm con B450C e 5, 6, 8, 10 mm con B450A (docs/validazione/ricerca-armature-convenzioni-normative.md §7.1): il dominio resta l'intero positivo e non un'enumerazione, per la stessa ragione di `classe_calcestruzzo`, ma 17 mm non esiste in commercio"
        ),
    )
    diametro_staffe: int = Field(
        ge=6,
        description=(
            "diametro delle staffe [mm]. Il minimo di norma è 6 mm, e vale "
            "insieme al minimo relativo Ø_long,max/4 che questa configurazione "
            "non può controllare da sola (NTC 2018 §4.1.6.1.2). La serie commerciale è 6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40 mm con B450C e 5, 6, 8, 10 mm con B450A (docs/validazione/ricerca-armature-convenzioni-normative.md §7.1): il dominio resta l'intero positivo e non un'enumerazione, per la stessa ragione di `classe_calcestruzzo`, ma 17 mm non esiste in commercio"
        ),
    )
    passo_staffe: float = Field(
        gt=0.0,
        description="passo delle staffe [mm]. Zero non è un passo (NTC 2018 §4.1.6.1.2)",
    )
    copriferro_nominale: float = Field(
        ge=10.0,
        description=(
            "copriferro nominale [mm], netto e misurato all'esterno delle staffe. "
            "Sotto i 10 mm non è un copriferro "
            "(docs/validazione/ricerca-armature-convenzioni-normative.md §7.1)"
        ),
    )


class SezioneConfig(_ModelloBase):
    """La sezione di una regione: i tre materiali e, dove c'e', l'armatura.

    Due calcestruzzi e non uno: il nucleo confinato dalle staffe e il
    copriferro hanno leggi diverse, ed e' la distinzione su cui il verdetto di
    duttilita' si regge.
    """

    calcestruzzo_confinato: MaterialeDichiarato = Field(
        description="il nucleo racchiuso dalle staffe"
    )
    calcestruzzo_copriferro: MaterialeDichiarato = Field(
        description="lo strato esterno alle staffe, non confinato"
    )
    acciaio: MaterialeDichiarato = Field(description="l'acciaio delle barre")
    armatura: ArmaturaConfig | None = Field(
        default=None,
        description=(
            "disposizione delle barre, dove è stata rilevata. Assente: la sezione "
            "è di solo calcestruzzo, e nessuna armatura si inventa"
        ),
    )


class RegioneConfig(_ModelloBase):
    """Una regione punta a una sezione; la sezione nomina i materiali (#135).

    Il nome della regione e' la chiave del dizionario `PipelineConfig.regioni`,
    e diventa un `*ELSET` nel deck: e' per questo che le chiavi seguono le
    stesse regole dei selettori.
    """

    membratura: int = Field(
        ge=0,
        description=(
            "indice della membratura nel prior geometrico (`12_wall.json`). Il "
            "tetto -- quante membrature il prior ha davvero trovato -- non è "
            "verificabile qui: la configurazione nasce prima che lo step 12 giri, "
            "e il rifiuto dell'indice fuori intervallo spetta a chi legge il prior"
        ),
    )
    sezione: SezioneConfig = Field(description="la sezione attribuita a questa regione")


class PipelineConfig(_ModelloBase):
    """Configurazione completa di un'elaborazione."""

    input: InputConfig
    segment: SegmentConfig = Field(default_factory=SegmentConfig)
    downsample: DownsampleConfig = Field(default_factory=DownsampleConfig)
    normals: NormalsConfig = Field(default_factory=NormalsConfig)
    surface: SurfaceConfig = Field(default_factory=SurfaceConfig)
    repair: RepairConfig = Field(default_factory=RepairConfig)
    simplify: SimplifyConfig = Field(default_factory=SimplifyConfig)
    tet: TetConfig = Field(default_factory=TetConfig)
    analysis: AnalysisConfig | None = Field(
        default=None,
        description=(
            "materiale e analisi. Assente finché non viene dichiarato: `analysis` "
            "è letto dai soli step 11 e 13 (vedi `steps.STEP_BLOCKS`), e pretenderlo "
            "alla nascita di una corsa costringeva a scegliere la classe del "
            "calcestruzzo prima di aver guardato un punto della nuvola. Il materiale "
            "resta obbligatorio *dentro* `AnalysisConfig`: quell'invariante nasce da "
            "un difetto misurato e non è allentata qui"
        ),
    )
    carichi: CarichiConfig = Field(default_factory=CarichiConfig)
    selettori: dict[NomeSet, Selettore] = Field(
        default_factory=dict,
        description=(
            "regole geometriche nominate che indirizzano i nodi di una mesh senza "
            "topologia. Nominate e non annidate nei carichi: due carichi sullo "
            "stesso posto citano lo stesso nome, e una correzione fatta in un "
            "punto solo li muove entrambi"
        ),
    )
    wall: WallConfig = Field(default_factory=WallConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    regioni: dict[NomeSet, RegioneConfig] = Field(
        default_factory=dict,
        description=(
            "le regioni in cui il pezzo è partizionato, ciascuna con la propria "
            "sezione e i propri materiali. Un dizionario a chiavi libere e non un "
            "modello con campi: il nome della regione lo sceglie l'operatore e "
            "diventa un `*ELSET` nel deck. La forma a dizionario è anche ciò che "
            "tiene ferma l'impronta delle corse già registrate: nasce `{}`, cioè "
            "falso, e `sweep.fingerprint` lo omette finché resta vuoto"
        ),
    )
    solutore: SolutoreConfig = Field(
        default_factory=SolutoreConfig,
        description=(
            "motore dello step 13 e percorso del suo eseguibile. Fuori "
            "dall'impronta per esclusione secca: vedi SolutoreConfig"
        ),
    )

    @model_validator(mode="after")
    def _i_nomi_dei_selettori_non_collidono_coi_sei(self) -> "PipelineConfig":
        """Il confronto normalizza il caso su entrambi i lati.

        Misurato in `docs/fase-6-cantiere/sonda-caso-nomi/README.md`: `ccx`
        risolve un `*NSET` senza distinguere le maiuscole, quindi un
        selettore `base` collide con `BASE` nel deck anche se le stringhe
        Python sono diverse. Per lo stesso motivo due selettori
        dell'operatore che differiscono solo per caso (`piastra`/`PIASTRA`)
        sono due chiavi distinte nel dizionario ma un solo nome nel deck.
        """
        _nomi_senza_collisioni(
            self.selettori, "il selettore", "i selettori", "*NSET", NOMI_SET_DI_FACCIA
        )
        return self

    @model_validator(mode="after")
    def _i_nomi_delle_regioni_non_collidono_con_all_wall(self) -> "PipelineConfig":
        """Stessa regola dei selettori, ma contro l'altro spazio di nomi.

        Il nome di una regione diventa un `*ELSET` nel deck, e `ccx` risolve
        anche quelli senza distinguere le maiuscole -- per analogia con la
        sonda, non misurato: `docs/fase-6-cantiere/sonda-caso-nomi/` dichiara
        due `*NSET` e nessun `*ELSET` di prova, quindi la regola qui e'
        conservativa nella direzione giusta ma non poggia su una misura.

        I nomi fabbricati confrontati sono quelli degli `*ELSET`, cioe'
        `ALL_WALL` e non i sei di faccia: quelli sono `*NSET`, e nel deck sono
        un altro spazio di nomi. Il validatore non legge `self.analysis`, che
        puo' essere assente: una corsa nasce dalla sola nuvola e le regioni si
        dichiarano prima del materiale unico.
        """
        _nomi_senza_collisioni(
            self.regioni, "la regione", "le regioni", "*ELSET", NOMI_ELSET_FABBRICATI
        )
        return self

    @model_validator(mode="after")
    def _i_carichi_col_selettore_citano_selettori_dichiarati(self) -> "PipelineConfig":
        # Il confronto sui nomi ignora il caso, come gia' fa
        # `_i_nomi_dei_selettori_non_collidono_coi_sei`. Una sola regola nel
        # modulo, non due: la ragione la' era misurata (ccx risolve gli *NSET
        # senza distinguere le maiuscole, vedi
        # docs/fase-6-cantiere/sonda-caso-nomi/), qui e' che due passi che
        # differiscono solo per caso sono indistinguibili per chi legge il
        # rapporto, e un nome che l'operatore crede nuovo ne sovrascrive uno
        # riservato nella sua testa se non nel deck.
        riservati = _mappa_casefold(NOMI_PASSO_RISERVATI)
        # `analysis` puo' mancare: una corsa nasce dalla sola nuvola e il
        # materiale si dichiara piu' tardi (lo pretendono gli step 11 e 13, non
        # gli altri). Questo validatore gira a OGNI costruzione, comprese le
        # configurazioni che un'analisi non ce l'hanno ancora, quindi leggere
        # `self.analysis.step_name` diritto la faceva cadere sulla nuvola appena
        # caricata. Senza analisi non c'e' nessun passo di peso proprio da
        # riservare, e il nome resta libero fino a quando l'analisi lo prende.
        passo_del_peso = self.analysis.step_name if self.analysis else None
        if passo_del_peso is not None:
            riservati[passo_del_peso.casefold()] = passo_del_peso
        selettori_per_caso = _mappa_casefold(self.selettori)
        visti: dict[str, str] = {}
        # Le tre liste insieme e non tre cicli: un distribuito, un posizionato
        # e una combinazione omonimi scriverebbero passi con lo stesso nome, e
        # cicli separati -- ognuno col proprio `visti` -- li lascerebbero
        # passare tutti. I controlli sono per il resto identici, perche' tutte
        # e tre le voci danno il nome a un passo; il solo pezzo che le
        # distingue e' il selettore, che le combinazioni non citano.
        for voce in (
            *self.carichi.posizionati,
            *self.carichi.distribuiti,
            *self.carichi.combinazioni,
        ):
            e_combinazione = isinstance(voce, Combinazione)
            soggetto = "la combinazione" if e_combinazione else "il carico"
            if not e_combinazione:
                chiave_selettore = voce.selettore.casefold()
                if chiave_selettore not in selettori_per_caso:
                    raise ValueError(
                        f"il carico '{voce.nome}' cita il selettore "
                        f"'{voce.selettore}', che non è dichiarato. Dichiarati: "
                        f"{sorted(self.selettori)}"
                    )
                # Normalizzato al nome canonico qui, a monte: a valle
                # (`core/abaqus.py`, che costruisce `nset_selettori` dalle
                # chiavi di `self.selettori`) il confronto e' un'uguaglianza
                # esatta, e deve trovare sempre lo stesso nome che il selettore
                # ha dichiarato, non la grafia con cui il carico lo ha citato.
                voce.selettore = selettori_per_caso[chiave_selettore]
            chiave = voce.nome.casefold()
            if chiave in riservati:
                raise ValueError(
                    f"{soggetto} '{voce.nome}' porta il nome del passo "
                    f"'{riservati[chiave]}', già preso. I riservati sono "
                    f"{list(NOMI_PASSO_RISERVATI)}"
                    # Nominato solo quando c'e': senza analisi la frase
                    # direbbe che il passo di peso proprio si chiama 'None',
                    # cioe' inventerebbe un nome che nessuno ha dichiarato.
                    + (
                        f" e il passo di peso proprio si chiama '{passo_del_peso}'"
                        if passo_del_peso is not None
                        else ""
                    )
                    + ". Il confronto ignora il caso: due passi che "
                    "differiscono solo per maiuscole sono indistinguibili "
                    "per chi legge il rapporto"
                )
            if chiave in visti:
                raise ValueError(
                    f"due passi si chiamano '{visti[chiave]}' e "
                    f"'{voce.nome}': il deck scriverebbe due passi omonimi e i "
                    "due risultati sarebbero indistinguibili nel file risolto"
                )
            visti[chiave] = voce.nome
        return self

    run: RunConfig = Field(default_factory=RunConfig)

    def analisi_dichiarata(self, chiede: str) -> AnalysisConfig:
        """L'analisi, oppure un rifiuto che dice chi la pretende e dove darla.

        Unico varco verso `self.analysis` per chi ne pretende uno: cosi' la
        guardia sta in un posto solo e nessun chiamante puo' leggere `None`
        scambiandolo per un materiale.

        `chiede` e' l'etichetta del chiamante e non un numero: `meshrec model`
        esporta lo stesso deck dello step 11 ma step non e', e chi lo lancia
        veniva mandato a guardare uno step che nel pannello poteva gia' essere
        verde. Il messaggio nomina il pannello e non i campi YAML per la stessa
        ragione: `young` e `density` nell'interfaccia non esistono, si chiamano
        «modulo elastico E [MPa]» e «densita [t/mm³]». Il nome del campo resta
        pero' nella coda, perche' chi arriva qui da `meshrec run` un pannello
        non ce l'ha e deve sapere dove scrivere.
        """
        if self.analysis is None:
            raise ValueError(
                f"{chiede} pretende il materiale, e questa corsa non lo dichiara. "
                "Dichiaralo nel pannello dello step 11, riquadro «materiale»: nome, "
                "modulo elastico, coefficiente di Poisson, densità -- da riga di "
                "comando è analysis.material nel config.yaml della corsa. Il "
                "programma non lo deduce dalla nuvola e non ne mette uno per conto suo"
            )
        return self.analysis


class _LoaderChiaviUniche(yaml.SafeLoader):
    """`SafeLoader` che rifiuta due chiavi omonime invece di tenere l'ultima.

    Misurato: con il loader di serie la prima delle due sparisce senza alcun
    segnale. E' l'unico ingresso degenere che non ha un sintomo -- gli altri
    almeno risolvono zero nodi -- e per questo si rifiuta alla lettura invece
    che a valle.

    Deriva da `yaml.SafeLoader` e ne eredita i costruttori: nessun tag
    `!!python/object`, nessuna costruzione di tipi arbitrari. Aggiunge un
    controllo, non toglie un divieto.
    """

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        viste: set[object] = set()
        for chiave_node, _ in node.value:
            chiave = self.construct_object(chiave_node, deep=deep)
            if chiave in viste:
                raise ValueError(
                    f"la chiave '{chiave}' compare due volte nello stesso blocco "
                    f"({chiave_node.start_mark}): il lettore terrebbe l'ultima e la "
                    "prima sparirebbe senza un segnale"
                )
            viste.add(chiave)
        return super().construct_mapping(node, deep=deep)


def carica_yaml_da_testo(testo: str) -> object:
    """Come `carica_yaml`, ma su un testo che non e' ancora un file.

    Esiste perche' chi vuole sapere in anticipo se un testo diventera' un
    `config.yaml` valido deve usare **lo stesso** lettore che quel file
    rileggera'. Con `yaml.safe_load` la prova era piu' permissiva del
    controllo vero: le chiavi omonime passavano di qui e venivano respinte
    solo dopo, a file gia' riscritto -- cioe' proprio l'ingresso degenere per
    cui `_LoaderChiaviUniche` esiste, e il solo che non ha altro sintomo.

    `yaml.load` con un loader che **eredita da SafeLoader** ha esattamente i
    costruttori di `safe_load`. Non sostituire il loader con `yaml.Loader` o
    `yaml.UnsafeLoader`, che i tag `!!python/object` li eseguono davvero.
    """
    return yaml.load(testo, Loader=_LoaderChiaviUniche)  # noqa: S506


def carica_yaml(path: Path) -> object:
    """L'unica lettura YAML del modulo, con il rifiuto delle chiavi omonime.

    Passa dal gemello su testo per costruzione: due lettori separati potevano
    divergere in silenzio, e lo avevano gia' fatto.
    """
    return carica_yaml_da_testo(Path(path).read_text(encoding="utf-8"))


def load_config(path: Path) -> PipelineConfig:
    """Legge un config.yaml senza perdita rispetto a quanto scritto da `save_config`."""
    return PipelineConfig.model_validate(carica_yaml(path))


def save_config(cfg: PipelineConfig, path: Path) -> None:
    """Scrive la configurazione completa, compresi i valori lasciati ai predefiniti."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg.model_dump(mode="json"), handle, sort_keys=False, allow_unicode=True)


class SweepConfig(_ModelloBase):
    """Motore di sweep: risorse di macchina e politica sugli artefatti."""

    workers: int = Field(
        default=4,
        gt=0,
        description=(
            "candidati in volo insieme, come processi separati. Non è il numero "
            "di processori: TetGen ha un picco misurato di 1,35 GB sulla corsa "
            "del muro e la macchina di sviluppo ha 7 GB liberi, quindi quattro "
            "candidati sono circa 5,4 GB di picco. Va tarato sulla macchina che "
            "esegue: nessun valore dedotto dai processori logici è corretto qui"
        ),
    )
    timeout_s: float = Field(
        default=1800.0,
        gt=0.0,
        description=(
            "tetto al tempo di un singolo candidato, perché uno patologico non "
            "blocchi lo sweep. La corsa completa più lenta documentata vale 134 s "
            "e il singolo step più lento 186 s: è un tetto contro il patologico, "
            "non contro il lento"
        ),
    )
    runs_root: Path = Path("runs")
    registry_root: Path = Path("experiments")
    keep_dominated_artifacts: bool = Field(
        default=False,
        description=(
            "gli artefatti dei candidati dominati vengono rimossi a sweep "
            "concluso; config.yaml e metrics.json restano sempre. Una corsa "
            "completa pesa circa 300 MB"
        ),
    )


class AxisSpec(_ModelloBase):
    """Un asse della griglia: il percorso puntato del parametro e i suoi livelli."""

    path: str = Field(description="percorso puntato dentro PipelineConfig, es. tet.min_ratio")
    values: list[float | int | bool | None] = Field(min_length=1)


class ExperimentConfig(_ModelloBase):
    """Dichiarazione di un esperimento. Tracciata da git accanto al proprio registro."""

    name: str
    base: Path = Field(
        description=(
            "configurazione di partenza, es. casi/muro.yaml. Risolta rispetto alla "
            "cartella da cui gira il programma, non rispetto a questo file"
        )
    )
    axes: list[AxisSpec] = Field(min_length=1)
    pairs: list[tuple[str, str]] = Field(
        default_factory=list,
        description=(
            "coppie di assi da incrociare in fattoriale, oltre allo sweep a un "
            "asse alla volta. Si dichiarano solo le coppie che la misura mostra "
            "interagenti: un fattoriale pieno sui cinque assi della griglia "
            "reale (3x3x3x4x2 livelli) sono 216 candidati"
        ),
    )
    known_thickness: float | None = Field(
        default=None,
        description=(
            "spessore reale misurato [mm], contro cui si controlla la misura "
            "letta sulla nuvola sorgente. E' il controllo che smentisce l'asse "
            "di fedeltà"
        ),
    )
    sweep: SweepConfig = Field(default_factory=SweepConfig)


def load_experiment(path: Path) -> ExperimentConfig:
    """Legge la dichiarazione di un esperimento."""
    return ExperimentConfig.model_validate(carica_yaml(path))


class ViewportConfig(_ModelloBase):
    """Disegno nel browser. Non entra in PipelineConfig: vedi la nota sotto.

    Aggiungere un campo a PipelineConfig cambierebbe sweep.fingerprint e quindi
    l'impronta di ogni riga gia' scritta nei registri della Fase 2, che sono la
    tabella sperimentale della tesi. Questi parametri governano il disegno e non
    l'elaborazione, quindi restano fuori.
    """

    max_points: int = Field(
        default=400_000,
        gt=0,
        description=(
            "punti al massimo inviati al browser per il disegno. 400.000 punti "
            "sono 4,8 MB in Float32, dell'ordine di 04_normals.ply di lab_crop "
            "(5.571.038 byte), un artefatto che la pipeline scrive e rilegge a "
            "ogni corsa. Non è un limite grafico ma di trasporto"
        ),
    )


class ServerConfig(_ModelloBase):
    """Server locale. Utente singolo, nessuna autenticazione."""

    host: str = "127.0.0.1"
    port: int = Field(default=8765, gt=0, le=65535)
    open_browser: bool = True
