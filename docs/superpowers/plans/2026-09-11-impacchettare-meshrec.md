# MeshRec come programma — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MeshRec si apre in una finestra sua con nome e icona, salva le immagini accanto alla corsa, dice chi è e come si cita, e il repository porta il suo nome con versione 1.0.0, CITATION.cff, CHANGELOG, release e DOI.

**Architecture:** uvicorn passa in un thread e il thread principale tiene il guscio (pywebview → Chromium `--app` → browser); una rotta nuova riceve il PNG dal browser e lo scrive in `runs/<corsa>/immagini/`; `/api/info` legge versione, commit e DOI e un piè di pagina li mostra; il bundle `MeshRec.app` e un collegamento Windows danno l'icona nel Dock e nel menu Start. L'identità su GitHub è lavoro di repository, non di codice.

**Tech Stack:** Python 3.12, FastAPI + uvicorn, pywebview ≥ 6.2, three.js r180 (invariato), Pillow (già nel lock), `iconutil`/`qlmanage` di macOS, `gh`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-11-impacchettare-meshrec-design.md`

**Ricerca:** `docs/ricerca/index.md`. Ogni task cita le righe delle ricerche da cui discende, o dichiara `nessun riferimento pertinente`.

## Global Constraints

- `requires-python = ">=3.12,<3.13"` (`meshrec/pyproject.toml:4`); nessuna dipendenza nuova oltre `pywebview>=6.2`.
- Lingua dell'interfaccia, dei commenti, dei messaggi di commit: italiano, con accenti corretti (`PRODUCT.md`, «Brand Commitments»).
- **Nessun `http://` o `https://` nei file `.html`/`.js`/`.css` di `meshrec/src/meshrec/ui/`** (`tests/test_server.py:2295-2304`): ogni URL arriva dal server via JSON.
- Ogni colore in `stile.css` è un token di `:root` (`tests/test_stile.py:46`); ogni variabile usata è dichiarata (`:36`).
- Le rotte non sollevano verso il browser: il gestore generico risponde 400 `{errore, messaggio}` (`server.py:864-870`). I rifiuti espliciti usano `JSONResponse(status_code=..., content={"errore": ..., "messaggio": ...})`.
- Test del server con la fixture `cliente` di `tests/test_server.py:21-48` (`base_url="http://127.0.0.1"`, `raise_server_exceptions=False`). Test del JS con `_esegui`/`_funzioni`/`_DOM` di `tests/test_app_js.py` (salta se `node` manca).
- Comandi: percorsi assoluti, `git -C /Users/mario/GitHub/Tesi`, un comando per chiamata. pytest si lancia da `/Users/mario/GitHub/Tesi/meshrec` con `uv run pytest`.
- Branch da `main`: `feat/salva-immagine-server`, `feat/finestra`, `chore/identita`. Commit con Conventional Commits in italiano.
- La cartella locale resta `/Users/mario/GitHub/Tesi` anche dopo il rename del repo.

---

## PR1 — `feat/salva-immagine-server`

### Task 1: Nome e scrittura dell'immagine, lato Python

**Files:**
- Create: `meshrec/src/meshrec/app/immagini.py`
- Test: `meshrec/tests/test_immagini.py`
- Test (parità con il JS): `meshrec/tests/test_app_js.py` (aggiunta in coda)

**Interfaces:**
- Consumes: `scrivi_atomico(path: Path, scrittore: Callable[[Path], None])` da `meshrec/core/io.py:118`; regola di nome di `nomeDellImmagine` in `app.js:1849-1856` e `nomeDellaCorsa` in `app.js:1845-1847`.
- Produces: `nome_dell_immagine(corsa: str, numero: int, nome: str, didascalia: str) -> str`; `decodifica_png(dati: str) -> bytes` (solleva `ValueError`); `salva(out_dir: Path, numero: int, nome: str, didascalia: str, png: bytes) -> Path`; costanti `CARTELLA = "immagini"`, `LIMITE_BYTE = 50 * 1024 * 1024`.

**Dispatch:** backend-engineer · sequenziale, primo di PR1 · skill-gate: `superpowers:test-driven-development` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `nessun riferimento pertinente` · ingressi: spec §2

