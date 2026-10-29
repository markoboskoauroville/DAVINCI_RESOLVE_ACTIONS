// THE ONE-BUTTON ACTIONS: scripts/actions.json lists them (a script and a line each), so a new action is added
// without touching this code. Each runs with Resolve's Python from outside; each can have his own shortcut (kept in
// ~/.config/resolve-actions.json), live only while Resolve is in front. The ones marked "menu" are also copied into
// Resolve's Workspace › Scripts › Utility, so they work from inside Resolve too.
import Foundation
import AppKit

struct Action: Identifiable, Decodable {
    let id: String; let name: String; let script: String
    var args: [String]? = nil; var about: String? = nil; var menu: Bool? = nil
    var group: String? = nil; var timeout: Int? = nil     // v8: the tab section it sits in; seconds the router allows it
    var steps: [String]? = nil                            // v9: the step titles, shown before the run (the script's step() calls)
    var tab: String? = nil                                // v10: "MODS" for a change to how Resolve itself works, else ACTIONS
    var ask: Ask? = nil                                   // v11: questions before every run (a folder, tick boxes)
    var direct: Bool? = nil                               // v11: run with Resolve's Python straight, not through the router
}

// v11 (Marko, 29.10.2026, Project Backup: "always before running, you ask for further user input. The user can press OK
// to confirm the last folder or enter a new one"): an action with "ask" opens a small form first; the folder is passed
// as --folder PATH and remembered, each ticked box as --<its words in lower case, joined by dashes>.
struct Ask: Decodable {
    var folder: String? = nil          // the label of the folder field; nil = no folder asked
    var checks: [String]? = nil        // tick boxes, off every time
    var warn: [String]? = nil          // ticks that destroy something: a second "are you sure" before the run
}

// v9 (28.10.2026, Marko: "Every action should have a play button, a next button (in this case, a "Next Step" button), a
// stop button, and a restart button. When I start an action, I still have control over how I run it" and "there should be
// a status line for each step, the title of the step, and I can press Next. If I press Play, I see what's going on"):
// one run at a time (the router runs one call at a time anyway). The app writes CONTROL, the script's steps.py waits on it
// between steps and writes STATUS, which is read four times a second while the run lasts.
let CONTROL = NSHomeDirectory() + "/.config/resolve-actions-control.json"
let STATUS = NSHomeDirectory() + "/.config/resolve-actions-status.json"

struct StepRow { var title: String; var state: String; var line: String }   // state: pending, waiting, running, done, stopped, failed

final class ActionsModule: ObservableObject {
    @Published var list: [Action] = []
    @Published var hotkeys: [String: String] = [:]
    @Published var running: String?          // the action of the current (or last) run
    @Published var said = ""
    @Published var phase = ""                 // RUNNING, WAITING FOR NEXT STEP, STOPPING, DONE, STOPPED, FAILED
    @Published var rows: [StepRow] = []
    @Published var live = false               // the script is still going
    var runID = ""; var mode = "play"; var allow = 0; var stopAsked = false
    var restartAfter: Action?
    var poll: Timer?

    init() { load() }
    func load() {
        struct File: Decodable { let actions: [Action] }
        if let d = try? Data(contentsOf: URL(fileURLWithPath: SCRIPTS + "/actions.json")), let f = try? JSONDecoder().decode(File.self, from: d) { list = f.actions }
        let saved = SETTINGS.read()["actions"] as? [String: [String: Any]] ?? [:]
        hotkeys = saved.compactMapValues { $0["hotkey"] as? String }
    }
    func run(_ a: Action) { play(a) }          // a shortcut or the menu: PLAY

    // ▶ PLAY: start, or let a paused run go on by itself
    func play(_ a: Action) {
        if live && running == a.id { mode = "play"; writeControl(); return }
        start(a, mode: "play")
    }
    // ⏭ NEXT STEP: start with the first step only, or let one more step begin (a playing run then pauses after this one)
    func next(_ a: Action) {
        if live && running == a.id {
            // the current step (0-based k) is step k+1 of steps.py, which begins once allow >= k+1: waiting there, this
            // lets it begin; running there (in PLAY), the run goes on to its end and pauses before the next one
            let k = rows.lastIndex { $0.state != "pending" } ?? 0
            mode = "step"; allow = max(allow, k + 1)
            writeControl(); return
        }
        start(a, mode: "step")
    }
    // ■ STOP: the script ends at its next step or status line
    func stop(_ a: Action) {
        guard live && running == a.id else { return }
        stopAsked = true; phase = "STOPPING"; writeControl()
    }
    // ↻ RESTART: stop, then play from the first step
    func restart(_ a: Action) {
        if live && running == a.id { restartAfter = a; stop(a) } else { start(a, mode: "play") }
    }

