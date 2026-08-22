"""Modelli di configurazione: unico luogo dove un parametro ha un valore predefinito.

Sistema di unita di lavoro: mm, N, MPa, tonnellata, secondo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

GRAVITY_MM_S2: float = 9810.0


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

    name: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "nome del materiale. Il vincolo non e' cosmetico: il nome viene interpolato "
            "in `*MATERIAL, NAME=...` e il deck e' scritto in ascii, quindi un carattere "
            "fuori tabella romperebbe l'esportazione dopo l'intera pipeline, e un a capo "
            "inietterebbe card nel deck senza che nulla se ne accorga"
        ),
    )
    young: float = Field(gt=0.0, description="modulo elastico [MPa]")
    poisson: float = Field(ge=0.0, lt=0.5, description="coefficiente di Poisson")
    density: float = Field(gt=0.0, description="densita [t/mm^3]")


class InputConfig(_ModelloBase):
    """Step 1: ingresso e scala."""

    path: Path
    scale: float = Field(default=1.0, gt=0.0, description="fattore verso i mm")
    max_points: int = Field(default=20_000_000, gt=0)
    expected_size: tuple[float, float, float] | None = Field(
        default=None, description="dimensioni reali misurate del muro [mm], per il controllo di scala"
    )
    size_tolerance: float = Field(default=0.2, gt=0.0, description="scarto relativo ammesso")
    spacing_sample: int = Field(default=20_000, gt=1, description="punti campionati per la spaziatura")
    seed: int = 0


class SegmentConfig(_ModelloBase):
    """Step 2: segmentazione."""

    method: Literal["crop", "auto"] = "crop"
    outlier_neighbors: int = Field(default=20, gt=0)
    outlier_std_ratio: float = Field(default=2.0, gt=0.0)
    crop_min: tuple[float, float, float] | None = None
    crop_max: tuple[float, float, float] | None = None
    plane_distance_factor: float = Field(default=3.0, gt=0.0, description="x spaziatura media")
    plane_max_count: int = Field(default=4, ge=0)
    plane_min_points_ratio: float = Field(default=0.05, gt=0.0, le=1.0)
    cluster_eps_factor: float = Field(default=4.0, gt=0.0, description="x spaziatura media")
    cluster_min_points: int = Field(default=50, gt=0)
    cluster_index: int = Field(default=0, ge=0, description="0 = cluster piu numeroso")


class DownsampleConfig(_ModelloBase):
    """Step 3: riduzione a voxel."""

    voxel_size: float | None = Field(default=None, description="None = 2 x spaziatura media")
    voxel_factor: float = Field(default=2.0, gt=0.0)


class NormalsConfig(_ModelloBase):
    """Step 4: normali."""

    knn: int = Field(default=30, gt=2)
    orient_knn: int = Field(default=30, gt=2)


class SurfaceConfig(_ModelloBase):
    """Step 5: ricostruzione della superficie."""

    method: Literal["poisson", "bpa", "alpha"] = "poisson"
    poisson_depth: int = Field(
        default=9,
        ge=4,
        le=14,
        description=(
            "profondita' dell'ottree del solutore Poisson: piu' alta, superficie piu' "
            "fitta; su muro, 9 -> 8 porta i triangoli da 908.118 a 221.369"
        ),
    )
    poisson_width: float = Field(default=0.0, ge=0.0)
    poisson_scale: float = Field(default=1.1, gt=0.0)
    density_quantile: float = Field(
        default=0.05, ge=0.0, lt=1.0, description="quantile di densita sotto il quale i vertici sono scartati"
    )
    poisson_n_threads: int = Field(
        default=1, description="thread per il solutore Poisson; 1 = riproducibile, -1 = automatico"
    )
    bpa_radius_factors: tuple[float, ...] = (1.0, 2.0, 4.0)
    alpha_factor: float = Field(default=5.0, gt=0.0, description="x spaziatura media")


class RepairConfig(_ModelloBase):
    """Step 6: riparazione."""

    largest_component_only: bool = True
    max_hole_area: float | None = Field(
        default=None,
        description=(
            "area [mm^2] oltre la quale un'apertura viene segnalata, sia essa un ciclo "
            "di bordo chiuso o un cammino aperto"
        ),
    )
    join_components: bool = False


class SimplifyConfig(_ModelloBase):
    """Step 8: semplificazione, opzionale."""

    enabled: bool = False
    mode: Literal["decimate", "remesh"] = "remesh"
    target_faces: int | None = Field(default=None, gt=0)
    remesh_target_len_pct: float = Field(default=1.0, gt=0.0, description="percentuale della diagonale")
    taubin_iterations: int = Field(default=0, ge=0)


class TetConfig(_ModelloBase):
    """Step 9: tetraedrizzazione."""

    min_ratio: float = Field(
        default=1.8,
        gt=0.0,
        description=(
            "rapporto raggio-spigolo massimo: valori piu bassi danno elementi piu "
            "regolari, ma il raffinamento puo' non convergere su geometrie difficili. "
            "Sul muro di riferimento 1.6 e valori inferiori interrompono TetGen con un "
            "errore interno mentre 1.7 converge: il predefinito 1.8 non e' quindi il "
            "valore piu severo che porta a termine il lavoro, ma quello che tiene un "
            "decimo di margine sopra di esso. Misura completa da 1.4 a 2.5 in "
            "docs/fase-1-min-ratio.md"
        ),
    )
    max_volume: float | None = Field(default=None, gt=0.0, description="volume massimo elemento [mm^3]")
    max_steiner_points: int = Field(
        default=-1,
        ge=-1,
        description=(
            "punti che TetGen puo' aggiungere per raffinare; -1 = nessun limite. "
            "Il predefinito della libreria tetgen e' 100000: su geometrie a scala "
            "reale quel tetto viene raggiunto e il raffinamento si ferma li, "
            "restituendo una mesh troncata che nessuna metrica segnalava"
        ),
    )
    nobisect: bool = Field(
        default=False,
        description=(
            "vieta a TetGen di suddividere le facce della superficie di ingresso. "
            "Serve dove la scala locale della superficie e' minuscola: la "
            "suddivisione per invasione ricorre fino alla distanza fra lembi "
            "opposti, e su lab_frame.pcd, che ha strozzature sotto il millimetro, "
            "il raffinamento non converge a nessun min_ratio finche' resta "
            "consentita. Attenzione: con nobisect attivo TetGen non aggiunge punti "
            "sul bordo, quindi su una superficie di ingresso grossolana max_volume "
            "puo' restare disatteso; il caso e' segnalato con "
            "IneffectiveVolumeLimitWarning. Vedi docs/fase-1-min-ratio.md"
        ),
    )
    reference_ratio: float = Field(
        default=1.8,
        gt=0.0,
        description=(
            "metro fisso con cui lo step 10 conta la frazione di elementi fuori "
            "vincolo raggio-spigolo. Non e' il vincolo chiesto a TetGen: nel "
            "motore di sweep min_ratio e' una variabile della griglia, e una "
            "frazione contata contro il proprio min_ratio confronterebbe "
            "candidati contro vincoli diversi. Il valore 1.8 coincide con il "
            "predefinito di min_ratio perche' e' il metro con cui sono state "
            "misurate le due corse di riferimento (8,10% e 9,55%)"
        ),
    )
    element: Literal["C3D4", "C3D10"] = "C3D4"


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


class CaricoSommita(_ModelloBase):
    """Risultante verticale ripartita sui nodi di un insieme.

    La ripartizione e' uniforme per nodo, quindi il carico si concentra dove i
    nodi sono piu' fitti, e l'insieme e' costruito per tolleranza e non e' la
    faccia superiore certificata del pezzo. Sono due cose da dichiarare accanto
    ai risultati di questo caso, non da correggere qui.
    """

    risultante: float = Field(gt=0.0, description="risultante in N, ripartita sui nodi")
    nset: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="insieme di nodi su cui ripartire, di norma TOP",
    )


class Modale(_ModelloBase):
    """Analisi in frequenza.

    Costa poco e smentisce molto: un modello mal vincolato ha una prima
    frequenza fuori scala. Misurato il 21/08/2026 sull'as-built del telaio:
    21,19 Hz col vincolo corretto, 4,03 Hz col vincolo su un piede solo.
    """

    modi: int = Field(gt=0, description="numero di modi da estrarre")


# Le etichette che `abaqus.export_model` assegna da se' agli altri casi di
# carico (il suo `casi_di_carico`), e che `solve.risolvi` usa come chiavi di
# `point_data`: non sono disponibili per il nome del passo di peso proprio.
NOMI_PASSO_RISERVATI = ("SPINTA_ORIZZONTALE", "CARICO_TOP", "MODALE")


class AnalysisConfig(_ModelloBase):
    """Materiale e analisi."""

    material: Material
    gravity: float = Field(default=GRAVITY_MM_S2, gt=0.0)
    fixed_nset: str = "BASE"
    step_name: str = "GRAVITA"
    set_tolerance_factor: float = Field(
        default=6.0,
        gt=0.0,
        description=(
            "moltiplica la spaziatura dei nodi sul bordo del maglio di volume e "
            "da' la tolleranza con cui i set di faccia sono estratti. Il "
            "predefinito 6 e' misurato: e' il piu piccolo intero che copre almeno "
            "il 95% della superficie d'appoggio su entrambe le corse di "
            "riferimento e per i quattro set utilizzabili. Il margine ha la "
            "stessa struttura di quello di tet.min_ratio: 5 e' il primo valore "
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
                f"step_name={self.step_name!r} e' un nome riservato: "
                f"{', '.join(NOMI_PASSO_RISERVATI)} sono le etichette che la "
                "pipeline assegna da se' agli altri casi di carico, e due passi "
                "sulla stessa etichetta si sovrascriverebbero a vicenda nel .vtu"
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
        le=9,
        description=(
            "la ripresa arriva fino allo step 9 (tetraedrizzazione); gli step 10 e 11 "
            "sono metriche di volume ed esportazione, senza lavoro costoso da saltare, "
            "e vengono comunque rieseguiti a ogni corsa."
            " Lo step 12 (prior geometrico) e' l'ultimo e non e' un punto di "
            "ripresa: legge 02_segmented.ply, che e' gia' cio' che una ripresa "
            "da 3 in poi ricarica. Chi vuole il solo prior usa `meshrec wall`, "
            "che e' un'azione e non una ripresa."
        ),
    )
    to_step: int = Field(
        default=13,
        ge=1,
        le=13,
        description=(
            "ultimo step eseguito. Serve all'interfaccia, che esegue uno step "
            "alla volta: from_step e to_step uguali eseguono soltanto quello. "
            "Il tetto e' 13 dalla Fase 5 e il predefinito coincide con esso: "
            "l'utente ha scelto esplicitamente che ogni corsa risolva e "
            "scriva spostamenti e tensioni accanto alle altre metriche, non "
            "che il solutore sia un extra da chiedere (scartata l'opzione "
            "'step opzionale acceso dalla configurazione'). "
            "Lo step 13 resta pero' diverso dagli altri: e' l'unico che paga "
            "un processo esterno vero (ccx) invece di lavoro in-process, e "
            "chi lo invoca su molti candidati -- uno sweep -- paga quel "
            "processo e i suoi artefatti per ciascuno, senza che la "
            "selezione se ne serva: misurati sull'unica corsa vera "
            "(runs/lab_telaio_v2), .frd 81 MiB, .vtu 8,2 MiB e .dat 4,3 MiB, "
            "cioe' 93,6 MiB per candidato. Questa e' la "
            "ragione per cui sweep.py chiede esplicitamente to_step=12 al "
            "sottoprocesso invece di ereditare questo predefinito, e per cui "
            "REQUIRED_STEPS in sweep.py non lo richiede: e' una decisione del "
            "chiamante, non del predefinito del prodotto. "
            "from_step resta fermo a 9 e non segue questo tetto, per la "
            "ragione scritta la'. "
            "Con validate_assignment attivo il validatore incrociato rifiuta "
            "ogni stato intermedio incoerente, e nessun ordine di assegnazione "
            "e' sicuro: restringendo un intervallo verso l'alto rompe to_step "
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
        description=(
            "lato della cella quadrata, in multipli della spaziatura media. E' il "
            "«metodo delle colonne» di docs/fase-1-tolleranza-set.md, dove il "
            "fattore 4 e' misurato e non scelto: con una cella larga quanto la "
            "spaziatura la griglia diventa piu fine dei triangoli della faccia e "
            "una colonna su dieci risulta vuota per puro artefatto di griglia"
        ),
    )
    spacing_sample: int = Field(
        default=20_000,
        gt=1,
        description=(
            "punti campionati per stimare la spaziatura locale di ogni regione, "
            "stessa semantica di input.spacing_sample ma per il riempimento della "
            "sezione: la spaziatura del pezzo intero non descrive una regione "
            "campionata piu' rada (piu' lontana dallo scanner, parzialmente "
            "occlusa), e usarla al posto di quella locale sposta la soglia sulla "
            "grandezza sbagliata"
        ),
    )
    seed: int = 0
    """Seme del campionamento di spacing_sample, stessa semantica di input.seed."""
    thickness_tolerance: float = Field(
        default=0.15,
        gt=0.0,
        lt=1.0,
        description=(
            "scarto relativo entro cui due celle adiacenti contano come «stesso "
            "spessore», e quindi come stessa membratura. E' la forma numerica di "
            "«quasi costante»: le membrature sono le regioni connesse a spessore "
            "quasi costante, e questa e' l'unica soglia della scomposizione"
        ),
    )
    min_cells: int = Field(
        default=12,
        gt=0,
        description=(
            "celle minime perche' una regione connessa sia una membratura. Sotto "
            "questo numero la regione e' rumore di griglia e non ha abbastanza "
            "celle perche' una direzione principale sia stimabile"
        ),
    )
    floor_angle_deg: float = Field(
        default=15.0,
        gt=0.0,
        lt=90.0,
        description=(
            "un piano estratto con la normale entro questo angolo dalla verticale "
            "e' candidato pavimento. Il pavimento non e' una membratura e va "
            "scartato come piano, mai come quota"
        ),
    )
    floor_min_ratio: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description=(
            "frazione minima dei punti perche' un piano quasi orizzontale sia il "
            "pavimento e non la faccia superiore di una membratura. Le due "
            "condizioni valgono insieme: orizzontale e esteso"
        ),
    )
    contour_tolerance: float = Field(
        default=5.0,
        gt=0.0,
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
        description=(
            "controllo intrinseco: frazione minima delle celle della regione che "
            "vedono entrambe le facce. E' la lezione gia' pagata su FACE_FRONT e "
            "FACE_BACK: una faccia vista da pochi punti produce un piano finto"
        ),
    )
    section_dispersion: float = Field(
        default=0.10,
        gt=0.0,
        description=(
            "controllo intrinseco: dispersione relativa massima della sezione "
            "lungo l'asse. Oltre, la regione non e' un prisma e viene riportata "
            "come tale invece di essere spacciata per una membratura. E' l'unica "
            "difesa contro una sezione a Π riportata come (pieno, affidabile): "
            "riempimento e affidabilita' misurano l'ingombro locale per fetta e "
            "non vedono due membrature uguali unite a Π, che restano piene di "
            "bounding box da un capo all'altro"
        ),
    )
    section_fill_ratio: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "confine fra i due esiti «pieno» e «vuoto» del riempimento di "
            "sezione: frazione (mediana sulle fette lungo l'asse) delle celle "
            "del proprio ingombro locale che la sezione occupa davvero. "
            "L'estensione e la dispersione sono entrambe misure di bounding box "
            "e non vedono un vuoto interno -- due membrature identiche unite a Π "
            "restano piene di bounding box da un capo all'altro. Stessa "
            "convenzione di meta' di face_coverage: sotto meta' delle celle del "
            "proprio ingombro, l'ingombro non e' la sezione ma il suo "
            "contenitore. Non scarta nulla: il riempimento e' un esito "
            "dichiarato, e il rifiuto spetta a chi costruisce i modelli"
        ),
    )
    density_dispersion_limit: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "condizione di validita' della misura di riempimento, non criterio "
            "di qualita' del pezzo: dispersione massima delle distanze al vicino "
            "piu' prossimo rispetto alla loro media. Sopra questo limite lo "
            "scarto tipo eguaglia la media, la media smette di essere la scala "
            "della nuvola, e la griglia costruita su di essa (cell_factor per la "
            "spaziatura) non risolve piu' la parte rada: il riempimento si "
            "dichiara «non verificabile» invece di dare un numero che misura il "
            "campionamento e non la sezione. Il valore uno e' il confine fra "
            "«descrivibile da una media» e no, non un numero tarato su un caso: "
            "una nuvola a densita' unica sta ben sotto (una griglia regolare da' "
            "zero, un campionamento casuale uniforme di superficie circa 0,52), "
            "una nuvola con una parte rada oltre cell_factor volte la media "
            "sta sopra"
        ),
    )
    union_tolerance: float = Field(
        default=0.02,
        gt=0.0,
        description=(
            "controllo intrinseco: scarto relativo ammesso fra la somma dei "
            "volumi delle membrature e il volume della loro unione. Oltre c'e' "
            "doppio conteggio alle giunzioni, che nessuna metrica di qualita' "
            "vedrebbe"
        ),
    )
    union_step_factor: float = Field(
        default=2.0,
        gt=0.0,
        description=(
            "passo del conteggio di celle con cui si misura il volume "
            "dell'unione, in multipli della spaziatura media. Piu' fine, piu' "
            "lento e piu' preciso: l'errore di discretizzazione viene riportato "
            "accanto al risultato, non nascosto"
        ),
    )
    membrature_attese: int | None = Field(
        default=None,
        gt=0,
        description=(
            "RISCONTRO DICHIARATO, facoltativo: quante membrature l'operatore si "
            "aspetta. Assente per definizione su un pezzo nuovo. Se dichiarato il "
            "prior riporta lo scarto; se assente riporta cio' che ha trovato e "
            "non inventa un'aspettativa"
        ),
    )
    sezioni_nominali: list[tuple[float, float]] | None = Field(
        default=None,
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
        description=(
            "RISCONTRO DICHIARATO, facoltativo: il volume complessivo atteso "
            "[mm^3], dal disegno se esiste"
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
            "modi a clessidra. C3D8I e' supportato sia da Abaqus sia da CalculiX"
        ),
    )
    min_layers: int = Field(
        default=3,
        ge=3,
        description=(
            "strati di elementi minimi nello spessore, imposti dal codice e non "
            "suggeriti. Con uno o due la flessione nello spessore non e' "
            "rappresentata e il risultato e' sbagliato senza alcun segnale. Il "
            "vincolo ge=3 e' il vincolo stesso: non si scende sotto"
        ),
    )
    target_size: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "passo caratteristico della mesh [mm]. None = la sezione minima "
            "divisa per min_layers, cioe' il passo piu' grosso che rispetta il "
            "vincolo degli strati"
        ),
    )
    tie_name_prefix: str = Field(
        default="GIUNZIONE",
        pattern=r"^[A-Za-z0-9_.-]+$",
        description=(
            "prefisso dei nomi dei vincoli *TIE fra membrature adiacenti. Stesso "
            "vincolo di caratteri del nome del materiale, e per la stessa "
            "ragione: finisce interpolato in un deck scritto in ascii"
        ),
    )
    lateral_nset: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_.-]+$",
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
                f"lateral_pressure={self.lateral_pressure!r}. Meta' dichiarazione "
                "produrrebbe un deck con una card muta o con una pressione "
                "applicata a nulla"
            )
        return self


# I sei nomi che `abaqus.build_node_sets` fabbrica a ogni esportazione.
# Stanno qui e non in `core/abaqus.py` perche' la validazione della
# configurazione deve conoscerli e `abaqus` importa gia' `config`: l'altro
# verso sarebbe un ciclo. `build_node_sets` li importa da qui, cosi' le due
# liste non possono divergere in silenzio.
NOMI_SET_DI_FACCIA: tuple[str, ...] = (
    "BASE", "TOP", "FACE_FRONT", "FACE_BACK", "SIDE_LEFT", "SIDE_RIGHT",
)

NomeSet = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+$")]


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
    raggio: float = Field(gt=0.0, description="raggio [mm]. Zero non e' una sfera piccola")


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
    nome: NomeSet = Field(
        description="nome di un *NSET gia' scritto, di norma uno dei sei di faccia"
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

    `braccio` dichiara quanto distano fra loro le due forze della coppia, e
    il programma lo contraddice se i nodi presi non lo sostengono. Il
    momento realizzato resta `modulo`: e' la forza a calibrarsi sul braccio
    che i nodi offrono davvero, non il momento a scostarsi da quello
    dichiarato.
    """

    asse: tuple[float, float, float] = Field(
        description="asse del momento, versore non normalizzato"
    )
    modulo: float = Field(gt=0.0, description="modulo del momento [N*mm]")
    braccio: float = Field(gt=0.0, description="distanza fra le due forze della coppia [mm]")


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

    @model_validator(mode="after")
    def _o_forza_o_momento(self) -> "CaricoPosizionato":
        if (self.forza is None) == (self.momento is None):
            raise ValueError(
                f"il carico '{self.nome}' deve dichiarare uno solo fra `forza` e "
                "`momento`: entrambi sono due carichi e vanno scritti come due voci, "
                "nessuno dei due non e' un carico"
            )
        if self.forza is not None and not any(self.forza):
            raise ValueError(
                f"il carico '{self.nome}' ha forza di modulo nullo: scriverebbe un "
                "passo statico identico al peso proprio, con un nome che promette altro"
            )
        return self


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
            "carichi che portano con se' il proprio selettore. Tupla vuota e non "
            "None: il codice a valle itera, e una corsa senza posizionati e una "
            "con la lista vuota sono lo stesso esperimento -- e' la regola che "
            "l'impronta di sweep gia' applica al blocco intero"
        ),
    )


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
    analysis: AnalysisConfig
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
        casi_di_faccia = {nome.casefold(): nome for nome in NOMI_SET_DI_FACCIA}
        visti: dict[str, str] = {}
        for nome in self.selettori:
            chiave = nome.casefold()
            if chiave in casi_di_faccia:
                raise ValueError(
                    f"il selettore {nome!r} collide, ignorando le maiuscole, con il "
                    f"set di faccia {casi_di_faccia[chiave]!r} che il deck fabbrica da "
                    "se': nel deck c'e' un solo spazio di nomi, case-insensitive "
                    "(vedi docs/fase-6-cantiere/sonda-caso-nomi/README.md), e il "
                    "*NSET dell'operatore lo sovrascriverebbe"
                )
            if chiave in visti:
                raise ValueError(
                    f"i selettori {visti[chiave]!r} e {nome!r} differiscono solo per "
                    "maiuscole: nel deck sono lo stesso nome, case-insensitive "
                    "(vedi docs/fase-6-cantiere/sonda-caso-nomi/README.md)"
                )
            visti[chiave] = nome
        return self

    @model_validator(mode="after")
    def _i_posizionati_citano_selettori_dichiarati(self) -> "PipelineConfig":
        # Il confronto sui nomi ignora il caso, come gia' fa
        # `_i_nomi_dei_selettori_non_collidono_coi_sei`. Una sola regola nel
        # modulo, non due: la ragione la' era misurata (ccx risolve gli *NSET
        # senza distinguere le maiuscole, vedi
        # docs/fase-6-cantiere/sonda-caso-nomi/), qui e' che due passi che
        # differiscono solo per caso sono indistinguibili per chi legge il
        # rapporto, e un nome che l'operatore crede nuovo ne sovrascrive uno
        # riservato nella sua testa se non nel deck.
        riservati = {nome.casefold(): nome for nome in NOMI_PASSO_RISERVATI}
        riservati[self.analysis.step_name.casefold()] = self.analysis.step_name
        visti: dict[str, str] = {}
        for carico in self.carichi.posizionati:
            if carico.selettore not in self.selettori:
                raise ValueError(
                    f"il carico '{carico.nome}' cita il selettore "
                    f"'{carico.selettore}', che non e' dichiarato. Dichiarati: "
                    f"{sorted(self.selettori)}"
                )
            chiave = carico.nome.casefold()
            if chiave in riservati:
                raise ValueError(
                    f"il carico '{carico.nome}' porta il nome del passo "
                    f"'{riservati[chiave]}', gia' preso. I riservati sono "
                    f"{list(NOMI_PASSO_RISERVATI)} e il passo di peso proprio si "
                    f"chiama '{self.analysis.step_name}'. Il confronto ignora il "
                    "caso: due passi che differiscono solo per maiuscole sono "
                    "indistinguibili per chi legge il rapporto"
                )
            if chiave in visti:
                raise ValueError(
                    f"due carichi posizionati si chiamano '{visti[chiave]}' e "
                    f"'{carico.nome}': il deck scriverebbe due passi omonimi e i "
                    "due risultati sarebbero indistinguibili nel file risolto"
                )
            visti[chiave] = carico.nome
        return self

    run: RunConfig = Field(default_factory=RunConfig)


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


