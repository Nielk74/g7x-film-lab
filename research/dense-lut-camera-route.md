# Dense PF3 table route: native compiler investigation

This investigation resolves an important distinction between accepting a PF3,
previewing it in Canon's desktop RAW renderer, compiling its camera carrier,
and observing an actual camera-produced JPEG. These are separate checks.
No camera was connected or written during the experiments below.

## Shipped registration interface

The inspected Windows PowerShot Picture Style File Registration Tool 1.1.0.4
contains a managed `GetUserStyleDataFromFile` method. Its recovered CIL opens
the PF3, sets native property `0x01000001` from the selected camera's model ID,
optionally sets `0x01000210` from a live LUT descriptor, then retrieves
`0x01000203` as user-style data. It does not secretly call `ReflectProperty`
between those operations. This is source-bound shipped-artifact evidence, not
an assumption based on EOS Utility instructions.

The companion installation evidence records the exact module digests and
managed-method evidence. The original executables and native carrier bytes
are private research inputs; no Canon code is included in this repository.

## A failed negative control and its correction

The first offline compiler probe loaded the top-level PSE EdsCFParse bundle.
It returned zero from ordinary initialization, file creation, model selection
and carrier retrieval. Identity and black-dense-table profiles produced the
same carrier. However, polynomial and curve positive controls also produced
that same carrier. This made the probe inconclusive.

Read-only native disassembly and loaded-memory inspection explained why.
EdsCFParse's MLib wrappers can return without doing color mathematics when
their function pointers are null. The loader finds `com.canon.MLib` among
bundles beside the selected `com.canon.edscfparse` bundle. The top-level
parser did not have an adjacent MLib in the staged installation; its ordinary
initialization return code did not expose that missing color engine.

The corrected probe loaded the **nested EdsCFParse 3.19.0.0** beside **MLib
1.4.2.0** inside DppCore's plug-ins. It explicitly checked
`LoadMLibFunction() == 1` before compiling. Only these fully initialized
results support camera-compiler conclusions.

## Positive dense-table control

Both source profiles used the same authored title, Neutral base, controls,
straight auxiliary curves and identity polynomial matrices. Only dense records
`0x1070` and `0x1071` were changed from identity to black. For model ID `0x808`
(G7 X III), compiler output property `0x01000203` returned 16,752 bytes in
both cases, with all ordinary API return codes zero.

| Input | Native carrier SHA-256 |
| --- | --- |
| Authored identity profile | `3d99085ed12e63cf5de624445d55c1dc1d31b94f0dc651a93088f54b1ee5d809` |
| Same metadata, both dense tables black | `272d6b11f28f15045beaf3514803599d363ed09e6414d90d369bf224dd1a6c35` |

The carriers differed in 15,484 byte positions, starting at file offset 372.
A matrix-only half-scale control, with dense identity tables unchanged,
retained the identity carrier. Thus the dense source tables causally affect
the working native camera compiler; this is stronger evidence than merely
reading the tables through the file parser.

Static corroboration, in the inspected native image: the PF3 profile maker's
`MakeLackyTable` virtual dispatch selects `MakeLackyTableFrom3DLut`. That
function reads the two dense records through `GetLutFileParam` and calls
MLib's `MLIBcalcLuckyFromFileLUT` before camera packing. Function names and
addresses describe this specific binary, not a guarantee for every Canon
version.

Native module identities:

- EdsCFParse 3.19.0.0:
  `b16b0cbf683989408e5509714de6d83c81bbdb4e054f17c9d5aa063d94a7d762`.
- MLib 1.4.2.0:
  `ebfd7db08f8febacc8d3a9f62224c3aa95ca5f4a0f4b6f16c7211075db0740be`.

The active top-level file-parser identity recorded elsewhere is a different
binary and should not be substituted for these complete-compiler inputs.

## Desktop renderer is a separate route

Canon DppCore's additional Picture Style path reads parametric records rather
than relying on the arbitrary dense cache. Actual local RAW rendering showed
that an all-black dense cache did not change the image, while zeroing the
active polynomial did. Independent red, red-squared, RGB-product and curve
ordering probes established the useful approximation domain:

`1018 RGB input curves -> 1021 polynomial -> 1065 RGB output curves -> 1019 luminance`.

The current fitter leaves the last luminance stage unchanged and stores the
same polynomial in alternate record `1029`. It uses independently authored
math, the observed 19-monomial ordering, signed Q16.16 coefficients and bounded
quadratic curve interpolation. It does not copy an unlicensed implementation.

This leads to two explicitly named parallel representations in each film
profile: the full authored 33³ dense table for camera compilation, and a
limited curve/polynomial/curve approximation for Canon desktop previews.
Their numerical and visual differences must be documented. Native-parser
success, desktop rendering success and exact reconstruction of this fitted
approximation do not prove that an actual G7 X III JPEG matches the full CUBE.

## Remaining boundary

The positive control establishes dense-table consumption by the inspected
Canon compiler with model ID `0x808`; the owner's live descriptor was not
available. Final release profiles require their own compiler digest receipts,
then registration and controlled JPEG comparisons on an actual camera.
No physical camera installation, firmware modification, grain synthesis,
halation or exact match to a measured roll/scan is established here.

The low-level observations used ordinary local `nm`, `otool`, CoreFoundation
and ctypes probes under the REA investigation workflow. They are not invented
REA Evidence IDs or traces from a camera. The public format research in
[Style Studio](https://github.com/LvClFER/Lut-to-Canon-Picture-Style) informed
which facts to test; no source file, fixed key arrays, native Canon library or
third-party generated profile is redistributed.
