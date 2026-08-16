"""Esecuzione di uno step in un processo separato, con log e annullamento.

Il sottoprocesso e non un thread, per le tre ragioni gia' misurate in Fase 2:
un processo ucciso dal sistema per esaurimento della memoria lascia un codice
di uscita invece di rompere il pool; il percorso eseguito e' esattamente
`meshrec run`, con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2; e
l'avvio di un interprete costa pochi secondi contro i minuti di una corsa.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

# Le righe tenute in memoria per il pannello del log. Un tetto e' necessario
# perche' un processo prolisso non faccia crescere il server senza limite; il
# log completo resta comunque sullo stderr del sottoprocesso.
MAX_RIGHE = 2000


class Worker:
    """Un solo step alla volta. Utente singolo: non serve una coda."""

    def __init__(self) -> None:
        self._processo: subprocess.Popen[str] | None = None
        self._righe: deque[str] = deque(maxlen=MAX_RIGHE)
        self._lucchetto = threading.Lock()
        # Alzato quando il thread lettore ha finito di scrivere l'esito. Nasce
        # alzato: senza una corsa in volo non c'e' niente da attendere.
        self._concluso = threading.Event()
        self._concluso.set()
        self.exit_code: int | None = None
        self.step: int | None = None
        self.annullato = False
        self.avviato: float | None = None

    def is_running(self) -> bool:
        if self._processo is None:
            return False
        if self._processo.poll() is None:
            return True
        # Il figlio e' uscito, ma l'esito lo scrive il thread lettore dopo aver
        # svuotato stdout, e fra i due momenti passa tutto il tempo che serve a
        # leggere il buffer. Fermandosi a poll(), un frame SSE poteva portare
        # in_corso: false con exit_code ancora None, e il browser lo classifica
        # -- correttamente, per la propria specifica -- come "conclusa". Una
        # corsa fallita si annunciava riuscita, e il fronte di discesa scatta
        # una volta sola: l'annuncio sbagliato non si correggeva mai piu'.
        # Lo stato concluso e' atomico qui dentro: chi legge in_corso: false
        # trova sempre un exit_code gia' fissato.
        return not self._concluso.is_set()

    def da_secondi(self) -> float | None:
        """Secondi dall'avvio dello step in corso. None se non gira nulla.

        Il tempo si misura qui, dove lo step parte davvero: contato nel
        browser conterebbe da quando quella pagina ha visto lo stato "in
        corso", non da quando il calcolo e' partito. time.monotonic e non
        time.time perche' l'orologio di sistema puo' saltare all'indietro e
        darebbe un tempo trascorso negativo.
        """
        if not self.is_running() or self.avviato is None:
            return None
        return time.monotonic() - self.avviato

    def righe(self) -> list[str]:
        with self._lucchetto:
            return list(self._righe)

    def start(self, config_path: Path, from_step: int, to_step: int) -> None:
        """Avvia lo step. Solleva se un altro sta gia' girando: e' un errore
        del chiamante, non un esito dell'elaborazione."""
        if self.is_running():
            raise RuntimeError("uno step sta gia' girando: annullalo prima di avviarne un altro")
        # Prima il processo, poi lo stato della corsa nuova. Scritto nell'ordine
        # opposto, un Popen che solleva (risorse esaurite, interprete sparito)
        # lascerebbe dietro di se' proprio la coppia proibita che is_running()
        # esiste per impedire: exit_code azzerato su una corsa che nessuno sta
        # piu' eseguendo, e _concluso abbassato senza un lettore che lo rialzi —
        # cioe' un worker impiccato, con ogni start() successiva rifiutata e
        # niente da annullare. Da questa riga in giu' non si solleva piu'.
        processo = subprocess.Popen(
            [
                sys.executable, "-m", "meshrec.cli", "run", str(config_path),
                "--from-step", str(from_step), "--to-step", str(to_step),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with self._lucchetto:
            self._righe.clear()
            self.exit_code = None
            self.annullato = False
        self.step = from_step
        self.avviato = time.monotonic()
        self._concluso.clear()
        self._processo = processo
        threading.Thread(target=self._leggi, daemon=True).start()

    def _leggi(self) -> None:
        processo = self._processo
        try:
            if processo is None or processo.stdout is None:
                return
            for riga in processo.stdout:
                with self._lucchetto:
                    self._righe.append(riga.rstrip("\n"))
            processo.wait()
            # L'esito e la marcatura si scrivono insieme, sotto il lucchetto che
            # cancel() prende a sua volta. Un annullamento chiesto a un processo
            # che era gia' uscito bene non e' un annullamento: il terminate()
            # arriva dopo l'ultimo respiro e il codice d'uscita resta 0, e
            # annullato: true con exit_code: 0 racconterebbe come interrotta una
            # corsa che ha prodotto i suoi artefatti. Rettificare qui senza il
            # lucchetto non basterebbe: cancel() puo' marcare *dopo* la
            # rettifica e prima che _concluso si rialzi, e la coppia proibita
            # tornerebbe. Un SIGTERM non produce mai un codice 0, quindi lo zero
            # e' la firma di una corsa arrivata in fondo.
            with self._lucchetto:
                self.exit_code = processo.returncode
                if self.exit_code == 0:
                    self.annullato = False
        finally:
            # Nel finally e non in coda: un'uscita anticipata (nessun processo,
            # nessuno stdout) deve comunque sbloccare is_running(), altrimenti
            # la corsa resterebbe «in volo» per sempre.
            self._concluso.set()

    def cancel(self) -> bool:
        """Termina lo step in corso. Falso se non ce n'era uno.

        La granularita' e' uno step: si annulla lo step, non una sua frazione,
        perche' le librerie di calcolo non offrono punti di ripresa. La
        cartella resta coerente perche' metrics.json viene riscritto solo a
        corsa conclusa e gli artefatti sono scritti in modo atomico.
        """
        # Il controllo e la marcatura sotto lo stesso lucchetto che il lettore
        # prende per scrivere l'esito: separati, il lettore poteva scrivere
        # exit_code 0 e rettificare la marcatura fra il controllo qui sotto e la
        # riga che marca, e la corsa riuscita si sarebbe raccontata annullata.
        # exit_code gia' fissato vuol dire che non c'e' piu' niente da fermare,
        # anche quando _concluso non e' ancora stato rialzato.
        # is_running() non prende il lucchetto: legge solo poll() e _concluso.
        with self._lucchetto:
            if not self.is_running() or self.exit_code is not None:
                return False
            self.annullato = True
        assert self._processo is not None
        self._processo.terminate()
        with self._lucchetto:
            self._righe.append("--- annullato su richiesta ---")
        return True
