#!/bin/sh
# Avvio col doppio clic dal Finder (macOS).
#
# Nessun argomento, e non e' una dimenticanza: `meshrec serve` senza
# configurazione apre la schermata d'ingresso, che elenca le corse gia' in
# runs/ e ne fa nascere una nuova da un file di punti. Chi riceve una scansione
# non ha uno yaml da scegliere, e chiederglielo prima di mostrargli qualcosa
# sarebbe uno sbarramento davanti alla porta.
#
# Due cose che questo file deve fare e che il comando da solo non fa:
#   1. spostarsi nella propria cartella. Il Finder avvia con la cartella
#      corrente sulla home, e i percorsi relativi del programma (run.out_dir,
#      runs/, experiments/, .cache/viewport) finirebbero fuori dal progetto.
#   2. tenere aperta la finestra quando qualcosa va storto, altrimenti il
#      Terminale si chiude e il messaggio di errore non lo legge nessuno.
cd "$(dirname "$0")" || exit 1

# Il Finder non legge ~/.zshrc: uv sta dove lo mette il suo installatore.
PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH

if ! command -v uv >/dev/null 2>&1; then
    echo "uv non trovato."
    echo "Installalo con:  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo
    printf "Premi Invio per chiudere. "
    read -r _
    exit 1
fi

# "$@" resta: da riga di comando `./MeshRec.command casi/lab_telaio.yaml` apre
# quel caso direttamente. E' il doppio clic a non passare nulla, ed e' li' che
# la schermata d'ingresso serve.
uv run meshrec serve "$@" || {
    echo
    printf "MeshRec si e' fermato. Premi Invio per chiudere. "
    read -r _
    exit 1
}