    func start(_ a: Action, mode m: String) {
        if let q = a.ask {
            guard !live else { said = "\(list.first { $0.id == running }?.name ?? "An action") is still running: STOP it first"; return }
            guard let extra = askBeforeRun(a, q) else { said = "\(a.name): cancelled"; return }
            var b = a; b.args = (a.args ?? []) + extra; b.ask = nil
            begin(b, mode: m); return
        }
        begin(a, mode: m)
    }

    /// The form before the run: the folder (the last one, OK keeps it), Choose…, the tick boxes. nil = cancelled.
    func askBeforeRun(_ a: Action, _ q: Ask) -> [String]? {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = a.name
        alert.informativeText = a.about ?? ""
        alert.addButton(withTitle: "OK"); alert.addButton(withTitle: "Cancel")
        let box = NSStackView(); box.orientation = .vertical; box.alignment = .leading; box.spacing = 8
        let lastKey = "ask." + a.id + ".folder"
        let field = NSTextField(string: SETTINGS.read()[lastKey] as? String ?? "")
        field.placeholderString = "/Volumes/…"
        field.widthAnchor.constraint(equalToConstant: 420).isActive = true
        if let label = q.folder {
            box.addArrangedSubview(NSTextField(labelWithString: label))
            let choose = NSButton(title: "Choose…", target: nil, action: nil)
            let chooser = Chooser(field: field); choose.target = chooser; choose.action = #selector(Chooser.pick)
            objc_setAssociatedObject(choose, "chooser", chooser, .OBJC_ASSOCIATION_RETAIN)
            let row = NSStackView(views: [field, choose]); row.spacing = 6
            box.addArrangedSubview(row)
        }
        let ticks = (q.checks ?? []).map { t -> NSButton in
            let c = NSButton(checkboxWithTitle: t, target: nil, action: nil); c.state = .off
            if q.warn?.contains(t) == true { c.contentTintColor = .systemRed }
            box.addArrangedSubview(c); return c
        }
        box.frame = NSRect(x: 0, y: 0, width: 520, height: CGFloat(30 + 26 * ticks.count + (q.folder == nil ? 0 : 50)))
        alert.accessoryView = box
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        var out: [String] = []
        if q.folder != nil {
            let path = (field.stringValue as NSString).expandingTildeInPath.trimmingCharacters(in: .whitespaces)
            guard !path.isEmpty else { said = "\(a.name): no folder given"; return nil }
            SETTINGS.change { $0[lastKey] = path }
            out += ["--folder", path]
        }
        let chosen = zip(q.checks ?? [], ticks).filter { $0.1.state == .on }.map { $0.0 }
        let dangerous = chosen.filter { q.warn?.contains($0) == true }
        if !dangerous.isEmpty {
            let sure = NSAlert()
            sure.alertStyle = .critical
            sure.messageText = dangerous.joined(separator: " and ") + "?"
            sure.informativeText = "This cannot be undone from here. Everything is copied and checked first; only then is it removed."
            sure.addButton(withTitle: "Yes, do it"); sure.addButton(withTitle: "Cancel")
            guard sure.runModal() == .alertFirstButtonReturn else { return nil }
        }
        out += chosen.map { "--" + $0.lowercased().split(separator: " ").joined(separator: "-") }
        return out
    }

