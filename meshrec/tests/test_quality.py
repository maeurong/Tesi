import numpy as np
import pytest

from meshrec.core import quality, synth

SIZE = (100.0, 40.0, 200.0)
EXACT_VOLUME = 100.0 * 40.0 * 200.0


def test_box_mesh_has_eight_vertices_and_twelve_triangles():
    vertices, faces = synth.box_mesh(SIZE)

    assert vertices.shape == (8, 3)
    assert faces.shape == (12, 3)
    assert vertices.min(axis=0) == pytest.approx([0.0, 0.0, 0.0])
    assert vertices.max(axis=0) == pytest.approx(list(SIZE))


def test_box_mesh_is_watertight_and_has_no_boundary_edges():
    _, faces = synth.box_mesh(SIZE)

    assert len(quality.boundary_edges(faces)) == 0
    assert quality.is_watertight(faces)


def test_box_mesh_volume_is_exact_and_positive():
    vertices, faces = synth.box_mesh(SIZE)

    assert quality.mesh_volume(vertices, faces) == pytest.approx(EXACT_VOLUME)


def test_punch_holes_opens_the_mesh():
    _, faces = synth.box_mesh(SIZE)
    damaged = synth.punch_holes(faces, remove=(0, 6))

    assert len(damaged) == 10
    # triangoli 0 e 6 condividono spigolo (1,2): sono adiacenti, quindi 4 spigoli di bordo
    assert len(quality.boundary_edges(damaged)) == 4
    assert not quality.is_watertight(damaged)
