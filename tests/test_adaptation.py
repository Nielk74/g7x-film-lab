import unittest
import numpy as np
from g7xfilm.adaptation import calibrate_display_shaper


class AdaptationTests(unittest.TestCase):
    def test_extended_model_range_does_not_flatten_white(self):
        x = np.linspace(0, 2, 4097)
        y = 1 - np.exp(-2 * x)
        ramp = np.stack([y] * 3, -1)
        s = calibrate_display_shaper(x, ramp, identity_share=.7, black=.035, white=.96)
        self.assertTrue(np.all(np.diff(s.exposure) > 0))
        recovered = np.interp(s.exposure, x, y)
        np.testing.assert_allclose(recovered, s.target_neutral, atol=1e-12)
        self.assertGreater(s.exposure[-1], 1)

    def test_unreachable_white_is_rejected_instead_of_clamped(self):
        x = np.linspace(0, 2, 4097)
        y = .8 * (1 - np.exp(-2 * x))
        with self.assertRaisesRegex(ValueError, "outside"):
            calibrate_display_shaper(x, np.stack([y] * 3, -1), identity_share=.7, black=.03, white=.96)

    def test_reversed_model_gray_response_fails(self):
        x = np.linspace(0, 2, 100)
        y = np.sin(x * 3)
        with self.assertRaisesRegex(ValueError, "monotonic"):
            calibrate_display_shaper(x, np.stack([y] * 3, -1), identity_share=.7, black=.03, white=.96)


if __name__ == "__main__": unittest.main()
