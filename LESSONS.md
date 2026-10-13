# LESSONS

1. (13.10.2026) A status item made while the SwiftUI App is being built crashes (CGSConnectionByID); make it after
   applicationDidFinishLaunching (a lazy global touched there).
2. (13.10.2026) A helper started with Process and a stdin pipe did not see EOF when its app was killed (it stayed, its
   parent became launchd). pages_helper.py now leaves when getppid() == 1.
3. (13.10.2026) `pkill -f "Name (Mantra).app"` matches nothing: the parentheses are a regex group. Quit an app by its
   executable name, `pkill -x ResolvePages`.
