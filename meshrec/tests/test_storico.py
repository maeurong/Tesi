"""Il deposito delle versioni di configurazione. Senza server e senza HTTP.

Su disco e non in memoria: una pila in memoria muore col processo, cioe'
proprio quando serve sapere che cosa si era cambiato.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshrec.app import storico
from meshrec.core import pipeline, steps


def test_indietro_rimette_il_testo_di_prima_byte_per_byte(tmp_path: Path):
    """L'undo ripristina davvero: non «una configurazione equivalente», la
    stessa. Un ripristino che riscrive il file passando da un modello lo
    normalizza — ordine delle chiavi, virgolette, campi predefiniti resi
    espliciti — e il confronto direbbe «uguale» su un file diverso."""
    storico.deposita(tmp_path, "prima: 1\n", "avvio", [])
    storico.deposita(tmp_path, "dopo: 2\n", "PUT /api/config", ["surface.poisson_depth"])
    assert storico.indietro(tmp_path) == "prima: 1\n"


def test_uno_storico_senza_niente_prima_risponde_none(tmp_path: Path):
    """Il difetto opposto — un silenzio identico fra riuscita e nulla-da-fare —
    e' gia' stato prodotto e corretto una volta su questo progetto, sul bottone
    Annulla (ui/index.html:21-26: «un bottone sempre acceso che risponde con un
    silenzio identico al successo non distingue annullato da non c'era nulla da
    annullare»). Qui l'assenza si distingue alla radice: None non e' una stringa
    vuota."""
    assert storico.indietro(tmp_path) is None
    storico.deposita(tmp_path, "sola: 1\n", "avvio", [])
    assert storico.indietro(tmp_path) is None


def test_avanti_torna_dove_si_era(tmp_path: Path):
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["b"])
    assert storico.indietro(tmp_path) == "due\n"
    assert storico.indietro(tmp_path) == "uno\n"
    assert storico.avanti(tmp_path) == "due\n"
    assert storico.avanti(tmp_path) == "tre\n"
    assert storico.avanti(tmp_path) is None


def test_una_scrittura_nuova_tronca_la_coda_oltre_il_cursore(tmp_path: Path):
    """Due futuri che convivono non sono uno storico, sono un albero, e nessun
    comando dell'interfaccia saprebbe quale ramo intende.

    Lo scenario ha tre versioni e non due di proposito: con una sola versione
    oltre il cursore la scrittura nuova ne riusa il numero e la coda sparisce
    da sola, quindi il controllo passerebbe anche senza troncatura. Con due
    oltre il cursore la seconda sopravvive, e «avanti» riporterebbe a un futuro
    che l'utente ha appena scartato.
    """
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["b"])
    storico.indietro(tmp_path)
    storico.indietro(tmp_path)
    storico.deposita(tmp_path, "altro\n", "POST /api/crop", ["segment.crop_min"])
    assert storico.avanti(tmp_path) is None, "la coda scartata e' ancora raggiungibile"
    assert storico.indietro(tmp_path) == "uno\n"

    # Dopo una troncatura il numero di versione ricompare nel registro: vale
    # l'ultima riga che lo porta, non la prima. Chi cercasse la provenienza
    # della versione 2 prendendo la prima riga che combacia mostrerebbe
    # «PUT /api/config» su un file scritto da «POST /api/crop».
    righe = [
        json.loads(riga)
        for riga in (tmp_path / ".storico" / "registro.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [riga["versione"] for riga in righe] == [1, 2, 3, 2]
    ultima_della_due = [riga for riga in righe if riga["versione"] == 2][-1]
    assert ultima_della_due["endpoint"] == "POST /api/crop"


def test_il_tetto_scarta_le_piu_vecchie_e_il_cursore_resta_coerente(tmp_path: Path):
    """Tetto misurato e non scelto: il config di lavoro pesa 1.328 byte, quindi
    duecento versioni costano 265,6 kB contro i circa 400 MB di artefatti che
    una corsa lascia."""
    for indice in range(storico.TETTO + 1):
        storico.deposita(tmp_path, f"versione: {indice}\n", "PUT /api/config", ["a"])
    rimaste = sorted((tmp_path / ".storico").glob("[0-9][0-9][0-9][0-9].yaml"))
    assert len(rimaste) == storico.TETTO
    assert rimaste[0].stem == "0002", "la prima versione doveva essere scartata"
    # Il cursore sta sull'ultima e «indietro» funziona ancora: un tetto che
    # lascia il cursore su un file cancellato romperebbe proprio il comando che
    # serve dopo una modifica di troppo.
    assert storico.indietro(tmp_path) == f"versione: {storico.TETTO - 1}\n"


def test_il_registro_tiene_una_riga_per_versione(tmp_path: Path):
    """Stessa forma in sola aggiunta del registro degli esperimenti della Fase
    2, per la stessa ragione: un file che si allunga non perde cio' che aveva.
    La provenienza e' parte del risultato, non un di piu'."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "POST /api/crop", ["segment.crop_min", "segment.crop_max"])
    righe = [
        json.loads(riga)
        for riga in (tmp_path / ".storico" / "registro.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [riga["versione"] for riga in righe] == [1, 2]
    assert righe[1]["endpoint"] == "POST /api/crop"
    assert righe[1]["campi"] == ["segment.crop_min", "segment.crop_max"]
    assert righe[1]["istante"].startswith("20")


def test_un_cursore_illeggibile_non_solleva(tmp_path: Path):
    """Uno stato illeggibile e' uno stato assente, come gia' fa
    core/steps.py:83-87 per lo stato della corsa. Sollevare qui vorrebbe dire che
    un file di servizio corrotto impedisce di annullare, cioe' proprio quando
    si sta cercando di rimediare a qualcosa."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    (tmp_path / ".storico" / "cursore.json").write_text("{non json", encoding="utf-8")
    assert storico.indietro(tmp_path) == "uno\n"


def test_un_cursore_fuori_intervallo_torna_dentro(tmp_path: Path):
    """Il cursore e' un file, e un file si puo' modificare a mano. Un numero
    fuori intervallo non e' innocuo: senza riportarlo dentro, la scrittura
    successiva prenderebbe il numero 10000, che ha cinque cifre e sta fuori
    dalla forma dei nomi che il deposito riconosce — la versione finirebbe su
    disco invisibile al deposito stesso."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    (tmp_path / ".storico" / "cursore.json").write_text(
        json.dumps({"versione": 9999}), encoding="utf-8"
    )
    assert storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["b"]) == 3
    assert storico.indietro(tmp_path) == "due\n"


