"""Fase 0 — PyMeshLab offre remeshing isotropo e distanza di Hausdorff?"""

import numpy as np
import pytest

from meshrec.core import synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)


def _percentage(pymeshlab, value: float):
    """Il tipo percentuale ha cambiato nome fra le versioni di PyMeshLab."""
    for attribute in ("PercentageValue", "Percentage"):
        if hasattr(pymeshlab, attribute):
            return getattr(pymeshlab, attribute)(value)
    raise AssertionError("nessun tipo percentuale trovato in pymeshlab")


def _apply_first_available(pymeshlab, mesh_set, names: tuple[str, ...], **kwargs):
    """Applica il primo filtro esistente fra i nomi dati.

    ``filter_list`` e una funzione di modulo dalla 2023.x in poi, non piu un
    metodo di ``MeshSet``: proviamo prima la forma nuova, poi la vecchia.
    """
    lister = getattr(pymeshlab, "filter_list", None) or mesh_set.filter_list
    available = set(lister())
    for name in names:
        if name in available:
            return mesh_set.apply_filter(name, **kwargs)
    raise AssertionError(f"nessuno dei filtri {names} e disponibile")


def test_isotropic_remeshing_increases_triangle_regularity():
    pymeshlab = pytest.importorskip("pymeshlab")

    vertices, faces = synth.box_mesh(SIZE)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "box")

    before = mesh_set.current_mesh().face_number()
    _apply_first_available(
        pymeshlab,
        mesh_set,
        ("meshing_isotropic_explicit_remeshing", "remeshing_isotropic_explicit_remeshing"),
        targetlen=_percentage(pymeshlab, 5.0),
    )
    after = mesh_set.current_mesh().face_number()

    assert after > before  # 12 triangoli grossolani diventano molti triangoli regolari


def test_hausdorff_distance_between_a_mesh_and_itself_is_zero():
    pymeshlab = pytest.importorskip("pymeshlab")

    vertices, faces = synth.box_mesh(SIZE)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "a")
    mesh_set.add_mesh(pymeshlab.Mesh(np.asarray(vertices), np.asarray(faces)), "b")

    result = _apply_first_available(
        pymeshlab,
        mesh_set,
        ("get_hausdorff_distance", "hausdorff_distance"),
        sampledmesh=0,
        targetmesh=1,
    )

    assert result["max"] == pytest.approx(0.0, abs=1e-6)
