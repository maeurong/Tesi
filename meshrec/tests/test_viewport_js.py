"""`ui/viewport.js`: la cucitura con l'interfaccia, e il fantasma.

**Da dove viene questo file, e perche' non e' nuovo.** E' il recupero di
quattro controlli di `tests/test_viewport_js.py` del ramo
`feat/fase-3-5-viewport`, la cui PR #2 e' stata chiusa senza fusione. Quel
file ne aveva diciassette; gli altri tredici sono rimasti sul ramo perche'
sorvegliano funzionalita' che in `main` **non esistono** -- pan col mouse e
da tastiera, guardia di reinquadratura, passo `PASSO_TASTIERA` -- e riscriverli
qui vorrebbe dire scrivere test per codice che nessuno ha scritto. La misura
sta nel corpo della PR che ha portato questo file.

**Perche' serviva un file e non quattro righe in `test_app_js.py`.** Quel banco
sa ritagliare solo funzioni di **primo livello**, e lo dichiara: `test_app_js.py`
annota che `aggiornaCamera` «vive dentro `creaViewport`, che tocca three.js e
non si [esegue]». Cosi' `viewport.js` risulta coperto per le sue funzioni pure
-- `scalaDelCampo`, `numeroDelCampo`, `didascaliaDelCampo`, `frazioneDellArrivo`
-- e **scoperto** per tutto cio' che sta nella chiusura di `creaViewport`, che
e' la scena, la camera e il fantasma. Questi quattro controlli entrano li'.

**Sono asserzioni sul testo, che e' il modo debole**, e vanno prese per quello
che sono: sorvegliano che una riga esista, non eseguono la logica. Il
`viewport.js` di oggi non e' eseguibile da `node` senza un three.js finto, e
costruirne uno per queste quattro righe costerebbe piu' di cio' che rende.
L'unica difesa contro un'asserzione che non salta mai e' mutare il sorgente e
vedere il controllo diventare rosso: le quattro mutazioni che uccidono questi
quattro controlli sono nominate nei rispettivi docstring, e sono state
**eseguite** contro il `viewport.js` di `main`, non ereditate dal ramo.

**Il primo controllo, invece, non e' sul testo in questo senso**: deriva da
`app.js` l'insieme dei comandi che l'interfaccia chiede a `vista` e verifica
che `creaViewport` li offra tutti. Non c'e' alcun elenco scritto a mano, quindi
il giorno che l'interfaccia chiede un comando nuovo il controllo se ne accorge
da solo.
"""

from __future__ import annotations

import re

from meshrec.app.server import UI_DIR


def _modulo() -> str:
    return (UI_DIR / "viewport.js").read_text(encoding="utf-8")


def _senza_commenti(modulo: str) -> str:
    return "\n".join(r for r in modulo.splitlines() if not r.lstrip().startswith("//"))


def _corpo_di(intestazione: str, chiusura: str = "\n  }") -> str:
    """Il corpo di una funzione o di un metodo della chiusura, che non chiude
    in prima colonna e che quindi un ritaglio di primo livello non vede.

    L'intestazione e' un'espressione regolare e non un letterale: scritta a
    lettere fissava anche gli spazi intorno all'`=` di un valore predefinito, e
    riscrivere `facce = null` come `facce=null` -- che non cambia niente di cio'
    che questi controlli sorvegliano -- li faceva saltare tutti insieme.
    """
    testo = _senza_commenti(_modulo())
    trovato = re.search(intestazione, testo)
    assert trovato is not None, f"{intestazione} non e' piu' nel modulo"
    return testo[trovato.end():].split(chiusura, 1)[0]


def _corpo_del_fantasma() -> str:
    """Il corpo di mostraFantasma, dove stanno i due materiali del velo."""
    return _corpo_di(r"mostraFantasma\(vertici, facce\s*=\s*null\) \{", "\n    }")