def test_un_temporaneo_lasciato_da_una_scrittura_morta_non_uccide_il_deposito(tmp_path: Path):
    """Il residuo esiste per davvero e nessuno lo raccoglie: scrivi_atomico
    scrive «0003.tmp.yaml» e rinomina, quindi un processo ucciso a meta' lo
    lascia li'; core/io.py:150 usa glob e non rglob, e l'unico che chiama
    scarta_temporanei lo fa sulla cartella della corsa, non su .storico/.

    La grandezza sorvegliata e' il deposito intero e non l'elenco: con un glob
    largo quel nome arriva a int(), che solleva ValueError dentro _numeri, cioe'
    dentro la lettura da cui passano esiste, deposita, indietro e avanti. Un
    file che non e' una versione spegnerebbe l'undo, e lo spegnerebbe proprio
    dopo un'interruzione, quando serve.
    """
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    (tmp_path / ".storico" / "0003.tmp.yaml").write_text("meta' scrittura", encoding="utf-8")

    assert storico.esiste(tmp_path) is True
    assert storico.indietro(tmp_path) == "uno\n"
    assert storico.avanti(tmp_path) == "due\n"
    # E la scrittura successiva prende il numero della versione seguente, non
    # quello del residuo: il temporaneo non conta come versione nemmeno per la
    # numerazione.
    assert storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["b"]) == 3


def test_esiste_dice_se_c_e_gia_una_versione(tmp_path: Path):
    assert storico.esiste(tmp_path) is False
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    assert storico.esiste(tmp_path) is True


