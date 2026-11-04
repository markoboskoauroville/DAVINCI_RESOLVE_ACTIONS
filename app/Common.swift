// What every part of DaVinci Resolve Actions shares: the colours and words of the CAMERA language, the state files,
// Resolve itself, Python, keys and hot keys.
import SwiftUI
import AppKit
import Carbon.HIToolbox

let VERSION = 20
let RELEASES = "https://github.com/markoboskoauroville/DAVINCI_RESOLVE_ACTIONS/releases/latest"
let BUNDLE = "com.blackmagic-design.DaVinciResolve"
let PYTHON = NSHomeDirectory() + "/.pyenv/versions/3.10.14/bin/python3"
// the scripts ship inside the app (Resources/scripts); in a development run they are read from the repository
let SCRIPTS: String = {
    let inApp = (Bundle.main.resourcePath ?? "") + "/scripts"
    return FileManager.default.fileExists(atPath: inApp) ? inApp : NSHomeDirectory() + "/Developer/DAVINCI_RESOLVE_ACTIONS/scripts"
}()
let UTILITY = NSHomeDirectory() + "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"

let GREEN = Color(red: 0x33/255, green: 0xD1/255, blue: 0x7A/255)
let GREY = Color(red: 0x7A/255, green: 0x80/255, blue: 0x87/255)
let AMBER = Color(red: 0xE8/255, green: 0xA3/255, blue: 0x3D/255)
let INK = Color(red: 0x0B/255, green: 0x0D/255, blue: 0x10/255)

struct Word: View {
    let text: String; let on: Bool; let action: () -> Void
    var body: some View {
        Text(text).font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(on ? GREEN : GREY)
            .padding(.horizontal, 6).padding(.vertical, 4).contentShape(Rectangle()).onTapGesture(perform: action)
    }
}
// v17 (Marko, 31.10.2026: "Each needs to have the same user interface elements. On, off and top"): TOP left of
// PERMISSIONS and the ✕; green = the window stays above every other window, kept in "onTop" and applied at launch
struct TopWord: View {
    @AppStorage("onTop") private var onTop = false
    var body: some View {
        Word(text: "TOP", on: onTop) { onTop.toggle(); TopWord.float(onTop) }
            .axButton("Top", id: "top", value: onTop ? "on" : "off") { onTop.toggle(); TopWord.float(onTop) }
            .help("Always on top: green, the window stays above every other window")
            .onAppear { DispatchQueue.main.async { TopWord.float(onTop) } }
    }
    static func float(_ on: Bool) {
        for w in NSApp.windows where w.title.hasPrefix("DaVinci Resolve Actions") { w.level = on ? .floating : .normal }
    }
}
// every control an Accessibility button (MANTRA_MANIFEST swift-apps.md, "Accessibility built in")
extension View {
    func axButton(_ label: String, id: String, value: String? = nil, _ action: @escaping () -> Void) -> some View {
        accessibilityElement(children: .ignore)
            .accessibilityLabel(label)
            .accessibilityIdentifier(id)
            .accessibilityValue(value ?? "")
            .accessibilityAddTraits(.isButton)
            .accessibilityAction(.default, action)
    }
}
struct Label10: View {
    let text: String
    var body: some View { Text(text).font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundColor(GREY) }
}
struct Small: View {
    let text: String
    var body: some View { Text(text).font(.system(size: 11, design: .monospaced)).foregroundColor(GREY).fixedSize(horizontal: false, vertical: true) }
}

// MARK: state files, read and changed as JSON dictionaries (the files the Lua apps wrote stay the same)

struct JSONFile {
    let url: URL
    init(_ name: String) { url = URL(fileURLWithPath: NSHomeDirectory() + "/.config/" + name) }
    func read() -> [String: Any] { (try? JSONSerialization.jsonObject(with: Data(contentsOf: url))) as? [String: Any] ?? [:] }
    func change(_ f: (inout [String: Any]) -> Void) {
        var s = read(); f(&s)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? JSONSerialization.data(withJSONObject: s, options: [.prettyPrinted, .sortedKeys]).write(to: url)
    }
}
let SETTINGS = JSONFile("resolve-actions.json")     // which modules are on, the actions' shortcuts

// MARK: Resolve and Python

func resolveApp() -> NSRunningApplication? { NSRunningApplication.runningApplications(withBundleIdentifier: BUNDLE).first }
func resolveFront() -> Bool { NSWorkspace.shared.frontmostApplication?.bundleIdentifier == BUNDLE }

