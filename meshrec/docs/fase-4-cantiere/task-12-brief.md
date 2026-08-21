> ## LEGGI QUESTO PRIMA DEL RESTO — correzioni vincolanti del 20/08/2026
>
> Il corpo del brief qui sotto e' la prima stesura. Contiene **due difetti
> bloccanti**, uno serio e due minori, e non conosce il lavoro fatto oggi nei
> Task 8 e 10. Dove questa sezione e il corpo divergono, **vale questa**.
>
> Ogni affermazione qui e' stata riletta nel codice, con file e riga. Se una ti
> risulta falsa, **fermati e dillo con la prova** invece di adattare il codice
> per farla tornare: in questa fase e' successo otto volte che avesse ragione
> chi eseguiva e non chi scriveva il piano.
>
> ### D1 (BLOCCANTE) — `_numero` solleva su `None`, e i modelli parametrici ne producono
>
> Il corpo scrive `_numero(confronto[grandezza][nome]) if nome in confronto[grandezza] else 'non generato'`.
> La guardia distingue **chiave assente** da chiave presente — ma una chiave
> presente e valorizzata `None` passa la guardia e finisce dentro `_numero`, che
> comincia con `math.isnan(valore)` e su `None` solleva
> `TypeError: must be real number, not NoneType`.
>
> `report._testo` (`report.py:287-297`) sa gia' che farne: `None` diventa
> `NON_IMPOSTATO`. Usa quello, e lascia `_numero` ai numeri:
>
> ```python
>         celle = "".join(
>             f"<td>{'non generato' if nome not in confronto[grandezza] else _testo(confronto[grandezza][nome])}</td>"
>             for nome in MODELLI
>         )
> ```
>
> ### D2 (era BLOCCANTE, ora **chiuso a monte**) — `scostamento_nuvola` adesso esiste
>
> Il corpo dichiara `quality.vertex_deviation` fra le dipendenze e poi non la
> chiama mai, lasciando vuota la colonna che lui stesso chiama «il perno» del
> confronto. Il calcolo **e' stato aggiunto al Task 10**: `pipeline.genera_modello`
> scrive `scostamento_nuvola` con `rms`, `max` e una nota in `modello.json`.
>
> Quindi tu **leggi e basta**, come il brief dice di fare («Non ricalcola
> nulla»), e `vertex_deviation` sparisce dalle tue dipendenze: non la chiami.
>
> Ma il banco finto va allineato, o il test non vedrebbe la colonna sparire:
>
> ```python
>                     "scostamento_nuvola": {"rms": 6.2, "max": 21.0, "nota": ""},
> ```
>
> con un'asserzione esplicita nel primo test:
> `assert confronto["scostamento_nuvola"]["estruso"] is not None`.
>
> **La guardia di D1 serve lo stesso**, e non e' ridondante: protegge dal caso in
> cui un `modello.json` piu' vecchio, o generato da una versione precedente, non
> porti la chiave.
>
> ### D3 (SERIO) — la colonna dei tetraedri ha il nome di un'altra cosa
>
> Il corpo scrive `qualita[nome] = {"min_ratio": volumi.get("radius_edge_ratio")}`.
> **`quality.volume_metrics` non ha alcuna chiave `min_ratio`**: le sue chiavi
> sono `nodes`, `tets`, `inverted`, `total_volume`, `element_volume`,
> `min_dihedral_deg`, `aspect_ratio`, `radius_edge_ratio`,
> `radius_edge_over_reference`, `reference_ratio` (`quality.py:353-362`).
>
> In questo progetto `min_ratio` e' un **ingresso** di TetGen — il vincolo che si
> chiede, `cfg.tet.min_ratio` — non una misura. Chiamare cosi' la distribuzione
> misurata mette nella tabella del confronto un nome che altrove significa
> un'altra cosa, ed e' esattamente l'errore che questo task esiste per evitare.
>
> Usa il nome vero **ovunque** — codice, docstring di `CONFRONTABILI`, entrambi i
> test:
>
> ```python
>             qualita[nome] = {"radius_edge_ratio": volumi.get("radius_edge_ratio")}
> ```
>
> e nella docstring: «Rapporto raggio-spigolo per i tetraedri
> (`radius_edge_ratio`, la misura; `tet.min_ratio` e' invece il vincolo chiesto a
> TetGen), Jacobiano scalato per gli esaedri: due colonne separate, mai una
> differenza.»
>
> ### D4 (MINORE) — due asserzioni che non possono fallire
>
> `assert "differenza" not in qualita` non puo' fallire: `qualita` e' indicizzato
> per nome di modello, e una differenza finirebbe **dentro** una voce, non
> accanto. Cercala dove finirebbe davvero:
>
> ```python
>     for colonna in qualita.values():
>         assert not (set(colonna) & {"differenza", "delta", "scarto"}), (
>             "il rapporto raggio-spigolo e il Jacobiano scalato non si sottraggono"
>         )
>     assert set(qualita["estruso"]) & set(qualita["as-built"]) == set()
> ```
>
> Le quattro asserzioni su `confronto["confrontabili"]` rileggono la costante
> `CONFRONTABILI` che il codice ha appena copiato: nessuna mutazione del
> **calcolo** le uccide. Tienile — sorvegliare una dichiarazione e' legittimo —
> ma **dillo nella docstring del test**: «sorveglia la costante, non un calcolo»,
> cosi' nessuno le scambia per una verifica di comportamento.
>
> ### D5 (MINORE) — `from tests.test_report import ...` non risolve
>
> `tests/` non e' un pacchetto: non c'e' `__init__.py`, ed e' `tests/` stessa a
> finire su `sys.path`. Il corpo lo dichiara come rischio e propone un ripiego:
> **prendi subito il ripiego** — `_tre_cartelle_finte` va in `tests/materiale.py`,
> accanto a `crea_config`, che entrambi i file importano gia' per nome semplice.
>
> ### D6 (NUOVO — non era nel corpo perche' non esisteva ancora)
>
> Il Task 8 ha chiuso con un limite noto, misurato e dichiarato, e **il confronto
> deve portarlo** o attribuira' alla geometria una differenza che viene dal
> vincolo.
>
> `modello.json` porta oggi, dentro `modello` (cioe' le metriche di
> `hexa.costruisci`), quattro numeri che devono comparire nel rapporto accanto al
> confronto:
>
> - `giunzioni` e `ties` — le giunzioni geometriche tagliate contro i vincoli
>   effettivamente scritti nel deck. **Sono due numeri diversi e restano tali**:
>   non sommarli, non farne un rapporto.
> - `nodi_dipendenti_legati` e `nodi_dipendenti_totali` — quanti nodi della
>   superficie dipendente il solutore riesce davvero a vincolare. Sul telaio di
>   prova il secondo e' maggiore del primo.
>
> Perche' contano: un modello parametrico con parte dei giunti non vincolati e'
> **piu' cedevole del vero**, e chi legge il confronto deve poter distinguere
> quella cedevolezza da quella geometrica. E' un limite noto della mesh non
> conforme fra blocchi, gia' misurato col solutore vero.
>
> Il modello as-built non ha ne' giunzioni ne' `*TIE`: e' monolitico. Nella
> tabella quelle righe valgono «non applicabile» per lui, che **non e' la stessa
> cosa** di «non generato» ne' di zero.
>
> Il testo dell'avvertenza non lo scrivi tu: `modello.json` porta gia'
> `nota_giunzioni`, scritta dal Task 10. Leggila e riportala.
>
> ---

