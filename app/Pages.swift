// PAGES: Command-Tab for Resolve's pages (from Resolve Pages (Mantra) v1, itself from the star's pages.lua).
// ⌥` while Resolve is in front opens the row of pages, most recent first; each ` steps, ⇧ steps back, letting go opens
// the lit one, a quick tap jumps back. The hand inside Resolve is scripts/pages_helper.py (its scripting API, a line
// per command: "open edit", "pages", "quit" in; "page edit", "pages a,b", "waiting", "error …" out); without it
// Shift+2..8 goes to Resolve. State: ~/.config/pages.json, as before.
import AppKit
import Carbon.HIToolbox

let PAGES_FILE = JSONFile("pages.json")
let ORDER = ["media", "cut", "edit", "fusion", "color", "fairlight", "deliver", "photo"]
let PAGE_NAME = ["media": "Media", "cut": "Cut", "edit": "Edit", "fusion": "Fusion", "color": "Color", "fairlight": "Fairlight",
                 "deliver": "Deliver", "photo": "Photo", "none": "no page"]
let PAGE_CODE = ["media": "MED", "cut": "CUT", "edit": "EDT", "fusion": "FUS", "color": "COL", "fairlight": "FAI",
                 "deliver": "DEL", "photo": "PHO", "none": "---"]
let SHIFTKEY: [String: Int] = ["media": kVK_ANSI_2, "cut": kVK_ANSI_3, "edit": kVK_ANSI_4, "fusion": kVK_ANSI_5,
                               "color": kVK_ANSI_6, "fairlight": kVK_ANSI_7, "deliver": kVK_ANSI_8]
let PAGES_HOTKEY = "alt+`"
let PREFS = NSHomeDirectory() + "/Library/Preferences/Blackmagic Design/DaVinci Resolve"

final class HUD {
    let panel = NSPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
    init() {
        panel.level = .popUpMenu; panel.isOpaque = false; panel.backgroundColor = .clear; panel.ignoresMouseEvents = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
    }
    func show(_ list: [String], _ sel: Int) {
        let cellW: CGFloat = 150, cellH: CGFloat = 66, pad: CGFloat = 14
        let w = CGFloat(list.count) * cellW + pad * 2, h = cellH + pad * 2
        let v = NSView(frame: NSRect(x: 0, y: 0, width: w, height: h)); v.wantsLayer = true
        v.layer?.backgroundColor = NSColor(white: 0.08, alpha: 0.88).cgColor; v.layer?.cornerRadius = 18
        for (i, page) in list.enumerated() {
            let x = pad + CGFloat(i) * cellW, lit = i == sel
            if lit {
                let hl = NSView(frame: NSRect(x: x + 4, y: pad, width: cellW - 8, height: cellH)); hl.wantsLayer = true
                hl.layer?.backgroundColor = NSColor(white: 1, alpha: 0.22).cgColor; hl.layer?.cornerRadius = 12; v.addSubview(hl)
            }
            let n = NSTextField(labelWithString: PAGE_NAME[page] ?? page); n.font = .systemFont(ofSize: 21); n.alignment = .center
            n.textColor = NSColor(white: 1, alpha: lit ? 1 : 0.6); n.frame = NSRect(x: x, y: pad + 26, width: cellW, height: 28); v.addSubview(n)
            let c = NSTextField(labelWithString: PAGE_CODE[page] ?? ""); c.font = .systemFont(ofSize: 11); c.alignment = .center
            c.textColor = NSColor(white: 1, alpha: lit ? 0.9 : 0.4); c.frame = NSRect(x: x, y: pad + 8, width: cellW, height: 16); v.addSubview(c)
        }
        let scr = NSScreen.main?.visibleFrame ?? .zero
        panel.contentView = v
        panel.setFrame(NSRect(x: scr.midX - w / 2, y: scr.midY - h / 2, width: w, height: h), display: true)
        panel.orderFrontRegardless()
    }
    func hide() { panel.orderOut(nil) }
}

