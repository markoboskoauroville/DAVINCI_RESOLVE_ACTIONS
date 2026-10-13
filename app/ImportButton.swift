// IMPORT BUTTON: the mouse's thumb button, pressed while Resolve is in front, becomes Command-I (Import Media), and
// Resolve never sees the button (from Import Button (Mantra) v1, itself from the star's importbutton.lua). An event tap
// on the other mouse buttons, made only while the module is on; it needs Accessibility, asked once for this app.
// State: ~/.config/importbutton.json (button as a person counts, 4 = the thumb; keys).
import AppKit

let IMPORT_FILE = JSONFile("importbutton.json")

final class ImportModule: ObservableObject {
    static var shared: ImportModule!
    @Published var button = max(3, IMPORT_FILE.read()["button"] as? Int ?? 4)
    @Published var keys = (IMPORT_FILE.read()["keys"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? "cmd+I"
    @Published var learning = false
    @Published var tapOK = false
    @Published var said = ""
    var tap: CFMachPort?; var source: CFRunLoopSource?
    var on = false
    var retry: Timer?

    init() { ImportModule.shared = self }

    func setOn(_ v: Bool) {
        on = v
        if v { startTap(); retry = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in if self?.tap == nil { self?.startTap() } } }
        else { retry?.invalidate(); stopTap() }
    }
    func startTap() {
        guard tap == nil else { return }
        let mask = (1 << CGEventType.otherMouseDown.rawValue) | (1 << CGEventType.otherMouseUp.rawValue)
        let cb: CGEventTapCallBack = { _, type, ev, _ in ImportModule.shared.handle(type, ev) }
        guard let t = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap,
                                        eventsOfInterest: CGEventMask(mask), callback: cb, userInfo: nil) else { tapOK = false; return }
        let s = CFMachPortCreateRunLoopSource(nil, t, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), s, .commonModes); CGEvent.tapEnable(tap: t, enable: true)
        tap = t; source = s; tapOK = true
    }
    func stopTap() {
        if let t = tap { CGEvent.tapEnable(tap: t, enable: false) }
        if let s = source { CFRunLoopRemoveSource(CFRunLoopGetMain(), s, .commonModes) }
        tap = nil; source = nil
    }
    func handle(_ type: CGEventType, _ ev: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput { if let t = tap { CGEvent.tapEnable(tap: t, enable: true) }; return Unmanaged.passUnretained(ev) }
        let n = Int(ev.getIntegerValueField(.mouseEventButtonNumber)) + 1
        if learning {
            if type == .otherMouseDown { DispatchQueue.main.async { self.button = n; IMPORT_FILE.change { $0["button"] = n }; self.learning = false; self.said = "mouse button \(n) is Import Media in Resolve" } }
            return nil
        }
        guard n == button, resolveFront() else { return Unmanaged.passUnretained(ev) }
        if type == .otherMouseDown { DispatchQueue.main.async { self.press() } }
        return nil
    }
    func press() { if let app = resolveApp() { Chord(keys)?.send(to: app) } }
    func learn() {
        guard tapOK else { said = "allow Accessibility first"; return }
        learning = true; said = "press the mouse button you want, within five seconds"
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) { if self.learning { self.learning = false; self.said = "no button heard; still button \(self.button)" } }
    }
    func setKeys(_ k: String) {
        let t = k.trimmingCharacters(in: .whitespaces)
        guard Chord(t) != nil else { said = "\"\(t)\" is not a key I know (e.g. cmd+I)"; return }
        keys = t; IMPORT_FILE.change { $0["keys"] = t }; said = "the button presses \(t) in Resolve"
    }
}