## Task 12: il confronto — quasi nessuna metrica e' confrontabile, e la tabella dice quale lo e'

**Files:**
- Modify: `src/meshrec/core/report.py`
- Modify: `src/meshrec/cli.py`
- Test: `tests/test_report.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `pipeline.WALL_FILENAME`, `pipeline.MODEL_FILENAME` (Task 9 e 10); `quality.vertex_deviation` (Fase 3).
- Produces:
  - `report.CONFRONTABILI: dict[str, bool]`.
  - `report.confronta(cartelle) -> dict[str, object]`.
  - `report.write_comparison_report(cartelle, out_path) -> Path`.
  - Comando `meshrec compare <cartella>... --out <file.html>`.

- [ ] **Step 1: I test del confronto**

In coda a `tests/test_report.py`:

```python
def test_il_confronto_di_tre_modelli_dice_quali_grandezze_lo_sono(tmp_path):
    """Quasi nessuna metrica e' confrontabile fra i tre modelli senza mentire.
    La tabella deve dire quale lo e', invece di allineare colonne che non si
    parlano."""
    cartelle = _tre_cartelle_finte(tmp_path)

    confronto = report.confronta(cartelle)

    assert set(confronto["modelli"]) == {"as-built", "estruso", "primitive"}
    assert confronto["confrontabili"]["volume"] is True
    assert confronto["confrontabili"]["scostamento_nuvola"] is True
    assert confronto["confrontabili"]["qualita_elementi"] is False
    assert confronto["confrontabili"]["rigidezza"] is False


