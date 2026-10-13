// The icon, drawn: a grid of one-button actions, like a control surface for Resolve: four round buttons, one lit
// amber, the page letters and HD/UHD on two of them; the version under it.
import AppKit
let S: CGFloat = 1024
let version = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "1"
let img = NSImage(size: NSSize(width: S, height: S)); img.lockFocus()
let ctx = NSGraphicsContext.current!.cgContext
ctx.addPath(CGPath(roundedRect: CGRect(x: 100, y: 100, width: 824, height: 824), cornerWidth: 180, cornerHeight: 180, transform: nil))
ctx.setFillColor(NSColor(calibratedRed: 0.04, green: 0.05, blue: 0.06, alpha: 1).cgColor); ctx.fillPath()
let amber = NSColor(calibratedRed: 0.91, green: 0.64, blue: 0.24, alpha: 1)
let labels = ["EDT", "UHD", "⌘I", "▶"]
for (i, l) in labels.enumerated() {
    let col = CGFloat(i % 2), row = CGFloat(1 - i / 2)
    let r = CGRect(x: 230 + col * 300, y: 330 + row * 280, width: 240, height: 240)
    ctx.setFillColor((i == 3 ? amber : NSColor(calibratedWhite: 0.24, alpha: 1)).cgColor); ctx.fillEllipse(in: r)
    ctx.setStrokeColor(NSColor(calibratedWhite: 0.45, alpha: 1).cgColor); ctx.setLineWidth(8); ctx.strokeEllipse(in: r.insetBy(dx: 4, dy: 4))
    let a: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: i == 3 ? 110 : 72, weight: .bold), .foregroundColor: i == 3 ? NSColor.black : NSColor(white: 0.92, alpha: 1)]
    let sz = (l as NSString).size(withAttributes: a)
    (l as NSString).draw(at: NSPoint(x: r.midX - sz.width / 2, y: r.midY - sz.height / 2), withAttributes: a)
}
("v" + version as NSString).draw(at: NSPoint(x: 170, y: 150), withAttributes: [.font: NSFont.systemFont(ofSize: 92, weight: .semibold), .foregroundColor: NSColor(calibratedWhite: 0.78, alpha: 1)])
img.unlockFocus()
try! NSBitmapImageRep(data: img.tiffRepresentation!)!.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "icon_1024.png"))