    func begin(_ a: Action, mode m: String) {
        guard !live else { said = "\(list.first { $0.id == running }?.name ?? "An action") is still running: STOP it first"; return }
        guard resolveApp() != nil else { said = "\(a.name): Resolve is not running"; return }
        running = a.id; runID = UUID().uuidString; mode = m; allow = m == "step" ? 1 : 0; stopAsked = false; live = true
        rows = (a.steps ?? [a.name]).map { StepRow(title: $0, state: "pending", line: "") }
        phase = "RUNNING"; said = ""
        try? FileManager.default.removeItem(atPath: STATUS)
        writeControl()
        poll?.invalidate()
        poll = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in self?.readStatus() }
        let stepped = a.steps != nil
        if !stepped { rows[0].state = "running" }
        // a run that waits between steps needs the router's longest time (1800 s), not the script's own
        runScript(a.script, a.args ?? [], timeout: stepped ? 1800 : (a.timeout ?? 30), direct: a.direct == true) { code, line in
            self.readStatus()
            self.poll?.invalidate(); self.live = false; self.writeControl(active: false)
            let stopped = self.stopAsked || self.rows.contains { $0.state == "stopped" }
            if stopped { self.phase = "STOPPED" }
            else if code == 0 { self.phase = "DONE"; for i in self.rows.indices where self.rows[i].state != "pending" { self.rows[i].state = "done" }
                if !stepped { self.rows[0].state = "done" } }
            else { self.phase = "FAILED (\(code))"; if let i = self.rows.lastIndex(where: { $0.state != "pending" }) ?? (stepped ? nil : 0) { self.rows[i].state = "failed" } }
            if !line.isEmpty, let i = self.rows.lastIndex(where: { $0.state != "pending" }), self.rows[i].line.isEmpty || code != 0 { self.rows[i].line = line }
            self.said = "\(a.name): " + self.phase.lowercased()
            if let r = self.restartAfter { self.restartAfter = nil; self.start(r, mode: "play") }
        }
    }

    func writeControl(active: Bool = true) {
        let c: [String: Any] = ["run": runID, "active": active, "mode": mode, "allow": allow, "stop": stopAsked]
        if let d = try? JSONSerialization.data(withJSONObject: c) {
            try? FileManager.default.createDirectory(atPath: NSHomeDirectory() + "/.config", withIntermediateDirectories: true)
            try? d.write(to: URL(fileURLWithPath: CONTROL), options: .atomic)
        }
    }

    func readStatus() {
        guard let d = try? Data(contentsOf: URL(fileURLWithPath: STATUS)),
              let s = try? JSONSerialization.jsonObject(with: d) as? [String: Any], s["run"] as? String == runID,
              let st = s["steps"] as? [[String: Any]] else { return }
        for (i, x) in st.enumerated() {
            let r = StepRow(title: x["title"] as? String ?? "", state: x["state"] as? String ?? "", line: x["line"] as? String ?? "")
            if i < rows.count { rows[i] = r } else { rows.append(r) }
        }
        guard live, !stopAsked else { return }
        switch s["state"] as? String {
        case "waiting": phase = "WAITING FOR NEXT STEP"
        case "stopped": phase = "STOPPED"
        default: phase = mode == "step" ? "RUNNING THIS STEP" : "RUNNING"
        }
    }
    func setHotkey(_ a: Action, _ t: String) -> Bool {
        let v = t.trimmingCharacters(in: .whitespaces)
        guard v.isEmpty || Chord(v) != nil else { said = "\"\(v)\" is not a key I know"; return false }
        hotkeys[a.id] = v.isEmpty ? nil : v
        SETTINGS.change { s in
            var all = s["actions"] as? [String: [String: Any]] ?? [:]
            all[a.id] = v.isEmpty ? nil : ["hotkey": v]; s["actions"] = all
        }
        said = v.isEmpty ? "\(a.name): no shortcut" : "\(a.name): \(v)"; return true
    }
    // v8: the groups in the order they first appear in actions.json
    var groups: [String] { var seen: [String] = []; for a in list { let g = a.group ?? "OTHER"; if !seen.contains(g) { seen.append(g) } }; return seen }
    // v10 (28.10.2026, Marko: "we have only one action ... These are all modifications of the [functionality] of DaVinci
    // Resolve. Please put them in Mods"): the tab an action sits in, ACTIONS unless actions.json says MODS
    func inTab(_ t: String) -> [Action] { list.filter { ($0.tab ?? "ACTIONS") == t } }
    func groups(_ t: String) -> [String] { var seen: [String] = []; for a in inTab(t) { let g = a.group ?? "OTHER"; if !seen.contains(g) { seen.append(g) } }; return seen }
    func keys() -> [(Chord, () -> Void)] {
        list.compactMap { a in hotkeys[a.id].flatMap(Chord.init).map { c in (c, { [weak self] in self?.run(a) }) } }
    }
    // the menu-marked scripts into Resolve's own Scripts menu (Resolve reads the folder each time the menu opens)
    func installIntoResolve() {
        let fm = FileManager.default
        try? fm.createDirectory(atPath: UTILITY, withIntermediateDirectories: true)
        var n = 0
        for a in list where a.menu == true {
            let to = UTILITY + "/" + a.script
            try? fm.removeItem(atPath: to)
            if (try? fm.copyItem(atPath: SCRIPTS + "/" + a.script, toPath: to)) != nil { n += 1 }
        }
        said = "\(n) scripts are in Resolve's Workspace › Scripts › Utility"
    }
}

/// v11: the folder field's Choose… button (an NSOpenPanel for folders).
final class Chooser: NSObject {
    let field: NSTextField
    init(field: NSTextField) { self.field = field }
    @objc func pick() {
        let p = NSOpenPanel(); p.canChooseDirectories = true; p.canChooseFiles = false; p.canCreateDirectories = true
        if !field.stringValue.isEmpty { p.directoryURL = URL(fileURLWithPath: field.stringValue) }
        if p.runModal() == .OK, let u = p.url { field.stringValue = u.path }
    }
}
