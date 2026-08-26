"""Le soglie di verifica sono dati con una fonte, non numeri nel codice.

La decisione sta in https://github.com/maeurong/Tesi/issues/35. Il motivo non e'
di stile: la lacuna n. 3 misurata sui 17 articoli di `Articoli/` e' che le
soglie si dichiarano quasi sempre **dopo** aver visto il numero -- uno solo su
diciassette la fissa prima, con la fonte. Una soglia decisa dopo non e' un test,
e' una descrizione.

Tenerle come dato con `fonte`, `origine` e `fissata` accanto al valore fa due
cose che una costante nuda non fa: il capitolo di tesi si **genera** dalla
stessa origine che il codice usa, quindi testo e controllo non possono
divergere; e una soglia senza fonte non e' rappresentabile, quindi non si puo'
aggiungere di nascosto.

Buona parte di questi controlli nasce da un giro di review sulla prima stesura,
e ognuno di quelli porta accanto il difetto che ha trovato.
"""

import re
from datetime import date

import pytest

from meshrec.core.soglie import (
    RATIFICA,
    SOGLIE,
    Soglia,
    _numero,
    sotto_la_risoluzione,
    tabella_markdown,
    trova,
)


def _soglia(**campi) -> Soglia:
    """Una `Soglia` valida, da deformare campo per campo nei casi limite."""
    predefiniti = dict(
        nome="prova",
        minimo=None,
        massimo=1.0,
        unita="adim.",
        tipo="etichetta",
        origine="letta",
        fonte="Autore (2020), Rivista 1:1-2",
        fissata=date(2026, 8, 26),
        nota="",
    )
    return Soglia(**{**predefiniti, **campi})


# --- il registro ---------------------------------------------------------


def test_ogni_soglia_porta_una_fonte_e_una_data():
    """Mutazione che lo uccide: aggiungere una `Soglia` con `fonte=""`."""
    senza_fonte = [s.nome for s in SOGLIE if not s.fonte.strip()]
    assert not senza_fonte, f"soglie senza fonte: {senza_fonte}"

    senza_data = [s.nome for s in SOGLIE if not isinstance(s.fissata, date)]
    assert not senza_data, f"soglie senza data di fissazione: {senza_data}"


def test_ogni_soglia_delimita_qualcosa():
    """Una soglia con entrambi gli estremi a `None` non vincola nulla.

    E' la forma esatta di una guardia inerte: presente nel registro, verde nel
    conteggio, incapace di bocciare. Vedi
    https://github.com/maeurong/Tesi/issues/38.
    """
    vuote = [s.nome for s in SOGLIE if s.minimo is None and s.massimo is None]
    assert not vuote, f"soglie che non delimitano nulla: {vuote}"

    rovesciate = [
        s.nome
        for s in SOGLIE
        if s.minimo is not None and s.massimo is not None and s.minimo > s.massimo
    ]
    assert not rovesciate, f"soglie con minimo sopra il massimo: {rovesciate}"


def test_i_nomi_non_collidono():
    nomi = [s.nome for s in SOGLIE]
    assert len(nomi) == len(set(nomi)), "due soglie con lo stesso nome"


def test_ogni_soglia_nostra_dichiara_perche_e_nostra():
    """Il controllo che ha corretto il difetto piu' profondo della prima stesura.

    Quella scriveva «Benzley et al. 1995» accanto al fattore 2,0 come se il 2,0
    stesse in Benzley. Non ci sta: Benzley e' il riferimento contro cui l'errore
    si misura, il 2,0 e' nostro. Senza `origine`, la tabella stampata prometteva
    una fonte esterna per ogni numero e non la aveva -- che e' esattamente la
    pretesa che questo modulo esiste per rendere verificabile.

    Mutazione che lo uccide: marcare `origine="letta"` su `patch_test_relativo`
    senza spostarne il valore in una fonte che davvero lo pubblichi.
    """
    mute = [s.nome for s in SOGLIE if s.origine == "nostra" and not s.nota.strip()]
    assert not mute, f"soglie nostre senza una nota che dica perche': {mute}"