def test_la_qualita_degli_elementi_sta_in_due_colonne_e_mai_in_una_differenza(tmp_path):
    """min_ratio per i tetraedri, Jacobiano scalato per gli esaedri: due
    colonne separate, mai una differenza fra le due."""
    cartelle = _tre_cartelle_finte(tmp_path)

    confronto = report.confronta(cartelle)

    qualita = confronto["qualita"]
    assert "min_ratio" in qualita["as-built"]
    assert "scaled_jacobian" in qualita["estruso"]
    assert "min_ratio" not in qualita["estruso"]
    assert "differenza" not in qualita


def test_con_due_modelli_su_tre_il_confronto_dice_quale_manca(tmp_path):
    """Nessuna colonna con un trattino che somigli a un valore, nessuna
    differenza calcolata contro un modello assente."""
    cartelle = _tre_cartelle_finte(tmp_path)[:2]

    confronto = report.confronta(cartelle)

    assert confronto["mancanti"] == ["primitive"]
    assert "primitive" not in confronto["volume"]
    testo = report.write_comparison_report(cartelle, tmp_path / "confronto.html").read_text(
        encoding="utf-8"
    )
    assert "primitive" in testo
    assert "non generato" in testo


def test_con_un_modello_solo_il_confronto_diventa_una_scheda_e_lo_dichiara(tmp_path):
    cartelle = _tre_cartelle_finte(tmp_path)[:1]

    confronto = report.confronta(cartelle)

    assert confronto["scheda_singola"] is True
    testo = report.write_comparison_report(cartelle, tmp_path / "solo.html").read_text(
        encoding="utf-8"
    )
    assert "scheda singola" in testo


def test_il_report_dichiara_le_tre_cose_che_non_derivano_dalla_geometria(tmp_path):
    """Senza queste righe una differenza nata dal *TIE verrebbe letta come
    effetto della forma, la base sembrerebbe una faccia del pezzo e il modello
    passerebbe per un telaio in cemento armato completo."""
    cartelle = _tre_cartelle_finte(tmp_path)

    testo = report.write_comparison_report(cartelle, tmp_path / "confronto.html").read_text(
        encoding="utf-8"
    )

    assert "as-built monolitico" in testo
    assert "vincolati alle giunzioni" in testo
    assert "armatura" in testo
    assert "dove abbiamo tagliato" in testo
