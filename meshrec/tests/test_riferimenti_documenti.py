"""`docs/validazione/controlla-riferimenti.py` gira dentro la suite, non a mano.

Lo script è il controllo che sorveglia i riferimenti `file:riga` dei documenti
di validazione (#96). Finché si lanciava solo a mano era un controllore il cui
controllo non veniva lanciato: `.github/workflows/suite.yml` chiama `pytest` e
nient'altro, e `grep -rn autoprova tests/` non trovava niente. Questi due test
lo agganciano senza toccare il workflow.

Il primo esegue la `autoprova()` che lo script porta con sé: se qualcuno rompe
una delle sue categorie, questo test diventa rosso. Sette mutazioni misurate una
per una — nome ambiguo disattivato, estremo destro dell'intervallo ignorato,
riga zero accettata, disambiguazione per percorso disattivata, uscita 2 sugli
argomenti, uscita 2 sul file inesistente, uscita 1 sui rotti — le uccide tutte.

Il secondo passa lo script sui documenti veri.

**Limite dichiarato del secondo test, sulla forma a numero.** Dei riferimenti
`file:riga` vede solo quelli che non risolvono affatto: riga oltre la fine del
file, riga zero, nome ambiguo. **Non** vede quelli che risolvono su una riga
sbagliata, che erano la larga maggioranza della deriva misurata in #96 — 166 su
168 puntavano a una riga esistente e a un contenuto diverso, e la fusione dei
sette rami ne ha prodotti altri 43. Per quelli serve leggere.

**Sulla forma a nome il limite non c'è**, ed è la ragione per cui i documenti di
validazione sono stati riscritti per citare `modulo.simbolo` invece della riga:
un nome che il modulo non definisce più è **rotto**, e questo test lo vede senza
che nessuno rilegga.
"""

import importlib.util
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
SCRIPT = RADICE / "docs" / "validazione" / "controlla-riferimenti.py"


def _carica():
    """Il nome del file porta un trattino: si carica dal percorso, non per `import`."""
    spec = importlib.util.spec_from_file_location("controlla_riferimenti", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_lo_script_dei_riferimenti_supera_la_propria_autoprova():
    _carica().autoprova()


def test_nessun_documento_di_validazione_porta_un_riferimento_che_non_risolve():
    modulo = _carica()
    indice = modulo._indice()
    guasti = {}
    for documento in sorted((RADICE / "docs" / "validazione").glob("*.md")):
        rotti, _fuori_albero, _non_verificabili = modulo.controlla(documento, indice)
        if rotti:
            guasti[documento.name] = rotti
    assert not guasti, guasti
