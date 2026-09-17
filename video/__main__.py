"""Run with python -m video. Outputs are local unless --upload is supplied."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from video.planner import SITE, build_plan


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    temporary.replace(path)


from video.seo import metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=["auto","guide","deals","local"],default="auto")
    parser.add_argument("--feed",type=Path,default=Path("data/coupons.json"))
    parser.add_argument("--state",type=Path,default=Path("data/video-state.json"))
    parser.add_argument("--output",type=Path,default=Path("output/videos"))
    parser.add_argument("--voice-provider",choices=["kokoro","edge","auto"],default="kokoro")
    parser.add_argument("--voice",default=None)
    parser.add_argument("--height",type=int,choices=[720,1080],default=1080)
    parser.add_argument("--plan-only",action="store_true")
    parser.add_argument("--upload",action="store_true")
    parser.add_argument("--privacy",choices=["private","unlisted","public"],default="private")
    args=parser.parse_args()
    feed=json.loads(args.feed.read_text(encoding="utf-8"))
    ledger=json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {"videos":[]}
    plan=build_plan(feed,ledger,args.mode)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/"run.json",plan)
    if plan["status"]=="skipped":
        print(plan["reason"],flush=True)
        return
    folder=args.output/plan["id"]
    folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/"plan.json",plan)
    (folder/"script.txt").write_text("\n\n".join(s["narration"] for s in plan["scenes"]),encoding="utf-8")
    if args.plan_only:
        print(f"Plan ready: {folder}")
        return
    from video.render import create_video
    try:
        voice=args.voice or ("en-US-AriaNeural" if args.voice_provider=="edge" else "af_heart")
        timeline=create_video(plan,folder,args.voice_provider,voice,args.height)
        info=metadata(plan,timeline)
        write_json(folder/"youtube.json",info)
        (folder/"description.txt").write_text(info["snippet"]["description"],encoding="utf-8")
        record={"id":plan["id"],"type":plan["type"],"date":plan["date"],
                "offer_keys":[o["key"] for o in plan["offers"]],"status":"rendered"}
        if plan.get("location"):
            record["location"]=plan["location"]
        ledger["videos"].append(record)
        # Persist an upload intent before making the external call. An ambiguous
        # network failure must not cause next week's job to upload a duplicate.
        if args.upload:
            from video.youtube import upload
            record["status"]="upload_started"
            write_json(args.state,ledger)
            record.update(upload(folder,args.privacy))
            record["status"]="uploaded"
        write_json(args.state,ledger)
        write_json(args.output/"run.json",{"status":"complete","folder":str(folder),"id":plan["id"]})
    except Exception:
        write_json(args.output/"run.json",{"status":"failed","folder":str(folder),"id":plan["id"]})
        raise
    print(f"Video package ready: {folder.resolve()}",flush=True)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write(f"### Video created\n{plan['title']}\n\nDownload the video-package artifact for the MP4, thumbnail, captions, and description.\n")


if __name__ == "__main__":
    main()
