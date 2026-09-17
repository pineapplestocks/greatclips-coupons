"""Optional OAuth connection and resumable uploads. Never opens a browser in CI."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCOPES=["https://www.googleapis.com/auth/youtube.upload"]


def upload(folder, privacy="private"):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    folder=Path(folder)
    metadata=json.loads((folder/"youtube.json").read_text(encoding="utf-8"))
    plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    today=datetime.now(timezone.utc).date().isoformat()
    if plan["offers"] and plan["date"] != today:
        raise RuntimeError("Deal uploads must happen on the live-check date. Regenerate from current offers.")
    raw=os.getenv("YOUTUBE_TOKEN_JSON")
    token=Path(".cache/youtube/token.json")
    if not raw and token.exists():
        raw=token.read_text(encoding="utf-8")
    if not raw:
        raise RuntimeError("YouTube is not connected. Run python -m video.youtube authorize --client-secrets PATH once.")
    credentials=Credentials.from_authorized_user_info(json.loads(raw),SCOPES)
    service=build("youtube","v3",credentials=credentials,cache_discovery=False)
    receipt_path=folder/"youtube-receipt.json"
    receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if not receipt.get("video_id"):
        request=service.videos().insert(part="snippet,status",body={
            "snippet":metadata["snippet"],
            "status":{"privacyStatus":privacy,"selfDeclaredMadeForKids":False,"containsSyntheticMedia":True}},
            media_body=MediaFileUpload(str(folder/"video.mp4"),chunksize=8*1024*1024,resumable=True))
        response=None
        while response is None:
            _,response=request.next_chunk(num_retries=5)
        receipt={"video_id":response["id"],"requested_privacy":privacy,
                 "actual_privacy":response.get("status",{}).get("privacyStatus","unknown"),
                 "thumbnail_uploaded":False}
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    if not receipt.get("thumbnail_uploaded"):
        service.thumbnails().set(videoId=receipt["video_id"],
            media_body=MediaFileUpload(str(folder/"thumbnail.jpg"),mimetype="image/jpeg")).execute(num_retries=3)
        receipt["thumbnail_uploaded"]=True
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    auth=commands.add_parser("authorize")
    auth.add_argument("--client-secrets",type=Path,required=True)
    send=commands.add_parser("upload")
    send.add_argument("folder",type=Path)
    send.add_argument("--privacy",choices=["private","unlisted","public"],default="private")
    args=parser.parse_args()
    if args.command == "authorize":
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow=InstalledAppFlow.from_client_secrets_file(str(args.client_secrets),SCOPES)
        credentials=flow.run_local_server(port=0,access_type="offline",prompt="consent")
        target=Path(".cache/youtube/token.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(credentials.to_json(),encoding="utf-8")
        print("Connected. Token saved in .cache/youtube/token.json; keep it private.")
    else:
        receipt=upload(args.folder,args.privacy)
        print(f"YouTube video: https://www.youtube.com/watch?v={receipt['video_id']}")


if __name__ == "__main__":
    main()
