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
   switches it. Restarted 751 → 32920. Marko tried it 20.10.2026: "yes, it moved. I tested it."

## 22.10.2026: ⌥` sometimes works, sometimes not

> Please fix my app Devon the Da Vinci Resolve Actions. There is a bug. Alt tick doesn't work to change my pages. Sometimes works, sometimes doesn't. So I'm confused what is that? You need to debug this application so it works. And eat category in the star menu, please change to Da Vinci Resolve Actions. But there is no need for category. If any category has only one entry. Actually, there should be direct access. If there is more than one, then we go to sub-menus. Fix everything.

1. ⌥` walks the pages every time. — **Status:** v5 built 22.10.2026. Three causes found (LESSONS 6–7): Resolve's API
   stalls while Resolve is busy (seen: 100 % CPU, every API call hung over 25 s, two old helpers frozen in it), the
   helper lost a command that arrived with another (proved), and the Carbon hot keys were armed only on app-switch
   notifications. Now: the shortcut is caught by an event tap at the press, an open unanswered in 0.6 s becomes Resolve's
   own ⇧2..⇧8, orphaned helpers are killed, every press is logged in ~/.config/resolve-assistant.log. Restarted
   23405 → 27571. Marko to try ⌥` in Resolve.

## 22.10.2026: the Resolve API router

> yes, I can switch between pages only in the menu. But actually, in reality the Davinci doesn't switch pages right now. There's another session, Elevate Media Local, who is using Davinci, so there is some clash in API access. We need to solve this API access. You need to make API access router for Davinci to resolve this kind of problems. If two apps are reaching resolve at the same time, talk with Elevate Media Local and please coordinate how you use Davinci resolve and fix that. When I have menu item and switch to another page, actually the action is happening now. It's not happening

1. One router owns Resolve's scripting connection; every app and every session sends its calls through it, one at a
   time, each with a timeout, and hears "busy" at once instead of hanging. — **Status:** building.
2. Coordinate with "elevate media local". — **Status:** it overwrote four .movs on the open timeline with ffmpeg at 17:30–17:55 (the likely cause of the spin), no API calls of its own then. It got the resolve-run commands and holds Resolve while it works.
3. A page chosen in the menu must really change in Resolve. — **Status:** found Resolve's main thread spinning at 100 %
   since about 18:05 (no API, no keys get in); four stuck "Toggle HD UHD --read" of ours removed, Resolve still spins. Marko restarted Resolve; through the router the page changes in 0.16 s.

## 22.10.2026: Resolve on the BenQ

> Davinci is always open. Please configure it so it opens on BenQ monitor, not on this monitor of MacBook Pro ... Please shut down Davinci. Don't care about lost work, and open it on BenQ and tell me why it's not opening

1. Why: Resolve's Workspace → Primary Display was "Built-in Retina Display"; moving the window by hand does not change
   it, so every start put Resolve back on the MacBook. — **Status:** done 22.10.2026: Resolve killed, reopened, Primary
   Display set to "BenQ LCD" through its own menu (Accessibility); the window is 0,0 2560×1440 on the BenQ; saved by
   Resolve (UI.preset PrimaryScreenIdx 0, 18:22). Marko: "issue with monitor fixed now".

