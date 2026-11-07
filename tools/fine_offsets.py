"""fine_offsets: the offset between two recordings of the same music to the sample, every N seconds.
Rough offset from the onset envelope (avsync), then the band-passed waveforms cross-correlated at 48 kHz with a
parabolic peak: sub-sample. python3 fine_offsets.py A B rough step out.json"""
import sys, json, subprocess, numpy as np, avsync
from scipy.signal import butter, sosfiltfilt, correlate
SR = 48000
def pcm(path, start, dur):
    p = subprocess.run(['ffmpeg','-v','error','-ss','%.4f'%max(0,start),'-i',path,'-t','%.4f'%dur,'-vn','-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True)
    return np.frombuffer(p.stdout,np.float32)
SOS = butter(4,[150,5000],btype='band',fs=SR,output='sos')
def fine(A,B,tA,off,win=3.0,search=0.012):
    a = sosfiltfilt(SOS,pcm(A,tA,win)); b = sosfiltfilt(SOS,pcm(B,tA+off-search,win+2*search))
    c = correlate(b,a,mode='valid'); c /= (np.linalg.norm(a)*np.sqrt(np.convolve(b**2,np.ones(len(a)),'valid'))+1e-12)
    k = int(c.argmax()); y0,y1,y2 = c[max(k-1,0)],c[k],c[min(k+1,len(c)-1)]
    sub = 0.5*(y0-y2)/(y0-2*y1+y2) if (y0-2*y1+y2)!=0 else 0
    return off-search+(k+sub)/SR, float(c[k])
if __name__=='__main__':
    A,B,rough,step,out = sys.argv[1],sys.argv[2],json.loads(sys.argv[3]),float(sys.argv[4]),sys.argv[5]
    endA = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A],capture_output=True,text=True).stdout)
    endB = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',B],capture_output=True,text=True).stdout)
    pts=[]; t=30.0
    while t < min(endA, endB-16.2)-5:
        r = np.interp(t,[p[0] for p in rough],[p[1] for p in rough])
        try:
            d,_,s = avsync.measure(A,t,B,t+r,length=12,search=0.25)
        except Exception:
            t+=step; continue
        o,c = fine(A,B,t+4,r+d)
        pts.append([t+4,o,c,s]); print('%7.1f  %.5f  corr %.2f  env %.1f'%(t+4,o,c,s),flush=True); t+=step
    json.dump(pts,open(out,'w'))
