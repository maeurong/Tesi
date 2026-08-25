"""Storico delle modifiche di configurazione fatte dall'interfaccia.

Su disco e non in memoria: una pila in memoria muore col processo, cioe'
proprio quando serve sapere che cosa si era cambiato. Il deposito sta dentro
la cartella della corsa, accanto agli artefatti che quelle modifiche hanno
prodotto, cosi' la provenienza viaggia con il risultato.

Il deposito tiene ogni stato, compreso quello corrente: la versione 1 e' il
config prima della prima modifica, ogni scrittura ne aggiunge una e sposta il
cursore in avanti. «Indietro» arretra il cursore e restituisce il testo su cui
e' arrivato; sulla prima versione non c'e' niente prima, e risponde None.

Non sa niente di HTTP e non importa FastAPI: chi lo usa e' app/server.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from meshrec.core import io, sweep

# Quante versioni si tengono. Misurato e non scelto: il config di lavoro
# (meshrec/prova-interfaccia.yaml) pesa 1.328 byte, quindi duecento versioni
# costano 265,6 kB, contro i circa 400 MB di artefatti che una corsa lascia.
# Il tetto vale per le versioni e non per registro.jsonl, che sta fuori di
# proposito e non viene mai potato: circa 92 byte per modifica, per sempre,
# perche' la provenienza di una versione scartata resta comunque un fatto.
TETTO = 200

CARTELLA = ".storico"


def _cartella(out_dir: Path) -> Path:
    return Path(out_dir) / CARTELLA


def _percorso(out_dir: Path, numero: int) -> Path:
    return _cartella(out_dir) / f"{numero:04d}.yaml"


def _numeri(out_dir: Path) -> list[int]:
    """I numeri delle versioni presenti, in ordine.

    Si filtra su `.isdigit()` e non con un glob a quattro cifre perche'
    scrivi_atomico lascia un temporaneo "0003.tmp.yaml" quando il processo muore
    a meta' scrittura, e nessuno lo raccoglie: scarta_temporanei non ricorre
    nelle sottocartelle (core/io.py:151 usa glob e non rglob) e l'unico che lo
    chiama e' pipeline sulla cartella della corsa. Con "*.yaml" nudo quel
    residuo farebbe sollevare int() a ogni chiamata, cioe' il deposito
    smetterebbe di funzionare per un file che non e' una versione. `"0003.tmp"`
    non e' `isdigit()`, quindi la guardia regge.

    "[0-9][0-9][0-9][0-9].yaml" reggeva anche lui, ma solo fino a 9999. I numeri
    sono monotoni -- `deposita` fa `corrente + 1` e il TETTO pota i FILE, non i
    numeri -- quindi la 10000esima versione si scrive come "10000.yaml", cinque
    cifre, e il glob a quattro non la vede piu'. Da li' in poi lo storico si
    congelava in silenzio: ogni scrittura sovrascriveva lo stesso file
    invisibile, e «avanti» restituiva la 9999, cioe' uno stato PIU' VECCHIO di
    quello che config.yaml portava davvero.
    """
    cartella = _cartella(out_dir)
    if not cartella.is_dir():
        return []
    return sorted(
        int(percorso.stem)
        for percorso in cartella.glob("*.yaml")
        if percorso.stem.isdigit()
    )


def _cursore(out_dir: Path) -> int:
    """Dove siamo adesso. Zero quando non c'e' ancora nessuna versione."""
    numeri = _numeri(out_dir)
    if not numeri:
        return 0
    try:
        salvato = int(
            json.loads(
                (_cartella(out_dir) / "cursore.json").read_text(encoding="utf-8")
            )["versione"]
        )
    except (OSError, ValueError, KeyError, TypeError):
        # Uno stato illeggibile e' uno stato assente, come core/steps.py:83-87
        # per lo stato della corsa, ma con una differenza da dichiarare: li' il
        # ripiego e' pessimista, qui e' ottimista e muto. Si riparte
        # dall'ultima versione, che e' quella che config.yaml porta, e chi
        # aveva gia' annullato due volte si ritrova sulla punta senza che
        # nessuno glielo dica: il prossimo «indietro» gli restituisce una
        # configurazione che aveva appena rifiutato. Dirglielo richiede un
        # canale verso l'interfaccia, che qui non c'e'.
        return numeri[-1]
    # Il cursore e' un file, e un file si puo' modificare a mano: e' la causa
    # che resta di un numero fuori intervallo, perche' deposita lascia sempre il
    # cursore sul massimo e il tetto toglie solo le piu' vecchie.
    #
    # Qui c'era scritto che fosse l'UNICA, e non lo era: `deposita` fa
    # `corrente + 1` senza mai rileggere il massimo, quindi ci arrivava da sola
    # oltre la 9999. Adesso `_numeri` riconosce i nomi per `.isdigit()` e non
    # per un glob a quattro cifre, quindi un numero a cinque cifre e' una
    # versione come le altre e quella strada non esiste piu'. Il clamp resta
    # per il file scritto a mano, che nessuno puo' impedire.
    return min(max(salvato, numeri[0]), numeri[-1])


def _scrivi_cursore(out_dir: Path, numero: int) -> None:
    io.scrivi_atomico(
        _cartella(out_dir) / "cursore.json",
        lambda destinazione: destinazione.write_text(
            json.dumps({"versione": numero}), encoding="utf-8"
        ),
    )


def esiste(out_dir: Path) -> bool:
    """C'e' gia' almeno una versione depositata."""
    return bool(_numeri(out_dir))


