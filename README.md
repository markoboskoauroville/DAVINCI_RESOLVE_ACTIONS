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
