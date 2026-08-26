"""Da regola geometrica a indici di nodo, e gli oracoli che la contraddicono."""

import numpy as np
import pytest

from meshrec.core import config, selezione


def _banco():
    """Otto nodi ai vertici di un cubo di lato 10 mm, due tetraedri.

    Esplicito e non tetraedrizzato: qui si prova il criterio di selezione,
    e un banco di cui si conoscono a memoria gli otto indici rende
    leggibile ogni assert. La mesh vera arriva nei test di
    `tests/test_abaqus.py`, dove la superficie conta.
    """
    nodi = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [10.0, 10.0, 0.0],
         [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [0.0, 10.0, 10.0], [10.0, 10.0, 10.0]]
    )
    elementi = np.array([[0, 1, 2, 4], [3, 5, 6, 7]], dtype=np.int64)
    node_sets = {"BASE": np.array([0, 1, 2, 3]), "TOP": np.array([4, 5, 6, 7])}
    return nodi, elementi, node_sets


def test_la_box_prende_i_nodi_dentro_e_solo_quelli():
    """Il criterio e' inclusivo sugli estremi e non prende nulla oltre.

    Gli estremi della box cadono **esattamente** su coordinate di nodo, su
    entrambi i lati: minimo (0, 0, 0) sul vertice 0, massimo (10, 10, 5)
    sulle coordinate alte di x e di y. Senza questo il test non prova
    nulla -- la versione precedente usava una box piu' larga del cubo, dove
    nessun nodo tocca l'estremo e la mutazione dichiarata lasciava 11
    passed.

    Mutazioni che lo uccidono: `<` al posto di `<=` sul massimo (escono i
    nodi a x = 10 e y = 10, resta il solo nodo 0) e `>` al posto di `>=`
    sul minimo (esce ogni nodo che tocca un estremo basso, la lista si
    svuota).
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(0.0, 0.0, 0.0), max=(10.0, 10.0, 5.0))
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="basso", spigolo=10.0)
    assert presi.tolist() == [0, 1, 2, 3]


def test_la_sfera_prende_per_distanza_dal_centro():
    """Dentro e' distanza <= raggio, non < raggio.

    Mutazione che lo uccide: confronto stretto. I nodi a distanza
    esattamente 10 dal centro escono e la lista si accorcia a uno.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=10.0)
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="angolo", spigolo=10.0)
    assert presi.tolist() == [0, 1, 2, 4]


def test_il_selettore_nodo_prende_il_piu_vicino():
    """Un nodo solo, quello di distanza minima.

    Mutazione che lo uccide: `argmax` al posto di `argmin`.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNodo(tipo="nodo", punto=(9.5, 9.5, 9.5))
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="punta", spigolo=10.0)
    assert presi.tolist() == [7]


def test_il_selettore_nset_rende_l_insieme_esistente():
    """Il nome cita un *NSET gia' costruito e ne rende gli indici.

    Mutazione che lo uccide: rendere tutti i nodi invece dell'insieme citato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNset(tipo="nset", nome="BASE")
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="appoggio", spigolo=10.0)
    assert presi.tolist() == [0, 1, 2, 3]


def test_un_nset_inesistente_solleva_e_nomina_quelli_che_ci_sono():
    """Il nome sbagliato si scopre alla risoluzione, e l'errore dice le alternative.

    Mutazione che lo uccide: `node_sets.get(nome, np.array([]))`, che
    renderebbe zero nodi e confonderebbe il sintomo con altri quattro.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNset(tipo="nset", nome="LATO")
    with pytest.raises(ValueError, match="BASE"):
        selezione.risolvi(selettore, nodi, node_sets, nome="appoggio", spigolo=10.0)


def test_zero_nodi_solleva_e_riporta_l_estensione_della_mesh():
    """Il sintomo comune a cinque ingressi degeneri ha un oracolo esplicito.

    Mutazione che lo uccide: rendere l'array vuoto invece di sollevare.
    Il carico finirebbe applicato a nulla e il deck uscirebbe valido.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(100.0, 100.0, 100.0), max=(200.0, 200.0, 200.0))
    with pytest.raises(ValueError, match="zero nodi"):
        selezione.risolvi(selettore, nodi, node_sets, nome="lontana", spigolo=10.0)