// the router (resolve_router.py): the one connection to Resolve, for this app and every Claude session
var ROUTER_PORT = 8940
func router(_ method: String, _ path: String, body: [String: Any]? = nil, timeout: Double, then: @escaping (Int, [String: Any]) -> Void) {
    var req = URLRequest(url: URL(string: "http://127.0.0.1:\(ROUTER_PORT)" + path)!, timeoutInterval: timeout)
    req.httpMethod = method
    if let b = body { req.httpBody = try? JSONSerialization.data(withJSONObject: b); req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
    URLSession.shared.dataTask(with: req) { data, resp, _ in
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        let b = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] } ?? [:]
        DispatchQueue.main.async { then(code, b) }
    }.resume()
}

// a script run against Resolve, through the router when it runs (one call at a time, a timeout, "busy" instead of a
// hang), else with Resolve's Python straight; the answer is its last line
func runScript(_ name: String, _ args: [String] = [], timeout: Int = 30, direct: Bool = false, then: @escaping (Int32, String) -> Void) {
    DispatchQueue.global().async {
        // v11: a long action (Project Backup copies for hours) talks to Resolve itself, outside the router's time limit
        let viaRouter = !direct && (try? Data(contentsOf: URL(string: "http://127.0.0.1:\(ROUTER_PORT)/health")!)) != nil
        let p = Process(); p.executableURL = URL(fileURLWithPath: PYTHON)
        p.arguments = viaRouter ? [SCRIPTS + "/resolve-run", "--who", "actions", "--plain", "--timeout", String(timeout), SCRIPTS + "/" + name] + args
                                : [SCRIPTS + "/" + name] + args
        let pipe = Pipe(); p.standardOutput = pipe; p.standardError = pipe
        do { try p.run() } catch { DispatchQueue.main.async { then(-1, "\(error)") }; return }
        let out = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self); p.waitUntilExit()
        let last = out.split(separator: "\n").last.map(String.init) ?? ""
        DispatchQueue.main.async { then(p.terminationStatus, last) }
    }
}

// MARK: keys

let KEYS: [String: Int] = ["`": kVK_ANSI_Grave, "a": kVK_ANSI_A, "b": kVK_ANSI_B, "c": kVK_ANSI_C, "d": kVK_ANSI_D, "e": kVK_ANSI_E,
    "f": kVK_ANSI_F, "g": kVK_ANSI_G, "h": kVK_ANSI_H, "i": kVK_ANSI_I, "j": kVK_ANSI_J, "k": kVK_ANSI_K, "l": kVK_ANSI_L,
    "m": kVK_ANSI_M, "n": kVK_ANSI_N, "o": kVK_ANSI_O, "p": kVK_ANSI_P, "q": kVK_ANSI_Q, "r": kVK_ANSI_R, "s": kVK_ANSI_S,
    "t": kVK_ANSI_T, "u": kVK_ANSI_U, "v": kVK_ANSI_V, "w": kVK_ANSI_W, "x": kVK_ANSI_X, "y": kVK_ANSI_Y, "z": kVK_ANSI_Z,
    "0": kVK_ANSI_0, "1": kVK_ANSI_1, "2": kVK_ANSI_2, "3": kVK_ANSI_3, "4": kVK_ANSI_4, "5": kVK_ANSI_5, "6": kVK_ANSI_6,
    "7": kVK_ANSI_7, "8": kVK_ANSI_8, "9": kVK_ANSI_9, "tab": kVK_Tab, "space": kVK_Space, "return": kVK_Return,
    "f1": kVK_F1, "f2": kVK_F2, "f3": kVK_F3, "f4": kVK_F4, "f5": kVK_F5, "f6": kVK_F6, "f7": kVK_F7, "f8": kVK_F8,
    "f9": kVK_F9, "f10": kVK_F10, "f11": kVK_F11, "f12": kVK_F12, "f13": kVK_F13, "f14": kVK_F14, "f15": kVK_F15,
    "f16": kVK_F16, "f17": kVK_F17, "f18": kVK_F18, "f19": kVK_F19, "f20": kVK_F20]

// "ctrl+alt+cmd+U": Carbon modifiers, CGEvent flags and the key code
struct Chord {
    var carbon: UInt32 = 0; var flags: CGEventFlags = []; var key: UInt32 = 0
    init?(_ text: String) {
        var k: UInt32?
        for p in text.split(whereSeparator: { $0 == "+" || $0 == " " }).map({ $0.lowercased() }) {
            switch p {
            case "ctrl", "control": carbon |= UInt32(controlKey); flags.insert(.maskControl)
            case "alt", "option", "opt": carbon |= UInt32(optionKey); flags.insert(.maskAlternate)
            case "cmd", "command": carbon |= UInt32(cmdKey); flags.insert(.maskCommand)
            case "shift": carbon |= UInt32(shiftKey); flags.insert(.maskShift)
            default: if let c = KEYS[p] { k = UInt32(c) }
            }
        }
        guard let kk = k else { return nil }
        key = kk
    }
    var cocoa: NSEvent.ModifierFlags {
        var f: NSEvent.ModifierFlags = []
        if flags.contains(.maskControl) { f.insert(.control) }; if flags.contains(.maskAlternate) { f.insert(.option) }
        if flags.contains(.maskCommand) { f.insert(.command) }; if flags.contains(.maskShift) { f.insert(.shift) }
        return f
    }
    // the chord sent to Resolve itself
    func send(to app: NSRunningApplication) {
        for down in [true, false] {
            let e = CGEvent(keyboardEventSource: nil, virtualKey: CGKeyCode(key), keyDown: down); e?.flags = flags
            e?.postToPid(app.processIdentifier)
        }
    }
}

