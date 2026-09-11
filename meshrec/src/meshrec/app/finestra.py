"""La finestra di MeshRec: pywebview, poi Chromium in modalita' app, poi il browser.

L'ordine e' quello della spec: la finestra propria (titolo, icona, chiusura
che ferma il server) quando c'e'; senza WebView2 su Windows MAI il fallback
MSHTML di pywebview, che e' IE11 senza WebGL2 e senza `import`, ma Edge o
Chrome con `--app`; senza nemmeno quelli, il browser di sistema come prima.

`apri` torna solo a finestra chiusa nei primi due rami: e' il chiamante
(`cli.py`) a fermare uvicorn quando `apri` torna.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path

TITOLO = "MeshRec"
LARGHEZZA, ALTEZZA = 1280, 800

_CHIAVI_WEBVIEW2 = (
    r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
)
_APP_PATHS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{}"
_MAC_CHROMIUM = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)


def webview2_presente() -> bool:
    """Fuori da Windows non serve. Su Windows: la chiave che l'installer scrive."""
    if sys.platform != "win32":
        return True
    import winreg

    for radice in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for chiave in _CHIAVI_WEBVIEW2:
            try:
                with winreg.OpenKey(radice, chiave) as aperta:
                    versione, _ = winreg.QueryValueEx(aperta, "pv")
                    if versione and versione != "0.0.0.0":
                        return True
            except OSError:
                continue
    return False


def trova_chromium() -> list[str] | None:
    """Il comando di Edge o Chrome, senza argomenti. None se non c'e'."""
    if sys.platform == "win32":
        import winreg

        for exe in ("msedge.exe", "chrome.exe"):
            for radice in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(radice, _APP_PATHS.format(exe)) as aperta:
                        percorso, _ = winreg.QueryValueEx(aperta, "")
                        if percorso and Path(percorso).is_file():
                            return [percorso]
                except OSError:
                    continue
        return None
    for percorso in _MAC_CHROMIUM:
        if Path(percorso).is_file():
            return [percorso]
    for nome in ("google-chrome", "chromium", "microsoft-edge"):
        trovato = shutil.which(nome)
        if trovato:
            return [trovato]
    return None


def apri(
    indirizzo: str,
    *,
    cache: Path,
    forza_browser: bool = False,
    avvisa: Callable[[str], object] = lambda testo: print(testo, file=sys.stderr),
) -> str:
    """Apre l'interfaccia. Torna "finestra" o "app" a finestra chiusa, "browser" subito."""
    if not forza_browser:
        try:
            import webview
        except ImportError:
            webview = None
        if webview is not None and webview2_presente():
            webview.settings["ALLOW_DOWNLOADS"] = True
            webview.create_window(TITOLO, indirizzo, width=LARGHEZZA, height=ALTEZZA)
            webview.start()
            return "finestra"
        if webview is not None:
            avvisa("il runtime WebView2 manca: apro con Edge o Chrome in modalità app")
        comando = trova_chromium()
        if comando is not None:
            profilo = Path(cache) / "finestra"
            processo = subprocess.Popen([
                *comando,
                f"--app={indirizzo}",
                f"--user-data-dir={profilo}",
                "--no-first-run",
                f"--window-size={LARGHEZZA},{ALTEZZA}",
            ])
            processo.wait()
            return "app"
        avvisa("nessuna finestra disponibile: apro nel browser")
    webbrowser.open(indirizzo)
    return "browser"
