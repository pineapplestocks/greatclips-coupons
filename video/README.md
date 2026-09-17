# Automated GreatClipsDeal videos — version 2

The generator makes a roughly 47-second coupon guide with local neural narration,
nine short shots, animated typography, an editorial salon image, animated search
and email illustrations, highlighted captions and a quiet original instrumental
bed. The old Windows voice and presentation renderer have been removed.

## Run

```powershell
python -m pip install -r video/requirements.txt
python -m video
```

Run from the repository root. The first run downloads approximately 340 MB of
speech model/voice assets from the kokoro-onnx GitHub release to `.cache/kokoro`,
verifies SHA-256 hashes, and caches them. Narration then runs locally without a
speech API key. Default voice: Kokoro `af_heart`, speed 1.07. Use `--voice af_bella`
for another supported Kokoro voice. `--voice-provider auto` is now an alias for
Kokoro. If neural speech fails, generation stops; there is no robotic fallback.

The optional `edge` provider requires network access and its own voice names:
`--voice-provider edge --voice en-US-AriaNeural`.

Outputs appear under `output/videos/<episode-id>/`:

- `video.mp4`: H.264 1080p, 30 fps, AAC stereo, with captions
- `thumbnail.jpg`: matching 1280 × 720 thumbnail
- `description.txt`, `youtube.json`: title, description, grouped chapters, UTM link
- `captions.srt`, `script.txt`: captions and narration
- `plan.json`, `timeline.json`: offer evidence and shot timing
- `narration.wav`, `music.wav`, `scene-*.png`: production/review files

Caption groups and word highlighting use estimated timing within each neural
utterance, not forced alignment. The instrumental bed is synthesized locally and
ducked under speech. See [asset provenance and licenses](assets/ASSETS.md).

## Content automation

The deployed schedule uses `--mode local`: one geographic area per video, with
up to three verified offers. A single verified offer is sufficient for a local
episode. Each address is included in narration and the description, with a
matching location thumbnail using the official offer page's coupon artwork,
preserved uncropped with a location label outside the image. Artwork source URLs
are saved in `thumbnail.source.json`; missing artwork stops publication.
Offer fingerprints prevent duplicates across all
video types; each location is limited to one new episode per seven days.
Repeated local runs can create separate episodes for different eligible areas.

The first automatic run makes the evergreen guide once. Subsequent runs make
local deal briefs only when at least two new offers can be confirmed from their
official pages. Otherwise the job skips. It does not fill a quota with repeated
content. The feed's legacy `price` field is never assumed to mean a haircut price.

Deal checks require explicit official wording for the amount/type, a confirmed
geographic label, and a clear expiry at least three days away. Image-only,
unavailable and ambiguous offers are skipped. Checks confirm online wording, not
actual salon acceptance. Reissued codes for equivalent offers do not count as new
content. At most one deal brief is made per seven days.

History lives in `data/video-state.json`; do not delete it to force production
runs. Version 2 has a new episode ID so the rejected first version does not
prevent creating the replacement.

```powershell
# Inspect the plan without rendering or changing history
python -m video --mode deals --plan-only

# Separate local preview history
python -m video --mode guide --state output/preview-state.json

# Smaller video
python -m video --height 720

# Tests
python -m unittest discover -s video/tests -v
```

## Weekly generation

`.github/workflows/youtube-videos.yml` runs Thursdays at 16:30 UTC and supports
manual triggering in Actions. It tests the code, caches neural speech assets,
renders eligible episodes, saves downloadable `video-package` artifacts for
90 days, and commits the creation ledger. Existing website jobs are unchanged.

The scheduled and manual default is `local`. The initial guide can be selected
explicitly. Upload receipts record both requested and returned privacy status.
Google OAuth Testing refresh tokens expire after seven days for YouTube access:
switch the OAuth audience to In production and authorize again for sustained
automation. This setting is separate from any YouTube API project audit.

The schedule starts only after these changes are pushed to the default branch
and Actions is enabled. Repository rules must permit writing the ledger. Actions
usage depends on your account allowance. Local generation does not activate the
schedule or publish a video.

