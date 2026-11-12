# Example photograph credits

These source photographs support identical-input comparisons of all five looks. Four are processed digital photographs from other cameras. The fifth is a G7 X III RAW file developed by native Canon software. They are not film scans or measured film references, and no film look has been applied to these source files.

The source photographs are public-domain or CC0 materials. The four JPEGs have embedded sRGB profiles and were reduced to at most 1600 pixels on the longest edge. The NASA portrait was also cropped. The Canon PNG retains the native 1620 × 1080 render and has no embedded ICC profile. See [the source manifest](../../research/example-sources.json) for original/output hashes, dimensions, colour-space observations and changes.

## Victor Glover inside the Kibo laboratory, portrait crop

- File: `skin-portrait.jpg`.
- Credit: NASA.
- Source: [NASA image article](https://www.nasa.gov/image-article/astronaut-victor-glover-inside-kibo-laboratory-module/) and [NASA JSC image record iss064e044145](https://images.nasa.gov/details/iss064e044145).
- Reuse terms: [NASA public-domain content and media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/). NASA permits factual informational use with NASA credit. This photograph is an illustration, not project branding or an endorsement.
- Evidence: the NASA record identifies a 17 March 2021 image; the original EXIF identifies a Nikon D5 digital capture.
- Changes: orientation applied, converted from embedded sRGB to sRGB, cropped to source-pixel box (1900, 900, 3700, 2900), reduced to 1440 × 1600 and saved as JPEG quality 97, 4:4:4, with embedded sRGB ICC.

## Coffee at Pikolo Espresso Bar

- File: `warm-coffee.jpg`.
- Credit: Rachel Michetti; Pikolo Espresso Bar.
- Source: [scikit-image coffee sample](https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.coffee).
- Reuse terms: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Evidence: [scikit-image v0.25.2 source documentation](https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/data/_fetchers.py) explicitly states CC0 by photographer Rachel Michetti and credits Pikolo Espresso Bar.
- Changes: interpreted untagged source RGB as sRGB, retained 600 × 400 composition and saved as JPEG quality 97, 4:4:4, with embedded sRGB ICC.

## Landscape, nature, sky and clouds

- File: `landscape-sky.jpg`.
- Credit: Ed Gregory / www.Pixel.la Free Stock Photos.
- Source: [Commons file description](https://commons.wikimedia.org/wiki/File:Landscape-nature-sky-clouds_(23958729879).jpg) and [original Flickr photo](https://www.flickr.com/photos/137643065@N06/23958729879/).
- Reuse terms: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Evidence: the Commons file description states CC0 and records a Flickr licence review on 16 September 2016. The original EXIF credits Ed Gregory.
- Changes: orientation applied, converted from embedded sRGB to sRGB, reduced to 1600 × 1063 and saved as JPEG quality 97, 4:4:4, with embedded sRGB ICC. Composition retained.

## Singapore skyline at night with black sky

- File: `night-city.jpg`.
- Credit: Merlion444.
- Source: [Commons file description](https://commons.wikimedia.org/wiki/File:Singapore_Skyline_at_Night_with_Black_Sky.JPG).
- Reuse terms: public-domain dedication and [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Evidence: the author identifies the photograph as their own work and explicitly releases it worldwide into the public domain, additionally offering CC0.
- Changes: orientation applied, interpreted untagged source RGB as sRGB, reduced to 1600 × 899 and saved as JPEG quality 97, 4:4:4, with embedded sRGB ICC. Composition retained.

## G7 X III creek landscape, native Canon Neutral RAW render

- File: `g7x-iii-canon-neutral.png`.
- Credit: raw.pixls.us contributor; an individual photographer name was not supplied in the inspected record or public metadata.
- Source: [raw.pixls.us repository](https://raw.pixls.us/), record 6053, `IMG_0253.CR3`, Canon PowerShot G7 X Mark III normal RAW, uploaded 21 October 2022. [Original RAW download](https://raw.pixls.us/getfile.php/6053/nice/Canon%20-%20PowerShot%20G7%20X%20Mark%20III%20-%203%3A2.CR3); [public metadata](https://raw.pixls.us/getfile.php/6053/exif/IMG_0253.CR3.exif.txt).
- Reuse terms: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The specific record is marked CC0; the repository's submission form requires ownership and a CC0 release.
- Original RAW SHA-256: `63ce623055dd2ac7374e0b1c645a4eabc7e181cd12c2039625f64b4e63a5ee86`. The RAW itself is not redistributed here.
- Changes: native Canon DppCore render with Neutral picture style (0x84), As Shot white balance, 0 EV exposure compensation and sharpening 0. Rendered at 1620 × 1080; composition retained. The RGB PNG is declared sRGB by the render settings and has no embedded ICC profile.
- This is a Canon software RAW render. A LUT preview of it is not an out-of-camera JPEG or an on-camera PF3 demonstration.
