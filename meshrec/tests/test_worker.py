"""Il worker esegue uno step in un processo separato e lo puo' terminare."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from meshrec.app.worker import CODIFICA_DEL_TUBO, Worker
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

    Il rimedio ha spostato che cosa questo controllo prova, e la docstring
    segue. Prima il figlio ereditava `PYTHONIOENCODING` dal genitore e scriveva
    davvero latin-1: il controllo pesava la sopravvivenza del lettore. Adesso i
    `Popen` passano un `env` che dichiara la codifica del figlio, quindi quel
    latin-1 non arriva piu' a destinazione -- ed e' proprio questo che si
    misura: **col genitore avvelenato, l'accento arriva INTATTO**. Non
    sostituito: intatto. E' la meta' del rimedio che chiude la causa invece di
    tamponarla, e la sola che si puo' pesare da qui.

    L'altra meta' -- `errors="replace"`, per i byte storti che le librerie in
    C++ scrivono sul descrittore saltando `sys.stdout` -- ha il suo controllo
    suo, `test_un_byte_storto_dal_descrittore_non_solleva`: da qui non e'
    raggiungibile, perche' `Worker` puo' lanciare solo `meshrec.cli` e su questa
    macchina non c'e' modo di far emettere byte non-UTF-8 a Open3D.

    Mutazione che lo uccide: togliere `env=_ambiente_del_figlio()` dai due
    `Popen`. Misurata: l'accento torna a essere scritto latin-1, il lettore lo
    sostituisce e la riga porta `citt<?>.ply` invece di `città.ply`.
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
    # INTATTO, non «arrivato in qualche forma»: la sostituzione sarebbe la
    # prova che i due capi non si sono accordati e che il lettore ha solo
    # tirato dritto. Accettarla qui renderebbe questo controllo cieco alla
    # meta' del rimedio che sta misurando.
    righe = lavoratore.righe()
    assert any("città.ply" in riga for riga in righe), (
        f"l'accento non e' arrivato intatto: {righe}"
    )


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


def test_un_byte_storto_dal_descrittore_non_solleva():
    """L'altra meta' del rimedio: `errors="replace"` sulla costante condivisa.

    `env` mette d'accordo i due capi finche' a scrivere e' Python. Open3D e
    `ccx` no: scrivono dal C++ direttamente sul descrittore, saltando
    `sys.stdout`, e `PYTHONIOENCODING` non li governa. Un byte storto di
    libreria non deve poter fermare una corsa, e senza `errors=` lo fermava --
    e' come il difetto e' arrivato all'utente.

    Si misura la COSTANTE e non un `Worker`, ed e' deliberato: `Worker` puo'
    lanciare solo `meshrec.cli` (`worker.py`, i due `Popen`), quindi da li' non
    esiste un modo di far emettere byte non-UTF-8 su questa macchina. La
    costante e' pero' esattamente la superficie che i due `Popen` condividono:
    provata qui, vale per tutti e due.

    `0xE0` e non un byte a caso: e' `à` in cp1252, il byte dell'errore vero.

    Mutazione che lo uccide: togliere `"errors": "replace"` da
    `CODIFICA_DEL_TUBO`. Misurata: `UnicodeDecodeError` invece della riga.
    """
    processo = subprocess.Popen(
        [
            sys.executable, "-c",
            r"import sys; sys.stdout.buffer.write(b'citt\xe0.ply\n'); sys.stdout.buffer.flush()",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **CODIFICA_DEL_TUBO,
    )
    righe = list(processo.stdout)
    processo.wait()

    assert len(righe) == 1
    # La riga c'e' e finisce dove deve: il byte storto e' diventato un
    # carattere di sostituzione, non ha mangiato il resto.
    assert righe[0].endswith(".ply\n"), righe
    assert "citt" in righe[0]


def test_il_codice_di_uscita_si_fissa_anche_se_la_lettura_esplode(tmp_path):
    """Il codice d'uscita non deve dipendere dall'esito della lettura.

    `_leggi` gira in un THREAD DEMONE: un'eccezione nel corpo non risale a
    nessuno, uccide il solo lettore, e da li' `wait()` non viene chiamato ed
    `exit_code` resta None per sempre. L'interfaccia legge `exit_code` nullo
    come «non lo so ancora» e TACE, quindi la corsa falliva e a video non
    compariva niente -- ne' conclusa, ne' fallita, ne' annullata. E' cosi' che
    il difetto di codifica e' arrivato come schermo muto invece che come
    messaggio, e il muto e' peggio.

    `errors="replace"` toglie la causa che l'ha prodotto; questo toglie la
    classe. Si prova con un processo finto perche' la causa vera adesso non si
    puo' piu' produrre: e' la classe a essere sorvegliata, non un guasto
    particolare.

    Mutazione che lo uccide: rimettere `processo.wait()` e l'assegnazione di
    `exit_code` nel corpo del `try` invece che nel `finally`.
    """
    class _StdoutCheEsplode:
        def __iter__(self):
            return self

        def __next__(self):
            raise UnicodeDecodeError("utf-8", b"\xe0", 0, 1, "invalid continuation byte")

    class _ProcessoFinto:
        returncode = 3
        stdout = _StdoutCheEsplode()

        def wait(self):
            return self.returncode

    lavoratore = Worker()
    lavoratore._processo = _ProcessoFinto()

    with pytest.raises(UnicodeDecodeError):
        lavoratore._leggi()

    assert lavoratore.exit_code == 3, (
        "il codice d'uscita non e' stato fissato: la corsa resta senza esito per sempre"
    )


def test_la_durata_della_corsa_sopravvive_alla_corsa(tmp_path):
    """`da_secondi()` misura l'attesa e smette di rispondere a processo morto:
    e' costruita per la riga che pulsa, e a corsa ferma non c'e' nessuna attesa
    in corso. Il numero pero' serve un istante dopo -- quando la corsa e' finita
    e l'interfaccia deve dire quanto e' costata -- e li' si perdeva.

    Il worker cronometrava gia' tutto: `avviato` si fissa in `start()` e vale
    per la corsa intera. Mancava solo conservare la differenza.

    Tre fatti, e il terzo e' quello che rende il numero leggibile senza corse:
    `durata` viene fissata PRIMA di `exit_code`, che e' il fatto con cui il
    resto del programma dichiara finita una corsa. Pubblicati nella stessa
    istantanea SSE, l'ordine inverso lascerebbe una finestra in cui il browser
    vede il fronte di discesa senza il numero.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    assert lavoratore.durata is None, "una durata prima di qualsiasi corsa e' una misura inventata"

    lavoratore.start(percorso, 1, 1)
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False

    # Il processo e' morto: `da_secondi()` tace, ed e' giusto che taccia.
    assert lavoratore.da_secondi() is None
    # La durata no: e' il tempo che l'utente ha appena passato ad aspettare.
    assert lavoratore.durata is not None, "la durata della corsa e' stata buttata via"
    assert lavoratore.durata > 0

    # Fallita o riuscita non cambia nulla: un fallimento e' costato lo stesso
    # tempo, e la corsa che fallisce e' quella che si aspetta con piu' ansia.
    assert lavoratore.exit_code != 0

    # La corsa dopo riparte da zero e non eredita la misura di quella prima: una
    # durata vecchia sotto una corsa nuova e' peggio di nessuna durata.
    lavoratore.start(percorso, 1, 1)
    assert lavoratore.durata is None, "la corsa nuova nasce con la durata della precedente"
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.durata is not None, "la seconda corsa non conserva la propria durata"
