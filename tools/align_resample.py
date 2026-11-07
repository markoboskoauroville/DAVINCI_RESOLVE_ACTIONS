"""align_resample: write recording B on recording A's clock, sample by sample (Marko, 7.11.2026: "align these two
music tracks ... match on the sample level").
points.json = [[tA, offset, corr, env], ...] from fine_offsets.py (B time = tA + offset). Between points the offset is
interpolated (a smooth stretch); where it changes by more than JUMP between neighbours, the jump is found to 0.5 s with
fine measurements and made a hard cut (a recorder that lost samples), never smeared.
python3 align_resample.py A B points.json out.wav"""
import sys, json, subprocess, numpy as np, soundfile as sf, fine_offsets as fo
SR = 48000; JUMP = 0.02
A, B, P, OUT = sys.argv[1:5]
pts = [p for p in json.load(open(P)) if p[2] > 0.2]
t = np.array([p[0] for p in pts]); o = np.array([p[1] for p in pts])
# robust: a point far from both neighbours is noise
keep = np.ones(len(t), bool)
for i in range(1, len(t) - 1):
    if abs(o[i] - o[i-1]) > 0.006 and abs(o[i] - o[i+1]) > 0.006 and abs(o[i-1] - o[i+1]) < 0.006: keep[i] = False
t, o = t[keep], o[keep]
knots_t, knots_o = [t[0]], [o[0]]
for i in range(1, len(t)):
    if abs(o[i] - o[i-1]) > JUMP:   # find the jump between t[i-1] and t[i]
        lo, hi = t[i-1], t[i]
        while hi - lo > 0.5:
            mid = (lo + hi) / 2; om, _ = fo.fine(A, B, mid, o[i-1], win=1.0, search=JUMP * 4)
            if abs(om - o[i-1]) < abs(om - o[i]): lo = mid
            else: hi = mid
        print("jump %.3f s at A %.2f s" % (o[i] - o[i-1], (lo + hi) / 2))
        cut = (lo + hi) / 2
        knots_t += [cut - 1e-6, cut]; knots_o += [o[i-1] + (o[i-1] - knots_o[-1]) * 0, o[i]]
    knots_t.append(t[i]); knots_o.append(o[i])
kt, ko = np.array(knots_t), np.array(knots_o)
durA = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A],capture_output=True,text=True).stdout)
raw = OUT + '.f32'
subprocess.run(['ffmpeg','-v','error','-y','-i',B,'-ac','2','-ar',str(SR),'-f','f32le',raw], check=True)
src = np.memmap(raw, np.float32, 'r').reshape(-1, 2); nB = len(src)
with sf.SoundFile(OUT, 'w', SR, 2, 'PCM_24') as w:
    n = int(durA * SR); step = SR * 30
    for s0 in range(0, n, step):
        ta = np.arange(s0, min(n, s0 + step)) / SR
        pos = (ta + np.interp(ta, kt, ko)) * SR          # where in B each sample of A's clock falls
        i0 = np.floor(pos).astype(np.int64); f = (pos - i0)[:, None]
        ok = (i0 >= 0) & (i0 + 1 < nB)
        y = np.zeros((len(ta), 2), np.float32)
        y[ok] = src[i0[ok]] * (1 - f[ok]) + src[i0[ok] + 1] * f[ok]
        w.write(y)
import os; os.remove(raw)
json.dump({"knots_t": kt.tolist(), "knots_o": ko.tolist()}, open(OUT + '.map.json', 'w'))
print("written", OUT, round(n / SR, 3), "s; B covers A from", round(-ko[0], 3) if ko[0] < 0 else 0, "to", round(min(durA, nB / SR - ko[-1]), 3))
