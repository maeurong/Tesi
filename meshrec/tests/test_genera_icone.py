"""Test dello script strumenti/genera-icone.py (nome col trattino: importato per percorso)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image

RADICE = Path(__file__).resolve().parent.parent
SCRIPT = RADICE / "strumenti" / "genera-icone.py"
UI = RADICE / "src" / "meshrec" / "ui"


def _carica_modulo():
    spec = importlib.util.spec_from_file_location("genera_icone", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_gli_angoli_sono_trasparenti_non_bianchi():
    grande = Image.open(UI / "icona-512.png").convert("RGBA")
    piccola = Image.open(UI / "icona-32.png").convert("RGBA")
    assert grande.getpixel((0, 0))[3] == 0
    assert grande.getpixel((2, 256))[:3] == (0x2F, 0x5D, 0x50)
    assert grande.getpixel((2, 256))[3] == 255
    assert piccola.getpixel((0, 0))[3] == 0


def test_senza_qlmanage_esce_1_e_non_scrive_nulla(monkeypatch, tmp_path):
    modulo = _carica_modulo()
    monkeypatch.setattr(modulo.shutil, "which", lambda nome: None)
    monkeypatch.setattr(modulo, "UI", tmp_path)
    monkeypatch.setattr(modulo, "ICNS", tmp_path / "bundle" / "icona.icns")
    assert modulo.main() == 1
    assert list(tmp_path.iterdir()) == []


def test_senza_iconutil_scrive_png_e_ico_e_salta_icns(monkeypatch, tmp_path, capsys):
    modulo = _carica_modulo()

    def _rasterizza_finta(misura: int, destinazione: Path) -> None:
        Image.new("RGBA", (1, 1)).save(destinazione)

    monkeypatch.setattr(modulo, "rasterizza", _rasterizza_finta)
    monkeypatch.setattr(modulo.shutil, "which", lambda nome: "/usr/bin/qlmanage" if nome == "qlmanage" else None)
    monkeypatch.setattr(modulo, "UI", tmp_path)
    icns = tmp_path / "bundle" / "icona.icns"
    monkeypatch.setattr(modulo, "ICNS", icns)

    assert modulo.main() == 0
    for misura in modulo.MISURE_PNG:
        assert (tmp_path / f"icona-{misura}.png").exists()
    assert (tmp_path / "icona.ico").exists()
    assert not icns.exists()
    assert "iconutil non trovato" in capsys.readouterr().err