def test_ogni_origine_e_una_delle_tre_dichiarate():
    ammesse = {"letta", "derivata", "nostra"}
    fuori = {s.origine for s in SOGLIE} - ammesse
    assert not fuori, f"origini non dichiarate: {fuori}"


def test_ogni_tipo_e_uno_dei_tre_dichiarati():
    ammessi = {"cancello", "etichetta", "parametro"}
    fuori = {s.tipo for s in SOGLIE} - ammessi
    assert not fuori, f"tipi non dichiarati: {fuori}"


def test_esistono_tutte_e_tre_le_classi():
    """Se il registro perdesse una classe, la distinzione decisa in #35 sarebbe
    sparita senza che nulla diventasse rosso."""
    assert {s.tipo for s in SOGLIE} == {"cancello", "etichetta", "parametro"}


def test_le_fonti_non_sono_autoreferenziali():
    """Una soglia la cui fonte siamo noi non e' una soglia esterna.

    La prima stesura ancorava la regex con `^` e usava `.match()`, quindi
    catturava solo la fonte che *iniziava* col prefisso: «nostro
    core/quality.py» e «misurato in runs/lab_telaio_v2» passavano entrambe. Era
    una guardia tarata sul proprio esempio -- uccideva la mutazione nominata nel
    docstring e nient'altro.

    Mutazione che lo uccide: dare a una soglia `fonte="misurato in
    core/quality.py"`.
    """
    interna = re.compile(r"(core/|src/|meshrec|runs/|tests/)")
    autoreferenziali = [s.nome for s in SOGLIE if interna.search(s.fonte)]
    assert not autoreferenziali, (
        f"soglie giustificate da noi stessi invece che da una fonte esterna: {autoreferenziali}"
    )


def test_lo_scaled_jacobian_del_tet_arriva_a_radice_di_due_mezzi_non_a_uno():
    """La trappola di Verdict, con l'oracolo trascritto e non ricalcolato.

    Il range accettabile dello scaled Jacobian **tetraedrico** e'
    [0,5, sqrt(2)/2 ~ 0,7071], non [0,5, 1] come per l'esaedro. Chi copia il
    range dell'esaedro accetta come buono un tetraedro che Verdict rifiuta.

    Il valore atteso e' 0,7071 **letto da SAND2007-1751**, non `2**0.5 / 2`
    ricalcolato: la prima stesura ripeteva l'espressione del modulo, quindi
    uccideva `massimo=1.0` ma non una formula sbagliata.
    """
    s = trova("scaled_jacobian_tet")
    assert s.massimo == pytest.approx(0.7071, rel=1e-4), (
        f"il massimo del range Verdict per il tet e' 0,7071, non 1: trovato {s.massimo}"
    )
    assert s.minimo == pytest.approx(0.5)


def test_la_soglia_incrociata_e_quella_dell_autore_di_calculix():
    """Pin di valore piu' oracolo sulla provenienza.

    Il numero in se' non ha un oracolo indipendente qui: e' un fermo contro la
    modifica accidentale. Cio' che porta significato e' la seconda asserzione --
    che la fonte resti quella dell'autore del codice che stiamo verificando.
    Perderla vorrebbe dire perdere la sola soglia che non abbiamo scelto noi.
    """
    s = trova("incrociato_calculix_abaqus")
    assert s.massimo == pytest.approx(1e-3)
    assert "datcheck" in s.fonte
    assert s.origine == "letta"


def test_trova_dice_quale_nome_non_esiste():
    with pytest.raises(KeyError, match="inesistente"):
        trova("inesistente")


def test_soglia_e_immutabile():
    """La mutazione che uccide: trasformare `Soglia` in una dataclass mutabile.

    Non e' la `tuple` della stdlib a essere sotto esame ma la scelta di
    modellare la soglia come `NamedTuple`: un registro riscrivibile a runtime
    permetterebbe di allargare una soglia dopo aver visto il risultato, che e'
    il difetto che tutto questo modulo esiste per impedire.
    """
    with pytest.raises(AttributeError):
        SOGLIE[0].massimo = 999.0  # type: ignore[misc]
    assert isinstance(SOGLIE, tuple)