def test_la_diecimillesima_versione_non_fa_sparire_lo_storico(tmp_path: Path):
    """Il numero non ha un tetto, il numero di FILE si'.

    `deposita` fa `corrente + 1` e non rilegge mai il massimo; `TETTO` pota i
    file e non i numeri. Quindi una corsa longeva ci arriva da sola: la
    10000esima versione si scrive «10000.yaml», cinque cifre.

    Con l'elenco preso da un glob a quattro cifre quel file era invisibile al
    deposito stesso, e il guasto era muto in tutti e tre i modi peggiori: ogni
    scrittura successiva sovrascriveva lo stesso file, `esiste` continuava a
    dire di si', e «avanti» restituiva la 9999 -- cioe' uno stato PIU' VECCHIO
    di quello che config.yaml portava davvero, presentato come il rifare.

    Le due versioni si posano a mano invece di depositarne diecimila: la
    grandezza sorvegliata e' il passaggio da quattro a cinque cifre, non la
    fatica di arrivarci.

    Mutazione che lo uccide: rimettere `glob("[0-9][0-9][0-9][0-9].yaml")` al
    posto del filtro su `.isdigit()` in `_numeri`.
    """
    cartella = tmp_path / ".storico"
    cartella.mkdir(parents=True)
    (cartella / "9998.yaml").write_text("a: 9998\n", encoding="utf-8")
    (cartella / "9999.yaml").write_text("a: 9999\n", encoding="utf-8")
    (cartella / "cursore.json").write_text(json.dumps({"versione": 9999}), encoding="utf-8")

    assert storico.deposita(tmp_path, "a: 10000\n", "PUT /api/config", ["x"]) == 10000
    # La nuova e' una versione come le altre: la si vede, e il cursore ci sta
    # sopra. Senza il filtro giusto qui l'elenco tornava [9998, 9999].
    assert storico.indietro(tmp_path) == "a: 9999\n"
    assert storico.avanti(tmp_path) == "a: 10000\n"
    # E la scrittura dopo prosegue da 10000, non ricomincia da 9999+1.
    assert storico.deposita(tmp_path, "a: 10001\n", "PUT /api/config", ["y"]) == 10001


def test_un_temporaneo_a_cinque_cifre_resta_fuori_dalle_versioni(tmp_path: Path):
    """La controprova del test qui sopra: allargare il glob non doveva far
    entrare i temporanei, che sono la ragione per cui il glob era stretto.

    `scrivi_atomico` lascia «10000.tmp.yaml» se il processo muore a meta', e
    `"10000.tmp"` non e' `.isdigit()`. La guardia regge alla larghezza nuova.
    """
    cartella = tmp_path / ".storico"
    cartella.mkdir(parents=True)
    (cartella / "9999.yaml").write_text("a: 9999\n", encoding="utf-8")
    (cartella / "10000.tmp.yaml").write_text("meta' scrittura", encoding="utf-8")
    (cartella / "cursore.json").write_text(json.dumps({"versione": 9999}), encoding="utf-8")

    assert storico.esiste(tmp_path) is True
    assert storico.deposita(tmp_path, "a: 10000\n", "PUT /api/config", ["x"]) == 10000


def test_versione_corrente_legge_senza_spostare_il_cursore(tmp_path: Path):
    """La lettura che prima non c'era, e per cui il server entrava nei nomi
    privati di questo modulo.

    Sbirciare con la sola coppia indietro/avanti costava tre scritture del
    cursore per zero spostamenti voluti, e ogni scrittura in piu' e'
    un'occasione in piu' di lasciarlo disallineato.

    Mutazione che lo uccide: far chiamare `indietro` a `versione_corrente`.
    """
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])

    assert storico.versione_corrente(tmp_path) == "due\n"
    # Due volte di fila la stessa risposta: se spostasse, la seconda sarebbe
    # «uno\n».
    assert storico.versione_corrente(tmp_path) == "due\n"
    # E il cursore e' rimasto dov'era: «indietro» adesso da' la prima.
    assert storico.indietro(tmp_path) == "uno\n"


def test_versione_corrente_su_un_deposito_vuoto_e_none(tmp_path: Path):
    """Non c'e' niente da leggere, e non e' un guasto: e' la corsa aperta e mai
    modificata. `_cursore` torna 0 e «0000.yaml» non esiste."""
    assert storico.versione_corrente(tmp_path) is None


