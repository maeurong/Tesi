"""Il worker esegue uno step in un processo separato e lo puo' terminare."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from meshrec.app.worker import Worker
from meshrec.core.config import InputConfig, PipelineConfig, save_config
from materiale import ANALISI


def test_un_worker_appena_creato_non_sta_girando():
    assert Worker().is_running() is False


def test_il_worker_cattura_le_righe_del_processo(tmp_path):
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    lavoratore.start(percorso, 1, 1)
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False
    # La nuvola non esiste: il processo esce con codice diverso da zero e la
    # riga d'errore e' catturata. Fallire e' un esito, non un'eccezione.
    assert lavoratore.exit_code != 0
    assert any("ValueError" in riga or "nessun punto" in riga for riga in lavoratore.righe())


def test_il_tempo_trascorso_lo_misura_il_worker_e_finisce_con_lo_step(tmp_path):
    """Il cronometro deve stare dove lo step parte davvero: misurato nel
    browser conterebbe da quando quella pagina ha visto lo stato 'in corso',
    e tornerebbe a zero a ogni ricarica mentre il calcolo prosegue."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    assert lavoratore.da_secondi() is None
    lavoratore.start(percorso, 1, 1)
    assert lavoratore.is_running() is True
    trascorsi = lavoratore.da_secondi()
    assert trascorsi is not None and trascorsi >= 0.0
    # Il discriminante fra i due orologi, senza orologi finti: time.monotonic
    # conta dall'avvio della macchina, time.time dal 1970, e i due valori non
    # possono essere vicini. Senza questa riga, sostituire monotonic con time
    # lascerebbe la suite verde e riporterebbe il difetto che monotonic evita:
    # un orologio di sistema che salta all'indietro da' un tempo negativo.
    assert abs(lavoratore.avviato - time.time()) > 1e6

    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False
    assert lavoratore.da_secondi() is None


def test_annullare_un_worker_fermo_non_solleva():
    assert Worker().cancel() is False


def test_il_worker_esegue_anche_un_comando_che_non_e_uno_step(tmp_path):
    """Il prior e i modelli sono azioni, non step: passano dallo stesso
    sottoprocesso -- perche' e' il percorso con cui sono stati prodotti tutti i
    numeri delle Fasi 1 e 2 -- ma non hanno un numero di step."""
    lavoratore = Worker()

    lavoratore.start_comando(["--version"], etichetta="prova")
    for _ in range(200):
        if not lavoratore.is_running():
            break
        time.sleep(0.05)

    assert lavoratore.step is None
    assert lavoratore.etichetta == "prova"
    assert lavoratore.exit_code is not None


