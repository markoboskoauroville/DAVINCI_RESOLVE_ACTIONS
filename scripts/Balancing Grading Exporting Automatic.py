#!/usr/bin/env python3
"""
Balancing, Grading, and Exporting Automatic, a DaVinci Resolve action (README.md).
Marko, 28.10.2026: "normalize exposure in every shot, and then color grade it to be like some popular music video
film stock ... filmic and high-end ... then export all individual clips in the folder of footages. For Svenir, you can
make a folder and put them inside, because he is editing on a 20-year-old PC. It must be MP4, H.264, not 5 ... full HD
... 20 megabits per second." Then: "burn in this workflow ... I just press a button and everything is happening
automatically."

One press, on the current timeline:
  1. Colour management: DaVinci YRGB Color Managed, timeline DaVinci WG/Intermediate, output Rec.709 Gamma 2.4 with
     DaVinci tone mapping.
  2. Input colour space per clip from the Sony sidecar XML (C0042M01.XML next to C0042.MP4): S-Log3 / S-Gamut3.Cine,
     S-Log3 / S-Gamut3, S-Log2. A clip without a log XML stays as Resolve reads it.
  3. Balancing: ffmpeg reads five frames of the used part of each clip, the log-average scene light in stops. Each clip
     moves 70 % of the way to the median of all clips, never more than 1.5 stops, as a CDL Offset on node 1 (one stop
     is 0.0733 in DaVinci Intermediate). Sky shots stay bright, dark ones come up.
  4. Grading: every clip into the colour group MANTRA FILMIC; its post-clip node carries Mantra Filmic.cube, written
     by this script into Resolve's LUT folder, Mantra/: first the grade (teal shadows, warm highlights, a little less
     saturation, a gentle lift in the blacks), then Resolve's own Kodak 2383 print film look (Film Looks/Rec709 Kodak
     2383 D65.cube, Cineon in), with the conversions around it (DaVinci Intermediate to Cineon, Rec.709 back), so the
     print film's own contrast and roll-off are the curve. Marko, 28.10.2026: "after color grade, apply the look from
     Kodak stock build-in." Output tone mapping is then None: the print film already rolls the highlights off.
  5. Exporting: each clip on its own, MP4 H.264, 1920x1080, 20 Mb/s, audio on, into a folder "FOR SVEMIR HD H264"
     beside the footage. The render starts and the script returns; Resolve shows its progress.

Run it again after a change: the offsets are measured anew, the look and the group are reused. The last printed line
is what DaVinci Resolve Actions shows.
"""

import json
import math
import os
import re
import statistics
import subprocess
import sys

