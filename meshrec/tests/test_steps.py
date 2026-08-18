"""Registro degli step, catena di impronte, stato di una corsa."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshrec.core import steps
from meshrec.core.config import InputConfig, PipelineConfig
from materiale import ANALISI


def _config(tmp_path: Path) -> PipelineConfig:
    cfg = PipelineConfig(input=InputConfig(path=tmp_path / "nuvola.ply"), analysis=ANALISI)
    cfg.run.out_dir = tmp_path / "corsa"
    return cfg


def test_i_dodici_step_sono_quelli_che_la_pipeline_scrive():
    assert steps.STEP_KEYS[0] == "01_load"
    assert steps.STEP_KEYS[-1] == "12_wall"
    assert len(steps.STEP_KEYS) == 12
    assert set(steps.STEP_BLOCKS) == set(range(1, 13))


def test_una_corsa_mai_eseguita_ha_tutti_gli_step_mai_eseguiti(tmp_path):
    stato = steps.run_state(tmp_path / "vuota", _config(tmp_path))
    assert len(stato) == 12
    assert {voce["stato"] for voce in stato} == {"mai eseguito"}


def test_cambiare_un_parametro_invalida_solo_da_li_in_giu(tmp_path):
    """Prova a variabile unica: cambia surface.poisson_depth e nient'altro."""
    prima = _config(tmp_path)
    dopo = _config(tmp_path)
    dopo.surface.poisson_depth = 7

    marchi_prima = steps.step_fingerprints(prima)
    marchi_dopo = steps.step_fingerprints(dopo)

    for numero in (1, 2, 3, 4):
        assert marchi_prima[numero] == marchi_dopo[numero], f"step {numero} non doveva cambiare"
    for numero in (5, 6, 7, 8, 9, 10, 11):
        assert marchi_prima[numero] != marchi_dopo[numero], f"step {numero} doveva cambiare"


def test_uno_stato_salvato_con_impronta_diversa_e_non_valido(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    marchi = steps.step_fingerprints(cfg)
    (corsa / steps.STATE_FILENAME).write_text(
        json.dumps(
            {
                "01_load": {"impronta": marchi[1], "esito": "riuscito", "artefatto": "01_cloud.ply"},
                "05_reconstruct": {"impronta": "altro", "esito": "riuscito", "artefatto": None},
            }
        ),
        encoding="utf-8",
    )
    per_chiave = {voce["chiave"]: voce["stato"] for voce in steps.run_state(corsa, cfg)}
    assert per_chiave["01_load"] == "valido"
    assert per_chiave["05_reconstruct"] == "non valido"
    assert per_chiave["09_tetrahedralize"] == "mai eseguito"


def test_uno_steps_json_troncato_non_solleva_e_non_rassicura(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / steps.STATE_FILENAME).write_text('{"01_load": {"impro', encoding="utf-8")
    assert {voce["stato"] for voce in steps.run_state(corsa, cfg)} == {"mai eseguito"}


def test_lo_stato_si_scrive_uno_step_alla_volta(tmp_path):
    corsa = tmp_path / "corsa"
    steps.write_state(corsa, 1, "abc", "riuscito", "01_cloud.ply", 2.5)
    steps.write_state(corsa, 2, "def", "riuscito", "02_segmented.ply", 9.0)
    salvato = steps.read_state(corsa)
    assert salvato["01_load"]["impronta"] == "abc"
    assert salvato["02_segment"]["secondi"] == 9.0
    assert len(salvato) == 2, "scrivere uno step non deve cancellare gli altri"


def test_uno_step_fallito_resta_fallito_anche_con_l_impronta_giusta(tmp_path):
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    marchi = steps.step_fingerprints(cfg)
    steps.write_state(corsa, 5, marchi[5], "fallito", None, 1.0)
    per_chiave = {voce["chiave"]: voce["stato"] for voce in steps.run_state(corsa, cfg)}
    assert per_chiave["05_reconstruct"] == "fallito"


def test_una_voce_di_stato_non_dizionario_non_solleva(tmp_path):
    """Il contratto del modulo: uno stato illeggibile e' uno stato assente."""
    cfg = _config(tmp_path)
    corsa = tmp_path / "corsa"
    corsa.mkdir()
    (corsa / steps.STATE_FILENAME).write_text(
        json.dumps({"01_load": "troncato", "05_reconstruct": 5}), encoding="utf-8"
    )
    per_chiave = {voce["chiave"]: voce["stato"] for voce in steps.run_state(corsa, cfg)}
    assert per_chiave["01_load"] == "mai eseguito"
    assert per_chiave["05_reconstruct"] == "mai eseguito"


def test_gli_step_sono_dodici_e_l_ultimo_e_il_prior():
    assert len(steps.STEP_KEYS) == 12
    assert steps.STEP_KEYS[-1] == "12_wall"
    assert steps.STEP_BLOCKS[12] == ("wall",)


def test_lo_step_dodici_non_cambia_le_impronte_degli_undici_precedenti(tmp_path):
    """La catena di impronte si allunga in coda: aggiungere lo step 12 non puo'
    invalidare un artefatto gia' scritto dagli step precedenti."""
    cfg = _config(tmp_path)
    impronte = steps.step_fingerprints(cfg)
    assert set(impronte) == set(range(1, 13))

    cfg_diverso = _config(tmp_path)
    cfg_diverso.wall.min_cells = cfg.wall.min_cells + 1
    diverse = steps.step_fingerprints(cfg_diverso)

    for numero in range(1, 12):
        assert diverse[numero] == impronte[numero], f"lo step {numero} non doveva cambiare"
    assert diverse[12] != impronte[12]
