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


def test_le_righe_arrivano_senza_le_sequenze_di_colore_del_terminale():
    """Open3D scrive i propri errori con i colori del terminale. Nel pannello
    del registro non colorano niente: arrivano come testo, e «[Open3D Error]
    Not enough points» si legge preceduto da «[1;31m» e seguito da una riga di
    solo «[0;m» — misurato a video. E' la finestra a cui l'interfaccia manda
    chi ha appena visto fallire uno step."""
    from meshrec.app.worker import _senza_colori

    sporca = "\x1b[1;31m[Open3D Error] Not enough points\x1b[0;m"
    assert _senza_colori(sporca) == "[Open3D Error] Not enough points"
    assert _senza_colori("nessun colore qui") == "nessun colore qui"


def test_il_worker_dichiara_anche_la_coda_della_corsa(tmp_path):
    """Un solo `meshrec run` copre from_step..to_step, e il worker ne teneva
    solo il capo: il browser riceveva «step: 1» per una corsa da 1 a 11 e
    annunciava «Lettura» per tutti gli undici, compresi i minuti dentro
    Tetraedri. Senza la coda l'interfaccia non puo' nemmeno distinguere una
    corsa di un solo step da una che ne copre undici."""
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    assert lavoratore.a_step is None, "un worker che non ha mai girato non ha una coda"
    lavoratore.start(percorso, 2, 7)
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert (lavoratore.step, lavoratore.a_step) == (2, 7)


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
        self.terminato = False

    def _righe(self, a_meta: threading.Event, prosegui: threading.Event):
        yield "prima riga\n"
        a_meta.set()
        assert prosegui.wait(timeout=10), "la prova non ha sbloccato il lettore"
        yield "ultima riga\n"

    def poll(self) -> int:
        return self.returncode

    def wait(self) -> int:
        return self.returncode

    def terminate(self) -> None:
        # Registrato e non un errore: se manca, un cancel() che non doveva
        # passare esplode qui e la prova diventa rossa per l'attributo assente
        # invece che per il fatto che si vuole sorvegliare.
        self.terminato = True


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
    lettore = threading.Thread(target=lavoratore._leggi, args=(lavoratore._processo,), daemon=True)
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


def test_un_popen_che_solleva_non_lascia_il_worker_impiccato(tmp_path, monkeypatch):
    """`start()` scrive lo stato della corsa nuova solo dopo che il processo
    esiste. Nell'ordine opposto, un Popen che solleva lasciava exit_code
    azzerato e `_concluso` abbassato senza un lettore che lo rialzasse: la
    coppia proibita che is_running() esiste per impedire, piu' un worker che
    si dichiara occupato per sempre — ogni start() successiva rifiutata, e
    niente da annullare.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    # Un worker che ha gia' concluso una corsa: e' lo stato in cui il difetto si
    # vede: `_processo` esiste ed e' uscito, quindi `poll()` non basta a dire
    # «ferma» e la risposta dipende tutta da `_concluso`. Su un worker mai
    # avviato (`_processo is None`) il sintomo non si presenta.
    lavoratore = Worker()
    fatto, subito = threading.Event(), threading.Event()
    subito.set()
    lavoratore._processo = _ProcessoUscitoCollettoStdout(3, fatto, subito)
    lavoratore._concluso.clear()
    lavoratore._leggi(lavoratore._processo)
    assert lavoratore.is_running() is False
    assert lavoratore.exit_code == 3
    lavoratore.annullato = True

    def niente_processi(*_args, **_chiavi):
        raise OSError("niente risorse per un altro processo")

    monkeypatch.setattr("meshrec.app.worker.subprocess.Popen", niente_processi)
    with pytest.raises(OSError):
        lavoratore.start(percorso, 1, 1)

    assert lavoratore.is_running() is False, "il worker si dichiara occupato senza un processo"
    # Lo stato della corsa precedente non e' stato toccato: non e' cominciata
    # nessuna corsa nuova da cui azzerarlo.
    assert lavoratore.exit_code == 3
    assert lavoratore.annullato is True

    monkeypatch.undo()
    lavoratore.start(percorso, 1, 1)
    for _ in range(600):
        if not lavoratore.is_running():
            break
        time.sleep(0.1)
    assert lavoratore.is_running() is False
    assert lavoratore.exit_code is not None


def test_due_start_sovrapposte_avviano_un_solo_processo(tmp_path, monkeypatch):
    """La prenotazione del worker sta nell'abbassare `_concluso`, e deve stare
    prima della Popen: dentro il fork+exec la guardia rispondeva ancora «libero»
    e due clic sovrapposti avviavano due `meshrec run` sulla stessa cartella di
    corsa. La finestra e' piccola ma vera — uvicorn serve le tratte sincrone su
    un pool di thread — ed e' la stessa riga su cui il registro fonda il Minor
    lasciato dei bottoni Esegui: «un secondo clic prende un 400 dal worker».
    Dentro quella finestra il 400 non arrivava.

    Il worker parte qui vergine, `_processo is None`, che e' il caso piu'
    probabile e non il piu' raro: pagina fresca dopo l'avvio del server, doppio
    clic impaziente. E' anche l'unico ramo in cui una prenotazione presa ma non
    consultata resta inerte, perche' is_running() usciva su `_processo is None`
    prima ancora di guardare `_concluso`.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    assert lavoratore.is_running() is False

    creati = []
    dentro_la_popen, prosegui = threading.Event(), threading.Event()

    def popen_lenta(*_args, **_chiavi):
        creati.append(1)
        # Solo la prima si ferma: se si fermassero tutte, un secondo clic che
        # passa (cioe' il difetto) bloccherebbe la prova invece di mostrarla, e
        # il rosso arriverebbe da un'attesa scaduta invece che dal fatto.
        if len(creati) == 1:
            dentro_la_popen.set()
            assert prosegui.wait(timeout=10), "la prova non ha sbloccato la Popen"
        finito, gia = threading.Event(), threading.Event()
        gia.set()
        return _ProcessoUscitoCollettoStdout(0, finito, gia)

    monkeypatch.setattr("meshrec.app.worker.subprocess.Popen", popen_lenta)

    primo = threading.Thread(target=lavoratore.start, args=(percorso, 1, 1), daemon=True)
    primo.start()
    assert dentro_la_popen.wait(timeout=10), "la prima start() non e' entrata nella Popen"

    # Il secondo clic cade esattamente dentro il fork+exec del primo.
    esiti = []
    try:
        lavoratore.start(percorso, 1, 1)
        esiti.append("avviata")
    except RuntimeError:
        esiti.append("rifiutata")

    prosegui.set()
    primo.join(timeout=10)
    assert creati == [1], f"sono stati avviati {len(creati)} processi sulla stessa corsa"
    assert esiti == ["rifiutata"], f"il secondo clic non e' stato rifiutato: {esiti}"


