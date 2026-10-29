import sys, subprocess, numpy as np
from scipy.signal import stft, fftconvolve
SR, HOP = 8000, 160                         # 50 values a second for the coarse search
def env(path, start=0, dur=None):
    out = []
    t = start
    while True:
        d = 600 if dur is None else min(600, start + dur - t)
        if d <= 0: break
        p = subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',path,'-t',str(d),'-vn','-ac','1','-ar',str(SR),'-f','s16le','-'],capture_output=True)
        x = np.frombuffer(p.stdout,np.int16).astype(np.float32)/32768
        if len(x) < SR: break
        _,_,Z = stft(x,SR,nperseg=256,noverlap=256-HOP)
        m = np.log1p(40*np.abs(Z)); f = np.maximum(0,np.diff(m,axis=1)).sum(0)
        out.append(f[:int(d*SR/HOP)])
        t += d
        if dur is None and len(x) < d*SR*0.99: break
    f = np.concatenate(out); f -= np.convolve(f,np.ones(10)/10,'same')
    return (f-f.mean())/(f.std()+1e-9)
M = env(sys.argv[1]); print('camera envelope', len(M)/50, 's', flush=True)
for song in sys.argv[2:]:
    s = env(song)
    c = fftconvolve(M, s[::-1], 'valid') / len(s)
    k = int(c.argmax()); o = np.delete(c, range(max(0,k-100), k+100))
    print('%s|%.2f|%.1f|%.0f' % (song.split('/')[-1], k/50, (c[k]-o.mean())/(o.std()+1e-9), len(s)/50), flush=True)
