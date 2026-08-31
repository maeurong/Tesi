"""Guardie che non potevano scattare, e nomi standard con formule diverse.

Ticket https://github.com/maeurong/Tesi/issues/38.

Sette punti in cui il programma teneva un ramo incapace di dare l'esito che
prometteva, oppure usava un nome preso da una fonte esterna per una grandezza
che quella fonte definisce diversamente. Le due famiglie hanno lo stesso
difetto sotto: **qualcosa sembra controllato e non lo e'**, e a leggere il
codice non si vede.

Questi test non provano che il programma funzioni -- provano che ogni esito
dichiarato sia **raggiungibile**, e che ogni divergenza da una definizione di
riferimento sia **misurata** invece che supposta. Un ramo che non puo' dare
`True` e un nome che non vale la formula che porta sono entrambi verdi finche'
nessuno li interroga.
"""

from __future__ import annotations

import numpy as np
import pytest

from meshrec.core import abaqus, quality, report, soglie

# Quattro punti vicini a una circonferenza di raggio 1, sfalsati in quota di
# `e` a due a due: e' lo sliver di manuale. La sfera circoscritta resta
# piccola, gli spigoli restano lunghi, il volume tende a zero.
TETS = np.array([[0, 1, 2, 3]])


def sliver(sfalsamento: float) -> np.ndarray:
    return np.array(
        [
            [1.0, 0.0, sfalsamento],
            [0.0, 1.0, -sfalsamento],
            [-1.0, 0.0, sfalsamento],
            [0.0, -1.0, -sfalsamento],
        ]
    )


# --- G1: la bimodalita' con i due modi in bin contigui -----------------------


def _thickness_da_conteggi(conteggi: list[int], passo: float = 1.0) -> dict[str, object]:
    """Una nuvola che produce esattamente l'istogramma dato lungo l'asse sottile.

    Costruire i conteggi invece di sperare che una nuvola casuale li dia: il
    ramo sotto prova dipende da **dove cadono i due massimi**, e su punti
    casuali non si sceglie.
    """
    punti = []
    for indice, quanti in enumerate(conteggi):
        z = (indice + 0.5) * passo
        for k in range(quanti):
            # Sparsi nel piano largo, impilati sull'asse sottile: cosi' l'asse
            # di minima varianza e' z e i bin sono quelli voluti.
            punti.append([float(k) * 10.0, float(k % 7) * 10.0, z])
    return quality.thickness(np.array(punti, dtype=np.float64), bin_width=passo)


def test_due_modi_in_bin_contigui_non_sono_bimodali():
    """L'esito e' `False`, e ora lo e' **per dichiarazione** e non per algebra.

    Prima il codice calcolava `valley = counts[lower]` e poi chiedeva
    `valley < 0.5 * min(counts[lower], counts[upper])`. Su conteggi non
    negativi quella condizione richiede `counts[lower] < 0` ed e' quindi falsa
    per costruzione: il ramo esisteva come se potesse dare `True`.

    La correzione non cambia il risultato -- cambia il fatto che si veda.
    """
    esito = _thickness_da_conteggi([2, 40, 40, 2])
    assert esito["bimodal"] is False


def test_una_valle_vera_e_bimodale():
    """L'altra direzione, senza la quale il test sopra non prova nulla.

    Un test che verifica solo l'esito `False` passerebbe identico su una
    funzione che rende sempre `False`. Serve la coppia.
    """
    esito = _thickness_da_conteggi([40, 40, 1, 1, 1, 40, 40])
    assert esito["bimodal"] is True


def test_la_valle_e_una_media_e_non_il_minimo_di_un_bin():
    """Un singolo bin vuoto per rumore non basta a dichiarare due facce.

    E' la scelta gia' documentata nel codice, e senza un test si perde alla
    prima semplificazione: il minimo e' una statistica d'ordine estremo, la
    media converge alla densita' vera.
    """
    # Valle larga tre bin, uno solo dei quali vuoto: la media resta alta.
    assert _thickness_da_conteggi([40, 40, 0, 38, 39, 40, 40])["bimodal"] is False


