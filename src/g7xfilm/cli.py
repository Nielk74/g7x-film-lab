"""Optional desktop-photo preview command; camera installation needs no Python."""
from __future__ import annotations
import argparse
from io import BytesIO
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageCms, ImageOps
from .lut import read_cube


def load_srgb(path):
    with Image.open(path) as source:
        im = ImageOps.exif_transpose(source)
        icc = source.info.get("icc_profile")
        if icc:
            mode = "RGBA" if "A" in im.getbands() else "RGB"
            try:
                im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(BytesIO(icc)),
                                              ImageCms.createProfile("sRGB"), outputMode=mode)
            except (ImageCms.PyCMSError, OSError, ValueError) as exc:
                raise ValueError(f"Cannot convert embedded profile to sRGB: {exc}") from exc
        else:
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        return im.copy()


def apply_image(image, lut):
    pixels = np.asarray(image)
    result = np.rint(lut.apply(pixels[..., :3] / 255.0) * 255).astype(np.uint8)
    if pixels.shape[-1] == 4:
        result = np.concatenate([result, pixels[..., 3:4]], axis=-1)
    return Image.fromarray(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--lut", type=Path, required=True, help="One released .cube file")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() == args.input.resolve():
            raise ValueError("Choose an output path distinct from the original")
        if args.output.exists():
            raise ValueError("Output exists; choose another path")
        image = load_srgb(args.input)
        result = apply_image(image, read_cube(args.lut))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        options = {"icc_profile": icc}
        if args.output.suffix.lower() in {".jpg", ".jpeg"}:
            result = result.convert("RGB")
            options.update(quality=96, subsampling=0)
        result.save(args.output, **options)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
