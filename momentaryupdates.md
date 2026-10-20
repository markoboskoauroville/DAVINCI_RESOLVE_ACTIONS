# DaVinci Resolve Actions: momentary updates

Every request from Marko, word for word, before any code. Each item has a Status line.

## 13.10.2026: one umbrella for everything Resolve

> and now migration, all the scripts related to Davinci Resolve need to go under one common software called Davinci Resolve Actions. In the future, we are going to store there many other actions which are going to automate by one button things inside Davinci Resolve through API or this other connection MCP, I think it's called. So no multiple now things for Resolve. Everything comes under one umbrella application

What goes under it (inventory 13.10.2026):
- Resolve Pages (Mantra).app (RESOLVE_PAGES, built today from the star's pages.lua): ⌥` walks the pages, the page in the menu bar.
- UHD HD Display (Mantra).app (UHD_HD_DISPLAY, built today from display.lua): HD / UHD word, click switches.
- Import Button (Mantra).app (IMPORT_BUTTON, built today from importbutton.lua): mouse button 4 in Resolve = ⌘I.
- resolve-scripts: Toggle HD UHD.py, Previous Page.py, Create Timeline.py (Resolve's Workspace › Scripts), check.py, star/.
- Resolve's Fusion/Scripts/Comp/Snap Captions.lua.
- The DaVinci Resolve MCP (run_script and the scripting API) as the second road for new actions.

**Status:** saved; not started.

## 19.10.2026: ON / OFF at the top of the window

> When I select any of the apps, the user interface opens up. In the top of every user interface, there will now be an on/off switch ... If I say on, I close it's on ... When I just switch the check mark, and that's how I activate it. This is gone. Let's work like this. This is the workflow now.

(MANTRA_MANIFEST modules/swift-apps.md, "ON / OFF at the top of every window"; the star, STAR_SWIFT v5, now only opens apps.)

1. The first row of the main window is ON / OFF in the window's own style, named after what it switches. ON is lit while
   the app runs; OFF stops the engine cleanly and quits the app. — **Status:** built 19.10.2026, v3: DAVINCI RESOLVE
   ACTIONS  ON  OFF above the scrolling modules (each module keeps its own ON / OFF below); OFF = NSApp.terminate,
   applicationWillTerminate stops pages_helper.py. Restarted 48786 → 39089 (helper 7248 left with the old app, new
   helper 39091). It came up without a window; a second `open` (the reopen) made it, which checks the reopen path.
   Checked by screenshot. Marko to try OFF.
2. Closing the window leaves the app ON; the reopen (a click in the star or the Dock) shows the window again; `--login`
   still starts without a window. — **Status:** built 19.10.2026, v3 (it already stayed on without its window; the
   reopen and Settings… now bring a closed window back; it has no --login).

> please unify the position of the close button on every application. It's far upper right corner. There is X to close the dialog in every dialog, same.

3. An ✕ at the window's far upper-right corner, on the ON / OFF row (ON / OFF at the left, ✕ at the right), grey; it
   closes the window only, the app stays ON. Every other dialog the app opens gets the same ✕. The title bar and its
   traffic lights stay as they are. — **Status:** built 19.10.2026, v3: ✕ (xmark, grey, 30×30) at the far right of
   the ON / OFF row, performClose. No other dialog (the pages HUD is an overlay, not a window he closes). Checked by
   screenshot. Marko to try ✕.

## 20.10.2026: J K L everywhere, the playhead in Resolve from anywhere

> we need to update my Davinci Resolve actions. We are building a new action which will block JKL keys anywhere in the system, and it will use JKL keys to control the playhead in the Davinci Resolve remotely, being Davinci Resolve in focus or not. Please build this module now

1. A new module, J K L, ON / OFF like the others: while it is ON, J, K and L never reach the app in front (any app);
   they move Resolve's playhead the way Resolve's own J K L do, whether Resolve is in front or not. — **Status:** built
   20.10.2026, v4 (app/JKL.swift): an event tap keeps J K L (alone or with ⇧) from every app while Resolve runs; Resolve
   becomes the active app without raising a window, plays the keys as its own, and the app he was in gets the focus back
   1.5 s after the last one (any other key gives it back at once and goes there). Keys to Resolve in the background were
   tried first and Resolve ignores them (LESSONS 4). ON by default; "J K L → Resolve from anywhere" in the menu-bar word
   switches it. Restarted 751 → 32920. Marko to try: L, K, J from another app.