def test_dentro_la_popen_lo_stato_e_gia_quello_della_corsa_nuova(tmp_path, monkeypatch):
    """La prenotazione rende viva la finestra del fork+exec: da li' is_running()
    risponde True e il frame SSE porta step e secondi. Se le due righe stanno
    sotto la Popen, quel frame porta lo step e il cronometro della corsa
    *precedente* -- «Riduzione in corso, 800 s» per una corsa appena lanciata su
    Tetraedri. Un numero misurato che nessuna misura sostiene, che e' il difetto
    che questo ramo esiste per non commettere.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    # Una corsa precedente conclusa sullo step 3, partita ottocento secondi fa.
    lavoratore.step = 3
    lavoratore.avviato = time.monotonic() - 800.0

    visto = {}

    def popen_che_guarda(*_args, **_chiavi):
        # Dentro il fork+exec: e' il momento in cui un frame SSE puo' cadere.
        visto["step"] = lavoratore.step
        visto["da_secondi"] = lavoratore.da_secondi()
        finito, gia = threading.Event(), threading.Event()
        gia.set()
        return _ProcessoUscitoCollettoStdout(0, finito, gia)

    monkeypatch.setattr("meshrec.app.worker.subprocess.Popen", popen_che_guarda)
    lavoratore.start(percorso, 9, 9)

    assert visto["step"] == 9, "il frame nomina lo step della corsa precedente"
    assert visto["da_secondi"] is not None, "la finestra viva che si vuole provare non esiste piu'"
    assert visto["da_secondi"] < 5.0, (
        f"la corsa appena lanciata si dichiara vecchia di {visto['da_secondi']:.0f} s"
    )


def test_annullare_dentro_la_finestra_del_fork_non_esplode(tmp_path, monkeypatch):
    """Il rovescio della prenotazione, ed e' il rovescio di un'invariante persa.

    Da quando is_running() consulta `_concluso` anche con `_processo is None`,
    esiste una finestra in cui il worker si dichiara occupato senza avere
    ancora un figlio — e sulla prima corsa `exit_code` e' None, quindi cancel()
    superava entrambi i controlli e arrivava a terminare un processo che non
    c'era: `assert self._processo is not None` non era piu' un'invariante. Un
    Annulla che cade li' rispondeva 500 con traceback e lasciava `annullato`
    alzato per la corsa che stava partendo.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    lavoratore = Worker()
    visto = {}

    def popen_annullata(*_args, **_chiavi):
        # Dentro il fork+exec, con la prenotazione presa e `_processo` ancora
        # None: e' l'istante che rende falsa la vecchia invariante.
        visto["prenotato"] = lavoratore.is_running()
        visto["processo"] = lavoratore._processo
        visto["esito"] = lavoratore.cancel()
        # Catturato qui e non dopo start(): il blocco subito sotto la Popen
        # riazzera annullato, quindi un'asserzione fatta alla fine sarebbe
        # verde qualunque cosa cancel() marchi.
        visto["annullato"] = lavoratore.annullato
        finito, gia = threading.Event(), threading.Event()
        gia.set()
        return _ProcessoUscitoCollettoStdout(0, finito, gia)

    monkeypatch.setattr("meshrec.app.worker.subprocess.Popen", popen_annullata)
    lavoratore.start(percorso, 1, 1)

    assert visto["prenotato"] is True, "la finestra che si vuole provare non esiste piu'"
    assert visto["processo"] is None, "il figlio esisteva gia': non e' la finestra giusta"
    assert visto["esito"] is False, "ha annullato una corsa senza processo"
    assert visto["annullato"] is False, "una corsa che sta partendo si racconta annullata"


