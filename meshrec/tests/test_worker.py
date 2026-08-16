"""Il worker esegue uno step in un processo separato e lo puo' terminare."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from meshrec.app.worker import Worker
from meshrec.core.config import InputConfig, PipelineConfig, save_config


def test_un_worker_appena_creato_non_sta_girando():
    assert Worker().is_running() is False


def test_il_worker_cattura_le_righe_del_processo(tmp_path):
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
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
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
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


def test_avviare_un_secondo_step_mentre_il_primo_gira_solleva(tmp_path):
    """E' un errore del chiamante, non un esito dell'elaborazione: la nuvola
    assente tiene comunque il processo in volo abbastanza a lungo (avvio
    dell'interprete) da coglierlo con is_running() subito dopo lo start."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
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


class _ProcessoUscitoCollettoStdout:
    """Un sottoprocesso gia' terminato il cui stdout non e' ancora stato letto.

    E' la finestra vera e non una sua caricatura: `poll()` vede il figlio uscito
    nell'istante in cui muore, mentre le righe restano nel buffer della pipe
    finche' il thread lettore non le consuma. Il generatore si ferma a meta'
    apposta, cosi' la prova puo' guardare lo stato del Worker mentre la lettura
    e' ancora in corso, senza dipendere da una temporizzazione.
    """

    def __init__(self, codice: int, a_meta: threading.Event, prosegui: threading.Event) -> None:
        self.returncode = codice
        self.stdout = self._righe(a_meta, prosegui)

    def _righe(self, a_meta: threading.Event, prosegui: threading.Event):
        yield "prima riga\n"
        a_meta.set()
        assert prosegui.wait(timeout=10), "la prova non ha sbloccato il lettore"
        yield "ultima riga\n"

    def poll(self) -> int:
        return self.returncode

    def wait(self) -> int:
        return self.returncode


def test_una_corsa_conclusa_porta_sempre_il_proprio_codice_di_uscita():
    """La corsa fra is_running() e exit_code, parcheggiata in Task 1.

    Il frame SSE legge i due campi insieme (server.py: "in_corso" ed
    "exit_code" nello stesso dizionario). Fermandosi a poll(), is_running()
    diventava falso appena il figlio usciva, mentre exit_code lo scrive il
    thread lettore dopo aver svuotato stdout: nel mezzo il browser riceveva
    in_corso: false con exit_code: null, che esitoDellaCorsa classifica —
    correttamente, per la propria specifica — come conclusa. Una corsa fallita
    annunciata come riuscita, e il fronte di discesa scatta una volta sola:
    l'annuncio sbagliato e' permanente, non transitorio.
    """
    a_meta, prosegui = threading.Event(), threading.Event()
    lavoratore = Worker()
    lavoratore._processo = _ProcessoUscitoCollettoStdout(1, a_meta, prosegui)
    lavoratore._concluso.clear()
    lettore = threading.Thread(target=lavoratore._leggi, daemon=True)
    lettore.start()
    assert a_meta.wait(timeout=10), "il lettore non e' mai partito"

    # Qui il figlio e' gia' uscito (poll() torna 1) e l'esito non e' ancora
    # scritto: e' esattamente il frame che il browser leggeva male.
    assert lavoratore.exit_code is None
    assert lavoratore.is_running() is True, (
        "una corsa senza esito si dichiara conclusa: il browser la annuncia riuscita"
    )

    prosegui.set()
    lettore.join(timeout=10)
    assert lettore.is_alive() is False
    assert lavoratore.is_running() is False
    assert lavoratore.exit_code == 1
    assert lavoratore.righe() == ["prima riga", "ultima riga"]


def test_un_annullamento_arrivato_dopo_una_corsa_riuscita_non_dice_annullato():
    """Il fratello della corsa qui sopra. `cancel()` guarda is_running() e poi
    marca `annullato`, e fra le due cose il figlio puo' finire da se': il
    terminate() arriva dopo l'ultimo respiro, il codice d'uscita resta 0, e la
    corsa si racconta interrotta pur avendo prodotto i propri artefatti.

    Un processo terminato da SIGTERM non esce mai con 0, quindi lo zero e'
    l'unica firma possibile di una corsa arrivata in fondo.
    """
    a_meta, prosegui = threading.Event(), threading.Event()
    prosegui.set()
    lavoratore = Worker()
    lavoratore._processo = _ProcessoUscitoCollettoStdout(0, a_meta, prosegui)
    lavoratore._concluso.clear()
    # Lo stato che cancel() lascia quando arriva un istante troppo tardi.
    lavoratore.annullato = True

    lavoratore._leggi()

    assert lavoratore.exit_code == 0
    assert lavoratore.annullato is False, (
        "una corsa riuscita si racconta annullata"
    )
