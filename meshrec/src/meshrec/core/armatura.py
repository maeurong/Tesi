"""L'armatura dichiarata, collocata nella sezione misurata, e il verdetto che ne esce.

**Le posizioni delle barre non sono un dato.** L'operatore dichiara quante barre,
di che diametro, con che copriferro (`config.ArmaturaConfig`); la sezione la
misura la nuvola, fetta per fetta (`wall.Membratura.sezioni_fette`). Dove
finiscano le barre e' il derivato dei due, e cambia stazione per stazione perche'
la sezione cambia lungo l'asse. Chiedere le posizioni all'operatore
significherebbe fargli battere a mano cio' che il rilievo gia' sa.

**Il programma rileva, non progetta** (#136). Una sezione sotto il minimo di
norma e' un risultato da mostrare, non un ingresso da rifiutare: chi descrive un
edificio esistente descrive cio' che ha misurato, e un programma che gli
impedisse di dichiararlo sarebbe un programma per edifici nuovi. Il verdetto
riferisce e il modello si costruisce comunque.

**Una sola cosa ferma il calcolo, ed e' la geometria impossibile.** Se le barre
non stanno nella sezione -- in larghezza fra le staffe, o in altezza col
baricentro teso fuori dal calcestruzzo -- non c'e' una sezione da descrivere, e
`mu = A_s/(b d)` non e' un rapporto ma un simbolo. Non e' norma disattesa: e'
aritmetica che non parte.

**Che cosa non sta qui.** L'interferro minimo: le NTC lo rapportano alla
dimensione massima degli inerti (§4.1.6.1.3), che nessun campo di configurazione
dichiara, e EC2 8.2(2) lo lega a `dg`. Manca l'ingresso, quindi l'interferro
netto si misura e si mostra e non si giudica -- come il riempimento di sezione,
che per la stessa ragione non e' una voce di `core/soglie.py`.

**Divergenza dal contratto §4.5**, dichiarata: `verdetti` ricava `f_cd`, `f_yd` e
`f_yk` dal catalogo invece di riceverli, cosi' la classe che l'operatore ha
scritto e le resistenze con cui si giudica non possono divergere, e il rifiuto di
`materiali.trova` arriva intero a chi ha sbagliato la classe. `f_ctm` resta un
argomento perche' il catalogo non lo porta: `core/materiali.py` lo dichiara fuori
nel proprio docstring, insieme a `epsilon_c2` e `epsilon_cu`.
"""

from __future__ import annotations

import math
from typing import Literal, NamedTuple

import numpy as np

from meshrec.core import materiali
from meshrec.core.config import ArmaturaConfig

EPS_C2 = 0.0020
"""Deformazione di picco del parabola-rettangolo, NTC 2018 §4.1.2.1.2.1: 0,20%."""

EPS_CU = 0.0035
"""Deformazione ultima del calcestruzzo, NTC 2018 §4.1.2.1.2.1: 0,35%.

Vale, come `EPS_C2`, per le sole classi fino alla C50/60. Oltre, lo stesso § le
rende funzioni di `f_ck`, e `_resistenze` si ferma la' invece di riusare questi
due -- non per le deformazioni, che le formule danno, ma per l'esponente della
parabola che serve ad `ALFA`, e che nessuna delle fonti lette pubblica.
"""

ALFA = 1.0 - EPS_C2 / (3.0 * EPS_CU)
"""Coefficiente di riempimento del diagramma parabola-rettangolo completo: 0,809524.

Forma chiusa dell'integrale del legame con esponente 2, verificata su nove punti
delle tavole del Bollettino CEB 123 in
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md` §4.3. **Non e' un
numero di norma**: le NTC danno le deformazioni e non l'esponente. Si scrive
esatto e non 0,81 come lo arrotonda la dispensa, perche' fra le due varianti
corrono 0,06% e l'oracolo di collaudo si confronta a cinque decimali.
"""

