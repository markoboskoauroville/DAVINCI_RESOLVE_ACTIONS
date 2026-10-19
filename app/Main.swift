// DaVinci Resolve Actions (Mantra): one app for everything that automates DaVinci Resolve. Marko, 13.10.2026: "all the
// scripts related to Davinci Resolve need to go under one common software called Davinci Resolve Actions. In the
// future, we are going to store there many other actions ... So no multiple now things for Resolve. Everything comes
// under one umbrella application." Inside: PAGES, HD / UHD, IMPORT BUTTON (each on or off), and the ONE-BUTTON ACTIONS
// (scripts/actions.json). One word in the menu bar while Resolve runs, "EDT · HD", whose menu reaches all of it.
// v3 (19.10.2026, Marko: "In the top of every user interface, there will now be an on/off switch ... If I say on, I
// close it's on" and "please unify the position of the close button on every application. It's far upper right
// corner"): the first row is DAVINCI RESOLVE ACTIONS  ON  OFF with the ✕ at its far right. OFF quits (the pages helper
// stops, the shortcuts and the import button's tap go with the app); ✕ (or the red button) closes the window only, every
// module keeps working. The star only opens it now.
import SwiftUI
import AppKit

final class Umbrella: NSObject, ObservableObject, NSMenuDelegate {
    let pages = PagesModule()
    let display = DisplayModule()
    let importer = ImportModule()
    let actions = ActionsModule()
    @Published var on: [String: Bool] = [:]
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

    override init() {
        super.init()
        let saved = SETTINGS.read()["modules"] as? [String: Bool] ?? [:]
        // first run: the modules that were on in the star's Lua apps stay on
        on = ["pages": saved["pages"] ?? true, "display": saved["display"] ?? true, "import": saved["import"] ?? true]
        let menu = NSMenu(); menu.delegate = self; item.menu = menu
        item.button?.toolTip = "DaVinci Resolve Actions: the page and the resolution; click for everything"
        pages.onChange = { [weak self] in self?.paint() }
        display.onChange = { [weak self] in self?.paint() }
        pages.setOn(on["pages"]!); display.on = on["display"]!; importer.setOn(on["import"]!)
        let nc = NSWorkspace.shared.notificationCenter
        nc.addObserver(forName: NSWorkspace.didLaunchApplicationNotification, object: nil, queue: .main) { [weak self] n in
            guard (n.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication)?.bundleIdentifier == BUNDLE else { return }
            self?.paint()
            DispatchQueue.main.asyncAfter(deadline: .now() + 10) { self?.pages.resolveCame(); self?.display.read(); self?.paint() }   // the project needs a moment
        }
        nc.addObserver(forName: NSWorkspace.didTerminateApplicationNotification, object: nil, queue: .main) { [weak self] n in
            guard (n.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication)?.bundleIdentifier == BUNDLE else { return }
            self?.pages.resolveLeft(); self?.paint()
        }
        // every shortcut is his only while Resolve is in front
        nc.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { _ in
            if resolveFront() { HotKeys.shared.arm() } else { HotKeys.shared.disarm() }
        }
        rebindKeys()
        if resolveApp() != nil { display.read() }
        paint()
    }

    func setModule(_ k: String, _ v: Bool) {
        on[k] = v; SETTINGS.change { $0["modules"] = self.on }
        switch k { case "pages": pages.setOn(v); case "display": display.on = v; if v { display.read() }; default: importer.setOn(v) }
        rebindKeys(); paint()
    }
    func rebindKeys() { HotKeys.shared.set(pages.hotkeys() + display.hotkeys() + actions.keys()) }

