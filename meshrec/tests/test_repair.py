"""Step 6: riparazione deterministica e registrata."""

import numpy as np
import pytest

from meshrec.core import config, quality, repair, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_a_punched_box_comes_back_watertight():
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    fixed_vertices, fixed_faces, metrics = repair.repair_surface(
        vertices, damaged, config.RepairConfig()
    )

    assert quality.is_watertight(fixed_faces)
    assert metrics["watertight_after"] is True
    assert metrics["holes_before"] == 1
    assert abs(quality.mesh_volume(fixed_vertices, fixed_faces)) == pytest.approx(
        EXACT_VOLUME, rel=0.05
    )


def test_an_already_closed_box_is_left_alone():
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)

    _, fixed_faces, metrics = repair.repair_surface(vertices, faces, config.RepairConfig())

    assert metrics["holes_before"] == 0
    assert metrics["watertight_after"] is True
    assert len(fixed_faces) >= len(faces)


def test_a_hole_over_the_threshold_is_reported_not_hidden():
    """La chiusura avviene comunque, ma il foro grande finisce nelle metriche."""
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces)

    _, _, metrics = repair.repair_surface(
        vertices, damaged, config.RepairConfig(max_hole_area=100.0)
    )

    assert len(metrics["holes_over_threshold"]) == 1
    assert metrics["holes_over_threshold"][0] > 100.0


def test_a_large_opening_on_an_open_path_does_not_slip_past_the_threshold():
    """La guardia non deve essere cieca proprio sulle aperture piu grandi.

    Dopo la separazione fra cicli chiusi e cammini aperti, le aperture maggiori
    finiscono fra i secondi: sul muro reale le due facce aperte da circa 23 m2
    sono cammini aperti. Una soglia che guardasse i soli cicli chiusi le
    lascerebbe passare senza un segno, che e' l'esatto contrario del motivo per
    cui `max_hole_area` esiste. Qui il ciclo chiuso sta sotto soglia e i due
    cammini aperti sopra: se la soglia torna cieca, la lista resta vuota.
    """
    pytest.importorskip("pymeshfix")
    vertices = np.array(
        [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [-100.0, 0.0, 0.0], [0.0, -100.0, 0.0]]
    )
    faces = np.array([[0, 1, 2], [0, 3, 4]], dtype=np.int64)

    _, _, metrics = repair.repair_surface(
        vertices, faces, config.RepairConfig(largest_component_only=False, max_hole_area=6000.0)
    )

    assert metrics["holes_over_threshold"] == []
    assert len(metrics["open_paths_over_threshold"]) == 2
    assert min(metrics["open_paths_over_threshold"]) > 6000.0


def test_the_smaller_connected_component_is_dropped():
    vertices, faces = synth.box_mesh(SIZE)
    far_vertices = vertices + np.array([1000.0, 0.0, 0.0])
    both_vertices = np.vstack([vertices, far_vertices])
    both_faces = np.vstack([faces, faces + len(vertices)])

    labels = repair.component_labels(both_faces, len(both_vertices))
    assert len(np.unique(labels)) == 2

    pytest.importorskip("pymeshfix")
    kept_vertices, kept_faces, metrics = repair.repair_surface(
        both_vertices, both_faces, config.RepairConfig(largest_component_only=True)
    )
    assert metrics["components_before"] == 2
    assert metrics["components_kept"] == 1
    assert len(kept_faces) < len(both_faces)
    assert quality.is_watertight(kept_faces)
    assert metrics["watertight_after"] is True
    assert len(kept_vertices) < len(both_vertices)


def test_degenerate_and_duplicate_faces_are_removed():
    pytest.importorskip("pymeshfix")
    vertices, faces = synth.box_mesh(SIZE)
    degenerate = np.array([[0, 0, 1]])
    duplicated = faces[:1]
    dirty = np.vstack([faces, degenerate, duplicated])

    _, clean_faces, metrics = repair.repair_surface(vertices, dirty, config.RepairConfig())

    assert metrics["degenerate_faces_removed"] == 1
    assert metrics["duplicate_faces_removed"] == 1


def test_a_non_manifold_boundary_junction_does_not_loop_forever():
    """Due triangoli uniti in un solo vertice: il vertice ha quattro spigoli di bordo.

    Partendo da un vertice esterno al triangolo in cui il cammino finisce per
    entrare, la ricerca dei cicli non ripassa mai dal punto di partenza: senza
    il tetto sulla lunghezza del ciclo questa chiamata non termina e consuma
    tutta la memoria. E' il guasto che ha ucciso l'esecuzione sul muro
    sintetico, dove il trimming per densita del Poisson lascia giunzioni di
    questo tipo sui bordi.
    """
    faces = np.array([[0, 1, 2], [0, 3, 4]], dtype=np.int64)

    loops, open_paths = repair.hole_loops(faces)

    # Un cammino troncato non deve passare per un foro: i due triangoli hanno un
    # solo ciclo chiuso vero, e i cammini che si perdono nella giunzione vanno
    # contati a parte invece di diventare fori fantasma con un'area inventata.
    assert len(open_paths) > 0
    assert all(len(loop) <= len(quality.boundary_edges(faces)) for loop in loops)
    assert max(len(path) for path in open_paths) <= len(quality.boundary_edges(faces)) + 1

    _, _, metrics = repair.repair_surface(
        np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]
        ),
        faces,
        config.RepairConfig(largest_component_only=False),
    )
    assert metrics["open_boundary_paths"] > 0
    assert metrics["holes_before"] == len(metrics["hole_areas"])
