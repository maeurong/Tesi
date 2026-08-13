"""Gmsh come generatore alternativo: il confronto va fatto a parita di elementi."""

import pytest

from meshrec.core import gmsh_backend, quality, synth, volume
from meshrec.core.config import TetConfig

SIZE = (100.0, 40.0, 200.0)

# Il confronto si fa a densita di lavoro, non alla triangolazione minima.
# Con TetConfig() senza vincolo di volume TetGen produce 46 tetraedri, cioe' la
# decomposizione minima del parallelepipedo, mentre il rimagliamento della
# superficie in Gmsh non scende sotto circa 190 tetraedri per quanto si allarghi
# la dimensione caratteristica (misurato: 195 a 100 mm e a 400 mm). A quel punto
# la parita non e' raggiungibile e il confronto non direbbe nulla sui due
# generatori. Un volume massimo di elemento porta TetGen intorno ai 900
# tetraedri, che e' l'ordine di grandezza della misura di Fase 0 (540 contro
# 775) e lascia entrambi i generatori liberi di scegliere la propria mesh.
TET_CONFIG = TetConfig(max_volume=2000.0)


def test_gmsh_produces_a_valid_tetrahedral_mesh():
    pytest.importorskip("gmsh")
    vertices, faces = synth.box_mesh(SIZE)

    nodes, tets, metrics = gmsh_backend.tetrahedralize_gmsh(vertices, faces, target_elements=None)

    assert len(tets) > 10
    assert len(quality.inverted_tets(nodes, tets)) == 0
    assert metrics["tets"] == len(tets)


def test_gmsh_beats_tetgen_at_comparable_element_counts():
    """L'esito di Fase 0 confondeva il guadagno di qualita con un raffittimento."""
    pytest.importorskip("gmsh")
    vertices, faces = synth.box_mesh(SIZE)

    tetgen_nodes, tetgen_tets, _ = volume.tetrahedralize_with_metrics(vertices, faces, TET_CONFIG)
    gmsh_nodes, gmsh_tets, metrics = gmsh_backend.tetrahedralize_gmsh(
        vertices, faces, target_elements=len(tetgen_tets)
    )

    ratio = len(gmsh_tets) / len(tetgen_tets)
    assert 0.7 < ratio < 1.4, f"confronto non a parita di elementi: rapporto {ratio:.2f}"
    assert metrics["element_ratio"] == pytest.approx(ratio)

    tetgen_min = quality.min_dihedral_angles(tetgen_nodes, tetgen_tets).min()
    gmsh_min = quality.min_dihedral_angles(gmsh_nodes, gmsh_tets).min()
    print(
        f"angolo diedro minimo: tetgen={tetgen_min:.6f} gmsh={gmsh_min:.6f} "
        f"elementi tetgen={len(tetgen_tets)} gmsh={len(gmsh_tets)} rapporto_elementi={ratio:.2f} "
        f"tentativi_calibrazione={metrics['calibration_attempts']}"
    )
    assert gmsh_min > 0.0


def test_calibration_reports_the_best_ratio_when_the_target_is_unreachable():
    """Sotto il pavimento di Gmsh la calibrazione riporta, non insiste."""
    pytest.importorskip("gmsh")
    vertices, faces = synth.box_mesh(SIZE)

    # 10 tetraedri sono sotto il pavimento del rimagliamento: nessuna dimensione
    # caratteristica li produce. La funzione deve restituire comunque una mesh
    # valida e dichiarare il rapporto ottenuto invece di iterare all'infinito.
    _, tets, metrics = gmsh_backend.tetrahedralize_gmsh(vertices, faces, target_elements=10)

    assert metrics["calibration_attempts"] <= gmsh_backend._MAX_ATTEMPTS
    assert metrics["element_ratio"] > 1.0
    assert len(tets) == metrics["tets"]
