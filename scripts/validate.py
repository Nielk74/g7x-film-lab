#!/usr/bin/env python3
"""Verify all released data and deterministically reconstruct all five PF3s."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from g7xfilm.lut import read_cube
from g7xfilm.pf3 import Field, build_profile, calibrate_identity, encode_fields, parse_profile


def validate():
    manifest = json.loads((ROOT / "research/bake-manifest.json").read_text())
    assert len(manifest["looks"]) == 5
    assert {x["id"] for x in manifest["looks"]} == {"portra400", "gold200", "ektar100", "pro400h", "trix400"}
    assert len(list((ROOT / "luts").glob("*.cube"))) == 5
    assert len(list((ROOT / "profiles").glob("*.PF3"))) == 5
    calibration = calibrate_identity((ROOT / "resources/neutral-calibration.pf3").read_bytes())
    for item in manifest["looks"]:
        for key in ("cube", "pf3"):
            assert hashlib.sha256((ROOT / item[key]).read_bytes()).hexdigest() == item[key + "_sha256"]
        cube = read_cube(ROOT / item["cube"])
        assert cube.size == 65
        expected = cube.table[::2, ::2, ::2]
        raw = (ROOT / item["pf3"]).read_bytes()
        profile = parse_profile(raw, calibration)
        assert profile.title == item["title"] and profile.base_style == 0x84
        assert profile.fields[0x1070] == profile.fields[0x1071]
        np.testing.assert_allclose(profile.lut_array(), expected, atol=.5/4095 + 1e-10)
        projection = json.loads((ROOT / item["camera_projection"]).read_text())
        extra = {int(key, 16): Field(value["kind"], bytes.fromhex(value["data_hex"]))
                 for key, value in projection["fields"].items()}
        reconstructed = dict(parse_profile(build_profile(expected, item["title"], calibration), calibration).fields)
        reconstructed.update(extra)
        assert encode_fields(reconstructed, calibration) == raw
        gray = np.linspace(0, 1, 8193)
        response = cube.apply(np.stack([gray] * 3, axis=-1))
        assert np.min(np.diff(response.mean(axis=-1))) > 0, "Flat or reversed gray interval"
        if item["id"] == "trix400":
            assert np.ptp(cube.table, axis=-1).max() < 2e-5
    examples = json.loads((ROOT / "research/example-renders.json").read_text())
    assert len(examples["renders"]) == 25
    for row in examples["renders"]:
        assert hashlib.sha256((ROOT / row["output"]).read_bytes()).hexdigest() == row["sha256"]
        look = next(x for x in manifest["looks"] if x["id"] == row["look"])
        assert row["lut_sha256"] == look["cube_sha256"]
    # Final native receipts must refer to the exact released files.
    native_path = ROOT / "research/canon-native-validation.json"
    if native_path.exists():
        native_text = native_path.read_text()
        for row in manifest["looks"]:
            assert row["pf3_sha256"] in native_text, "Stale native Canon validation receipt"
    print("Verified five LUTs, exact PF3 reconstruction, gray continuity and 25 linked examples.")


if __name__ == "__main__": validate()
