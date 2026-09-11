"""Le immagini salvate dall'interfaccia, accanto alla corsa.

Prima il browser scaricava il PNG in Downloads con `<a download>`. Dentro
una finestra pywebview quel gesto apre un pannello «Salva» modale per ogni
immagine, e «salva un'immagine per step» ne aprirebbe undici. Il file va
dove finisce in appendice: `runs/<corsa>/immagini/`.

Il nome lo decide il server con la regola di `nomeDellImmagine` in app.js,
non il client: così un `../` nel nome non puo' uscire dalla cartella.
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from pathlib import Path

from meshrec.core.io import scrivi_atomico

CARTELLA = "immagini"
LIMITE_BYTE = 50 * 1024 * 1024
_PREFISSO = "data:image/png;base64,"
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"


def _pezzo(testo: object) -> str:
    # Stessa sequenza di app.js:1851-1853: minuscolo, NFD, via i combinanti
    # U+0300-U+036F, tutto cio' che non e' [a-z0-9] diventa un trattino.
    piatto = unicodedata.normalize("NFD", str(testo).lower())
    piatto = re.sub(r"[\u0300-\u036f]", "", piatto)
    return re.sub(r"[^a-z0-9]+", "-", piatto).strip("-")


def _nome_della_corsa(out_dir: object) -> str:
    # app.js:1845-1847: l'ultimo segmento, con separatori di entrambi i sistemi.
    pezzi = [p for p in re.split(r"[\\/]", str(out_dir)) if p]
    return pezzi[-1] if pezzi else "corsa"


def nome_dell_immagine(corsa: object, numero: int, nome: object, didascalia: object) -> str:
    pezzi = [_pezzo(_nome_della_corsa(corsa)), f"{int(numero):02d}", _pezzo(nome), _pezzo(didascalia)]
    return "-".join(p for p in pezzi if p) + ".png"


def decodifica_png(dati: str) -> bytes:
    """I byte del PNG da un data URL. ValueError se non e' un PNG."""
    if not dati.startswith(_PREFISSO):
        raise ValueError("l'immagine non è un data URL image/png")
    try:
        png = base64.b64decode(dati[len(_PREFISSO):], validate=True)
    except (binascii.Error, ValueError) as errore:
        raise ValueError(f"l'immagine non si decodifica: {errore}") from None
    if not png.startswith(_FIRMA_PNG):
        raise ValueError("i byte decodificati non sono un PNG")
    return png


def salva(out_dir: Path, numero: int, nome: object, didascalia: object, png: bytes) -> Path:
    """Scrive il PNG in `<out_dir>/immagini/` e torna il percorso. Sovrascrive."""
    cartella = Path(out_dir) / CARTELLA
    if cartella.exists() and not cartella.is_dir():
        raise OSError(f"{cartella} esiste ed è un file, non una cartella: spostalo o cancellalo")
    cartella.mkdir(parents=True, exist_ok=True)
    percorso = cartella / nome_dell_immagine(out_dir, numero, nome, didascalia)
    scrivi_atomico(percorso, lambda temporaneo: temporaneo.write_bytes(png))
    return percorso
