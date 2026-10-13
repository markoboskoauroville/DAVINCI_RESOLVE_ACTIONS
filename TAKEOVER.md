# TAKEOVER

- `app/Common.swift`: VERSION, colours and words, JSONFile, Resolve and Python (`runScript`), keys (`Chord`), `HotKeys`
  (one Carbon handler; the set is armed only while Resolve is in front).
- `app/Pages.swift` (PagesModule + HUD), `app/Display.swift`, `app/ImportButton.swift` (the event tap), `app/Actions.swift`
  (actions.json, shortcuts, install into Resolve's menu), `app/Main.swift` (Umbrella: the status item and its menu, the
  modules on/off; SettingsView; the App).
- `scripts/` travels inside the app as Resources/scripts. `pages_helper.py` protocol: in `open <page>`, `pages`, `quit`;
  out `page <p>`, `pages a,b`, `waiting`, `error …`. It leaves by itself when its parent dies (getppid() == 1).
- Build: `./build.sh` (VERSION from app/Common.swift).