**Ricerca:** nessun riferimento pertinente (la regola di nome è del codice esistente).

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# meshrec/tests/test_immagini.py
"""Il nome del file e la scrittura dell'immagine salvata accanto alla corsa.

La regola di nome vive due volte, in `app.js` (per il messaggio a video) e
qui (per il file su disco): `test_app_js.py` verifica che coincidano.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from meshrec.app import immagini

PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.mark.parametrize("corsa, numero, nome, didascalia, atteso", [
    ("runs/lab_telaio_v2", 6, "Riparazione", "scarto RMS 9,5 mm", "lab-telaio-v2-06-riparazione-scarto-rms-9-5-mm.png"),
    ("corsa", 5, "Superficie", "", "corsa-05-superficie.png"),
    ("runs\\lab", 1, "Lettura", "", "lab-01-lettura.png"),
    ("runs/lab/", 1, "Lettura", "", "lab-01-lettura.png"),
    ("", 1, "Lettura", "", "corsa-01-lettura.png"),
    ("lab", 2, "Perché", "città à è", "lab-02-perche-citta-a-e.png"),
    ("lab", 3, "../../etc", "/passwd", "lab-03-etc-passwd.png"),
    ("lab", 4, "", "", "lab-04.png"),
])
def test_il_nome_del_file_segue_la_regola_di_app_js(corsa, numero, nome, didascalia, atteso):
    assert immagini.nome_dell_immagine(corsa, numero, nome, didascalia) == atteso


def test_decodifica_un_data_url_png():
    dati = "data:image/png;base64," + base64.b64encode(PNG_MINIMO).decode("ascii")
    assert immagini.decodifica_png(dati) == PNG_MINIMO


@pytest.mark.parametrize("dati", [
    "",
    "data:image/jpeg;base64,AAAA",
    "data:image/png;base64,***non-base64***",
    "data:image/png;base64," + base64.b64encode(b"GIF89a").decode("ascii"),
])
def test_un_data_url_che_non_e_un_png_viene_rifiutato(dati):
    with pytest.raises(ValueError):
        immagini.decodifica_png(dati)


def test_salva_scrive_dentro_immagini_e_sovrascrive(tmp_path: Path):
    primo = immagini.salva(tmp_path / "corsa", 5, "Superficie", "", PNG_MINIMO)
    assert primo == tmp_path / "corsa" / "immagini" / "corsa-05-superficie.png"
    assert primo.read_bytes() == PNG_MINIMO
    secondo = immagini.salva(tmp_path / "corsa", 5, "Superficie", "", PNG_MINIMO + b"x")
    assert secondo == primo
    assert primo.read_bytes() == PNG_MINIMO + b"x"
    assert sorted(p.name for p in primo.parent.iterdir()) == ["corsa-05-superficie.png"]


def test_salva_non_esce_dalla_cartella_immagini(tmp_path: Path):
    percorso = immagini.salva(tmp_path / "corsa", 1, "../../fuori", "..", PNG_MINIMO)
    assert percorso.parent == tmp_path / "corsa" / "immagini"
    assert not (tmp_path / "fuori").exists()


def test_immagini_che_e_un_file_e_non_una_cartella_dice_il_percorso(tmp_path: Path):
    (tmp_path / "corsa").mkdir()
    (tmp_path / "corsa" / "immagini").write_text("non una cartella")
    with pytest.raises(OSError, match="immagini"):
        immagini.salva(tmp_path / "corsa", 1, "Lettura", "", PNG_MINIMO)
```

E in coda a `meshrec/tests/test_app_js.py`:

```python
def test_la_regola_di_nome_del_js_e_quella_del_server_coincidono(tmp_path):
    """Il messaggio a video (app.js) e il file su disco (immagini.py) devono
    dire lo stesso nome: i casi sono gli stessi di test_immagini.py, e il JS
    vero gira su di essi."""
    from meshrec.app import immagini

    casi = [
        ("runs/lab_telaio_v2", 6, "Riparazione", "scarto RMS 9,5 mm"),
        ("corsa", 5, "Superficie", ""),
        ("runs\\\\lab", 1, "Lettura", ""),
        ("", 1, "Lettura", ""),
        ("lab", 2, "Perché", "città à è"),
        ("lab", 3, "../../etc", "/passwd"),
        ("lab", 4, "", ""),
    ]
    attesi = [immagini.nome_dell_immagine(c.replace("\\\\", "\\"), n, no, d) for c, n, no, d in casi]
    righe = "\n".join(
        f'assert.equal(nomeDellImmagine("{c}", {n}, "{no}", "{d}"), "{a}");'
        for (c, n, no, d), a in zip(casi, attesi)
    )
    _esegui(tmp_path, _DOM + _funzioni("nomeDellaCorsa", "nomeDellImmagine") + righe)
```

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `uv run pytest tests/test_immagini.py tests/test_app_js.py::test_la_regola_di_nome_del_js_e_quella_del_server_coincidono -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'meshrec.app.immagini'`

- [ ] **Step 3: Scrivere il modulo**

```python
# meshrec/src/meshrec/app/immagini.py
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
```

Verificare la firma di `scrivi_atomico` in `meshrec/core/io.py:118-140` prima di scrivere la lambda: se lo scrittore riceve un percorso temporaneo, la lambda sopra è giusta; se riceve un file aperto, adattare a `lambda f: f.write(png)`.

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `uv run pytest tests/test_immagini.py tests/test_app_js.py::test_la_regola_di_nome_del_js_e_quella_del_server_coincidono -v`
Expected: PASS (il test JS salta se `node` manca: va eseguito dove `node` c'è, sul Mac di Mario c'è)

- [ ] **Step 5: Commit**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/app/immagini.py meshrec/tests/test_immagini.py meshrec/tests/test_app_js.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(immagini): nome e scrittura del PNG accanto alla corsa"
```

### Task 2: Rotta `POST /api/immagine`

**Files:**
- Modify: `meshrec/src/meshrec/app/server.py` (dopo `@app.post("/api/sfoglia")`, riga ~1043; import in testa accanto a `from meshrec.app import storico`, riga 37)
- Test: `meshrec/tests/test_server.py` (in coda)

**Interfaces:**
- Consumes: `immagini.decodifica_png`, `immagini.salva`, `immagini.LIMITE_BYTE` (Task 1); `config_path`, `corrente()` chiusure di `create_app` (`server.py:733-741`).
- Produces: `POST /api/immagine` → 200 `{"percorso": str}`; 409 `{"errore": "NessunaCorsa"}`; 413 `{"errore": "ImmagineTroppoGrande"}`; 400 `{"errore": "ImmagineNonValida"}` o `{"errore": "ValueError"|"OSError", ...}` dal gestore generico.

**Dispatch:** backend-engineer · sequenziale dopo Task 1 (importa `immagini`) · skill-gate: `superpowers:test-driven-development` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `nessun riferimento pertinente` · ingressi: spec §2

**Ricerca:** nessun riferimento pertinente.

Decisione di piano: le corse in **sola lettura** (`SOLA_LETTURA`, `server.py:752-768`) **accettano** il salvataggio delle immagini. `runs/muro` e `runs/lab_crop` sono le corse di riferimento della tesi ed è proprio di quelle che servono le figure; un PNG in `immagini/` non tocca configurazione né artefatti. Deviazione dalla spec: «`immagini/` esiste come file → 500» diventa **400** con il messaggio di `OSError`, perché il gestore generico risponde 400 a ogni eccezione e la spec chiede solo «messaggio che dice il percorso, nessuna eccezione non gestita».

- [ ] **Step 1: Scrivere i test che falliscono**

In coda a `meshrec/tests/test_server.py`:

```python
PNG_MINIMO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def _corpo_immagine(**cambi):
    corpo = {"numero": 5, "nome": "Superficie", "didascalia": "vista dall'alto",
             "dati": "data:image/png;base64," + PNG_MINIMO_B64}
    corpo.update(cambi)
    return corpo


def test_l_immagine_si_salva_accanto_alla_corsa(cliente, tmp_path):
    risposta = cliente.post("/api/immagine", json=_corpo_immagine())
    assert risposta.status_code == 200, risposta.text
    percorso = Path(risposta.json()["percorso"])
    assert percorso == tmp_path / "corsa" / "immagini" / "corsa-05-superficie-vista-dall-alto.png"
    assert percorso.read_bytes().startswith(b"\x89PNG")


def test_senza_corsa_legata_l_immagine_non_si_salva(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CACHE_DIR", tmp_path / "cache")
    slegato = TestClient(create_app(None, radice_corse=tmp_path / "runs"),
                         base_url="http://127.0.0.1", raise_server_exceptions=False)
    risposta = slegato.post("/api/immagine", json=_corpo_immagine())
    assert risposta.status_code == 409
    assert risposta.json()["errore"] == "NessunaCorsa"
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("dati", [
    "", "data:image/jpeg;base64,AAAA", "data:image/png;base64,***",
    "data:image/png;base64," + "R0lGODlh",
])
def test_un_corpo_che_non_e_un_png_e_rifiutato_senza_scrivere(cliente, tmp_path, dati):
    risposta = cliente.post("/api/immagine", json=_corpo_immagine(dati=dati))
    assert risposta.status_code == 400
    assert risposta.json()["errore"] == "ImmagineNonValida"
    assert not (tmp_path / "corsa" / "immagini").exists()


def test_un_corpo_sopra_il_limite_e_rifiutato_con_413(cliente, tmp_path):
    from meshrec.app.immagini import LIMITE_BYTE
    grande = "data:image/png;base64," + "A" * (LIMITE_BYTE + 1)
    risposta = cliente.post("/api/immagine", json=_corpo_immagine(dati=grande))
    assert risposta.status_code == 413
    assert risposta.json()["errore"] == "ImmagineTroppoGrande"
    assert not (tmp_path / "corsa" / "immagini").exists()


def test_un_corpo_senza_i_campi_attesi_e_rifiutato(cliente):
    risposta = cliente.post("/api/immagine", json={"numero": "cinque"})
    assert risposta.status_code == 400
    assert risposta.json()["errore"] == "ImmagineNonValida"


def test_il_nome_lo_decide_il_server_e_resta_dentro_immagini(cliente, tmp_path):
    risposta = cliente.post("/api/immagine", json=_corpo_immagine(nome="../../fuori", didascalia="/x"))
    assert risposta.status_code == 200, risposta.text
    percorso = Path(risposta.json()["percorso"])
    assert percorso.parent == tmp_path / "corsa" / "immagini"
    assert percorso.name == "corsa-05-fuori-x.png"


def test_lo_stesso_nome_sovrascrive(cliente, tmp_path):
    cliente.post("/api/immagine", json=_corpo_immagine())
    risposta = cliente.post("/api/immagine", json=_corpo_immagine())
    assert risposta.status_code == 200
    assert len(list((tmp_path / "corsa" / "immagini").iterdir())) == 1


def test_una_corsa_in_sola_lettura_accetta_le_immagini(cliente, tmp_path):
    # Le corse di riferimento sono quelle di cui servono le figure in appendice.
    (tmp_path / "SOLA_LETTURA").write_text("")
    risposta = cliente.post("/api/immagine", json=_corpo_immagine())
    assert risposta.status_code == 200, risposta.text


def test_immagini_che_e_un_file_torna_un_messaggio_col_percorso(cliente, tmp_path):
    (tmp_path / "corsa").mkdir()
    (tmp_path / "corsa" / "immagini").write_text("")
    risposta = cliente.post("/api/immagine", json=_corpo_immagine())
    assert risposta.status_code == 400
    assert "immagini" in risposta.json()["messaggio"]
```

Nota sulla fixture: `cliente` lega `tmp_path / "config.yaml"` con `out_dir = tmp_path / "corsa"`; la sentinella `SOLA_LETTURA` si cerca in `config_path.parent`, cioè `tmp_path`.

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `uv run pytest tests/test_server.py -k immagine -v`
Expected: FAIL con 404 su `/api/immagine`

- [ ] **Step 3: Scrivere la rotta**

In testa a `server.py` (riga 37): `from meshrec.app import immagini, storico`. Aggiungere `from fastapi import Request` all'import di riga 25. Dopo la rotta `/api/sfoglia`:

```python
    class ImmagineDaSalvare(BaseModel):
        model_config = ConfigDict(extra="forbid")

        numero: int = Field(ge=1, le=99)
        nome: str = ""
        didascalia: str = ""
        dati: str

    @app.post("/api/immagine")
    async def salva_immagine(richiesta: Request) -> JSONResponse | dict[str, object]:
        """Il PNG del viewport, scritto in `<out_dir>/immagini/`.

        Il corpo si legge a mano e non con un modello nella firma: il limite di
        dimensione deve rispondere 413 prima di decodificare cinquanta
        megabyte, e un modello nella firma li avrebbe gia' letti.

        Le corse in sola lettura accettano: un PNG in `immagini/` non tocca
        configurazione ne' artefatti, e sono proprio le corse di riferimento
        quelle di cui servono le figure.
        """
        dichiarata = richiesta.headers.get("content-length")
        if dichiarata is not None and dichiarata.isdigit() and int(dichiarata) > immagini.LIMITE_BYTE:
            return JSONResponse(status_code=413, content={
                "errore": "ImmagineTroppoGrande",
                "messaggio": f"l'immagine supera i {immagini.LIMITE_BYTE // (1024 * 1024)} MB",
            })
        if config_path is None:
            return JSONResponse(status_code=409, content={
                "errore": "NessunaCorsa",
                "messaggio": "nessuna corsa aperta: l'immagine si salva accanto a una corsa",
            })
        corpo = await richiesta.body()
        if len(corpo) > immagini.LIMITE_BYTE:
            return JSONResponse(status_code=413, content={
                "errore": "ImmagineTroppoGrande",
                "messaggio": f"l'immagine supera i {immagini.LIMITE_BYTE // (1024 * 1024)} MB",
            })
        try:
            dati = ImmagineDaSalvare.model_validate_json(corpo)
            png = immagini.decodifica_png(dati.dati)
        except (ValueError, ValidationError) as errore:
            return JSONResponse(status_code=400, content={
                "errore": "ImmagineNonValida",
                "messaggio": f"l'immagine non si è potuta leggere: {errore}",
            })
        percorso = immagini.salva(Path(corrente().run.out_dir), dati.numero, dati.nome, dati.didascalia, png)
        return {"percorso": str(percorso)}
```

`ValidationError` va importato da `pydantic` nell'import di riga 28-36 se non c'è già; `Field` e `ConfigDict` ci sono (`CorsaScelta`, riga 700).

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `uv run pytest tests/test_server.py -k immagine -v`
Expected: PASS, 11 test

- [ ] **Step 5: Tutta la suite**

Run: `uv run pytest -q`
Expected: nessun rosso oltre gli skip già noti

- [ ] **Step 6: Commit**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/app/server.py meshrec/tests/test_server.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(server): POST /api/immagine scrive il PNG in runs/<corsa>/immagini/"
```

### Task 3: L'interfaccia consegna l'immagine al server

**Files:**
- Modify: `meshrec/src/meshrec/ui/app.js:2132-2140` (dentro `salvaImmagine`)
- Test: `meshrec/tests/test_app_js.py` (in coda)

**Interfaces:**
- Consumes: `POST /api/immagine` (Task 2); `serverMuto` (`app.js:2403`), `ragioneDelRifiuto`, `corpoLetto`, `superata`, `dichiaraErrore` (`app.js:2434`).
- Produces: `async function consegnaImmagine(corpo)` → `{percorso}` oppure `null` dopo aver chiamato `dichiaraErrore`; `salvaImmagine` torna `true` solo a file scritto.

**Dispatch:** frontend-engineer · sequenziale dopo Task 2 (Step 5 prova la rotta vera; `tests/test_app_js.py` già toccato da Task 1) · skill-gate: `superpowers:test-driven-development` (logica di consegna, nessuno stile: `impeccable` non serve; con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-guscio-desktop.md:169` · ingressi: spec §2

**Ricerca:** `docs/ricerca/2026-09-11-guscio-desktop.md:169` (download data URL non documentato in pywebview: la ragione del salvataggio via server).

- [ ] **Step 1: Scrivere il test che fallisce**

In coda a `meshrec/tests/test_app_js.py`:

```python
def test_l_immagine_va_al_server_e_l_esito_dice_il_percorso(tmp_path):
    """Consegna via POST /api/immagine: 200 -> percorso; rifiuto -> dichiaraErrore, null."""
    sorgente = _DOM + _funzioni("consegnaImmagine", "serverMuto", "ragioneDelRifiuto", "corpoLetto", "dichiaraErrore", "superata") + """
