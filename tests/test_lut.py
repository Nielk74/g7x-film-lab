import tempfile
import unittest
from pathlib import Path
import numpy as np
from g7xfilm.lut import LUT, identity, read_cube, write_cube


class LUTTests(unittest.TestCase):
    def test_identity_endpoints_ties_and_all_tetrahedra(self):
        rng = np.random.default_rng(29)
        points = np.vstack([rng.random((10000, 3)), identity(3).reshape(-1, 3)])
        np.testing.assert_allclose(LUT("identity", identity(17)).apply(points), points, atol=1e-14)

    def test_affine_mapping_in_every_cell(self):
        table = identity(5)
        matrix = np.array([[.7, .1, .1], [.1, .6, .2], [.2, .1, .5]])
        lut = LUT("affine", table @ matrix.T + .02)
        points = np.random.default_rng(7).random((2000, 3))
        np.testing.assert_allclose(lut.apply(points, chunk_size=117), points @ matrix.T + .02, atol=1e-14)

    def test_cube_axis_order_and_roundtrip(self):
        table = identity(5)[..., [2, 0, 1]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "swap.cube"
            write_cube(path, LUT("axis test", table))
            loaded = read_cube(path)
            np.testing.assert_allclose(loaded.table, table, atol=1e-9)
            points = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            np.testing.assert_equal(loaded.apply(points), points[:, [2, 0, 1]])

    def test_invalid_inputs_and_truncated_files_fail(self):
        with self.assertRaises(ValueError): LUT("bad", np.zeros((3, 3, 2, 3)))
        lut = LUT("ok", identity(3))
        for points in ([[-1, 0, 0]], [[float("nan"), 0, 0]], [[0, 0, 2]]):
            with self.assertRaises(ValueError): lut.apply(points)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.cube"
            path.write_text("LUT_3D_SIZE 2\n0 0 0\n")
            with self.assertRaises(ValueError): read_cube(path)


if __name__ == "__main__": unittest.main()
