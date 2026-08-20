"""Il worker esegue uno step in un processo separato e lo puo' terminare."""

from __future__ import annotations

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
