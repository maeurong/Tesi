"""I modelli parametrici: prismi in esaedri, con il volume analitico a smentirli.

hexa.py costruisce e non misura, esattamente come wall.py misura e non
costruisce. Il confine e' cio' che rende questi test possibili: la verita' di
riferimento e' il volume analitico del prisma, calcolato qui e non dal codice
sotto prova.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import hexa, quality
from meshrec.core.config import ModelConfig

# Un rettangolo 200 x 140, in senso antiorario. Sono numeri del banco.
RETTANGOLO = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 140.0], [0.0, 140.0]])
LUNGHEZZA = 1500.0
ASSE_Z = np.array([0.0, 0.0, 1.0])


def test_il_prisma_e_fatto_di_soli_esaedri_e_ne_ha_il_volume_analitico():
    """La verita' di riferimento e' 200 x 140 x 1500: se la mesh non la
    riproduce, ogni massa e ogni confronto che ne discendono sono falsi."""
    nodi, esaedri, metriche = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, ModelConfig()
    )

    assert esaedri.shape[1] == 8, "soli esaedri: nessun prisma a base triangolare"
    volume = quality.hex_volumes(nodi, esaedri).sum()
    assert volume == pytest.approx(200.0 * 140.0 * LUNGHEZZA, rel=1e-6)
    assert metriche["hexes"] == len(esaedri)
    assert metriche["volume_analitico"] == pytest.approx(200.0 * 140.0 * LUNGHEZZA)


def test_nessun_esaedro_del_prisma_ha_jacobiano_non_positivo():
    """Un elemento rovesciato in mezzo a centomila non si vede guardando la
    mesh, e il solutore o si ferma o restituisce numeri senza senso."""
    nodi, esaedri, _ = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, ModelConfig()
    )

    assert (quality.scaled_jacobian(nodi, esaedri) > 0.0).all()


def test_lo_spessore_ha_almeno_tre_strati_di_elementi():
    """Vincolo imposto dal codice e non suggerito: con uno o due strati la
    flessione nello spessore non e' rappresentata, e il risultato e' sbagliato
    senza alcun segnale."""
    cfg = ModelConfig(target_size=1000.0)  # un passo assurdamente grosso

    nodi, esaedri, metriche = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, cfg
    )

    assert metriche["passo"] <= 140.0 / 3.0 + 1e-9, (
        "il passo chiesto e' stato ridotto fino a garantire tre strati nella "
        "sezione minima, o non lo e' stato ed e' un difetto"
    )
    # tre strati nello spessore vogliono almeno quattro piani di nodi
    quote = np.unique(np.round(nodi[:, 1], 6))
    assert len(quote) >= 4


def test_il_prisma_parte_dall_origine_e_va_lungo_l_asse_che_gli_si_da():
    """L'asse misurato conserva il fuori piombo: se la funzione lo ignorasse,
    il modello estruso e quello primitive sarebbero la stessa cosa e il
    confronto non separerebbe piu' i due effetti."""
    asse = np.array([0.0, np.sin(np.radians(5.0)), np.cos(np.radians(5.0))])
    origine = np.array([100.0, 50.0, -20.0])

    nodi, _esaedri, _ = hexa.mesh_prisma(RETTANGOLO, origine, asse, LUNGHEZZA, ModelConfig())

    lungo = (nodi - origine) @ asse
    assert lungo.min() == pytest.approx(0.0, abs=1e-6)
    assert lungo.max() == pytest.approx(LUNGHEZZA, abs=1e-6)


