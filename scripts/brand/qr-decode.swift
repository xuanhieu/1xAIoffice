import Foundation
import CoreImage
// Decode every QR code in an image file and print its payload, one per line.
let args = CommandLine.arguments
guard args.count > 1, let img = CIImage(contentsOf: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("không đọc được ảnh\n".data(using: .utf8)!); exit(2)
}
let ctx = CIContext()
let det = CIDetector(ofType: CIDetectorTypeQRCode, context: ctx, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])!
let found = det.features(in: img).compactMap { ($0 as? CIQRCodeFeature)?.messageString }
if found.isEmpty { FileHandle.standardError.write("không thấy mã QR\n".data(using: .utf8)!); exit(1) }
for s in found { print(s) }
