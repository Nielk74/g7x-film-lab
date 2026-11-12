# Rebuild and verify

The release download needs no developer tools. These instructions are for
reproducing or changing the looks.

## Verify the checked-in pack

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[research]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate.py
.venv/bin/python scripts/check_docs.py
.venv/bin/python scripts/package.py
```

`validate.py` checks every CUBE/PF3 hash, independently decodes the profiles,
compares their complete dense tables with the CUBE samples, reconstructs all
five PF3 files byte-for-byte from public build inputs, checks gray continuity,
and verifies all 25 linked examples and final native Canon receipts.

The original mathematical `resources/neutral-calibration.pf3` provides a public
format calibration input. No private reference or Canon library is needed to
reconstruct the profiles. The neutral scaffold and codec are independently
authored. See [PF3_FORMAT.md](PF3_FORMAT.md).

## Re-bake the spectral LUTs

The numeric sampler in `tools/FilmBake` calls Fotufilm's runtime, pinned at
`3a789c436716c902654f248166ebb4f580611146`. It takes explicit floating-point
samples, rather than rendering a Hald image with neighborhood effects.

On a Mac with Swift 5.9+ and a compatible Halide developer distribution:

```sh
mkdir -p .cache
git clone https://github.com/DhaliwalX/fotufilm-engine .cache/fotufilm-engine
git -C .cache/fotufilm-engine checkout 3a789c436716c902654f248166ebb4f580611146
export HALIDE_ROOT=/absolute/path/to/extracted/Halide
swift build -c release --package-path tools/FilmBake
.venv/bin/python scripts/bake.py
.venv/bin/python scripts/fit_camera.py
.venv/bin/python scripts/examples.py
.venv/bin/python scripts/quality.py
.venv/bin/python scripts/guide.py
```

`FOTUFILM_SOURCE=/absolute/path/to/the/pinned/checkout` can select an existing
engine tree instead. The published local bake used Apple Swift 6.3.2 on
arm64 macOS 26.4.1 and the official Halide 21.0.0 arm64 macOS distribution.
The Halide package is a build dependency; it is not needed to install a look.
Its official distribution is available from
[Halide releases](https://github.com/halide/Halide/releases/tag/v21.0.0).

Preserve the exact upstream revision and compare the copied stock-profile
hashes with `research/film-sources.json`. No upstream source modification is
needed. CPU/compiler differences can change low floating-point bits; the
quality report uses numerical tolerances rather than promising cross-machine
byte-identical model rendering. PF3 reconstruction from the checked-in CUBEs
and parameter fields is byte-identical.

## Pipeline and data contracts

1. Sample the stock's gray response at 4097 extended internal exposure
   coordinates on `[0,2]`. Public input remains encoded sRGB on `[0,1]`.
2. Build the disclosed, monotonic inverse pre-shaper. Reject an unreachable
   display target instead of flattening highlights through inverse clamping.
3. Decode/convert the pre-shaped samples to linear Rec.2020 and run the
   pointwise film model with fixed 5500 K light, fixed Graded Print / grade 2,
   and local cross-layer couplers. Disable all neighborhood effects and
   per-image metering.
4. Convert the result to linear sRGB with soft luminance/chroma delivery,
   encode it, and apply the fixed neutral print timing described in
   [FILM_MODELS.md](FILM_MODELS.md).
5. Write a 65³ CUBE. Sample its even nodes into the full 33³ / 12-bit camera
   tables. Independently fit Canon's parametric editing fields for approximate
   desktop preview; those fields do not replace the complete dense look.
6. Verify interpolation against direct model evaluations, including shuffled
   pixel order and changed image geometry. This rejects accidental spatial or
   image-metering dependence.

`scripts/fit_camera.py` writes the public parameter field records used for
reconstruction. Its fitting error describes the desktop preview approximation,
not the error of the full dense camera LUT.

## Canon-specific validation

The saved native parser/compiler and RAW-render reports were produced locally
using a separately downloaded official PSE 1.33.10 runtime. No Canon binary,
installer, firmware, ICC file or opaque compiled camera payload is included.
Native checks require a compatible, independently obtained Canon runtime;
ordinary CI therefore verifies their exact input identities rather than
pretending to rerun those proprietary components.

The fully initialized compiler needs its native MLib color engine. A successful
parser initialization without MLib once yielded an unchanged carrier; positive
and negative controls exposed that incomplete setup. The final report verifies
the loaded engine and distinct look data for G7 X III model `0x808`.

## Release

Update the version consistently, run checks, then push an annotated `vX.Y.Z`
tag. The workflow checks Linux and macOS before publishing the installation
ZIP and SHA256SUMS. Download the public ZIP separately, verify its outer and
inner checksums, file count, link targets and forbidden vendor-file exclusions.
Physical camera installation is a separate acceptance gate.