    func paint() {
        let up = resolveApp() != nil
        item.isVisible = up
        var parts: [String] = []
        if on["pages"]! { parts.append(PAGE_CODE[pages.current] ?? "---") }
        if on["display"]! { parts.append(display.mode) }
        item.button?.title = parts.isEmpty ? "DR" : parts.joined(separator: " · ")
        objectWillChange.send()
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        func add(_ t: String, _ sel: Selector?, _ obj: Any? = nil, state: Bool = false) {
            let i = NSMenuItem(title: t, action: sel, keyEquivalent: ""); i.target = self; i.representedObject = obj
            i.state = state ? .on : .off; if sel == nil { i.isEnabled = false }; menu.addItem(i)
        }
        if on["pages"]! {
            add("PAGES", nil)
            for p in pages.ring { add("  " + (PAGE_NAME[p] ?? p), #selector(pickPage(_:)), p, state: p == pages.current) }
            add("  Previous page  (\(pages.hotkey))", #selector(prevPage))
            menu.addItem(.separator())
        }
        if on["display"]! {
            add("Switch to \(display.mode == "UHD" ? "HD" : "UHD")  (now \(display.mode))", #selector(switchHD))
            menu.addItem(.separator())
        }
        add("ACTIONS", nil)
        for a in actions.list { add("  " + a.name + (actions.hotkeys[a.id].map { "  (\($0))" } ?? ""), #selector(runAction(_:)), a.id) }
        menu.addItem(.separator())
        add("Settings…", #selector(showSettings))
    }
    @objc func pickPage(_ i: NSMenuItem) { if let p = i.representedObject as? String { pages.open(p) } }
    @objc func prevPage() { pages.previous() }
    @objc func switchHD() { display.toggle() }
    @objc func runAction(_ i: NSMenuItem) { if let id = i.representedObject as? String, let a = actions.list.first(where: { $0.id == id }) { actions.run(a) } }
    @objc func showSettings() {
        NSApp.activate(ignoringOtherApps: true)
        if let w = NSApp.windows.first(where: { $0.title.contains("DaVinci Resolve Actions") }) { w.makeKeyAndOrderFront(nil) }
        else { NSWorkspace.shared.open(Bundle.main.bundleURL) }    // v3: closed with ✕, the reopen makes it again
    }
}

// MARK: the window

struct ModuleHead: View {
    let title: String; let on: Bool; let set: (Bool) -> Void; var value: String = ""
    var body: some View {
        HStack {
            Text(title).font(.system(size: 12, weight: .bold, design: .monospaced)).foregroundColor(.white)
            Word(text: "ON", on: on) { set(true) }
            Word(text: "OFF", on: !on) { set(false) }
            Spacer()
            Text(value).font(.system(size: 15, weight: .bold, design: .monospaced)).foregroundColor(AMBER)
        }
    }
}

struct KeyField: View {
    let placeholder: String; @State var text: String; let set: (String) -> Bool
    var body: some View {
        HStack {
            TextField(placeholder, text: $text).textFieldStyle(.roundedBorder).frame(width: 150).onSubmit { _ = set(text) }
            Word(text: "SET", on: false) { _ = set(text) }
        }
    }
}

struct SettingsView: View {
    @ObservedObject var u: Umbrella
    @ObservedObject var pages: PagesModule
    @ObservedObject var display: DisplayModule
    @ObservedObject var importer: ImportModule
    @ObservedObject var actions: ActionsModule
    var body: some View {
        VStack(spacing: 0) {
        // v3 (19.10.2026): ON / OFF first, above the scrolling modules; the ✕ at the far right closes the window only
        HStack(spacing: 4) {
            Text("DAVINCI RESOLVE ACTIONS").font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(.white).padding(.trailing, 6)
            Word(text: "ON", on: true) {}.help("DaVinci Resolve Actions runs")
            Word(text: "OFF", on: false) { NSApp.terminate(nil) }.help("Stop every module and quit")
            Spacer()
            Button(action: { (NSApp.keyWindow ?? NSApp.windows.first { $0.title.contains("DaVinci Resolve Actions") })?.performClose(nil) }) {
                Image(systemName: "xmark").font(.system(size: 15, weight: .medium)).foregroundColor(GREY)
                    .frame(width: 30, height: 30).contentShape(Rectangle())
            }.buttonStyle(.plain).help("Close the window (DaVinci Resolve Actions stays ON)")
        }.padding(.leading, 24).padding(.trailing, 12).padding(.top, 10).padding(.bottom, 4)
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    Label10(text: "DAVINCI RESOLVE")
                    Spacer()
                    Text(resolveApp() == nil ? "NOT RUNNING" : "RUNNING").font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(resolveApp() == nil ? GREY : GREEN)
                }
                // PAGES
                VStack(alignment: .leading, spacing: 8) {
                    ModuleHead(title: "PAGES", on: u.on["pages"]!, set: { u.setModule("pages", $0) }, value: (PAGE_NAME[pages.current] ?? pages.current).uppercased())
                    if u.on["pages"]! {
                        HStack(spacing: 0) {
                            Label10(text: "THE RING ")
                            ForEach(ORDER, id: \.self) { pg in
                                Word(text: PAGE_CODE[pg]!, on: pages.ring.contains(pg)) {
                                    var r = pages.ring; if r.contains(pg) { r.removeAll { $0 == pg } } else { r.append(pg) }; pages.saveRing(r)
                                }
                            }
                        }
                        HStack { Label10(text: "SHORTCUT"); KeyField(placeholder: PAGES_HOTKEY, text: pages.hotkey) { let ok = pages.setHotkey($0); u.rebindKeys(); return ok } }
                        Word(text: "PREVIOUS PAGE NOW", on: false) { pages.previous() }
                        Small(text: "Hold ⌥ and tap ` in Resolve to walk the ring (⇧ back), let go to open. Helper: \(pages.helperState)")
                        if !pages.said.isEmpty { Small(text: pages.said) }
                    }
                }
                Divider()
                // HD / UHD
                VStack(alignment: .leading, spacing: 8) {
                    ModuleHead(title: "HD / UHD", on: u.on["display"]!, set: { u.setModule("display", $0) }, value: display.mode)
                    if u.on["display"]! {
                        HStack { Word(text: "SWITCH NOW", on: false) { display.toggle() }; Word(text: "READ AGAIN", on: false) { display.read() } }
                        HStack { Label10(text: "SHORTCUT"); KeyField(placeholder: "ctrl+alt+cmd+U", text: display.hotkey) { let ok = display.setHotkey($0); u.rebindKeys(); return ok } }
                        if !display.said.isEmpty { Small(text: display.said) }
                    }
                }
                Divider()
                // IMPORT BUTTON
                VStack(alignment: .leading, spacing: 8) {
                    ModuleHead(title: "IMPORT BUTTON", on: u.on["import"]!, set: { u.setModule("import", $0) }, value: "BUTTON \(importer.button) → \(importer.keys.uppercased())")
                    if u.on["import"]! {
                        HStack { Word(text: importer.learning ? "PRESS IT NOW…" : "LEARN THE BUTTON", on: importer.learning) { importer.learn() }
                                 Label10(text: "KEYS"); KeyField(placeholder: "cmd+I", text: importer.keys) { importer.setKeys($0); return true } }
                        if !importer.tapOK {
                            Text("Accessibility: not allowed yet. System Settings → Privacy & Security → Accessibility → DaVinci Resolve Actions (Mantra) on.")
                                .font(.system(size: 11)).foregroundColor(AMBER).fixedSize(horizontal: false, vertical: true)
                        }
                        if !importer.said.isEmpty { Small(text: importer.said) }
                    }
                }
                Divider()
                // THE ONE-BUTTON ACTIONS
                VStack(alignment: .leading, spacing: 10) {
                    HStack { Text("ONE-BUTTON ACTIONS").font(.system(size: 12, weight: .bold, design: .monospaced)).foregroundColor(.white); Spacer()
                             Word(text: "INSTALL INTO RESOLVE'S MENU", on: false) { actions.installIntoResolve() } }
                    ForEach(actions.list) { a in
                        VStack(alignment: .leading, spacing: 2) {
                            HStack {
                                Word(text: (actions.running == a.id ? "… " : "▶ ") + a.name.uppercased(), on: actions.running == a.id) { actions.run(a) }
                                Spacer()
                                KeyField(placeholder: "shortcut", text: actions.hotkeys[a.id] ?? "") { let ok = actions.setHotkey(a, $0); u.rebindKeys(); return ok }
                            }
                            if let about = a.about { Small(text: about) }
                        }
                    }
                    if !actions.said.isEmpty { Text(actions.said).font(.system(size: 12, design: .monospaced)).foregroundColor(AMBER).fixedSize(horizontal: false, vertical: true) }
                    Small(text: "A new action: a script in the app's scripts folder and one line in actions.json. Shortcuts work while Resolve is in front.")
                }
                HStack { Spacer(); Text("v\(VERSION)").font(.system(size: 11, design: .monospaced)).foregroundColor(GREY).onTapGesture { NSWorkspace.shared.open(URL(string: RELEASES)!) } }
            }
            .padding(24)
        }
        }
        .frame(width: 600, height: 760).background(INK).preferredColorScheme(.dark)
    }
}

// made after launch: a status item needs a running NSApplication
let UMBRELLA = Umbrella()

final class Delegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ n: Notification) {
        _ = UMBRELLA
        _ = AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { false }
    // v3 (19.10.2026): the reopen (the star's row, the Dock) brings the window back, or lets the WindowGroup make a new one
    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows: Bool) -> Bool {
        let ws = s.windows.filter { $0.title.contains("DaVinci Resolve Actions") && ($0.isMiniaturized || $0.isVisible) }
        if ws.isEmpty { return true }
        for w in ws { w.deminiaturize(nil); w.makeKeyAndOrderFront(nil) }
        s.activate(ignoringOtherApps: true)
        return false
    }
    func applicationWillTerminate(_ n: Notification) { UMBRELLA.pages.stopHelper() }
}

@main struct DaVinciResolveActions: App {
    @NSApplicationDelegateAdaptor(Delegate.self) var delegate
    var body: some Scene {
        WindowGroup("DaVinci Resolve Actions (Mantra)") {
            SettingsView(u: UMBRELLA, pages: UMBRELLA.pages, display: UMBRELLA.display, importer: UMBRELLA.importer, actions: UMBRELLA.actions)
        }.windowResizability(.contentSize)
    }
}
