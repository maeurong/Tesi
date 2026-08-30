"""Da tetraedro a membratura: chi sta dentro che cosa, e quanto resta fuori.

Il maglio di volume non sa nulla della scomposizione in membrature: e' un
solido unico, e il deck gli attribuisce un materiale solo. Qui il legame si
misura, elemento per elemento, sul **baricentro** (#135): sta dentro il prisma
di una membratura, oppure e' orfano.

Il baricentro e non l'intersezione dei volumi: un tetraedro a cavallo del
confine appartiene per intero a una parte sola, ed e' la sola convenzione che
non spezzi un elemento che il solutore non sa spezzare. Il prezzo si vede e si
misura -- `frazione_orfana` insieme al conteggio dei contesi -- invece di
restare implicito in un'attribuzione che sembra esatta.

Le coordinate sono gia' comuni: `align_to_axes` gira allo step 11 e il prior
misura nello stesso riferimento, quindi qui non si riallinea nulla.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from meshrec.core import abaqus, hexa, quality
from meshrec.core.config import RegioneConfig

_TIPO_DI_PRISMA = "estruso"
"""Il prisma con cui si decide l'appartenenza: sezione e asse **misurati**.

Non e' un parametro di elaborazione. Il maglio da attribuire e' quello del
solido as-built, e il prisma estruso e' quello che ne segue la sezione
rilevata e il fuori piombo; `primitive` -- rettangolo squadrato e asse ideale
-- e' la forma del modello parametrico, cioe' un'altra geometria, e usarlo qui
misurerebbe anche lo scarto fra le due invece della sola appartenenza.
"""


def prismi_delle_regioni(
    membrature: Sequence,
    regioni: Mapping[str, RegioneConfig],
    *,
    tipo: str = _TIPO_DI_PRISMA,
) -> dict[str, hexa.Prisma]:
    """Il prisma di ogni regione dichiarata, nell'ordine della configurazione.

    `membrature` sono quelle del prior (`12_wall.json`), `regioni` il blocco
    `PipelineConfig.regioni`: ogni regione cita l'indice della propria
    membratura, e il rifiuto dell'indice fuori intervallo spetta a chi legge il
    prior -- cioe' a qui, che e' il primo punto in cui le due cose si toccano
    (vedi `RegioneConfig.membratura`).

    Due regioni sulla stessa membratura sono rifiutate: sarebbero due `*ELSET`
    che si contendono gli stessi elementi, e l'ultima sezione scritta vincerebbe
    in silenzio -- misurato su `ccx`, che accetta due `*SOLID SECTION` sovrapposte
    senza un avviso e applica l'ultima.
    """
    di_chi = {}
    for nome, regione in regioni.items():
        if regione.membratura >= len(membrature):
            raise ValueError(
                f"la regione '{nome}' cita la membratura {regione.membratura}, ma il "
                f"prior ne ha {len(membrature)}: gli indici validi vanno da 0 a "
                f"{len(membrature) - 1}"
            )
        gemella = di_chi.setdefault(regione.membratura, nome)
        if gemella != nome:
            raise ValueError(
                f"le regioni '{gemella}' e '{nome}' citano la stessa membratura "
                f"({regione.membratura}): sarebbero due *ELSET sugli stessi "
                "elementi, e nel deck vincerebbe l'ultima sezione scritta"
            )
    return {
        nome: hexa.prisma_di(membrature[regione.membratura], tipo)
        for nome, regione in regioni.items()
    }


def attribuisci(
    nodes: np.ndarray,
    elements: np.ndarray,
    prismi: Mapping[str, hexa.Prisma],
) -> tuple[np.ndarray, dict[str, object]]:
    """Per ogni elemento la posizione della regione che lo contiene, o -1.

    `nodes` sono i nodi del maglio [mm], `elements` gli elementi (4 o 10
    colonne: i primi quattro indici sono i vertici del tetraedro), `prismi` la
    mappa da nome di regione al prisma della sua membratura, quella che
    `prismi_delle_regioni` costruisce.

    Il primo valore e' un `(n,)` di interi: la **posizione** della regione in
    `prismi`, o -1 se l'elemento e' orfano. Posizione e non nome perche' e' un
    array numpy, e chi scrive il deck ricava gli insiemi con
    `{nome: np.flatnonzero(etichette == posizione)}`.

    Il secondo e' il resoconto, che si mostra e non si tace:

        {"elementi_per_regione": {"<nome>": int, ...},   # conteggio
         "volume_per_regione": {"<nome>": float, ...},   # [mm^3]
         "frazione_orfana": float,                       # 0..1, adimensionale
         "contesi_risolti": int}

    Le due mappe sono per **nome** di regione perche' il resoconto finisce in
    `metrics.json` ed e' li' che l'interfaccia lo legge: una chiave posizionale
    la costringerebbe a rifare da sola il legame con la configurazione.

    Un tetraedro conteso fra due regioni va alla membratura **maggiore** per
    area di sezione, che e' il Ruling AD gia' usato in `hexa.taglia_giunzioni`;
    a pari area vince la regione che viene prima in `prismi`. Lo spareggio
    serve perche' «alla maggiore» non decide fra due sezioni identiche, e
    senza di esso deciderebbe l'ordine interno del ciclo invece di un dato.

    Un tetraedro che non cade in nessun prisma e' orfano: prende
    `analysis.material`, il materiale unico della corsa, che resta dov'e'
    (#145). Non e' un ripiego silenzioso -- `frazione_orfana` lo misura, e alta
    significa che la scomposizione non descrive il pezzo.
    """
    elementi = np.asarray(elements, dtype=np.int64)
    # Le righe prima delle colonne: un maglio vuoto darebbe una frazione
    # orfana calcolata su zero elementi, cioe' `nan`, e un resoconto verde su
    # un modello che non esiste. Stesso testo delle due porte di `abaqus.py`,
    # e non un terzo che scivola via da quelle.
    if len(elementi) == 0:
        raise ValueError(abaqus.MAGLIO_VUOTO)
    if elementi.shape[1] not in (4, 10):
        raise ValueError(
            f"elemento con {elementi.shape[1]} nodi: l'attribuzione per baricentro "
            "è definita sui tetraedri (4 o 10 nodi), i cui primi quattro indici "
            "sono i vertici. Su un'altra forma i primi quattro nodi sono una "
            "faccia, e il baricentro cadrebbe altrove senza che nulla protesti"
        )

    punti = np.asarray(nodes, dtype=np.float64)
    baricentri = punti[elementi[:, :4]].mean(axis=1)

    nomi = list(prismi)
    contenuto = np.array(
        [hexa.dentro(prismi[nome], baricentri) for nome in nomi], dtype=bool
    ).reshape(len(nomi), len(elementi))
    aree = np.array([abs(hexa._area_poligono(prismi[nome].contorno)) for nome in nomi])

    etichette = np.full(len(elementi), -1, dtype=np.int64)
    # Dalla peggiore alla migliore, e l'ultima assegnazione vince: area
    # crescente come chiave principale, posizione **decrescente** come
    # spareggio, cosi' a pari area la prima regione e' l'ultima a scrivere.
    for posizione in np.lexsort((-np.arange(len(nomi)), aree)):
        etichette[contenuto[posizione]] = posizione

    volumi = np.abs(quality.element_volumes(punti, elementi))
    return etichette, {
        "elementi_per_regione": {
            nome: int((etichette == posizione).sum()) for posizione, nome in enumerate(nomi)
        },
        "volume_per_regione": {
            nome: float(volumi[etichette == posizione].sum())
            for posizione, nome in enumerate(nomi)
        },
        "frazione_orfana": float((etichette == -1).mean()),
        "contesi_risolti": int((contenuto.sum(axis=0) >= 2).sum()),
    }
