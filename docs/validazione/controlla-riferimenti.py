#!/usr/bin/env python
"""Verifica che ogni riferimento `file:riga` di un documento risolva ancora.

    python docs/validazione/controlla-riferimenti.py docs/validazione/inventario-grandezze.md
    python docs/validazione/controlla-riferimenti.py --autoprova

Ordina cio' che trova in **tre** categorie, e solo la prima e' un difetto:

- **rotti** -- il file sta nell'albero e la riga non c'e' (o il nome e'
  ambiguo). Uscita 1.
- **fuori albero** -- il file non sta in questo repository e non ci stara' mai:
  i documenti citano il sorgente di CalculiX (`spooles.c`, `gen3delem.f`) per
  provenienza. Non risolvibili **per costruzione**, non un difetto, uscita 0.
  Restano stampati: un nome di file scritto male finisce qui, e va visto.
- **non verificabili a macchina** -- la forma abbreviata `` `:NNN` ``, dove il
  file lo porta il contesto. Dentro una stessa riga di tabella i documenti
  alternano il sorgente e il suo test, quindi «l'ultimo file nominato»
  sbaglia. Contati e dichiarati invece che dati per buoni.

Uscita 2 se l'argomento non e' un file leggibile.

**Limite che resta.** Un riferimento che risolve puo' comunque mentire: che la
riga esista non dice che porti ancora la cosa di cui il testo parla. Quello lo
vede solo chi legge.
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
SALTA = {".git", "node_modules", ".venv", "__pycache__"}

RIFERIMENTO = re.compile(r"(?<![\w/.-])([A-Za-z_][\w./-]*\.[A-Za-z]{1,5}):(\d+)(?:-(\d+))?")
ABBREVIATO = re.compile(r"`:(\d+)")


def _indice() -> dict[str, list[Path]]:
    """Nome di file -> percorsi che lo portano, su tutto l'albero."""
    trovati: dict[str, list[Path]] = {}
    for percorso in RADICE.rglob("*"):
        if percorso.is_file() and not SALTA & set(percorso.parts):
            trovati.setdefault(percorso.name, []).append(percorso)
    return trovati


def _breve(percorso: Path) -> str:
    """Il percorso relativo alla radice, o quello intero se ne sta fuori."""
    try:
        return str(percorso.relative_to(RADICE))
    except ValueError:
        return str(percorso)


def _righe(percorso: Path) -> int:
    with percorso.open("rb") as f:
        return sum(1 for _ in f)


def controlla(
    documento: Path, indice: dict[str, list[Path]] | None = None
) -> tuple[list[str], list[str], list[str]]:
    """(rotti, fuori albero, non verificabili), gia' formattati per la stampa."""
    if indice is None:
        indice = _indice()
    rotti: list[str] = []
    fuori: list[str] = []
    non_verificabili: list[str] = []

    for numero, riga in enumerate(documento.read_text(encoding="utf-8").splitlines(), 1):
        dove = f"{documento}:{numero}"
        for nome, prima, ultima in RIFERIMENTO.findall(riga):
            candidati = indice.get(Path(nome).name, [])
            if "/" in nome:
                candidati = [c for c in candidati if str(c).endswith(nome)]
            citato = f"{nome}:{prima}" + (f"-{ultima}" if ultima else "")
            if not candidati:
                fuori.append(f"{dove}: {citato} -- fuori dall'albero di questo "
                             f"repository, non risolvibile per costruzione")
            elif len(candidati) > 1:
                elenco = ", ".join(_breve(c) for c in sorted(candidati))
                rotti.append(f"{dove}: {citato} -- nome ambiguo: {elenco}")
            else:
                quante = _righe(candidati[0])
                oltre = any(int(n) > quante for n in (prima, ultima) if n)
                if oltre or int(prima) < 1:
                    rotti.append(f"{dove}: {citato} -- "
                                 f"{_breve(candidati[0])} ha {quante} righe")
        for abbreviato in ABBREVIATO.findall(riga):
            non_verificabili.append(f"{dove}: `:{abbreviato}` -- il file lo porta "
                                    f"il contesto, non verificabile a macchina")
    return rotti, fuori, non_verificabili


