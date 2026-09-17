"""Optional OAuth connection and resumable uploads. Never opens a browser in CI."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
MANAGE_SCOPE="https://www.googleapis.com/auth/youtube.force-ssl"


def connect():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    token=Path('.cache/youtube/token.json')
    raw=os.getenv('YOUTUBE_TOKEN_JSON') or (token.read_text(encoding='utf-8') if token.exists() else None)
    if not raw:
        raise RuntimeError('YouTube is not connected. Authorize first.')
    credentials=Credentials.from_authorized_user_info(json.loads(raw))
    return build('youtube','v3',credentials=credentials,cache_discovery=False),credentials


def upload_captions(service, video_id, folder):
    from googleapiclient.http import MediaFileUpload
    path=Path(folder)/'captions.srt'
    if not path.exists():
        return 'missing'
    tracks=service.captions().list(part='snippet',videoId=video_id).execute().get('items',[])
    for track in tracks:
        if track['snippet'].get('language')=='en':
            return 'existing'
    service.captions().insert(part='snippet',body={'snippet':{
        'videoId':video_id,'language':'en','name':'English - GreatClipsDeal','isDraft':False}},
        media_body=MediaFileUpload(str(path),mimetype='application/octet-stream')).execute(num_retries=3)
    return 'uploaded'


def update_metadata(folder):
    """Update the existing video only; preserve privacy and other snippet fields."""
    folder=Path(folder)
    receipt=json.loads((folder/'youtube-receipt.json').read_text())
    desired=json.loads((folder/'youtube.json').read_text(encoding='utf-8'))['snippet']
    service,credentials=connect()
    if not credentials.has_scopes([MANAGE_SCOPE]):
        raise RuntimeError('Editing existing videos needs authorize --manage-videos and Google consent.')
    items=service.videos().list(part='snippet',id=receipt['video_id']).execute().get('items',[])
    if len(items)!=1:
        raise RuntimeError('Published video could not be read; refusing metadata replacement.')
    current=items[0]['snippet']
    writable=('title','description','tags','categoryId','defaultLanguage','defaultAudioLanguage')
    previous={k:current[k] for k in writable if k in current}
    backup=folder/'youtube-before-seo.json'
    if not backup.exists():
        backup.write_text(json.dumps({'snippet':previous},indent=2),encoding='utf-8')
    snippet={**previous,**desired}
    response=service.videos().update(part='snippet',body={'id':receipt['video_id'],'snippet':snippet}).execute(num_retries=3)
    if any(response['snippet'].get(k)!=snippet[k] for k in ('title','description','tags')):
        raise RuntimeError('YouTube did not return the expected metadata.')
    receipt['seo_updated']=True
    # Save the metadata result even if caption processing needs a later retry.
    (folder/'youtube-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    receipt['captions']=upload_captions(service,receipt['video_id'],folder)
    (folder/'youtube-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


def upload(folder, privacy="private"):
    from googleapiclient.http import MediaFileUpload
    folder=Path(folder)
    metadata=json.loads((folder/"youtube.json").read_text(encoding="utf-8"))
    plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    today=datetime.now(timezone.utc).date().isoformat()
    if plan["offers"] and plan["date"] != today:
        raise RuntimeError("Deal uploads must happen on the live-check date. Regenerate from current offers.")
    service,credentials=connect()
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
    if credentials.has_scopes([MANAGE_SCOPE]):
        receipt['captions']=upload_captions(service,receipt['video_id'],folder)
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    auth=commands.add_parser("authorize")
    auth.add_argument("--client-secrets",type=Path,required=True)
    auth.add_argument('--manage-videos',action='store_true',help='Allow existing-video metadata edits and caption uploads.')
    update=commands.add_parser('update-metadata')
    update.add_argument('folder',type=Path)
    send=commands.add_parser("upload")
    send.add_argument("folder",type=Path)
    send.add_argument("--privacy",choices=["private","unlisted","public"],default="private")
    args=parser.parse_args()
    if args.command == "authorize":
        from google_auth_oauthlib.flow import InstalledAppFlow
        scopes=SCOPES+[MANAGE_SCOPE] if args.manage_videos else SCOPES
        flow=InstalledAppFlow.from_client_secrets_file(str(args.client_secrets),scopes)
        credentials=flow.run_local_server(port=0,access_type="offline",prompt="consent")
        target=Path(".cache/youtube/token.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(credentials.to_json(),encoding="utf-8")
        print("Connected. Token saved in .cache/youtube/token.json; keep it private.")
    elif args.command=='update-metadata':
        receipt=update_metadata(args.folder)
        print(f"Updated SEO and captions: https://www.youtube.com/watch?v={receipt['video_id']}")
    else:
        receipt=upload(args.folder,args.privacy)
        print(f"YouTube video: https://www.youtube.com/watch?v={receipt['video_id']}")


if __name__ == "__main__":
    main()
