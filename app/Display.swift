// HD / UHD: Resolve's project resolution (from UHD HD Display (Mantra) v2, itself from the star's display.lua). The
// switch is scripts/Toggle HD UHD.py, Resolve's own scripting; it writes the new mode into ~/.config/hdbadge.json,
// which is followed every second. --read asks without changing anything.
import Foundation

let HD_FILE = JSONFile("hdbadge.json")

final class DisplayModule: ObservableObject {
    @Published var mode = HD_FILE.read()["mode"] as? String ?? "?" { didSet { onChange?() } }
    @Published var hotkey = HD_FILE.read()["hotkey"] as? String ?? ""
    @Published var said = ""
    var onChange: (() -> Void)?
    var on = false
    init() {
        Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self = self, let m = HD_FILE.read()["mode"] as? String, m != self.mode else { return }
            self.mode = m
        }
    }
    func toggle() {
        guard resolveApp() != nil else { said = "Resolve is not running"; return }
        said = "switching…"
        runScript("Toggle HD UHD.py") { code, line in
            self.said = code == 0 ? line : "Resolve: \(line.isEmpty ? "the script failed" : line) (External scripting: Local?)"
        }
    }
    func read() {
        guard on, resolveApp() != nil else { return }
        runScript("Toggle HD UHD.py", ["--read"]) { code, line in
            if code == 0 && (line == "HD" || line == "UHD") { self.mode = line; HD_FILE.change { $0["mode"] = line } }
        }
    }
    func hotkeys() -> [(Chord, () -> Void)] {
        guard on, let c = Chord(hotkey) else { return [] }
        return [(c, { [weak self] in self?.toggle() })]
    }
    func setHotkey(_ t: String) -> Bool {
        let v = t.trimmingCharacters(in: .whitespaces)
        guard v.isEmpty || Chord(v) != nil else { said = "\"\(v)\" is not a key I know"; return false }
        hotkey = v; HD_FILE.change { $0["hotkey"] = v }; said = v.isEmpty ? "no shortcut" : "\(v) switches"; return true
    }
}