def test_la_coda_si_chiede_prima_di_depositare(tmp_path: Path):
    """C'e' qualcosa da rifare oltre il punto in cui siamo?

    La domanda ha senso solo PRIMA di una scrittura: dopo, la versione appena
    depositata e' essa stessa oltre il cursore di prima, e la risposta sarebbe
    sempre vera. E' l'unico modo che il server ha di sapere se un deposito ha
    fatto sparire delle versioni da rifare, cioe' se deve dirlo.

    Mutazione che lo uccide: `>=` al posto di `>` in `coda_oltre_il_cursore`.
    """
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    # Sul massimo non c'e' coda: siamo in fondo.
    assert storico.coda_oltre_il_cursore(tmp_path) is False

    storico.indietro(tmp_path)
    # Adesso «due» sta oltre il cursore, e un deposito la cancellerebbe.
    assert storico.coda_oltre_il_cursore(tmp_path) is True


def _scambio(da=2, a=2, sposta=("02_segmented.ply",), copia=("steps.json",)):
    return {"da": da, "a": a, "sposta": list(sposta), "copia": list(copia)}


def test_depositare_un_esecuzione_sposta_gli_artefatti_e_copia_lo_stato(tmp_path: Path):
    """Spostare e non copiare: un rename sullo stesso filesystem costa zero byte
    anche per un artefatto da cento megabyte. Lo stato invece si copia, perche'
    la ripresa lo rilegge per aggiungere la voce nuova: spostato via, gli step
    a monte risulterebbero «mai eseguito» a esecuzione finita."""
    (tmp_path / "02_segmented.ply").write_bytes(b"mesh")
    (tmp_path / "steps.json").write_text("{}", encoding="utf-8")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    cartella = tmp_path / storico.CARTELLA / f"{numero:04d}"
    assert not (tmp_path / "02_segmented.ply").exists(), "l'artefatto non e' stato spostato"
    assert (cartella / "02_segmented.ply").read_bytes() == b"mesh"
    assert (tmp_path / "steps.json").exists(), "lo stato doveva restare nella corsa"
    assert (cartella / "steps.json").read_text(encoding="utf-8") == "{}"
    dichiarato = json.loads((cartella / storico.SCAMBIO).read_text(encoding="utf-8"))
    assert dichiarato == {"da": 2, "a": 2, "file": ["02_segmented.ply", "steps.json"]}


def test_un_artefatto_assente_non_ferma_il_deposito(tmp_path: Path):
    """Uno step mai eseguito non ha artefatto: e' il caso normale della prima
    esecuzione, non un guasto."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    assert (tmp_path / storico.CARTELLA / f"{numero:04d}" / storico.SCAMBIO).exists()


def test_lo_scambio_e_la_propria_inversa(tmp_path: Path):
    """Indietro e avanti sono la stessa operazione: dopo due scambi ogni file e'
    dove stava. Tre casi in un colpo: presente da entrambe le parti, solo nella
    corsa, solo nella cartella."""
    (tmp_path / "02_segmented.ply").write_bytes(b"prima")
    (tmp_path / "steps.json").write_text("prima", encoding="utf-8")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(
        tmp_path, "uno\n", "POST /api/step/2", [],
        scambio=_scambio(sposta=("02_segmented.ply", "metrics.partial.json"), copia=("steps.json",)),
    )
    # L'esecuzione scrive la corsa nuova; il parziale esiste solo dopo.
    (tmp_path / "02_segmented.ply").write_bytes(b"dopo")
    (tmp_path / "steps.json").write_text("dopo", encoding="utf-8")
    (tmp_path / "metrics.partial.json").write_text("parziale", encoding="utf-8")

    assert storico.scambia(tmp_path, numero) == {"da": 2, "a": 2}
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"prima"
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "prima"
    assert not (tmp_path / "metrics.partial.json").exists()
    cartella = tmp_path / storico.CARTELLA / f"{numero:04d}"
    assert (cartella / "02_segmented.ply").read_bytes() == b"dopo"
    assert (cartella / "metrics.partial.json").read_text(encoding="utf-8") == "parziale"

    assert storico.scambia(tmp_path, numero) == {"da": 2, "a": 2}
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"dopo"
    assert (tmp_path / "steps.json").read_text(encoding="utf-8") == "dopo"
    assert (tmp_path / "metrics.partial.json").read_text(encoding="utf-8") == "parziale"
    assert not (cartella / "metrics.partial.json").exists()


def test_una_versione_di_configurazione_non_scambia_niente(tmp_path: Path):
    (tmp_path / "02_segmented.ply").write_bytes(b"resta")
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    numero = storico.deposita(tmp_path, "due\n", "PUT /api/config", ["a"])
    assert storico.scambia(tmp_path, numero) is None
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"resta"


def test_la_troncatura_e_il_tetto_cancellano_anche_le_cartelle(tmp_path: Path, monkeypatch):
    """Le cartelle oltre il cursore portano gli artefatti del futuro scartato:
    tenerle sarebbe disco occupato da cio' che nessun comando puo' piu'
    raggiungere. Il tetto pota le piu' vecchie con la stessa regola."""
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    (tmp_path / "02_segmented.ply").write_bytes(b"x")
    seconda = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    (tmp_path / "02_segmented.ply").write_bytes(b"y")
    terza = storico.deposita(tmp_path, "uno\n", "POST /api/step/2", [], scambio=_scambio())
    storico.indietro(tmp_path)
    storico.indietro(tmp_path)
    storico.deposita(tmp_path, "tre\n", "PUT /api/config", ["a"])
    assert not (tmp_path / storico.CARTELLA / f"{seconda:04d}").exists()
    assert not (tmp_path / storico.CARTELLA / f"{terza:04d}").exists()

    monkeypatch.setattr(storico, "TETTO", 2)
    (tmp_path / "02_segmented.ply").write_bytes(b"z")
    storico.deposita(tmp_path, "tre\n", "POST /api/step/2", [], scambio=_scambio())
    storico.deposita(tmp_path, "quattro\n", "PUT /api/config", ["b"])
    superstiti = sorted(p.name for p in (tmp_path / storico.CARTELLA).iterdir())
    assert not any(nome == "0001.yaml" for nome in superstiti)
    assert not any(nome.isdigit() and int(nome) < storico.cursore(tmp_path) - 1 for nome in superstiti)


