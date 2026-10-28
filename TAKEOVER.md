# TAKEOVER

**28.10.2026, v10: a MODS tab.** Marko: "we have only one action: Color and Export ... These are all modifications of the
[functionality] of DaVinci Resolve. Please put them in Mods." Tabs: ACTIONS (only Balancing, Grading, and Exporting
Automatic), MODS (Create Timeline, Previous Page, Toggle HD / UHD, Check everything), NAVIGATE, PROJECT. The tab is
`"tab": "MODS"` in actions.json (none means ACTIONS). Both tabs seen in window captures.

**28.10.2026, v9: every action is played, stepped, stopped, restarted.** Marko: "Every action should have a play button,
a next button ("Next Step"), a stop button, and a restart button" and "a status line for each step, the title of the step".
- Each action has ▶ PLAY, ⏭ NEXT STEP, ■ STOP, ↻ RESTART. While it runs (or after), a box under it shows the run's state
  (RUNNING, WAITING FOR NEXT STEP, STOPPING, DONE, STOPPED, FAILED) and one line per step: mark, number, title, and the
  step's last status line.
- The wire: the app writes ~/.config/resolve-actions-control.json, the script's `scripts/steps.py` (step(title), say(text))
  waits on it between steps and writes ~/.config/resolve-actions-status.json, read four times a second. STOP ends the run
  at the next step() or say(), cleanly (SystemExit 0). A stepped run gets the router's longest time, 1800 s.
- Stepped scripts: Balancing Grading Exporting Automatic (6 steps), check.py (7 steps); their titles are `steps` in
  actions.json. Any other action is one step. Run from Resolve's own Scripts menu, step() and say() only print.
- Tested 28.10.2026 without Resolve, check.py from the terminal with the control file written by hand: NEXT STEP stops at
  each next step, PLAY runs to the end, STOP ends at the waiting step (exit 0), no control runs straight through. The
  window seen (v9, the four controls on every action). **Not yet seen: the step box during a run inside the app**, because
  the app starts an action only while Resolve runs; first time Resolve is open, run CHECK EVERYTHING with NEXT STEP.
- The grading script only got its steps marked; it was not run (Marko, 28.10.2026: "don't do any grading").


- `app/Common.swift`: VERSION, colours and words, JSONFile, Resolve and Python (`runScript`), keys (`Chord`), `HotKeys`
  (one Carbon handler; the set is armed only while Resolve is in front).
- `app/Pages.swift` (PagesModule + HUD), `app/Display.swift`, `app/ImportButton.swift` (the event tap), `app/Actions.swift`
  (actions.json, shortcuts, install into Resolve's menu), `app/JKL.swift` (the key tap, the focus lent to Resolve
  without raising it through SkyLight, given back after FOCUS_BACK), `app/Main.swift` (Umbrella: the status item and its menu, the
  modules on/off; SettingsView; the App).
- `scripts/` travels inside the app as Resources/scripts. `pages_helper.py` protocol: in `open <page>`, `pages`, `quit`;
  out `page <p>`, `pages a,b`, `waiting`, `error …`. It leaves by itself when its parent dies (getppid() == 1).
- Build: `./build.sh` (VERSION from app/Common.swift).