RAPPORTO_MINIMO_ASSOLUTO = 0.0013
"""Il «e comunque» della [4.1.45], NTC 2018 §4.1.6.1.1: `A_s,min >= 0,0013 b_t d`.

Governa fino alla C25/30 compresa, dove `0,26 f_ctm/f_yk` gli sta sotto.
"""

_F_CK_DELLE_DEFORMAZIONI_COSTANTI = 50.0
"""Sopra questo `f_ck` [MPa] le deformazioni limite dipendono dalla classe."""


class BarraCollocata(NamedTuple):
    """Una barra longitudinale, nel piano di sezione di **una** stazione.

    Le coordinate sono nel piano `(e1, e2)` di `wall.Membratura.base_sezione`,
    misurate da uno spigolo della sezione: `y` lungo e1 in `[0, b]`, `z` lungo e2
    in `[0, h]`, con `z = 0` sul bordo teso.
    """

    y: float
    """Posizione lungo e1 [mm], all'**asse** della barra."""
    z: float
    """Posizione lungo e2 [mm], all'asse della barra. Il bordo teso e' z = 0."""
    diametro: float
    """Diametro nominale [mm]."""


class VerdettoStazione(NamedTuple):
    """Che cosa si sa della sezione a una stazione. Un verdetto per fetta, non per membratura.

    Una gabbia dichiarata una volta sola puo' essere duttile dove la sezione e'
    piena e fragile dove si restringe: un verdetto solo per membratura
    appiattirebbe le due cose in una.
    """

    quota: float
    """Coordinata della stazione lungo l'asse [mm], dall'origine della membratura."""
    b: float
    """Estensione lungo e1 [mm]. E' la base su cui `mu` si misura."""
    h: float
    """Estensione lungo e2 [mm]. E' l'altezza in cui `d` scende."""
    d: float
    """Altezza utile [mm]: `h - copriferro - Ø_staffa - Ø_teso/2`."""
    mu: float
    """`A_s/(b d)`, rapporto geometrico dell'armatura tesa. Adimensionale."""
    mu_min: float
    """`max(0,26 f_ctm/f_yk ; 0,0013)` -- NTC 2018 §4.1.6.1.1, [4.1.45]."""
    mu_bil: float
    """`alpha f_cd k_bil / f_yd`, il rapporto della sezione bilanciata."""
    verdetto: Literal["fragile", "duttile", "oltre_la_bilanciata"]
    """Dove `mu` cade fra i due estremi. Riferisce, non rifiuta."""
    interferro_netto: float
    """Distanza **libera** fra due barre tese adiacenti [mm]. Calcolata, non dichiarata."""
    copriferro_netto: float
    """Copriferro vero della barra longitudinale [mm]: il dichiarato piu' Ø_staffa.

    L'operatore dichiara il copriferro alla staffa, che e' l'elemento piu'
    esterno (`docs/validazione/ricerca-armature-convenzioni-normative.md` §1.3).
    Il numero che copre la barra longitudinale e' un altro, ed e' questo.
    """


def bilanciata(f_cd: float, f_yd: float, young_acciaio: float) -> tuple[float, float]:
    """`(k_bil, mu_bil)` della sezione bilanciata, dalle sole ipotesi del §4.1.2.3.4.1.

    Rottura bilanciata: `eps_c = eps_cu` e `eps_s = eps_yd` nella stessa sezione.
    Dalla similitudine dei triangoli del diagramma lineare delle deformazioni,
    e poi dall'equilibrio alla traslazione col coefficiente di riempimento:

        k_bil  = eps_cu / (eps_cu + f_yd/E_s)
        mu_bil = alpha f_cd k_bil / f_yd

    «Bilanciata» non e' una parola delle NTC -- zero occorrenze nel testo -- ma
    la costruzione poggia solo sulle ipotesi che il §4.1.2.3.4.1 elenca.

    `E_s` e' un argomento e non una costante perche' le fonti divergono: 200.000
    di UNI EN 1992-1-1 §3.2.7(4), che il catalogo porta e con cui l'oracolo di
    collaudo torna, contro i 210.000 della Circolare §C4.1.2.2.5, con cui
    `k_bil` passa da 0,641434 a 0,652577.
    """
    k_bil = EPS_CU / (EPS_CU + f_yd / young_acciaio)
    return k_bil, ALFA * f_cd * k_bil / f_yd


