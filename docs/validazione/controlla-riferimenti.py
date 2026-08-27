#!/usr/bin/env python
"""Verifica che ogni riferimento `file:riga` di un documento risolva ancora.

    python docs/validazione/controlla-riferimenti.py docs/validazione/inventario-grandezze.md
    python docs/validazione/controlla-riferimenti.py --autoprova

Stampa **solo** i riferimenti che non risolvono, uno per riga, con il perche':
file assente, nome ambiguo, riga oltre la fine (con la lunghezza vera). Esce 1
se ne resta almeno uno, 0 se risolvono tutti o se il documento non ne porta
nessuno, 2 se l'argomento non e' un file leggibile.

**Limite dichiarato.** Vede i riferimenti in forma `nome.ext:NNN`. La forma
abbreviata `` `:NNN` `` -- il file lo porta il contesto -- non e' risolvibile a
macchina: dentro una stessa riga di tabella i documenti alternano il sorgente e
il suo test, quindi «l'ultimo file nominato» sbaglia. Lo script li conta e lo
dice invece di darli per buoni.
"""

from __future__ import annotations

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


def _righe(percorso: Path) -> int:
    with percorso.open("rb") as f:
        return sum(1 for _ in f)


def controlla(documento: Path) -> list[str]:
    """I riferimenti del documento che non risolvono, gia' formattati."""
    indice = _indice()
    guasti = []
    for numero, riga in enumerate(documento.read_text(encoding="utf-8").splitlines(), 1):
        for nome, prima, ultima in RIFERIMENTO.findall(riga):
            candidati = indice.get(Path(nome).name, [])
            if len(nome.split("/")) > 1:
                candidati = [c for c in candidati if str(c).endswith(nome)]
            citato = f"{nome}:{prima}" + (f"-{ultima}" if ultima else "")
            if not candidati:
                guasti.append(f"{documento}:{numero}: {citato} -- nessun file con questo nome nell'albero")
            elif len(candidati) > 1:
                elenco = ", ".join(str(c.relative_to(RADICE)) for c in sorted(candidati))
                guasti.append(f"{documento}:{numero}: {citato} -- nome ambiguo: {elenco}")
            else:
                quante = _righe(candidati[0])
                oltre = [n for n in (prima, ultima) if n and int(n) > quante]
                if oltre or int(prima) < 1:
                    guasti.append(f"{documento}:{numero}: {citato} -- "
                                  f"{candidati[0].relative_to(RADICE)} ha {quante} righe")
    return guasti


def autoprova() -> None:
    indice = _indice()
    with tempfile.TemporaryDirectory() as cartella:
        doc = Path(cartella) / "prova.md"

        doc.write_text("vedi `inesistente.py:1` e basta\n", encoding="utf-8")
        esito = controlla(doc)
        assert len(esito) == 1 and "inesistente.py:1" in esito[0], esito

        doc.write_text("nessun riferimento qui, solo prosa.\n", encoding="utf-8")
        assert controlla(doc) == []

        mio = Path(__file__).name
        doc.write_text(f"oltre la fine: `{mio}:99999`\n", encoding="utf-8")
        esito = controlla(doc)
        vere = _righe(Path(__file__))
        assert len(esito) == 1 and str(vere) in esito[0], (esito, vere)

        doc.write_text(f"buono: `{mio}:1`\n", encoding="utf-8")
        assert controlla(doc) == []

        assert main([cartella]) == 2, "una cartella si dichiara, non solleva"

    assert indice, "l'indice dell'albero non puo' essere vuoto"
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

    non_risolti = controlla(documento)
    abbreviati = len(ABBREVIATO.findall(documento.read_text(encoding="utf-8")))
    for riga in non_risolti:
        print(riga)
    if abbreviati:
        print(f"({abbreviati} riferimenti in forma `:NNN` non verificabili: "
              f"il file lo porta il contesto)")
    return 1 if non_risolti else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
