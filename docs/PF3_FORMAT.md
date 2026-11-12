# PF3 format implementation

The codec in `src/g7xfilm/pf3.py` is independently authored for this project.
It implements the observed PF3 `0x3000` file-format facts and generates its own
neutral metadata, mathematical identity matrices, straight curves and sampled
film LUTs. No Canon executable, original Canon profile, third-party generated
profile, upstream source file, or fixed cipher-key array is bundled.

Format research was informed by the public [Style Studio investigation](https://github.com/LvClFER/Lut-to-Canon-Picture-Style)
and by local inspection of its six generated example profiles, at revision
`aee6af16e901b6008ea2493773d674856315679c`. That repository did not declare a
source license when inspected; its source and example files are not vendored
here. The implementation follows decoded structure and mathematical behavior,
not copied source text. This attribution is not a claim of endorsement.

## Scope

Only the observed envelope is supported: the first eight bytes are
`00 00 30 00 50 53 50 00`, followed by a big-endian 32-bit body length. The
body uses a symmetric periodic byte-mask transform. This differs from the
camera's encrypted and digitally signed firmware update format.

Each decoded body record has a big-endian 16-bit identifier, 16-bit type and
32-bit payload length. Observed types are byte strings (`2`), 16-bit numeric
words (`3`), 32-bit numeric words (`4`) and opaque bytes (`0xffff`). Numeric
payload words are stored big-endian on disk; the Python `Field.data` interface
uses little-endian words. Record `0xfffe` contains the additive checksum of
all preceding decoded body bytes. Record `0xffff` is the final terminator.
The parser checks the complete envelope, field boundaries, supported types,
duplicates, checksum order, checksum value and absence of trailing data.

The constructed profile has 26 data records and is 434,511 bytes. It uses
the Neutral base selector `0x84`. Records `0x1070` and `0x1071` each contain a
33 × 33 × 33 table with three 12-bit channels. The grid traversal is **R outer,
G middle, B inner**, with RGB outputs. This differs from the commonly used
`.cube` text traversal where R changes fastest. The caller passes a NumPy
array of shape `[33,33,33,3]` indexed as `[R,G,B,channel]`.

The two observed table records receive the same authored look. A complete
native Canon compiler test now establishes that these dense records affect
the model-`0x808` camera carrier; physical-camera rendering remains untested.
`build_profile` starts with identity auxiliary matrices and straight curves.
The film build adds separately fitted parametric metadata for desktop preview,
as explained below. Default controls are contrast 0, saturation 0, color tone
0, sharpness strength 0, fineness 2 and threshold 4. Titles are limited to 31
printable ASCII bytes.

## Camera table and desktop approximation are parallel representations

The release retains the full authored color/tone transform in the dense
`0x1070`/`0x1071` records: 33³ samples of the stock's 65³ sRGB CUBE, quantized
to 12 bits. The native Canon camera compiler reads this representation when
preparing a model-`0x808` carrier. Its lower-resolution packing, interpolation,
gamut policy and camera behavior are separate stages; a 12-bit source table
does not promise 12-bit JPEG output.

Canon's desktop DPP renderer follows a different representation. Controlled
rendering showed that replacing both dense tables with black did not change
its image, while changes to polynomial coefficients or curves did. Therefore
the film profiles also contain an approximation in the parametric records:

1. RGB input curves: `0x1018`.
2. Three rows of 19 cubic polynomial coefficients, signed Q16.16, with an
   unused twentieth word per row: `0x1021` / alternate `0x1029`.
3. RGB output curves: `0x1065`.
4. Luminance curve: `0x1019`, left as identity by this project's fitter.

The input/matrix/output order was corroborated by actual Canon rendering:
with a matrix routing blue input to red output, a red input-curve change had
no effect, while a red output-curve change affected red output. Polynomial
controls separately corroborated linear red, red squared and RGB-product
terms; the twentieth word had no effect in that tested mode.

`src/g7xfilm/parametric.py` fits this limited curve/polynomial/curve family to
the full LUT with deterministic holdout, neutral and skin-region error reports.
These are **desktop preview approximations**, not a claim that 57 polynomial
coefficients reproduce every value of an arbitrary 3D LUT. Color management
and native quantization can add further differences. The original stock
transform stays in the dense camera tables; the fitted preview is not
substituted for that transform. Metrics and previews must name which
representation they measure.

## Reproducible calibration from our authored identity profile

`calibrate_identity(reference_bytes)` derives a compatible byte-mask stream
from a caller-supplied PF3 containing a mathematically known identity table.
The method uses the two observed coprime periods, 512 and 513. XORing bytes at
positions `p`, `p+512`, `p+513` and `p+1025` cancels both periodic factors. A
known identity table can therefore be located without distributing key tables.
Known plaintext then supplies a bipartite XOR constraint graph, from which
the factors are solved up to an irrelevant common-XOR value.

Calibration succeeds only after the complete known table and decoded file
checksum validate. An arbitrary creative profile is not assumed to contain an
identity. The function does not search nearby files, download a calibration,
or save factors. The `Calibration` representation does not print factors.

Public source builds use `resources/neutral-calibration.pf3`, an original
identity profile constructed from this module's own mathematical scaffolding.
It is **not** a copy of the privately inspected third-party profile. Its title
is `G7X Lab Identity`; its controls are the defaults documented above. This
authored calibration data is MIT licensed, as is this codec.

The profile is 434,511 bytes; SHA-256 is
`76b0c3bc266931321e8e27e3e5b8cff07ccc4136971a3154b36c7e7ae3183ae4`.
The initial compatible stream was learned from a private inspection input,
then used to serialize entirely caller-authored metadata and mathematical
tables. Original reference bytes and derived factor arrays are not committed.
Public CI can learn the compatible stream from this project's own identity
profile and deterministically regenerate all five film styles without a
private fixture, a download, or an installed Canon runtime.

You may alternatively provide another compatible identity profile that you
are authorized to inspect as a local input. Keep any third-party references
and derived factor data outside the repository. Generated film files carry
this project's authored look data; the resource is a developer build input,
not a sixth film look offered for camera installation.

## API

```python
from pathlib import Path
from g7xfilm.pf3 import calibrate_identity, build_profile, parse_profile

calibration = calibrate_identity(Path("resources/neutral-calibration.pf3").read_bytes())
encoded = build_profile(lut_rgb, "Portra 400 study", calibration)
profile = parse_profile(encoded, calibration)
assert profile.title == "Portra 400 study"
```

`lut_rgb` must contain finite values in `[0,1]`. Profile generation quantizes
them to 12-bit codes, serializes all fields, then parses the result and checks
complete field equality before returning bytes. `encode_fields` exists for
explicit typed-record work; it does not bypass format bounds or integrity
checks.

## Validation boundary

Tests cover identity calibration from synthetic factors, full structural
roundtrip, 12-bit quantization, RGB orientation, control values, malformed
boundaries and corruption. The authored public identity is decoded,
re-encoded and regenerated byte-for-byte. An optional
`G7XFILM_PF3_REFERENCE` environment variable can substitute a private local
reference for that comparison; no third-party reference file is committed.

The authored identity profile was also read successfully by **Canon Picture
Style Editor 1.33.10's native macOS EdsCFParse library**. Initialization,
CreateRef, property size/data queries, release and termination returned zero.
Native readback confirmed base selector `0x84`, the authored title, the default
controls and both 215,628-byte tables. Each table's native readback SHA-256 is
`7a5c2f3fc6aefc9c5f8e636a104d4f15a4c9ddc815c6236630e5baba436b5121`.
The inspected Canon library SHA-256 is
`1d3860617a1d3508a1393cde7f1800a328a2311ef082aa83f5ec0e029df205e9`.
No Canon library is redistributed.

Self-consistent parsing and native-parser acceptance do **not** establish
registration or rendered appearance on the G7 X III. Each generated creative
profile requires its own native readback, and actual camera registration/JPEG
comparisons remain separate checks. This module never communicates with a
camera or writes firmware.

## Native camera-compiler positive control

The inspected PSE 1.33.10 installation includes a nested **EdsCFParse
3.19.0.0** next to **MLib 1.4.2.0** inside DppCore's plug-ins. Complete
initialization matters: the top-level parser can return zero from its ordinary
initializer even when its MLib function pointers remain null. A byte-identical
carrier in that incomplete state is not evidence that a profile feature is
ignored.

The corrected offline experiment explicitly confirmed that Canon's
`LoadMLibFunction` succeeded, opened each local PF3, set model ID `0x808`, and
read compiler property `0x01000203`. No camera API was called. The tested
interface matches the sequence observed in the shipped PowerShot registration
tool: select model, optionally supply the live descriptor, then request the
compiled user-style data.

| Input, with identical title and other metadata | Carrier length | Carrier SHA-256 |
| --- | ---: | --- |
| Authored identity PF3 | 16,752 | `3d99085ed12e63cf5de624445d55c1dc1d31b94f0dc651a93088f54b1ee5d809` |
| Same PF3 with only both dense tables replaced by black | 16,752 | `272d6b11f28f15045beaf3514803599d363ed09e6414d90d369bf224dd1a6c35` |

The output changed at 15,484 byte positions, beginning at offset 372. A
matrix-only control with unchanged dense identity tables retained the identity
carrier. This is direct causal evidence that the working native PF3 compiler
consumed the dense table data in this tested model route. It is not a measured
camera installation or a physical JPEG result, and the actual camera's optional
descriptor was not available.

Inspected native module identities:

- Nested EdsCFParse SHA-256:
  `b16b0cbf683989408e5509714de6d83c81bbdb4e054f17c9d5aa063d94a7d762`.
- MLib SHA-256:
  `ebfd7db08f8febacc8d3a9f62224c3aa95ca5f4a0f4b6f16c7211075db0740be`.

Digest and return-code evidence is retained with this project. Canon libraries
and opaque Canon-generated camera carriers remain private research artifacts
and are not part of the release.
