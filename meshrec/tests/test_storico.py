"""Il deposito delle versioni di configurazione. Senza server e senza HTTP.

Su disco e non in memoria: una pila in memoria muore col processo, cioe'
proprio quando serve sapere che cosa si era cambiato.
"""

from __future__ import annotations

import json
from pathlib import Path

from meshrec.app import storico


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


def test_esiste_dice_se_c_e_gia_una_versione(tmp_path: Path):
    assert storico.esiste(tmp_path) is False
    storico.deposita(tmp_path, "uno\n", "avvio", [])
    assert storico.esiste(tmp_path) is True