const chiamate = [];
globalThis.fetch = async (url, opzioni) => {
  chiamate.push([url, opzioni]);
  const corpo = JSON.parse(opzioni.body);
  if (corpo.numero === 99) return { ok: false, status: 409, text: async () => JSON.stringify({errore: "NessunaCorsa", messaggio: "nessuna corsa aperta"}) };
  return { ok: true, status: 200, text: async () => JSON.stringify({percorso: "runs/lab/immagini/lab-05-superficie.png"}) };
};
const esito = await consegnaImmagine({ numero: 5, nome: "Superficie", didascalia: "", dati: "data:image/png;base64,AAAA" });
assert.equal(esito.percorso, "runs/lab/immagini/lab-05-superficie.png");
assert.equal(chiamate[0][0], "/api/immagine");
assert.equal(chiamate[0][1].method, "POST");
assert.equal(chiamate[0][1].headers["Content-Type"], "application/json");
const rifiuto = await consegnaImmagine({ numero: 99, nome: "", didascalia: "", dati: "data:image/png;base64,AAAA" });
assert.equal(rifiuto, null);
assert.ok(document.getElementById("errore").textContent.includes("nessuna corsa aperta"));
"""
    _esegui(tmp_path, sorgente)


def test_salva_immagine_non_scarica_piu_dal_browser():
    """La mossa: rimettere `<a download>` riaprirebbe il pannello Salva in pywebview."""
    corpo = _sorgente_di("salvaImmagine", _modulo())
    assert ".download =" not in corpo
    assert "consegnaImmagine(" in corpo
```

Prima di scrivere il test guardare come `_DOM` espone `document.getElementById` e `#errore` (`tests/test_app_js.py:283-400`): se `dichiaraErrore` scrive in un nodo con id `errore`, il test sopra regge; se l'id è diverso, adeguarlo.

- [ ] **Step 2: Eseguire i test e vederli fallire**

Run: `uv run pytest tests/test_app_js.py -k "consegna or non_scarica" -v`
Expected: FAIL (`consegnaImmagine` non esiste; `.download =` c'è ancora)

- [ ] **Step 3: Scrivere il JS**

Prima di `salvaImmagine` (verso `app.js:2040`), una funzione nuova:

```javascript
// La consegna al server: prima il PNG usciva con `<a download>` verso la
// cartella Downloads, e dentro la finestra pywebview quel gesto apre un
// pannello «Salva» modale per ogni immagine. Il file va accanto alla corsa,
// in immagini/, dove finisce in appendice. Torna {percorso} a file scritto,
// null dopo aver detto perche' no.
async function consegnaImmagine(corpo) {
  const risposta = await fetch("/api/immagine", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  }).catch(serverMuto);
  if (!risposta.ok) {
    dichiaraErrore("l'immagine non si è potuta salvare: " + await ragioneDelRifiuto(risposta));
    return null;
  }
  const letto = await corpoLetto(risposta);
  if (letto == null || typeof letto.percorso !== "string") {
    dichiaraErrore("l'immagine non si è potuta salvare: il server ha risposto senza dire dove l'ha scritta. " + RIMEDIO);
    return null;
  }
  return letto;
}
```

In `salvaImmagine`, le righe 2132-2140 (da `const collegamento = ...` a `return true;`) diventano:

```javascript
    const esito = await consegnaImmagine({ numero: mostrato, nome, didascalia, dati });
    if (superata(ordine)) return;
    if (esito === null) return;
    document.getElementById("esito-salvataggio").textContent = `Salvata in ${esito.percorso}`;
    // `true` solo a file scritto: i rami di rifiuto qui sopra tornano
    // undefined, e il giro di salvaTuttiGliStep si ferma su quello.
    return true;
```

`superata(ordine)` prima di `esito === null`: un rifiuto arrivato dopo un clic su un altro step non deve scrivere sotto lo step nuovo (stessa regola del fix `1d48b69`). Verificare che `dichiaraErrore` dentro `consegnaImmagine` non violi quella regola: se serve, passare `ordine` a `consegnaImmagine` e fare `if (!superata(ordine)) dichiaraErrore(...)`. In `salvaTuttiGliStep` il `finally` sovrascrive `esito.textContent` con il conteggio: la riga «Salvata in …» del singolo salvataggio è visibile fra uno step e l'altro e poi lascia il posto al totale, che è ciò che serve.

- [ ] **Step 4: Eseguire i test e vederli passare**

Run: `uv run pytest tests/test_app_js.py -v`
Expected: PASS

- [ ] **Step 5: Prova a mano nel browser**

Run: `uv run meshrec serve --port 8770` da `/Users/mario/GitHub/Tesi/meshrec`, aprire `geoandgeo-lab-pr2`, uno step con geometria, «Salva immagine»: `#esito-salvataggio` dice `Salvata in runs/geoandgeo-lab-pr2/immagini/…png`, il file esiste e si apre. Poi «Salva un'immagine per step»: N file, esito finale «N immagini salvate». Chiudere il server.

- [ ] **Step 6: Commit, PR**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/ui/app.js meshrec/tests/test_app_js.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(ui): l'immagine salvata va in runs/<corsa>/immagini/, non in Downloads"
git -C /Users/mario/GitHub/Tesi push -u origin feat/salva-immagine-server
```

Round pre-commit in parallelo (`security-reviewer`, `code-reviewer`, `test-writer`, `craft-reviewer`, `spec-reviewer` contro la spec §2), poi `gh pr create`.

---

## PR2 — `feat/finestra`

### Task 4: Icona

**Files:**
- Create: `meshrec/src/meshrec/ui/icona.svg`
- Create: `meshrec/strumenti/genera-icone.py`
- Create (generati, committati): `meshrec/src/meshrec/ui/icona-32.png`, `icona-180.png`, `icona-512.png`, `meshrec/src/meshrec/ui/icona.ico`, `meshrec/MeshRec.app/Contents/Resources/icona.icns` (la cartella del bundle nasce qui, il resto del bundle in Task 9)
- Modify: `meshrec/src/meshrec/ui/index.html:9-14` (favicon)
- Test: `meshrec/tests/test_server.py` (in coda)

**Interfaces:**
- Produces: i file sopra; `/ui/icona-32.png` servito dalla rotta statica (`server.py:880-885`).

**Dispatch:** frontend-engineer · parallelo con Task 5 e Task 7 (con Task 5 un solo file in comune, `tests/test_server.py`, entrambi in coda: chi commette secondo rilegge il file prima di aggiungere) · **gate: Mario** allo Step 1, l'SVG si mostra prima dei derivati · skill-gate: `impeccable` (critica del render contro `PRODUCT.md` prima di mostrarlo; con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:206`, `:210`, `docs/ricerca/2026-09-11-guscio-desktop.md:62-63` · ingressi: spec §3

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:206` (pattern accademico: glifo semplice + nome), `:210` (una sorgente SVG in `ui/`, il PNG al posto del data URI), `docs/ricerca/2026-09-11-guscio-desktop.md:62-63` (`.ico` Windows, `.icns` macOS; l'icona del Dock arriva solo dal bundle).

- [ ] **Step 1: Disegnare l'SVG e farlo vedere a Mario**

`icona.svg`, 512×512, sfondo quadrato con angoli arrotondati nel colore `--accento` (`#2f5d50`, `stile.css:19`), sopra un tetraedro in filo bianco (quattro vertici, sei spigoli, spessore 28) con i vertici marcati da punti pieni: la mesh a tetraedri è ciò che il programma produce. Nessun testo dentro l'icona: il nome sta accanto, nel Dock e nella barra del titolo.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" rx="104" fill="#2f5d50"/>
  <g stroke="#ffffff" stroke-width="28" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <path d="M256 92 L92 388 L420 388 Z"/>
    <path d="M256 92 L256 300"/>
    <path d="M92 388 L256 300 L420 388"/>
  </g>
  <g fill="#ffffff">
    <circle cx="256" cy="92" r="30"/><circle cx="92" cy="388" r="30"/>
    <circle cx="420" cy="388" r="30"/><circle cx="256" cy="300" r="30"/>
  </g>
</svg>
```

Renderla e aprirla: `qlmanage -t -s 512 -o /private/tmp/claude-501/-Users-mario/dcd8fe22-d1a1-4044-8155-2c20b9321bb1/scratchpad /Users/mario/GitHub/Tesi/meshrec/src/meshrec/ui/icona.svg` poi `open <scratchpad>/icona.svg.png`. **Fermarsi qui e chiedere a Mario se va bene.** Un `xmlns` con `http://` in un `.svg` non viola il banco di rete (guarda solo `.html`/`.js`/`.css`).

- [ ] **Step 2: Scrivere il test del favicon che fallisce**

```python
def test_il_favicon_e_un_file_servito_e_non_un_data_uri(cliente):
    pagina = cliente.get("/").text
    assert 'href="/ui/icona-32.png"' in pagina
    assert "data:image/png;base64" not in pagina
    assert cliente.get("/ui/icona-32.png").status_code == 200
```

Run: `uv run pytest tests/test_server.py -k favicon -v` → FAIL.

- [ ] **Step 3: Lo script che genera i derivati**

```python
# meshrec/strumenti/genera-icone.py
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

from PIL import Image

RADICE = Path(__file__).resolve().parent.parent
UI = RADICE / "src" / "meshrec" / "ui"
SORGENTE = UI / "icona.svg"
ICNS = RADICE / "MeshRec.app" / "Contents" / "Resources" / "icona.icns"
MISURE_PNG = (32, 180, 512)
MISURE_ICNS = (16, 32, 64, 128, 256, 512, 1024)


def rasterizza(misura: int, destinazione: Path) -> None:
    with tempfile.TemporaryDirectory() as cartella:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(misura), "-o", cartella, str(SORGENTE)],
            check=True, capture_output=True,
        )
        prodotto = Path(cartella) / (SORGENTE.name + ".png")
        Image.open(prodotto).convert("RGBA").resize((misura, misura)).save(destinazione)


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
```

Run: `uv run python /Users/mario/GitHub/Tesi/meshrec/strumenti/genera-icone.py`. Expected: elenco dei file; `file icona.ico` dice «MS Windows icon resource»; `icona.icns` si apre in Anteprima.

- [ ] **Step 4: Favicon nel markup**

In `index.html`, righe 9-14: togliere il commento e il `<link rel="icon" ... data:...>`, mettere:

```html
<!-- L'icona della scheda e della finestra: la sorgente e' icona.svg, i PNG
     li scrive strumenti/genera-icone.py. Un file servito e non un data URI:
     lo stesso PNG serve al bundle .app e al collegamento Windows. -->
<link rel="icon" type="image/png" sizes="32x32" href="/ui/icona-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/ui/icona-180.png">
```

Run: `uv run pytest tests/test_server.py -k "favicon or rete_esterna" -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/ui/icona.svg meshrec/src/meshrec/ui/icona-32.png meshrec/src/meshrec/ui/icona-180.png meshrec/src/meshrec/ui/icona-512.png meshrec/src/meshrec/ui/icona.ico meshrec/MeshRec.app/Contents/Resources/icona.icns meshrec/strumenti/genera-icone.py meshrec/src/meshrec/ui/index.html meshrec/tests/test_server.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(ui): icona di MeshRec, sorgente SVG e derivati per scheda, Dock e Windows"
```

### Task 5: `GET /api/info`

**Files:**
- Create: `meshrec/src/meshrec/app/info.py`
- Modify: `meshrec/src/meshrec/app/server.py` (rotta accanto a `/api/run`, riga ~888)
- Test: `meshrec/tests/test_info.py`, `meshrec/tests/test_server.py` (in coda)

**Interfaces:**
- Produces: `informazioni(radice: Path | None = None) -> dict` con chiavi `nome`, `versione`, `commit`, `licenza`, `doi`, `repository`; `GET /api/info` che la restituisce.

**Dispatch:** backend-engineer · parallelo con Task 4 e Task 7 (vedi nota su `tests/test_server.py` in Task 4) · skill-gate: `superpowers:test-driven-development` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:176-177`, `:101-103` · ingressi: spec §3

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:176-177` (`importlib.metadata.version`: una sola fonte di verità), `:101-103` (`CITATION.cff` letto da Zenodo: il DOI sta lì).

- [ ] **Step 1: Test che falliscono**

```python
# meshrec/tests/test_info.py
"""Chi e' il programma: versione, commit, licenza, DOI. Mai un errore."""