def test_il_viewport_restituisce_ogni_comando_che_l_interfaccia_gli_chiede():
    """La cucitura fra le due meta', ed e' il punto che nessuno dei due banchi
    guardava: qui si prova che una funzione esiste e che il letterale di ritorno
    la nomina, mentre di la' `vista` e' una finta che quel metodo ce l'ha per
    costruzione. Tolto un nome dal letterale -- `togliFantasma,` o `inquadra,`
    -- tutti e due i banchi restano verdi e il primo clic che ci arriva lancia
    TypeError.

    Derivato e non elencato a mano: un elenco scritto qui diventa la copia di un
    fatto che sta in un altro file, e il giorno che l'interfaccia chiede un
    comando nuovo la copia tace.

    Mutazione che lo uccide, eseguita su `main`: togliere `togliFantasma,` dal
    letterale. Deve essere un comando che `app.js` **chiama davvero**: togliere
    `inquadra,` lascia il controllo verde, e giustamente -- l'interfaccia non lo
    chiama, quindi non e' parte della cucitura che qui si sorveglia. Una
    mutazione mal scelta non prova che il controllo sia inerte.
    """
    testo = _senza_commenti(_modulo())
    assert "\n  return {\n" in testo, (
        "creaViewport non restituisce piu' un oggetto letterale: la cucitura si "
        "guarda altrove"
    )
    letterale = testo.split("\n  return {\n", 1)[1].split("\n  };", 1)[0]
    offerti = set(re.findall(r"^    (\w+)[,(]", letterale, flags=re.MULTILINE))
    app = "\n".join(
        r for r in (UI_DIR / "app.js").read_text(encoding="utf-8").splitlines()
        if not r.lstrip().startswith("//")
    )
    chiesti = set(re.findall(r"\bvista\.(\w+)\(", app))
    assert chiesti, "nessuna chiamata a `vista` in app.js: il banco non guarda piu' niente"
    assert chiesti <= offerti, (
        f"l'interfaccia chiama comandi che il viewport non restituisce, e il "
        f"primo clic che ci arriva lancia TypeError: {sorted(chiesti - offerti)}"
    )


def test_il_fantasma_nasce_fratello_del_gruppo_e_non_figlio():
    """Da figlio di `gruppo` il fantasma finirebbe nel precedente, perche'
    svuota() sposta i figli di `gruppo` invece di distruggerli: ricomparirebbe
    premendo «Confronta», sovrapposto alla geometria di prima, cioe' tre
    geometrie a video mentre la didascalia ne nomina una. E finirebbe anche
    dentro scatolaDelGruppo(), che percorre i figli di `gruppo`: il cursore del
    taglio si tarerebbe sull'unione di due passaggi.

    Mutazione che lo uccide, eseguita su `main`: `scena.add(fantasma)` scritto
    `gruppo.add(fantasma)`.
    """
    testo = _senza_commenti(_modulo())
    assert "scena.add(fantasma);" in testo, (
        "il fantasma non entra nella scena accanto a `gruppo`: da figlio di "
        "`gruppo` svuota() lo sposta nel precedente e «Confronta» lo rimette a "
        "video sopra la geometria di prima"
    )


def test_il_fantasma_se_ne_va_col_passaggio_che_lo_ha_prodotto():
    """togliFantasma libera davvero: togliere un oggetto dalla scena non
    cancella i suoi buffer, sono le chiamate a dispose a farlo. E si chiama in
    testa a svuota(): ogni strada che disegna chiama svuota(), e in coda invece
    che in testa lascerebbe il fantasma sotto la geometria nuova.

    Mutazione che lo uccide, eseguita su `main`: togliere `fantasma = null` dal
    corpo di togliFantasma.
    """
    corpo = _corpo_di(r"function togliFantasma\(\) \{")
    for pezzo in ("geometry.dispose()", "material.dispose()", "scena.remove(fantasma)"):
        assert pezzo in corpo, f"togliFantasma non fa {pezzo}: {corpo}"
    assert "fantasma = null" in corpo, (
        f"togliFantasma non azzera il riferimento: il prossimo disegno lo perde "
        f"sulla scheda invece di sostituirlo: {corpo}"
    )
    svuota = _corpo_di(r"svuota\(\) \{", "\n    }")
    assert "togliFantasma();" in svuota, (
        "svuota() lascia in scena il fantasma del passaggio che si sta lasciando"
    )
    mostra = _corpo_del_fantasma()
    assert "togliFantasma();" in mostra, (
        "mostraFantasma non toglie quello di prima: il vecchio resta in scena e "
        "nessun riferimento lo raggiunge piu'"
    )


def test_il_velo_e_materia_della_stessa_scena_della_geometria():
    """Due righe che nessun conteggio del velo guardava, e sono cio' che lo tiene
    dentro la scena invece che sopra.

    Il piano di taglio: l'elenco e' uno solo e condiviso, e una materia che non
    lo riceve nasce senza taglio. Il velo mostrerebbe la geometria che il taglio
    ha appena tolto, cioe' la vista che contraddice il proprio comando -- sul
    passaggio 9 il taglio serve proprio a guardare dentro.

    E le normali: senza, `MeshStandardMaterial` non ha da che parte sta la
    superficie e il velo esce piatto e nero, che dietro la geometria corrente
    non e' un velo, e' una macchia.

    Mutazione che lo uccide, eseguita su `main`: togliere un
    `clippingPlanes: pianiTaglio,` dai due materiali del velo.
    """
    corpo = _corpo_del_fantasma()
    assert corpo.count("clippingPlanes: pianiTaglio,") == 2, (
        f"una delle due materie del fantasma ignora il piano di taglio, e mostra "
        f"la geometria che il taglio ha tolto: {corpo}"
    )
    assert "computeVertexNormals();" in corpo, (
        f"il velo di una superficie non ha normali: esce piatto e nero invece che "
        f"illuminato come la geometria che sta dietro: {corpo}"
    )