```

Scrivi anche l'aiuto `_tre_cartelle_finte(tmp_path)`, in testa alla sezione nuova del file di test:

```python
def _tre_cartelle_finte(tmp_path):
    """Tre cartelle di corsa con i soli file che il confronto legge.

    Il confronto non ricalcola nulla: legge metrics.json, 12_wall.json e
    modello.json. Un banco che scrive quei tre file esercita esattamente il
    codice sotto prova, senza far girare la pipeline per ogni test.
    """
    import json

    from meshrec.core import pipeline

    cartelle = []
    for nome, tipo in (("madre", None), ("madre-estruso", "estruso"), ("madre-primitive", "primitive")):
        cartella = tmp_path / nome
        cartella.mkdir()
        metriche = {
            "07_surface_quality": {"geometric_error": {"cloud_to_mesh": {"rms": 4.9}}},
            "10_volume_quality": {
                "total_volume": 1.0e8,
                "radius_edge_ratio": {"p50": 1.4},
                "nodes": 1000,
            },
            "11_export": {"volume": 1.0e8, "mass": 0.25, "node_sets": {"BASE": 40}},
        }
        (cartella / "metrics.json").write_text(json.dumps(metriche), encoding="utf-8")
        if tipo is None:
            (cartella / pipeline.WALL_FILENAME).write_text(
                json.dumps({
                    "regioni_trovate": 4,
                    "membrature": [],
                    "scartate": [],
                    "chiusura_volume": {"somma": 1.0e8, "unione": 1.0e8,
                                         "scarto_relativo": 0.0, "passato": True,
                                         "soglia": 0.02, "passo": 20.0, "spiegazione": ""},
                    "riscontri": {"membrature_attese": None, "scarto_membrature": None,
                                   "sezioni_nominali": None, "volume_atteso": None,
                                   "scarto_volume": None, "nota": ""},
                }),
                encoding="utf-8",
            )
        else:
            (cartella / pipeline.MODEL_FILENAME).write_text(
                json.dumps({
                    "tipo": tipo,
                    "sorgente": str(tmp_path / "madre"),
                    "modello": {"tipo": tipo, "membrature": 4, "giunzioni": 3,
                                 "element_type": "C3D8I", "vincolo_giunzioni": ""},
                    "hexa": {"hexes": 5000, "nodes": 7000, "inverted": 0,
                              "total_volume": 0.98e8,
                              "scaled_jacobian": {"p50": 0.95, "min": 0.61}},
                    "export": {"volume": 0.98e8, "mass": 0.245, "element_type": "C3D8I"},
                }),
                encoding="utf-8",
            )
        cartelle.append(cartella)
    return cartelle
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `uv run pytest tests/test_report.py -k "confronto or qualita or scheda or non_derivano" -v`
Expected: FAIL con `AttributeError: module 'meshrec.core.report' has no attribute 'confronta'`.

- [ ] **Step 3: `confronta`**

In `report.py`, in coda:

