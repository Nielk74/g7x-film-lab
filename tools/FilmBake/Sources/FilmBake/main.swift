import Foundation
import FotufilmCore

// Preserve luminance and the direction of the linear RGB chroma vector while
// approaching the sRGB boundary smoothly. This happens BEFORE channel clipping.
func deliveryRGB(_ rgb: SIMD3<Float>, knee: Float) -> SIMD3<Float> {
    let luminance = max(0, rgb.x * 0.2126 + rgb.y * 0.7152 + rgb.z * 0.0722)
    guard luminance > 1e-12 else { return .zero }
    let light = ColorScience.displayShoulder(luminance, knee: knee)
    let chroma = rgb * (light / luminance) - SIMD3<Float>(repeating: light)
    var distance: Float = 0
    for channel in 0..<3 {
        let room = chroma[channel] >= 0 ? max(1 - light, 1e-8) : max(light, 1e-8)
        distance = max(distance, abs(chroma[channel]) / room)
    }
    let start: Float = 0.80, ceiling: Float = 0.985
    let mapped = distance <= start ? distance
        : start + (ceiling - start) * (1 - exp(-(distance - start) / (ceiling - start)))
    let factor = distance > 0 ? mapped / distance : 1
    return SIMD3<Float>(repeating: light) + chroma * factor
}

// Numerical sampling utility. No image decoder, image auto-meter, 8-bit
// quantization, dither, spatial effect, or camera transport is involved.
struct Request: Decodable {
    var stock: String
    var input: String
    var output: String
    var width: Int
    var height: Int
    var grade: Float?
    var exposureEV: Float?
    var digitalReference: String?
    var couplers: Float?
}

func run() throws {
    guard CommandLine.arguments.count == 2 else {
        throw NSError(domain: "FilmBake", code: 1, userInfo: [
            NSLocalizedDescriptionKey: "Usage: film-bake request.json (sRGB float32 interleaved input/output)"
        ])
    }
    let request = try JSONDecoder().decode(Request.self, from: Data(
        contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
    guard request.width > 0, request.height > 0,
          request.width <= 1_000_000, request.height <= 1_000_000,
          request.width <= 2_000_000 / request.height,
          var stock = FilmStock.named(request.stock) else {
        throw NSError(domain: "FilmBake", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid dimensions or stock"])
    }
    let count = request.width * request.height
    let data = try Data(contentsOf: URL(fileURLWithPath: request.input))
    guard data.count == count * 12 else {
        throw NSError(domain: "FilmBake", code: 3, userInfo: [NSLocalizedDescriptionKey: "Input byte length does not match dimensions"])
    }
    let samples: [Float] = data.withUnsafeBytes { bytes in
        (0..<(count * 3)).map { index in
            Float(bitPattern: UInt32(littleEndian: bytes.loadUnaligned(fromByteOffset: index * 4, as: UInt32.self)))
        }
    }
    // Values over one are an internal scene-exposure calibration domain, not
    // the public LUT input contract. The sRGB transfer is extended by its
    // standard power expression for this numerical pre-exposure shaper.
    guard samples.allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 4 }) else {
        throw NSError(domain: "FilmBake", code: 4, userInfo: [NSLocalizedDescriptionKey: "Internal encoded exposure samples must be finite and in 0...4"])
    }

    // A LUT represents one pixel's mapping. Suppress every neighborhood stage
    // while preserving the stock's local, cross-layer chemical interactions.
    stock.emulsionDiffusionMM = [Float](repeating: 0, count: stock.emulsionDiffusionMM.count)
    stock.emulsionDiffusionSecondaryMM = [Float](repeating: 0, count: stock.emulsionDiffusionSecondaryMM.count)
    stock.lumaDiffusionMM = 0
    stock.mtfLumaShare = 0
    stock.couplerDiffusionMM = 0
    stock.chromaticFringeAmount = 0
    stock.adjacencyStrength = 0
    stock.adjacencyRadiusMM = 0
    stock.layeredTransport = nil

    var options = FotufilmEngine.Options()
    options.paper = .screen
    options.digitalReference = DigitalReferenceStyle(rawValue: request.digitalReference ?? "graded-print") ?? .gradedPrint
    options.screenGrade = request.grade ?? 2
    options.exposureEV = request.exposureEV ?? 0
    options.screenExposureEV = 0
    options.sceneIlluminantKelvin = 5500
    options.grainScale = 0
    options.halationScale = 0
    options.flareScale = 0
    options.localTone = false
    options.couplerScale = request.couplers ?? 1
    options.chromaticFringeAmount = 0
    options.shadowDetail = 0
    options.highlightDetail = 0
    options.labScanDodging = 0
    options.labScanLook = 0
    options.format = .still35

    var image = ImageBuffer(width: request.width, height: request.height)
    for index in 0..<count {
        let srgb = SIMD3<Float>(samples[index * 3], samples[index * 3 + 1], samples[index * 3 + 2])
        let linear = SIMD3<Float>(ColorScience.srgbToLinear(srgb.x),
                                 ColorScience.srgbToLinear(srgb.y),
                                 ColorScience.srgbToLinear(srgb.z))
        let working = ColorScience.linearSRGBToRec2020(linear)
        for channel in 0..<3 { image.planes[channel][index] = working[channel] }
    }
    let engine = FotufilmEngine(stock: stock, options: options)
    let start = Date()
    let developed = try engine.processChecked(linearRGB: image)
    var result = [Float](repeating: 0, count: count * 3)
    let shoulder = options.sdrShoulderKnee(for: stock)
    for index in 0..<count {
        let p3 = SIMD3<Float>(developed.planes[0][index], developed.planes[1][index], developed.planes[2][index])
        let srgb = deliveryRGB(ColorScience.linearDisplayP3ToSRGB(p3), knee: shoulder)
        for channel in 0..<3 {
            let value = ColorScience.linearToSrgb(srgb[channel])
            guard value.isFinite else {
                throw NSError(domain: "FilmBake", code: 5, userInfo: [NSLocalizedDescriptionKey: "Non-finite model output"])
            }
            result[index * 3 + channel] = value
        }
    }
    let encoded: [UInt32] = result.map { $0.bitPattern.littleEndian }
    try encoded.withUnsafeBufferPointer { buffer in
        try Data(buffer: buffer).write(to: URL(fileURLWithPath: request.output), options: .atomic)
    }
    let receipt: [String: Any] = [
        "stock": request.stock, "pixels": count, "seconds": Date().timeIntervalSince(start),
        "input": "sRGB IEC61966-2-1 float32", "working": "linear Rec.2020",
        "output": "sRGB IEC61966-2-1 float32", "paper": "screen",
        "digital_reference": options.digitalReference.rawValue, "screen_grade": options.screenGrade,
        "exposure_ev": options.exposureEV, "scene_kelvin": 5500,
        "halide_available": FotufilmEngine.isHalideBackendAvailable,
        "local_tone": false, "spatial_effects": false, "auto_levels": false,
        "grain": false, "halation": false, "coupler_scale": options.couplerScale,
        "couplers": "local cross-layer preserved",
        "delivery": "linear-sRGB luminance-axis soft chroma compression before clipping",
        "gamut_knee": 0.80, "gamut_ceiling": 0.985
    ]
    let json = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(json)
    FileHandle.standardOutput.write(Data([10]))
}

do { try run() }
catch {
    FileHandle.standardError.write(Data(("film-bake: \(error.localizedDescription)\n").utf8))
    exit(1)
}
