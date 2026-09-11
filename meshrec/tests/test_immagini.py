"""Il nome del file e la scrittura dell'immagine salvata accanto alla corsa.

La regola di nome vive due volte, in `app.js` (per il messaggio a video) e
qui (per il file su disco): `test_app_js.py` verifica che coincidano.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from meshrec.app import immagini

PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.mark.parametrize("corsa, numero, nome, didascalia, atteso", [
    ("runs/lab_telaio_v2", 6, "Riparazione", "scarto RMS 9,5 mm", "lab-telaio-v2-06-riparazione-scarto-rms-9-5-mm.png"),
    ("corsa", 5, "Superficie", "", "corsa-05-superficie.png"),
    ("runs\\lab", 1, "Lettura", "", "lab-01-lettura.png"),
    ("runs/lab/", 1, "Lettura", "", "lab-01-lettura.png"),
    ("", 1, "Lettura", "", "corsa-01-lettura.png"),
    ("lab", 2, "Perché", "città à è", "lab-02-perche-citta-a-e.png"),
    ("lab", 3, "../../etc", "/passwd", "lab-03-etc-passwd.png"),
    ("lab", 4, "", "", "lab-04.png"),
])
def test_il_nome_del_file_segue_la_regola_di_app_js(corsa, numero, nome, didascalia, atteso):
    assert immagini.nome_dell_immagine(corsa, numero, nome, didascalia) == atteso


def test_decodifica_un_data_url_png():
    dati = "data:image/png;base64," + base64.b64encode(PNG_MINIMO).decode("ascii")
    assert immagini.decodifica_png(dati) == PNG_MINIMO


@pytest.mark.parametrize("dati", [
    "",
    "data:image/jpeg;base64,AAAA",
    "data:image/png;base64,***non-base64***",
    "data:image/png;base64," + base64.b64encode(b"GIF89a").decode("ascii"),
])
def test_un_data_url_che_non_e_un_png_viene_rifiutato(dati):
    with pytest.raises(ValueError):
        immagini.decodifica_png(dati)


def test_salva_scrive_dentro_immagini_e_sovrascrive(tmp_path: Path):
    primo = immagini.salva(tmp_path / "corsa", 5, "Superficie", "", PNG_MINIMO)
    assert primo == tmp_path / "corsa" / "immagini" / "corsa-05-superficie.png"
    assert primo.read_bytes() == PNG_MINIMO
    secondo = immagini.salva(tmp_path / "corsa", 5, "Superficie", "", PNG_MINIMO + b"x")
    assert secondo == primo
    assert primo.read_bytes() == PNG_MINIMO + b"x"
    assert sorted(p.name for p in primo.parent.iterdir()) == ["corsa-05-superficie.png"]


def test_salva_non_esce_dalla_cartella_immagini(tmp_path: Path):
    percorso = immagini.salva(tmp_path / "corsa", 1, "../../fuori", "..", PNG_MINIMO)
    assert percorso.parent == tmp_path / "corsa" / "immagini"
    assert not (tmp_path / "fuori").exists()


def test_immagini_che_e_un_file_e_non_una_cartella_dice_il_percorso(tmp_path: Path):
    (tmp_path / "corsa").mkdir()
    (tmp_path / "corsa" / "immagini").write_text("non una cartella")
    with pytest.raises(OSError, match="immagini"):
        immagini.salva(tmp_path / "corsa", 1, "Lettura", "", PNG_MINIMO)