```python
MODELLI = ("as-built", "estruso", "primitive")
"""I tre modelli dello stesso pezzo, nell'ordine in cui il confronto li mostra.

as-built e' la corsa madre e c'e' sempre: e' la superficie rilevata in mesh
tetraedrica, che esiste dalla Fase 1. Gli altri due sono corse figlie e possono
mancare.
"""

CONFRONTABILI: dict[str, bool] = {
    "volume": True,
    "massa": True,
    "scostamento_nuvola": True,
    "gradi_di_liberta": True,
    "qualita_elementi": False,
    "rigidezza": False,
}
"""Quali grandezze si confrontano fra i tre modelli senza mentire.

- volume e massa: si', ed e' anche il confronto con il volume dichiarato dal
  disegno, quando il disegno c'e';
- scostamento dalla nuvola sorgente: si', ed e' il perno -- e' definito allo
  stesso modo per tutti e tre e risponde alla domanda vera, quanto costa in
  fedelta' al rilievo la regolarizzazione della forma;
- numero di nodi e gradi di liberta': si', ma solo accanto al tipo di elemento,
  perche' un C3D8I e un C3D4 non spendono lo stesso per nodo;
- qualita' degli elementi: NO. min_ratio per i tetraedri, Jacobiano scalato per
  gli esaedri: due colonne separate, mai una differenza fra le due;
- rigidezza e spostamenti: NO. Nessun solutore in questa fase.
"""

NOTE_NON_GEOMETRICHE = (
    "as-built monolitico, parametrici vincolati alle giunzioni con *TIE: e' una "
    "differenza fra i modelli che non deriva dalla geometria, e senza questa riga "
    "una differenza di rigidezza nata dal vincolo verrebbe letta come effetto "
    "della forma.",
    "Nessuna armatura in alcun modello: calcestruzzo omogeneo. E' una scelta "
    "dell'autore e non una dimenticanza, e il dato delle barre resta nel disegno. "
    "Un telaio in cemento armato modellato senza armatura non e' il telaio vero.",
    "Il set BASE non e' una faccia del pezzo: e' la quota di taglio scelta "
    "dall'operatore. Quella superficie non esiste nel pezzo vero, e' dove abbiamo "
    "tagliato.",
)


def _legge_json(percorso: Path) -> dict | None:
    try:
        with percorso.open(encoding="utf-8") as handle:
            letto = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return letto if isinstance(letto, dict) else None


def confronta(cartelle: list[Path]) -> dict[str, object]:
    """Il confronto fra i modelli **generati**, e la dichiarazione di quelli assenti.

    Regge gli insiemi parziali perche' l'utente sceglie quali modelli generare:
    con due su tre confronta due modelli e dice quale manca, con uno solo
    diventa una scheda singola e lo dichiara. Nessuna colonna con un trattino
    che somigli a un valore, nessuna differenza calcolata contro un modello
    assente.

    Non ricalcola nulla: legge cio' che ogni corsa ha scritto. Ricalcolare
    darebbe numeri che nessun artefatto sostiene.
    """
    presenti: dict[str, dict] = {}
    for cartella in cartelle:
        percorso = Path(cartella)
        modello = _legge_json(percorso / "modello.json")
        metriche = _legge_json(percorso / METRICS_FILENAME) or {}
        if modello is None:
            presenti["as-built"] = {"cartella": percorso, "metriche": metriche, "modello": None}
        else:
            presenti[str(modello.get("tipo"))] = {
                "cartella": percorso, "metriche": metriche, "modello": modello
            }

    mancanti = [nome for nome in MODELLI if nome not in presenti]

    volume: dict[str, float] = {}
    massa: dict[str, float] = {}
    scostamento: dict[str, object] = {}
    gradi: dict[str, object] = {}
    qualita: dict[str, dict] = {}
    for nome, voce in presenti.items():
        if voce["modello"] is None:
            export = voce["metriche"].get("11_export", {})
            volumi = voce["metriche"].get("10_volume_quality", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = (
                voce["metriche"]
                .get("07_surface_quality", {})
                .get("geometric_error", {})
                .get("cloud_to_mesh", {})
                .get("rms")
            )
            gradi[nome] = {"nodi": volumi.get("nodes"), "elemento": export.get("element_type", "C3D4")}
            qualita[nome] = {"min_ratio": volumi.get("radius_edge_ratio")}
        else:
            export = voce["modello"].get("export", {})
            esaedri = voce["modello"].get("hexa", {})
            volume[nome] = export.get("volume")
            massa[nome] = export.get("mass")
            scostamento[nome] = voce["modello"].get("scostamento_nuvola")
            gradi[nome] = {"nodi": esaedri.get("nodes"), "elemento": export.get("element_type")}
            qualita[nome] = {"scaled_jacobian": esaedri.get("scaled_jacobian")}

    return {
        "modelli": sorted(presenti),
        "mancanti": mancanti,
        "scheda_singola": len(presenti) == 1,
        "confrontabili": dict(CONFRONTABILI),
        "volume": volume,
        "massa": massa,
        "scostamento_nuvola": scostamento,
        "gradi_di_liberta": gradi,
        "qualita": qualita,
        "note_non_geometriche": list(NOTE_NON_GEOMETRICHE),
    }
```

- [ ] **Step 4: `write_comparison_report`**

In coda a `report.py`:

