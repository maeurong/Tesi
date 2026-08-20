"""Il materiale di prova, in un posto solo.

`config.Material` non ha piu' valori predefiniti: il materiale e' una decisione
di chi analizza, non un valore che il programma possa supplire (vedi
`docs/fase-4-materiale.md`). Ne discende che ogni configurazione di prova deve
dichiararne uno, e che quel materiale merita un posto unico invece di una copia
per file di test.

I valori sono quelli dell'ex predefinito, muratura: qui non contano, contano
solo dove un test guarda il deck e si aspetta `MATERIAL=MURATURA`.
"""

from meshrec.core import config

MATERIALE = config.Material(name="MURATURA", young=1500.0, poisson=0.2, density=1.8e-9)
ANALISI = config.AnalysisConfig(material=MATERIALE)


def crea_config(**campi) -> config.PipelineConfig:
    """`PipelineConfig` con il materiale di prova gia' dichiarato."""
    return config.PipelineConfig(analysis=ANALISI, **campi)


def _tre_cartelle_finte(tmp_path):
    """Tre cartelle di corsa con i soli file che il confronto legge.

    Il confronto non ricalcola nulla: legge metrics.json, 12_wall.json e
    modello.json. Un banco che scrive quei tre file esercita esattamente il
    codice sotto prova, senza far girare la pipeline per ogni test.

    Sta qui e non in tests/test_report.py perche' tests/ non e' un pacchetto
    (nessun __init__.py, e' tests/ stessa a finire su sys.path): un
    `from tests.test_report import _tre_cartelle_finte` in test_cli.py non
    risolverebbe.

    Vengono qui distinti apposta cloud_to_mesh e mesh_to_cloud (con la
    chiave RMS maiuscola, quella vera restituita da PyMeshLab -- vedi
    quality.py:428 e tests/test_quality.py:107) e la chiave dei tetraedri e'
    radius_edge_ratio, non min_ratio: quest'ultimo nel progetto e' il vincolo
    chiesto a TetGen (cfg.tet.min_ratio), non la distribuzione misurata da
    quality.volume_metrics (quality.py:353-362).
    """
    import json

    from meshrec.core import pipeline

    nota_giunzioni = (
        "*TIE fra superfici a contatto: le mesh di membrature adiacenti "
        "non combaciano nodo a nodo. E' una differenza fra i modelli che "
        "non deriva dalla geometria -- as-built monolitico, parametrici "
        "vincolati alle giunzioni -- e va letta accanto al confronto"
    )
    cartelle = []
    for nome, tipo in (("madre", None), ("madre-estruso", "estruso"), ("madre-primitive", "primitive")):
        cartella = tmp_path / nome
        cartella.mkdir()
        metriche = {
            "07_surface_quality": {
                "geometric_error": {
                    "cloud_to_mesh": {"RMS": 4.9},
                    "mesh_to_cloud": {"RMS": 3.1},
                }
            },
            "10_volume_quality": {
                "total_volume": 1.0e8,
                "radius_edge_ratio": {"p50": 1.4},
                "nodes": 1000,
            },
            "11_export": {"volume": 1.0e8, "mass": 0.25, "node_sets": {"BASE": 40}},
        }
        (cartella / "metrics.json").write_text(json.dumps(metriche), encoding="utf-8")
        if tipo is None:
            (cartella / pipeline.WALL_FILENAME).write_text(
                json.dumps({
                    "regioni_trovate": 4,
                    "membrature": [],
                    "scartate": [],
                    "chiusura_volume": {"somma": 1.0e8, "unione": 1.0e8,
                                         "scarto_relativo": 0.0, "passato": True,
                                         "soglia": 0.02, "passo": 20.0, "spiegazione": ""},
                    "riscontri": {"membrature_attese": None, "scarto_membrature": None,
                                   "sezioni_nominali": None, "volume_atteso": None,
                                   "scarto_volume": None, "nota": ""},
                }),
                encoding="utf-8",
            )
        else:
            (cartella / pipeline.MODEL_FILENAME).write_text(
                json.dumps({
                    "tipo": tipo,
                    "sorgente": str(tmp_path / "madre"),
                    "modello": {
                        "tipo": tipo, "membrature": 4, "giunzioni": 3, "ties": 2,
                        "element_type": "C3D8I",
                        "nodi_dipendenti_legati": 18, "nodi_dipendenti_totali": 24,
                    },
                    "hexa": {"hexes": 5000, "nodes": 7000, "inverted": 0,
                              "total_volume": 0.98e8,
                              "scaled_jacobian": {"p50": 0.95, "min": 0.61}},
                    "export": {"volume": 0.98e8, "mass": 0.245, "element_type": "C3D8I"},
                    "scostamento_nuvola": {"rms": 6.2, "max": 21.0, "nota": ""},
                    "nota_giunzioni": nota_giunzioni,
                }),
                encoding="utf-8",
            )
        cartelle.append(cartella)
    return cartelle
