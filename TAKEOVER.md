# TAKEOVER

**31.10.2026, v17: TOP on the first row.** Marko: *"Each needs to have the same user interface elements. On, off and
top"*. TOP (TopWord in Common.swift) left of PERMISSIONS and ✕; green = window `.floating`, UserDefaults `onTop`,
applied at launch. OFF, TOP, PERMISSIONS, ✕ are Accessibility buttons (`off`, `top`, `permissions`, `close`).

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

## 4.11.2026 (v18–v20)
- Toggle HD UHD.py only writes ~/.config/hdbadge.json (no hs); this app follows it every second (menu bar "EDT · HD").
- Opens with Resolve (Star v14 row `with: com.blackmagic-design.DaVinciResolve`), quits itself 1 s after Resolve quits (v19).
- v20: Switch now / Read again are AX buttons (`hd-switch`, `hd-read`). The toggle knows only landscape HD/UHD: a vertical
  project reads "?" and a switch would make it 3840x2160. Test projects only (ELEVATE_MEDIA is vertical).


## From the former README (9.11.2026)

# DaVinci Resolve Actions (Mantra)

**One app for everything that automates DaVinci Resolve.** Marko, 13.10.2026: *"all the scripts related to Davinci
Resolve need to go under one common software called Davinci Resolve Actions. In the future, we are going to store
there many other actions which are going to automate by one button things inside Davinci Resolve ... Everything comes
under one umbrella application."*

`/Applications/DaVinci Resolve Actions (Mantra).app`, signed "Mantra Apps", built by `./build.sh`; the star opens it. While Resolve runs, one word sits in the menu bar, **`EDT · HD`** (the page and the resolution); its menu
reaches the pages, the HD/UHD switch, every action and the settings window.

## HANG DETECTOR (v21, 6.11.2026)

Marko: *"It's going to just warn you if DaVinci hangs. If it hangs, we need to restart it and start the job again"* and
*"give me the voice, and also show a message on screen that this DaVinci stopped responding"*.

Inside the router (`scripts/hang_watch.py`), every 5 sec through the router's own queue: a render whose percent and
output file stand still for 3 min (one pass) or 10 min (multi-pass: the second pass may sit still for minutes), or a
Resolve that does not answer for 90 sec, is HUNG. Then the voice says it once and a panel on the screen with the mouse
says **This DaVinci stopped responding** (the menu-bar word starts with ⚠ HUNG). A hung render is restarted by itself
(`scripts/hang_restart.py`): Cmd+S, Cmd+Q through Macro Recorder (ax-quit, SIGTERM, SIGKILL only if ignored; MANTRA 31.57), opened again, the project loaded, the half-written file
to the Trash, every unfinished job queued again with captions burned in whenever the timeline has captions, started;
at most 3 times for the same job. A frozen Resolve with no render running is only warned about: **RESTART DAVINCI**
in the panel is his. State: `~/.config/resolve-hang.json`. Built by GitHub Actions (`.github/workflows/build.yml`).

## ON / OFF and the ✕ (v3, 19.10.2026)

The window starts with **DAVINCI RESOLVE ACTIONS  ON  OFF** (MANTRA_MANIFEST swift-apps.md): ON is lit while it runs;
OFF quits it (the pages helper stops, the shortcuts and the import button go with it). The ✕ at the far right of that
row (Marko: *"unify the position of the close button on every application. It's far upper right corner"*) closes the
window only; every module keeps working, and a click on its row in the star, or Settings… in its menu-bar word, brings
the window back.

## Inside

| Module | What it does | State |
|---|---|---|
| **PAGES** | ⌥\` in Resolve walks its pages like ⌘Tab (⇧ back), let go to open, a quick tap = the last page; the ring is his choice | `~/.config/pages.json` |
| **HD / UHD** | the project flips between 1920x1080 and 3840x2160; a shortcut if he sets one | `~/.config/hdbadge.json` |
| **IMPORT BUTTON** | the mouse's thumb button in Resolve = ⌘I, Import Media; LEARN THE BUTTON, the keys are his | `~/.config/importbutton.json` |
| **J K L** (v4) | J, K, L in any app drive Resolve's playhead; the app in front never sees them (⌘ ⌃ ⌥ combinations stay letters). Resolve takes the focus without coming forward and gives it back 1.5 s after the last key, or at once on any other key. Switch: the window, or "J K L → Resolve from anywhere" in the menu-bar word | `resolve-actions.json` |
| **ONE-BUTTON ACTIONS** | `scripts/actions.json`: Create Timeline, Previous Page, Toggle HD/UHD, Check everything; a shortcut each | `~/.config/resolve-actions.json` |

Each module is ON or OFF in the window (`resolve-actions.json` → `modules`). Every shortcut is live only while Resolve
is in front. INSTALL INTO RESOLVE'S MENU copies the actions marked `menu` into Resolve's Workspace › Scripts › Utility.

## Adding an action

1. A Python script in `scripts/` that reaches Resolve the usual way (inside Resolve `resolve` exists; from outside it
   imports `DaVinciResolveScript`, which needs Resolve › Preferences › System › General › External scripting: **Local**).
   Its last printed line is what the app shows.
2. One entry in `scripts/actions.json`: `id`, `name`, `script`, optional `args`, `about`, `menu`.
3. `./build.sh`. A Claude session can write and try the script first through the DaVinci Resolve MCP
   (`run_script`, the scripting API), then save it here as an action.

## What it replaced (13.10.2026)

The star's Lua apps pages.lua, display.lua, importbutton.lua and their overlays; the same day's separate Swift apps
Resolve Pages, UHD HD Display and Import Button; and the `resolve-scripts` repository (its scripts now live in
`scripts/`). `scripts/Snap Captions.lua` is a Fusion composition script that runs inside Resolve's Fusion page (Fusion
speaks Lua); it is kept here with the rest, not run by the app.

Permission: Accessibility, for the event taps of the shortcuts (v5: ⌥` and the others are caught at the press, only when the key goes to Resolve), the import button and J K L. Every page press is logged in `~/.config/resolve-assistant.log`; when Resolve is too busy to answer its API in 0.6 s, Resolve's own ⇧2..⇧8 open the page.

## The router (v6, 22.10.2026)

`scripts/resolve_router.py` is the one connection to Resolve's scripting API, for this app and every Claude session.
It runs calls one at a time with a timeout and answers busy at once when Resolve hangs. The app starts it while Resolve
runs. `resolve-run` (linked into ~/.local/bin) is the command-line door: `resolve-run status`, `resolve-run --who me
job.py`, `hold`/`release`. Port `resolve` (8940) in ~/.config/mantra-ports.json, log ~/.config/resolve-router.log. The
rule: MANTRA_MANIFEST modules/resolve-router.md.

**v9 (28.10.2026):** every action has PLAY, NEXT STEP, STOP and RESTART, with a status line per step. A script marks its steps with `scripts/steps.py` (`step("title")`, `say("what it does")`) and lists their titles as `steps` in actions.json; see TAKEOVER.