def test_tutti_i_nodi_solleva():
    """Un selettore che prende tutto non e' un posizionato, e' un peso proprio storto.

    Mutazione che lo uccide: togliere il controllo. La risultante si
    spalma sull'intero solido e il caso di carico perde significato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreBox(tipo="box", min=(-1.0, -1.0, -1.0), max=(11.0, 11.0, 11.0))
    with pytest.raises(ValueError, match="tutti"):
        selezione.risolvi(selettore, nodi, node_sets, nome="tutto", spigolo=10.0)


def test_il_nodo_troppo_lontano_solleva_oltre_tre_spigoli():
    """`argmin` un vincitore ce l'ha sempre: l'oracolo e' la distanza, non il conteggio.

    Mutazione che lo uccide: alzare SPIGOLI_DI_TOLLERANZA a 300. Il punto
    a 1000 mm da una mesh di spigolo 10 entra, e il carico finisce su un
    nodo che l'operatore non ha indicato.
    """
    nodi, _, node_sets = _banco()
    selettore = config.SelettoreNodo(tipo="nodo", punto=(1000.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="spigol"):
        selezione.risolvi(selettore, nodi, node_sets, nome="persa", spigolo=10.0)


def test_lo_spigolo_medio_si_misura_sugli_spigoli_degli_elementi():
    """Un tetraedro regolare di lato 10 ha spigolo medio 10.

    Mutazione che lo uccide: misurare sulle distanze fra tutti i nodi
    della mesh invece che sugli spigoli degli elementi. Su un banco con
    due tetraedri lontani fra loro la media esplode.
    """
    nodi = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [5.0, 8.66, 0.0], [5.0, 2.89, 8.16]])
    elementi = np.array([[0, 1, 2, 3]], dtype=np.int64)
    assert selezione.spigolo_medio(nodi, elementi) == pytest.approx(10.0, abs=0.05)


def test_gli_indici_resi_sono_ordinati_senza_ripetizioni_e_int64():
    """Ordine, unicita' e dtype non sono un dettaglio di implementazione, sono l'oracolo.

    Mutazione che lo uccide: togliere `np.unique`. Un *NSET dichiarato con
    indici ripetuti e fuori ordine (capita quando lo si scrive a mano)
    passerebbe cosi' com'e' invece di uscire pulito.
    """
    nodi, _, _ = _banco()
    node_sets = {"SPARSO": np.array([3, 1, 3, 0])}
    selettore = config.SelettoreNset(tipo="nset", nome="SPARSO")
    presi = selezione.risolvi(selettore, nodi, node_sets, nome="sparso", spigolo=10.0)
    assert presi.tolist() == [0, 1, 3]
    assert presi.dtype == np.int64


def test_risolvi_tutti_senza_selettori_rende_un_dizionario_vuoto():
    """Ingresso degenere del caso normale: chi non dichiara nulla non paga nulla.

    Mutazione che lo uccide: togliere il ritorno anticipato. `spigolo_medio`
    verrebbe calcolato su una mesh che nessuno usera', e su un array di
    elementi vuoto solleverebbe.
    """
    nodi, elementi, node_sets = _banco()
    assert selezione.risolvi_tutti({}, nodi, elementi, node_sets) == {}


# Un nodo con una coordinata non finita rendeva inerti, in due modi
# **indipendenti**, la guardia «questo non e' un indirizzo» (#50). I test qui
# sotto tengono i due modi separati, perche' separatamente si presentano:
# chiuderne uno solo lascerebbe l'altro aperto e la suite verde.
_NODI_CON_UN_NAN = np.array([[0.0, 0.0, 0.0], [1000.0, 0.0, 0.0], [float("nan"), 0.0, 0.0]])


def test_il_selettore_a_nodo_non_sceglie_mai_il_nodo_non_finito():
    """Primo modo: `np.argmin` su distanze con `nan` rende l'indice del `nan`.

    Reperto misurato prima della correzione: su questi nodi, col punto a
    (5000, 0, 0) e spigolo 10, la funzione rendeva **`[2]`** -- il nodo
    rotto -- mentre il vicino vero sta a 4000 mm, cioe' **oltre** i 30 mm di
    tolleranza. Due asserzioni, e servono entrambe: la prima dice che il
    `nan` non vince, la seconda che il rifiuto e' quello giusto, col numero
    vero (4000) e non con un `nan` stampato nel messaggio.
    """
    selettore = config.SelettoreNodo(tipo="nodo", punto=(5000.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="4000.0 mm") as errore:
        selezione.risolvi(selettore, _NODI_CON_UN_NAN, {}, nome="carico", spigolo=10.0)
    assert "nan" not in str(errore.value)


def test_col_nodo_non_finito_presente_vince_comunque_il_finito_piu_vicino():
    """Controprova del test sopra, e la meta' che lo rende non vacuo: un
    controllo che sollevasse **sempre** in presenza di un `nan` lo
    supererebbe senza distinguere nulla. Qui il vicino finito e' dentro
    tolleranza e deve vincere -- l'indice 1, non il 2.
    """
    selettore = config.SelettoreNodo(tipo="nodo", punto=(1005.0, 0.0, 0.0))

    presi = selezione.risolvi(selettore, _NODI_CON_UN_NAN, {}, nome="carico", spigolo=10.0)

    assert presi.tolist() == [1]


def test_senza_alcun_nodo_finito_il_selettore_lo_dice_con_parole_sue():
    """Caso limite del ramo nuovo: escludendo i non finiti non resta nulla su
    cui fare `argmin`. Messaggio distinto da «troppo lontano», perche' e' una
    condizione diversa: li' un vicino c'era ed era sbagliato, qui non c'e'.
    """
    rotti = np.array([[float("nan"), 0.0, 0.0], [float("nan"), 1.0, 0.0]])
    selettore = config.SelettoreNodo(tipo="nodo", punto=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="coordinate finite"):
        selezione.risolvi(selettore, rotti, {}, nome="carico", spigolo=10.0)


def test_uno_spigolo_non_finito_non_spegne_il_controllo_sulla_distanza():
    """Secondo modo, **indipendente dal primo**: i nodi sono tutti sani, ma
    `spigolo` e' `nan` e allora `limite` e' `nan`, e `distanza > nan` e'
    falso per qualunque distanza. Misurato: rendeva il nodo a 3000 mm.

    Nodi sani apposta -- se il test usasse quelli col `nan` non
    distinguerebbe questo modo dall'altro, e chiudere uno solo dei due lo
    lascerebbe passare.
    """
    sani = np.array([[0.0, 0.0, 0.0], [1000.0, 0.0, 0.0], [2000.0, 0.0, 0.0]])
    selettore = config.SelettoreNodo(tipo="nodo", punto=(5000.0, 0.0, 0.0))
    for spigolo in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="tolleranza non finita"):
            selezione.risolvi(selettore, sani, {}, nome="carico", spigolo=spigolo)


def test_lo_spigolo_medio_non_propaga_un_nan_come_se_fosse_una_lunghezza():
    """`lunghezze.mean()` rende `nan` con un solo nodo non finito, e quel
    valore e' la **tolleranza** con cui i selettori decidono. Propagarlo non
    sbaglia il confronto a valle: lo spegne.
    """
    elementi = np.array([[0, 1, 2, 2]], dtype=np.int64)
    with pytest.raises(ValueError, match="spigolo medio"):
        selezione.spigolo_medio(_NODI_CON_UN_NAN, elementi)


def test_box_e_sfera_gia_escludevano_il_nodo_non_finito():
    """Il **perche'** non serve una guardia unica all'ingresso di questo
    modulo, misurato invece che assunto: `box` e `sfera` confrontano con
    `>=`/`<=`, che sono falsi su `nan`, quindi il nodo rotto resta fuori da
    solo. Solo `nodo` falliva aperto, perche' `argmin` un vincitore lo
    nomina comunque.

    Se un domani uno dei due cambiasse forma e cominciasse a includerlo,
    questo test cadrebbe e direbbe che la decisione va rifatta.
    """
    tutto = config.SelettoreBox(tipo="box", min=(-1e9, -1e9, -1e9), max=(1e9, 1e9, 1e9))
    sfera = config.SelettoreSfera(tipo="sfera", centro=(0.0, 0.0, 0.0), raggio=1e9)

    presi_box = selezione.risolvi(tutto, _NODI_CON_UN_NAN, {}, nome="b", spigolo=10.0)
    presi_sfera = selezione.risolvi(sfera, _NODI_CON_UN_NAN, {}, nome="s", spigolo=10.0)

    assert presi_box.tolist() == [0, 1]
    assert presi_sfera.tolist() == [0, 1]
