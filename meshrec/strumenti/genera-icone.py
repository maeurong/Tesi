"""Dall'SVG dell'icona ai formati che i sistemi vogliono.

Si lancia sul Mac dell'autore e i derivati si committano: chi clona non deve
avere `qlmanage` ne' `iconutil`. Senza `iconutil` (fuori da macOS) produce
PNG e .ico e salta l'.icns con un avviso.

    uv run python strumenti/genera-icone.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

RADICE = Path(__file__).resolve().parent.parent
UI = RADICE / "src" / "meshrec" / "ui"
SORGENTE = UI / "icona.svg"
ICNS = RADICE / "MeshRec.app" / "Contents" / "Resources" / "icona.icns"
MISURE_PNG = (32, 180, 512)
# 64 e 1024 non hanno uno slot nell'iconset di iconutil: generarli e' rasterizzare a vuoto.
MISURE_ICNS = (16, 32, 128, 256, 512)
RAGGIO_ANGOLI = 104 / 512  # rx del rect nell'SVG (104 su un viewBox 512), in frazione del lato


def rasterizza(misura: int, destinazione: Path) -> None:
    with tempfile.TemporaryDirectory() as cartella:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(misura), "-o", cartella, str(SORGENTE)],
            check=True, capture_output=True,
        )
        prodotto = Path(cartella) / (SORGENTE.name + ".png")
        immagine = Image.open(prodotto).convert("RGBA").resize((misura, misura))
        # qlmanage compone il render su sfondo bianco: senza questa maschera gli
        # angoli arrotondati del chip portano un quadrato bianco opaco dietro,
        # visibile nel Dock/taskbar su sfondo scuro.
        maschera = Image.new("L", (misura, misura), 0)
        ImageDraw.Draw(maschera).rounded_rectangle(
            (0, 0, misura - 1, misura - 1), radius=round(misura * RAGGIO_ANGOLI), fill=255
        )
        immagine.putalpha(maschera)
        immagine.save(destinazione)


def main() -> int:
    if shutil.which("qlmanage") is None:
        print("qlmanage non trovato: questo script rasterizza l'SVG solo su macOS", file=sys.stderr)
        return 1
    for misura in MISURE_PNG:
        rasterizza(misura, UI / f"icona-{misura}.png")
    grande = UI / "icona-512.png"
    Image.open(grande).save(UI / "icona.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    if shutil.which("iconutil") is None:
        print("iconutil non trovato: .icns saltato", file=sys.stderr)
        return 0
    with tempfile.TemporaryDirectory() as cartella:
        iconset = Path(cartella) / "icona.iconset"
        iconset.mkdir()
        for misura in MISURE_ICNS:
            rasterizza(misura, iconset / f"icon_{misura}x{misura}.png")
            if misura <= 512:
                rasterizza(misura * 2, iconset / f"icon_{misura}x{misura}@2x.png")
        ICNS.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS)], check=True)
    print("icone scritte:", *sorted(p.name for p in UI.glob("icona*")), ICNS.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