def _corsa(argomenti: list[str]) -> tuple[str, int]:
    """`main` con lo stdout catturato: l'autoprova non sporca la propria corsa."""
    catturato = io.StringIO()
    with contextlib.redirect_stdout(catturato):
        uscita = main(argomenti)
    return catturato.getvalue(), uscita


def autoprova() -> None:
    with tempfile.TemporaryDirectory() as cartella:
        doc = Path(cartella) / "prova.md"
        mio = Path(__file__).name

        # un sorgente che questo repository non contiene, e non conterra' mai
        doc.write_text("il manuale cita `spooles.c:225` e basta\n", encoding="utf-8")
        rotti, fuori, _ = controlla(doc)
        assert rotti == [], rotti
        assert len(fuori) == 1 and "per costruzione" in fuori[0], fuori
        assert _corsa([str(doc)])[1] == 0, "un fuori albero da solo non e' un difetto"

        # la forma abbreviata: terza categoria, ne' risolta ne' taciuta
        doc.write_text(f"`{mio}:1` e poi `:2`\n", encoding="utf-8")
        rotti, fuori, ignoti = controlla(doc)
        assert (rotti, fuori) == ([], []), (rotti, fuori)
        assert len(ignoti) == 1 and "`:2`" in ignoti[0], ignoti

        # documento senza alcun riferimento: esito stampato, non il vuoto
        doc.write_text("nessun riferimento qui, solo prosa.\n", encoding="utf-8")
        assert controlla(doc) == ([], [], [])
        esito, uscita = _corsa([str(doc)])
        assert uscita == 0 and "0 rotti" in esito, esito

        # riga oltre la fine: la lunghezza vera nel messaggio, non un IndexError
        doc.write_text(f"oltre la fine: `{mio}:99999`\n", encoding="utf-8")
        rotti, _, _ = controlla(doc)
        vere = _righe(Path(__file__))
        assert len(rotti) == 1 and str(vere) in rotti[0], (rotti, vere)
        assert _corsa([str(doc)])[1] == 1

        # file che esiste ma e' vuoto, citato a riga 1: rotto, e lo dice con lo 0
        vuoto = Path(cartella) / "vuoto.md"
        vuoto.write_text("", encoding="utf-8")
        doc.write_text("`vuoto.md:1` non esiste perche' il file e' vuoto\n", encoding="utf-8")
        rotti, _, _ = controlla(doc, {"vuoto.md": [vuoto]})
        assert len(rotti) == 1 and "ha 0 righe" in rotti[0], rotti

        esito, uscita = _corsa([cartella])
        assert uscita == 2 and "cartella" in esito, esito

    assert _indice(), "l'indice dell'albero non puo' essere vuoto"
    print("autoprova: tutti gli assert passati")


def main(argomenti: list[str]) -> int:
    if argomenti == ["--autoprova"]:
        autoprova()
        return 0
    if len(argomenti) != 1:
        print(__doc__)
        return 2
    documento = Path(argomenti[0])
    if documento.is_dir():
        print(f"{documento} e' una cartella, non un documento: passane uno alla volta")
        return 2
    if not documento.is_file():
        print(f"{documento} non esiste")
        return 2

    rotti, fuori, non_verificabili = controlla(documento)
    for titolo, elenco in (
        ("rotti", rotti),
        ("fuori albero, non risolvibili per costruzione", fuori),
        ("non verificabili a macchina", non_verificabili),
    ):
        if elenco:
            print(f"--- {titolo}: {len(elenco)}")
            for riga in elenco:
                print(riga)
    # L'esito si stampa sempre, anche quando non c'e' nulla da elencare: un
    # prompt vuoto non dice se il controllo e' passato o se non e' partito.
    testo = documento.read_text(encoding="utf-8")
    totale = len(RIFERIMENTO.findall(testo)) + len(ABBREVIATO.findall(testo))
    print(f"{documento}: {len(rotti)} rotti, {len(fuori)} fuori albero, "
          f"{len(non_verificabili)} non verificabili, su {totale} riferimenti")
    return 1 if rotti else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
