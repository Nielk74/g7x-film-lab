# SPDX-License-Identifier: MIT
import struct
import unittest

import numpy as np

from g7xfilm.parametric import curve_cache, fit_lut, polynomial_basis


class ParametricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        axis = np.linspace(0, 1, 17)
        cls.grid = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)

    def test_basis_has_observed_rgb_order_and_no_constant(self):
        rgb = np.array([.2, .3, .4])
        terms = polynomial_basis(rgb)
        np.testing.assert_allclose(terms[:9], [.2, .3, .4, .04, .06, .08, .09, .12, .16])
        self.assertEqual(len(terms), 19)
        np.testing.assert_array_equal(polynomial_basis(np.zeros(3)), np.zeros(19))

    def test_identity_and_three_point_curve_are_monotonic(self):
        identity = curve_cache([[0, 0], [255, 255]])
        np.testing.assert_allclose(identity, np.linspace(0, 1, 256), atol=1e-15)
        darkened = curve_cache([[0, 0], [128, 64], [255, 255]])
        self.assertAlmostEqual(darkened[128], 64/255, places=12)
        self.assertTrue(np.all(np.diff(darkened) >= 0))
        self.assertGreater(identity[128], darkened[128])

    def test_reject_invalid_curve_domains(self):
        for points in ([[0, 0], [128, 10], [128, 20], [255, 255]],
                       [[1, 0], [255, 255]], [[0, 10], [255, 0]]):
            with self.assertRaises(ValueError):
                curve_cache(points)

    def test_fit_identity_and_storage_have_no_second_tone_curve(self):
        fit = fit_lut(self.grid, validation_samples=512, training_grid=9)
        random = np.random.default_rng(57).uniform(0, 1, (512, 3))
        np.testing.assert_allclose(fit.evaluate(random), random, atol=1e-4)
        self.assertEqual(set(fit), {0x1021, 0x1029, 0x1018, 0x1065, 0x1019})
        matrix = np.frombuffer(fit[0x1021].data, dtype="<i4").reshape(3, 20)
        np.testing.assert_array_equal(matrix[:, -1], [0, 0, 0])
        self.assertEqual(fit[0x1021], fit[0x1029])
        words = struct.unpack("<75I", fit[0x1019].data)
        self.assertEqual(words[:5], (2, 0, 0, 255, 255))

    def test_fit_nonidentity_is_evaluated_and_reported_as_approximation(self):
        target = self.grid @ np.array([[.8, .15, .05], [.05, .9, .05], [.05, .15, .8]]).T
        fit = fit_lut(target, validation_samples=512, training_grid=9)
        reference = target.reshape(-1, 3)
        np.testing.assert_allclose(fit.evaluate(self.grid).reshape(-1, 3), reference, atol=.001)
        self.assertFalse(fit.report["native_camera_validated"])
        self.assertGreater(len(fit.report["candidates"]), 1)

    def test_fit_monochrome_preserves_equal_channels(self):
        luminance = self.grid @ np.array([.3, .6, .1])
        target = np.repeat(luminance[..., None], 3, axis=-1)
        fit = fit_lut(target, validation_samples=512, training_grid=9)
        predicted = fit.evaluate(self.grid)
        np.testing.assert_array_equal(predicted[..., 0], predicted[..., 1])
        np.testing.assert_array_equal(predicted[..., 1], predicted[..., 2])
        self.assertTrue(fit.report["monochrome"])


if __name__ == "__main__":
    unittest.main()