STEP = 0.07329248            # one stop in DaVinci Intermediate
PULL, LIMIT = 0.7, 1.5       # how far to the median, at most how many stops
BITRATE = 20000              # kb/s
OUT_NAME = "FOR SVEMIR HD H264"
GROUP = "MANTRA FILMIC"
LUT_DIR = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/Mantra"
LUT_FILE = "Mantra Filmic.cube"
KODAK = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/Film Looks/Rec709 Kodak 2383 D65.cube"
FFMPEG = next((p for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg") if os.path.exists(p)), "ffmpeg")

SONY = {("s-log3-cine", "s-gamut3-cine"): "S-Gamut3.Cine/S-Log3",
        ("s-log3", "s-gamut3"): "S-Gamut3/S-Log3",
        ("s-log3-cine", "s-gamut3"): "S-Gamut3/S-Log3",
        ("s-log2", "s-gamut"): "S-Gamut/S-Log2"}


def get_resolve():
    try:
        return resolve                                    # noqa: F821  inside Resolve (or the router) the name exists
    except NameError:
        pass
    api = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting'
    os.environ.setdefault('RESOLVE_SCRIPT_API', api)
    os.environ.setdefault('RESOLVE_SCRIPT_LIB',
                          '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so')
    sys.path.append(os.path.join(api, 'Modules'))
    import DaVinciResolveScript as dvr                   # noqa: E402
    return dvr.scriptapp('Resolve')


def say(*a):
    print(*a, flush=True)


# ---- the look, in DaVinci Intermediate in and out --------------------------------------------------------------------

def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def grade(r, g, b):
    """The grade, in DaVinci Intermediate: split tone, less saturation, lifted blacks. The contrast is the film's."""
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sh, hi = 1 - smooth(0.15, 0.42, y), smooth(0.38, 0.65, y)
    r += -0.010 * sh + 0.012 * hi                         # teal shadows, warm highlights
    g += 0.003 * sh + 0.004 * hi
    b += 0.011 * sh - 0.014 * hi
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    r, g, b = (y + (c - y) * 0.9 for c in (r, g, b))      # a little less saturation
    lift = 0.012 * (1 - smooth(0.0, 0.30, y))             # blacks lifted, never crushed
    return r + lift, g + lift, b + lift


# DaVinci Intermediate and Wide Gamut (Blackmagic's white paper), Cineon (Kodak), Rec.709
DI_A, DI_B, DI_C, DI_M, DI_LIN, DI_LOG = 0.0075, 7.0, 0.07329248, 10.44426855, 0.00262409, 0.02740668


def di_dec(y):
    return y / DI_M if y <= DI_LOG else 2 ** (y / DI_C - DI_B) - DI_A


def di_enc(x):
    return x * DI_M if x <= DI_LIN else (math.log2(x + DI_A) + DI_B) * DI_C


def to_xyz(prim, white=(0.3127, 0.3290)):
    def xyz(x, y):
        return [x / y, 1.0, (1 - x - y) / y]
    cols = [xyz(*p) for p in prim]
    m = [[cols[c][r] for c in range(3)] for r in range(3)]
    s = mul(inv(m), xyz(*white))
    return [[m[r][c] * s[c] for c in range(3)] for r in range(3)]


def inv(m):
    a, b, c = m[0]; d, e, f = m[1]; g, h, i = m[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def mul(m, v):
    return [sum(m[r][k] * v[k] for k in range(3)) for r in range(3)]


def matmul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


DWG = to_xyz([(0.8000, 0.3130), (0.1682, 0.9877), (0.0790, -0.1155)])
R709 = to_xyz([(0.640, 0.330), (0.300, 0.600), (0.150, 0.060)])
DWG_TO_709, R709_TO_DWG = matmul(inv(R709), DWG), matmul(inv(DWG), R709)
CIN_B = 10 ** ((95 - 685) / 300)


def cineon_enc(x):
    return (685 + 300 * math.log10(max(x, 0) * (1 - CIN_B) + CIN_B)) / 1023


def read_cube(path):
    n, rows = 0, []
    for line in open(path):
        t = line.split()
        if not t or t[0].startswith("#"):
            continue
        if t[0] == "LUT_3D_SIZE":
            n = int(t[1])
        elif len(t) == 3:
            try:
                rows.append(tuple(float(v) for v in t))
            except ValueError:
                pass
    return n, rows


def sample(cube, r, g, b):
    """Trilinear, red fastest (the .cube order)."""
    n, rows = cube
    def at(i, j, k):
        return rows[i + j * n + k * n * n]
    f = [min(max(c, 0.0), 1.0) * (n - 1) for c in (r, g, b)]
    i0 = [min(int(c), n - 2) for c in f]
    t = [c - i for c, i in zip(f, i0)]
    out = [0.0, 0.0, 0.0]
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                w = (t[0] if di else 1 - t[0]) * (t[1] if dj else 1 - t[1]) * (t[2] if dk else 1 - t[2])
                v = at(i0[0] + di, i0[1] + dj, i0[2] + dk)
                for c in range(3):
                    out[c] += w * v[c]
    return out


KODAK_CUBE = None


def look(r, g, b):
    """DaVinci Intermediate in and out: the grade, then Kodak 2383 print film."""
    r, g, b = grade(r, g, b)
    if not KODAK_CUBE:
        return tuple(min(1.0, max(0.0, c)) for c in (r, g, b))
    lin709 = mul(DWG_TO_709, [di_dec(c) for c in (r, g, b)])
    shown = sample(KODAK_CUBE, *[cineon_enc(c) for c in lin709])          # Rec.709, gamma 2.4 on the screen
    back = mul(R709_TO_DWG, [max(c, 0.0) ** 2.4 for c in shown])
    return tuple(min(1.0, max(0.0, di_enc(max(c, 0.0)))) for c in back)


def write_lut(path, n=33):
    global KODAK_CUBE
    KODAK_CUBE = read_cube(KODAK) if os.path.exists(KODAK) else None
    lines = ['TITLE "Mantra Filmic + Kodak 2383 (DaVinci Intermediate in and out), Mantra Productions 28.10.2026"',
             f"LUT_3D_SIZE {n}", "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 1 1 1"]
    for bi in range(n):
        for gi in range(n):
            for ri in range(n):
                lines.append("%.6f %.6f %.6f" % look(ri / (n - 1), gi / (n - 1), bi / (n - 1)))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ---- measuring ------------------------------------------------------------------------------------------------------

def sony_space(path):
    xml = os.path.splitext(path)[0] + "M01.XML"
    if not os.path.exists(xml):
        return None, None
    text = open(xml, errors="ignore").read()
    gamma = re.search(r'CaptureGammaEquation" value="([^"]+)"', text)
    gamut = re.search(r'CaptureColorPrimaries" value="([^"]+)"', text)
    gamma, gamut = (gamma.group(1) if gamma else ""), (gamut.group(1) if gamut else "")
    return gamma, SONY.get((gamma, gamut))


def to_linear(code, gamma):
    """A 10-bit full-range code value (0..1023) to scene light."""
    if gamma.startswith("s-log3"):
        return 10 ** ((code - 420) / 261.5) * 0.19 - 0.01 if code >= 171.2 else (code - 95) * 0.01125 / (171.2 - 95)
    if gamma.startswith("s-log2"):
        x = code / 1023
        return (10 ** ((x - 0.616596 - 0.03) / 0.432699) - 0.037584) * 0.9 if x >= 0.030001222851889303 else (x - 0.030001222851889303) * 0.28258064516129 * 0.9
    return (max(code, 0) / 1023) ** 2.4                   # video gammas, near enough for a balance


def stops(path, gamma, fps, first, last):
    """The log-average scene light of five frames of the used part, in stops."""
    vals = []
    for p in (0.15, 0.35, 0.5, 0.65, 0.85):
        t = (first + (last - first) * p) / fps
        try:
            raw = subprocess.run([FFMPEG, "-v", "error", "-ss", "%.3f" % t, "-i", path, "-frames:v", "1",
                                  "-vf", "scale=192:108,format=gray16le", "-f", "rawvideo", "-"],
                                 capture_output=True, timeout=40).stdout
        except subprocess.TimeoutExpired:
            continue
        if len(raw) < 2:
            continue
        px = memoryview(raw).cast("H")
        s = 0.0
        for x in px:
            code = ((x / 65535 * 1023) - 64) / 876 * 1023    # legal range to full
            s += math.log2(max(to_linear(code, gamma), 1e-4))
        vals.append(s / len(px))
    return statistics.median(vals) if vals else None


# ---- the job --------------------------------------------------------------------------------------------------------

def main():
    rv = get_resolve()
    project = rv.GetProjectManager().GetCurrentProject()
    tl = project.GetCurrentTimeline() if project else None
    if not tl:
        say("No timeline is open")
        return 1

    for k, v in [("colorScienceMode", "davinciYRGBColorManagedv2"), ("isAutoColorManage", "0"),
                 ("colorSpaceTimeline", "DaVinci WG/Intermediate"), ("colorSpaceOutput", "Rec.709 Gamma 2.4"),
                 ("colorSpaceOutputToneMapping", "None" if os.path.exists(KODAK) else "DaVinci")]:
        if project.GetSetting(k) != v and not project.SetSetting(k, v):
            say(f"Resolve refused {k} = {v}")

    items = []
    for t in range(1, tl.GetTrackCount("video") + 1):
        for it in tl.GetItemListInTrack("video", t) or []:
            mp = it.GetMediaPoolItem()
            path = mp.GetClipProperty("File Path") if mp else ""
            if path and os.path.exists(path):
                items.append((it, mp, path))
    if not items:
        say("No clips with media on the timeline")
        return 1

    # 2 + 3: input colour space and the measurement
    measured = []
    for it, mp, path in items:
        gamma, space = sony_space(path)
        if space and mp.GetClipProperty("Input Color Space") != space:
            mp.SetClipProperty("Input Color Space", space)
        fps = float(mp.GetClipProperty("FPS") or 25)
        first = it.GetLeftOffset() if hasattr(it, "GetLeftOffset") else 0
        last = first + it.GetDuration()
        ev = stops(path, gamma or "", fps, first, last)
        measured.append(ev)
        say(f"{it.GetName()}: {space or 'as read'}, {ev if ev is None else round(ev, 2)} stops")
    known = [e for e in measured if e is not None]
    target = statistics.median(known) if known else 0

    report = []
    for (it, mp, path), ev in zip(items, measured):
        shift = 0.0 if ev is None else max(-LIMIT, min(LIMIT, PULL * (target - ev)))
        o = "%.5f" % (shift * STEP)
        it.SetCDL({"NodeIndex": "1", "Slope": "1 1 1", "Offset": f"{o} {o} {o}", "Power": "1 1 1", "Saturation": "1"})
        report.append({"clip": it.GetName(), "stops": None if ev is None else round(ev, 2), "shift": round(shift, 2)})

    # 4: the look
    os.makedirs(LUT_DIR, exist_ok=True)
    lut = os.path.join(LUT_DIR, LUT_FILE)
    write_lut(lut)
    project.RefreshLUTList()
    group = next((g for g in project.GetColorGroupsList() or [] if g.GetName() == GROUP), None) \
        or project.AddColorGroup(GROUP)
    for it, _, _ in items:
        it.AssignToColorGroup(group)
    if not group.GetPostClipNodeGraph().SetLUT(1, lut):
        say("Resolve refused the look LUT on the group's post-clip node")

    # 5: the export
    out = os.path.join(os.path.dirname(items[0][2]), OUT_NAME)
    os.makedirs(out, exist_ok=True)
    project.SetCurrentRenderMode(0)
    project.SetCurrentRenderFormatAndCodec("mp4", "H264")
    ok = project.SetRenderSettings({"SelectAllFrames": True, "TargetDir": out, "FormatWidth": 1920, "FormatHeight": 1080,
                                    "VideoQuality": BITRATE, "ExportVideo": True, "ExportAudio": True})
    job = project.AddRenderJob()
    started = bool(job) and project.StartRendering([job], isInteractiveMode=False)
    with open(os.path.join(out, "balance.json"), "w") as f:
        json.dump({"target_stops": round(target, 2), "clips": report}, f, indent=1)
    say(f"{len(items)} clips balanced and graded; render {'started' if started else 'NOT started'} into {out}"
        + ("" if ok else " (some render settings refused)"))
    return 0 if started else 1


if __name__ == "__main__":
    sys.exit(main())
