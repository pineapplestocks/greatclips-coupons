"""Local neural speech. No operating-system voice fallback."""
from __future__ import annotations

import hashlib
from pathlib import Path

import requests

FILES={
    "kokoro-v1.0.onnx":"7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    "voices-v1.0.bin":"bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def ensure_models():
    root=Path(".cache/kokoro").resolve()
    root.mkdir(parents=True,exist_ok=True)
    for name,expected in FILES.items():
        path=root/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==expected:
            continue
        print(f"Downloading neural speech asset: {name}",flush=True)
        temporary=path.with_suffix(".part")
        with requests.get(BASE+name,stream=True,timeout=(10,60)) as response:
            response.raise_for_status()
            digest=hashlib.sha256()
            with temporary.open("wb") as f:
                for chunk in response.iter_content(1024*1024):
                    digest.update(chunk)
                    f.write(chunk)
        if digest.hexdigest()!=expected:
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Neural model checksum mismatch. No fallback voice will be used.")
        temporary.replace(path)
    return root


class NeuralVoice:
    def __init__(self,voice="af_heart",speed=1.07):
        self.voice=voice
        self.speed=speed
        self.engine=None

    def speak(self,text,path):
        import soundfile as sf
        if self.engine is None:
            from kokoro_onnx import Kokoro
            root=ensure_models()
            self.engine=Kokoro(str(root/"kokoro-v1.0.onnx"),str(root/"voices-v1.0.bin"))
        samples,rate=self.engine.create(text,voice=self.voice,speed=self.speed,lang="en-us",sentence_pause=0.12)
        sf.write(str(path),samples,rate,subtype="PCM_16")
