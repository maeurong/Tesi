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
