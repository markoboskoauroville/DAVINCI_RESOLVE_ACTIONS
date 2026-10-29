// NUMBER KEYS (Marko, 29.10.2026: "my number key 1 is to switch to angle 1 in Multicam ... For some reason, they're
// going to timecode ... I need the numeric keyboard to be not triggering the timecode entry boxes."). His keyboard preset
// already gives keypad 1..9 to Switch to Angle 1..9; outside a multicam clip that command has nothing to do and Resolve
// hands the digit to its timecode entry. So: while Resolve is in front, the keypad's digits pass only when the clip under
// the playhead is a multicam clip (asked twice a second through the router); otherwise they are swallowed.
// Needs Accessibility, as the other taps.
import AppKit

final class KeypadModule: ObservableObject {
    static var shared: KeypadModule!
    @Published var tapOK = false
    @Published var multicam = false      // the clip under the playhead is a multicam clip
    @Published var said = ""
    var tap: CFMachPort?; var source: CFRunLoopSource?
    var poll: Timer?
    var swallowed = 0

    // kVK_ANSI_Keypad0 … Keypad9
    static let digits: Set<Int64> = [82, 83, 84, 85, 86, 87, 88, 89, 91, 92]

    init() { KeypadModule.shared = self }

    func setOn(_ v: Bool) {
        if v {
            startTap()
            poll = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                guard let self else { return }
                if self.tap == nil { self.startTap() }
                if resolveFront() { self.ask() }
            }
        } else { poll?.invalidate(); poll = nil; stopTap() }
    }

    func startTap() {
        guard tap == nil else { return }
        let mask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
        let cb: CGEventTapCallBack = { _, type, ev, _ in KeypadModule.shared.handle(type, ev) }
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
        let code = ev.getIntegerValueField(.keyboardEventKeycode)
        // only the keypad's digits, only bare (with ⌘ ⌃ ⌥ they stay Resolve's), only while Resolve is in front
        guard KeypadModule.digits.contains(code), resolveFront(),
              ev.flags.intersection([.maskCommand, .maskControl, .maskAlternate]).isEmpty else { return Unmanaged.passUnretained(ev) }
        if multicam { return Unmanaged.passUnretained(ev) }
        if type == .keyDown { swallowed += 1; DispatchQueue.main.async { self.said = "keypad digit held back: no multicam clip under the playhead (\(self.swallowed) so far)" } }
        return nil
    }

    /** Is the clip under the playhead a multicam clip? */
    func ask() {
        let code = """
        pm = resolve.GetProjectManager(); pr = pm.GetCurrentProject()
        tl = pr.GetCurrentTimeline() if pr else None
        it = tl.GetCurrentVideoItem() if tl else None
        mp = it.GetMediaPoolItem() if it else None
        result = bool(mp and 'multicam' in (mp.GetClipProperty('Type') or '').lower())
        """
        router("POST", "/run", body: ["who": "keypad", "code": code, "timeout": 3], timeout: 4) { [weak self] status, b in
            guard let self, status == 200, (b["ok"] as? Bool) == true else { return }
            let m = (b["result"] as? Bool) ?? false
            if m != self.multicam { self.multicam = m }
        }
    }
}
