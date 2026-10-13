// THE ONE-BUTTON ACTIONS: scripts/actions.json lists them (a script and a line each), so a new action is added
// without touching this code. Each runs with Resolve's Python from outside; each can have his own shortcut (kept in
// ~/.config/resolve-actions.json), live only while Resolve is in front. The ones marked "menu" are also copied into
// Resolve's Workspace › Scripts › Utility, so they work from inside Resolve too.
import Foundation

struct Action: Identifiable, Decodable {
    let id: String; let name: String; let script: String
    var args: [String]? = nil; var about: String? = nil; var menu: Bool? = nil
}

final class ActionsModule: ObservableObject {
    @Published var list: [Action] = []
    @Published var hotkeys: [String: String] = [:]
    @Published var running: String?
    @Published var said = ""

    init() { load() }
    func load() {
        struct File: Decodable { let actions: [Action] }
        if let d = try? Data(contentsOf: URL(fileURLWithPath: SCRIPTS + "/actions.json")), let f = try? JSONDecoder().decode(File.self, from: d) { list = f.actions }
        let saved = SETTINGS.read()["actions"] as? [String: [String: Any]] ?? [:]
        hotkeys = saved.compactMapValues { $0["hotkey"] as? String }
    }
    func run(_ a: Action) {
        guard resolveApp() != nil else { said = "\(a.name): Resolve is not running"; return }
        running = a.id; said = "\(a.name)…"
        runScript(a.script, a.args ?? []) { code, line in
            self.running = nil
            self.said = "\(a.name): " + (line.isEmpty ? (code == 0 ? "done" : "failed (\(code))") : line)
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
