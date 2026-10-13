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
