#!/usr/bin/env python3
"""Project the five LUTs into Canon's active parametric Picture Style fields."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from g7xfilm.lut import identity, read_cube
from g7xfilm.parametric import fit_lut
from g7xfilm.pf3 import build_profile, calibrate_identity, encode_fields, parse_profile


def main():
    manifest_path = ROOT / "research/bake-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    calibration = calibrate_identity((ROOT / "resources/neutral-calibration.pf3").read_bytes())
    destination = ROOT / "research/camera-fits"
    destination.mkdir(parents=True, exist_ok=True)
    for item in manifest["looks"]:
        lut = read_cube(ROOT / item["cube"])
        print("Fitting", item["name"], flush=True)
        fit = fit_lut(lut.table)
        # Canon's correctly initialized G7 X III camera compiler consumes the
        # dense table, while native DPP renders the parametric editing fields.
        # Keep the complete sampled look for camera compilation and a measured
        # approximation for desktop DPP preview; do not replace the dense look.
        camera = lut.table[::2, ::2, ::2] if lut.size == 65 else lut.table
        encoded = build_profile(camera, item["title"], calibration)
        fields = dict(parse_profile(encoded, calibration).fields)
        fields.update(fit)
        encoded = encode_fields(fields, calibration)
        profile = parse_profile(encoded, calibration)
        np.testing.assert_allclose(profile.lut_array(), camera, atol=.5/4095 + 1e-12)
        path = ROOT / item["pf3"]
        path.write_bytes(encoded)
        projection_path = destination / (item["id"] + ".json")
        projection_path.write_text(json.dumps({
            "look": item["id"], "report": fit.report,
            "fields": {hex(key): {"kind": field.kind, "data_hex": field.data.hex()} for key, field in fit.items()},
            "native_canon_render_tested": False,
        }, indent=2) + "\n")
        item.update({"pf3_sha256": hashlib.sha256(encoded).hexdigest(),
                     "pf3_size": len(encoded),
                     "pf3_table_sha256": hashlib.sha256(profile.fields[0x1070].data).hexdigest(),
                     "camera_projection": str(projection_path.relative_to(ROOT)),
                     "pf3_representation": "complete 33-cubed camera table plus parametric DPP preview approximation"})
        print(fit.report["selected"]["holdout"], flush=True)
    manifest["camera_format_note"] = "PF3 contains complete 33-cubed look tables for camera compilation and a separate parametric approximation for native DPP preview. Physical camera output remains untested."
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__": main()
