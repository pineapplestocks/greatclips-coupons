# Assets for video version 2

- `salon-editorial.png`: generated with the built-in image-generation tool for
  this project. Generic fictional salon scene, not a real Great Clips location.
  Its use is disclosed in the video and description; uploads set
  `containsSyntheticMedia` to true.
- `Anton-Regular.ttf`: Google Fonts Anton, SIL Open Font License.
- `Manrope[wght].ttf`: Google Fonts Manrope, SIL Open Font License.
- The adjacent `*-OFL.txt` files retain the full font licenses.

The music is synthesized in `video/sound.py`; it contains no sampled or licensed
recording. The Kokoro ONNX model and voice embeddings are fetched on first run
into `.cache/kokoro`, never committed. Kokoro is Apache-2.0 licensed and the
kokoro-onnx wrapper is MIT licensed. Source and model download provenance:
https://github.com/thewh1teagle/kokoro-onnx
