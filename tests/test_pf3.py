"""Offline integrity, channel-order and calibration tests; no camera access."""

import os
from pathlib import Path
import random
import struct
import unittest

import numpy as np

from g7xfilm.pf3 import (
    Calibration, Field, PF3Error, build_profile, calibrate_identity,
    encode_fields, parse_profile,
)


class PF3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deliberately synthetic factors. No Canon or third-party key fixture.
        generator = random.Random(9187)
        cls.calibration = Calibration(generator.randbytes(512), generator.randbytes(513))
        axis = np.linspace(0, 1, 33)
        cls.identity = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
        cls.raw = build_profile(cls.identity, "Identity test", cls.calibration)

    def test_full_profile_controls_and_identity_channels(self):
        profile = parse_profile(self.raw, self.calibration)
        self.assertEqual(profile.byte_length, 434511)
        self.assertEqual(profile.title, "Identity test")
        self.assertEqual(profile.base_style, 0x84)
        self.assertEqual(profile.controls, {
            "sharpness": 0, "contrast": 0, "saturation": 0,
            "color_tone": 0, "fineness": 2, "threshold": 4,
        })
        np.testing.assert_allclose(profile.lut_array(), self.identity, atol=0.5 / 4095)
        self.assertEqual(encode_fields(profile.fields, self.calibration), self.raw)

    def test_independent_calibration_from_mathematical_identity(self):
        learned = calibrate_identity(self.raw)
        self.assertEqual(learned.transform(self.raw[12:]), self.calibration.transform(self.raw[12:]))
        self.assertEqual(parse_profile(self.raw, learned).title, "Identity test")
        self.assertNotIn(learned.first.hex(), repr(learned))

    def test_nonidentity_rgb_order_and_auxiliary_curve_preservation(self):
        transformed = self.identity[..., [2, 0, 1]].copy()
        result = build_profile(transformed, "RGB order test", self.calibration)
        profile = parse_profile(result, self.calibration)
        codes = profile.lut_array()
        np.testing.assert_allclose(codes[32, 0, 0], [0, 1, 0], atol=0)
        np.testing.assert_allclose(codes[0, 32, 0], [0, 0, 1], atol=0)
        np.testing.assert_allclose(codes[0, 0, 32], [1, 0, 0], atol=0)
        self.assertEqual(profile.fields[0x1070], profile.fields[0x1071])
        for identifier in (0x1018, 0x1019, 0x1065):
            self.assertEqual(profile.fields[identifier], parse_profile(self.raw, self.calibration).fields[identifier])

    def test_corruption_lengths_and_checksums_fail(self):
        changed = bytearray(self.raw)
        changed[100] ^= 1
        for invalid in (self.raw[:-1], self.raw + b"X", bytes(changed), bytes(8) + self.raw[8:]):
            with self.subTest(size=len(invalid)):
                with self.assertRaises(PF3Error):
                    parse_profile(invalid, self.calibration)

    def test_reject_invalid_lut_values_shape_and_titles(self):
        for value in (float("nan"), float("inf"), -0.00001, 1.00001):
            data = self.identity.copy()
            data[4, 3, 2, 1] = value
            with self.assertRaises(PF3Error):
                build_profile(data, "Invalid", self.calibration)
        for data in (np.zeros((17, 17, 17, 3)), np.zeros((33, 33, 33, 4))):
            with self.assertRaises(PF3Error):
                build_profile(data, "Invalid", self.calibration)
        for title in ("", "A" * 32, "café", "one\ntwo"):
            with self.assertRaises(PF3Error):
                build_profile(self.identity, title, self.calibration)

    def test_reject_typed_field_boundary_and_invalid_control(self):
        with self.assertRaises(PF3Error):
            encode_fields({0x1009: Field(3, b"x")}, self.calibration)
        with self.assertRaises(PF3Error):
            build_profile(self.identity, "Bad", self.calibration, contrast=5)
        with self.assertRaises(PF3Error):
            build_profile(self.identity, "Bad", self.calibration, base_style=0x81)

    def test_duplicate_records_and_missing_final_checksum(self):
        record = struct.pack(">HHIH", 0x1009, 3, 2, 0x84)
        for plain in (record + record + struct.pack(">HHII", 0xFFFE, 4, 4, sum(record * 2))
                      + struct.pack(">HHI", 0xFFFF, 0xFFFF, 0),
                      record + struct.pack(">HHI", 0xFFFF, 0xFFFF, 0)):
            raw = bytes.fromhex("0000300050535000") + struct.pack(">I", len(plain)) + self.calibration.transform(plain)
            with self.assertRaises(PF3Error):
                parse_profile(raw, self.calibration)

    def test_authored_reference_decodes_and_reencodes_exactly(self):
        own_reference = Path(__file__).resolve().parents[1] / "resources/neutral-calibration.pf3"
        raw = Path(os.environ.get("G7XFILM_PF3_REFERENCE", own_reference)).read_bytes()
        learned = calibrate_identity(raw)
        profile = parse_profile(raw, learned)
        self.assertEqual(encode_fields(profile.fields, learned), raw)
        self.assertEqual(len(profile.fields), 26)
        if "G7XFILM_PF3_REFERENCE" not in os.environ:
            self.assertEqual(profile.title, "G7X Lab Identity")
            self.assertEqual(build_profile(self.identity, "G7X Lab Identity", learned), raw)


if __name__ == "__main__":
    unittest.main()
