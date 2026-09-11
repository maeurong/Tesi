"""Il guscio: pywebview, poi Chromium in modalita' app, poi il browser.

Nessun test apre una finestra vera: `webview` e `subprocess.Popen` sono finti
messi in sys.modules e in monkeypatch. Cio' che si prova e' la scelta del
ramo e il fatto che il ritorno arrivi solo a finestra chiusa.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from meshrec.app import finestra


@pytest.fixture()
def webview_finto(monkeypatch):
    modulo = types.ModuleType("webview")
    modulo.settings = {}
    modulo.finestre = []

    def create_window(titolo, url, **opzioni):
        modulo.finestre.append((titolo, url, opzioni))
        return object()

    modulo.create_window = create_window
    modulo.start = lambda *a, **k: None  # torna subito: finestra «chiusa»
    monkeypatch.setitem(sys.modules, "webview", modulo)
    return modulo


@pytest.fixture()
def senza_webview(monkeypatch):
    monkeypatch.setitem(sys.modules, "webview", None)  # import fallisce


class _ChiaveRegistroFinta:
    """Context manager di `winreg.OpenKey`: un dizionario {valore: (dato, tipo)}."""

    def __init__(self, dati):
        self._dati = dati

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _winreg_finto(mappa):
    """Registro finto: mappa (radice, chiave) -> {valore: (dato, tipo)}.

    `OpenKey`/`QueryValueEx` sollevano `OSError` per chiavi/valori assenti,
    come il vero `winreg` quando la chiave non esiste.
    """
    modulo = types.ModuleType("winreg")
    modulo.HKEY_LOCAL_MACHINE = "HKLM"
    modulo.HKEY_CURRENT_USER = "HKCU"

    def OpenKey(radice, chiave):
        if (radice, chiave) not in mappa:
            raise OSError("chiave assente")
        return _ChiaveRegistroFinta(mappa[(radice, chiave)])

    def QueryValueEx(aperta, valore):
        if valore not in aperta._dati:
            raise OSError("valore assente")
        return aperta._dati[valore]

    modulo.OpenKey = OpenKey
    modulo.QueryValueEx = QueryValueEx
    return modulo


@pytest.fixture()
def windows(monkeypatch):
    monkeypatch.setattr(finestra.sys, "platform", "win32")


def test_con_pywebview_apre_la_finestra_e_torna_a_chiusura(webview_finto, tmp_path, monkeypatch):
    monkeypatch.setattr(finestra, "webview2_presente", lambda: True)
    esito = finestra.apri("http://127.0.0.1:8765/", cache=tmp_path)
    assert esito == "finestra"
    assert webview_finto.finestre[0][:2] == ("MeshRec", "http://127.0.0.1:8765/")
    assert webview_finto.settings["ALLOW_DOWNLOADS"] is True


def test_senza_webview2_su_windows_passa_a_chromium(webview_finto, tmp_path, monkeypatch):
    monkeypatch.setattr(finestra, "webview2_presente", lambda: False)
    monkeypatch.setattr(finestra, "trova_chromium", lambda: ["/finto/msedge"])
    lanci = []

    class Popen:
        def __init__(self, comando, **k):
            lanci.append(comando)

        def wait(self):
            return 0

    monkeypatch.setattr(finestra.subprocess, "Popen", Popen)
    detti = []
    esito = finestra.apri("http://127.0.0.1:8765/", cache=tmp_path, avvisa=detti.append)
    assert esito == "app"
    assert webview_finto.finestre == []
    assert lanci[0][0] == "/finto/msedge"
    assert "--app=http://127.0.0.1:8765/" in lanci[0]
    assert f"--user-data-dir={tmp_path / 'finestra'}" in lanci[0]
    assert "--no-first-run" in lanci[0]
    assert any("WebView2" in d for d in detti)


def test_senza_pywebview_e_senza_chromium_apre_il_browser(senza_webview, tmp_path, monkeypatch):
    monkeypatch.setattr(finestra, "trova_chromium", lambda: None)
    aperti = []
    monkeypatch.setattr(finestra.webbrowser, "open", aperti.append)
    detti = []
    esito = finestra.apri("http://127.0.0.1:8765/", cache=tmp_path, avvisa=detti.append)
    assert esito == "browser"
    assert aperti == ["http://127.0.0.1:8765/"]
    assert any("browser" in d for d in detti)


def test_forza_browser_salta_la_finestra_anche_con_pywebview(webview_finto, tmp_path, monkeypatch):
    aperti = []
    monkeypatch.setattr(finestra.webbrowser, "open", aperti.append)
    esito = finestra.apri("http://127.0.0.1:8765/", cache=tmp_path, forza_browser=True)
    assert esito == "browser"
    assert webview_finto.finestre == []
    assert aperti == ["http://127.0.0.1:8765/"]


def test_webview2_presente_e_vero_fuori_da_windows(monkeypatch):
    monkeypatch.setattr(finestra.sys, "platform", "darwin")
    assert finestra.webview2_presente() is True


def test_trova_chromium_torna_none_se_non_c_e_nulla(monkeypatch):
    monkeypatch.setattr(finestra.sys, "platform", "darwin")
    monkeypatch.setattr(finestra.Path, "is_file", lambda self: False)
    monkeypatch.setattr(finestra.shutil, "which", lambda nome: None)
    assert finestra.trova_chromium() is None


def test_webview2_presente_vero_con_chiave_hklm(windows, monkeypatch):
    chiave = finestra._CHIAVI_WEBVIEW2[0]
    mappa = {("HKLM", chiave): {"pv": ("120.0.0.0", 1)}}
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    assert finestra.webview2_presente() is True


def test_webview2_presente_vero_con_solo_hkcu(windows, monkeypatch):
    chiave = finestra._CHIAVI_WEBVIEW2[1]
    mappa = {("HKCU", chiave): {"pv": ("120.0.0.0", 1)}}
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    assert finestra.webview2_presente() is True


def test_webview2_presente_falso_senza_alcuna_chiave(windows, monkeypatch):
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto({}))
    assert finestra.webview2_presente() is False


def test_webview2_presente_falso_con_versione_zero(windows, monkeypatch):
    chiave = finestra._CHIAVI_WEBVIEW2[0]
    mappa = {("HKLM", chiave): {"pv": ("0.0.0.0", 1)}}
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    assert finestra.webview2_presente() is False


def test_trova_chromium_windows_trova_msedge_in_app_paths(windows, monkeypatch):
    chiave = finestra._APP_PATHS.format("msedge.exe")
    percorso = r"C:\Program Files\Microsoft\Edge\msedge.exe"
    mappa = {("HKLM", chiave): {"": (percorso, 1)}}
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    monkeypatch.setattr(finestra.Path, "is_file", lambda self: True)
    assert finestra.trova_chromium() == [percorso]


def test_trova_chromium_windows_prova_chrome_dopo_msedge(windows, monkeypatch):
    chiave_chrome = finestra._APP_PATHS.format("chrome.exe")
    percorso = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    mappa = {("HKLM", chiave_chrome): {"": (percorso, 1)}}  # msedge assente
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    monkeypatch.setattr(finestra.Path, "is_file", lambda self: True)
    assert finestra.trova_chromium() == [percorso]


def test_trova_chromium_windows_none_senza_chiavi(windows, monkeypatch):
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto({}))
    monkeypatch.setattr(finestra.Path, "is_file", lambda self: True)
    assert finestra.trova_chromium() is None


def test_trova_chromium_windows_none_se_il_file_non_esiste(windows, monkeypatch):
    chiave = finestra._APP_PATHS.format("msedge.exe")
    percorso = r"C:\Program Files\Microsoft\Edge\msedge.exe"
    mappa = {("HKLM", chiave): {"": (percorso, 1)}}
    monkeypatch.setitem(sys.modules, "winreg", _winreg_finto(mappa))
    monkeypatch.setattr(finestra.Path, "is_file", lambda self: False)
    assert finestra.trova_chromium() is None
