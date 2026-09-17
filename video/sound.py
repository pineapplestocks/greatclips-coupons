"""Quiet original synthesized beat and transition accents; no licensed music."""
import numpy as np
import soundfile as sf


def make_bed(seconds,scene_starts,path,rate=48000):
    total=int(seconds*rate)
    music=np.zeros(total,dtype=np.float32)
    rng=np.random.default_rng(17)
    beat=60/112

    def add(start,samples,gain):
        at=int(start*rate)
        count=min(len(samples),total-at)
        if count>0:
            music[at:at+count]+=samples[:count]*gain

    for i,start in enumerate(np.arange(0,seconds,beat/2)):
        t=np.arange(int(rate*.085))/rate
        noise=rng.normal(0,1,len(t))
        hat=np.diff(noise,prepend=0)*np.exp(-t*65)
        add(start,hat,.009 if i%2 else .006)
        if i%4==0:
            t=np.arange(int(rate*.27))/rate
            kick=np.sin(2*np.pi*(48*t+5*(1-np.exp(-t*30))))*np.exp(-t*19)
            add(start,kick,.10)
        if i%4==2:
            t=np.arange(int(rate*.10))/rate
            clap=rng.normal(0,1,len(t))*np.exp(-t*40)
            add(start,clap,.012)
    # Sparse plucked notes, low beneath speech.
    for i,start in enumerate(np.arange(0,seconds,beat*2)):
        freq=[220,329.63,293.66,196][i%4]
        t=np.arange(int(rate*.6))/rate
        tone=(np.sin(2*np.pi*freq*t)+.25*np.sin(2*np.pi*freq*2*t))*np.exp(-t*9)*(1-np.exp(-t*100))
        add(start,tone,.025)
    for start in scene_starts[1:]:
        t=np.arange(int(rate*.15))/rate
        whoosh=rng.normal(0,1,len(t))*np.sin(np.pi*t/.15)**2
        add(max(0,start-.08),whoosh,.012)
    fade=np.minimum(1,np.minimum(np.arange(total)/rate/.5,(total-np.arange(total))/rate/.6))
    music*=fade
    sf.write(path,np.column_stack((music,music*.92)),rate,subtype="PCM_16")
