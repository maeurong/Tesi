"""MeshRec - pipeline da nuvola di punti a modello FEM."""

import os

# OpenMP legge OMP_NUM_THREADS alla prima regione parallela, cioe' al primo uso
# di Open3D, non a ogni chiamata: la variabile va quindi impostata prima che un
# qualunque modulo importi Open3D. Questo file e' l'unico punto che Python
# esegue prima di ogni sottomodulo del pacchetto, quindi prima di io.py,
# surface.py e segment.py, in qualunque ordine i test o la riga di comando li
# carichino.
#
# Serve perche' la riproducibilita' dipende dal numero di thread: il RANSAC di
# segment_plane e il solutore Poisson sono paralleli, e con piu' thread l'ordine
# di scoperta del risultato dipende dallo scheduling, quindi il seme fissato con
# o3d.utility.random.seed da solo non basta (verificato: due esecuzioni della
# stessa configurazione davano un numero diverso di punti residui).
#
# setdefault e non assegnazione: chi preferisce la velocita' alla
# riproducibilita' esporta OMP_NUM_THREADS dall'esterno e questa riga si fa da
# parte.
os.environ.setdefault("OMP_NUM_THREADS", "1")
