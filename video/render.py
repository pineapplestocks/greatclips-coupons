"""Narration, timed captions, animated 1080p scenes, and H.264 assembly."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

from video.motion import render_thumbnail

FPS = 30


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"Media command failed: {result.stderr[-2500:]}")
    return result


def ffmpeg():
    return os.getenv("FFMPEG_BINARY") or imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    with wave.open(str(path),"rb") as f:
        return f.getnframes()/f.getframerate()


async def edge_speech(text, voice, target):
    import edge_tts
    boundaries=[]
    async def collect():
        with target.open("wb") as f:
            async for item in edge_tts.Communicate(text, voice, rate="+0%", boundary="WordBoundary").stream():
                if item["type"] == "audio":
                    f.write(item["data"])
                elif item["type"] == "WordBoundary":
                    boundaries.append({"start":item["offset"]/1e7,"end":(item["offset"]+item["duration"])/1e7,"text":item["text"]})
    await asyncio.wait_for(collect(),timeout=40)
    return boundaries


def approximate_cues(text, seconds):
    words=text.split()
    groups=[" ".join(words[i:i+4]) for i in range(0,len(words),4)]
    total=sum(len(g) for g in groups)
    offset=0
    result=[]
    for group in groups:
        length=seconds*len(group)/total
        result.append({"start":offset,"end":offset+length,"text":group})
        offset+=length
    return result


def group_boundaries(words, seconds):
    if not words:
        return []
    groups=[]
    for i in range(0,len(words),7):
        group=words[i:i+7]
        start=max(0,group[0]["start"])
        end=min(seconds,group[-1]["end"]+0.12)
        if end > start:
            groups.append({"start":start,"end":end,"text":" ".join(w["text"] for w in group)})
    return groups


class Speaker:
    def __init__(self, provider="kokoro", voice="af_heart", cache=Path(".cache/video-voice")):
        if provider == "sapi":
            raise ValueError("The robotic Windows voice has been removed. Use kokoro or edge.")
        self.provider="kokoro" if provider == "auto" else provider
        self.voice=voice
        self.neural=None
        self.cache=cache.resolve()
        self.cache.mkdir(parents=True,exist_ok=True)

    def speak(self,text,target):
        key=hashlib.sha256(f"v2-speed1.07:{self.provider}:{self.voice}:{text}".encode()).hexdigest()
        cached=self.cache/f"{key}.wav"
        timing=self.cache/f"{key}.json"
        if cached.exists() and timing.exists():
            import shutil
            shutil.copyfile(cached,target)
            data=json.loads(timing.read_text())
            self.provider=data["provider"]
            return duration(target),data["cues"],data["provider"]
        provider=self.provider
        boundaries=[]
        if provider == "kokoro":
            from video.neural import NeuralVoice
            if self.neural is None:
                self.neural=NeuralVoice(self.voice)
            self.neural.speak(text,target)
        elif provider == "edge":
            mp3=target.with_suffix(".mp3")
            try:
                boundaries=asyncio.run(edge_speech(text,self.voice,mp3))
                run([ffmpeg(),"-y","-loglevel","error","-i",mp3,"-ar","48000","-ac","1",target])
                provider="edge"
            except Exception as error:
                raise RuntimeError("Neural narration unavailable. No robotic fallback will be used.") from error
        else:
            raise ValueError(f"Unsupported speech provider: {provider}")
        seconds=duration(target)
        # Keep the same neural voice throughout the episode.
        self.provider=provider
        cues=group_boundaries(boundaries,seconds) or approximate_cues(text,seconds)
        import shutil
        shutil.copyfile(target,cached)
        timing.write_text(json.dumps({"provider":provider,"cues":cues}),encoding="utf-8")
        return seconds,cues,provider


def timestamp(value, ass=False):
    units=100 if ass else 1000
    ticks=round(value*units)
    h,ticks=divmod(ticks,3600*units)
    m,ticks=divmod(ticks,60*units)
    s,sub=divmod(ticks,units)
    return f"{h}:{m:02}:{s:02}.{sub:02}" if ass else f"{h:02}:{m:02}:{s:02},{sub:03}"


def write_ass(cues,path):
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,36,&H00FFFFFF,&H00FFFFFF,&H002A201C,&H002A201C,0,0,0,0,100,100,0,0,3,12,0,2,110,110,121,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=[]
    for cue in cues:
        text=cue["text"].replace("\\"," ").replace("{", "(").replace("}",")").replace("\n"," ")
        lines.append(f"Dialogue: 0,{timestamp(cue['start'],True)},{timestamp(cue['end'],True)},Default,,0,0,0,,{text}")
    path.write_text(header+"\n".join(lines),encoding="utf-8")


def create_video(plan,out,provider="kokoro",voice="af_heart",height=1080):
    import numpy as np
    import soundfile as sf
    from video.motion import frame
    from video.sound import make_bed
    out=out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    speaker=Speaker(provider,voice)
    render_thumbnail(plan,out/"thumbnail.jpg")
    timeline=[]
    all_cues=[]
    offset=0.0
    width=height*16//9
    shots=[]
    audio_parts=[]
    for index,scene in enumerate(plan["scenes"]):
        stem=f"scene-{index:02}"
        print(f"Neural narration {index+1}/{len(plan['scenes'])}: {scene['eyebrow']}",flush=True)
        seconds,cues,actual=speaker.speak(scene["narration"],out/f"{stem}.wav")
        length=math.ceil((seconds+0.13)*FPS)/FPS
        run([ffmpeg(),"-y","-loglevel","error","-i",out/f"{stem}.wav","-af","apad",
             "-t",f"{length:.8f}","-ar","48000","-ac","1",out/f"{stem}-padded.wav"])
        samples,_=sf.read(out/f"{stem}-padded.wav",dtype="float32")
        target_samples=round(length*48000)
        audio_parts.append(np.pad(samples[:target_samples],(0,max(0,target_samples-len(samples)))))
        timeline.append({"title":scene["eyebrow"],"start":offset,"duration":length,"voice_provider":actual})
        shots.append({"scene":scene,"duration":length,"cues":cues})
        all_cues.extend({**c,"start":c["start"]+offset,"end":c["end"]+offset} for c in cues)
        offset+=length
    sf.write(out/"narration.wav",np.concatenate(audio_parts),48000,subtype="PCM_16")
    make_bed(offset,[r["start"] for r in timeline],out/"music.wav")
    print(f"Animating {len(shots)} shots / {offset:.1f}s / {width}x{height}",flush=True)
    error_log=out/"render-error.log"
    with error_log.open("w") as errors:
        encoder=subprocess.Popen([ffmpeg(),"-y","-hide_banner","-loglevel","error",
            "-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}",
            "-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","19",
            "-threads","4","-pix_fmt","yuv420p",str(out/"picture.mp4")],
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
        try:
            for index,shot in enumerate(shots):
                scene,length,cues=shot["scene"],shot["duration"],shot["cues"]
                for number in range(round(length*FPS)):
                    image=frame(scene,number/FPS,length,index,len(shots),cues,height)
                    if number==round(min(length*.55,2)*FPS):
                        image.save(out/f"scene-{index:02}.png")
                    encoder.stdin.write(image.tobytes())
                print(f"Animated shot {index+1}/{len(shots)}",flush=True)
            encoder.stdin.close()
            if encoder.wait(timeout=120):
                raise RuntimeError(error_log.read_text()[-2500:])
        except BaseException:
            encoder.kill()
            encoder.wait(timeout=20)
            raise
    # Duck the original instrumental bed under speech; normalize the final mix.
    filters=("[1:a]loudnorm=I=-16:TP=-2:LRA=9,asplit=2[voice][side];"
             "[2:a][side]sidechaincompress=threshold=0.02:ratio=5:attack=10:release=160[bed];"
             "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.94[a]")
    run([ffmpeg(),"-y","-loglevel","error","-i","picture.mp4","-i","narration.wav","-i","music.wav",
         "-filter_complex",filters,"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k",
         "-ar","48000","-ac","2","-movflags","+faststart","-shortest","video.mp4"],cwd=out,timeout=120)
    (out/"captions.srt").write_text("\n\n".join(f"{i+1}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for i,c in enumerate(all_cues))+"\n",encoding="utf-8")
    (out/"timeline.json").write_text(json.dumps(timeline,indent=2),encoding="utf-8")
    # Decode the complete final file. Corrupt output never advances the ledger.
    run([ffmpeg(),"-v","error","-i","video.mp4","-f","null","-"],cwd=out,timeout=300)
    return timeline