## Optional automated YouTube upload: connect once

Uploading is disabled by default. Authorize your own channel once:

1. Enable YouTube Data API v3 in Google Cloud, configure OAuth consent, and create
   a Desktop app OAuth client. Save its downloaded JSON outside the repository or
   under the ignored filename `youtube-client.json`.
2. Run:

   ```powershell
   python -m video.youtube authorize --client-secrets C:/path/to/youtube-client.json
   ```

   Sign in to the intended channel. The token is saved in the ignored file
   `.cache/youtube/token.json`. Never commit it or paste it into chat.
3. Save the token contents as the Actions secret `YOUTUBE_TOKEN_JSON`. Configure
   OAuth for sustained use; testing-mode credentials may require renewal.
4. Set the repository variable `YOUTUBE_UPLOAD_ENABLED=true`. Uploads default to
   private. Deliberately set `YOUTUBE_PRIVACY=public` or `unlisted` if desired.
5. Enable channel features for custom thumbnails and clickable links.

```powershell
# Upload an existing package
python -m video.youtube upload output/videos/EPISODE_ID --privacy private

# Create and upload
python -m video --upload --privacy private
```

The uploader sends the video, metadata and thumbnail. It sets
`containsSyntheticMedia` because the generic salon photograph was AI-generated.
Captions are burned in; the separate SRT is included but not separately uploaded.
Unverified API projects can be restricted to private uploads until a Google audit;
see [YouTube API documentation](https://developers.google.com/youtube/v3/docs/videos/insert).

An upload intent is saved before calling YouTube. If a network failure leaves the
outcome uncertain, the next job does not blindly upload another copy. Download
the artifact and check `youtube-receipt.json` and your channel before retrying.
With an existing receipt the upload command reuses the ID and retries the
thumbnail. Deal uploads must happen on their live-check date.

## Maintenance

### Search metadata and captions

All new uploads use `seo.py` for location-and-offer titles, unique descriptive
opening lines, tracked website links, exact addresses and expirations, a small
set of relevant tags, and three relevant hashtags. Dollar-off coupons remain
discounts, never advertised as fixed haircut prices. Chapters use actual scene
starts and require at least three sections of ten seconds each.

For updates to already-published videos and English SRT uploads, authorize with:

```powershell
python -m video.youtube authorize --manage-videos --client-secrets C:/path/to/client.json
python -m video.youtube update-metadata output/videos/EPISODE_ID
```

Replace the Actions token secret after reauthorization. The extra YouTube scope
is required by Google's metadata and caption endpoints. Metadata updates back
up the previous values, preserve other writable snippet fields, and never write
the privacy/status part. Existing English caption tracks are preserved. Future
uploads attach generated English captions when the token has this permission;
upload-only tokens can still publish the video with the improved metadata.

Caption timing is estimated from each neural utterance, not forced alignment.
Search optimization improves relevance and clarity; it cannot guarantee ranks.
Check impressions, click-through rate and viewer retention in YouTube Studio
once the channel has enough traffic to compare results.

- `planner.py`: offer selection, factual checks, short scripts
- `neural.py`: verified model downloads and local neural speech
- `motion.py`: frame-by-frame visuals, animation, thumbnail, captions
- `sound.py`: original instrumental bed and transition sounds
- `render.py`: speech caching, timing, encoding, audio mix
- `__main__.py`: CLI, metadata, grouped chapters, history
- `youtube.py`: optional OAuth and uploading
- `seo.py`: factual search titles, descriptions, tags and valid chapter lists

The illustrated steps describe the current email-based coupon flow. A future
website flow change needs a corresponding script/visual update. The generated
salon image is generic, not footage of an actual Great Clips location.

The replacement was rendered locally with Kokoro at 1080p/30 fps. Verification
decodes the complete MP4. Tests cover factual selection, deduplication, failures,
chapter grouping, frame motion, and preventing Windows voice fallback. YouTube
uploads and GitHub scheduling require the one-time activation above.