def carica_yaml(path: Path) -> object:
    """L'unica lettura YAML del modulo, con il rifiuto delle chiavi omonime.

    `yaml.load` con un loader che **eredita da SafeLoader** ha esattamente i
    costruttori di `safe_load`. Non sostituire il loader con `yaml.Loader` o
    `yaml.UnsafeLoader`, che i tag `!!python/object` li eseguono davvero.
    """
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=_LoaderChiaviUniche)  # noqa: S506


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
            "candidati in volo insieme, come processi separati. Non e' il numero "
            "di processori: TetGen ha un picco misurato di 1,35 GB sulla corsa "
            "del muro e la macchina di sviluppo ha 7 GB liberi, quindi quattro "
            "candidati sono circa 5,4 GB di picco. Va tarato sulla macchina che "
            "esegue: nessun valore dedotto dai processori logici e' corretto qui"
        ),
    )
    timeout_s: float = Field(
        default=1800.0,
        gt=0.0,
        description=(
            "tetto al tempo di un singolo candidato, perche' uno patologico non "
            "blocchi lo sweep. La corsa completa piu lenta documentata vale 134 s "
            "e il singolo step piu lento 186 s: e' un tetto contro il patologico, "
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
    base: Path = Field(description="configurazione di partenza, es. muro.yaml")
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
            "di fedelta'"
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
            "ogni corsa. Non e' un limite grafico ma di trasporto"
        ),
    )


class ServerConfig(_ModelloBase):
    """Server locale. Utente singolo, nessuna autenticazione."""

    host: str = "127.0.0.1"
    port: int = Field(default=8765, gt=0, le=65535)
    open_browser: bool = True