// MARK: hot keys: each key a closure, his only while Resolve is in front
// v5 (22.10.2026, Marko: "Alt tick doesn't work to change my pages. Sometimes works, sometimes doesn't"): the keys are
// caught by an event tap that asks, at the moment of the press, whether the key goes to Resolve. Before, Carbon hot keys
// were registered when Resolve became the active app and dropped when another did, and a switch the notification missed
// (the J K L lend through SkyLight, a full-screen space) left ⌥` dead in Resolve or caught in another app. Carbon stays
// only as the fallback while the tap is not allowed (Accessibility).

func log(_ text: String) {
    let f = NSHomeDirectory() + "/.config/resolve-assistant.log"
    let line = "\(DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)) actions: \(text)\n"
    if let h = FileHandle(forWritingAtPath: f) { h.seekToEndOfFile(); h.write(Data(line.utf8)); try? h.close() }
}

final class HotKeys {
    static let shared = HotKeys()
    private var refs: [UInt32: EventHotKeyRef] = [:]
    private var actions: [UInt32: () -> Void] = [:]
    private var next: UInt32 = 1
    private var wanted: [(Chord, () -> Void)] = []
    private var tap: CFMachPort?
    private var kept: Set<Int64> = []                // keys whose down was ours: their up is ours too
    init() {
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, ev, _ in
            var id = EventHotKeyID()
            GetEventParameter(ev, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &id)
            DispatchQueue.main.async { HotKeys.shared.actions[id.id]?() }
            return noErr
        }, 1, &spec, nil, nil)
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { _ in if HotKeys.shared.tap == nil { HotKeys.shared.startTap() } }
    }
    var viaTap: Bool { tap != nil }
    // the whole set, said again whenever a module or a shortcut changes
    func set(_ list: [(Chord, () -> Void)]) { wanted = list; startTap(); if resolveFront() { arm() } }
    func startTap() {
        guard tap == nil else { return }
        let mask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
        guard let t = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap,
                                        eventsOfInterest: CGEventMask(mask), callback: { _, type, ev, _ in HotKeys.shared.handle(type, ev) },
                                        userInfo: nil) else { return }
        CFRunLoopAddSource(CFRunLoopGetMain(), CFMachPortCreateRunLoopSource(nil, t, 0), .commonModes)
        CGEvent.tapEnable(tap: t, enable: true); tap = t; disarm(); log("shortcuts by event tap")
    }
    func match(_ ev: CGEvent) -> (() -> Void)? {
        let code = ev.getIntegerValueField(.keyboardEventKeycode)
        let mods = ev.flags.intersection([.maskCommand, .maskControl, .maskAlternate, .maskShift])
        return wanted.first { Int64($0.0.key) == code && $0.0.flags == mods }?.1
    }
    func toResolve(_ ev: CGEvent) -> Bool {
        if resolveFront() { return true }
        let pid = ev.getIntegerValueField(.eventTargetUnixProcessID)
        return pid != 0 && Int64(resolveApp()?.processIdentifier ?? -1) == pid
    }
    private func handle(_ type: CGEventType, _ ev: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput { if let t = tap { CGEvent.tapEnable(tap: t, enable: true) }; return Unmanaged.passUnretained(ev) }
        let code = ev.getIntegerValueField(.keyboardEventKeycode)
        if type == .keyUp { return kept.remove(code) != nil ? nil : Unmanaged.passUnretained(ev) }
        guard let f = match(ev), toResolve(ev) else { return Unmanaged.passUnretained(ev) }
        kept.insert(code)
        if ev.getIntegerValueField(.keyboardEventAutorepeat) == 0 { DispatchQueue.main.async(execute: f) }
        return nil
    }
    // Carbon, only while there is no tap
    func arm() {
        guard tap == nil else { return }
        disarm()
        for (c, f) in wanted {
            var ref: EventHotKeyRef?
            let id = next; next += 1
            if RegisterEventHotKey(c.key, c.carbon, EventHotKeyID(signature: 0x44525341, id: id), GetApplicationEventTarget(), 0, &ref) == noErr, let r = ref {
                refs[id] = r; actions[id] = f
            }
        }
    }
    func disarm() { refs.values.forEach { UnregisterEventHotKey($0) }; refs = [:]; actions = [:] }
}
