# TAKEOVER

**29.10.2026, v11: PROJECT BACKUP (backup and clean up).** scripts/Project Backup.py; actions.json "ask" (a form before
the run: folder → --folder, ticks → --delete-source-media / --delete-source-project, "warn" ticks get a second confirm)
and "direct" (runScript without the router: no time limit). Renders = files in a render job's TargetDir named like its
output (exact, or the words before the clip name for per-clip jobs), never a project source. Generated = CacheClip/<id>,
.gallery/<id>, projectMediaLocation/<name>, linked proxies. Trash through Finder (recoverable). Image sequences are left
in place. Tested 29.10.2026 on two throwaway projects (see momentaryupdates).

**28.10.2026, v10: a MODS tab.** Marko: "we have only one action: Color and Export ... These are all modifications of the
[functionality] of DaVinci Resolve. Please put them in Mods." Tabs: ACTIONS (only Balancing, Grading, and Exporting
Automatic) and MODS, the only two tabs (Marko: "Actions and Mods are two only tabs. Navigate and Projects are under
Mods"). MODS: Create Timeline, Previous Page, Toggle HD / UHD, Check everything, then PAGES, J K L, HD / UHD and the
IMPORT BUTTON. An action's tab is `"tab": "MODS"` in actions.json (none means ACTIONS); a saved NAVIGATE or PROJECT tab
opens as MODS. Both tabs seen in window captures. (A first v10 push had a broken Swift string in the bottom hint; fixed.)

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

## tools/avsync.py and tools/songfind.py: sync by sound (29.10.2026)

Used on SANTOSH / MEGAMIX to sync Svemir's α7 V (Rec Run timecode, useless for sync) and the eight printed desk songs to
Marko's continuous camera take, after Resolve's own "Sync by sound" failed. The sound is reduced to an onset envelope
(where new sound starts in each band, log magnitude, so level and EQ drop out) and slid against the other recording.
`songfind.py <long file> <songs...>` finds each song in a long take (50 values/s, FFT correlation, strength above 10 is
certain); `avsync.measure(A, tA, B, tB)` refines to 5 ms. Measure at 2–3 points per clip: agreement means right and no drift.
Placement went through the Resolve scripting (DeleteClips + AppendToTimeline with recordFrame, mediaType 1 and 2 separately:
a single AppendToTimeline without mediaType lost the linked audio). Next: make it an Action ("Sync by rhythm").

## 29.10.2026 (afternoon): time code from the music, NUMBER KEYS tried and removed

- **tools/retimecode_by_music.py** (from the Santoshi concert): every clip gets the master camera's time code at the
  moment it was recorded, measured with avsync/songfind (music onsets). MP4: `ffmpeg -map 0:v:0 -map 0:a -c copy
  -timecode HH:MM:SS:FF` into a NEW file (originals untouched; Sony's rtmd data stream is left out). WAV: BWF
  `-write_bext 1 -metadata time_reference=<samples since midnight>`. Resolve reads both as Start TC (checked). Result:
  ~/Music/SantoshiKoncert/SYNCHRONIZED BY TIME CODE (+ time codes.json), bin "synchronized by time code", timeline
  "MEGAMIX synchronized by time code" placed by time code alone. Next: make it an action (Marko: "the user should point
  to the name of the bin ... our algorithm should synchronize by music, changing the time codes").
- Open: Marko's camera picture (V1) looked out of sync against the rest; all sync rests on its SOUND, so if its sound
  is late against its picture, the same offset stays. Light/motion correlation of pictures was too weak (strength ~3)
  and Marko stopped it; ask him the frames by eye.
- NUMBER KEYS (v14) held the keypad back off multicam clips; removed in v15. The real cause was single viewer mode:
  with the source viewer hidden, Switch to Angle has no multicam viewer and Resolve hands the digit to timecode entry.