final class PagesModule: ObservableObject {
    @Published var current = "none" { didSet { onChange?() } }
    @Published var hotkey = (PAGES_FILE.read()["hotkey"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? PAGES_HOTKEY
    @Published var ring: [String] = PagesModule.loadRing()
    @Published var helperState = "not started"
    @Published var said = ""
    var onChange: (() -> Void)?
    var mru: [String] = (PAGES_FILE.read()["mru"] as? [String]) ?? []
    let hud = HUD()
    var row: [String]?; var lit = 0; var releaseWatch: Timer?
    var helper: Process?; var helperIn: FileHandle?; var buffer = ""
    var prefStamp: Date?
    var on = false

    init() {
        // a helper left from an app that was killed while it waited inside Resolve's API (it holds Python's lock there,
        // so neither its own checks nor SIGTERM can end it): its parent is launchd now (22.10.2026)
        let k = Process(); k.executableURL = URL(fileURLWithPath: "/usr/bin/pkill"); k.arguments = ["-9", "-P", "1", "-f", "scripts/pages_helper.py"]
        try? k.run(); k.waitUntilExit()
        Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in self?.checkPrefs() } }

    static func loadRing() -> [String] { let c = PAGES_FILE.read()["ring"] as? [String]; return ORDER.filter { c == nil || c!.contains($0) } }
    func saveRing(_ r: [String]) { ring = ORDER.filter { r.contains($0) }; PAGES_FILE.change { $0["ring"] = self.ring } }
    func remember() { PAGES_FILE.change { $0["mru"] = self.mru; $0["current"] = self.current } }
    func touch(_ p: String) { mru.removeAll { $0 == p }; mru.insert(p, at: 0); if mru.count > ORDER.count { mru.removeLast() }; remember() }

    func candidates() -> [String] {
        var list: [String] = []
        if current != "none" { list.append(current) }
        for p in mru where ring.contains(p) && !list.contains(p) { list.append(p) }
        for p in ring where !list.contains(p) { list.append(p) }
        return list
    }

    // the module switched on or off, Resolve arriving or leaving: the helper follows
    func setOn(_ v: Bool) { on = v; if v && resolveApp() != nil { startHelper() } else { stopHelper(); commit(); current = "none" } }
    func resolveCame() { if on { startHelper() } }
    func resolveLeft() { stopHelper(); commit(); current = "none"; helperState = "Resolve is not running" }

    func startHelper() {
        guard on, helper?.isRunning != true, resolveApp() != nil else { return }
        let p = Process(); p.executableURL = URL(fileURLWithPath: PYTHON); p.arguments = ["-u", SCRIPTS + "/pages_helper.py"]
        let inPipe = Pipe(), outPipe = Pipe(); p.standardInput = inPipe; p.standardOutput = outPipe; p.standardError = FileHandle.nullDevice
        outPipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let d = h.availableData; if d.isEmpty { return }
            DispatchQueue.main.async { self?.heardData(d) }
        }
        p.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.helper = nil; self.helperState = "stopped"
                if self.on && resolveApp() != nil { DispatchQueue.main.asyncAfter(deadline: .now() + 20) { self.startHelper() } }
            }
        }
        do { try p.run(); helper = p; helperIn = inPipe.fileHandleForWriting; helperState = "starting" } catch { helperState = "could not start: \(error)" }
    }
    func stopHelper() {
        send("quit"); let p = helper; helper = nil
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { if p?.isRunning == true { p?.terminate() } }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { if let p = p, p.isRunning { kill(p.processIdentifier, SIGKILL) } }
    }
    @discardableResult func send(_ line: String) -> Bool {
        guard helper?.isRunning == true, let h = helperIn else { return false }
        h.write(Data((line + "\n").utf8)); return true
    }
    func heardData(_ d: Data) {
        buffer += String(decoding: d, as: UTF8.self)
        while let r = buffer.firstIndex(of: "\n") {
            let line = String(buffer[..<r]); buffer = String(buffer[buffer.index(after: r)...]); heard(line)
        }
    }
    func heard(_ line: String) {
        let parts = line.split(separator: " ", maxSplits: 1).map(String.init)
        let cmd = parts.first ?? "", arg = parts.count > 1 ? parts[1] : ""
        switch cmd {
        case "page": helperState = "connected"; asked = nil; current = arg; if arg != "none" { touch(arg) } else { remember() }
        case "pages": PAGES_FILE.change { $0["bar"] = arg.split(separator: ",").map(String.init) }
        case "waiting": if let p = asked { asked = nil; press(p) }; helperState = "waiting for Resolve's API (a project loading, or External scripting not Local)"
        case "error": said = arg; log("helper: " + arg); if let p = asked { asked = nil; press(p) }
        default: break
        }
    }
    func checkPrefs() {
        guard helper?.isRunning == true, let e = FileManager.default.enumerator(atPath: PREFS) else { return }
        var newest: Date?
        for case let f as String in e where f.hasSuffix("UI.preset") {
            if let m = (try? FileManager.default.attributesOfItem(atPath: PREFS + "/" + f))?[.modificationDate] as? Date, newest == nil || m > newest! { newest = m }
        }
        if let n = newest, let p = prefStamp, n > p { send("pages") }
        prefStamp = newest ?? prefStamp
    }

    var asked: String?                       // the page sent to the helper, until it says where Resolve is
    func open(_ page: String) {
        guard page != current else { return }
        log("open \(page) (helper \(helperState))")
        if helperState == "connected" && send("open " + page) {
            // Resolve's API stalls while Resolve is busy (seen 22.10.2026: 100 % CPU, scriptapp() hung over 25 s): no
            // answer in 0.6 s and Resolve's own keys go instead
            asked = page
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { [weak self] in
                guard let self = self, self.asked == page else { return }
                self.asked = nil; log("no answer from Resolve's API for \(page)"); self.press(page)
            }
        } else { press(page) }
        current = page; touch(page)
    }
    // Resolve's own keys for its pages, ⇧2..⇧8, when the API cannot (Resolve is in front: the shortcut fired there)
    func press(_ page: String) {
        guard let k = SHIFTKEY[page], let app = resolveApp() else { said = "no way to reach \(PAGE_NAME[page] ?? page) without external scripting"; return }
        if !resolveFront() { app.activate() }
        for down in [true, false] { let e = CGEvent(keyboardEventSource: nil, virtualKey: CGKeyCode(k), keyDown: down); e?.flags = .maskShift; e?.postToPid(app.processIdentifier) }
        log("pressed ⇧ for \(page)")
    }
    func previous() { let c = candidates(); if c.count > 1 { open(c[1]) } else { said = "only one page in the ring" } }

    var heldMods: NSEvent.ModifierFlags { (Chord(hotkey)?.cocoa ?? .option).subtracting(.shift) }
    // read from the keyboard's state itself, not from this app's last event
    func held() -> Bool {
        let h = heldMods, f = CGEventSource.flagsState(.combinedSessionState)
        var now: NSEvent.ModifierFlags = []
        if f.contains(.maskControl) { now.insert(.control) }; if f.contains(.maskAlternate) { now.insert(.option) }; if f.contains(.maskCommand) { now.insert(.command) }
        return !h.isEmpty && now.isSuperset(of: h)
    }
    func step(_ dir: Int) {
        if row == nil {
            let c = candidates()
            guard c.count > 1 else { said = "only \(PAGE_NAME[current] ?? "one page") is in the ring"; return }
            row = c; lit = 0; log("\(hotkey): \(c.joined(separator: " ")), Resolve on \(current)")
            releaseWatch = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in if self?.held() == false { self?.commit() } }
        }
        lit = ((lit + dir) % row!.count + row!.count) % row!.count
        hud.show(row!, lit)
        if !held() { commit() }
    }
    func commit() {
        releaseWatch?.invalidate(); releaseWatch = nil; hud.hide()
        if let r = row { row = nil; open(r[lit]) }
    }
    // its keys: the shortcut forwards, with ⇧ backwards
    func hotkeys() -> [(Chord, () -> Void)] {
        guard on, var c = Chord(hotkey) else { return [] }
        var list: [(Chord, () -> Void)] = [(c, { [weak self] in self?.step(1) })]
        if c.carbon & UInt32(shiftKey) == 0 { c.carbon |= UInt32(shiftKey); c.flags.insert(.maskShift); list.append((c, { [weak self] in self?.step(-1) })) }
        return list
    }
    func setHotkey(_ t: String) -> Bool {
        let v = t.trimmingCharacters(in: .whitespaces)
        guard v.isEmpty || Chord(v) != nil else { said = "\"\(v)\" is not a key I know"; return false }
        hotkey = v.isEmpty ? PAGES_HOTKEY : v; PAGES_FILE.change { $0["hotkey"] = v.isEmpty ? nil : v }
        said = "\(hotkey) walks the pages"; return true
    }
}
