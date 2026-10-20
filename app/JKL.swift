// J K L: Resolve's transport from anywhere. Marko, 20.10.2026: "block JKL keys anywhere in the system, and it will use
// JKL keys to control the playhead in the Davinci Resolve remotely, being Davinci Resolve in focus or not."
// While the module is on and Resolve runs, J, K and L (alone or with ⇧) never reach the app in front; they go to Resolve.
// Resolve takes keys only while it is the active app (tried 20.10.2026: keys posted to its process in the background, and
// its window made key without activating it, both ignored; its scripting API has no play or stop), so the focus is lent:
// Resolve becomes the active app without raising a window (SkyLight, the way yabai and AutoRaise focus without raise),
// the keys play there natively (holding K with J or L, tapping L twice, all as in Resolve), and FOCUS_BACK seconds after
// the last of them the app he was in gets the focus back. Any other key in between gives it back at once and goes there.
// With ⌘, ⌃ or ⌥ the keys are left alone; with Resolve already in front they are Resolve's own. State: resolve-actions.json.
import AppKit

let JKL_CODES: [Int64: String] = [38: "J", 40: "K", 37: "L"]
let FOCUS_BACK = 1.5

// SkyLight and HIServices, found at run time: if they are missing the lend falls back to a plain activate()
private let SKY = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_NOW)
private let HIS = dlopen("/System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIServices.framework/HIServices", RTLD_NOW)
private typealias FrontFn = @convention(c) (UnsafeMutablePointer<ProcessSerialNumber>, UInt32, UInt32) -> Int32
private typealias RecordFn = @convention(c) (UnsafeMutablePointer<ProcessSerialNumber>, UnsafeMutablePointer<UInt8>) -> Int32
private typealias PsnFn = @convention(c) (pid_t, UnsafeMutablePointer<ProcessSerialNumber>) -> OSStatus
private let setFront = dlsym(SKY, "_SLPSSetFrontProcessWithOptions").map { unsafeBitCast($0, to: FrontFn.self) }
private let postRecord = dlsym(SKY, "SLPSPostEventRecordTo").map { unsafeBitCast($0, to: RecordFn.self) }
private let psnFor = dlsym(HIS, "GetProcessForPID").map { unsafeBitCast($0, to: PsnFn.self) }

// the app's front window on screen (layer 0), the one that gets the key
func frontWindow(_ pid: pid_t) -> UInt32? {
    let infos = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    return infos.first { ($0[kCGWindowOwnerPID as String] as? pid_t) == pid && ($0[kCGWindowLayer as String] as? Int) == 0 }?[kCGWindowNumber as String] as? UInt32
}

// the app becomes the active one and its window the key window, nothing is raised
func focusWithoutRaise(_ app: NSRunningApplication) {
    let pid = app.processIdentifier
    guard let setFront = setFront, let postRecord = postRecord, let psnFor = psnFor, var wid = frontWindow(pid) else { app.activate(); return }
    var psn = ProcessSerialNumber()
    guard psnFor(pid, &psn) == noErr else { app.activate(); return }
    _ = setFront(&psn, wid, 0x400)                       // kCPSNoWindows: front process, windows stay where they are
    var b = [UInt8](repeating: 0, count: 0xf8)
    b[0x04] = 0xf8; b[0x3a] = 0x10
    withUnsafeBytes(of: &wid) { for i in 0..<4 { b[0x3c + i] = $0[i] } }
    for i in 0x20..<0x30 { b[i] = 0xff }
    b[0x08] = 0x01; _ = postRecord(&psn, &b)
    b[0x08] = 0x02; _ = postRecord(&psn, &b)
}

final class JKLModule: ObservableObject {
    static var shared: JKLModule!
    @Published var tapOK = false
    @Published var said = ""
    var tap: CFMachPort?; var source: CFRunLoopSource?
    var on = false
    var retry: Timer?
    var lentFrom: NSRunningApplication?      // the app he was in while Resolve holds the focus for J K L
    var ready = false                        // Resolve is active: the keys go to it the normal way
    var queue: [CGEvent] = []                // keys pressed before Resolve was ready
    var down: Set<Int64> = []
    var back: DispatchWorkItem?

    init() {
        JKLModule.shared = self
        // a click into another app, or ⌘Tab, ends the lend: nothing to give back
        NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { [weak self] n in
            guard let self = self, self.lentFrom != nil, let a = n.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else { return }
            if a.bundleIdentifier != BUNDLE && a.processIdentifier != self.lentFrom?.processIdentifier { self.endLend(giveBack: false) }
        }
    }

    func setOn(_ v: Bool) {
        on = v
        if v { startTap(); retry = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in if self?.tap == nil { self?.startTap() } } }
        else { retry?.invalidate(); stopTap(); endLend(giveBack: true) }
    }
    func startTap() {
        guard tap == nil else { return }
        let mask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
        let cb: CGEventTapCallBack = { _, type, ev, _ in JKLModule.shared.handle(type, ev) }
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

    // runs on the main run loop for every key on the Mac: quick, and only J K L are ever kept
    func handle(_ type: CGEventType, _ ev: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput { if let t = tap { CGEvent.tapEnable(tap: t, enable: true) }; return Unmanaged.passUnretained(ev) }
        let code = ev.getIntegerValueField(.keyboardEventKeycode)
        let isJKL = JKL_CODES[code] != nil && ev.flags.intersection([.maskCommand, .maskControl, .maskAlternate]).isEmpty
        if lentFrom != nil {
            if isJKL {
                if type == .keyDown { down.insert(code) } else { down.remove(code) }
                schedule()
                if ready { return Unmanaged.passUnretained(ev) }              // Resolve is active: its own keys
                if let c = ev.copy() { queue.append(c) }; return nil
            }
            // another key: his app gets the focus back and the key with it
            if type == .keyDown, let to = lentFrom, let c = ev.copy() {
                endLend(giveBack: true)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) { c.postToPid(to.processIdentifier) }
                return nil
            }
            return Unmanaged.passUnretained(ev)
        }
        guard isJKL, on, let resolve = resolveApp(), !resolveFront() else { return Unmanaged.passUnretained(ev) }
        guard type == .keyDown, let c = ev.copy() else { return nil }       // a lone key up from before: dropped
        lend(to: resolve); down.insert(code); queue.append(c); schedule()
        return nil
    }

    func lend(to resolve: NSRunningApplication) {
        lentFrom = NSWorkspace.shared.frontmostApplication; ready = false
        focusWithoutRaise(resolve)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.06) { [weak self] in
            guard let self = self, self.lentFrom != nil else { return }
            self.ready = true
            for e in self.queue { e.postToPid(resolve.processIdentifier) }
            self.said = "Resolve: " + self.queue.filter { $0.type == .keyDown }.compactMap { JKL_CODES[$0.getIntegerValueField(.keyboardEventKeycode)] }.joined(separator: " ")
            self.queue = []
        }
    }
    // FOCUS_BACK seconds after the last J K L, with none held, his app gets the focus back
    func schedule() {
        back?.cancel()
        let w = DispatchWorkItem { [weak self] in
            guard let self = self else { return }
            if self.down.isEmpty { self.endLend(giveBack: true) } else { self.schedule() }
        }
        back = w; DispatchQueue.main.asyncAfter(deadline: .now() + FOCUS_BACK, execute: w)
    }
    func endLend(giveBack: Bool) {
        back?.cancel(); back = nil
        let from = lentFrom; lentFrom = nil; ready = false; queue = []; down = []
        if giveBack, let a = from, !a.isTerminated, a.bundleIdentifier != BUNDLE { focusWithoutRaise(a) }
    }
}