class _ProcessoVivoFinoAlKill:
    """Un figlio che resta vivo finche' non lo si uccide.

    Serve a distinguere «rilasciata la prenotazione» da «il figlio non c'e'
    piu'»: con un fantoccio gia' uscito poll() risponderebbe subito e il worker
    sembrerebbe a posto anche senza il kill.
    """

    def __init__(self) -> None:
        self.stdout = iter(())
        self.returncode: int | None = None
        self.ucciso = False

    def poll(self) -> int | None:
        return self.returncode

    def kill(self) -> None:
        self.ucciso = True
        self.returncode = -9

    def wait(self) -> int | None:
        return self.returncode


def test_un_thread_che_non_parte_non_lascia_un_figlio_orfano(tmp_path, monkeypatch):
    """Il gemello di `test_un_popen_che_solleva...`, un passo piu' avanti.

    Quando e' Thread.start() a fallire -- esaurimento dei thread -- il figlio e'
    gia' vivo. Rialzare `_concluso` non basta: `poll()` non vede nessuna uscita,
    quindi is_running() resta True per sempre, senza nessun lettore che ne
    svuoti lo stdout, e il `meshrec run` orfano continua a girare. Si
    recuperava solo cliccando Annulla.
    """
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "assente.ply"))
    cfg.run.out_dir = tmp_path / "corsa"
    percorso = tmp_path / "config.yaml"
    save_config(cfg, percorso)

    figli = []

    def popen_finta(*_args, **_chiavi):
        figli.append(_ProcessoVivoFinoAlKill())
        return figli[-1]

    class _ThreadCheNonParte:
        def __init__(self, *_args, **_chiavi) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr("meshrec.app.worker.subprocess.Popen", popen_finta)
    monkeypatch.setattr("meshrec.app.worker.threading.Thread", _ThreadCheNonParte)

    lavoratore = Worker()
    with pytest.raises(RuntimeError):
        lavoratore.start(percorso, 1, 1)

    assert figli[0].ucciso is True, "il figlio resta a girare senza nessuno che lo legga"
    assert lavoratore.is_running() is False, "il worker si dichiara occupato per sempre"
    # La coppia proibita, di nuovo: il blocco dentro start() ha gia' azzerato
    # exit_code, e in_corso: false con exit_code: null il browser lo annuncia
    # come «concluso» — un falso successo su una corsa mai partita.
    assert lavoratore.exit_code is not None, "una corsa mai partita si annuncia riuscita"
    assert lavoratore.exit_code != 0


def test_un_annullamento_che_arriva_a_esito_gia_scritto_non_marca(tmp_path):
    """Il fratello visto da `cancel()`, che e' la strada vera: il banco qui
    sotto chiama `_leggi()` diretto e non prova mai l'ordinamento fra i due.

    Il lettore scrive l'esito e rettifica la marcatura sotto il lucchetto, poi
    rialza `_concluso`. Fra le due cose `is_running()` risponde ancora True:
    senza il controllo su exit_code, `cancel()` marcava li' e la coppia
    proibita tornava — «annullato» su una corsa che ha scritto i suoi
    artefatti, che e' proprio cio' che la rettifica doveva impedire.
    """
    lavoratore = Worker()
    a_meta, prosegui = threading.Event(), threading.Event()
    prosegui.set()
    lavoratore._processo = _ProcessoUscitoCollettoStdout(0, a_meta, prosegui)
    lavoratore._concluso.clear()

    # Il lettore fino in fondo, ma senza rialzare _concluso: e' la finestra in
    # cui is_running() risponde ancora True con l'esito gia' scritto.
    with lavoratore._lucchetto:
        lavoratore.exit_code = 0
    assert lavoratore.is_running() is True, "la finestra che si vuole provare non esiste piu'"

    assert lavoratore.cancel() is False, "ha annullato una corsa che era gia' finita"
    assert lavoratore.annullato is False, "una corsa riuscita si racconta annullata"
    assert lavoratore._processo.terminato is False, "ha mandato un segnale a un processo gia' uscito"
    assert "--- annullato su richiesta ---" not in lavoratore.righe()


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

    lavoratore._leggi(lavoratore._processo)

    assert lavoratore.exit_code == 0
    assert lavoratore.annullato is False, (
        "una corsa riuscita si racconta annullata"
    )
