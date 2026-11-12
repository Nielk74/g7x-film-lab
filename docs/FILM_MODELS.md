# Film models and the meaning of the five looks

The five requested materials are Kodak Portra 400, Kodak Gold 200, Kodak Ektar 100, Fujifilm Pro 400H, and Kodak Tri-X 400. Their color and tone should come from separate stock-response models. Portra is not a warm preset, and Tri-X is not an arithmetic RGB average.

These are **film-inspired color/tone transforms based on published material data**. They are not a measured match to this owner's G7 X III, a particular laboratory scanner, or every roll bearing the film name. A LUT cannot reproduce grain, halation, emulsion diffusion, adjacency, or image-dependent lab timing.

## Selected numerical reference

[Fotufilm](https://github.com/DhaliwalX/fotufilm-engine/tree/3a789c436716c902654f248166ebb4f580611146), revision `3a789c436716c902654f248166ebb4f580611146`, includes all five exact stock profiles. Its runtime models a film response and a separate positive conversion or print medium. Its spectral grid has 81 samples from 380 through 780 nm at 5 nm intervals. This is a reference model containing digitised data and assumptions; neither the grid nor the stock name establishes physical accuracy on its own.

The stock provenance below comes from the pinned repository's [SOURCE_ASSETS.json](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/SOURCE_ASSETS.json). The sampled records preserve the upstream digitisation; the fitted parameters, extrapolated tails, separated dye estimates, and inferred spatial construction have different evidence strength.

| Look | Runtime stock | Recorded characteristic-curve source | Samples per R/G/B record |
| --- | --- | --- | --- |
| Portra 400 | `portra400` | Kodak E-4050 | 490 / 490 / 490 |
| Gold 200 | `gold200` | Kodak E-7022, 2016 | 490 / 490 / 490 |
| Ektar 100 | `ektar100` | Kodak E-4046 | 483 / 490 / 483 |
| Pro 400H | `pro400h` | Fujifilm AF3-176E | 483 / 483 / 483 |
| Tri-X 400 | `trix400` | Kodak F-4017 | 963 / 963 / 963; the monochrome record is repeated |

Portra's upstream profile extends its highlight response beyond the main datasheet trace before approaching a maximum density. Other stocks also extrapolate outside the digitised exposure range. Those tails must not be described as fresh measurements made by this project.

For Tri-X, the profile specifies D-76 at 20°C, large-tank agitation at one-minute intervals. Kodak's [F-4017](https://business.kodakmoments.com/sites/default/files/files/resources/triXf4017.pdf) contains several developers, times, formats, and contrast indices; these are different renditions of the material. In this PDF, the D-76 400TX characteristic graphs are on printed page 12. The profile's `sourcePage` value is 8, so use the publication and conditions to identify the graph rather than silently treating that metadata value as the PDF page. The spectral-sensitivity note on printed page 10 says those data were obtained from the older Tri-X Pan 5063 and considered applicable to the newer film.

## What the physical model expresses

A simplified description of the non-spatial chain is:

1. Reconstruct a plausible spectrum from scene-linear RGB under a declared scene illuminant.
2. Integrate that light against each film record's wavelength sensitivity. Exposure changes are multiplicative in light and additive in log exposure.
3. Map log exposure through the stock's characteristic curves, including the chosen model of inter-image inhibition.
4. Form a negative transmittance spectrum from minimum/base density and the developed dye or silver density. In optical-density notation, transmittance is `10 ** (-density)`.
5. Convert that negative through a declared positive receiver or print medium, then view and encode it in the delivery color space.

There is no unique spectrum behind an RGB triplet. Two real surfaces with the same digital RGB can expose film differently. The reconstruction chooses a plausible member of that family; it does not recover the original spectrum. The selected [SpectralModel.swift](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/Sources/FotufilmCore/SpectralModel.swift) and [sampled-curve implementation](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/Sources/FotufilmCore/SampledCharacteristicCurve.swift) are the implementation references.

Published color-negative datasheets constrain the minimum and neutral combined dye spectrum more directly than the separate individual dyes. A fitted separation is not a measurement of every coating. Pro 400H's [manufacturer document](https://asset.fujifilm.com/www/us/files/2020-04/12ed29db8d4d8bb45563ecdd668b0894/films_pro-400h_datasheet_01.pdf) describes a fourth color-sensitive layer. The inspected runtime profile carries three effective dye-forming records; do not present it as a fully measured reconstruction of that four-layer chemistry.

## Conditions that make a LUT meaningful

The input and output transfer functions are part of a LUT's definition. A display-sRGB LUT must decode sRGB correctly, convert the primaries into the reference engine's scene-linear Rec.2020 working space, and encode the returned linear Display P3 result into sRGB after the declared gamut/highlight handling. Applying that LUT to log, Adobe RGB, PQ, HLG, or linear RGB without the corresponding conversion changes the look.

A G7 X III JPEG or Canon base-style rendition is already processed. Decoding its sRGB transfer curve does not undo Canon's tone mapping, clipping, noise reduction, or sensor color transform. The camera profile therefore needs an explicitly stated base-style/input assumption and a later camera calibration pass. Lost highlights cannot be recreated.

### Adapting the model to an already rendered photograph

The physical reference and the delivered display look have different input assumptions. Feeding an already rendered JPEG directly into the reference as scene light applies another film/positive tone response on top of the camera's rendition. In the initial Portra portrait proof, this produced excessive orange-red skin, harder facial shadows and loss of dark fabric detail. Those are observations of this prototype, not measured characteristics of Portra film.

The display adaptation reduces this repeated tone mapping using the model's own neutral ramp. Let `F` be the fixed stock/positive model, `g` its neutral brightness response, and `t` a monotonic target ramp. Construct `t` from a weighted combination of the input ramp and the normalised stock ramp, within an explicitly chosen black/white display range. An inverse pre-shaper `p = inverse(g)(t)` then feeds the stock model. The [bake manifest](../research/bake-manifest.json) and [stored shapers](../research/shapers/) record the weight, endpoint choices, model gray samples and inverse-sampling domain. These are this project's rendering choices, not values measured from the manufacturer's film.

This changes the tone supplied to the stock model while retaining its colour-dependent response. It does not recover the original scene or undo Canon processing. A common nonlinear pre-shaper applied to RGB channels can also change channel ratios and therefore hue or saturation away from neutral. Consequently, the absence of a separate warming or hue filter is not a claim of hue preservation. Skin, foliage, deep blues and coloured lights need independent visual checks after adaptation.

The inverse must cover every target value. The internal model can be sampled at virtual exposures above the public input maximum, using an extension of the sRGB transfer function as an internal exposure coordinate. Such internal samples are not additional allowed values in an input JPEG or the CUBE domain: the public contract remains encoded SDR sRGB in `[0, 1]`. The target white must remain within the actually sampled model response. Silently clamping an unreachable inverse makes several different highlight inputs identical; that is a plateau, not a gradual shoulder. Verify a positive neutral slope through the upper ramp and inspect the white endpoint after interpolation.

Neither a lifted black nor a compressed display white is an intrinsic property of a film stock. They belong to the selected positive/display rendition. Similarly, a natural-looking display adaptation does not reproduce the exposure latitude of a negative: details clipped by the original digital capture remain lost.

The final settings are:

| Look | Input-ramp share | Stock-ramp share | Encoded black | Encoded white |
| --- | --- | --- | --- | --- |
| Portra 400 | 0.72 | 0.28 | 0.035 | 0.960 |
| Gold 200 | 0.65 | 0.35 | 0.025 | 0.960 |
| Ektar 100 | 0.52 | 0.48 | 0.020 | 0.965 |
| Pro 400H | 0.78 | 0.22 | 0.040 | 0.960 |
| Tri-X 400 | 0.40 | 0.60 | 0.015 | 0.960 |

These shares combine **neutral tone ramps**. They do not blend the original colour photograph back into the final look. All five neutral model ramps are sampled at 4097 internal exposure coordinates over `[0, 2]`; all public CUBEs cover `[0, 1]` with 65 samples per channel.

### Positive timing and display gamut

The final conversion also balances the model's neutral colours and gently contains colours that exceed sRGB. These fixed operations are defined by the model, with no photograph metering or automatic white balance.

First, the native sampling utility converts the model's linear Display P3 output into linear sRGB. It applies the stock's display shoulder to luminance, then reduces colour distance towards the neutral axis as a colour approaches the available sRGB boundary. Compression begins at 80% of that available distance and approaches 98.5% of it. These percentages describe distance to the gamut boundary, not an 80% brightness threshold or a 98.5% output-white setting. This stage preserves the direction of colour away from neutral in linear RGB, together with the mapped luminance; it does not promise constant perceptual hue. It occurs before any channel clipping, so strongly coloured coffee, foliage or lights can retain colour gradation instead of flattening at zero or one channel.

Second, after sRGB encoding, a fixed positive-timing correction subtracts the model's neutral colour bias at the corresponding mean RGB brightness. The bias has zero channel mean, so this correction retains the chosen mean neutral tone while balancing unwanted colour crossover. The lookup comes entirely from the stored gray ramp. It is an authored print/scanner balancing decision, not a new measurement of film chemistry. A second, smaller containment step starts at 90% of the available encoded-RGB colour distance and approaches 99.5%, keeping any colours moved by that correction inside the delivery range.

Together, the pre-shaper, positive timing and gamut handling define the released display rendition. They intentionally affect colour as well as tone; the source stock model still supplies the colour-dependent differences among the five looks. The [independent review](../research/independent-lut-review.json) records the exact reviewed CUBE hashes, neutral slopes, residual casts, clipping diagnostics and visual limits.

For a bake, use fixed settings. The reference offers fixed **Reference Exposure** and **Graded Print** screen conversions. A screen Graded Print at grade 2 is a defined idealised positive conversion; a physical Endura Premier reflection print viewed under D50 is another defined choice. They are different looks. Record the chosen medium and every setting in the release manifest.

Never bake the engine's default Auto Levels, Lab Scan metering, automatic stock selection, or a local-tone operator into a universal table. Their answers depend on the rest of the image. Disable grain, halation, lens flare, local tone and all spatial stages. Preserve pointwise inter-image response if supported independently of diffusion. The [`Options` defaults](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/Sources/FotufilmCore/Pipeline.swift) include `localTone = true`; that default requires deliberate attention.

Rendering a Hald chart through a blur is not a valid LUT bake: neighbouring chart pixels represent unrelated colors. The reference's [physical paper route](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/Sources/FotufilmCore/PrintPaper.swift) includes enlarger blur, whereas its screen route has zero enlarger blur. A bake should be invariant to rearranging the same input colors. That permutation test catches hidden spatial or image-metering behavior.

## Validation and remaining calibration

Numerical checks should compare the delivered table against its declared, adapted floating-point model on held-out colors, not merely read the same grid back. Check neutral ramps, skin-color patches, saturated colors, toe and shoulder continuity, clipping, finite values and interpolation. Check inverse range coverage explicitly, and report the resulting black/white endpoints. A flat upper ramp is unacceptable even if its samples are nondecreasing. Grid-domain clipping percentages describe a sampling diagnostic; they are not the fraction of a real photograph that clips.

Tri-X should remain achromatic throughout the domain. Its spectral conversion must precede the monochrome tone response; averaging the three display RGB channels is not the selected stock model. Blending a colour original into the final monochrome output would reintroduce colour, so any retention of input tone must operate on the neutral target or a defined monochrome brightness signal.

Natural-image previews test whether plausible colors remain plausible; attractive previews are not physical validation. The supplied gallery includes one portrait case, daylight landscapes, a warm coffee scene and city lights. That range helps reveal repeated tone mapping and saturated-colour failures, but it does not establish accuracy across skin tones, lighting spectra, exposures or Canon white-balance settings.

### Finishing priorities for the five looks

These are qualitative checks against the model and manufacturer descriptions, not additional measured colour corrections:

| Look | What to preserve when finishing | Failure to avoid |
| --- | --- | --- |
| Portra 400 | Plausible skin across brightness levels, neutral fabric, visible shadow gradation and controlled colour intensity. Kodak identifies portrait skin and colour saturation as strengths. | Orange-red skin or crushed clothing caused by repeated tone mapping; forcing every scene into a faded pastel palette. |
| Gold 200 | Lively daylight colours and useful separation of warm reds, wood and skin. Kodak's sheet describes a daylight/flash material with substantial colour saturation. | A blanket yellow cast presented as a physical stock measurement, or merging warm colours into one orange. |
| Ektar 100 | Greater colour intensity where the model produces it, while retaining distinctions in red objects, foliage and blue skies. Kodak positions it for vivid nature, travel and product work. | Extra saturation that simply clips the most colourful objects, or sharpening effects attributed to a pointwise LUT. |
| Pro 400H | Neutral grays, continuous skin gradation and controlled shadow colour. Fujifilm specifically describes these properties. | A mandatory green cast, washed-out highlights or milky shadows used as a substitute for the stock response. |
| Tri-X 400 | The declared D-76 response, panchromatic colour-to-brightness relationships and distinct dark and bright tones under the chosen positive conversion. | Treating every Tri-X image as pushed, heavily crushed or grainy; grain and adjacency are absent from these LUTs. |

Kodak's [Portra product description](https://www.kodakprofessional.com/photographers/film/color/kodak-professional-portra-400-film/516) and [2017 colour-negative film brochure](https://business.kodakmoments.com/sites/default/files/files/products/KODAK_PROFESSIONAL_Color_Negative_Film_Brochure_English_2017.pdf) provide qualitative context and credited photographic examples. They show different photographic and finishing choices, not a universal pixel target. The brochure images were viewed as references and are not redistributed in this repository. Gold, Ektar, Pro 400H and Tri-X constraints above come from their manufacturer sheets linked below. No colour offset, contrast amount or pastel treatment was fitted to a brochure scan.

The CUBE result and a camera Picture Style require separate acceptance. A file parsing correctly, reproducing its own packed table or passing a quantisation check does not show that Canon software or the camera consumes that table. A camera rendition must be checked through the native Canon path, then on the camera, before claiming installation or output equivalence. A parametric camera approximation may differ from the full three-dimensional CUBE; its measured approximation error and native validation status belong in the release evidence.

The inspected reference repository includes ColorChecker-like digital test charts and numerical engine tests. This investigation did **not** find a paired physical-film/digital ColorChecker dataset or a numerical measured-film matching report for the five stock profiles. Do not claim a real-film ΔE score, calibrated G7 X III match, or scanner parity on that basis.

A useful physical comparison would capture the same chart and skin/foliage scene with the G7 X III and the target film, under recorded lighting and exposure. Document processing and scanner settings, use a fixed WB on the Canon, and retain the RAW and JPEG. Include exposure brackets. Compare within one managed color space and distinguish a stock response from lab grading. Camera installation/acceptance and aesthetic accuracy are separate tests.

## Sources and distribution

Fotufilm's [engine code licence](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/LICENSE) is Apache-2.0. Its [47 runtime film profiles](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/licenses/FILM-PROFILES.txt), including these five, are separately CC BY-SA 4.0. The [licensing document](https://github.com/DhaliwalX/fotufilm-engine/blob/3a789c436716c902654f248166ebb4f580611146/LICENSING.md) explicitly covers the profile rendering parameters and spectral samples. Retain the Fotufilm attribution, MUAStudio Inc. copyright, source and licence notices, and identify modifications. Derived LUT/profile assets should carry that data attribution and ShareAlike notice; the application source has its own licence. Rendering a user's photograph does not make that photograph a profile adaptation.

The alternative [spektrafilm reference](https://github.com/andreavolpato/spektrafilm/tree/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc) has GPLv3 software and separately CC BY-SA 4.0 profiles/direct LUT derivatives. It remains useful prior art. Its authoritative profile licence is `SPEKTRAFILM_LICENSE.txt`; an old custom-licence sentence remains in the inspected README. This pack should not combine datasets without recording which model supplied each asset.

Primary manufacturer references:

- [Kodak Portra 400, E-4050, February 2016](https://business.kodakmoments.com/sites/default/files/files/products/e4050_portra_400.pdf).
- [Kodak Gold 200, E-7022, February 2016](https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf).
- [Kodak Ektar 100, E-4046, February 2016](https://business.kodakmoments.com/sites/default/files/files/products/e4046_ektar_100.pdf).
- [Fujifilm Pro 400H, AF3-176E](https://asset.fujifilm.com/www/us/files/2020-04/12ed29db8d4d8bb45563ecdd668b0894/films_pro-400h_datasheet_01.pdf).
- [Kodak Tri-X 320/400, F-4017, May 2007](https://business.kodakmoments.com/sites/default/files/files/resources/triXf4017.pdf).

Profile hashes, precise source revision and bounded research findings are recorded in [research/film-sources.json](../research/film-sources.json). No manufacturer PDF is bundled as profile data.
