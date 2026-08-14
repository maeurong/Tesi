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
        self.exit_code: int | None = None
        self.step: int | None = None
        self.annullato = False
        self.avviato: float | None = None

    def is_running(self) -> bool:
        return self._processo is not None and self._processo.poll() is None

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
        with self._lucchetto:
            self._righe.clear()
        self.exit_code = None
        self.annullato = False
        self.step = from_step
        self.avviato = time.monotonic()
        self._processo = subprocess.Popen(
            [
                sys.executable, "-m", "meshrec.cli", "run", str(config_path),
                "--from-step", str(from_step), "--to-step", str(to_step),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._leggi, daemon=True).start()

    def _leggi(self) -> None:
        processo = self._processo
        if processo is None or processo.stdout is None:
            return
        for riga in processo.stdout:
            with self._lucchetto:
                self._righe.append(riga.rstrip("\n"))
        processo.wait()
        self.exit_code = processo.returncode

    def cancel(self) -> bool:
        """Termina lo step in corso. Falso se non ce n'era uno.

        La granularita' e' uno step: si annulla lo step, non una sua frazione,
        perche' le librerie di calcolo non offrono punti di ripresa. La
        cartella resta coerente perche' metrics.json viene riscritto solo a
        corsa conclusa e gli artefatti sono scritti in modo atomico.
        """
        if not self.is_running():
            return False
        self.annullato = True
        assert self._processo is not None
        self._processo.terminate()
        with self._lucchetto:
            self._righe.append("--- annullato su richiesta ---")
        return True