# --- il pavimento di risoluzione ----------------------------------------


def test_la_soglia_geometrica_non_scende_sotto_la_risoluzione_della_ricostruzione():
    """Principio 3 di PRODUCT.md: non fabbricare precisione che non esiste.

    Il voxel non ha un valore predefinito fisso -- `config.py:133` lo lascia a
    `None`, cioe' due volte la spaziatura media -- quindi il pavimento non e'
    una costante ma una **funzione della corsa**. La corsa di riferimento
    `runs/lab_telaio_v2` usa `voxel_size: 10.0`: sotto i 5 mm la ricostruzione
    non risolve, e una soglia piu' stretta dichiarerebbe una precisione che il
    dato non ha.

    Mutazione che lo uccide: portare la soglia geometrica a 2,0 mm.
    """
    s = trova("errore_geometrico_max")
    assert not sotto_la_risoluzione(s.massimo, voxel_mm=10.0), (
        f"soglia geometrica {s.massimo} mm sotto meta' del voxel della corsa di riferimento"
    )
    # E il controllo morde: una soglia piu' fine dello stesso voxel e' rifiutata.
    assert sotto_la_risoluzione(2.0, voxel_mm=10.0)


def test_esattamente_meta_voxel_e_il_pavimento_non_e_sotto_di_esso():
    """Il bordo, nominato invece che coperto di riflesso.

    `errore_geometrico_max` vale 5,0 con voxel 10,0, cioe' sta **sul** bordo:
    un `<` che diventasse `<=` renderebbe rossa la geometrica senza che nessun
    test dica perche'. Questo lo dice.
    """
    assert not sotto_la_risoluzione(5.0, voxel_mm=10.0)
    assert sotto_la_risoluzione(4.999, voxel_mm=10.0)


def test_sotto_la_risoluzione_su_ingressi_degeneri():
    """Voxel non calcolabile, o soglia che non e' un numero confrontabile."""
    with pytest.raises(ValueError):
        sotto_la_risoluzione(5.0, voxel_mm=0.0)
    with pytest.raises(ValueError):
        sotto_la_risoluzione(5.0, voxel_mm=-1.0)
    with pytest.raises(ValueError):
        sotto_la_risoluzione(5.0, voxel_mm=float("nan"))
    with pytest.raises(ValueError):
        sotto_la_risoluzione(float("nan"), voxel_mm=10.0)


def test_una_soglia_senza_estremo_superiore_e_rifiutata_non_solleva_typeerror():
    """`Soglia.massimo` e' opzionale, e il chiamante naturale gliela passa.

    Un `TypeError` da `math.isfinite` direbbe al chiamante che ha sbagliato
    tipo, non che ha passato una soglia priva dell'estremo che serve.
    """
    with pytest.raises(ValueError, match="estremo superiore"):
        sotto_la_risoluzione(None, voxel_mm=10.0)


# --- la tabella che finisce in tesi -------------------------------------


def test_la_tabella_riporta_ogni_soglia_con_il_proprio_riferimento():
    """Mutazione che lo uccide: generare la tabella saltando la colonna del riferimento."""
    testo = tabella_markdown()
    righe = [r for r in testo.splitlines() if r.startswith("|")]
    # intestazione + separatore + una riga per soglia
    assert len(righe) == len(SOGLIE) + 2, (
        f"{len(righe)} righe per {len(SOGLIE)} soglie: la tabella perde o duplica"
    )
    for s in SOGLIE:
        assert s.nome in testo, f"{s.nome} assente dalla tabella"
        assert s.fonte.split(",")[0] in testo, f"riferimento di {s.nome} assente dalla tabella"


