"""Il registro dei coefficienti NTC, la proposta delle combinazioni e la sismica statica.

I numeri attesi vengono da
`docs/validazione/ricerca-ntc-2018-numeri-per-il-catalogo.md`, sezioni 7 e 8,
che li ha letti sul testo di norma. Qui non si ricerca nulla: si verifica che
il codice dica quello che la ricerca ha letto.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from meshrec.core import combinazioni
from meshrec.core.config import (
    CaricoPosizionato,
    CarichiConfig,
    Combinazione,
    InputConfig,
    SelettoreNset,
    SpintaOrizzontale,
)
from materiale import crea_config


# ---------------------------------------------------------------- il registro


def test_ogni_voce_del_registro_porta_una_fonte_e_una_data():
    """Stessa regola di `core/soglie.py`: una voce senza fonte non entra.

    E' la meta' che rende verificabile la pretesa «il numero viene dalla
    norma»: senza fonte resta una costante scritta a memoria, e nessuno puo'
    smentirla.
    """
    voci = [*combinazioni.PSI, *combinazioni.GAMMA]
    assert voci, "il registro è vuoto"
    for voce in voci:
        assert voce.fonte.strip(), f"{voce}: nessuna fonte"
        assert isinstance(voce.fissata, date), f"{voce}: nessuna data"
        assert voce.origine in ("letta", "derivata", "nostra"), voce


def test_una_voce_nostra_senza_nota_e_rifiutata():
    """Un numero scelto da noi senza il motivo scritto accanto non è difendibile."""
    for voce in (*combinazioni.PSI, *combinazioni.GAMMA):
        if voce.origine == "nostra":
            assert voce.nota.strip(), f"{voce}: origine «nostra» senza nota"


def test_i_psi_della_categoria_a_sono_quelli_della_tab_2_5_i():
    """NTC 2018 §2.5.2, Tab. 2.5.I, riga A (residenziale): 0,7 / 0,5 / 0,3."""
    voce = combinazioni.psi_di("A")
    assert (voce.psi_0, voce.psi_1, voce.psi_2) == (0.7, 0.5, 0.3)


def test_i_gamma_sono_quelli_della_colonna_a1_della_tab_2_6_i():
    """NTC 2018 §2.6.1, Tab. 2.6.I, colonna A1 (STR).

    Il γ delle variabili favorevoli è **zero e non uno**: un carico variabile
    che aiuta si toglie, non si riduce.
    """
    g1 = combinazioni.gamma_di("permanente_strutturale")
    g2 = combinazioni.gamma_di("permanente_non_strutturale")
    q = combinazioni.gamma_di("variabile")
    assert (g1.favorevole, g1.sfavorevole) == (1.0, 1.3)
    assert (g2.favorevole, g2.sfavorevole) == (0.8, 1.5)
    assert (q.favorevole, q.sfavorevole) == (0.0, 1.5)


def test_le_categorie_da_valutare_caso_per_caso_non_stanno_nel_registro():
    """I e K: la Tab. 2.5.I scrive «da valutarsi caso per caso», non tre numeri.

    Metterle nel registro con dei numeri vorrebbe dire inventarli.
    """
    presenti = {voce.categoria for voce in combinazioni.PSI}
    assert "I" not in presenti and "K" not in presenti
    with pytest.raises(KeyError, match="caso per caso"):
        combinazioni.psi_di("I")


# ---------------------------------------------------------------- la proposta


def test_un_azione_senza_natura_ferma_la_proposta_e_la_nomina():
    """#146 Q1: senza la natura nessun coefficiente parziale si sceglie da solo.

    Il rifiuto nomina l'azione: chi legge deve sapere quale campo compilare,
    non che «qualcosa» manca.
    """
    with pytest.raises(ValueError, match="VENTO"):
        combinazioni.proponi(
            {"GRAVITA": "permanente_strutturale", "VENTO": None}, "A"
        )


def test_senza_categoria_d_uso_le_combinazioni_non_si_generano():
    """Il programma non può sapere se un solaio è residenziale o un magazzino."""
    with pytest.raises(KeyError):
        combinazioni.proponi({"GRAVITA": "permanente_strutturale"}, "")


def test_nessuna_azione_dichiarata_nessuna_combinazione_proposta():
    """Insieme vuoto: si dichiara, non si schianta e non si inventa un passo."""
    assert combinazioni.proponi({}, "A") == []


def test_la_fondamentale_porta_i_gamma_della_tab_2_6_i():
    """[2.5.1]: γ_G1·G1 + γ_G2·G2 + γ_Q1·Q_k1, colonna A1, tutti sfavorevoli."""
    proposte = combinazioni.proponi(
        {
            "GRAVITA": "permanente_strutturale",
            "IMPIANTI": "permanente_non_strutturale",
            "FOLLA": "variabile",
        },
        "A",
    )
    fondamentali = [c for c in proposte if c.tipo == "slu_fondamentale"]
    assert len(fondamentali) == 1
    assert dict(fondamentali[0].termini) == {
        "GRAVITA": 1.3,
        "IMPIANTI": 1.5,
        "FOLLA": 1.5,
    }


def test_con_due_variabili_la_fondamentale_si_ripete_una_per_ciascuna_base():
    """§2.5.2: `Q_k1` è la variabile di base, le altre l'accompagnano.

    Con n variabili le fondamentali sono n, non una: quale delle due domini
    non si sa prima di risolvere.
    """
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile", "NEVE": "variabile"},
        "A",
    )
    fondamentali = [c for c in proposte if c.tipo == "slu_fondamentale"]
    assert len(fondamentali) == 2
    coefficienti = [dict(c.termini) for c in fondamentali]
    # base FOLLA: gamma_Q su FOLLA, gamma_Q*psi_0 su NEVE (e viceversa)
    assert {"G": 1.3, "FOLLA": 1.5, "NEVE": pytest.approx(1.5 * 0.7)} in coefficienti
    assert {"G": 1.3, "FOLLA": pytest.approx(1.5 * 0.7), "NEVE": 1.5} in coefficienti


def test_la_frequente_e_la_quasi_permanente_differiscono_nel_solo_psi_di_base():
    """[2.5.3] porta ψ_11 sulla base, [2.5.4] porta ψ_2j su tutte.

    Sono le due che si scambiano più facilmente: un solo pedice le distingue.
    """
    azioni = {"G": "permanente_strutturale", "FOLLA": "variabile"}
    proposte = combinazioni.proponi(azioni, "A")
    frequente = next(c for c in proposte if c.tipo == "sle_frequente")
    quasi = next(c for c in proposte if c.tipo == "sle_quasi_permanente")
    assert dict(frequente.termini) == {"G": 1.0, "FOLLA": 0.5}   # psi_1 = 0,5
    assert dict(quasi.termini) == {"G": 1.0, "FOLLA": 0.3}       # psi_2 = 0,3


def test_la_quasi_permanente_e_una_sola_anche_con_due_variabili():
    """[2.5.4] non ha una variabile di base: ψ_2j su tutte, una combinazione."""
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile", "NEVE": "variabile"},
        "A",
    )
    quasi = [c for c in proposte if c.tipo == "sle_quasi_permanente"]
    assert len(quasi) == 1


def test_ogni_proposta_nasce_col_flag_proposta():
    """Il flag dice quali voci nessuno ha ancora guardato."""
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile"}, "A"
    )
    assert proposte and all(c.proposta for c in proposte)


def test_ogni_proposta_porta_almeno_un_termine():
    """Uno `*STEP` senza azioni dà spostamenti nulli, indistinguibili da una
    struttura scarica."""
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile"}, "A"
    )
    assert all(len(c.termini) >= 1 for c in proposte)


def test_una_sola_azione_permanente_da_combinazioni_a_un_termine_solo():
    """Un termine solo è legittimo: è la struttura che porta il proprio peso
    moltiplicato per il γ di norma, non un errore."""
    proposte = combinazioni.proponi({"G": "permanente_strutturale"}, "A")
    fondamentale = next(c for c in proposte if c.tipo == "slu_fondamentale")
    assert fondamentale.termini == (("G", 1.3),)


def test_senza_azione_sismica_la_combinazione_sismica_non_si_propone():
    """[2.5.5] pretende `E`, e nessuna `natura` dichiara «sismica».

    Il programma non sceglie da sé quale azione sia il sisma: si ferma e lo
    dichiara, esattamente come per la natura mancante.
    """
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile"}, "A"
    )
    assert not [c for c in proposte if c.tipo == "sismica"]


def test_con_l_azione_sismica_la_sismica_porta_psi_2_sulle_variabili():
    """[2.5.5]: E + G1 + G2 + ψ_2j·Q_kj, nessun γ."""
    proposte = combinazioni.proponi(
        {"G": "permanente_strutturale", "FOLLA": "variabile", "SISMA": "variabile"},
        "A",
        azione_sismica="SISMA",
    )
    sismica = next(c for c in proposte if c.tipo == "sismica")
    assert dict(sismica.termini) == {"SISMA": 1.0, "G": 1.0, "FOLLA": 0.3}


def test_l_azione_sismica_deve_essere_fra_quelle_dichiarate():
    with pytest.raises(ValueError, match="TERREMOTO"):
        combinazioni.proponi(
            {"G": "permanente_strutturale"}, "A", azione_sismica="TERREMOTO"
        )


# ------------------------------------------------------ correzione a mano


def test_una_combinazione_corretta_a_mano_non_viene_sovrascritta():
    """`proposta=False` dice che il numero l'ha scelto l'operatore.

    Ricalcolare le proposte non può cancellarlo: sarebbe il programma che
    smentisce chi analizza, in silenzio.
    """
    a_mano = Combinazione(
        nome="MIA", tipo="slu_fondamentale",
        termini=(("G", 1.35),), proposta=False,
    )
    azioni = {"G": "permanente_strutturale", "FOLLA": "variabile"}
    aggiornate = combinazioni.aggiorna((a_mano,), azioni, "A")
    assert a_mano in aggiornate
    assert [c for c in aggiornate if not c.proposta] == [a_mano]


def test_una_proposta_vecchia_viene_sostituita_dalla_nuova():
    """Le sole voci `proposta=True` si rifanno: sono quelle che nessuno ha
    ancora guardato."""
    vecchia = Combinazione(
        nome="SLU", tipo="slu_fondamentale",
        termini=(("G", 999.0),), proposta=True,
    )
    aggiornate = combinazioni.aggiorna(
        (vecchia,), {"G": "permanente_strutturale"}, "A"
    )
    assert vecchia not in aggiornate
    assert all(c.proposta for c in aggiornate)


def test_una_correzione_a_mano_omonima_di_una_proposta_vince():
    """Due passi omonimi il deck non li scrive: la configurazione li rifiuta.

    Fra i due vince quello dell'operatore, e la proposta omonima non entra.
    """
    a_mano = Combinazione(
        nome="SLU", tipo="slu_fondamentale",
        termini=(("G", 1.35),), proposta=False,
    )
    aggiornate = combinazioni.aggiorna(
        (a_mano,), {"G": "permanente_strutturale"}, "A"
    )
    omonime = [c for c in aggiornate if c.nome.casefold() == "slu"]
    assert omonime == [a_mano]


# ------------------------------------------------------ la sismica statica


def test_il_periodo_e_due_radici_dello_spostamento_in_metri():
    """[7.3.6] `T_1 = 2·√d`, con `d` **in metri**.

    Il progetto lavora in millimetri: passare millimetri alla formula dà un
    periodo 31,6 volte più grande.
    """
    # 25 mm = 0,025 m -> T_1 = 2*sqrt(0,025) = 0,3162... s
    assert combinazioni.periodo_fondamentale(25.0) == pytest.approx(
        2.0 * math.sqrt(0.025)
    )


def test_una_struttura_che_non_si_sposta_non_ha_un_periodo():
    """Spostamento nullo darebbe `T_1 = 0`: un numero, non un risultato."""
    with pytest.raises(ValueError, match="spostamento"):
        combinazioni.periodo_fondamentale(0.0)


def test_lambda_vale_085_solo_se_entrambe_le_condizioni_valgono():
    """§7.3.3.2: λ = 0,85 se `T_1 < 2·T_C` **e** almeno tre orizzontamenti.

    È congiuntivo: un edificio a due piani non prende lo sconto.
    """
    assert combinazioni.coefficiente_lambda(0.3, 0.5, 3) == 0.85
    assert combinazioni.coefficiente_lambda(0.3, 0.5, 2) == 1.0
    assert combinazioni.coefficiente_lambda(1.2, 0.5, 5) == 1.0


def test_la_forza_di_base_divide_per_g():
    """§7.3.3.2: `F_h = S_d(T_1)·W·λ/g`.

    `S_d` è un'accelerazione e `W` un peso: senza la divisione nasce
    l'errore di un fattore 9,81.
    """
    # S_d = 0,2 g -> F_h = 0,2 * W * lambda
    forza = combinazioni.forza_di_base(0.2 * 9810.0, 1000.0, 0.85)
    assert forza == pytest.approx(0.2 * 1000.0 * 0.85)


def test_una_struttura_senza_peso_non_ha_una_forza_di_base():
    """Una forza nulla spacciata per risultato è il difetto peggiore: valida
    per costruzione, falsa nei fatti."""
    with pytest.raises(ValueError, match="peso"):
        combinazioni.forza_di_base(0.2 * 9810.0, 0.0, 1.0)


def test_le_forze_di_piano_sommano_alla_forza_di_base():
    """[7.3.7]: `F_i = F_h·z_i·W_i / Σ_j z_j·W_j`.

    La somma vale `F_h` per costruzione, ed è la verifica di autoconsistenza
    più economica che questa formula porti con sé.
    """
    quote = np.array([3000.0, 6000.0, 9000.0])
    pesi = np.array([100.0, 100.0, 80.0])
    forze = combinazioni.forze_di_piano(500.0, quote, pesi)
    assert forze.sum() == pytest.approx(500.0)
    # distribuzione triangolare pesata: il piano alto prende più del basso
    assert forze[2] > forze[0]


def test_una_struttura_senza_altezza_non_distribuisce_nulla():
    """Tutte le masse al piano di fondazione: `Σ z_j W_j` è zero, e la
    ripartizione non è definita. Si dichiara, non si divide per zero."""
    with pytest.raises(ValueError, match="quota"):
        combinazioni.forze_di_piano(
            500.0, np.array([0.0, 0.0]), np.array([100.0, 100.0])
        )


def test_una_struttura_senza_massa_non_distribuisce_nulla():
    with pytest.raises(ValueError, match="quota|peso"):
        combinazioni.forze_di_piano(
            500.0, np.array([3000.0, 6000.0]), np.array([0.0, 0.0])
        )


# ------------------------------------------------- le azioni della configurazione


def test_azioni_dichiarate_porta_il_peso_proprio_come_permanente_strutturale():
    """Il passo di peso proprio non ha un campo `natura` da compilare: è `G1`
    per definizione (NTC §2.5.1, «peso proprio degli elementi strutturali»).

    Le altre azioni portano la natura che l'operatore ha dichiarato, `None`
    compreso: la funzione riporta, non completa.
    """
    cfg = crea_config(
        input=InputConfig(path="nuvola.ply"),
        selettori={"CIMA": SelettoreNset(tipo="nset", nome="TOP")},
        carichi=CarichiConfig(
            spinta=SpintaOrizzontale(coefficiente=0.1, asse="y", natura="variabile"),
            posizionati=(
                CaricoPosizionato(
                    nome="PESO_SOLAIO", selettore="CIMA", forza=(0.0, 0.0, -1000.0)
                ),
            ),
        ),
    )
    azioni = combinazioni.azioni_dichiarate(cfg)
    assert azioni["GRAVITA"] == "permanente_strutturale"
    assert azioni["SPINTA_ORIZZONTALE"] == "variabile"
    assert azioni["PESO_SOLAIO"] is None
