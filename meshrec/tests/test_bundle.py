"""Il bundle macOS e i launcher: forma, non esecuzione."""

from __future__ import annotations

import plistlib
import stat
import tomllib
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


def test_lo_script_del_bundle_avvisa_se_spostato_fuori_dal_progetto():
    """Punto 5 fix wave: bundle spostato fuori da meshrec/ -> dialogo che lo
    dice, non un errore muto di uv."""
    testo = (BUNDLE / "MacOS" / "MeshRec").read_text(encoding="utf-8")
    assert "pyproject.toml" in testo


def test_la_versione_del_plist_segue_pyproject():
    """Punto 6 fix wave: se pyproject.toml cambia versione e il plist non
    segue, questo test diventa rosso."""
    plist = plistlib.loads((BUNDLE / "Info.plist").read_bytes())
    versione = tomllib.loads((RADICE / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert plist["CFBundleShortVersionString"] == versione
    assert plist["CFBundleVersion"] == versione


def test_lo_script_del_bundle_scrive_il_codice_d_uscita_nel_log():
    """Il dialogo dice solo «si e' fermato con un errore»: il numero che
    distingue un'uscita ordinata (1) da una morte per segnale (134/139) andava
    perso con l'`if ! uv run ...`. Senza, la prossima diagnosi e' inventata."""
    testo = (BUNDLE / "MacOS" / "MeshRec").read_text(encoding="utf-8")
    assert "codice=$?" in testo
    assert "uscito con codice $codice" in testo
    assert 'exit "$codice"' in testo  # il bundle non maschera l'uscita con 1
