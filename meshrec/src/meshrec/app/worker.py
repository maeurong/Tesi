"""Esecuzione di uno step in un processo separato, con log e annullamento.

Il sottoprocesso e non un thread, per le tre ragioni gia' misurate in Fase 2:
un processo ucciso dal sistema per esaurimento della memoria lascia un codice
di uscita invece di rompere il pool; il percorso eseguito e' esattamente
`meshrec run`, con cui sono stati prodotti tutti i numeri delle Fasi 1 e 2; e
l'avvio di un interprete costa pochi secondi contro i minuti di una corsa.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

# I due capi del tubo, dichiarati invece che lasciati al locale della macchina.
#
# `text=True` da solo fa scegliere a ciascun capo la propria codifica di
# sistema, e nessuno garantisce che coincidano. Su Windows non coincidono: il
# lettore leggeva UTF-8 e il figlio scriveva nella codepage italiana, quindi il
# primo accento -- e dopo la passata di ieri le righe mostrate ne portano --
# faceva sollevare `UnicodeDecodeError` a meta' della prima riga. Misurato:
# `0xE0` e' `à` in cp1252.
#
# Servono TUTTI E DUE i capi, misurato con tre Popen a confronto: con il solo
# `errors="replace"` il lettore smette di morire ma il registro consegna
# `citt<?>.ply` invece di `città.ply`, cioe' il guasto diventa invisibile
# invece che chiuso. E `errors="replace"` serve comunque anche col figlio
# forzato, perche' Open3D e ccx scrivono sul descrittore in C++ saltando
# `sys.stdout`: `PYTHONIOENCODING` non li governa, e una riga storta di
# libreria non deve poter fermare una corsa.
CODIFICA_DEL_TUBO = {"encoding": "utf-8", "errors": "replace"}


def _ambiente_del_figlio() -> dict[str, str]:
    """L'ambiente del sottoprocesso con la codifica di stdout dichiarata."""
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

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
        # Il capo di arrivo. `step` da solo e' il capo di PARTENZA e non avanza
        # mai -- si fissa in start() e resta li' -- quindi una corsa da 1 a 11
        # si annunciava «step 1 in corso» dall'inizio alla fine, e a quattro
        # secondi dall'avvio diceva ancora Lettura, che ne era durata 0,03.
        # Con i due capi l'interfaccia puo' dire di che cosa parla la corsa
        # invece di nominare solo il primo passo.
        self.a_step: int | None = None
        self.etichetta: str | None = None
        self.annullato = False
        # Identita' della corsa, non il suo conteggio: due avvii ravvicinati
        # possono lasciare lo stesso numero di righe (o di piu'), e il flusso
        # SSE in server.py usa questo contatore per sapere che le righe sono
        # ripartite da zero anche quando il conteggio da solo non lo direbbe.
        self.avvii = 0
        self.avviato: float | None = None
        # Quanto e' durata l'ultima corsa finita. `da_secondi()` smette di
        # rispondere a processo morto -- e' costruita per l'attesa, e a corsa
        # ferma non c'e' nessuna attesa in corso -- quindi il tempo che
        # l'utente ha appena passato ad aspettare si perdeva nello stesso
        # istante in cui diventava un fatto compiuto. Su un intervallo era
        # l'unica misura possibile: `secondi` nel file di stato e' il tempo del
        # singolo step, e su una corsa da 1 a 11 non descrive niente.
        self.durata: float | None = None

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
            raise RuntimeError("uno step sta già girando: annullalo prima di avviarne un altro")
        with self._lucchetto:
            self._righe.clear()
        self.avvii += 1
        self.exit_code = None
        self.annullato = False
        self.durata = None
        self.step = from_step
        self.a_step = to_step
        self.etichetta = None
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
            env=_ambiente_del_figlio(),
            **CODIFICA_DEL_TUBO,
        )
        threading.Thread(target=self._leggi, daemon=True).start()

    def start_comando(self, argomenti: list[str], etichetta: str) -> None:
        """Avvia un comando di `meshrec` che non e' uno step della pipeline.

        Il prior e i modelli parametrici sono azioni e non step: non hanno un
        numero, non entrano nella colonna della pipeline e non invalidano nulla
        a valle. Passano pero' dallo stesso sottoprocesso degli step, per le
        stesse tre ragioni gia' misurate: un processo ucciso lascia un codice
        di uscita, il percorso eseguito e' esattamente quello della riga di
        comando, e l'avvio di un interprete costa pochi secondi.
        """
        if self.is_running():
            raise RuntimeError("uno step sta già girando: annullalo prima di avviarne un altro")
        with self._lucchetto:
            self._righe.clear()
        self.avvii += 1
        self.exit_code = None
        self.annullato = False
        self.durata = None
        self.step = None
        # Un comando fuori pipeline (il prior, un modello parametrico) non ha
        # capi: azzerato qui perche' altrimenti resterebbe quello della corsa
        # di prima, e il browser annuncerebbe un intervallo che questo comando
        # non percorre.
        self.a_step = None
        self.etichetta = etichetta
        self.avviato = time.monotonic()
        self._processo = subprocess.Popen(
            [sys.executable, "-m", "meshrec.cli", *argomenti],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            env=_ambiente_del_figlio(), **CODIFICA_DEL_TUBO,
        )
        threading.Thread(target=self._leggi, daemon=True).start()

    def _leggi(self) -> None:
        processo = self._processo
        if processo is None or processo.stdout is None:
            return
        # Il `finally` non e' cintura sopra bretelle. Questo corpo gira in un
        # THREAD DEMONE: un'eccezione qui dentro non risale a nessuno, uccide
        # solo il lettore, e da li' `wait()` non viene chiamato ed `exit_code`
        # resta None PER SEMPRE. E `exit_code` nullo l'interfaccia lo tratta
        # come «non lo so ancora» e tace (ui/app.js, `esitoDellaCorsa`), quindi
        # la corsa falliva e a video non compariva niente: ne' conclusa, ne'
        # fallita, ne' annullata. Misurato: e' cosi' che il difetto di codifica
        # e' arrivato all'utente come schermo muto invece che come messaggio.
        #
        # `errors="replace"` toglie la causa che l'ha prodotto; questo toglie la
        # classe. Il codice di uscita e' l'unica cosa che il resto del programma
        # ha per sapere com'e' finita una corsa, e non deve dipendere dal fatto
        # che la lettura del registro sia andata bene.
        try:
            for riga in processo.stdout:
                with self._lucchetto:
                    self._righe.append(riga.rstrip("\n"))
        finally:
            processo.wait()
            # La durata PRIMA del codice di uscita, e non e' un ordine
            # indifferente: `exit_code` e' il fatto che dichiara la corsa
            # finita, il carico SSE lo spedisce nella stessa istantanea di
            # `durata`, e un browser che leggesse fra le due assegnazioni
            # vedrebbe il fronte di discesa senza il numero -- una volta su
            # quante, non si sa, ed e' esattamente il genere di guasto che non
            # si riproduce quando lo si cerca.
            if self.avviato is not None:
                self.durata = time.monotonic() - self.avviato
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