def versione_corrente(out_dir: Path) -> str | None:
    """Il testo della versione su cui il cursore sta adesso, senza spostarlo.

    Una LETTURA, che la sola coppia indietro/avanti non sapeva fare: sbirciare
    con quelle costava indietro -> avanti -> indietro, tre scritture del cursore
    al posto di zero, e ogni scrittura in piu' e' un'occasione in piu' di
    lasciarlo disallineato.
    """
    percorso = _percorso(out_dir, _cursore(out_dir))
    return percorso.read_text(encoding="utf-8") if percorso.exists() else None


def coda_oltre_il_cursore(out_dir: Path) -> bool:
    """C'e' almeno una versione da rifare oltre quella su cui siamo.

    Va chiesta PRIMA di depositare: dopo, la versione appena scritta e' essa
    stessa oltre il cursore di prima e la risposta e' sempre vera.
    """
    cursore = _cursore(out_dir)
    return any(numero > cursore for numero in _numeri(out_dir))


def _applica_tetto(out_dir: Path) -> None:
    numeri = _numeri(out_dir)
    if len(numeri) <= TETTO:
        return
    for numero in numeri[: len(numeri) - TETTO]:
        _percorso(out_dir, numero).unlink()


def deposita(out_dir: Path, testo: str, endpoint: str, campi: list[str]) -> int:
    """Aggiunge `testo` in coda come versione nuova e torna il suo numero.

    Una scrittura nuova tronca la coda oltre il cursore: due futuri che
    convivono non sono uno storico, sono un albero, e nessun comando
    dell'interfaccia saprebbe quale ramo intende.
    """
    cartella = _cartella(out_dir)
    corrente = _cursore(out_dir)
    for numero in _numeri(out_dir):
        if numero > corrente:
            _percorso(out_dir, numero).unlink()

    nuovo = corrente + 1
    io.scrivi_atomico(
        _percorso(out_dir, nuovo),
        lambda destinazione: destinazione.write_text(testo, encoding="utf-8"),
    )
    # Lo stesso append_row del registro degli esperimenti della Fase 2, non una
    # seconda forma che gli somiglia: in sola aggiunta, un file che si allunga
    # non perde cio' che aveva. L'istante e' UTC perche' un registro che cambia
    # significato col fuso orario di chi lo legge non e' una provenienza.
    #
    # Dopo una troncatura un numero di versione ricompare: la sequenza 1, 2, 3,
    # 2 e' regolare e vuol dire che la 3 non esiste piu' e che la 2 e' stata
    # riscritta. Vale l'ultima riga che porta quel numero; chi legge la prima
    # attribuisce a un file l'endpoint che l'ha scritto la volta prima.
    sweep.append_row(
        cartella / "registro.jsonl",
        {
            "versione": nuovo,
            "istante": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "endpoint": endpoint,
            "campi": campi,
        },
    )

    _scrivi_cursore(out_dir, nuovo)
    _applica_tetto(out_dir)
    return nuovo


def indietro(out_dir: Path) -> str | None:
    """Il testo della versione precedente, o None se non c'e' niente prima."""
    corrente = _cursore(out_dir)
    precedenti = [numero for numero in _numeri(out_dir) if numero < corrente]
    if not precedenti:
        return None
    _scrivi_cursore(out_dir, precedenti[-1])
    return _percorso(out_dir, precedenti[-1]).read_text(encoding="utf-8")


def avanti(out_dir: Path) -> str | None:
    """Il testo della versione successiva, o None se siamo gia' in coda."""
    corrente = _cursore(out_dir)
    successivi = [numero for numero in _numeri(out_dir) if numero > corrente]
    if not successivi:
        return None
    _scrivi_cursore(out_dir, successivi[0])
    return _percorso(out_dir, successivi[0]).read_text(encoding="utf-8")
