"""Fase 0 — PyMeshFix riesce a chiudere una superficie forata?"""

import numpy as np
import pytest

from meshrec import quality, synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_pymeshfix_closes_a_punched_box():
    pymeshfix = pytest.importorskip("pymeshfix")

    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))
    assert not quality.is_watertight(damaged)

    fixer = pymeshfix.MeshFix(np.asarray(vertices), np.asarray(damaged, dtype=np.int32))
    fixer.repair()

    # API reale di pymeshfix 0.18.1: .points/.faces, non .v/.f come previsto dal piano.
    repaired_vertices = np.asarray(fixer.points, dtype=np.float64)
    repaired_faces = np.asarray(fixer.faces, dtype=np.int64)

    assert len(repaired_faces) > 0
    assert quality.is_watertight(repaired_faces)
    assert abs(quality.mesh_volume(repaired_vertices, repaired_faces)) == pytest.approx(
        EXACT_VOLUME, rel=0.05
    )
