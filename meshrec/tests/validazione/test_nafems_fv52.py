"""NAFEMS FV52: piastra quadrata spessa, appoggiata, analisi modale.

Ticket https://github.com/maeurong/Tesi/issues/48. La scheda completa, letta
dalle fonti, sta in `docs/validazione/benchmark-nafems.md` §6.

**Perche' FV52 e non FV32.** FV32 e' una membrana **piana**: non esercita un
esportatore di solidi. FV52 e' l'unico benchmark modale della serie pensato per
elementi solidi tridimensionali -- NAFEMS lo elenca cosi': «3D solid elements:
... simply supported solid square plate (52)».

**Il numero e' 52.** «FV51» che circola e' un errore di TechSoft3D, che intitola
la piastra e cita il numero della trave. Sciolto in
`docs/validazione/benchmark-nafems.md` §7.

**Due set di target, e si usa quello numerico.** NAFEMS ne pubblica due per ogni
prova: uno in forma chiusa (45,897 Hz sul modo 4) e uno numerico (44,092 Hz).
Si usa il **numerico**, perche' e' quello contro cui Abaqus tabula gli errori
per tipo di elemento, e mescolarli darebbe uno scarto del 4% che non e' del
nostro modello.

**Il vincolo e' cinematicamente incompleto, e deve esserlo.** `u_z = 0` sui soli
quattro spigoli della faccia inferiore, e nient'altro: nessun grado in x e y e'
bloccato. I primi tre modi **devono** uscire moti rigidi a frequenza nulla, e
la lettura comincia dal quarto. Fissare un insieme in tutti e tre i gradi
renderebbe il problema un altro problema -- ed e' il motivo per cui `write_inp`
ha imparato ad accettare `fixed_nset=None`.

**Unita'.** La scheda e' in metri, GPa e kg/m^3; qui si lavora nelle unita' del
progetto -- mm, N, MPa, tonnellata -- come `PRODUCT.md` impone. Le frequenze in
Hz non cambiano, perche' il sistema e' coerente.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from meshrec.core import abaqus, solve, synth, volume
from meshrec.core.config import CarichiConfig, Material, Modale

pytestmark = pytest.mark.validazione

LATO = 10_000.0  # mm  (10 m)
SPESSORE = 1_000.0  # mm  (1 m)
MATERIALE = Material(
    name="FV52",
    young=200_000.0,  # MPa  (200 GPa)
    poisson=0.3,
    density=8.0e-9,  # t/mm^3  (8000 kg/m^3)
)

# Set **numerico** dei target, modi 4-10 [Hz]. Non quello in forma chiusa.
TARGET = (44.092, 106.66, 106.66, 156.23, 193.58, 200.13, 200.13)

# Errori che Abaqus pubblica per C3D10 sugli stessi modi, in percento. Servono
# da metro: un elemento quadratico che sbaglia molto piu' di cosi' ha un
# problema che non e' l'elemento.
ABAQUS_C3D10 = (0.58, 1.00, 1.00, 4.70, 0.02, 2.30, 2.48)

MODI_RIGIDI = 3


def _ccx_o_salta() -> str:
    eseguibile = shutil.which("ccx")
    if eseguibile is None:
        pytest.skip("eseguibile 'ccx' non presente nel PATH")
    return eseguibile


def _piastra(order: int, passo: float) -> tuple[np.ndarray, np.ndarray]:
    vertici, facce = synth.box_mesh((LATO, LATO, SPESSORE))
    return volume.tetrahedralize(
        vertici, facce,
        max_volume=passo**3 / 6.0, min_ratio=1.8, max_steiner_points=-1, nobisect=False,
        order=order,
    )


def _spigoli_inferiori(nodi: np.ndarray) -> np.ndarray:
    """I nodi sui quattro spigoli della faccia inferiore.

    «Z = 0 along the 4 edges on the plane Z = -0.5m», cioe' i nodi che stanno
    **sia** sulla faccia inferiore **sia** sul perimetro in pianta. Non tutta
    la faccia inferiore: quello sarebbe un incastro distribuito, un altro
    problema.
    """
    tolleranza = 1e-6
    sotto = nodi[:, 2] < tolleranza
    perimetro = (
        (nodi[:, 0] < tolleranza)
        | (nodi[:, 0] > LATO - tolleranza)
        | (nodi[:, 1] < tolleranza)
        | (nodi[:, 1] > LATO - tolleranza)
    )
    return np.flatnonzero(sotto & perimetro)


def _frequenze(tmp_path, order: int, tipo: str, passo: float) -> list[float]:
    eseguibile = _ccx_o_salta()
    nodi, tets = _piastra(order, passo)
    appoggio = _spigoli_inferiori(nodi)
    assert len(appoggio) >= 12, f"solo {len(appoggio)} nodi sugli spigoli: maglia inadeguata"

    abaqus.write_inp(
        tmp_path / "fv52.inp", nodi, tets,
        material=MATERIALE, element_type=tipo,
        node_sets={"APPOGGIO": appoggio, "TUTTI": np.arange(len(nodi))},
        # Nessun set bloccato in tutti e tre i gradi: il vincolo di FV52 e'
        # cinematicamente incompleto per costruzione.
        fixed_nset=None,
        spostamenti_imposti={int(i): {3: 0.0} for i in appoggio},
        gravity=0.0,
        carichi=CarichiConfig(modale=Modale(modi=MODI_RIGIDI + len(TARGET))),
    )
    esito = subprocess.run(
        [eseguibile, "-i", "fv52"],
        cwd=tmp_path, capture_output=True, text=True, timeout=3600,
    )
    assert esito.returncode == 0, esito.stdout[-3000:] + esito.stderr[-3000:]
    frequenze = solve.leggi_frequenze(tmp_path / "fv52.dat")
    assert frequenze, "nessuna frequenza letta dal .dat"
    return frequenze


def test_i_primi_tre_modi_sono_rigidi(tmp_path):
    """Il vincolo lascia liberi x e y: tre moti rigidi, e devono uscire nulli.

    Se non uscissero nulli, il deck starebbe vincolando qualcosa che FV52 non
    vincola -- e le frequenze successive sarebbero di un altro problema.
    """
    frequenze = _frequenze(tmp_path, order=2, tipo="C3D10", passo=900.0)
    rigidi = frequenze[:MODI_RIGIDI]
    primo_elastico = frequenze[MODI_RIGIDI]
    print(f"\nmodi rigidi letti: {[f'{f:.4f}' for f in rigidi]} Hz")
    for f in rigidi:
        assert abs(f) < 1e-3 * primo_elastico, (
            f"modo rigido a {f:.4f} Hz contro un primo elastico di {primo_elastico:.2f}: "
            "il deck vincola piu' di quanto FV52 preveda"
        )


def test_le_frequenze_contro_il_set_numerico_nafems(tmp_path):
    """I sette modi elastici contro i target, con gli errori di Abaqus a fianco.

    Il confronto non e' «coincide» ma «sta nello stesso mondo di un solutore
    commerciale sullo stesso benchmark». Abaqus con C3D10 sbaglia fino al 4,70%
    sul modo 7; pretendere meno da noi sarebbe pretendere piu' di lui.
    """
    frequenze = _frequenze(tmp_path, order=2, tipo="C3D10", passo=900.0)
    elastici = frequenze[MODI_RIGIDI:MODI_RIGIDI + len(TARGET)]
    assert len(elastici) == len(TARGET), (
        f"letti {len(elastici)} modi elastici invece di {len(TARGET)}"
    )

    print("\nmodo   nostro      NAFEMS    scarto    Abaqus C3D10")
    scarti: list[float] = []
    for indice, (nostro, atteso, abaqus_err) in enumerate(
        zip(elastici, TARGET, ABAQUS_C3D10, strict=True), start=4
    ):
        scarto = (nostro - atteso) / atteso
        scarti.append(scarto)
        print(f"{indice:>4}  {nostro:>8.3f}  {atteso:>8.3f}  {scarto:>+7.2%}  {abaqus_err:>10.2f}%")

    # **Sotto il target non e' una violazione.** Il metodo agli spostamenti da'
    # un limite superiore agli autovalori del **continuo**; il target NAFEMS e'
    # a sua volta **numerico**, non la soluzione esatta -- la scheda lo
    # qualifica cosi'. Una frequenza qualche decimo sotto un target numerico
    # significa solo che il nostro maglio e' diverso dal suo, non che il
    # teorema e' caduto. Una sottostima **marcata** invece indicherebbe un
    # vincolo di troppo, ed e' quella che la soglia sorveglia.
    assert min(scarti) > -0.05, (
        f"un modo sta il {min(scarti):.1%} sotto il target: il metodo agli spostamenti "
        "da' un limite superiore, quindi una sottostima marcata e' un difetto del deck"
    )
    assert max(abs(s) for s in scarti) < 0.15, (
        f"scarto massimo {max(abs(s) for s in scarti):.1%}: fuori dal mondo di Abaqus, "
        "che sullo stesso benchmark con C3D10 arriva al 4,70%"
    )


def test_i_due_modi_gemelli_restano_gemelli(tmp_path):
    """I modi 5 e 6, e i 9 e 10, sono degeneri: la piastra e' **quadrata**.

    E' un oracolo che non dipende da alcun target: discende dalla simmetria
    della geometria. Se i gemelli si separassero, il maglio avrebbe rotto una
    simmetria che il problema ha, e ogni altro confronto sarebbe sospetto.

    Non si pretende coincidenza esatta: un maglio tetraedrico non e' simmetrico
    nemmeno su una geometria simmetrica, ed e' proprio questa la misura di
    quanto quell'asimmetria costi.
    """
    frequenze = _frequenze(tmp_path, order=2, tipo="C3D10", passo=900.0)
    elastici = frequenze[MODI_RIGIDI:MODI_RIGIDI + len(TARGET)]
    for primo, secondo, nomi in ((1, 2, "5 e 6"), (5, 6, "9 e 10")):
        a, b = elastici[primo], elastici[secondo]
        separazione = abs(a - b) / max(a, b)
        print(f"\nmodi {nomi}: {a:.3f} e {b:.3f} Hz, separati del {separazione:.2%}")
        assert separazione < 0.05, (
            f"i modi {nomi} dovrebbero essere degeneri e distano il {separazione:.1%}: "
            "il maglio ha rotto la simmetria della piastra quadrata"
        )
