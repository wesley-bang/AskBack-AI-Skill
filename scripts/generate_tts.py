#!/usr/bin/env python3
"""Generate one narration file per storyboard scene using OpenAI TTS."""

import argparse
import json
import os
import pathlib
import urllib.error
import urllib.request


def synthesize(text, output, model, voice):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set; refusing to create fake audio")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {"model": model, "voice": voice, "input": text, "response_format": "wav"}
    request = urllib.request.Request(
        f"{base_url}/audio/speech",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"TTS API failed ({exc.code}): {detail}") from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", default="work/storyboard.json")
    parser.add_argument("--workdir", default="work")
    parser.add_argument("--model", default=os.environ.get("ASKBACK_TTS_MODEL", "tts-1"))
    parser.add_argument("--voice", default=os.environ.get("ASKBACK_TTS_VOICE", "alloy"))
    args = parser.parse_args()
    storyboard = json.loads(pathlib.Path(args.storyboard).read_text(encoding="utf-8"))
    audio_dir = pathlib.Path(args.workdir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, scene in enumerate(storyboard["scenes"], 1):
            path = audio_dir / f"scene_{index:02d}.wav"
            if path.exists() and path.stat().st_size > 44:
                continue
            synthesize(scene["narration"], path, args.model, args.voice)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"audio_dir": str(audio_dir), "scenes": len(storyboard["scenes"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