4. Marko, 22.10.2026: *"confirmed it's working. Give session to other session"*. ⌥` and the page menu confirmed by Marko; Resolve handed to "elevate media local".

## 26.10.2026 — the playback frame rate follows the project's

> "that reminds me that we need to update my helper for DaVinci Resolve. When I change the frame rate of the project, the playback frame rate stays in manual mode. It doesn't follow up. Usually, my project is at 30 fps. It's at 25, then I change it to 30. Then my next project is in 25, and I always need to go in Settings and change the playback rate manually. I have the same exact same problem with my DaVinci Resolve and the dropping sound. Things become unsynchronized. It's nonsense. I don't know why they have two settings, but synchronize these two settings always" (Marko, 26.10.2026)

- Resolve's playback frame rate always equals the project's (timeline) frame rate, in every project, at every change; the sound drops and the loss of sync that the mismatch causes go with it. — **Status:** v7 built: the router compares every 3 s and sets playback to the open timeline's (custom) or the project's rate. TESTED with Resolve 26.10.2026 07:59 in a new empty project "Mantra fps test 25" (deleted after; PIXAR_husband-song_V2 reopened): the mismatch is seen at once (playback 30, project 25), but Resolve REFUSES SetSetting('timelinePlaybackFrameRate') in every form ('25', 25, '25.0', ...) — the scripting stub says "Read-only". Ways left: a project-settings preset per rate (SetPreset; a preset also carries resolution and colour), or the Project Settings dialog through accessibility. Marko's choice.

> "for davinci, save the preset per frame rate" (Marko, 26.10.2026)

- The answer to the two ways (presets per rate, or the Project Settings dialog): a project-settings preset per frame rate, so the playback rate comes with the rate. — **Status:** asked.

## 28.10.2026

"please burn in this workflow inside the DaVinci Resolve workflows. It is called \"Balancing, Grading, and Exporting Automatic.\" Next time, I don't need to use the UAI tool. I just press a button and everything is happening automatically"

"I have a tool in a star menu called \"DaVinci Resolve Actions.\" Inside, put this action and make a tab for Actions. Please redesign the user interface for this application with tabs and group different styles of working. This is Actions"

"after color grade, apply the look from Kodak stock build-in. Use the build-in effect film look"

"your color grading is wrong. You need to balance the shot, right? First of all, you have burnout in some shots. There is burnout, so you need to pay attention to the highlights. Highlights should not be burned out, and the whole image should be balanced.

Please work in DaVinci Resolve color space and export as 709 workspace, and don't make anything a clip"

"final grade. Make it with the film look plugin The film, whatever the name is."

"any changes you are making to the image exposure? Use the Curves only. Curves and everything you need to do inside the Color page. I want to see all nodes. Everything you are doing, one node, one correction"

"When the we finish the project, then you're going to put this in the application. For now we need to find the right workflow."

"for this kind of workflow, I need a tutorial, the same as we are doing for mixing inside Ableton Live. Same style of the tutorial. See the repositories and understand how it's done. Make lifestyle images and diagrams to understand what it is. You can use Nano Banana in Chrome or Grok in Chrome, whatever. Make a nice tutorial for this workflow. You need to guide me how to set up the whole thing, so in the future I can just press \"Action\" and everything is happening automatically"

"this is not happening. Use Grok instead"

"continue with Gemini working Gemini refused multiple times to grow."

"please call me in voice if you need some actions from me"

## 28.10.2026: every action with play, next step, stop, restart

> please also fix my DaVinci Resolve action mantra application. Every action should have a play button, a next button (in this case, a "Next Step" button), a stop button, and a restart button. When I start an action, I still have control over how I run it

> also, there should be a status line for each step, the title of the step, and I can press Next. If I press Play, I see what's going on. That's all

## 28.10.2026: a MODS tab

> please fix my DaVinci Resolve actions mantra. Actually, we have only one action: Color and Export Timeline Project. Check. These are all modifications of the Functioniko Ebleton of DaVinci Resolve. Please put them in Mods. Inside Actions, we have only one, so the new tab is called Mods

Read as: ACTIONS holds only "Balancing, Grading, and Exporting Automatic" (COLOR AND EXPORT); TIMELINE (Create Timeline,
Previous Page), PROJECT (Toggle HD / UHD) and CHECK (Check everything) are modifications of DaVinci Resolve's
functionality and go into a new tab MODS.

> Actions and Mods are two only tabs. Navigate and Projects are under Mods, actually

## 29.10.2026 — action: Export Current Project to a Folder (with Delete Source Media / Delete Source Project)

> You finish testing. Please make DaVinci Actions: "Export Current Project to a Folder." That is doing what it collects all the media from the project and the project file itself and saves it in a predefined folder. The user selects it, and always before running, you ask for further user input. The user can press OK to confirm the last folder or enter a new one. The same action needs to have the option Delete Source Media. It means it's going to delete all the media. Another checkmark is Delete Source Project, so the project is gone. It's complete cleanup.
>
> Move the folder and media and everything to an external drive. The project is deleted. We have there one project file and we have a media file. You need to organize everything in a unifying structure. The project name is the folder name, and inside the folder name is the project itself with its name. Then you can make a folder called Sources, and inside Sources you collect sources from everywhere. You need to rearrange them in three categories: images, videos, and audio.

> While an action is running, it must have a verbose display showing what is currently copying, the speed of the transfer, and the estimated time for finishing the action.

> We can call this Action Project Backup.

> Yes, we can. Also now you remind me this is a project backup and clean up. It means you need to clean up every render file, everything what this project was generating from the system drive.

**Status:** v11 29.10.2026: PROJECT BACKUP in ACTIONS (group PROJECT). Before every run a form: the backup folder (the
last one, OK keeps it; Choose…), Delete Source Media, Delete Source Project (both red, a second "are you sure").
<folder>/<project>/<project>.drp, Sources/Images | Videos | Audio, Renders. Six steps with a live line: file, size,
MB/s, done of total, time left. Every copy size-checked before anything is removed; originals and everything the
project made go to the Trash (recoverable); the project is deleted only after its .drp is on the drive; without the
delete ticks the open project keeps its own files. Runs outside the router (no 30-minute limit).
Tested twice with throwaway projects and generated test files (PETAK13B saved, closed, reopened on Deliver, its 2
render jobs untouched): structure right, name clash → "clip (2).mp4", the .drp points at Sources, originals in the
Trash, the project gone from Resolve, its render backed up and removed, a source clip in the render folder not
mistaken for a render, the gallery gone. Not yet seen: the form in the app (Marko's PLAY).

## 29.10.2026 — the ACTIONS tab as a plain list

> Please, inside the actions, write "Simplify action flow: just one action after the other, top of each other." A list of actions so we understand what's going on without too much additional text.

**Status:** in progress 29.10.2026.
