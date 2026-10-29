// Compare uploaded image presentation using the existing macOS ImageIO runtime.
import Foundation
import ImageIO
import CoreGraphics
import Darwin

let state = URL(fileURLWithPath: CommandLine.arguments[1])
let ledger = try JSONSerialization.jsonObject(with: Data(contentsOf: state.appendingPathComponent("ledger.json"))) as! [String: Any]
let assets = ledger["assets"] as! [String: [String: Any]]
func pixels(_ file: URL) throws -> (Int, Int, [UInt8]) {
    guard let source = CGImageSourceCreateWithURL(file as CFURL, nil),
          let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true, kCGImageSourceThumbnailMaxPixelSize: 512] as CFDictionary)
    else { throw NSError(domain: "invalid-image", code: 1) }
    let width = image.width, height = image.height
    var data = [UInt8](repeating: 0, count: width * height * 4)
    data.withUnsafeMutableBytes { buffer in
        let context = CGContext(data: buffer.baseAddress, width: width, height: height, bitsPerComponent: 8,
                                bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    return (width, height, data)
}
var results: [String: Any] = [:]
for (id, entry) in assets where entry["image_reencoded"] as? Bool == true {
    let a = try pixels(state.appendingPathComponent("assets/" + id))
    let b = try pixels(state.appendingPathComponent("rendered-assets/" + id))
    guard a.0 == b.0 && a.1 == b.1 else { throw NSError(domain: "image-dimensions-changed:" + id, code: 1) }
    var error = 0.0
    for i in a.2.indices where i % 4 != 3 { let delta = Double(a.2[i]) - Double(b.2[i]); error += delta * delta }
    let mse = error / Double(a.0 * a.1 * 3)
    let psnr = mse == 0 ? 100 : 10 * log10(255 * 255 / mse)
    guard psnr > 28 else { throw NSError(domain: "image-appearance-changed:" + id, code: 1) }
    results[id] = ["thumbnail_width": a.0, "thumbnail_height": a.1, "psnr_db": psnr, "verified": true]
}
umask(0o077)
try JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys]).write(to: state.appendingPathComponent("image-verification.json"), options: .atomic)
print("Verified image appearance:", results.count)
