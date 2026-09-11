"""Il bundle macOS e i launcher: forma, non esecuzione."""

from __future__ import annotations

import plistlib
import stat
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
BUNDLE = RADICE / "MeshRec.app" / "Contents"


def test_il_bundle_ha_plist_eseguibile_e_icona():
    plist = plistlib.loads((BUNDLE / "Info.plist").read_bytes())
    assert plist["CFBundleName"] == "MeshRec"
    assert plist["CFBundleExecutable"] == "MeshRec"
    assert plist["CFBundleIconFile"] == "icona"
    assert plist["CFBundleIdentifier"] == "it.meshrec.app"
    assert plist["CFBundlePackageType"] == "APPL"
    eseguibile = BUNDLE / "MacOS" / "MeshRec"
    assert eseguibile.stat().st_mode & stat.S_IXUSR
    assert (BUNDLE / "Resources" / "icona.icns").is_file()


def test_lo_script_del_bundle_lancia_serve_dalla_cartella_del_programma():
    testo = (BUNDLE / "MacOS" / "MeshRec").read_text(encoding="utf-8")
    assert testo.startswith("#!/bin/sh")
    assert 'uv run meshrec serve "$@"' in testo
    assert "../../.." in testo  # risale dal bundle alla cartella meshrec/
    assert "display dialog" in testo  # gli errori si vedono anche senza Terminale


def test_il_command_non_esiste_piu():
    assert not (RADICE / "MeshRec.command").exists()


def test_il_collegamento_windows_punta_al_bat_con_l_icona():
    testo = (RADICE / "crea-collegamento.ps1").read_text(encoding="utf-8")
    assert "MeshRec.bat" in testo
    assert "icona.ico" in testo
    assert "WScript.Shell" in testo
