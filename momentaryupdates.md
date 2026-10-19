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
   the app runs; OFF stops the engine cleanly and quits the app. — **Status:** started
2. Closing the window leaves the app ON; the reopen (a click in the star or the Dock) shows the window again; `--login`
   still starts without a window. — **Status:** started