def test_avviare_un_secondo_step_mentre_il_primo_gira_solleva(tmp_path):
    """E' un errore del chiamante, non un esito dell'elaborazione: la nuvola
    assente tiene comunque il processo in volo abbastanza a lungo (avvio
    dell'interprete) da coglierlo con is_running() subito dopo lo start."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    lavoratore.start(percorso, 1, 1)
    assert lavoratore.is_running() is True
    with pytest.raises(RuntimeError):
        lavoratore.start(percorso, 1, 1)

    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False


def _fino_alla_fine(lavoratore: Worker) -> None:
    """Aspetta due cose, non una: che il processo esca e che il lettore chiuda.

    `is_running()` guarda il processo; `exit_code` lo fissa il thread lettore
    dopo l'ultima riga. Fermarsi alla prima attesa coglierebbe `exit_code`
    ancora `None` anche quando il lettore sta per fissarlo un istante dopo --
    e' la finestra gia' nota fra «non in corso» e «codice d'uscita», e qui
    andrebbe scambiata per il difetto che questi test sorvegliano.

    I due budget sono diversi apposta: l'uscita del processo paga l'avvio
    dell'interprete e l'import di open3d, la chiusura del lettore no. Cinque
    secondi dopo l'uscita del figlio, un `exit_code` ancora assente non e'
    lentezza: e' un lettore morto.
    """
    scadenza = time.monotonic() + 60.0
    while lavoratore.is_running() and time.monotonic() < scadenza:
        time.sleep(0.05)
    scadenza = time.monotonic() + 5.0
    while lavoratore.exit_code is None and time.monotonic() < scadenza:
        time.sleep(0.05)


def _eccezioni_dei_thread(monkeypatch) -> list[str]:
    """Le eccezioni uscite da un thread, raccolte invece che stampate.

    `_leggi` gira in un thread demone: un'eccezione la' dentro non fa fallire
    nessun test da se' -- `threading.excepthook` la scrive sullo stderr del
    processo di prova e il thread muore in silenzio. Senza questa raccolta il
    solo sintomo visibile sarebbe un `exit_code` mai fissato, e il test
    direbbe «manca il codice d'uscita» invece di «il lettore e' morto qui».
    """
    fuori: list[str] = []
    monkeypatch.setattr(
        threading,
        "excepthook",
        lambda arg: fuori.append(f"{arg.exc_type.__name__}: {arg.exc_value}"),
    )
    return fuori


def test_una_riga_non_decodificabile_non_uccide_il_lettore(tmp_path, monkeypatch):
    """Un byte che la codifica del lettore non regge non deve fermare la corsa.

    Riproduce il guasto visto su Windows -- «UnicodeDecodeError: 'utf-8' codec
    can't decode byte 0xe0 in position 79: invalid continuation byte» cliccando
    «Esegui step» sullo step 1 -- senza una macchina Windows, forzando la sola
    condizione che lo produce: i due capi del tubo non concordano sulla
    codifica. Il figlio scrive latin-1 (`PYTHONIOENCODING`), dove `à` e' il
    byte 0xE0; il genitore legge con la codifica di locale, perche' i due
    `subprocess.Popen` di `worker.py` passano `text=True` senza dichiarare
    ne' `encoding=` ne' `errors=`. Su questa macchina quella codifica e'
    UTF-8, e 0xE0 da solo non e' UTF-8 valido.

    L'accento sta nel percorso della nuvola e in quello della configurazione,
    che e' da dove il byte arriva davvero: la riga che lo step 1 stampa quando
    il file di punti non si apre lo nomina per intero.

    Le tre asserzioni sono un solo difetto guardato da tre lati, e servono
    tutte: senza la prima il test direbbe «manca il codice d'uscita» senza
    dire perche'; senza la seconda un lettore morto resterebbe indistinguibile
    da una corsa lenta; senza la terza passerebbe un rimedio che tiene in vita
    il thread ma butta via la riga.

    Mutazione che lo uccide: togliere `errors=` (o l'accordo sulla codifica)
    dai `Popen` di `worker.py:78` e `worker.py:114` lo riporta rosso.
    """
    fuori = _eccezioni_dei_thread(monkeypatch)
    monkeypatch.setenv("PYTHONIOENCODING", "latin-1")

    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "città.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "configurazione già scelta.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    lavoratore.start(percorso, 1, 1)
    _fino_alla_fine(lavoratore)

    assert fuori == []
    assert lavoratore.exit_code is not None
    # O l'accento e' arrivato intatto (i due capi si sono accordati), o e'
    # diventato un carattere di sostituzione (il lettore ha tirato dritto):
    # tutte e due sono esiti buoni, perche' la riga c'e'. Perderla non lo e'.
    assert any(".ply" in riga for riga in lavoratore.righe())


def test_un_accento_italiano_vero_arriva_integro_al_registro(tmp_path):
    """Con i due capi d'accordo, `à` resta `à`: non mojibake, non `?`.

    Gemello del test qui sopra e suo contrappeso: quello pretende che una riga
    illeggibile non fermi la corsa, questo che il rimedio non si prenda quella
    licenza sempre. Un `Popen` con `errors="replace"` e una codifica sbagliata
    -- ASCII, o latin-1 contro un figlio che scrive UTF-8 -- soddisfa il primo
    e fallisce questo, perche' consegna al registro una riga leggibile e
    sbagliata. Gli accenti veri nelle stringhe mostrate all'utente sono una
    regola dichiarata del progetto (vedi `tests/test_accenti.py`), e il
    registro e' mostrato all'utente.

    Mutazione che lo uccide: `encoding="ascii"` (o qualunque codifica che non
    porti gli accenti) sui `Popen` di `worker.py`.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "più_città.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    lavoratore.start(percorso, 1, 1)
    _fino_alla_fine(lavoratore)

    assert lavoratore.exit_code is not None
    assert any("più_città.ply" in riga for riga in lavoratore.righe())


def test_una_riga_vuota_del_sottoprocesso_non_e_un_guasto(tmp_path, monkeypatch):
    """Riga vuota: nessuna eccezione, e il codice d'uscita resta quello vero.

    `--help` ne stampa quattro, ed esce con zero. Sorveglia il rimedio piu'
    che il difetto: un lettore riscritto per sopravvivere ai byte storti puo'
    finire per saltare, contare o rifiutare le righe vuote, e allora una corsa
    riuscita si annuncerebbe fallita.

    Mutazione che lo uccide: in `_leggi`, saltare le righe che dopo
    `rstrip("\\n")` sono vuote, oppure trattarle come fine del flusso.
    """
    fuori = _eccezioni_dei_thread(monkeypatch)

    lavoratore = Worker()
    lavoratore.start_comando(["--help"], etichetta="aiuto")
    _fino_alla_fine(lavoratore)

    assert fuori == []
    assert lavoratore.exit_code == 0
    assert "" in lavoratore.righe()