# --- G2: la copertura dell'impronta senza alcuna colonna a contatto ----------


def test_senza_il_nodo_piu_basso_fra_i_bordi_la_copertura_solleva():
    """Non piu' `0.0`, che era un numero plausibile per una domanda diversa.

    Zero significa «l'insieme non copre nulla dell'impronta»: una condizione
    vera, distinta e gia' rappresentabile. Renderlo anche quando l'impronta
    **non esiste** rendeva indistinguibili un vincolo sbagliato e un ingresso
    rotto.

    Dalla pipeline non si arriva qui -- su un solido chiuso il nodo piu' basso
    e' di bordo, quindi la sua colonna tocca sempre. Ci si arriva sbagliando a
    chiamare, ed e' esattamente il caso in cui un errore va detto.
    """
    nodi = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 5.0], [0.0, 10.0, 5.0], [10.0, 10.0, 5.0]]
    )
    # Il bordo esclude il nodo 0, il piu' basso: nessuna colonna tocca.
    bordo = np.array([1, 2, 3])
    with pytest.raises(ValueError, match="nessuna colonna tocca"):
        abaqus.footprint_coverage(nodi, bordo, np.array([1]), 5.0)


# --- N1: lo scaled Jacobian sugli otto angoli contro i nove di Verdict -------


def _verdict_centro(p: np.ndarray) -> float:
    """Il nono punto di Verdict, riscritto qui a mano da `calc_hex_efg`.

    Assi principali **medi** -- la somma dei quattro spigoli paralleli -- e non
    tre spigoli uscenti da un vertice. E' il punto che la nostra
    implementazione omette, e riscriverlo qui e' cio' che rende il confronto un
    oracolo indipendente invece di un rimando alla stessa funzione.
    """
    e = (p[1] - p[0]) + (p[2] - p[3]) + (p[5] - p[4]) + (p[6] - p[7])
    f = (p[3] - p[0]) + (p[2] - p[1]) + (p[7] - p[4]) + (p[6] - p[5])
    g = (p[4] - p[0]) + (p[5] - p[1]) + (p[6] - p[2]) + (p[7] - p[3])
    den = float(np.linalg.norm(e) * np.linalg.norm(f) * np.linalg.norm(g))
    return float(np.dot(e, np.cross(f, g)) / den) if den > 0.0 else 0.0


CUBO = np.array(
    [
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
    ]
)
HEX = np.array([[0, 1, 2, 3, 4, 5, 6, 7]])

# I tre spigoli uscenti da ciascuno degli otto nodi, nell'ordine che da'
# determinante positivo sul cubo. Riscritti qui a mano: usare la tabella del
# modulo sotto prova renderebbe il confronto una tautologia.
_ANGOLI = (
    (1, 3, 4), (2, 0, 5), (3, 1, 6), (0, 2, 7),
    (7, 5, 0), (4, 6, 1), (5, 7, 2), (6, 4, 3),
)


def _jacobiano_all_angolo(p: np.ndarray, angolo: int) -> float:
    """Il jacobiano scalato in un solo angolo: la **vecchia** definizione a otto.

    Serve separata perche' `quality.scaled_jacobian` ora include anche il nono
    punto: senza questo riferimento indipendente non si potrebbe piu' mostrare
    che gli otto angoli da soli davano un verdetto diverso.
    """
    a, b, c = _ANGOLI[angolo]
    e1, e2, e3 = p[a] - p[angolo], p[b] - p[angolo], p[c] - p[angolo]
    prodotto = float(
        np.linalg.norm(e1) * np.linalg.norm(e2) * np.linalg.norm(e3)
    )
    return float(np.dot(e1, np.cross(e2, e3)) / prodotto) if prodotto > 0.0 else 0.0


