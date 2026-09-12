"""Chi e' il programma: versione, commit, licenza, DOI. Mai un errore."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from meshrec.app import identita
from meshrec.app.server import create_app


def test_senza_git_e_senza_cff_le_voci_mancanti_sono_null(tmp_path: Path):
    voci = identita.informazioni(tmp_path)
    assert voci["nome"] == "MeshRec"
    assert voci["commit"] is None
    assert voci["doi"] is None
    assert voci["doi_url"] is None
    assert voci["licenza"] == "MIT"
    assert voci["repository"].startswith("https://github.com/maeurong/")
    assert isinstance(voci["versione"], str) and voci["versione"]


def test_il_commit_e_quello_di_head(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=a@b", "-c", "user.name=a",
                    "commit", "-q", "--allow-empty", "-m", "primo"], check=True)
    atteso = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert identita.informazioni(tmp_path)["commit"] == atteso


def test_il_doi_viene_dal_citation_cff(tmp_path: Path):
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\ntitle: MeshRec\ndoi: 10.5281/zenodo.1234\n", encoding="utf-8")
    voci = identita.informazioni(tmp_path)
    assert voci["doi"] == "10.5281/zenodo.1234"
    assert voci["doi_url"] == "https://doi.org/10.5281/zenodo.1234"


def test_un_cff_valido_senza_doi_lascia_doi_a_none(tmp_path: Path):
    """Punto 7 fix wave (test mancante): CFF valido ma senza la chiave `doi`
    -- non e' il ramo illeggibile, e' un `dict` a cui manca solo quella voce."""
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\ntitle: MeshRec\n", encoding="utf-8")
    voci = identita.informazioni(tmp_path)
    assert voci["doi"] is None
    assert voci["doi_url"] is None


def test_un_cff_illeggibile_non_rompe(tmp_path: Path):
    (tmp_path / "CITATION.cff").write_text("::: non yaml :::\n  - [", encoding="utf-8")
    assert identita.informazioni(tmp_path)["doi"] is None


def test_senza_pacchetto_installato_la_versione_dice_sorgente(tmp_path: Path, monkeypatch):
    import importlib.metadata as metadata

    def manca(_nome):
        raise metadata.PackageNotFoundError("meshrec")

    monkeypatch.setattr(identita.metadata, "version", manca)
    assert identita.informazioni(tmp_path)["versione"] == "sorgente"


def test_un_cff_non_utf8_non_rompe_il_doi(tmp_path: Path):
    (tmp_path / "CITATION.cff").write_bytes(b"\xff\xfe cff")
    assert identita.informazioni(tmp_path)["doi"] is None


def test_un_cff_non_utf8_non_fa_cadere_la_rotta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "CITATION.cff").write_bytes(b"\xff\xfe cff")
    monkeypatch.setattr(identita, "RADICE_REPO", tmp_path)
    cliente = TestClient(create_app(), base_url="http://127.0.0.1")
    risposta = cliente.get("/api/info")
    assert risposta.status_code == 200
    assert risposta.json()["doi"] is None


def test_radice_repo_punta_alla_radice_vera():
    assert (identita.RADICE_REPO / "meshrec" / "pyproject.toml").is_file()
    assert (identita.RADICE_REPO / "LICENSE").is_file()


def test_informazioni_senza_argomenti_legge_il_commit_vero():
    if shutil.which("git") is None:
        pytest.skip("git non disponibile su questa macchina")
    assert identita.informazioni()["commit"] is not None