from __future__ import annotations

import subprocess
from pathlib import Path

from meshrec.app import info


def test_senza_git_e_senza_cff_le_voci_mancanti_sono_null(tmp_path: Path):
    voci = info.informazioni(tmp_path)
    assert voci["nome"] == "MeshRec"
    assert voci["commit"] is None
    assert voci["doi"] is None
    assert voci["doi_url"] is None
    assert voci["licenza"] == "MIT"
    assert voci["repository"].startswith("https://github.com/maeurong/")
    assert isinstance(voci["versione"], str) and voci["versione"]


def test_il_commit_e_quello_di_head(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=a@b", "-c", "user.name=a",
                    "commit", "-q", "--allow-empty", "-m", "primo"], check=True)
    atteso = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert info.informazioni(tmp_path)["commit"] == atteso


def test_il_doi_viene_dal_citation_cff(tmp_path: Path):
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\ntitle: MeshRec\ndoi: 10.5281/zenodo.1234\n", encoding="utf-8")
    voci = info.informazioni(tmp_path)
    assert voci["doi"] == "10.5281/zenodo.1234"
    assert voci["doi_url"] == "https://doi.org/10.5281/zenodo.1234"


def test_un_cff_illeggibile_non_rompe(tmp_path: Path):
    (tmp_path / "CITATION.cff").write_text("::: non yaml :::\n  - [", encoding="utf-8")
    assert info.informazioni(tmp_path)["doi"] is None


def test_senza_pacchetto_installato_la_versione_dice_sorgente(tmp_path: Path, monkeypatch):
    import importlib.metadata as metadata

    def manca(_nome):
        raise metadata.PackageNotFoundError("meshrec")

    monkeypatch.setattr(info.metadata, "version", manca)
    assert info.informazioni(tmp_path)["versione"] == "sorgente"
```

E in `test_server.py`:

```python
def test_api_info_risponde_sempre(cliente):
    risposta = cliente.get("/api/info")
    assert risposta.status_code == 200
    assert set(risposta.json()) == {"nome", "versione", "commit", "licenza", "doi", "doi_url", "repository"}
```

Run: `uv run pytest tests/test_info.py tests/test_server.py::test_api_info_risponde_sempre -v` → FAIL.

- [ ] **Step 2: Il modulo e la rotta**

```python
# meshrec/src/meshrec/app/info.py
"""Chi e' il programma. Legge, non decide: la versione sta in pyproject.toml,
il commit in git, il DOI in CITATION.cff. Ogni voce assente e' None, mai un
errore: il pie' di pagina non deve mai far cadere l'interfaccia."""

from __future__ import annotations

import importlib.metadata as metadata
import subprocess
from pathlib import Path

import yaml

NOME = "MeshRec"
LICENZA = "MIT"
REPOSITORY = "https://github.com/maeurong/meshrec"
# server.py -> app -> meshrec -> src -> meshrec -> radice del repo
RADICE_REPO = Path(__file__).resolve().parents[4]


def _versione() -> str:
    try:
        return metadata.version("meshrec")
    except metadata.PackageNotFoundError:
        return "sorgente"


