# LESSONS

1. (13.10.2026) A status item made while the SwiftUI App is being built crashes (CGSConnectionByID); make it after
   applicationDidFinishLaunching (a lazy global touched there).
2. (13.10.2026) A helper started with Process and a stdin pipe did not see EOF when its app was killed (it stayed, its
   parent became launchd). pages_helper.py now leaves when getppid() == 1.
3. (13.10.2026) `pkill -f "Name (Mantra).app"` matches nothing: the parentheses are a regex group. Quit an app by its
   executable name, `pkill -x ResolvePages`.
4. (20.10.2026) Resolve (Qt) takes keys only while it is the active app: keys posted to its pid in the background, and
   its window made key through SLPSPostEventRecordTo without activating it, were both ignored (the playhead stayed at
   00:00:03:13), and its scripting API has GetCurrentTimecode / SetCurrentTimecode but no play or stop. Hence J K L lend
   the focus (_SLPSSetFrontProcessWithOptions with kCPSNoWindows, nothing raised) and give it back.
5. (20.10.2026) GetProcessForPID is unavailable in Swift; dlsym it from HIServices
   (ApplicationServices.framework/Frameworks/HIServices.framework). dlopen(nil) does not always find it.
6. (22.10.2026) ⌥` "sometimes works": three causes. (a) Resolve's scripting API stalls while Resolve is busy (100 % CPU:
   scriptapp() and GetCurrentPage hung over 25 s, also through Resolve's own MCP), and the helper waited with it; now an
   open unanswered in 0.6 s becomes Resolve's own ⇧2..⇧8. (b) sys.stdin.readline() after select() pulls every waiting
   line into Python's buffer, where select() no longer sees it: a second command waited for the next one. Read the
   descriptor with os.read and split lines yourself. (c) Carbon hot keys armed on didActivateApplication miss switches
   (the SkyLight lend, spaces); an event tap that asks at the press whether the key goes to Resolve does not.
7. (22.10.2026) A helper blocked inside a Resolve API call never reaches its getppid() check: when its app is killed it
   stays (found 23406 orphaned in WaitPkt). A Python watchdog thread does not help either: fusionscript keeps the GIL while it waits. The app kills orphans (pkill -9 -P 1) when it starts, and SIGKILLs its helper 2 s after quit.
8. (22.10.2026) Overwriting media that an open Resolve timeline uses (ffmpeg onto the same .mov) left Resolve's main
   thread spinning at 100 % for over ten minutes: no API, no keys. Hence the router (one connection, timeouts, busy
   answered at once) and the rule: new files, then relink.
9. (22.10.2026) Resolve opens on the screen named in Workspace → Primary Display, not where the window was left. Editing
   UI.preset's PrimaryScreenIdx with Resolve closed was not enough (it still opened on the MacBook); clicking the menu
   item through Accessibility worked and Resolve saved it.

## 28.10.2026: steps live in the script, control lives in a file

The router runs a script inside one worker process and only answers when it ends, so the app cannot reach between
steps through the router. A small file both sides read (control from the app, status from the script) works with the
router, without it, and from Resolve's own menu (no active control: the steps just print). The worker outlives runs, so
steps.py keys its state on the run id the app writes, never on module state alone.

## 29.10.2026
- Resolve's scripting cannot reach inside a multicam clip; work on a normal timeline (and Open in Timeline for angles).
- No command turns a hand-synced timeline into a multicam clip: give the clips the timeline's time code, then Create
  New Multicam Clip with Angle Sync: Timecode.
- Time code that travels with the files: ffmpeg -c copy -timecode for MP4, BWF time_reference for WAV; a 24 h wrap
  (a master starting at 21:43 puts late clips at 00:13) breaks a time-code sync: choose the master's start with room.
- Keypad digits opening the timecode box on a multicam: look for single viewer mode before writing a key mod.
- Resolve's keyboard preset (keyboard.preset.xml) is a hex-encoded binary blob: read it, never edit it by hand.
