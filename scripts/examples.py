#!/usr/bin/env python3
"""Render licensed photographs through the exact released CUBE files."""
from pathlib import Path
import json
import hashlib
import sys
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from g7xfilm.cli import load_srgb, apply_image
from g7xfilm.lut import read_cube


def font(size):
    return ImageFont.load_default(size=size)


def fitted(image, width, height):
    image = image.copy()
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#f2efe9")
    canvas.paste(image, ((width-image.width)//2, (height-image.height)//2))
    return canvas


def main():
    manifest = json.loads((ROOT / "research/bake-manifest.json").read_text())
    sources = json.loads((ROOT / "research/example-sources.json").read_text())["images"]
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    rows, source_images = [], {}
    for item in sources:
        path = ROOT / "examples/source" / (item["id"] + (".png" if item["id"] == "g7x-iii-canon-neutral" else ".jpg"))
        source_images[item["id"]] = load_srgb(path).convert("RGB")
    rendered = {}
    for look in manifest["looks"]:
        lut = read_cube(ROOT / look["cube"])
        rendered[look["id"]] = {}
        folder = ROOT / "examples/rendered" / look["id"]
        folder.mkdir(parents=True, exist_ok=True)
        for name, image in source_images.items():
            out = apply_image(image, lut)
            target = folder / (name + ".jpg")
            out.save(target, quality=94, subsampling=0, icc_profile=icc)
            rendered[look["id"]][name] = out
            rows.append({"look": look["id"], "source": name,
                         "lut_sha256": look["cube_sha256"],
                         "output": str(target.relative_to(ROOT)),
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        # Two identical-input comparisons per stock: skin and exact-camera RAW.
        page = Image.new("RGB", (1200, 1020), "#f2efe9")
        draw = ImageDraw.Draw(page)
        draw.text((24, 16), look["name"] + "  /  sRGB LUT preview", fill="#20201e", font=font(25))
        draw.text((24, 55), "Original", fill="#55554f", font=font(18))
        draw.text((624, 55), look["name"], fill="#55554f", font=font(18))
        for index, name in enumerate(["skin-portrait", "g7x-iii-canon-neutral"]):
            y = 86 + index * 450
            page.paste(fitted(source_images[name], 584, 420), (8, y))
            page.paste(fitted(rendered[look["id"]][name], 584, 420), (608, y))
        draw.text((24, 991), "Digital preview from the released .cube. Camera PF3 approximation has separate native Canon examples.",
                  fill="#55554f", font=font(15))
        page.save(ROOT / "previews" / (look["id"] + ".jpg"), quality=94, subsampling=0, icc_profile=icc)
    overview = Image.new("RGB", (1500, 880), "#f2efe9")
    draw = ImageDraw.Draw(overview)
    cards = [("Original Canon Neutral", source_images["g7x-iii-canon-neutral"])] + [
        (item["name"], rendered[item["id"]]["g7x-iii-canon-neutral"]) for item in manifest["looks"]]
    for index, (title, image) in enumerate(cards):
        x, y = (index % 3) * 500, (index // 3) * 440
        draw.text((x+14, y+14), title, fill="#20201e", font=font(21))
        overview.paste(fitted(image, 484, 376), (x+8, y+48))
    overview.save(ROOT / "previews/overview.jpg", quality=94, subsampling=0, icc_profile=icc)
    (ROOT / "research/example-renders.json").write_text(json.dumps({
        "method": "Tetrahedral interpolation of the exact released CUBE; no extra grading, grain, sharpening or per-image auto settings.",
        "scope": "Desktop LUT previews; not physical film scans or camera JPEGs.", "renders": rows
    }, indent=2) + "\n")
    print("Rendered", len(rows), "photo examples and six comparison sheets.")


if __name__ == "__main__": main()