```python
def write_comparison_report(cartelle: list[Path], out_path: Path) -> Path:
    """Il confronto in una pagina, con lo stesso rivestimento del report di corsa.

    I modelli assenti compaiono per nome e con la dicitura «non generato», mai
    con un trattino in una colonna di numeri: un trattino in mezzo ai numeri
    somiglia a un valore.
    """
    confronto = confronta(cartelle)
    righe = []
    for grandezza in ("volume", "massa", "scostamento_nuvola"):
        celle = "".join(
            f"<td>{_numero(confronto[grandezza][nome]) if nome in confronto[grandezza] else 'non generato'}</td>"
            for nome in MODELLI
        )
        righe.append(f"<tr><th>{grandezza}</th>{celle}</tr>")

    qualita_righe = "".join(
        f"<tr><th>{nome}</th><td>{_testo(confronto['qualita'].get(nome, 'non generato'))}</td></tr>"
        for nome in MODELLI
    )
    note = "".join(f"<li>{nota}</li>" for nota in confronto["note_non_geometriche"])
    intestazione = "".join(f"<th>{nome}</th>" for nome in MODELLI)
    avviso = (
        "<p class='avviso'>Un solo modello generato: questa non e' una tabella di "
        "confronto ma una <strong>scheda singola</strong>.</p>"
        if confronto["scheda_singola"]
        else ""
    )

    pagina = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>MeshRec -- confronto fra modelli</title>
<style>{_STILE}</style></head><body>
<h1>Confronto fra modelli</h1>
{avviso}
<h2>Grandezze confrontabili</h2>
<table><thead><tr><th></th>{intestazione}</tr></thead><tbody>{''.join(righe)}</tbody></table>
<h2>Qualita' degli elementi: due colonne, mai una differenza</h2>
<p>min_ratio vale per i tetraedri, il Jacobiano scalato per gli esaedri. Non sono
la stessa grandezza e la loro differenza non e' un numero.</p>
<table><tbody>{qualita_righe}</tbody></table>
<h2>Che cosa non deriva dalla geometria</h2>
<ul>{note}</ul>
<h2>Che cosa questa fase non dice</h2>
<p>Nessun solutore e' stato eseguito: rigidezza e spostamenti non sono in questa
pagina perche' non sono stati calcolati, non perche' siano stati omessi.</p>
</body></html>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(pagina, encoding="utf-8")
    return Path(out_path)
```

- [ ] **Step 5: Eseguire**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS.

- [ ] **Step 6: Il comando `compare`**

In `_build_parser`:

```python
    compare_command = commands.add_parser(
        "compare", help="confronta le cartelle dei modelli generati dello stesso pezzo"
    )
    compare_command.add_argument("cartelle", type=Path, nargs="+")
    compare_command.add_argument("--out", type=Path, required=True)
```

In `main`:

```python
    if args.command == "compare":
        from meshrec.core import report

        try:
            percorso = report.write_comparison_report(args.cartelle, args.out)
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
        print(f"confronto in {percorso}")
        return 0
```

- [ ] **Step 7: Il test del comando, eseguire, commit**

In coda a `tests/test_cli.py`:

```python
def test_il_comando_compare_scrive_la_pagina_e_nomina_i_modelli_assenti(tmp_path, capsys):
    from tests.test_report import _tre_cartelle_finte  # stesso banco, una definizione sola

    cartelle = _tre_cartelle_finte(tmp_path)[:2]
    uscita = tmp_path / "confronto.html"

    assert cli.main(["compare", *[str(c) for c in cartelle], "--out", str(uscita)]) == 0
    assert "non generato" in uscita.read_text(encoding="utf-8")
    assert str(uscita) in capsys.readouterr().out
```

Se l'import da `tests.test_report` non risolve nella configurazione di pytest del progetto, sposta `_tre_cartelle_finte` in `tests/materiale.py` accanto a `crea_config` e importalo da li' in entrambi i file: una definizione sola resta il requisito.

Run: `uv run pytest tests -q --ignore=tests/feasibility`
Expected: PASS.

```bash
git add meshrec/src/meshrec/core/report.py meshrec/src/meshrec/cli.py meshrec/tests/test_report.py meshrec/tests/test_cli.py meshrec/tests/materiale.py
git commit -m "feat(fase-4): confronto fra modelli, insiemi parziali compresi"
```

---