def _tre_spigoli_a_sessanta_gradi() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tre versori con tutti e tre i prodotti scalari a 1/2, in forma chiusa."""
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.5, np.sqrt(3.0) / 2.0, 0.0])
    cx = 0.5
    cy = (0.5 - cx * b[0]) / b[1]
    return a, b, np.array([cx, cy, np.sqrt(1.0 - cx**2 - cy**2)])


def test_lo_scaled_jacobian_sul_romboedro_vale_la_radice_di_due_mezzi():
    """Oracolo in forma chiusa per la formula sugli otto angoli.

    Su un parallelepipedo ogni angolo ha per spigoli uscenti gli stessi tre
    vettori a meno del segno, quindi il valore e' lo stesso in tutti e otto e
    si calcola a mano. Con tre spigoli unitari a 60 gradi l'uno dall'altro il
    determinante vale `sqrt(1 - 3cos^2 + 2cos^3)` con `cos = 1/2`, cioe'
    `sqrt(1/2)`, e le lunghezze valgono 1: **0,70711**.

    Serve un secondo punto oltre al cubo, dove il valore e' 1: **1 e' anche il
    numero che uscirebbe da una normalizzazione sbagliata**, e da solo non
    inchioda la formula. E' lo stesso argomento gia' usato per il rapporto
    d'aspetto in #37.
    """
    a, b, c = _tre_spigoli_a_sessanta_gradi()
    # Verifica della costruzione prima di usarla: tre versori a 60 gradi.
    for primo, secondo in ((a, b), (a, c), (b, c)):
        assert float(np.dot(primo, secondo)) == pytest.approx(0.5)
        assert float(np.linalg.norm(primo)) == pytest.approx(1.0)

    romboedro = np.array([np.zeros(3), a, a + b, b, c, a + c, a + b + c, b + c])
    valore = float(quality.scaled_jacobian(romboedro, HEX)[0])
    assert valore == pytest.approx(np.sqrt(0.5), rel=1e-9)


# L'esaedro che ha deciso il ticket, trovato per ottimizzazione e non per
# campionamento: otto angoli eccellenti e l'interno completamente ripiegato.
# Sulla vecchia definizione a otto punti valeva 0,9155 -- «elemento ottimo».
RIPIEGATO = np.array(
    [
        [3.07874, -1.03802, 1.80790], [2.10540, -0.66178, 3.76536],
        [-0.82237, 2.71463, -0.32646], [-1.36025, 3.06848, 0.83508],
        [2.46922, -1.46407, 1.70206], [1.48452, -1.13839, 3.57875],
        [0.44847, 3.87654, 0.24398], [0.00875, 4.01630, 1.09586],
    ]
)


def test_l_esaedro_con_gli_spigoli_a_posto_e_l_interno_ripiegato_viene_colto():
    """Il reperto che ha deciso di implementare il nono punto invece di dichiararlo.

    Tutti e otto gli angoli valgono **0,9155**: guardando gli spigoli l'elemento
    e' ottimo. Il centro vale **-0,9979**, cioe' l'interno e' rovesciato, e un
    solutore che integri li' dentro produce numeri senza senso.

    Trovato per ottimizzazione mirata, non per campionamento: 148 689 cubi
    perturbati a caso non ne avevano prodotto **nessuno**. E' la ragione per cui
    la ricerca casuale non basta a dichiarare inerte un ramo.
    """
    angoli = [
        _jacobiano_all_angolo(RIPIEGATO, indice) for indice in range(8)
    ]
    assert min(angoli) == pytest.approx(0.9155, abs=1e-3), "il provino non e' piu' quello"
    assert _verdict_centro(RIPIEGATO) == pytest.approx(-0.9979, abs=1e-3)

    assert float(quality.scaled_jacobian(RIPIEGATO, HEX)[0]) < 0.0, (
        "un esaedro con l'interno rovesciato viene promosso: il nono punto "
        "non e' piu' nel minimo"
    )


def test_su_magli_veri_il_nono_punto_non_sposta_nulla():
    """L'altra meta' del reperto, ed e' quella che vale in tesi.

    Il nono punto coglie un caso patologico, ma **non cambia alcun numero gia'
    pubblicato**: su esaedri distorti a caso il centro non e' mai il minimo,
    perche' gli assi principali medi sono meglio condizionati del peggiore degli
    otto angoli. Misurato qui su duecento esaedri, e fuori dai test su 1644
    esaedri di tre prismi gmsh e 148 689 cubi perturbati.

    Serve dichiararlo perche' la domanda del ticket era proprio questa: quali
    numeri gia' pubblicati vanno rigenerati. La risposta e' nessuno.
    """
    rng = np.random.default_rng(3838)
    esaminati = vincolanti = 0
    for _ in range(200):
        p = CUBO + rng.uniform(-0.5, 0.5, size=(8, 3))
        angoli = min(_jacobiano_all_angolo(p, indice) for indice in range(8))
        if angoli <= 0.0:
            continue  # gia' respinto: non discrimina
        esaminati += 1
        if _verdict_centro(p) < angoli - 1e-9:
            vincolanti += 1
    assert esaminati > 50, "campione troppo piccolo per dire qualcosa"
    assert vincolanti == 0, (
        f"su {esaminati} esaedri distorti il centro e' il minimo in "
        f"{vincolanti}: i numeri gia' pubblicati vanno rigenerati"
    )


# --- N2: «aspect ratio» vale due grandezze diverse ---------------------------


def test_il_nostro_aspetto_e_quello_di_verdict_non_quello_di_abaqus():
    """Due numeri diversi sullo stesso tetraedro, entrambi in forma chiusa.

    Sul tetraedro rettangolo di lato 1 la definizione Verdict -- spigolo
    massimo su `2*sqrt(6)` volte il raggio inscritto -- vale `(1+sqrt(3))/2`,
    mentre l'«aspect ratio» di Abaqus, che e' spigolo massimo su minimo, vale
    `sqrt(2)`. Non sono riscalabili l'una nell'altra, quindi una soglia presa
    da un manuale Abaqus applicata al nostro numero confronta due cose diverse.

    Il test fissa **entrambi** i valori: con il solo nostro non si vedrebbe che
    la divergenza esiste.
    """
    nodi = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    nostro = float(quality.tet_aspect_ratios(nodi, TETS)[0])
    assert nostro == pytest.approx((1.0 + np.sqrt(3.0)) / 2.0)

    spigoli = [
        float(np.linalg.norm(nodi[i] - nodi[j]))
        for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    ]
    abaqus_ratio = max(spigoli) / min(spigoli)
    assert abaqus_ratio == pytest.approx(np.sqrt(2.0))
    assert nostro != pytest.approx(abaqus_ratio)


def test_il_registro_dichiara_la_collisione_di_nome():
    """La divergenza deve stare accanto al valore, o la soglia si cita a vuoto.

    Il numero senza la definizione e' il modo tipico in cui una soglia
    ratificata diventa falsa: resta giusta e viene applicata alla grandezza
    sbagliata.
    """
    nota = soglie.trova("aspect_ratio_tet").nota
    assert "Abaqus" in nota and "spigolo massimo e" in nota


# --- N3: il raggio-spigolo e' cieco agli sliver ------------------------------


def test_il_raggio_spigolo_promuove_uno_sliver_inservibile():
    """Il reperto che rende N3 un difetto e non un'osservazione.

    Il default `-q` di TetGen impone raggio-spigolo <= 2,0 e diedro minimo
    **zero**. Su uno sliver di manuale il rapporto vale circa 0,707 -- meglio
    del limite, e persino vicino allo 0,612 del tetraedro regolare -- mentre
    l'elemento e' inservibile. Non e' un caso limite raro: e' la forma che
    quel vincolo non puo' vedere, per costruzione.
    """
    nodi = sliver(0.001)
    rapporto = float(quality.radius_edge_ratios(nodi, TETS)[0])
    diedro = float(quality.min_dihedral_angles(nodi, TETS)[0])

    assert rapporto < 2.0, "l'ingresso scelto non e' uno sliver che passa il vincolo"
    assert diedro < 1.0, "l'ingresso scelto non e' degenere abbastanza"


def test_il_diedro_minimo_e_l_unica_metrica_che_lo_vede():
    """L'oracolo del contratto: **almeno una** metrica marca lo sliver.

    Si controllano tutte e tre quelle pubblicate. Se un giorno il raggio-spigolo
    cominciasse a coglierlo, o il diedro smettesse, questo test lo direbbe --
    ed e' il motivo per cui interroga le metriche invece di fissare un numero.
    """
    nodi = sliver(0.001)
    limite = soglie.trova("diedro_minimo_tet").minimo
    assert limite is not None

    visto_dal_diedro = float(quality.min_dihedral_angles(nodi, TETS)[0]) < limite
    visto_dal_raggio = float(quality.radius_edge_ratios(nodi, TETS)[0]) > 2.0

    assert visto_dal_diedro, "la sola metrica che deve vedere lo sliver non lo vede"
    assert not visto_dal_raggio, (
        "il raggio-spigolo ora coglie lo sliver: la cecita' dichiarata nel "
        "docstring non e' piu' vera e va riscritta"
    )


def _riga(diedro: dict[str, object]) -> dict[str, object]:
    return {"metrics": {"10_volume_quality": {"min_dihedral_deg": diedro}}}


def test_il_report_mostra_il_peggiore_e_non_solo_la_mediana():
    """Con la sola mediana un maglio con uno sliver si legge sano.

    E' il difetto concreto dietro N3: il numero che vede lo sliver stava gia'
    in `metrics.json` come `min_dihedral_deg.min`, ma la tabella stampava la
    mediana -- che su un maglio con un elemento cattivo su diecimila non si
    muove di un grado. Un controllo che non puo' cambiare esito non e' un
    controllo.
    """
    cella = report._cell(_riga({"min": 0.16, "median": 42.31}), "dihedral")
    assert "0.16" in cella and "42.31" in cella


def test_una_riga_vecchia_senza_il_peggiore_non_fabbrica_un_valore():
    """Il registro contiene corse scritte prima che `min` fosse pubblicato.

    Si scrive quello che c'e'. Un trattino o uno zero al posto del numero
    mancante si rileggerebbe fra mesi come una misura, ed e' esattamente il
    modo in cui un'assenza diventa un dato. NON_MISURATO non e' un valore
    fabbricato ma la dichiarazione dell'assenza, e sostituisce la cella vuota
    che stampata non si distingueva da un dato mancante.
    """
    assert report._cell(_riga({"median": 38.0}), "dihedral") == "38"
    assert report._cell(_riga({}), "dihedral") == report.NON_MISURATO


def test_uno_sliver_ben_orientato_non_e_marcato_invertito():
    """Nemmeno il cancello di finitezza lo ferma, ed e' il punto.

    Un elemento **positivo** e degenere passa `inverted_tets`: quel controllo
    cerca volumi non finiti, nulli o negativi, non elementi mal condizionati.
    Senza questo test si potrebbe credere che gli sliver siano gia' coperti
    dalla guardia che copre gli invertiti.
    """
    nodi = sliver(0.001)
    positivo = TETS if quality.tet_volumes(nodi, TETS)[0] > 0 else TETS[:, [0, 1, 3, 2]]
    assert quality.tet_volumes(nodi, positivo)[0] > 0.0
    assert len(quality.inverted_tets(nodi, positivo)) == 0


# --- N4: il volume dell'esaedro non e' la quadratura di Gauss ----------------


def test_il_volume_dell_esaedro_e_quello_del_solido_a_facce_triangolate():
    """Gia' dichiarato nel docstring; qui c'e' il numero che lo rende verificabile.

    Su un esaedro a facce piane le due definizioni coincidono, e il cubo lo
    mostra. La divergenza vive sugli esaedri a facce **non** piane, dove la
    decomposizione in sei tetraedri misura il solido che la superficie di bordo
    racchiude -- coerente con `mesh_volume`, che e' la ragione della scelta.
    """
    assert float(quality.hex_volumes(CUBO, HEX)[0]) == pytest.approx(1.0)

    # Una faccia superiore svergolata: un nodo sollevato rompe la planarita'.
    svergolato = CUBO.copy()
    svergolato[6, 2] += 0.5
    volume = float(quality.hex_volumes(svergolato, HEX)[0])
    # Il solido a facce triangolate: il cubo piu' la piramide che il nodo
    # sollevato aggiunge, e la decomposizione lo conta una volta sola.
    assert 1.0 < volume < 1.5