def colloca(armatura: ArmaturaConfig, sezione: tuple[float, float]) -> list[BarraCollocata]:
    """Le barre di **una** stazione, tese per prime e compresse poi, ordinate per `y`.

    `sezione` sono le due estensioni della fetta [mm], nell'ordine di
    `wall.Membratura.sezioni_fette`: la prima lungo e1, la seconda lungo e2.
    L'ordine non si raddrizza -- niente `min`/`max` -- perche' una 300x500 e una
    500x300 sono due sezioni diverse e non due scritture della stessa.

    Le barre si spartiscono la luce fra le staffe a interferro costante, con le
    due estreme a filo. Con una barra sola non c'e' interferro da spartire e la
    barra sta in mezzo.

    Solleva se le barre non ci stanno. E' l'unica guardia che ferma in tutto il
    modulo, ed e' geometria: senza posto per l'armatura non c'e' sezione, e
    `A_s/(b d)` non e' un rapporto.
    """
    b, h = float(sezione[0]), float(sezione[1])
    scostamento = float(armatura.copriferro_nominale) + float(armatura.diametro_staffe)

    z_teso = scostamento + armatura.diametro_teso / 2.0
    if h - scostamento - armatura.diametro_teso / 2.0 <= 0.0:
        raise ValueError(
            f"sezione alta {h:g} mm: l'altezza utile è "
            f"{h - scostamento - armatura.diametro_teso / 2.0:g} mm, cioè il baricentro "
            f"dell'armatura tesa cade fuori dal calcestruzzo (copriferro {armatura.copriferro_nominale:g} "
            f"+ staffa {armatura.diametro_staffe:g} + mezza barra {armatura.diametro_teso / 2.0:g})"
        )

    barre = _fila(armatura.barre_tese, float(armatura.diametro_teso), b, scostamento, z_teso)
    if armatura.barre_compresse:
        z_compresso = h - scostamento - armatura.diametro_compresso / 2.0
        if z_compresso <= z_teso:
            raise ValueError(
                f"sezione alta {h:g} mm: le barre compresse cadrebbero a {z_compresso:g} mm "
                f"e le tese stanno a {z_teso:g} mm, cioè i due strati si attraversano"
            )
        barre += _fila(
            armatura.barre_compresse,
            float(armatura.diametro_compresso),
            b,
            scostamento,
            z_compresso,
        )
    return barre