def test_l_ordine_di_nodi_ed_elementi_e_canonico_e_non_quello_dei_tag():
    """Quinto vincolo di prodotto. I tag di gmsh sono un ordine di generazione,
    non un dato della geometria, e il progetto ha gia' pagato una volta la
    lezione dell'ordine di iterazione di una libreria fra due piattaforme.

    Il cubo unitario non basta a provarlo: e' simmetrico per permutazione
    degli assi, quindi non distingue la priorita' x -> y -> z dichiarata da
    `ordine_canonico` da una qualunque altra priorita' fra gli stessi tre
    assi (RULING S). Qui il parallelepipedo ha tre estensioni diverse fra
    loro (1, 2, 3), e la sequenza ordinata attesa e' calcolata a mano
    scorrendo prima tutti gli x=0, poi gli x=1, e dentro ciascuno prima gli
    y piu' piccoli poi quelli piu' grandi, e infine gli z: e' l'unica
    sequenza compatibile con la priorita' x, poi y, poi z."""
    nodi = np.array([
        [1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 2.0, 0.0], [1.0, 2.0, 0.0],
        [1.0, 0.0, 3.0], [0.0, 0.0, 3.0], [0.0, 2.0, 3.0], [1.0, 2.0, 3.0],
    ])
    esaedri = np.array([[1, 0, 3, 2, 5, 4, 7, 6]], dtype=np.int64)

    ordinati, rimappati = hexa.ordine_canonico(nodi, esaedri)

    # sequenza calcolata a mano: x=0 prima di x=1, dentro ciascuno y=0 prima
    # di y=2, dentro ciascuno z=0 prima di z=3. Una priorita' diversa da
    # x -> y -> z (per esempio z -> y -> x) produrrebbe un'altra sequenza,
    # perche' le tre estensioni sono diverse fra loro e nessuna permutazione
    # delle chiavi coincide con un'altra: verificato permutando le chiavi del
    # lexsort e osservando la sequenza cambiare (vedi task-7-report.md).
    attesi = np.array([
        [0.0, 0.0, 0.0], [0.0, 0.0, 3.0], [0.0, 2.0, 0.0], [0.0, 2.0, 3.0],
        [1.0, 0.0, 0.0], [1.0, 0.0, 3.0], [1.0, 2.0, 0.0], [1.0, 2.0, 3.0],
    ])
    assert ordinati == pytest.approx(attesi)
    # l'elemento punta agli stessi punti fisici di prima
    assert np.sort(ordinati[rimappati[0]], axis=0) == pytest.approx(
        np.sort(nodi[esaedri[0]], axis=0)
    )
    # e il volume non e' cambiato: la topologia interna dell'elemento resta
    assert quality.hex_volumes(ordinati, rimappati) == pytest.approx(
        quality.hex_volumes(nodi, esaedri)
    )


def test_metriche_strati_conta_i_piani_di_nodi_lungo_l_asse():
    """`metriche["strati"]` dichiara il vincolo portante del task (RULING U):
    non puo' essere l'unico testimone di se stesso. N strati di elementi
    vogliono N+1 piani di nodi distinti lungo l'asse di estrusione, ed e'
    quello che si conta qui, indipendentemente da come il numero e' stato
    calcolato."""
    nodi, _esaedri, metriche = hexa.mesh_prisma(
        RETTANGOLO, np.zeros(3), ASSE_Z, LUNGHEZZA, ModelConfig()
    )

    piani = np.unique(np.round(nodi[:, 2], 6))
    assert len(piani) == metriche["strati"] + 1


def test_mesh_prisma_rifiuta_una_lunghezza_non_positiva():
    """RULING U: senza guardia, lunghezza=0 o negativa producono una mesh
    valida in forma ma di volume nullo o negativo, senza alcun segnale."""
    with pytest.raises(ValueError, match="lunghezza"):
        hexa.mesh_prisma(RETTANGOLO, np.zeros(3), ASSE_Z, 0.0, ModelConfig())
    with pytest.raises(ValueError, match="lunghezza"):
        hexa.mesh_prisma(RETTANGOLO, np.zeros(3), ASSE_Z, -1500.0, ModelConfig())


def test_passo_di_mesh_rifiuta_un_contorno_con_estensione_nulla_su_un_asse():
    """RULING U: un contorno degenere (per esempio appiattito su un asse) fa
    scendere la sezione minima a zero; senza guardia il passo si azzera e la
    divisione successiva fallisce con un errore che non dice ne' il valore
    ne' la ragione."""
    degenere = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 0.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match="estensione"):
        hexa.passo_di_mesh(degenere, ModelConfig())