def test_ogni_riga_della_tabella_ha_lo_stesso_numero_di_colonne():
    """Il difetto trovato in review: una barra verticale in un campo spaccava la riga.

    Il controllo precedente contava le **righe** e restava verde, perche' la
    riga guasta resta una riga. E la fonte e' testo bibliografico arbitrario:
    nulla vieta che un giorno ne contenga una.

    Mutazione che lo uccide: togliere l'escape in `_senza_barre`.
    """
    con_barra = _soglia(nome="barra", fonte="Rossi | Bianchi (2020), Tab. 1")
    righe = [r for r in tabella_markdown((con_barra,)).splitlines() if r.startswith("|")]
    # Si spezza sulle sole barre **non** protette: `\|` e' una barra dentro la
    # cella, non un separatore, ed e' proprio quello che l'escape produce.
    # Contarla come separatore era l'errore della prima stesura di questo test.
    colonne = {len(re.split(r"(?<!\\)\|", r)) for r in righe}
    assert len(colonne) == 1, f"righe con numero di colonne diverso: {colonne}"
    assert "\\|" in "\n".join(righe), "la barra nella fonte non e' stata protetta"


def test_la_tabella_su_registro_vuoto_resta_una_tabella():
    """Ingresso degenere: nessuna soglia -> intestazione e separatore, non uno schianto."""
    testo = tabella_markdown(())
    righe = [r for r in testo.splitlines() if r.startswith("|")]
    assert len(righe) == 2
    assert "Note." not in testo, "un registro vuoto non ha note da elencare"


def test_la_tabella_porta_legenda_e_note():
    """Senza queste due, la tabella stampata non e' difendibile in discussione.

    Un lettore dell'appendice non puo' sapere che un'etichetta fuori range non
    ferma nulla, ne' perche' il massimo dello scaled Jacobian sia sqrt(2)/2 e
    non 1. La legenda e le note portano l'unica cosa che rende la tabella
    leggibile da sola.
    """
    testo = tabella_markdown()
    for parola in ("cancello", "etichetta", "parametro", "letta", "derivata", "nostra"):
        assert parola in testo, f"la legenda non spiega «{parola}»"
    assert "**Note.**" in testo
    for s in SOGLIE:
        if s.nota:
            assert s.nota in testo, f"la nota di {s.nome} non raggiunge la pagina"
    assert f"{RATIFICA:%d/%m/%Y}" in testo, "la data di ratifica non compare"


def test_una_soglia_senza_estremi_non_finge_di_delimitare():
    """Il ramo che la prima stesura dichiarava irraggiungibile, e non lo era.

    Il registro suo proprio non puo' contenerla, ma `tabella_markdown` e'
    pubblica e accetta una tupla arbitraria: il ramo si raggiunge da li'. Il
    commento che lo giustificava nominava la funzione sbagliata.
    """
    senza = _soglia(nome="vuota", minimo=None, massimo=None)
    testo = tabella_markdown((senza,))
    assert "nessun limite" in testo


# --- i numeri come li vuole un'appendice italiana -----------------------


@pytest.mark.parametrize(
    ("valore", "atteso"),
    [
        (1e-8, "10⁻⁸"),
        (1e-6, "10⁻⁶"),
        (1e-3, "10⁻³"),
        (-5.38, "-5,38"),
        (70.5288, "70,5288"),
        (1.25, "1,25"),
        (5.0, "5"),
        (44.092, "44,092"),
    ],
)
def test_i_numeri_escono_in_una_sola_grafia(valore, atteso):
    """Il rilievo di review: `:g` rendeva `1e-08`, `1e-06` e `0.001`.

    Tre grafie per tre tolleranze sorelle, e il punto decimale mentre la prosa
    intorno scrive `70,5288` e `45,897`. La tabella generata litigava con il
    testo che le sta accanto -- che e' il divergere che questo modulo esiste
    per impedire.
    """
    assert _numero(valore) == atteso


def test_il_bound_in_forma_chiusa_resta_simbolico():
    """Sei decimali di sqrt(2)/2 asserirebbero una precisione che il bound non ha."""
    testo = _numero(2**0.5 / 2)
    assert "sqrt(2)/2" in testo
    assert "0,707107" not in testo