def _commit(radice: Path) -> str | None:
    try:
        esito = subprocess.run(
            ["git", "-C", str(radice), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if esito.returncode != 0:
        return None
    return esito.stdout.strip() or None


def _doi(radice: Path) -> str | None:
    cff = radice / "CITATION.cff"
    if not cff.is_file():
        return None
    try:
        voci = yaml.safe_load(cff.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    doi = voci.get("doi") if isinstance(voci, dict) else None
    return str(doi) if doi else None


def informazioni(radice: Path | None = None) -> dict[str, object]:
    radice = RADICE_REPO if radice is None else Path(radice)
    doi = _doi(radice)
    return {
        "nome": NOME,
        "versione": _versione(),
        "commit": _commit(radice),
        "licenza": LICENZA,
        "doi": doi,
        # L'URL lo compone il server: app.js non porta indirizzi di rete
        # (test_server.py, rete esterna).
        "doi_url": f"https://doi.org/{doi}" if doi else None,
        "repository": REPOSITORY,
    }
```

Nota: `REPOSITORY` porta già il nome nuovo del repo (Task 11 lo rinomina; fino ad allora GitHub non reindirizza in avanti, ma il link è a un piè di pagina e la PR3 chiude il buco entro la stessa settimana). In `server.py`, accanto a `/api/run`:

```python
    @app.get("/api/info")
    def informazioni_sul_programma() -> dict[str, object]:
        return info.informazioni()
```

con `from meshrec.app import immagini, info, storico` in testa.

- [ ] **Step 3: Test verdi e commit**

Run: `uv run pytest tests/test_info.py tests/test_server.py::test_api_info_risponde_sempre -v` → PASS.

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/app/info.py meshrec/src/meshrec/app/server.py meshrec/tests/test_info.py meshrec/tests/test_server.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(server): GET /api/info dice versione, commit, licenza e DOI"
```

### Task 6: Piè di pagina «Informazioni su»

**Files:**
- Modify: `meshrec/src/meshrec/ui/index.html` (prima di `</main>`, riga 367)
- Modify: `meshrec/src/meshrec/ui/stile.css` (in coda)
- Modify: `meshrec/src/meshrec/ui/app.js` (funzione nuova + chiamata in `caricaStato`, riga 66)
- Test: `meshrec/tests/test_app_js.py`, `meshrec/tests/test_stile.py` (i test esistenti sui token devono restare verdi)

**Interfaces:**
- Consumes: `GET /api/info` (Task 5).
- Produces: `function righeDelleInformazioni(info) -> Array<{testo, href?}>`; `async function mostraInformazioni()`; markup `<footer class="informazioni" id="informazioni">`.

**Dispatch:** frontend-engineer · sequenziale dopo Task 4 (`index.html`) e Task 5 (`/api/info`); parallelo con Task 8 · skill-gate: `impeccable` (scoped al solo `<footer>`: spec §3 vieta grafica nuova, quindi critica e tipografia, non colori nuovi) più `superpowers:test-driven-development` su `righeDelleInformazioni` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:54`, `:109` · ingressi: spec §3

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:54` (la versione interrogabile è un segnale di maturità), `:109` (la forma della citazione).

- [ ] **Step 1: Test che fallisce**

```python
def test_il_pie_di_pagina_tace_le_voci_nulle_e_porta_il_link_al_repository(tmp_path):
    sorgente = _DOM + _funzioni("righeDelleInformazioni") + """
const piene = righeDelleInformazioni({nome: "MeshRec", versione: "1.0.0", commit: "abc1234", licenza: "MIT", doi: "10.5281/zenodo.99", doi_url: "https://doi.org/10.5281/zenodo.99", repository: "https://github.com/maeurong/meshrec"});
assert.deepEqual(piene.map((r) => r.testo), ["MeshRec 1.0.0", "abc1234", "MIT", "doi 10.5281/zenodo.99", "come citare"]);
assert.equal(piene[4].href, "https://github.com/maeurong/meshrec");
assert.equal(piene[3].href, "https://doi.org/10.5281/zenodo.99");
const vuote = righeDelleInformazioni({nome: "MeshRec", versione: "sorgente", commit: null, licenza: "MIT", doi: null, doi_url: null, repository: "https://github.com/maeurong/meshrec"});
assert.deepEqual(vuote.map((r) => r.testo), ["MeshRec sorgente", "MIT", "come citare"]);
assert.ok(!JSON.stringify(vuote).includes("null"));
"""
    _esegui(tmp_path, sorgente)


def test_il_pie_di_pagina_esiste_nel_markup():
    markup = _senza_commenti_html(_markup())
    assert '<footer class="informazioni" id="informazioni"' in markup
```

Run: `uv run pytest tests/test_app_js.py -k pie_di_pagina -v` → FAIL.

- [ ] **Step 2: Markup, stile, JS**

`index.html`, prima di `</main>` (riga 367):

```html
<!-- Chi e' il programma: versione, commit, licenza, come citare. Le voci le
     scrive app.js da /api/info; l'URL del repository arriva da li' e non da
     qui, perche' l'interfaccia non porta indirizzi di rete (test_server.py,
     rete esterna). -->
<footer class="informazioni" id="informazioni" aria-label="Informazioni sul programma"></footer>
```

`stile.css`, in coda:

```css
/* Il pie' di pagina delle informazioni: corpo di nota, colore tenue, una
   riga sola separata da un filo. Non e' una zona: non porta comandi. */
.informazioni { display: flex; flex-wrap: wrap; gap: 0 var(--passo-3); padding: var(--passo-2) var(--passo-6); border-top: 1px solid var(--bordo); font-size: var(--tipo-nota); line-height: var(--interlinea-riga); color: var(--tenue); }
.informazioni a { color: inherit; }
.informazioni span + span::before { content: "·"; margin-right: var(--passo-3); }
```

Verificare che `--passo-3` e `--interlinea-riga` siano dichiarati in `:root` (`stile.css:50-110`); se `--passo-3` manca usare `--passo-2`.

`app.js`, accanto a `caricaStato` (riga 66):

```javascript
// Le voci del pie' di pagina, da /api/info. Una voce nulla non si scrive:
// «commit null» a video direbbe che qualcosa e' rotto, e non lo e'.
function righeDelleInformazioni(info) {
  const righe = [{ testo: `${info.nome} ${info.versione}` }];
  if (info.commit) righe.push({ testo: info.commit });
  righe.push({ testo: info.licenza });
  if (info.doi) righe.push({ testo: `doi ${info.doi}`, href: info.doi_url });
  righe.push({ testo: "come citare", href: info.repository });
  return righe;
}

async function mostraInformazioni() {
  const risposta = await fetch("/api/info").catch(serverMuto);
  const info = risposta.ok ? await corpoLetto(risposta) : null;
  if (info == null) return;
  const piede = document.getElementById("informazioni");
  piede.replaceChildren(...righeDelleInformazioni(info).map((riga) => {
    const voce = document.createElement("span");
    if (riga.href) {
      const collegamento = document.createElement("a");
      collegamento.href = riga.href;
      collegamento.target = "_blank";
      collegamento.rel = "noopener";
      collegamento.textContent = riga.testo;
      voce.append(collegamento);
    } else {
      voce.textContent = riga.testo;
    }
    return voce;
  }));
}
```

**Banco di rete:** nessuna stringa `https://` in `app.js`: l'URL del DOI arriva come `doi_url` da `/api/info` (Task 5), quello del repository come `repository`.

Chiamare `mostraInformazioni()` una volta all'avvio, in coda a `caricaStato` o nel punto in cui `app.js` fa le prime richieste (leggere `app.js:66-110` per il posto giusto): senza `await`, il piè di pagina non deve ritardare la schermata.

- [ ] **Step 3: Test verdi, prova a occhio, commit**

Run: `uv run pytest tests/test_app_js.py tests/test_stile.py tests/test_server.py -k "pie_di_pagina or stile or rete_esterna or info" -v` → PASS.
Prova: `uv run meshrec serve --port 8770`, la riga in fondo dice «MeshRec 0.1.0 · <sha> · MIT · come citare» e il link apre GitHub.

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/ui/index.html meshrec/src/meshrec/ui/stile.css meshrec/src/meshrec/ui/app.js meshrec/src/meshrec/app/info.py meshrec/tests/test_app_js.py meshrec/tests/test_info.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(ui): pie' di pagina con versione, commit, licenza e come citare"
```

### Task 7: Il guscio — `meshrec/app/finestra.py`

**Files:**
- Modify: `meshrec/pyproject.toml:8-24` (dipendenza `pywebview>=6.2`) e `meshrec/uv.lock` via `uv lock`
- Create: `meshrec/src/meshrec/app/finestra.py`
- Test: `meshrec/tests/test_finestra.py`

**Interfaces:**
- Produces: `webview2_presente() -> bool`; `trova_chromium() -> list[str] | None` (comando pronto per `Popen`, senza l'URL); `apri(indirizzo: str, *, cache: Path, forza_browser: bool = False, avvisa=print) -> str` che torna `"finestra"`, `"app"` o `"browser"` **dopo** che la finestra è stata chiusa (per `finestra` e `app`), subito (per `browser`).

**Dispatch:** backend-engineer · parallelo con Task 4 e Task 5 (file disgiunti: `pyproject.toml`, `uv.lock`, `finestra.py`, `test_finestra.py`) · skill-gate: `superpowers:test-driven-development` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-guscio-desktop.md:46-49`, `:56`, `:69-70`, `:86-96` · ingressi: spec §1

**Ricerca:** `docs/ricerca/2026-09-11-guscio-desktop.md:46-49` (WebView2 e il fallback MSHTML da evitare, chiave di registro), `:56` (`ALLOW_DOWNLOADS`), `:69-70` (evento di chiusura, forma minima), `:86-96` (`--app`, `--user-data-dir`, App Paths, perché il profilo dedicato fa tornare `wait`).

- [ ] **Step 1: Dipendenza**

In `pyproject.toml`, dopo `"gmsh>=4.15.2",`:

```toml
    # Il guscio della finestra (app/finestra.py). >=6.2: prima crashava su
    # Apple Silicon e su Windows mancava il fallback coreclr di pythonnet.
    "pywebview>=6.2",
```

Run: `uv lock` poi `uv sync` da `/Users/mario/GitHub/Tesi/meshrec`. Expected: `pywebview` nel lock; `uv run python -c "import webview; print(webview.__version__)"` stampa ≥ 6.2.

- [ ] **Step 2: Test che falliscono**

```python
# meshrec/tests/test_finestra.py
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
```

Run: `uv run pytest tests/test_finestra.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Il modulo**

```python
# meshrec/src/meshrec/app/finestra.py
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
```

`monkeypatch.setitem(sys.modules, "webview", None)` fa fallire `import webview` con `ImportError`: è il meccanismo standard di Python per un modulo marcato assente.

- [ ] **Step 4: Test verdi e commit**

Run: `uv run pytest tests/test_finestra.py -v` → PASS.

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/pyproject.toml meshrec/uv.lock meshrec/src/meshrec/app/finestra.py meshrec/tests/test_finestra.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(finestra): pywebview, poi Chromium --app, poi il browser"
```

### Task 8: `meshrec serve` apre la finestra e ferma il server alla chiusura

**Files:**
- Modify: `meshrec/src/meshrec/cli.py:82-95` (parser) e `:222-272` (ramo `serve`)
- Test: `meshrec/tests/test_cli.py` (in coda)

**Interfaces:**
- Consumes: `finestra.apri` (Task 7); `create_app`, `ServerConfig`.
- Produces: `meshrec serve [--port N] [--no-browser] [--browser] [config]`; codice 0 a finestra chiusa, 1 su porta occupata o server che non parte.

**Dispatch:** backend-engineer · sequenziale dopo Task 7 (`finestra.apri`); parallelo con Task 6 · skill-gate: `superpowers:test-driven-development` (con `caveman:caveman`, `ponytail:ponytail`) · ricerca: `docs/ricerca/2026-09-11-guscio-desktop.md:67`, `:70` · ingressi: spec §1

Nota di dispatch: lo Step 4 apre e chiude una finestra vera — lo fa Mario o il thread principale davanti al Mac, non il subagente; il subagente chiude allo Step 3 e riporta.

**Ricerca:** `docs/ricerca/2026-09-11-guscio-desktop.md:67` (uvicorn fuori dal thread principale, `should_exit`), `:70` (forma minima).

- [ ] **Step 1: Test che falliscono**

```python
def _server_finto(monkeypatch, cli_module):
    """uvicorn.Server finto: «parte» subito e registra should_exit."""
    import uvicorn

    stato = {"should_exit": False, "serviti": 0}

    class Server:
        def __init__(self, config):
            self.config = config
            self.started = True

        @property
        def should_exit(self):
            return stato["should_exit"]

        @should_exit.setter
        def should_exit(self, valore):
            stato["should_exit"] = valore

        def run(self):
            stato["serviti"] += 1
            while not stato["should_exit"]:
                import time
                time.sleep(0.01)

    monkeypatch.setattr(uvicorn, "Server", Server)
    return stato


def test_serve_apre_la_finestra_e_ferma_il_server_quando_si_chiude(monkeypatch, capsys):
    from meshrec.app import finestra

    stato = _server_finto(monkeypatch, cli)
    chiamate = []

    def apri(indirizzo, *, cache, forza_browser=False, avvisa=None):
        chiamate.append((indirizzo, forza_browser))
        return "finestra"

    monkeypatch.setattr(finestra, "apri", apri)
    codice = cli.main(["serve", "--port", "0"])
    assert codice == 0
    assert stato["serviti"] == 1
    assert stato["should_exit"] is True
    assert chiamate and chiamate[0][1] is False
    assert "MeshRec in ascolto su" in capsys.readouterr().err


def test_serve_browser_forza_il_browser_e_resta_in_ascolto_fino_a_should_exit(monkeypatch):
    from meshrec.app import finestra
    import threading

    stato = _server_finto(monkeypatch, cli)
    chiamate = []

    def apri(indirizzo, *, cache, forza_browser=False, avvisa=None):
        chiamate.append(forza_browser)
        # Nel ramo browser il server resta vivo: qualcuno deve fermarlo.
        threading.Timer(0.05, lambda: stato.__setitem__("should_exit", True)).start()
        return "browser"

    monkeypatch.setattr(finestra, "apri", apri)
    assert cli.main(["serve", "--port", "0", "--browser"]) == 0
    assert chiamate == [True]


def test_serve_no_browser_non_apre_nulla(monkeypatch):
    from meshrec.app import finestra
    import threading

    stato = _server_finto(monkeypatch, cli)
    monkeypatch.setattr(finestra, "apri", lambda *a, **k: pytest.fail("non doveva aprire"))
    threading.Timer(0.05, lambda: stato.__setitem__("should_exit", True)).start()
    assert cli.main(["serve", "--port", "0", "--no-browser"]) == 0


def test_se_il_server_non_parte_entro_il_tempo_serve_lo_dice(monkeypatch, capsys):
    import uvicorn

    class ServerCheNonParte:
        def __init__(self, config):
            self.started = False
            self.should_exit = False

        def run(self):
            while not self.should_exit:
                import time
                time.sleep(0.01)

    monkeypatch.setattr(uvicorn, "Server", ServerCheNonParte)
    monkeypatch.setattr(cli, "ATTESA_AVVIO_S", 0.2)
    assert cli.main(["serve", "--port", "0", "--no-browser"]) == 1
    assert "non si è messo in ascolto" in capsys.readouterr().err
```

`--port 0` fa passare il bind di prova su una porta libera qualunque; con il server finto la porta non viene usata. Se `ServerConfig.port` ha `gt=0` (`config.py:1032`), il test deve usare una porta libera vera: sostituire `"0"` con la porta ottenuta come in `test_la_porta_occupata_si_dice_prima_di_annunciare_l_ascolto` (bind su 0, leggi la porta, chiudi).

Run: `uv run pytest tests/test_cli.py -k serve -v` → FAIL.

- [ ] **Step 2: Il parser e il ramo `serve`**

Parser (riga 94-95):

```python
    serve_command.add_argument("--port", type=int, default=None)
    serve_command.add_argument("--no-browser", action="store_true", help="solo il server, nessuna finestra")
    serve_command.add_argument("--browser", action="store_true", help="nel browser di sistema invece che nella finestra (DevTools, debug)")
```

Costante di modulo, accanto agli import: `ATTESA_AVVIO_S = 10.0`.

Il ramo `serve` (`cli.py:222-272`): tenere invariato tutto fino a `prova.close()` compreso; sostituire da `if impostazioni.open_browser and not args.no_browser:` fino a `return 0` con:

```python
        import threading
        import time

        import uvicorn

        from meshrec.app import finestra
        from meshrec.app.server import CACHE_DIR, create_app

        # uvicorn in un thread e il thread principale al guscio: pywebview
        # vuole il thread principale (Cocoa) e uvicorn, fuori da esso, salta
        # da solo i gestori di segnale. `should_exit` lo ferma.
        server = uvicorn.Server(uvicorn.Config(
            create_app(args.config), host=impostazioni.host, port=impostazioni.port, log_level="warning",
        ))
        thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
        thread.start()
        scadenza = time.monotonic() + ATTESA_AVVIO_S
        while not server.started and thread.is_alive() and time.monotonic() < scadenza:
            time.sleep(0.05)
        if not server.started:
            server.should_exit = True
            thread.join(timeout=2)
            print(
                f"il server non si è messo in ascolto su {indirizzo} entro {ATTESA_AVVIO_S:.0f} s. "
                "Rilancia con `--no-browser` per vedere l'errore di uvicorn.",
                file=sys.stderr,
            )
            return 1
        print(f"MeshRec in ascolto su {indirizzo}", file=sys.stderr)
        if args.no_browser or not impostazioni.open_browser:
            thread.join()
            return 0
        modo = finestra.apri(indirizzo, cache=CACHE_DIR.parent, forza_browser=args.browser)
        if modo == "browser":
            # Come prima: il server resta in ascolto finche' Ctrl-C.
            thread.join()
            return 0
        server.should_exit = True
        thread.join(timeout=5)
        return 0
```

`CACHE_DIR` è `Path(".cache/viewport")` (`server.py:66`): il profilo del fallback va in `.cache/finestra`, accanto. `Ctrl-C` nel ramo browser: `thread.join()` in un thread principale riceve `KeyboardInterrupt`; aggiungere `try: thread.join() except KeyboardInterrupt: server.should_exit = True; thread.join(timeout=5)` in entrambi i `join()` senza timeout, altrimenti il processo muore con la traccia.

`socket`, `webbrowser` e `threading.Timer` di prima: togliere `webbrowser` dagli import del ramo (ora sta in `finestra.py`).

- [ ] **Step 3: Test verdi**

Run: `uv run pytest tests/test_cli.py -v` → PASS (anche il test della porta occupata di prima).

- [ ] **Step 4: Prova a mano su macOS**

Run: `uv run meshrec serve` da `/Users/mario/GitHub/Tesi/meshrec`. Expected: finestra «MeshRec» con l'interfaccia, viewport 3D, «Salva immagine» scrive in `immagini/`, chiusura della finestra → il comando torna al prompt con codice 0 e `lsof -i :8765` vuoto. Poi `uv run meshrec serve --browser`: scheda nel browser, Ctrl-C ferma pulito. Poi il link «come citare» dal piè di pagina dentro la finestra: annotare se apre il browser di sistema o resta nella finestra (spec §3: se resta, la riga mostra l'URL come testo).

- [ ] **Step 5: Commit**

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/src/meshrec/cli.py meshrec/tests/test_cli.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(cli): serve apre la finestra e ferma il server alla chiusura"
```

### Task 9: `MeshRec.app`, collegamento Windows, README, prova Windows

**Files:**
- Create: `meshrec/MeshRec.app/Contents/Info.plist`, `meshrec/MeshRec.app/Contents/MacOS/MeshRec` (eseguibile)
- Delete: `meshrec/MeshRec.command`
- Create: `meshrec/crea-collegamento.ps1`
- Modify: `README.md:24-36`, `meshrec/README.md:12-26`
- Create: `docs/prove/2026-09-finestra-windows.md`
- Test: `meshrec/tests/test_bundle.py`

**Interfaces:**
- Consumes: `icona.icns` (Task 4), `icona.ico` (Task 4), `MeshRec.bat` (esistente).

**Dispatch:** coder · sequenziale dopo Task 4 (`icona.icns`), Task 6 e Task 8 (la prova e il README descrivono finestra e piè di pagina); ultimo di PR2 · **gate: Mario** allo Step 4, la PR resta aperta finché `docs/prove/2026-09-finestra-windows.md` non porta l'esito · skill-gate: `ponytail:ponytail` (con `caveman:caveman`; `wizard` non si applica: la prova gira su Windows e il piano chiede una checklist `.md`) · ricerca: `docs/ricerca/2026-09-11-guscio-desktop.md:159-160`, `:76`, `docs/ricerca/2026-09-11-distribuzione-binaria.md:159` · ingressi: spec §3 (bundle, `.ps1`) e §1 (prova Windows)

**Ricerca:** `docs/ricerca/2026-09-11-guscio-desktop.md:159-160` (bundle minimo e `.lnk`), `:76` (la finestra `cmd` accanto alla finestra su Windows resta), `docs/ricerca/2026-09-11-distribuzione-binaria.md:159` (Gatekeeper su Sequoia: Privacy e sicurezza › Apri comunque).

Deviazione dalla spec §3, dichiarata: un `.app` avviato dal Finder **non apre un Terminale**, quindi «la finestra del Terminale che resta aperta» sugli errori non esiste. Gli errori si dicono con un dialogo `osascript` e l'uscita del programma va in `~/Library/Logs/MeshRec.log`.

- [ ] **Step 1: Test che falliscono**

```python
# meshrec/tests/test_bundle.py
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
```

Run: `uv run pytest tests/test_bundle.py -v` → FAIL.

- [ ] **Step 2: Il bundle**

`meshrec/MeshRec.app/Contents/Info.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>MeshRec</string>
  <key>CFBundleDisplayName</key><string>MeshRec</string>
  <key>CFBundleIdentifier</key><string>it.meshrec.app</string>
  <key>CFBundleVersion</key><string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>MeshRec</string>
  <key>CFBundleIconFile</key><string>icona</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
```

`meshrec/MeshRec.app/Contents/MacOS/MeshRec`:

```sh
#!/bin/sh
# Avvio col doppio clic dal Finder (macOS). Sostituisce MeshRec.command.
#
# Un bundle .app non apre il Terminale: la cartella corrente e' la home, nessuno
# legge stdout. Quindi: cd nella cartella del programma (tre livelli sopra il
# bundle), l'uscita nel log dell'utente, e gli errori in un dialogo.
cd "$(dirname "$0")/../../.." || exit 1

PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH
LOG="$HOME/Library/Logs/MeshRec.log"
mkdir -p "$(dirname "$LOG")"

if ! command -v uv >/dev/null 2>&1; then
    osascript -e 'display dialog "uv non trovato. Installalo con:\n\ncurl -LsSf https://astral.sh/uv/install.sh | sh\n\ne riapri MeshRec." with title "MeshRec" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

if ! uv run meshrec serve "$@" >>"$LOG" 2>&1; then
    osascript -e "display dialog \"MeshRec si è fermato con un errore. Le ultime righe sono in:\n$LOG\" with title \"MeshRec\" buttons {\"OK\"} default button 1 with icon stop"
    exit 1
fi
```

Run: `chmod +x /Users/mario/GitHub/Tesi/meshrec/MeshRec.app/Contents/MacOS/MeshRec` e `git -C /Users/mario/GitHub/Tesi rm -q meshrec/MeshRec.command`.

`meshrec/crea-collegamento.ps1`:

```powershell
# Crea «MeshRec» nel menu Start dell'utente, con l'icona, verso MeshRec.bat.
# Si lancia una volta, con il tasto destro > Esegui con PowerShell. Rilanciato,
# sovrascrive il collegamento.
$cartella = Split-Path -Parent $MyInvocation.MyCommand.Path
$shell = New-Object -ComObject WScript.Shell
$destinazione = Join-Path ([Environment]::GetFolderPath('Programs')) 'MeshRec.lnk'
$collegamento = $shell.CreateShortcut($destinazione)
$collegamento.TargetPath = Join-Path $cartella 'MeshRec.bat'
$collegamento.WorkingDirectory = $cartella
$collegamento.IconLocation = Join-Path $cartella 'src\meshrec\ui\icona.ico'
$collegamento.Description = 'MeshRec: dal rilievo fotogrammetrico al modello FEM'
$collegamento.Save()
Write-Host "Collegamento creato: $destinazione"
```

- [ ] **Step 3: README**

`README.md`, righe 34-36 diventano:

```markdown
Si apre in una finestra propria con l'elenco delle corse già eseguite, e la
possibilità di crearne una nuova da un file di punti (`.pcd`, `.ply`, `.xyz`).
Su macOS basta il doppio clic su `meshrec/MeshRec.app` (al primo avvio macOS
chiede di autorizzarlo da Impostazioni di Sistema › Privacy e sicurezza ›
«Apri comunque»); su Windows `meshrec/MeshRec.bat`, e
`meshrec/crea-collegamento.ps1` mette MeshRec nel menu Start con la sua icona.
```

`meshrec/README.md`, righe 14-26: `MeshRec.command` → `MeshRec.app` con le stesse frasi; aggiungere che `--browser` apre nel browser di sistema (DevTools) e che il fallback senza WebView2 è Edge/Chrome in modalità app; il paragrafo su `./MeshRec.command casi/lab_telaio.yaml` diventa `open -a meshrec/MeshRec.app --args casi/lab_telaio.yaml`. Verificare quest'ultimo comando a mano: se `--args` non arriva allo script, togliere la frase.

- [ ] **Step 4: La prova per Windows**

`docs/prove/2026-09-finestra-windows.md`:

```markdown
# Prova della finestra su Windows 11

Da fare sul PC Windows dell'autore, prima di fondere `feat/finestra`.

## Comandi

    cd meshrec
    uv sync
    uv run meshrec serve

## Da guardare, uno alla volta

- [ ] Si apre una finestra con titolo «MeshRec» (non una scheda di Edge).
- [ ] Il viewport 3D di uno step con geometria si vede e ruota.
- [ ] «Sfoglia…» porta il selettore file in primo piano, sopra la finestra.
- [ ] «Salva immagine» scrive in `runs\<corsa>\immagini\` e la riga di esito dice il percorso.
- [ ] «come citare» nel piè di pagina: si apre nel browser di sistema? (sì/no)
- [ ] Chiudere la finestra: il prompt torna, `netstat -ano | findstr :8765` è vuoto.
- [ ] `uv run meshrec serve --browser`: scheda nel browser, Ctrl-C ferma.
- [ ] Se possibile, senza WebView2 (o rinominando temporaneamente la chiave di registro
      `HKCU\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`):
      stderr dice «il runtime WebView2 manca» e si apre Edge in modalità app.
- [ ] `crea-collegamento.ps1` (tasto destro › Esegui con PowerShell): «MeshRec» nel menu Start con l'icona.

## Esito

Data: __________  Windows: __________  WebView2: __________

Note:
```

- [ ] **Step 5: Test verdi, prova a mano, commit**

Run: `uv run pytest tests/test_bundle.py -v` → PASS.
Prova: `open /Users/mario/GitHub/Tesi/meshrec/MeshRec.app` → finestra «MeshRec» nel Dock con l'icona, menu bar «MeshRec»; chiuderla → `lsof -i :8765` vuoto; `~/Library/Logs/MeshRec.log` porta «MeshRec in ascolto su».

```bash
git -C /Users/mario/GitHub/Tesi add meshrec/MeshRec.app meshrec/crea-collegamento.ps1 README.md meshrec/README.md docs/prove/2026-09-finestra-windows.md meshrec/tests/test_bundle.py
git -C /Users/mario/GitHub/Tesi commit -m "feat(avvio): MeshRec.app al posto di MeshRec.command, collegamento Windows, prova da fare"
git -C /Users/mario/GitHub/Tesi push -u origin feat/finestra
```

Round pre-commit in parallelo (`security-reviewer`: sottoprocessi, registro, PowerShell; `code-reviewer`; `test-writer`; `craft-reviewer`: README, piè di pagina, dialoghi; `spec-reviewer` contro §1 e §3). `gh pr create`. **La PR resta aperta finché `docs/prove/2026-09-finestra-windows.md` non porta l'esito.**

---

## PR3 — `chore/identita`

### Task 10: Rename del repository

**Dispatch:** coder · sequenziale, primo di PR3 (ogni task dopo scrive l'URL nuovo) · skill-gate: false — meccanico: `gh repo rename` + `sed` verificato da `grep` a zero righe (resta `caveman:caveman`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:237` · ingressi: spec §4

Nota di dispatch: gli appunti in `~/.claude/projects/` sono fuori repo e li aggiorna il thread principale, non il subagente.

**Files:**
- GitHub: `maeurong/Tesi` → `maeurong/meshrec`
- Modify: ogni file con `maeurong/Tesi` fuori da `docs/ricerca/fonti/` e `.git/` (elenco con il `grep` del passo 1)

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:237` (il record DOI congela il nome: rename prima di Zenodo).

- [ ] **Step 1: Inventario**

Run: `grep -rln "maeurong/Tesi" /Users/mario/GitHub/Tesi --exclude-dir=fonti --exclude-dir=.git --exclude-dir=.venv --exclude-dir=graphify-out`
Expected: l'elenco dei file (al 11/09/2026: 29, fra `docs/`, `meshrec/tests/`, `meshrec/docs/`).

- [ ] **Step 2: Rename su GitHub e remote**

Run: `gh repo rename meshrec --repo maeurong/Tesi --yes`
Run: `gh repo edit maeurong/meshrec --description "MeshRec — dal rilievo fotogrammetrico al modello FEM"`
Run: `git -C /Users/mario/GitHub/Tesi remote set-url origin https://github.com/maeurong/meshrec.git`
Run: `git -C /Users/mario/GitHub/Tesi fetch --dry-run` → nessun errore.

- [ ] **Step 3: Sostituzione**

Run: `grep -rl "maeurong/Tesi" /Users/mario/GitHub/Tesi --exclude-dir=fonti --exclude-dir=.git --exclude-dir=.venv --exclude-dir=graphify-out | xargs sed -i '' 's#maeurong/Tesi#maeurong/meshrec#g'`
Run: `grep -rn "maeurong/Tesi" /Users/mario/GitHub/Tesi --exclude-dir=fonti --exclude-dir=.git --exclude-dir=.venv --exclude-dir=graphify-out | wc -l` → `0`.
Run: `uv run pytest -q` (i test in `test_accenti.py`, `test_guardie_e_nomi.py` e altri citano l'URL nei docstring: devono restare verdi).

- [ ] **Step 4: Commit**

```bash
git -C /Users/mario/GitHub/Tesi add -A
git -C /Users/mario/GitHub/Tesi commit -m "chore(repo): il repository si chiama meshrec, come il programma"
```

Poi aggiornare gli appunti dell'assistente (`~/.claude/projects/-Users-mario/memory/progetto-tesi-meshrec-deck-nudo.md` e affini) con l'URL nuovo: fuori dal repo, ma va fatto nella stessa sessione.

### Task 11: `CITATION.cff`

**Dispatch:** coder · sequenziale dopo Task 10 (`repository-code` porta l'URL nuovo); parallelo con Task 12 · skill-gate: false — contenuto nel piano, validazione `uvx cffconvert --validate` (resta `caveman:caveman`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:91-103`, `:109` · ingressi: spec §4

**Files:**
- Create: `CITATION.cff` (radice del repo)

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:91-103` (formato, un solo file senza `.zenodo.json`), `:109` (la forma della citazione in bibliografia).

- [ ] **Step 1: Il file**

```yaml
cff-version: 1.2.0
message: "Se usi MeshRec in un lavoro, cita il software con questi metadati."
title: "MeshRec"
abstract: >-
  Pipeline riproducibile da nuvola di punti fotogrammetrica a modello a
  elementi finiti di strutture in cemento armato: segmentazione,
  ricostruzione della superficie, riempimento a tetraedri, deck Abaqus.
type: software
authors:
  - family-names: Fiorenzoni
    given-names: Mario
version: 1.0.0
date-released: "2026-09-19"
license: MIT
repository-code: "https://github.com/maeurong/meshrec"
keywords:
  - photogrammetry
  - point cloud
  - finite element mesh
  - reinforced concrete
  - Abaqus
```

`date-released` va riscritta con il giorno del tag (Task 14). Il campo `doi` si aggiunge dopo Zenodo (Task 15).

- [ ] **Step 2: Validazione e commit**

Run: `uvx cffconvert --validate -i /Users/mario/GitHub/Tesi/CITATION.cff` → `Citation metadata are valid according to schema version 1.2.0`.

```bash
git -C /Users/mario/GitHub/Tesi add CITATION.cff
git -C /Users/mario/GitHub/Tesi commit -m "docs(cff): CITATION.cff, il software si cita"
```

### Task 12: `CHANGELOG.md` e versione 1.0.0

**Dispatch:** architect · sequenziale dopo Task 10 (`gh pr list --repo maeurong/meshrec`); parallelo con Task 11 · skill-gate: `documentation` (con `caveman:caveman`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:158`, `:38` · ingressi: nessun ingresso esterno (documento e numero di versione, non codice)

**Files:**
- Create: `CHANGELOG.md` (radice)
- Modify: `meshrec/pyproject.toml:3` (`version = "1.0.0"`), `meshrec/uv.lock` (`uv lock`)

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:158` (Keep a Changelog), `:38` (la pagina «novità» è la prova di vita).

- [ ] **Step 1: Le voci dalle PR**

Run: `gh pr list --repo maeurong/meshrec --state merged --limit 200 --json number,title,mergedAt --jq '.[] | "\(.mergedAt[:10]) #\(.number) \(.title)"' | sort`
Raggruppare per fase (Fase 0 fattibilità, 1-2 pipeline, 3 interfaccia, 4 prior, 5-6 carichi poi tolti, 7 validazione, 8 prior esteso, deck nudo): una riga per PR, in italiano, senza il numero della fase nella voce.

- [ ] **Step 2: Il file**

```markdown
# Changelog

Le versioni di MeshRec, nella forma di [Keep a Changelog](https://keepachangelog.com/it/1.1.0/),
con [versionamento semantico](https://semver.org/lang/it/).

## [Unreleased]

## [1.0.0] — 2026-09-19

Prima versione: quella discussa in sede di tesi.

### Aggiunto
- Pipeline in undici step da nuvola di punti (`.pcd`, `.ply`, `.xyz`) a deck Abaqus `.inp` nudo, con parametri e metriche di ogni step salvati nella corsa.
- Interfaccia locale con viewport 3D, storico con Ctrl+Z, salvataggio delle immagini con cartiglio dei parametri.
- Prior geometrico del telaio (step 12) e geometria STEP dei modelli parametrici.
- Finestra propria (pywebview) con icona, `MeshRec.app` per macOS e collegamento per Windows.
- `CITATION.cff`, `/api/info`, piè di pagina con versione e come citare.
<!-- una riga per PR fusa, dal comando del passo 1 -->

### Rimosso
- Il solutore integrato e le verifiche di norma (2 settembre 2026): l'analisi si fa in Abaqus.
- Materiali, carichi e selettori dal deck (8 settembre 2026): si assegnano in Abaqus/CAE.

[Unreleased]: https://github.com/maeurong/meshrec/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/maeurong/meshrec/releases/tag/v1.0.0
```

Le righe sopra sono l'ossatura: le voci vere vengono dal passo 1, tutte, non un riassunto. Il commento HTML sparisce.

- [ ] **Step 3: Versione e commit**

`pyproject.toml:3` → `version = "1.0.0"`. Run: `uv lock` da `/Users/mario/GitHub/Tesi/meshrec`, poi `uv sync`, poi `uv run python -c "import importlib.metadata as m; print(m.version('meshrec'))"` → `1.0.0`. Aggiornare `CFBundleVersion`/`CFBundleShortVersionString` in `meshrec/MeshRec.app/Contents/Info.plist` se ancora `0.1.0`.

```bash
git -C /Users/mario/GitHub/Tesi add CHANGELOG.md meshrec/pyproject.toml meshrec/uv.lock meshrec/MeshRec.app/Contents/Info.plist
git -C /Users/mario/GitHub/Tesi commit -m "chore(release): CHANGELOG e versione 1.0.0"
```

### Task 13: Screenshot e badge nel README

**Dispatch:** architect · Step 1-2 paralleli con Task 11 e Task 12 (file disgiunti); Step 3 (push, PR) dopo che Task 11 e Task 12 sono committati · skill-gate: `documentation` (con `caveman:caveman`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:170-172`, `:54`, `:58` · ingressi: nessun ingresso esterno (README e un PNG)

Nota di dispatch: lo Step 1 vuole la finestra pywebview a schermo — Mario o il thread principale davanti al Mac.

**Files:**
- Create: `docs/immagini/viewport.png`
- Modify: `README.md:1-14`

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:170-172` (i quattro badge, non di più), `:54` (screenshot del viewer), `:58` (elenco dei formati in/out).

- [ ] **Step 1: Lo screenshot**

Run: `uv run meshrec serve` (finestra pywebview), aprire `geoandgeo-lab-pr2`, uno step con la mesh visibile, la finestra a 1280×800. Run: `screencapture -x -R<x,y,1280,800> /Users/mario/GitHub/Tesi/docs/immagini/viewport.png` con le coordinate della finestra (o `screencapture -w` interattivo con un clic sulla finestra). Peso sotto 1 MB: se serve, `sips -Z 1600 viewport.png`.

- [ ] **Step 2: README**

In testa a `README.md`, dopo `# MeshRec`:

```markdown
[![Release](https://img.shields.io/github/v/release/maeurong/meshrec)](https://github.com/maeurong/meshrec/releases)
[![Licenza MIT](https://img.shields.io/github/license/maeurong/meshrec)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](meshrec/pyproject.toml)

**Dal rilievo fotogrammetrico al modello FEM.** Ingressi: `.pcd`, `.ply`, `.xyz`.
Uscite: deck Abaqus `.inp` e geometria `.step`.

![Il viewport di MeshRec su una corsa del caso studio](docs/immagini/viewport.png)
```

Il badge DOI arriva con Task 15.

- [ ] **Step 3: Commit, PR**

```bash
git -C /Users/mario/GitHub/Tesi add docs/immagini/viewport.png README.md
git -C /Users/mario/GitHub/Tesi commit -m "docs(readme): badge, formati in ingresso e uscita, screenshot del viewport"
git -C /Users/mario/GitHub/Tesi push -u origin chore/identita
```

Round pre-commit: `craft-reviewer` (README, CHANGELOG, CFF), `code-reviewer`, `spec-reviewer` contro §4. `gh pr create`, merge.

### Task 14: Zenodo, tag, release (a mano, con Mario)

**Dispatch:** coder · sequenziale dopo PR3 fusa (Task 13) · **gate: Mario** — toggle Zenodo prima del tag (Step 1) e lettura del DOI dalla pagina Zenodo (Step 3) · skill-gate: false — procedura di cinque righe già nel piano; `wizard` produrrebbe uno script per un interruttore solo (resta `caveman:caveman`) · ricerca: `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:107-109` · ingressi: spec §4

**Files:**
- Create: `docs/prove/2026-09-zenodo.md`
- Modify (dopo): `CITATION.cff` (`date-released`, `doi`), `CHANGELOG.md` (data), `README.md` (badge DOI), `meshrec/src/meshrec/app/info.py` se il DOI va anche lì (no: lo legge dal CFF)

**Ricerca:** `docs/ricerca/2026-09-11-identita-e-autorevolezza.md:107-109` (toggle prima della release, Zenodo legge i metadati al momento della release).

- [ ] **Step 1: La procedura per Mario**

```markdown
# Zenodo: il DOI di MeshRec

Prima del tag `v1.0.0`. Cinque passi, dieci minuti.

1. Apri https://zenodo.org e accedi con «Log in with GitHub» (account `maeurong`).
2. In alto a destra, menu utente › **GitHub**. Compare l'elenco dei tuoi repository.
3. Se `maeurong/meshrec` non c'è, premi **Sync now** in alto a destra.
4. Accanto a `maeurong/meshrec` porta l'interruttore su **ON**.
5. Torna qui e dillo: il tag e la release li faccio io. Zenodo crea il record
   alla release e assegna il DOI in un minuto; il badge compare nella stessa
   pagina di Zenodo, sotto il repository.

Esito: data __________, DOI __________
```

- [ ] **Step 2: Tag e release (a PR3 fusa, dopo il toggle)**

Run: `git -C /Users/mario/GitHub/Tesi checkout main` e `git -C /Users/mario/GitHub/Tesi pull --ff-only`.
Aggiornare `date-released` in `CITATION.cff` e la data in `CHANGELOG.md` al giorno corrente se diverso dal 19/09; commit `chore(release): data della 1.0.0`.
Run: `git -C /Users/mario/GitHub/Tesi tag -a v1.0.0 -m "MeshRec 1.0.0"`
Run: `git -C /Users/mario/GitHub/Tesi push origin main v1.0.0`
Run: `gh release create v1.0.0 --repo maeurong/meshrec --title "MeshRec 1.0.0" --generate-notes --notes-start-tag "" --notes "$(sed -n '/^## \[1.0.0\]/,/^## \[/p' /Users/mario/GitHub/Tesi/CHANGELOG.md | sed '$d')"`
Expected: la pagina della release con le voci del CHANGELOG.

- [ ] **Step 3: Il DOI torna nel repo**

Dopo che Zenodo ha assegnato il DOI (Mario lo legge dalla pagina Zenodo): branch `chore/doi`, in `CITATION.cff` aggiungere `doi: 10.5281/zenodo.NNNNNNN`; in `README.md` sotto gli altri badge `[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.NNNNNNN.svg)](https://doi.org/10.5281/zenodo.NNNNNNN)`. `uv run pytest tests/test_info.py -q`. Commit `docs(doi): il DOI Zenodo della 1.0.0`, PR, merge. Il piè di pagina lo mostra da solo (`/api/info` legge il CFF).

### Task 15: Chiusura

**Dispatch:** thread principale, nessun subagente (`/graphify --update` va lanciato in sessione, gli appunti sono suoi) · sequenziale dopo Task 14 · skill-gate: `graphify`, `superpowers:finishing-a-development-branch` · ricerca: `nessun riferimento pertinente` · ingressi: nessun ingresso esterno

- [ ] `/graphify --update` sul repo (il grafo è committato in `graphify-out/`; docs nuove = costo semantico, da fare o dichiarare).
- [ ] Appunti dell'assistente: URL nuovo, stato delle tre PR, esito della prova Windows.
- [ ] `superpowers:finishing-a-development-branch` per ogni branch fuso.

---

## Autoverifica del piano

**Copertura della spec.** §1 finestra → Task 7-8 (+ prova Windows in Task 9). §2 salvataggio → Task 1-3. §3 icona/bundle/About → Task 4-6, 9. §4 identità → Task 10-14. §5 sequenza e review → intestazioni delle PR e Task 15. Fuori ambito rispettato: nessun watchdog, nessuno spostamento di `runs/`, nessun installer.

**Deviazioni dichiarate.** (a) `immagini/` come file → 400 e non 500 (gestore generico). (b) Le corse in sola lettura accettano le immagini. (c) Il bundle non ha un Terminale: dialogo `osascript` e log in `~/Library/Logs/MeshRec.log`. (d) `/api/info` porta anche `doi_url`, così `app.js` non contiene `https://`.

**Coerenza dei nomi.** `immagini.nome_dell_immagine`, `immagini.decodifica_png`, `immagini.salva`, `immagini.LIMITE_BYTE` (Task 1 ↔ 2). `consegnaImmagine` (Task 3). `info.informazioni` con chiavi `nome, versione, commit, licenza, doi, doi_url, repository` (Task 5 ↔ 6). `finestra.apri(indirizzo, *, cache, forza_browser, avvisa)` → `"finestra" | "app" | "browser"` (Task 7 ↔ 8). `cli.ATTESA_AVVIO_S` (Task 8). `icona-32.png`, `icona.ico`, `icona.icns` (Task 4 ↔ 9).


## Sequenza di dispatch

Tre PR in fila; dentro ogni PR le righe sotto dicono chi parte insieme e chi aspetta. Frecce = «aspetta». Ruolo fra parentesi.

    PR1 feat/salva-immagine-server
      Task 1 (backend-engineer)
        → Task 2 (backend-engineer)
          → Task 3 (frontend-engineer)  → round review, PR

    PR2 feat/finestra — parte quando PR1 è fusa
      onda 1, in parallelo:
        Task 4 (frontend-engineer)  [gate Mario: l'SVG prima dei derivati]
        Task 5 (backend-engineer)
        Task 7 (backend-engineer)
        (4 e 5 aggiungono entrambi in coda a tests/test_server.py: il secondo rilegge prima di scrivere)
      onda 2, in parallelo:
        Task 6 (frontend-engineer)  ← 4, 5
        Task 8 (backend-engineer)   ← 7      [Step 4: finestra a schermo, Mario o thread principale]
      onda 3:
        Task 9 (coder)              ← 4, 6, 8   [gate Mario: esito Windows in docs/prove/, la PR non si fonde senza]
      → round review, PR aperta finché l'esito non c'è

    PR3 chore/identita — parte quando PR2 è fusa
      Task 10 (coder)                          [appunti fuori repo: thread principale]
        → in parallelo: Task 11 (coder), Task 12 (architect), Task 13 Step 1-2 (architect)
                        [Task 13 Step 1: finestra a schermo, Mario o thread principale]
          → Task 13 Step 3 (push, PR)  ← 11, 12   → round review, merge
            → Task 14 (coder)                  [gate Mario: toggle Zenodo prima del tag; poi il DOI letto da Zenodo]
              → Task 15 (thread principale)

Gate umani, tre: Task 4 Step 1 (icona a vista), Task 9 Step 4 (prova Windows), Task 14 Step 1 e 3 (Zenodo). Non sono gate ma servono una persona davanti al Mac: Task 8 Step 4 e Task 13 Step 1.

Skill-gate false, tre, tutti meccanici: Task 10 (rename + sed), Task 11 (CFF dato nel piano, validato da cffconvert), Task 14 (procedura di cinque righe). Ogni brief nomina comunque `caveman:caveman` e, per chi scrive codice, `ponytail:ponytail`.
