#!/usr/bin/env python3
"""Bake five fixed, pointwise spectral models; generate original PF3 files."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from g7xfilm.lut import LUT, identity, read_cube, write_cube
from g7xfilm.pf3 import build_profile, calibrate_identity, parse_profile
from g7xfilm.adaptation import calibrate_display_shaper, neutral_print_timing

ENGINE_COMMIT = "3a789c436716c902654f248166ebb4f580611146"
LOOKS = [
    {"id": "portra400", "name": "Portra 400", "title": "G7X Portra 400", "filename": "G7P400.PF3", "identity_share": .72, "black": .035, "white": .960},
    {"id": "gold200", "name": "Gold 200", "title": "G7X Gold 200", "filename": "G7G200.PF3", "identity_share": .65, "black": .025, "white": .960},
    {"id": "ektar100", "name": "Ektar 100", "title": "G7X Ektar 100", "filename": "G7E100.PF3", "identity_share": .52, "black": .020, "white": .965},
    {"id": "pro400h", "name": "Pro 400H", "title": "G7X Pro 400H", "filename": "G7F400.PF3", "identity_share": .78, "black": .040, "white": .960},
    {"id": "trix400", "name": "Tri-X 400", "title": "G7X Tri-X 400", "filename": "G7TX400.PF3", "identity_share": .40, "black": .015, "white": .960},
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(engine, stock, rgb, name, *, width=None):
    folder = ROOT / ".cache/bakes"
    folder.mkdir(parents=True, exist_ok=True)
    points = np.asarray(rgb, dtype="<f4").reshape(-1, 3)
    width = width or len(points)
    if len(points) % width:
        raise ValueError("Point count must divide the selected width")
    source, target = folder / f"{name}-input.f32", folder / f"{name}-output.f32"
    points.tofile(source)
    request = {"stock": stock, "input": str(source), "output": str(target),
               "width": width, "height": len(points) // width, "grade": 2, "exposureEV": 0}
    path = folder / f"{name}-request.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    proc = subprocess.run([str(engine), str(path)], text=True, capture_output=True, check=True)
    (folder / f"{name}-stdout.txt").write_text(proc.stdout)
    (folder / f"{name}-stderr.txt").write_text(proc.stderr)
    # Native engine can emit optional diagnostic lines before the receipt.
    text = proc.stdout
    receipt = json.loads(text[text.index("{"):])
    values = np.fromfile(target, dtype="<f4")
    if values.size != points.size:
        raise ValueError("Baker output has wrong byte count")
    output = values.reshape(np.asarray(rgb).shape).astype(np.float64)
    if not np.isfinite(output).all() or output.min() < 0 or output.max() > 1:
        raise ValueError("Baker produced non-finite or out-of-range output")
    for field in ("input", "output"):
        receipt.pop(field, None)
    return output, receipt


def build(engine, size=65, only=None):
    if size not in {33, 65}:
        raise ValueError("Use 33 or 65 samples per axis")
    calibration = calibrate_identity((ROOT / "resources/neutral-calibration.pf3").read_bytes())
    records = []
    for item in LOOKS:
        if only and item["id"] not in only:
            continue
        print("Sampling", item["name"], flush=True)
        gray_axis = np.linspace(0, 2, 4097)
        gray, _ = evaluate(engine, item["id"], np.stack([gray_axis] * 3, -1), item["id"] + "-gray")
        shaper = calibrate_display_shaper(gray_axis, gray,
            identity_share=item["identity_share"], black=item["black"], white=item["white"])
        grid = identity(size)
        table, receipt = evaluate(engine, item["id"], shaper.apply(grid), item["id"] + f"-{size}", width=size * size)
        table = neutral_print_timing(table, gray)
        shaper_path = ROOT / "research/shapers" / (item["id"] + ".json")
        shaper_path.parent.mkdir(exist_ok=True, parents=True)
        shaper_path.write_text(json.dumps({
            "input_axis": shaper.axis.tolist(), "internal_exposure_coordinate": shaper.exposure.tolist(),
            "target_neutral_mean": shaper.target_neutral.tolist(),
            "model_gray_rgb": gray.tolist(),
            "neutral_timing": "Fixed model-gray crossover subtraction; encoded RGB soft containment knee .90 ceiling .995",
            "identity_share": item["identity_share"], "black": item["black"], "white": item["white"],
            "model_exposure_domain": [0, 2], "public_input_domain": [0, 1],
            "note": "Authored display-input adaptation, not measured film/Canon calibration. No inverse clamping."
        }, indent=2) + "\n")
        cube = ROOT / "luts" / (item["id"] + ".cube")
        write_cube(cube, LUT(item["title"], table), comments=[
            "G7X Film Lab 0.1.0 - manufacturer-data-based film-inspired color and tone",
            "INPUT / OUTPUT: encoded SDR sRGB IEC61966-2-1, D65, range 0..1. NOT LOG.",
            "Fixed 5500 K simulated light; Graded Print, grade 2; no auto levels or spatial effects.",
            f"Authored display-input pre-shaper: identity share {item['identity_share']}, black {item['black']}, white {item['white']}.",
            "Derived from Fotufilm film profiles, Copyright 2026 MUAStudio Inc. https://fotufilm.com",
            "Profile-derived LUT/PF3 data: CC BY-SA 4.0. Modified/baked by G7X Film Lab contributors.",
            f"Fotufilm engine/profile revision {ENGINE_COMMIT}.",
            "No grain/halation in a 3D LUT. No claim of matching a measured G7X III/film scan pair.",
            "Authored neutral print timing and soft gamut delivery; no per-image automatic correction.",
        ])
        lut = read_cube(cube)
        camera = lut.table[::2, ::2, ::2] if size == 65 else lut.table
        pf3 = ROOT / "profiles" / item["filename"]
        pf3.parent.mkdir(parents=True, exist_ok=True)
        encoded = build_profile(camera, item["title"], calibration)
        pf3.write_bytes(encoded)
        decoded = parse_profile(encoded, calibration)
        np.testing.assert_allclose(decoded.lut_array(), camera, atol=.5 / 4095 + 1e-10)
        records.append({**item,
            "cube": str(cube.relative_to(ROOT)), "cube_size": size, "cube_sha256": sha(cube),
            "pf3": str(pf3.relative_to(ROOT)), "pf3_size": len(encoded), "pf3_sha256": sha(pf3),
            "pf3_grid": 33, "pf3_channel_bits": 12,
            "display_shaper": str(shaper_path.relative_to(ROOT)),
            "pf3_table_sha256": hashlib.sha256(decoded.fields[0x1070].data).hexdigest(),
            "model": receipt,
        })
        print("Wrote", cube.name, pf3.name, flush=True)
    manifest = ROOT / "research/bake-manifest.json"
    if only and manifest.exists():
        old = json.loads(manifest.read_text())
        retained = [x for x in old["looks"] if x["id"] not in only]
        records = sorted(retained + records, key=lambda x: [y["id"] for y in LOOKS].index(x["id"]))
    data = {"version": "0.1.0", "upstream": "https://github.com/DhaliwalX/fotufilm-engine",
            "upstream_commit": ENGINE_COMMIT, "data_license": "CC-BY-SA-4.0",
            "input_contract": "encoded SDR sRGB IEC61966-2-1; Neutral-like rendering; fixed white balance",
            "camera_registration_tested": False, "camera_jpeg_match_tested": False,
            "looks": records}
    manifest.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", type=Path, default=ROOT / "tools/FilmBake/.build/release/film-bake")
    p.add_argument("--size", type=int, default=65)
    p.add_argument("--only", choices=[x["id"] for x in LOOKS], action="append")
    args = p.parse_args()
    build(args.engine.resolve(), args.size, args.only)
