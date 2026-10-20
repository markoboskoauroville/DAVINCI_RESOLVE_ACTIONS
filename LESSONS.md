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
