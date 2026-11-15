// Dựng các trang đầu của một PDF thành PNG để duyệt bộ hướng dẫn (PDFKit sẵn trong macOS, không cần poppler).
// Dùng: swift scripts/guides/pdf-pages.swift <tệp.pdf> <tiền tố ra> <số trang>
import PDFKit
import AppKit
let args = CommandLine.arguments
guard args.count == 4, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])), let n = Int(args[3]) else {
    print("Dùng: swift pdf-pages.swift <tệp.pdf> <tiền tố ra> <số trang>"); exit(1)
}
print("trang:", doc.pageCount)
for i in 0..<min(doc.pageCount, n) {
    let img = doc.page(at: i)!.thumbnail(of: NSSize(width: 700, height: 990), for: .mediaBox)
    let rep = NSBitmapImageRep(data: img.tiffRepresentation!)!
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(args[2])-\(i + 1).png"))
}
