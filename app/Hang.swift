// HANG DETECTOR, the screen half (v21, 6.11.2026). Marko: "When it hangs, it needs to give me the voice, and also show
// a message on screen that this DaVinci stopped responding." The detecting, the voice and the restart are in
// scripts/hang_watch.py and hang_restart.py (inside the router); this file only reads ~/.config/resolve-hang.json every
// 2 sec and shows it: a panel on the screen with the mouse, above every window, and ⚠ in the menu-bar word.
import SwiftUI
import AppKit

let HANG_FILE = NSHomeDirectory() + "/.config/resolve-hang.json"
let RED = Color(red: 0xE5/255, green: 0x48/255, blue: 0x4D/255)

final class HangModule: ObservableObject {
    @Published var state = "ok"          // ok | hung | restarting | restarted
    @Published var why = ""
    @Published var step = ""
    @Published var restarting = false    // the app must not quit with Resolve while this is true
    var onChange: (() -> Void)?
    private var panel: NSPanel?
    private var shownFor: Double = 0     // the "since" of the hang already shown (CLOSE keeps it closed)
    private var closedFor: Double = -1

    init() {
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.read() }
    }

    func read() {
        guard let d = try? Data(contentsOf: URL(fileURLWithPath: HANG_FILE)),
              let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
        let s = j["state"] as? String ?? "ok"
        let since = j["since"] as? Double ?? 0
        let w = j["why"] as? String ?? ""
        let st = j["step"] as? String ?? ""
        let changed = s != state || w != why || st != step
        state = s; why = w; step = st
        restarting = s == "restarting"
        if s == "ok" || (s == "restarted" && Date().timeIntervalSince1970 - (j["updated"] as? Double ?? 0) > 20) {
            hide()
        } else if since != closedFor {
            show(since)
        }
        if changed { onChange?() }
    }

    func show(_ since: Double) {
        if panel == nil {
            let p = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 520, height: 210),
                            styleMask: [.titled, .nonactivatingPanel, .utilityWindow, .resizable],
                            backing: .buffered, defer: false)
            p.title = "DaVinci Resolve Actions: hang detector"
            p.level = .floating
            p.isFloatingPanel = true
            p.hidesOnDeactivate = false
            p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
            p.contentView = NSHostingView(rootView: HangView(h: self))
            panel = p
        }
        if shownFor != since {
            shownFor = since
            // on the screen where the mouse is, in the middle
            let m = NSEvent.mouseLocation
            let scr = NSScreen.screens.first { NSMouseInRect(m, $0.frame, false) } ?? NSScreen.main
            if let f = scr?.visibleFrame, let p = panel {
                p.setFrameOrigin(NSPoint(x: f.midX - p.frame.width / 2, y: f.midY - p.frame.height / 2))
            }
        }
        panel?.orderFrontRegardless()
    }

    func hide() { panel?.orderOut(nil) }
    func close() { closedFor = shownFor; hide() }

    /// RESTART DAVINCI: the same restart the detector does by itself for a hung render
    func restartNow() {
        let p = Process(); p.executableURL = URL(fileURLWithPath: PYTHON); p.arguments = [SCRIPTS + "/hang_restart.py"]
        try? p.run()
    }
}

struct HangView: View {
    @ObservedObject var h: HangModule
    var title: String {
        switch h.state {
        case "restarting": return "Restarting DaVinci Resolve"
        case "restarted": return "DaVinci Resolve is back"
        default: return "This DaVinci stopped responding"
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title).font(.system(size: 20, weight: .bold)).foregroundColor(h.state == "hung" ? RED : (h.state == "restarted" ? GREEN : AMBER))
                .fixedSize(horizontal: false, vertical: true)
            if !h.why.isEmpty { Text(h.why).font(.system(size: 13)).foregroundColor(.white).fixedSize(horizontal: false, vertical: true) }
            if !h.step.isEmpty { Text(h.step).font(.system(size: 13, design: .monospaced)).foregroundColor(GREY).fixedSize(horizontal: false, vertical: true) }
            Spacer(minLength: 0)
            HStack(spacing: 14) {
                if h.state == "hung" {
                    Word(text: "RESTART DAVINCI", on: true) { h.restartNow() }
                        .axButton("Restart DaVinci", id: "restart-davinci") { h.restartNow() }
                        .help("Quit DaVinci Resolve, open it again with the project, queue the unfinished renders again (captions burned in)")
                }
                Spacer()
                Word(text: "✕", on: false) { h.close() }.axButton("Close", id: "close-hang") { h.close() }
            }
        }
        .padding(18).frame(minWidth: 420, maxWidth: .infinity, minHeight: 170, maxHeight: .infinity, alignment: .topLeading)
        .background(INK)
    }
}