def test_il_cursore_e_pubblico(tmp_path: Path):
    assert storico.cursore(tmp_path) == 0
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    assert storico.cursore(tmp_path) == 1


def test_l_elenco_del_solo_prior_non_porta_via_il_deck():
    """Lo step 12 non riscrive il deck dello step 11: portarlo via lo farebbe
    sparire dalla corsa mentre steps.json continua a dire «11_export riuscito»,
    cioe' proprio lo stato che lo scambio esiste per non produrre."""
    assert storico.elenco_di_scambio(12, 12)["sposta"] == [
        pipeline.WALL_FILENAME,
        pipeline.METRICS_PARTIAL,
    ]
    undici = storico.elenco_di_scambio(11, 11)["sposta"]
    assert pipeline.DECK_FILENAME in undici and pipeline.WALL_VTU_FILENAME in undici
    assert pipeline.WALL_FILENAME not in undici
    intera = storico.elenco_di_scambio(1, 12)
    assert intera["copia"] == [pipeline.METRICS_FILENAME, steps.STATE_FILENAME]
    assert intera["sposta"][0] == pipeline.ARTIFACTS[1]


def test_lo_scambio_si_dichiara_prima_di_muovere_i_file(tmp_path: Path, monkeypatch):
    """Una copia che fallisce a meta' non deve lasciare una cartella muta: senza
    scambio.json dentro, `scambia` la ignora e il deposito successivo la
    cancella con tutto cio' che aveva gia' spostato -- artefatti persi per
    sempre. Dichiarato prima, un deposito interrotto resta annullabile."""
    (tmp_path / "02_segmented.ply").write_bytes(b"mesh")
    (tmp_path / "steps.json").write_text("{}", encoding="utf-8")
    storico.deposita(tmp_path, "uno\n", "avvio", [])

    def esplode(*_argomenti, **_parole):
        raise OSError("disco pieno")

    monkeypatch.setattr(storico.shutil, "copy2", esplode)
    with pytest.raises(OSError):
        storico.deposita(tmp_path, "due\n", "POST /api/step/2", [], scambio=_scambio())

    numero = storico.cursore(tmp_path) + 1
    cartella = tmp_path / storico.CARTELLA / f"{numero:04d}"
    assert (cartella / storico.SCAMBIO).exists(), "la cartella senza dichiarazione e' irrecuperabile"
    assert storico.scambia(tmp_path, numero) == {"da": 2, "a": 2}
    assert (tmp_path / "02_segmented.ply").read_bytes() == b"mesh"
