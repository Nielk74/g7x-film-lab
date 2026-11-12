#!/usr/bin/env python3
"""Compare the baked LUT with its exact numerical model, not physical film."""
from pathlib import Path
import json
import sys
import numpy as np
import colour

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from bake import evaluate
from g7xfilm.lut import LUT, read_cube
from g7xfilm.adaptation import neutral_print_timing


def delta(reference, actual):
    a = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(reference))
    b = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual))
    d = colour.delta_E(a, b, method="CIE 2000")
    return {"delta_e00_mean": float(np.mean(d)), "delta_e00_p95": float(np.percentile(d, 95)),
            "delta_e00_p99": float(np.percentile(d, 99)), "delta_e00_max": float(np.max(d)),
            "encoded_rgb_rmse": float(np.sqrt(np.mean((reference-actual)**2)))}


def main():
    rng = np.random.default_rng(49004)
    points = rng.random((8192, 3))
    manifest = json.loads((ROOT / "research/bake-manifest.json").read_text())
    engine = ROOT / "tools/FilmBake/.build/release/film-bake"
    rows = []
    for item in manifest["looks"]:
        data = json.loads((ROOT / item["display_shaper"]).read_text())
        shaped = np.interp(points, data["input_axis"], data["internal_exposure_coordinate"])
        reference, _ = evaluate(engine, item["id"], shaped, item["id"] + "-holdout", width=128)
        reference = neutral_print_timing(reference, data["model_gray_rgb"])
        order = rng.permutation(len(points))
        shuffled, _ = evaluate(engine, item["id"], shaped[order], item["id"] + "-permuted", width=64)
        shuffled = neutral_print_timing(shuffled, data["model_gray_rgb"])
        difference = float(np.max(np.abs(shuffled[np.argsort(order)]-reference)))
        if difference > 2e-6:
            raise ValueError(f"{item['id']}: pixel permutation changed the model by {difference}")
        lut = read_cube(ROOT / item["cube"])
        camera = LUT(item["title"], np.rint(lut.table[::2, ::2, ::2] * 4095)/4095)
        gray_axis = np.linspace(0, 1, 8193)
        gray = lut.apply(np.stack([gray_axis] * 3, -1))
        lab = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(gray))
        row = {"id": item["id"], "samples": len(points), "seed": 49004,
               "cube_sha256": item["cube_sha256"], "pf3_sha256": item["pf3_sha256"],
               "cube65_vs_direct_model": delta(reference, lut.apply(points)),
               "quantized33_table_vs_direct_model": delta(reference, camera.apply(points)),
               "permutation_max_encoded_rgb_difference": difference,
               "neutral_max_chroma_ab": float(np.max(np.sqrt(np.sum(lab[:, 1:]**2, axis=-1)))),
               "neutral_black": gray[0].tolist(), "neutral_white": gray[-1].tolist(),
               "minimum_gray_step": float(np.min(np.diff(gray.mean(axis=-1)))),
               "maximum_gray_rgb_spread": float(np.ptp(gray, axis=-1).max())}
        print(item["id"], row["cube65_vs_direct_model"], flush=True)
        rows.append(row)
    output = {"scope": "LUT interpolation and format fidelity against the project's specified spectral model + authored display adaptation. Not accuracy against physical film or measured camera output.",
              "looks": rows, "physical_film_match_measured": False, "physical_camera_output_measured": False}
    (ROOT / "research/quality.json").write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__": main()