def verdetti(
    armatura: ArmaturaConfig,
    sezioni_fette: np.ndarray,
    quote_fette: np.ndarray,
    f_ctm: float,
) -> list[VerdettoStazione]:
    """Un verdetto per stazione, nell'ordine delle fette. Riferisce e non ferma.

    `sezioni_fette` e' `(n, 2)` [mm] e `quote_fette` e' `(n,)` [mm], nella forma
    che `wall.misura` produce. Vuote danno lista vuota: una membratura senza
    fette misurabili non ha sezioni da giudicare, e la `sezione` media e' una
    sintesi, non una stazione.

    `f_ctm` [MPa] arriva da fuori perche' il catalogo dei materiali non lo porta.

    Solleva solo per la geometria impossibile di `colloca`, e per la classe che
    il catalogo non ha.
    """
    sezioni = np.asarray(sezioni_fette, dtype=np.float64).reshape(-1, 2)
    quote = np.asarray(quote_fette, dtype=np.float64).reshape(-1)
    if len(sezioni) != len(quote):
        raise ValueError(
            f"le stazioni non tornano: {len(sezioni)} sezioni e {len(quote)} quote. "
            "Senza la propria quota una sezione non colloca nulla, e la coppia sbagliata "
            "sposterebbe ogni verdetto sulla stazione successiva"
        )

    f_cd, f_yd, f_yk, young_acciaio = _resistenze(armatura)
    _, mu_bil = bilanciata(f_cd, f_yd, young_acciaio)
    mu_min = max(0.26 * f_ctm / f_yk, RAPPORTO_MINIMO_ASSOLUTO)
    area_tesa = armatura.barre_tese * math.pi * armatura.diametro_teso**2 / 4.0
    copriferro_netto = float(armatura.copriferro_nominale) + float(armatura.diametro_staffe)

    esiti = []
    for (b, h), quota in zip(sezioni, quote):
        try:
            barre = colloca(armatura, (b, h))
        except ValueError as errore:
            raise ValueError(f"stazione a quota {quota:g} mm: {errore}") from errore
        d = h - copriferro_netto - armatura.diametro_teso / 2.0
        mu = area_tesa / (b * d)
        esiti.append(
            VerdettoStazione(
                quota=float(quota),
                b=float(b),
                h=float(h),
                d=float(d),
                mu=float(mu),
                mu_min=float(mu_min),
                mu_bil=float(mu_bil),
                verdetto=_giudizio(mu, mu_min, mu_bil),
                interferro_netto=barre[1].y - barre[0].y - barre[0].diametro,
                copriferro_netto=copriferro_netto,
            )
        )
    return esiti


def _fila(
    numero: int, diametro: float, b: float, scostamento: float, z: float
) -> list[BarraCollocata]:
    """Una fila di barre a quota `z`, spartita sulla luce fra le staffe."""
    luce = b - 2.0 * scostamento
    ingombro = numero * diametro
    if ingombro > luce:
        raise ValueError(
            f"sezione larga {b:g} mm: {numero} barre da {diametro:g} mm ingombrano "
            f"{ingombro:g} mm e fra le staffe ce ne sono {luce:g}"
        )
    if numero == 1:
        return [BarraCollocata(b / 2.0, z, diametro)]
    passo = (luce - diametro) / (numero - 1)
    primo = scostamento + diametro / 2.0
    return [BarraCollocata(primo + i * passo, z, diametro) for i in range(numero)]


def _giudizio(
    mu: float, mu_min: float, mu_bil: float
) -> Literal["fragile", "duttile", "oltre_la_bilanciata"]:
    """Dove `mu` cade. Il minimo si guarda per primo: e' quello che la norma impone."""
    if mu < mu_min:
        return "fragile"
    if mu > mu_bil:
        return "oltre_la_bilanciata"
    return "duttile"


def _resistenze(armatura: ArmaturaConfig) -> tuple[float, float, float, float]:
    """`(f_cd, f_yd, f_yk, E_s)` dalle due classi dichiarate, via catalogo.

    `f_yk` e non `f_yd` nel minimo di norma: la [4.1.45] e' tarata sulla
    resistenza caratteristica, e usare quella di progetto alzerebbe il minimo del
    15%.
    """
    calcestruzzo = materiali.trova(armatura.classe_calcestruzzo)
    if calcestruzzo.f_k > _F_CK_DELLE_DEFORMAZIONI_COSTANTI:
        raise ValueError(
            f"{calcestruzzo.classe}: oltre la C50/60 le deformazioni limite dipendono dalla "
            "classe (NTC 2018 §4.1.2.1.2.1), e l'esponente della parabola da cui alpha si "
            "ricava non è pubblicato in nessuna delle fonti lette "
            "(docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md §4.2). "
            "Il rapporto della sezione bilanciata non è calcolabile: il dato manca, e "
            "riusare lo 0,809524 delle classi ordinarie sarebbe indovinarlo"
        )
    acciaio = materiali.trova(armatura.classe_acciaio)
    return (
        materiali.valori_di_progetto(calcestruzzo)["f_cd"],
        materiali.valori_di_progetto(acciaio)["f_yd"],
        acciaio.f_k,
        acciaio.young,
    )
