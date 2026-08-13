"""
Fase 0 — Verifica di fattibilita di fTetWild (wildmeshing).

NOTA PIATTAFORMA (win_amd64):
wildmeshing==0.4.1 non ha wheel per Windows. Installazione fallita con:
  "Distribution `wildmeshing==0.4.1 @ registry+https://pypi.org/simple` can't be
   installed because it doesn't have a source distribution or wheel for the
   current platform. You're on Windows (win_amd64), but wildmeshing (v0.4.1)
   only has wheels for: manylinux_2_17_x86_64, manylinux2014_x86_64,
   macosx_13_0_x86_64, macosx_14_0_arm64"

Esito: SKIP atteso. Ripiego adottato per Fase 1: TetGen + PyMeshFix con guardia
di superficie chiusa mantenuta.

Su Linux/macOS: test skippa se il pacchetto non e' installato, passa se presente.
"""

import numpy as np
import pytest

from meshrec.core import quality, synth

pytestmark = pytest.mark.feasibility

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_ftetwild_meshes_a_punched_box():
    wildmeshing = pytest.importorskip("wildmeshing")

    vertices, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    tetrahedralizer = wildmeshing.Tetrahedralizer(stop_quality=10)
    tetrahedralizer.set_mesh(
        np.asarray(vertices, dtype=np.float64),
        np.asarray(damaged, dtype=np.int32),
    )
    tetrahedralizer.tetrahedralize()

    result = tetrahedralizer.get_tet_mesh()
    nodes = np.asarray(result[0], dtype=np.float64)
    tets = np.asarray(result[1], dtype=np.int64)

    assert len(tets) > 10
    total = np.abs(quality.tet_volumes(nodes, tets)).sum()
    assert total == pytest.approx(EXACT_VOLUME, rel=0.10)
